"""Pre-registered ONE US index turn-of-month paired economic GROSS exam.

Pure original CIBO DEMO M5 source: SP500 PRIMARY, NAS100/US30 diagnostic replicates.
No bar OHLC read >= 2024-09-17; no bid/ask, fills, NET PnL or authorization.
Science prereg first committed 358d2d0e9691a95bbd9c121ea62b0075c2182975.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as source

PREREG_SHA = "358d2d0e9691a95bbd9c121ea62b0075c2182975"
PREREG_DOC = (
    "docs/research/"
    "QORE_NATIVE_US_INDEX_TOM_H1_SINGLE_ECONOMIC_GROSS_PREREG_2026-10-13.md"
)
SYMBOLS = ("SP500", "US30", "NAS100")
EMBARGO = date(2024, 9, 17)
DEV_BEGIN, DEV_END = (2016, 11), (2022, 8)
DIAG_BEGIN, DIAG_END = (2022, 10), (2024, 8)
NY = ZoneInfo("America/New_York")
CASH_LAST_BAR = (15, 55)
CASH_START_MIN = 9 * 60 + 30
CASH_LAST_MIN = 15 * 60 + 55
CASH_MIN_BARS = 60
BSTRAP_DRAWS = 4000
BSTRAP_BLOCK_MONTHS = 3
BSTRAP_SEED = 20261013
MIN_DEV = 40
MIN_DIAG = 16
PRIMARY_TOM_BPS_MIN = 15
PRIMARY_PAIRED_BPS_MIN = 15
REPLICATION_PAIRED_BPS_MIN = 5
STRESS_RT_BPS = (5, 10, 20)


@dataclass(frozen=True)
class CashFix:
    day: date
    at_utc: datetime
    reference_open: int
    observed_rth_m5: int


@dataclass(frozen=True)
class PairedMonth:
    yyyy_mm: str
    tom_bps: float
    control_bps: float
    excess_bps: float


def _qualifying_dates(
    count_by_day: dict[date, int],
    open_by_day: dict[date, tuple[datetime, int]],
) -> dict[date, CashFix]:
    return {
        day: CashFix(day, at, op, count_by_day[day])
        for day, (at, op) in sorted(open_by_day.items())
        if count_by_day.get(day, 0) >= CASH_MIN_BARS
        and day.weekday() < 5 and op > 0
    }


def collect_cash_fixes(root: Path, symbol: str) -> tuple[dict[date, CashFix], dict[str, int]]:
    """Only read M5 bars <= last NY cash session pre-embargo; no future OHLC."""
    if symbol not in SYMBOLS:
        raise ValueError("UNREGISTERED_MARKET")
    counts: dict[date, int] = defaultdict(int)
    fixes: dict[date, tuple[datetime, int]] = {}
    last_at: datetime | None = None
    counters = {
        "source_rows_pre_embargo": 0, "rth_m5_rows": 0,
        "bar_1555_reference_count": 0, "post_embargo_rows_skipped_without_ohlc": 0,
    }
    for year in range(2016, 2025):
        path = root / "RAW_M5_LEDGER" / f"{year}.jsonl"
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                row: dict[str, Any] = json.loads(line)
                at = datetime.fromisoformat(row["opened_at"])
                if at.tzinfo is None or at.utcoffset() is None:
                    raise ValueError("M5_DATE_WITHOUT_UTC_ZONE")
                utc = at.astimezone(UTC)
                if utc.date() >= EMBARGO:
                    counters["post_embargo_rows_skipped_without_ohlc"] += 1
                    continue  # NEVER touch row relative OHLC fields, even in memory.
                if (utc < source.FIRST or (last_at is not None and utc <= last_at)
                        or utc.second != 0 or utc.microsecond != 0
                        or utc.minute % 5 != 0):
                    raise ValueError("SOURCE_M5_TIME_NOT_CANONICAL")
                last_at = utc
                counters["source_rows_pre_embargo"] += 1
                ny = utc.astimezone(NY)
                minute = ny.hour * 60 + ny.minute
                if (ny.weekday() >= 5 or not CASH_START_MIN <= minute <= CASH_LAST_MIN):
                    continue
                if (row.get("schema") != source.RAW_SCHEMA
                        or row.get("identity") != source.PRODUCER
                        or row.get("canonical_symbol") != symbol
                        or row.get("provider_symbol") != source.SOURCE_SYMBOL_MAP[symbol]):
                    raise ValueError("FROZEN_G0_PROVIDER_IDENTITY_DRIFT")
                counts[ny.date()] += 1
                counters["rth_m5_rows"] += 1
                if minute == CASH_LAST_MIN:
                    if ny.date() in fixes:
                        raise ValueError("DUPLICATE_NY_CASH_FINAL_BAR")
                    op = row["open_relative"]
                    cl = row["close_relative"]
                    high = row["high_relative"]
                    low = row["low_relative"]
                    if (any(type(x) is not int for x in (op, cl, high, low))
                            or low <= 0 or low > min(op, cl)
                            or high < max(op, cl)):
                        raise ValueError("INVALID_REFERENTIAL_M5_OHLC")
                    fixes[ny.date()] = (utc, op)
                    counters["bar_1555_reference_count"] += 1
    return _qualifying_dates(counts, fixes), counters


def _month_key(d: date) -> tuple[int, int]:
    return d.year, d.month


def _prev_month(key: tuple[int, int]) -> tuple[int, int]:
    year, month = key
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _period(key: tuple[int, int]) -> str | None:
    if DEV_BEGIN <= key <= DEV_END:
        return "dev"
    if DIAG_BEGIN <= key <= DIAG_END:
        return "diag"
    return None


def paired_months(fixes: dict[date, CashFix]) -> tuple[dict[str, list[PairedMonth]], dict[str, int]]:
    by_month: dict[tuple[int, int], list[CashFix]] = defaultdict(list)
    for day, fix in sorted(fixes.items()):
        if day != fix.day or fix.reference_open <= 0:
            raise ValueError("INVALID_REFERENCE_FIXTURE")
        by_month[_month_key(day)].append(fix)
    out: dict[str, list[PairedMonth]] = {"dev": [], "diag": []}
    stats = {"months_assessed": 0, "months_missing_calendar": 0,
             "months_complete": 0, "dev_months": 0, "diag_months": 0}
    for key, current in sorted(by_month.items()):
        period = _period(key)
        if period is None:
            continue
        stats["months_assessed"] += 1
        preceding = by_month.get(_prev_month(key))
        if preceding is None or len(current) < 13:
            stats["months_missing_calendar"] += 1
            continue
        # Ex post reconstructed previous last active session; official calendar
        # first-published-at not yet verified: NOT approval to fill orders.
        end_prev = preceding[-1]
        first3 = current[2]
        mid10, mid13 = current[9], current[12]
        if ((first3.day - end_prev.day).days >= 8
                or (mid13.day - mid10.day).days >= 7
                or not (end_prev.day < first3.day < mid10.day < mid13.day)
                or any(x.reference_open <= 0 for x in (end_prev, first3, mid10, mid13))):
            stats["months_missing_calendar"] += 1
            continue
        tom = 10000 * (first3.reference_open - end_prev.reference_open) / end_prev.reference_open
        control = 10000 * (mid13.reference_open - mid10.reference_open) / mid10.reference_open
        if not math.isfinite(tom + control):
            raise ValueError("NONFINITE_REFERENCE_RETURN")
        out[period].append(PairedMonth(
            f"{key[0]:04d}-{key[1]:02d}", tom, control, tom - control
        ))
        stats["months_complete"] += 1
        stats[period + "_months"] += 1
    return out, stats


def bootstrap_lower_one_sided_95(
    values: list[float], seed: int,
) -> float | None:
    if len(values) < MIN_DIAG:
        return None
    rng = random.Random(seed)
    n = len(values)
    simulated: list[float] = []
    for _ in range(BSTRAP_DRAWS):
        draws: list[float] = []
        while len(draws) < n:
            idx = rng.randrange(n)
            draws.extend(values[(idx + offset) % n] for offset in range(BSTRAP_BLOCK_MONTHS))
        simulated.append(mean(draws[:n]))
    simulated.sort()
    return simulated[int(0.05 * BSTRAP_DRAWS)]


def summarize(
    rows: list[PairedMonth], *, seed: int, primary: bool, period: str,
) -> dict[str, Any]:
    if period not in ("dev", "diag"):
        raise ValueError("INVALID_EXPERIMENT_PERIOD")
    floor = MIN_DEV if period == "dev" else MIN_DIAG
    n = len(rows)
    base: dict[str, Any] = {
        "months": n,
        "minimum_months": floor,
        "adequate_months": n >= floor,
        "strategy_is_broker_executable": False,
        "real_historical_bidask_contract_available": False,
    }
    if n < floor:
        base.update({
            "gross_TOM_mean_bps": None, "gross_midmonth_control_mean_bps": None,
            "paired_excess_mean_bps": None, "bootstrap_lower_excess_bps": None,
            "verdict": "INCONCLUSIVE_COVERAGE",
        })
        return base
    gross = mean(x.tom_bps for x in rows)
    ctrl = mean(x.control_bps for x in rows)
    delta = gross - ctrl
    lower = bootstrap_lower_one_sided_95([x.excess_bps for x in rows], seed=seed)
    assert lower is not None
    if primary:
        passed = (
            gross > PRIMARY_TOM_BPS_MIN
            and delta > PRIMARY_PAIRED_BPS_MIN and lower > 0
        )
    else:
        passed = delta > REPLICATION_PAIRED_BPS_MIN
    base.update({
        "gross_TOM_mean_bps": gross,
        "gross_midmonth_control_mean_bps": ctrl,
        "paired_excess_mean_bps": delta,
        "bootstrap_lower_excess_bps": lower,
        "gross_TOM_positive_month_fraction": (
            sum(x.tom_bps > 0 for x in rows) / n
        ),
        "gross_TOM_after_hypothetical_RT_cost_bps": {
            str(cost): gross - cost for cost in STRESS_RT_BPS
        },
        "verdict": "PRELIMINARY_SUPPORT" if passed else "NO_SUPPORT",
    })
    return base


def run_symbol(
    symbol: str, source_root: Path, aggregate_root: Path
) -> dict[str, Any]:
    if symbol not in SYMBOLS:
        raise ValueError("FROZEN_MARKET_NOT_PERMITTED")
    original = source.aggregate_index(aggregate_root)
    audit = source.audit_symbol(symbol, source_root, original[symbol])
    if (audit["status"] != "G0_M5_SOURCE_INTEGRITY_PASS"
            or audit["all_11_years_raw_and_quality_sha256_verified"] is not True
            or audit["source_symbol"] != symbol):
        raise ValueError("SHA_AUDIT_OF_CTRADER_SOURCE_FAILED")
    fixes, counters = collect_cash_fixes(source_root, symbol)
    months, stats = paired_months(fixes)
    idx = SYMBOLS.index(symbol)
    partitions: dict[str, Any] = {}
    for period_idx, period in enumerate(("dev", "diag")):
        partitions[period] = summarize(
            months[period],
            seed=BSTRAP_SEED + idx * 10 + period_idx,
            primary=symbol == "SP500",
            period=period,
        )
    return {
        "schema": "qore.native.tom.single-index-reference.v1",
        "identity": symbol,
        "provider": source.SOURCE_SYMBOL_MAP[symbol],
        "prereg_sha": PREREG_SHA,
        "source_original_manifest_sha": audit["symbol_manifest_sha256"],
        "source_all_11_years_SHA_verified": True,
        "source_aggregate_SHA": source.AGGREGATE_INDEX_SHA256,
        "source_producer_commit": source.PRODUCER_SHA,
        "prices_post_2024_09_17_read": False,
        "future_holdout_return_inspected": False,
        "calendar_first_published_at_verified": False,
        "data_is_native_futures": False,
        "historical_bidask_net_calculated": False,
        "broker_swaps_and_fees_verified": False,
        "live_authorized": False, "capital_risked": False,
        "source_clocks": counters,
        "paired_months": stats,
        "dev": partitions["dev"],
        "diag": partitions["diag"],
        "baseline": "same-month-10th-to-13th-US-cash-session-1555-NY-open",
        "target": "previous-month-last-to-current-third-US-cash-session-1555-NY-open",
    }


def decide(all_symbols: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if set(all_symbols) != set(SYMBOLS):
        raise ValueError("ALL_THREE_INDICES_REQUIRED_NO_WINNER_SELECTION")
    enough = all(
        item[period]["adequate_months"]
        for item in all_symbols.values()
        for period in ("dev", "diag")
    )
    if not enough:
        verdict = "INCONCLUSIVE_COVERAGE"
        next_action = "CLOSE_WITHOUT_RETUNING"
    elif all(
        item[period]["verdict"] == "PRELIMINARY_SUPPORT"
        for item in all_symbols.values()
        for period in ("dev", "diag")
    ):
        verdict = "PRELIMINARY_GROSS_ASSOCIATION_ONLY_NOT_EXECUTABLE"
        next_action = "NEED_FRESH_OOS_AND_REAL_EXECUTION_COSTS"
    else:
        verdict = "NO_SUPPORT_UNDER_PREREG"
        next_action = "CLOSE_H_TOM_1_NO_PARAMETER_SEARCH"
    return {
        "schema": "qore.native.tom.single-three-index-exam.v1",
        "prereg_sha": PREREG_SHA,
        "markets_primary_and_replicates": list(SYMBOLS),
        "all_original_manifest_SHA_verifications_pass": True,
        "verdict": verdict,
        "next_action": next_action,
        "holdout_2024_09_17_plus_consumed": False,
        "independent_fresh_OOS_completed": False,
        "broker_historical_net_executed": False,
        "edge_certified": False, "traders_certified": 0,
        "cibo_shared_live_deploy": False,
        "capital_real_risked": False,
        "symbols": all_symbols,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="action", required=True)
    unit = sub.add_parser("symbol")
    unit.add_argument("symbol", choices=SYMBOLS)
    unit.add_argument("source_root", type=Path)
    unit.add_argument("aggregate_root", type=Path)
    unit.add_argument("output_root", type=Path)
    combined = sub.add_parser("aggregate")
    combined.add_argument("witness_dir", type=Path)
    combined.add_argument("output_dir", type=Path)
    args = ap.parse_args()
    if args.action == "symbol":
        result = run_symbol(args.symbol, args.source_root, args.aggregate_root)
        args.output_root.mkdir(parents=True, exist_ok=True)
        p = args.output_root / f"qore-tom-single-{args.symbol}.json"
        p.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print("QORE_TOM_ECONOMICS", args.symbol)
        for period in ("dev", "diag"):
            print(period, json.dumps(result[period], sort_keys=True))
        print("NO_NET_CERTIFICATION")
    else:
        included: dict[str, dict[str, Any]] = {}
        for symbol in SYMBOLS:
            matches = list(args.witness_dir.rglob(f"qore-tom-single-{symbol}.json"))
            if len(matches) != 1:
                raise ValueError("MISSING_OR_DUPLICATE_FROZEN_MARKET_RESULT")
            d = json.loads(matches[0].read_text())
            if (d["identity"] != symbol or d["prereg_sha"] != PREREG_SHA
                    or d["source_all_11_years_SHA_verified"] is not True
                    or d["prices_post_2024_09_17_read"] is not False
                    or d["historical_bidask_net_calculated"] is not False):
                raise ValueError("FOREIGN_OR_UNSAFE_SOURCE_WITNESS")
            included[symbol] = d
        conclusion = decide(included)
        packed = json.dumps(conclusion, sort_keys=True, separators=(",", ":"))
        conclusion["receipt_sha256"] = hashlib.sha256(packed.encode()).hexdigest()
        args.output_dir.mkdir(parents=True, exist_ok=True)
        p = args.output_dir / "qore-tom-final-three-index.json"
        p.write_text(json.dumps(conclusion, indent=2, sort_keys=True) + "\n")
        print("QORE_TOM_PRIMARY_VERDICT", conclusion["verdict"])
        print("QORE_TOM_NEXT_ACTION", conclusion["next_action"])
        print("QORE_TOM_RECEIPT_SHA256", conclusion["receipt_sha256"])


if __name__ == "__main__":
    main()
