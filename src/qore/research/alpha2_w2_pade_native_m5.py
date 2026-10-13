"""W2 PADE research-only one-rule native M5 replay on SHA-gated 33 markets.

One symbol per parallel Trader Lab worker. Price/activity signals are causal
and out-of-sample claims are NOT made. NO broker costs, NET, live or production.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

from qore.research.alpha2_g1a_native_m5_gross import arm
from qore.research.alpha2_intermarket import M5, MARKETS, Bar, _check_bar, sha256_file
from qore.research.alpha2_lab_h4_extract import (
    source33_manifest,
    verify_source,
)
from qore.research.alpha2_w2_volume_full33 import CUTOFF

H1 = timedelta(hours=1)
HISTORY_DAYS = 35
SAME_SLOT_HOURS = 10
STOP_HOURS = 20
ACTIVITY_MULTIPLE = 1.65
BODY_FRACTION_MAX = 0.20
IMBALANCE_MIN = 0.30
ENTRY_DELAY = M5
HOLD = timedelta(hours=4)
DEVELOPMENT_END = datetime(2022, 9, 17, tzinfo=UTC)
SOURCE_ONLY_ID = "QORE_ALPHA2_W2_PADE_FIRST_GROSS_NATIVE_M5_V01"
ORIGINAL33_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"


@dataclass(frozen=True, slots=True)
class NativeM5:
    bar: Bar
    volume: int


@dataclass(frozen=True, slots=True)
class H1Hour:
    start: datetime
    open: float
    high: float
    low: float
    close: float
    volume_sum: int
    weighted_signed_imbalance: float

    @property
    def range_price(self) -> float:
        return self.high - self.low


def complete_hours(rows: dict[datetime, NativeM5]) -> dict[datetime, H1Hour]:
    grouped: dict[datetime, list[NativeM5]] = defaultdict(list)
    for instant, item in rows.items():
        start = instant.replace(minute=0, second=0, microsecond=0)
        grouped[start].append(item)
    result = {}
    for h, chunk in grouped.items():
        chunk.sort(key=lambda r: r.bar.at)
        if len(chunk) != 12 or any(
            b.bar.at != h + k * M5 for k, b in enumerate(chunk)
        ):
            continue
        activity = sum(r.volume for r in chunk)
        if activity <= 0:
            continue
        directional = sum(
            r.volume * ((r.bar.close > r.bar.open) - (r.bar.close < r.bar.open))
            for r in chunk
        )
        result[h] = H1Hour(
            start=h, open=chunk[0].bar.open,
            high=max(r.bar.high for r in chunk),
            low=min(r.bar.low for r in chunk),
            close=chunk[-1].bar.close, volume_sum=activity,
            weighted_signed_imbalance=directional / activity,
        )
    return result


def propose(
    current: H1Hour,
    known_prior: dict[datetime, H1Hour],
) -> tuple[dict[str, Any] | None, str]:
    """Only H1 closed at/before decision and previous-day slot activity."""
    h = current.start
    if h.weekday() > 4 or not 8 <= h.hour <= 15:
        return None, "OUTSIDE_FROZEN_UTC_WINDOW"
    historic_activities = [
        known_prior[when].volume_sum
        for days in range(1, HISTORY_DAYS + 1)
        if (when := h - timedelta(days=days)) in known_prior
    ][:SAME_SLOT_HOURS]
    if len(historic_activities) != SAME_SLOT_HOURS:
        return None, "MISSING_TEN_SAME_UTC_HOUR_HISTORY_DAYS"
    previous_hours = [
        known_prior.get(h - n * H1)
        for n in range(1, STOP_HOURS + 1)
    ]
    if any(x is None for x in previous_hours):
        return None, "MISSING_TWENTY_PRIOR_CONTIGUOUS_HOURS"
    median_activity = float(median(historic_activities))
    if median_activity <= 0:
        return None, "INVALID_PAST_ACTIVITY_MEDIAN"
    if current.volume_sum / median_activity < ACTIVITY_MULTIPLE:
        return None, "ACTIVITY_SHOCK_NOT_ABNORMAL"
    if current.range_price <= 0:
        return None, "DEGENERATE_CURRENT_H1_RANGE"
    if abs(current.close - current.open) / current.range_price > BODY_FRACTION_MAX:
        return None, "H1_DISPLACEMENT_NOT_ABSORBED"
    imb = current.weighted_signed_imbalance
    if abs(imb) < IMBALANCE_MIN:
        return None, "NO_SIGNED_ACTIVITY_IMBALANCE"
    # Baseline strictly BEFORE current H1. Cannot be mechanically equal to imbalance.
    old3 = known_prior[h - 3 * H1]
    old1 = known_prior[h - H1]
    ctrl_change = old1.close - old3.close
    if ctrl_change == 0:
        return None, "BASELINE_ZERO_DIRECTION"
    d = float(median(x.range_price for x in previous_hours if x is not None))
    if not math.isfinite(d) or d <= 0:
        return None, "INVALID_H1_PAST_STOP"
    return {
        "direction": 1 if imb > 0 else -1,
        "control_direction": 1 if ctrl_change > 0 else -1,
        "decision_utc": (h + H1).isoformat(),
        "entry_utc": (h + H1 + ENTRY_DELAY).isoformat(),
        "exit_deadline_utc": (h + H1 + ENTRY_DELAY + HOLD).isoformat(),
        "activity_ratio": float(current.volume_sum / median_activity),
        "displacement_fraction": float(abs(current.close-current.open) /
                                       current.range_price),
        "activity_signed_imbalance": float(imb),
        "stop_distance_price": d,
        "comparator_is_pre_event_prior_2h": True,
    }, "EVENT"


def read_original_market_rows(
    symbol: str, source: Path,
) -> Any:
    """Read ONLY pre-embargo M5; original source SHA must already be checked."""
    from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as newsrc
    from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as oldsrc

    is_original = symbol in oldsrc.SYMBOLS
    schema = oldsrc.RAW_SCHEMA if is_original else newsrc.NEW_RAW_SCHEMA
    identity = oldsrc.PRODUCER if is_original else newsrc.NEW_CAPTURE_IDENTITY
    provider = oldsrc.SOURCE_SYMBOL_MAP.get(symbol, symbol)
    previous = None
    for year in range(2016, 2025):
        with (source / "RAW_M5_LEDGER" / f"{year}.jsonl").open(encoding="utf-8") as file:
            for line in file:
                item = json.loads(line)
                instant = datetime.fromisoformat(item["opened_at"])
                if instant.tzinfo is None or instant.utcoffset() is None:
                    raise ValueError("original M5 timestamp not UTC-aware")
                instant = instant.astimezone(UTC)
                if instant >= CUTOFF:
                    continue  # no OHLC/volume read from reserved future
                if (previous is not None and instant <= previous
                        or instant.second or instant.microsecond
                        or instant.minute % 5):
                    raise ValueError("original provider M5 time corrupted")
                previous = instant
                if (item.get("schema") != schema or item.get("identity") != identity
                        or item.get("canonical_symbol") != symbol
                        or item.get("provider_symbol") != provider):
                    raise ValueError("original provider M5 identity mismatch")
                volume = item.get("volume")
                if type(volume) is not int or volume <= 0:
                    raise ValueError("native volume source census contradicted")
                keys = ("open_relative", "high_relative", "low_relative", "close_relative")
                if any(type(item.get(k)) is not int for k in keys):
                    raise ValueError("M5 integer native relative OHLC required")
                bar = Bar(instant, float(item[keys[0]]), float(item[keys[1]]),
                          float(item[keys[2]]), float(item[keys[3]]))
                _check_bar(bar)
                yield NativeM5(bar, volume)


def research_one_day(
    symbol: str, day: date,
    today: dict[datetime, NativeM5],
    historical: dict[datetime, H1Hour],
) -> tuple[list[dict[str, Any]], Counter[str], dict[datetime, H1Hour]]:
    """Current H1 decisions depend only on their closed/current and prior hours."""
    hours = complete_hours(today)
    reasons: Counter[str] = Counter()
    if day.weekday() > 4:
        return [], reasons, hours
    if not datetime(2016, 9, 17, tzinfo=UTC).date() <= day < CUTOFF.date():
        return [], reasons, hours
    known = dict(historical)
    opportunities: list[dict[str, Any]] = []
    # Build all today's H1 data, but only reveal hours to the signal one by one.
    for h, cur in sorted(hours.items()):
        if h.hour in range(8,16):
            plan, reason = propose(cur, known)
            reasons[reason] += 1
            if plan:
                opportunities.append(plan)
                # Rule is FIRST qualifying event per UTC day; never choose best outcome.
                break
        known[h] = cur
    if opportunities:
        plan = opportunities[0]
        t = datetime.fromisoformat(plan["entry_utc"])
        expire = datetime.fromisoformat(plan["exit_deadline_utc"])
        # The original native M5 daily map may have gaps. Incomplete future
        # trajectory is censored, never filled or omitted from denominator.
        m5 = {x: obj.bar for x,obj in today.items()}
        if expire > CUTOFF:
            strategy = control = {"status": "EMBARGO_CROSS_CENSORED"}
        elif (t < DEVELOPMENT_END <= expire):
            strategy = control = {"status": "ERA_BOUNDARY_CENSORED"}
        else:
            strategy = arm(m5=m5, entry_at=t, expire_at=expire,
                           distance=plan["stop_distance_price"],
                           direction=plan["direction"])
            control = arm(m5=m5, entry_at=t, expire_at=expire,
                          distance=plan["stop_distance_price"],
                          direction=plan["control_direction"])
        paired = strategy["status"] == control["status"] == "COMPLETE_GROSS_PROXY"
        decision = datetime.fromisoformat(plan["decision_utc"])
        wk = decision.isocalendar()
        opportunities = [{
            "symbol": symbol, "utc_day": day.isoformat(),
            "iso_week": f"{wk.year}-W{wk.week:02d}",
            "era": "DEVELOPMENT" if decision < DEVELOPMENT_END else "DIAGNOSTIC",
            "plan": plan, "strategy": strategy, "control": control,
            "paired": paired,
            "delta_gross_bps": (
                strategy["gross_bps"] - control["gross_bps"] if paired else None
            ), "delta_gross_R": (
                strategy["gross_R"] - control["gross_R"] if paired else None
            ), "bidask_net_not_measured": True,
        }]
    return opportunities, reasons, hours


def replay(
    symbol: str,
    native: Path,
    signed33: Path,
    aggregate12: Path | None = None,
) -> dict[str, Any]:
    if symbol not in MARKETS:
        raise ValueError("exact frozen G0 33 roster required")
    frozen = source33_manifest(signed33)
    proof = verify_source(symbol, native, frozen, aggregate12)
    observed: dict[datetime, NativeM5] = {}
    hist: dict[datetime, H1Hour] = {}
    original_signals: list[dict[str, Any]] = []
    reason_tally: Counter[str] = Counter()
    previous_day: date | None = None
    days_observed = 0
    for item in read_original_market_rows(symbol, native):
        day = item.bar.at.date()
        if previous_day is not None and day != previous_day:
            events, reasons, hours = research_one_day(symbol, previous_day, observed, hist)
            original_signals.extend(events)
            reason_tally.update(reasons)
            hist.update(hours)
            expire_before = datetime(previous_day.year, previous_day.month,
                                     previous_day.day, tzinfo=UTC) - timedelta(
                                         days=HISTORY_DAYS + 2)
            hist = {k: v for k,v in hist.items() if k >= expire_before}
            observed = {}
            days_observed += 1
        observed[item.bar.at] = item
        previous_day = day
    if previous_day is not None:
        events, reasons, _ = research_one_day(symbol, previous_day, observed, hist)
        original_signals.extend(events)
        reason_tally.update(reasons)
        days_observed += 1
    if len({x["utc_day"] for x in original_signals}) != len(original_signals):
        raise ValueError("more than one opportunity per UTC day")
    return {
        "identity": SOURCE_ONLY_ID, "symbol": symbol,
        "source_33_manifest_sha256": ORIGINAL33_SHA,
        "source_proof": proof,
        "full_native_source_SHA_verified_before_OHLC": True,
        "days_with_any_source_rows": days_observed,
        "original_signal_count": len(original_signals),
        "paired_observed": sum(e["paired"] for e in original_signals),
        "opportunities": original_signals,
        "predeclared_rule_exclusion_counts": dict(sorted(reason_tally.items())),
        "comparison": "PADE_VS_PRE_EVENT_LAG_2H_NONTAUTOLOGICAL",
        "broker_volume_semantics": "UNVERIFIED_REPORTED_ACTIVITY_PROXY",
        "broker_costs_verified": False,
        "news_known_asof_verified": False,
        "ohlc_broker_fill_executable": False,
        "UTC001_certified": False, "production_untouched": True,
        "after_2024_09_17_price_unread": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbol", choices=MARKETS)
    p.add_argument("original_provider", type=Path)
    p.add_argument("source33", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--aggregate12", type=Path)
    args = p.parse_args()
    result = replay(args.symbol, args.original_provider, args.source33,
                    args.aggregate12)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"alpha2-w2-pade-gross-{args.symbol}.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    path.with_name(path.name+".sha256").write_text(
        sha256_file(path) + "  " + path.name + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": SOURCE_ONLY_ID, "symbol": args.symbol,
                      "signals": result["original_signal_count"],
                      "paired": result["paired_observed"], "NET": "NOT_COMPUTED"},
                     sort_keys=True))


if __name__ == "__main__":
    main()
