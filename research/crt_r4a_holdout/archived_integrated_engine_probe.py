"""Run unified causal R4-A research engine on source-verified USDCHF native M5.

Counts experimental A/B events only: NO trades, PnL, bid/ask or Pine parity.
Original 2024–2025 archive was previously researched and is NOT a virgin OOS.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from research.crt_r4a_holdout.archived_2y_strategy_proxy import source_m5
from research.crt_r4a_holdout.causal_crt_m5_engine import Candle, CausalCRTM5
from research.crt_r4a_holdout.seven_family_event_tape import write_event_tape


def analyze(
    root: Path, symbol: str, family: str, cohort: str,
    event_tape_out: Path | None = None,
) -> dict:
    if family not in ("forex", "index"):
        raise ValueError("BTC original source not supplied")
    bars, verified = source_m5(root, symbol, cohort)
    engine = CausalCRTM5(symbol, family=family, phase=0)
    events_per_year: Counter[str] = Counter()
    latest = None
    for old in bars:
        candle = Candle(
            old.opened_at, float(old.open), float(old.high),
            float(old.low), float(old.close)
        )
        new = engine.consume(candle)
        for e in new:
            if not (
                e.sweep_at < e.mss_at <= e.available_at
                and e.ratified_at <= e.available_at
            ):
                raise ValueError("causality breach")
            if e.available_at > candle.opened_at:
                raise ValueError("event emitted before it was observable")
            events_per_year[str(e.available_at.year) + "_" + e.model] += 1
        latest = candle
    if len(bars) != verified["total_m5"]:
        raise ValueError("provider count mismatch")
    ids = [e.identity for e in engine.evidence]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate CRT cycle identity")
    report = engine.readout()
    if event_tape_out is not None:
        report["source_event_tape"] = write_event_tape(
            event_tape_out, engine=engine, provider_cohort=cohort
        )
    report.update({
        "provider_cohort": cohort,
        "source_m5_rows": verified["total_m5"],
        "last_native_m5_time": latest.opened_at.isoformat() if latest else None,
        "events_per_year_model": dict(events_per_year),
        "year_2024_2025_SHA256_verified": True,
        "replay_period_used": "2024_2025_ALREADY_RESEARCHED",
        "full_pine_f_engine_parity": False,
        "mss_with_exact_provider_phase_parity": False,
        "bid_ask_costs_included": False,
        "real_money_authorized": False,
        "trades_executed": 0,
    })
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--family", choices=("forex", "index"), required=True)
    parser.add_argument("--cohort", required=True)
    parser.add_argument("--event-tape", type=Path)
    args = parser.parse_args()
    print(json.dumps(
        analyze(
            args.root, args.symbol, args.family, args.cohort,
            event_tape_out=args.event_tape,
        ), sort_keys=True
    ))


if __name__ == "__main__":
    main()
