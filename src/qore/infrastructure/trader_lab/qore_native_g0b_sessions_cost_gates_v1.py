"""QORE Native G0B: source-verified M5 clock signatures, NOT broker sessions.

This research-only module reads timestamp/identity, never OHLC, returns,
volatility or PnL. Observed absence is NOT an exchange or broker closure.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0

IDENTITY = "QORE_NATIVE_EXISTING12_G0B_OBSERVED_CLOCK_V1"
NEW_YORK = ZoneInfo("America/New_York")
G1_STATUS = "BLOCKED_BROKER_SESSIONS_COSTS_AND_NEWS_ASOF"


def utc_m5_census(instants: Iterable[datetime]) -> dict:
    """Descriptive timestamps only. DST local clock slots include UTC offset."""
    previous = None
    bars = gaps = max_gap = missing_slots = 0
    weeks: Counter[str] = Counter()
    weekdays: Counter[str] = Counter()
    slots: Counter[str] = Counter()
    offset_counts: Counter[str] = Counter()
    utc_days: dict[str, int] = {}
    gap_examples: list[dict[str, str | int]] = []
    for instant in instants:
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("naive M5 timestamp")
        at = instant.astimezone(UTC)
        if at.second or at.microsecond or int(at.timestamp()) % 300:
            raise ValueError("non-aligned M5 timestamp")
        if previous is not None:
            delta = int((at - previous).total_seconds()) // 60
            if delta <= 0:
                raise ValueError("duplicate or reversed original M5")
            if delta > 5:
                gaps += 1
                max_gap = max(max_gap, delta)
                missing_slots += delta // 5 - 1
                if len(gap_examples) < 20:
                    gap_examples.append({
                        "prior_utc": previous.isoformat(),
                        "next_utc": at.isoformat(),
                        "unobserved_m5_slots": delta // 5 - 1,
                        "classification": "UNKNOWN_CLOSURE_OR_FEED_GAP",
                    })
        ny = at.astimezone(NEW_YORK)
        offset = ny.strftime("%z")
        iso = ny.isocalendar()
        weeks[f"{iso.year}-W{iso.week:02d}"] += 1
        weekdays[str(ny.weekday())] += 1
        offset_counts[offset] += 1
        slots[f"{ny.weekday()}-{ny.hour:02d}:{ny.minute:02d}-{offset}"] += 1
        day = at.date().isoformat()
        utc_days[day] = utc_days.get(day, 0) + 1
        bars += 1
        previous = at

    if bars == 0:
        raise ValueError("empty original timestamp series")
    return {
        "bars": bars,
        "observed_utc_calendar_days": len(utc_days),
        "utc_days_with_288_m5": sum(n == 288 for n in utc_days.values()),
        "utc_days_partial": sum(n != 288 for n in utc_days.values()),
        "unclassified_discontinuity_runs": gaps,
        "unclassified_absent_m5_slots_inside_observed_span": missing_slots,
        "max_unclassified_gap_minutes": max_gap,
        "gap_examples_first_20": gap_examples,
        "new_york_utc_offset_bar_counts": dict(sorted(offset_counts.items())),
        "new_york_weekday_bar_counts": dict(sorted(weekdays.items())),
        "new_york_weekly_bar_counts": dict(sorted(weeks.items())),
        "new_york_weekday_clock_offset_bar_counts": dict(sorted(slots.items())),
        "new_york_clock_is_observation_only_not_broker_session": True,
        "broker_rollover_and_dst_verified": False,
        "exchange_holiday_and_expected_closures_verified": False,
        "h4_d1_broker_candles_verified": False,
    }


def source_timestamps(root: Path):
    """Use RAW annual JSONL only after the independent G0 SHA audit passes."""
    for year in g0.YEARS:
        path = root / "RAW_M5_LEDGER" / f"{year}.jsonl"
        with path.open(encoding="utf-8") as infile:
            for line in infile:
                # No row OHLC/volume access.
                yield datetime.fromisoformat(json.loads(line)["opened_at"])


def evidence_gate(evidence: dict | None) -> dict:
    """Presence of a self-declared source never certifies its accuracy."""
    required = (
        "broker_account_type", "symbol_and_contract_provenance_sha256",
        "historical_bid_ask_source_sha256", "broker_commission_schedule_sha256",
        "roundtrip_slippage_calibration_sha256", "swap_financing_source_sha256",
        "news_calendar_known_asof_source_sha256", "broker_session_calendar_sha256",
        "stop_side_bid_ask_execution_protocol_sha256",
    )
    claims = evidence or {}
    missing = [name for name in required if not claims.get(name)]
    return {
        "present_source_claims": sorted(set(required) - set(missing)),
        "missing_source_claims": missing,
        "status": ("SOURCE_CLAIMS_NEED_INDEPENDENT_VERIFICATION"
                   if not missing else "BLOCKED_MISSING_SOURCE_EVIDENCE"),
        "cost_pit_verified": False,
        "broker_session_verified": False,
        "no_news_asof_verified": False,
        "stop_spread_survivability_verified": False,
        "g1_net_authorized": False,
    }


def census_symbol(symbol: str, source: Path, aggregate: Path) -> dict:
    expected = g0.aggregate_index(aggregate)
    original = g0.audit_symbol(symbol, source, expected[symbol])
    clock = utc_m5_census(source_timestamps(source))
    if clock["bars"] != original["native_m5_bars"]:
        raise ValueError("G0B M5 recount differs from SHA-verified G0")
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "provider_symbol": g0.SOURCE_SYMBOL_MAP[symbol],
        "source_run": g0.SOURCE_RUN,
        "producer_sha": g0.PRODUCER_SHA,
        "g0_original_raw_sha_verified": True,
        "source_broker_icmarkets_verified": False,
        "timestamp_clock_census": clock,
        "broker_session_ledger_status": "UNVERIFIED_NOT_INFERRED_FROM_FEED",
        "economic_evidence_gate": evidence_gate(None),
        "status": G1_STATUS,
        "analysis_contains_ohlc_or_pnl": False,
        "holdout_opened": False,
        "live_or_production_affected": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=g0.SYMBOLS)
    parser.add_argument("original_artifact_root", type=Path)
    parser.add_argument("aggregate_original_artifact_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = census_symbol(
        args.symbol, args.original_artifact_root, args.aggregate_original_artifact_root
    )
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / f"qore-native-g0b-{args.symbol}.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / f"{target.name}.sha256").write_text(
        g0.sha256(target) + f"  {target.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "symbol": args.symbol, "bars": result["timestamp_clock_census"]["bars"],
        "status": result["status"], "broker_session_certified": False,
        "no_market_outcomes": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
