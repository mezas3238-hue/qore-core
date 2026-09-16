"""Freeze previously-resolved consumed VT-31 fill bars for tick parity testing.

This manifest is the control group for the tick execution resolver. It contains
only already-consumed R5/R6/R8 gap05 setups whose frozen M1 replay produced a
resolved trade and whose original fill minute therefore had no stop/target path
ambiguity. No fresh period is opened and no rule is retuned.
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

import vt31_historical_tick_window_manifest as ambiguous_manifest
import vt31_r5_candidate as r5
import vt31_r8_fill_attrition_forensics as attr
import vt31_r8_sparse_reference_forensics as sparse

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

MARKETS = ("NAS100", "SP500", "US30")
POLICY = "gap05"
EXPECTED_TOTAL = 339


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _ms(value: object) -> int:
    dt = getattr(value, "astimezone")(UTC)
    return int(dt.timestamp() * 1000)


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

        trade, reason = attr._diagnose_simulation(day_bars, selected_index, selected)
        if trade is None:
            continue
        if reason in {
            "fill-bar-path-ambiguous",
            "later-same-bar-stop-target-ambiguous",
            "lifecycle-unresolved-censored",
        }:
            raise AssertionError("resolved parity row cannot carry an unresolved reason")

        side = getattr(selected, "side").value
        entry = cast(Decimal, getattr(selected, "entry"))
        stop = cast(Decimal, getattr(selected, "stop"))
        risk = abs(entry - stop)
        target = entry + r5.TARGET_R * risk if side == "long" else entry - r5.TARGET_R * risk
        fill_index = ambiguous_manifest._find_fill_index(day_bars, selected_index, entry)
        fill = day_bars[fill_index]
        signal = day_bars[selected_index]

        first_stop = (
            _d(cast(float, getattr(fill, "low"))) <= stop
            if side == "long"
            else _d(cast(float, getattr(fill, "high"))) >= stop
        )
        first_target = (
            _d(cast(float, getattr(fill, "high"))) >= target
            if side == "long"
            else _d(cast(float, getattr(fill, "low"))) <= target
        )
        if first_stop or first_target:
            raise AssertionError("resolved parity fill bar must be path-clear in frozen M1 replay")

        row = {
            "partition": partition,
            "market": market,
            "provider": provider,
            "ny_date": local_day.isoformat(),
            "side": side,
            "signal_opened_at": getattr(signal, "opened_at").astimezone(UTC).isoformat(),
            "fill_bar_opened_at": getattr(fill, "opened_at").astimezone(UTC).isoformat(),
            "fill_bar_closed_at": getattr(fill, "closed_at").astimezone(UTC).isoformat(),
            "tick_window_open_ms": _ms(getattr(fill, "opened_at")),
            "tick_window_close_ms": _ms(getattr(fill, "closed_at")) - 1,
            "entry": str(entry),
            "initial_stop": str(stop),
            "fixed_2r_target": str(target),
            "m1_low": str(_d(cast(float, getattr(fill, "low")))),
            "m1_high": str(_d(cast(float, getattr(fill, "high")))),
            "expected_tick_control": "m1-fill-bar-path-clear",
            "frozen_exit_reason": str(trade["exit_reason"]),
            "frozen_r_multiple": str(trade["r_multiple"]),
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
        counts[partition] = {"total": len(rows) - before, **per_market}

    if len(rows) != EXPECTED_TOTAL:
        raise AssertionError(f"consumed resolved parity total changed: {len(rows)} != {EXPECTED_TOTAL}")
    identities = {str(row["window_id"]) for row in rows}
    if len(identities) != len(rows):
        raise AssertionError("parity window ids must be unique")
    rows.sort(
        key=lambda item: (
            str(item["partition"]),
            int(cast(int, item["tick_window_open_ms"])),
            str(item["market"]),
        )
    )
    payload: dict[str, object] = {
        "schema": "qore.vt31.consumed_resolved_fill_bar_tick_parity.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "reference_policy": POLICY,
        "expected_total": EXPECTED_TOTAL,
        "counts": counts,
        "windows": rows,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    Path("vt31-historical-tick-parity-windows.json").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    )
    Path("vt31-historical-tick-parity-summary.json").write_text(
        json.dumps(counts, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps({"total": len(rows), "counts": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
