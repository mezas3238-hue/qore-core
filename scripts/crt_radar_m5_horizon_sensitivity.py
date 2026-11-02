#!/usr/bin/env python3
"""Experimental M5 history-window sensitivity, same-source calibration only.

Reproduces history-window length (1500 M5 vs full defined calibration) with
identical simple structural predicates. Not parity to Pine f_engine/TradingView.
No prices are written or printed; sources stay on ephemeral GH runner.
"""
from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path

from scripts.crt_radar_archived_m5_prescreen import (
    CAL_END, CAL_START, C1_HOURS, H4, M5,
    _verify_2026_partition, completed_h4, frozen_bucket, native_to_bar,
)

SCOPE = "IN_SAMPLE_M5_WINDOW_STUDY_NOT_PINE_PARITY"


def measure(closed_m5: list[M5], family: str) -> dict[str, int]:
    """Only closed, contiguous NY-H4 and strict unilateral sweep+return."""
    if family not in C1_HOURS:
        raise ValueError("BAD_FAMILY")
    groups: list[tuple[str, list[M5]]] = []
    previous_key = None
    for bar in closed_m5:
        key, _ = frozen_bucket(bar, family)
        if previous_key != key:
            groups.append((key, []))
            previous_key = key
        groups[-1][1].append(bar)
    candidate: H4 | None = None
    followup: tuple[H4, int] | None = None
    eligible_c1 = c2_count = c3_count = rejected = internal = closed_h4 = 0
    last_c2_closed_at = None
    for _, bars in groups:
        b = completed_h4(bars, family)
        if b is None:
            rejected += 1
            internal += int(any(
                bars[i].opened_at - bars[i - 1].opened_at != timedelta(minutes=5)
                for i in range(1, len(bars))
            ))
            candidate = None
            followup = None
            continue
        closed_h4 += 1
        eligible_c1 += int(b.c1_allowed)
        if followup:
            prior, direction = followup
            if (prior.closed_at == b.opened_at and
                (b.close >= prior.low if direction > 0 else b.close <= prior.high)):
                c3_count += 1
        followup = None
        if candidate is not None and candidate.closed_at == b.opened_at:
            low = b.low < candidate.low
            high = b.high > candidate.high
            if candidate.c1_allowed and low != high and candidate.low <= b.close <= candidate.high:
                c2_count += 1
                followup = (b, 1 if low else -1)
                last_c2_closed_at = b.closed_at
        candidate = b
    # No historical signal becomes 'currently valid' merely because it was
    # counted. This optional diagnostic is NOT the Pine CRT+MSS gate.
    return {
        "observed_m5": len(closed_m5),
        "h4_closed": closed_h4,
        "eligible_c1": eligible_c1,
        "structural_2c_historical": c2_count,
        "structural_3c_followup": c3_count,
        "h4_partial": rejected,
        "h4_internal_gap": internal,
        "last_c2_close_utc_ms": int(last_c2_closed_at.timestamp() * 1000)
        if last_c2_closed_at else None,
    }


def inspect_window(root: Path, symbol: str, family: str, cohort: str) -> dict[str, object]:
    if family not in C1_HOURS or cohort not in (
        "ATLAS_DEMO_BROKER_UNVERIFIED", "ICMARKETS_DEMO_CONFIRMED"
    ):
        raise ValueError("INVALID_SCOPE_OR_COHORT")
    source, manifest = _verify_2026_partition(root)
    provider = ({"NAS100": "USTEC", "SP500": "US500"}.get(symbol, symbol)
                if cohort == "ATLAS_DEMO_BROKER_UNVERIFIED" else symbol)
    if (manifest.get("canonical_symbol") != symbol or
        manifest.get("provider_symbol") != provider):
        raise ValueError("PROVIDER_SOURCE_ALIAS_MISMATCH")
    symbol_id = manifest.get("provider_symbol_id")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise ValueError("PROVIDER_SYMBOL_ID_UNVERIFIED")
    rows: list[M5] = []
    last = None
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            candle = native_to_bar(raw, symbol, provider, symbol_id)
            if last is not None and candle.opened_at <= last:
                raise ValueError("OUT_OF_ORDER_SOURCE_M5")
            last = candle.opened_at
            if CAL_START <= candle.opened_at < CAL_END:
                rows.append(candle)
    if len(rows) <= 1500:
        raise ValueError("NOT_ENOUGH_M5_FOR_1500_COMPARISON")
    wide = measure(rows, family)
    short = measure(rows[-1500:], family)
    return {
        "symbol": symbol,
        "cohort": cohort,
        "source_partition_sha256": "VERIFIED",
        "window_as_of_utc": CAL_END.isoformat(),
        "period": "2026-08-01--2026-09-17",
        "scope": SCOPE,
        "full": wide,
        "last_1500_m5": short,
        "historic_2c_lost_from_short_window":
            wide["structural_2c_historical"] - short["structural_2c_historical"],
        "same_provider": True,
        "same_rules": True,
        "is_Pine_f_engine": False,
        "is_fresh_holdout": False,
        "is_TradingView_feed": False,
        "mss_m15_tested": False,
        "send_push": False,
        "orders": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--family", required=True, choices=tuple(C1_HOURS))
    parser.add_argument("--cohort", required=True)
    args = parser.parse_args()
    report = inspect_window(args.root, args.symbol, args.family, args.cohort)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
