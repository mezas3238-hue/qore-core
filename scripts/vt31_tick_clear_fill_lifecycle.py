"""Continue consumed VT-31 tick-clear fills with the frozen M1 lifecycle.

The exact fill minute has already been proven path-clear by BID/ASK evidence. From
the next M1 bar onward this module preserves the original protected-swing trail,
fixed 2R target and 16:00 New York lifecycle. A later M1 bar touching both stop
and target is emitted as an exact consumed ambiguity window instead of guessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_r5_candidate as r5
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import _day, load_market_evidence

MARKETS = ("NAS100", "SP500", "US30")
PARTITIONS = ("r5", "r6", "r8_fresh")
EXPECTED_CLEAR_SOURCE_MINUTE = 47


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _ms(value: object) -> int:
    dt = getattr(value, "astimezone")(UTC)
    return int(dt.timestamp() * 1000)


def _load_market_days(path: Path) -> dict[date, tuple[object, ...]]:
    series, _, _, _, _, _ = load_market_evidence(path)
    grouped: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        grouped[_day(bar.opened_at)].append(bar)
    return {key: tuple(value) for key, value in grouped.items()}


def _ambiguous_window(
    source: dict[str, Any],
    bar: object,
    current_stop: Decimal,
    target: Decimal,
    risk: Decimal,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "parent_window_id": source["window_id"],
        "partition": source["partition"],
        "market": source["market"],
        "provider": source["provider"],
        "ny_date": source["ny_date"],
        "side": source["side"],
        "entry": source["entry"],
        "current_protected_stop": format(current_stop, "f"),
        "fixed_2r_target": format(target, "f"),
        "initial_risk": format(risk, "f"),
        "tick_window_open_ms": _ms(getattr(bar, "opened_at")),
        "tick_window_close_ms": _ms(getattr(bar, "closed_at")) - 1,
        "m1_low": format(_d(cast(float, getattr(bar, "low"))), "f"),
        "m1_high": format(_d(cast(float, getattr(bar, "high"))), "f"),
        "reason": "later-protected-stop-and-fixed-target-same-m1-bar",
    }
    material = json.dumps(row, sort_keys=True, separators=(",", ":"))
    row["window_id"] = hashlib.sha256(material.encode()).hexdigest()[:24]
    return row


def _continue_one(source: dict[str, Any], day_bars: tuple[object, ...]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    side = str(source["side"])
    entry = Decimal(str(source["entry"]))
    initial_stop = Decimal(str(source["initial_stop"]))
    target = Decimal(str(source["fixed_2r_target"]))
    risk = abs(entry - initial_stop)
    if risk <= 0:
        raise ValueError("non-positive frozen risk")
    fill_open = str(source["fill_bar_opened_at"])
    matches = [index for index, bar in enumerate(day_bars) if getattr(bar, "opened_at").astimezone(UTC).isoformat() == fill_open]
    if len(matches) != 1:
        raise ValueError(f"expected one frozen fill bar for {source['window_id']}, got {len(matches)}")
    fill_index = matches[0]
    current_stop = initial_stop
    previous = day_bars[fill_index]

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        local = getattr(bar, "opened_at").astimezone(r5.NY)
        if local.hour * 60 + local.minute >= 16 * 60:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return ({
                "parent_window_id": source["window_id"],
                "status": "censored-m1-continuity-gap",
                "terminal_r": None,
                "exit_reason": None,
                "exit_at": None,
            }, None)
        previous = bar
        low = _d(cast(float, getattr(bar, "low")))
        high = _d(cast(float, getattr(bar, "high")))
        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= target if side == "long" else low <= target
        if hit_stop and hit_target:
            ambiguity = _ambiguous_window(source, bar, current_stop, target, risk)
            return ({
                "parent_window_id": source["window_id"],
                "status": "censored-later-same-bar-stop-target-ambiguity",
                "terminal_r": None,
                "exit_reason": None,
                "exit_at": None,
                "ambiguity_window_id": ambiguity["window_id"],
            }, ambiguity)
        if hit_stop:
            terminal = (current_stop - entry) / risk if side == "long" else (entry - current_stop) / risk
            return ({
                "parent_window_id": source["window_id"],
                "status": "terminal-protected-stop",
                "terminal_r": format(terminal, "f"),
                "exit_reason": "protected-stop",
                "exit_at": getattr(bar, "closed_at").astimezone(UTC).isoformat(),
            }, None)
        if hit_target:
            return ({
                "parent_window_id": source["window_id"],
                "status": "terminal-fixed-2r-target",
                "terminal_r": "2",
                "exit_reason": "fixed-2r-target",
                "exit_at": getattr(bar, "closed_at").astimezone(UTC).isoformat(),
            }, None)
        current_stop = r5._new_protected_stop(
            day_bars,
            index,
            side,
            current_stop,
            _d(cast(float, getattr(bar, "close"))),
        )

    eligible = [
        item
        for item in day_bars
        if getattr(item, "opened_at").astimezone(r5.NY).hour * 60
        + getattr(item, "opened_at").astimezone(r5.NY).minute
        < 16 * 60
    ]
    if not eligible:
        return ({
            "parent_window_id": source["window_id"],
            "status": "censored-no-lifecycle-close",
            "terminal_r": None,
            "exit_reason": None,
            "exit_at": None,
        }, None)
    final = eligible[-1]
    final_close = _d(cast(float, getattr(final, "close")))
    terminal = (final_close - entry) / risk if side == "long" else (entry - final_close) / risk
    return ({
        "parent_window_id": source["window_id"],
        "status": "terminal-16-00-lifecycle",
        "terminal_r": format(terminal, "f"),
        "exit_reason": "16:00-lifecycle",
        "exit_at": getattr(final, "closed_at").astimezone(UTC).isoformat(),
    }, None)


def run(
    manifest_path: Path,
    resolution_path: Path,
    evidence_paths: dict[tuple[str, str], Path],
    output_dir: Path,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text())
    resolution = json.loads(resolution_path.read_text())
    if manifest.get("research_only") is not True or manifest.get("opens_new_holdout") is not False:
        raise ValueError("source manifest governance guard failed")
    if resolution.get("research_only") is not True or resolution.get("opens_new_holdout") is not False:
        raise ValueError("source resolution governance guard failed")
    source_rows = manifest.get("windows")
    resolved_rows = resolution.get("results")
    if not isinstance(source_rows, list) or len(source_rows) != 437:
        raise ValueError("expected immutable 437-row source manifest")
    if not isinstance(resolved_rows, list) or len(resolved_rows) != 437:
        raise ValueError("expected immutable 437-row source resolution")
    sources = {row["window_id"]: row for row in source_rows if isinstance(row, dict)}
    selected = [row for row in resolved_rows if isinstance(row, dict) and row.get("status") == "filled-clear-source-minute"]
    if len(selected) != EXPECTED_CLEAR_SOURCE_MINUTE:
        raise ValueError(f"tick-clear source count changed: {len(selected)}")

    market_days = {key: _load_market_days(path) for key, path in evidence_paths.items()}
    results: list[dict[str, Any]] = []
    ambiguities: list[dict[str, Any]] = []
    for tick_row in selected:
        parent_id = tick_row["window_id"]
        source = sources[parent_id]
        key = (str(source["partition"]), str(source["market"]))
        local_day = date.fromisoformat(str(source["ny_date"]))
        day_bars = market_days[key].get(local_day)
        if day_bars is None:
            raise ValueError(f"missing consumed M1 day for {key} {local_day}")
        result, ambiguity = _continue_one(source, day_bars)
        result.update({
            "partition": source["partition"],
            "market": source["market"],
            "ny_date": source["ny_date"],
            "side": source["side"],
            "tick_fill_timestamp_ms": tick_row.get("fill_timestamp_ms"),
        })
        results.append(result)
        if ambiguity is not None:
            ambiguities.append(ambiguity)

    counts = Counter(str(row["status"]) for row in results)
    payload: dict[str, Any] = {
        "schema": "qore.vt31.tick_clear_fill_frozen_m1_lifecycle.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "source_tick_clear_count": EXPECTED_CLEAR_SOURCE_MINUTE,
        "counts": dict(sorted(counts.items())),
        "results": results,
    }
    ambiguity_payload: dict[str, Any] = {
        "schema": "qore.vt31.consumed_later_same_bar_tick_manifest.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "source": "tick-clear fills continued under frozen M1 protected-swing lifecycle",
        "windows": ambiguities,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "vt31-tick-clear-fill-lifecycle.json").write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    (output_dir / "vt31-later-same-bar-ambiguity-manifest.json").write_text(json.dumps(ambiguity_payload, sort_keys=True, indent=2) + "\n")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--resolution", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    for partition in PARTITIONS:
        for market in MARKETS:
            parser.add_argument(f"--{partition.replace('_', '-')}-{market.lower()}", required=True, type=Path)
    args = parser.parse_args()
    paths: dict[tuple[str, str], Path] = {}
    for partition in PARTITIONS:
        for market in MARKETS:
            attribute = f"{partition}_{market.lower()}"
            paths[(partition, market)] = getattr(args, attribute)
    payload = run(args.manifest, args.resolution, paths, args.output_dir)
    print(json.dumps({"source_tick_clear_count": payload["source_tick_clear_count"], "counts": payload["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
