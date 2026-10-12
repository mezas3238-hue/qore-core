"""One locked daily UTC momentum, 5-session future gross-reference experiment.

Hypothesis from TSMOM prereg ancestor 1c46194e; exposed DEV/DIAG exploratory.
This is NOT source bid/ask, portfolio NAV, new OOS, NET or live trading.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterable

from qore.research.alpha2_intermarket import MARKETS, Bar, _check_bar, sha256_file
from qore.research.alpha2_lab_h4_extract import (
    source33_manifest,
    source_rows_before_embargo,
    verify_source,
)

IDENTITY = "QORE_ALPHA2_TSMOM_D1_WK252_X5_EXPLORATORY_GROSS_V1"
SOURCE33_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
BEGIN = date(2016, 9, 17)
DEV_END = date(2022, 9, 17)
EMBARGO = date(2024, 9, 17)
MIN_BARS_PER_DAY = 12
LOOKBACK = 252
WARMUP = LOOKBACK + 1
HOLD_SESSIONS = 5


@dataclass(frozen=True)
class Day:
    utc_day: date
    open: float
    close: float
    native_m5_bars: int

    def __post_init__(self) -> None:
        if self.utc_day.weekday() > 4 or not BEGIN <= self.utc_day < EMBARGO:
            raise ValueError("TSMOM_UNADMITTED_DAY")
        if not 0 < self.open or not 0 < self.close or self.native_m5_bars < MIN_BARS_PER_DAY:
            raise ValueError("TSMOM_DAILY_QUOTE_OR_DENSITY_INVALID")


def daily_from_native(bars: Iterable[Bar]) -> tuple[list[Day], dict]:
    """Use only FIRST native M5 open/LAST native M5 close; skip sparse days."""
    daily: list[Day] = []
    day: date | None = None
    start: float | None = None
    last: float | None = None
    n = 0
    prev: datetime | None = None
    dropped = 0
    weekends = 0
    original_bars = 0

    def flush() -> None:
        nonlocal dropped, weekends
        if day is None:
            return
        if day.weekday() > 4:
            weekends += 1
        elif n < MIN_BARS_PER_DAY:
            dropped += 1
        else:
            assert start is not None and last is not None
            daily.append(Day(day, start, last, n))

    for bar in bars:
        _check_bar(bar)
        if bar.at.tzinfo is None or bar.at.utcoffset().total_seconds() != 0:
            raise ValueError("TSMOM_NATIVE_M5_TIMESTAMP_NOT_UTC")
        if bar.at.date() >= EMBARGO:
            raise ValueError("TSMOM_NATIVE_HISTORICAL_EMBARGO_BREACH")
        if (
            prev is not None and bar.at <= prev
            or bar.at.minute % 5 or bar.at.second or bar.at.microsecond
        ):
            raise ValueError("TSMOM_NATIVE_SOURCE_NOT_STRICT_M5")
        original_bars += 1
        prev = bar.at
        newday = bar.at.date()
        if newday != day:
            flush()
            day = newday
            start = bar.open
            n = 0
        last = bar.close
        n += 1
    flush()
    if len(daily) != len({x.utc_day for x in daily}):
        raise ValueError("TSMOM_DUPLICATED_DAILY_SOURCE")
    return daily, {
        "native_M5_rows_read_pre_embargo": original_bars,
        "eligible_source_UTC_weekdays": len(daily),
        "dropped_sparse_UTC_days": dropped,
        "ignored_weekend_UTC_days": weekends,
    }


def _sign(value: float) -> int:
    return int(value > 0) - int(value < 0)


def directions_before_entry(days: list[Day], i: int) -> tuple[int, int]:
    """Neither signal nor control may inspect the current/entry day."""
    if i < WARMUP or i >= len(days):
        raise ValueError("TSMOM_WARMUP_OR_EVENT_INDEX_INVALID")
    return (
        _sign(days[i - 1].close - days[i - LOOKBACK - 1].close),
        _sign(days[i - 1].close - days[i - 6].close),
    )


def replay_days(symbol: str, days: list[Day]) -> dict:
    if symbol not in MARKETS or any(a.utc_day >= b.utc_day for a, b in zip(days, days[1:])):
        raise ValueError("TSMOM_SYMBOL_OR_DAILY_ORDER_INVALID")
    events: list[dict] = []
    dropped: dict[str, int] = {}
    attempted_weeks: set[str] = set()
    exit_day: date | None = None
    eligible_weeks: set[str] = set()
    for i, current in enumerate(days):
        if i < WARMUP:
            continue
        iso = current.utc_day.isocalendar()
        wk = f"{iso.year}-W{iso.week:02d}"
        eligible_weeks.add(wk)
        if wk in attempted_weeks or (exit_day is not None and current.utc_day <= exit_day):
            continue
        # One first available *non-overlapping* source weekday per ISO week.
        attempted_weeks.add(wk)
        primary, control = directions_before_entry(days, i)
        if primary == 0 or control == 0:
            key = "ZERO_PRIOR_MOMENTUM_OR_BASELINE_CENSORED"
            dropped[key] = dropped.get(key, 0) + 1
            continue
        if i + HOLD_SESSIONS > len(days):
            key = "INSUFFICIENT_FIVE_FUTURE_SESSIONS_CENSORED"
            dropped[key] = dropped.get(key, 0) + 1
            continue
        final = days[i + HOLD_SESSIONS - 1]
        if (current.utc_day < DEV_END <= final.utc_day or final.utc_day >= EMBARGO):
            key = "ERA_BOUNDARY_OR_EMBARGO_CENSORED"
            dropped[key] = dropped.get(key, 0) + 1
            continue
        price_in = current.open
        price_out = final.close
        if price_in <= 0 or price_out <= 0:
            raise ValueError("TSMOM_PRICE_INVALID")
        basis = 10000.0 * (price_out / price_in - 1.0)
        strategy = primary * basis
        benchmark = control * basis
        era = "DEVELOPMENT" if current.utc_day < DEV_END else "DIAGNOSTIC"
        events.append({
            "symbol": symbol, "era": era, "iso_week": wk,
            "signal_decision_at_utc": current.utc_day.isoformat() + "T00:00:00+00:00",
            "entry_first_native_M5_open_on_utc_day": current.utc_day.isoformat(),
            "exit_last_native_M5_close_on_utc_day": final.utc_day.isoformat(),
            "entry_day_native_bar_count": current.native_m5_bars,
            "exit_day_native_bar_count": final.native_m5_bars,
            "direction_252_prior_sessions": primary,
            "control_direction_5_prior_sessions": control,
            "opposed_control": primary != control,
            "strategy_gross_reference_bps": strategy,
            "control_gross_reference_bps": benchmark,
            "paired_delta_gross_reference_bps": strategy - benchmark,
            "source_provider_BID_ASK_asof": False,
            "NET_economic_execution_not_measured": True,
        })
        exit_day = final.utc_day
    if len({event["iso_week"] for event in events}) != len(events):
        raise ValueError("TSMOM_WEEKLY_DUPLICATE_SIGNAL")
    return {
        "symbol": symbol,
        "original_events": len(events),
        "not_entered_week_counts": dropped,
        "weeks_after_warmup_with_eligible_days": len(eligible_weeks),
        "events": events,
    }


def replay_original(
    symbol: str, native: Path, signed33: Path, aggregate12: Path | None = None,
) -> dict:
    if symbol not in MARKETS:
        raise ValueError("TSMOM_SYMBOL_NOT_CANONICAL33")
    source = source33_manifest(signed33)
    original_proof = verify_source(symbol, native, source, aggregate12)
    days, census = daily_from_native(source_rows_before_embargo(native, symbol))
    research = replay_days(symbol, days)
    return {
        "identity": IDENTITY,
        "original_33_source_sha256": SOURCE33_SHA,
        "original_proof": original_proof,
        "native_full_RAW_QUALITY_11year_SHA_verified_before_prices": True,
        "original_M5_embargo_start": EMBARGO.isoformat(),
        "after_embargo_OHLC_unread": True,
        "cohort_contract_homologation_not_proven": True,
        "all_daily_sessions_are_UTC_approximation_not_broker_calendar": True,
        "entry_exit_are_native_M5_OHLC_refs_not_broker_BIDASK": True,
        "original_source_census": census,
        **research,
        "NET_computed": False, "UTC001_certified": False,
        "orders": 0, "production_modified": False,
        "historical_panel_previously_exposed_not_virgin_OOS": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbol", choices=MARKETS)
    p.add_argument("native", type=Path)
    p.add_argument("signed33", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--aggregate12", type=Path)
    args = p.parse_args()
    result = replay_original(args.symbol, args.native, args.signed33, args.aggregate12)
    args.output.mkdir(parents=True, exist_ok=True)
    name = f"alpha2-tsmom-daily-weekly-{args.symbol}.json"
    path = args.output / name
    path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / (name + ".sha256")).write_text(
        sha256_file(path) + "  " + name + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "symbol": args.symbol,
        "events": result["original_events"],
        "source_M5_verified": result["native_full_RAW_QUALITY_11year_SHA_verified_before_prices"],
        "embargo_kept": result["after_embargo_OHLC_unread"],
        "NET": "BLOCKED", "orders": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
