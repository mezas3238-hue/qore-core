"""E1 native 33x7 all-method gross OHLC, strictly causal and news-unfiltered.

The frozen prereg controls every clock/sign/benchmark: no optimization, no
broker BID/ASK, no fills, no signals to VPS/MT5/Shared/CIBO/production.
Only original SHA-audited M5 on UTC timestamps BEFORE 2024-09-17 is read.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import qore_native_gross04_panel33_sweep_reclaim_v1 as source_g0
from qore.infrastructure.trader_lab import qore_native_33x7_method_market_registry_v1 as register
from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0

IDENTITY = "QORE_NATIVE_33X7_E1_FROZEN_GROSS_ONLY_V1"
PREREG_SHA = "67022daf7e2c3335eda991fd217df83fc1a34bc4"
SOURCE_33_SHA = register.SOURCE_SHA
START_UTC = datetime(2016, 9, 17, tzinfo=UTC)
DEV_CUTOFF = datetime(2022, 9, 17, tzinfo=UTC)
EMBARGO = datetime(2024, 9, 17, tzinfo=UTC)
END_SOURCE_YEAR = 2024
ROUNDTRIP_ASSUMPTIONS = (0, 1, 3, 5, 10, 20)
Bar = tuple[int, int, int, int]  # open, close, high, low; cTrader-relative
BarMap = dict[date, dict[int, Bar]]
METHODS = tuple(m for m, _ in register.METHODOLOGIES)
MAX_TIME_SLOT = 20 * 60

def sign(x: int) -> int:
    return (x > 0) - (x < 0)

def read_original_preembargo(path: Path, symbol: str) -> tuple[BarMap, dict[str, int]]:
    """A single chronological pass; 2024-09-17+ OHLC keys are never accessed."""
    original = symbol in source_g0.new_source.EXISTING
    expected_identity = g0.PRODUCER if original else source_g0.new_source.NEW_CAPTURE_IDENTITY
    expected_schema = g0.RAW_SCHEMA if original else source_g0.new_source.NEW_RAW_SCHEMA
    calendars: BarMap = {}
    stats = {"native_timestamp_rows_before_embargo": 0, "stored_session_bars": 0}
    previous: datetime | None = None
    for year in range(2016, END_SOURCE_YEAR + 1):
        file = path / "RAW_M5_LEDGER" / f"{year}.jsonl"
        with file.open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                at = datetime.fromisoformat(row["opened_at"])
                if at.tzinfo is None or at.utcoffset() is None:
                    raise ValueError("M5 naive timestamp is disallowed")
                at = at.astimezone(UTC)
                if at >= EMBARGO or at < START_UTC:
                    continue
                if ((previous is not None and at <= previous) or at.second
                        or at.microsecond or at.minute % 5):
                    raise ValueError("source chronological UTC M5 integrity broken")
                previous = at
                stats["native_timestamp_rows_before_embargo"] += 1
                if at.weekday() > 4 or at.hour < 4 or at.hour * 60 + at.minute >= MAX_TIME_SLOT:
                    continue
                if (
                    row.get("identity") != expected_identity
                    or row.get("schema") != expected_schema
                    or row.get("canonical_symbol") != symbol
                    or (not original and row.get("provider_symbol") != symbol)
                    or any(type(row.get(k)) is not int for k in (
                        "open_relative", "close_relative", "high_relative", "low_relative"
                    ))
                ):
                    raise ValueError("source broker, schema or original integer price mismatch")
                o, c, hi, lo = (
                    row["open_relative"], row["close_relative"],
                    row["high_relative"], row["low_relative"]
                )
                if lo <= 0 or lo > min(o, c) or hi < max(o, c):
                    raise ValueError("provider-relative OHLC invalid")
                d = calendars.setdefault(at.date(), {})
                minute = at.hour * 60 + at.minute
                if minute in d:
                    raise ValueError("duplicate UTC minute within day")
                d[minute] = (o, c, hi, lo)
                stats["stored_session_bars"] += 1
    return calendars, stats


def exact_bars(cal: BarMap, opened: datetime, n: int) -> list[Bar] | None:
    """n causal exact-contiguous M5s; no imputation; ends open+(n*5) exclusive."""
    if opened.tzinfo is None or opened.utcoffset() is None or n < 1:
        raise ValueError("M5 exact block must have aware UTC clock and positive count")
    start = opened.astimezone(UTC)
    vals: list[Bar] = []
    for index in range(n):
        at = start + timedelta(minutes=index * 5)
        slot = cal.get(at.date(), {}).get(at.hour * 60 + at.minute)
        if slot is None:
            return None
        vals.append(slot)
    return vals


def roll(bars: list[Bar]) -> tuple[int, int, int, int]:
    return bars[0][0], bars[-1][1], max(x[2] for x in bars), min(x[3] for x in bars)


def matched_event(method: str, day: date, signal: int, baseline: int,
                  target: list[Bar], decision_utc: datetime) -> dict[str, Any] | None:
    """Both signs fixed at or before target first open; no future in signal."""
    if not signal or not baseline:
        return None
    if target[0][0] <= 0 or decision_utc >= EMBARGO:
        raise ValueError("invalid target or attempted post-embargo outcome")
    gross_return = 10000 * (target[-1][1] - target[0][0]) / target[0][0]
    week = day.isocalendar()
    return {
        "utc_date": day.isoformat(),
        "iso_week": f"{week.year}-W{week.week:02d}",
        "method_id": method,
        "strategy_signal": signal,
        "baseline_signal": baseline,
        "reference_entry_utc": decision_utc.isoformat(),
        "strategy_gross_bps": signal * gross_return,
        "baseline_gross_bps": baseline * gross_return,
        "paired_delta_bps": (signal - baseline) * gross_return,
        "broker_executable_fill": False,
        "macro_news_asof_filtered": False,
    }


def synthetic_events_for_day(method: str, day: date, cal: BarMap,
                             history_days: list[date]) -> tuple[dict[str, Any] | None, str]:
    d = datetime(day.year, day.month, day.day, tzinfo=UTC)
    if method in ("REVERSAL_12H", "PERSISTENCE_12H", "TREND_MULTI_DAY"):
        recent = exact_bars(cal, d + timedelta(hours=12), 48)
        target = exact_bars(cal, d + timedelta(hours=16), 48)
        if recent is None or target is None:
            return None, "MISSING_CAUSAL_M5"
        if method == "TREND_MULTI_DAY":
            last = [p for p in history_days if p < day and (day - p).days <= 7]
            prior: list[tuple[date, list[Bar]]] = []
            for p in reversed(last):
                x = exact_bars(cal, datetime(p.year,p.month,p.day,16,tzinfo=UTC), 48)
                if x is not None:
                    prior.append((p, x))
                if len(prior) == 3:
                    break
            if len(prior) != 3:
                return None, "NO_THREE_PAST_FULL_SESSIONS_WITHIN_7D"
            # Sort oldest->newest; 3 full sessions end BEFORE today's decision.
            prior.sort(key=lambda t: t[0])
            trend_change = prior[-1][1][-1][1] - prior[0][1][0][0]
            signal = sign(trend_change)
        else:
            lookback = exact_bars(cal, d + timedelta(hours=4), 144)
            if lookback is None:
                return None, "MISSING_CAUSAL_M5"
            observed_change = lookback[-1][1] - lookback[0][0]
            signal = -sign(observed_change) if method == "REVERSAL_12H" else sign(observed_change)
        short = recent[-1][1] - recent[0][0]
        baseline = -sign(short) if method == "REVERSAL_12H" else sign(short)
        ret = matched_event(method, day, signal, baseline, target, d + timedelta(hours=16))
        return (ret, "EVENT") if ret is not None else (None, "ZERO_DIRECTION")
    if method in ("RANGE_BREAK_CONT", "SWEEP_RECLAIM"):
        prev = exact_bars(cal, d + timedelta(hours=8), 48)
        probe = exact_bars(cal, d + timedelta(hours=12), 12)
        target = exact_bars(cal, d + timedelta(hours=13), 24)
        if prev is None or probe is None or target is None:
            return None, "MISSING_CAUSAL_M5"
        preo, prec, prehi, prelo = roll(prev)
        po, pc, phi, plo = roll(probe)
        if method == "SWEEP_RECLAIM":
            up, down = phi > prehi, plo < prelo
            if up == down:
                return None, "DOUBLE_OR_NO_SWEEP"
            if not prelo <= pc <= prehi:
                return None, "NO_RECLAIM"
            direction = -1 if up else 1
            baseline = -sign(pc - po)
        else:
            direction = 1 if pc > prehi else -1 if pc < prelo else 0
            baseline = sign(prec - preo)
            if direction == 0:
                return None, "NO_CONFIRMED_BREAKOUT"
        ret = matched_event(method, day, direction, baseline, target, d + timedelta(hours=13))
        return (ret, "EVENT") if ret is not None else (None, "ZERO_DIRECTION")
    raise ValueError("method is not a UTC-based family")


def session_events_for_day(method: str, symbol: str, day: date,
                           cal: BarMap) -> tuple[dict[str, Any] | None, str]:
    if method not in ("POST_OPEN_CONT", "OPEN_INITIAL_REACTION"):
        raise ValueError("non-session rule passed to session clock")
    ref = register.session_reference(symbol, method)
    hour, minute = (int(n) for n in ref["local_reference"].split(":"))
    zoned = datetime(day.year, day.month, day.day, hour, minute,
                     tzinfo=ZoneInfo(ref["tz"]))
    reference = zoned.astimezone(UTC)
    if reference.date() != day or zoned.weekday() > 4:
        return None, "INVALID_SESSION_LOCAL_UTC_DAY"
    if method == "OPEN_INITIAL_REACTION":
        before = exact_bars(cal, reference - timedelta(minutes=15), 3)
        first = exact_bars(cal, reference, 3)
        target = exact_bars(cal, reference + timedelta(minutes=15), 3)
    else:
        before = exact_bars(cal, reference - timedelta(minutes=30), 6)
        first = exact_bars(cal, reference, 6)
        target = exact_bars(cal, reference + timedelta(minutes=30), 24)
    if before is None or first is None or target is None:
        return None, "MISSING_CAUSAL_SESSION_M5"
    direction = sign(first[-1][1] - first[0][0])
    control = sign(before[-1][1] - before[0][0])
    enter = reference + timedelta(minutes=15 if method == "OPEN_INITIAL_REACTION" else 30)
    ret = matched_event(method, day, direction, control, target, enter)
    return (ret, "EVENT") if ret is not None else (None, "ZERO_DIRECTION")


def source_witness(methods_symbol: str, source_root: Path,
                   source33_root: Path, aggregate12: Path | None) -> dict[str, Any]:
    if methods_symbol not in source_g0.final33.FROZEN_UNIVERSE_33:
        raise ValueError("symbol outside frozen source33")
    frozen = source_g0.source33_parent_manifest(source33_root)
    original_row = next(r for r in frozen["market_roster"] if r["symbol"] == methods_symbol)
    audited = source_g0.verify_original(methods_symbol, source_root, aggregate12)
    if audited["native_m5_original_bars"] != original_row["m5_bars"]:
        raise ValueError("original signed 33 bars source mismatch")
    # Verify new21 original manifest SHA matches roster too.
    if methods_symbol not in source_g0.new_source.EXISTING:
        expect = original_row.get("manifest_sha256", original_row.get("source_manifest_sha256"))
        if expect != audited["source_manifest_sha256"]:
            raise ValueError("new21 source manifest not frozen parent SHA")
    cal, stats = read_original_preembargo(source_root, methods_symbol)
    days = sorted(cal)
    results = []
    for method in METHODS:
        events: list[dict[str, Any]] = []
        exclusions: Counter[str] = Counter()
        for day in days:
            if method in register.SESSION_DEPENDENT:
                event, reason = session_events_for_day(method, methods_symbol, day, cal)
            else:
                event, reason = synthetic_events_for_day(method, day, cal, days)
            exclusions[reason] += 1
            if event is not None:
                events.append(event)
        status = register.cell_prior(method, methods_symbol)
        results.append({
            "cell_id": f"{method}__{methods_symbol}",
            "method_id": method, "source_symbol": methods_symbol,
            "evidence_status": status["status"], "prior_pr": status["prior_pr"],
            "prior_result": status["prior_result"],
            "source_span_utc": "[2016-09-17,2024-09-17) PAST ONLY",
            "zero_return_events_retained": True,
            "exclusion_reason_counts": dict(sorted(exclusions.items())),
            "paired_events": events,
            "news_asof_filtered": False,
            "bidask_measured": False,
            "net_economics_authorized": False,
        })
    if len(results) != 7 or sum(len(x["paired_events"]) for x in results) < 0:
        raise ValueError("seven rules not all run")
    return {
        "identity": IDENTITY, "status": "E1_SEVEN_METHOD_GROSS_ONLY_PREVIOUSLY_EXPOSED_PERIODS",
        "frozen_prereg_commit": PREREG_SHA, "source33_sha": SOURCE_33_SHA,
        "original_symbol": methods_symbol,
        "source_audit": audited,
        "clock_spec": "UTC and per-family America/New_York/Europe/London ZoneInfo",
        "source_timestamp_census": stats,
        "past_dev_only_till": DEV_CUTOFF.isoformat(),
        "past_diagnostic_only_till": EMBARGO.isoformat(),
        "future_ohlc_not_read": True, "net_certified": False,
        "traders_certified": 0, "production_untouched": True,
        "seven_methods": results,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbol", choices=sorted(source_g0.final33.FROZEN_UNIVERSE_33))
    p.add_argument("original_source", type=Path)
    p.add_argument("frozen33", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--original12-aggregate", type=Path)
    args = p.parse_args()
    data = source_witness(args.symbol, args.original_source, args.frozen33,
                          args.original12_aggregate)
    args.out.mkdir(parents=True, exist_ok=True)
    file = args.out / f"qore-native-e1-seven-{args.symbol}.json"
    file.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    file.with_name(file.name + ".sha256").write_text(
        g0.sha256(file) + f"  {file.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "symbol": args.symbol,
        "methods": len(data["seven_methods"]),
        "events_by_method": {x["method_id"]:len(x["paired_events"]) for x in data["seven_methods"]},
        "net_certified": False,
        "future_price_embargo_respected": True,
        "provenance": data["source_audit"]["source_cohort"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
