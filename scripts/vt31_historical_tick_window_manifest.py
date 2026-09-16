"""Freeze exact consumed VT-31 fill-bar windows that require tick resolution.

The manifest is reconstructed from the immutable R5/R6/R8 market evidence and
frozen R8 simulator semantics. It opens no new evidence and changes no trading
rule. Only `gap05`-admitted setups whose frozen M1 replay ends in
`fill-bar-path-ambiguous` are emitted.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5
import vt31_r8_fill_attrition_forensics as attr
import vt31_r8_sparse_reference_forensics as sparse

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

MARKETS = ("NAS100", "SP500", "US30")
EXPECTED = {"r5": 157, "r6": 159, "r8_fresh": 121}
POLICY = "gap05"


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _ms(value: object) -> int:
    dt = getattr(value, "astimezone")(UTC)
    return int(dt.timestamp() * 1000)


def _find_fill_index(
    day_bars: tuple[object, ...], signal_index: int, entry: Decimal
) -> int:
    for index in range(signal_index + 1, len(day_bars)):
        bar = day_bars[index]
        if _wall(getattr(bar, "opened_at")) >= (11, 0, 0):
            break
        if r5._touch(bar, entry):
            return index
    raise AssertionError("ambiguous classification must have an entry-touch fill bar")


def _run_market(path: Path, market: str, partition: str) -> list[dict[str, object]]:
    series, _, _, _, _, provider = load_market_evidence(path)
    by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)

    rows: list[dict[str, object]] = []
    for local_day in sorted(by_day):
        day_bars = tuple(by_day[local_day])
        reference = sparse._reference_bars(day_bars)
        indexed_session = tuple(
            (index, bar)
            for index, bar in enumerate(day_bars)
            if (10, 0, 0) <= _wall(getattr(bar, "opened_at")) < (11, 0, 0)
        )
        if len(indexed_session) != 60 or not reference:
            continue
        if not sparse._policy_accepts(reference, POLICY):
            continue
        ref_high = max(_d(cast(float, getattr(item, "high"))) for item in reference)
        ref_low = min(_d(cast(float, getattr(item, "low"))) for item in reference)
        ref_width = ref_high - ref_low
        if ref_width <= 0:
            continue

        prefix = list(reference)
        selected: object | None = None
        selected_index: int | None = None
        for global_index, bar in indexed_session:
            prefix.append(bar)
            candidate, _ = sparse._evaluate_sparse(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                bars=tuple(prefix),
                variant=r5.BASE_VARIANT,
            )
            if candidate is None:
                continue
            if not sparse._quality_sparse(tuple(prefix), candidate, ref_width):
                break
            selected = candidate
            selected_index = global_index
            break
        if selected is None or selected_index is None:
            continue

        _, reason = attr._diagnose_simulation(day_bars, selected_index, selected)
        if reason != "fill-bar-path-ambiguous":
            continue

        side = getattr(selected, "side").value
        entry = cast(Decimal, getattr(selected, "entry"))
        stop = cast(Decimal, getattr(selected, "stop"))
        risk = abs(entry - stop)
        target = entry + r5.TARGET_R * risk if side == "long" else entry - r5.TARGET_R * risk
        fill_index = _find_fill_index(day_bars, selected_index, entry)
        fill = day_bars[fill_index]
        signal = day_bars[selected_index]
        row = {
            "partition": partition,
            "market": market,
            "provider": provider,
            "ny_date": local_day.isoformat(),
            "side": side,
            "signal_opened_at": getattr(signal, "opened_at").astimezone(UTC).isoformat(),
            "signal_closed_at": getattr(signal, "closed_at").astimezone(UTC).isoformat(),
            "fill_bar_opened_at": getattr(fill, "opened_at").astimezone(UTC).isoformat(),
            "fill_bar_closed_at": getattr(fill, "closed_at").astimezone(UTC).isoformat(),
            "tick_window_open_ms": _ms(getattr(fill, "opened_at")),
            "tick_window_close_ms": _ms(getattr(fill, "closed_at")) - 1,
            "entry": str(entry),
            "initial_stop": str(stop),
            "fixed_2r_target": str(target),
            "m1_low": str(_d(cast(float, getattr(fill, "low")))),
            "m1_high": str(_d(cast(float, getattr(fill, "high")))),
            "classification": reason,
        }
        row_material = json.dumps(row, sort_keys=True, separators=(",", ":"))
        row["window_id"] = hashlib.sha256(row_material.encode()).hexdigest()[:24]
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 9:
        print("usage: script R5_NAS R5_SP R5_US R6_NAS R6_SP R6_US R8_NAS R8_SP R8_US")
        return 2
    partitions = {
        "r5": dict(zip(MARKETS, map(Path, args[0:3]), strict=True)),
        "r6": dict(zip(MARKETS, map(Path, args[3:6]), strict=True)),
        "r8_fresh": dict(zip(MARKETS, map(Path, args[6:9]), strict=True)),
    }
    rows: list[dict[str, object]] = []
    counts: dict[str, dict[str, int]] = {}
    for partition, paths in partitions.items():
        per_market: dict[str, int] = {}
        before = len(rows)
        for market, path in paths.items():
            market_rows = _run_market(path, market, partition)
            rows.extend(market_rows)
            per_market[market] = len(market_rows)
        observed = len(rows) - before
        if observed != EXPECTED[partition]:
            raise AssertionError(
                f"{partition} ambiguous-window parity failed: {observed} != {EXPECTED[partition]}"
            )
        counts[partition] = {"total": observed, **per_market}

    rows.sort(key=lambda item: (
        str(item["partition"]),
        int(cast(int, item["tick_window_open_ms"])),
        str(item["market"]),
    ))
    payload: dict[str, object] = {
        "schema": "qore.vt31.consumed_fill_bar_tick_windows.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "R8_REJECTED_FRESH_CONSUMED",
        "reference_policy": POLICY,
        "counts": counts,
        "windows": rows,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    Path("vt31-historical-tick-windows.json").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    )
    Path("vt31-historical-tick-window-summary.json").write_text(
        json.dumps(counts, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
