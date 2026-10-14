#!/usr/bin/env python3
"""VT31 M2 native-CognitiveDecision causal closed-M1 gap forensics.

No pool resurrection, no broker calendar guesses, no synthetic decisions,
no price leakage, no sizing or trading. Reuses the frozen G3 auditor #942.
"""
from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_m2_dol_reconciliation_20261014 import (
    DATES,
    MARKET_SHA,
    NY,
    checksum,
    collect_frozen_days,
)
from scripts.vt31_m2_native_cog_real_m1_20261014 import audit_groups

PREREG_SHA = "5c59705b3c4f00581a65c5245045182a7497672b"
MODEL = "VT31_M2_NATIVE_G3_M1_POST_POOL_GAP_TOPOLOGY_NO_BROKER_CALENDAR"
REFERENCE_HOLIDAY = date(2024, 1, 15)
ONE = timedelta(minutes=1)
EXPECTED_SOURCE_M1 = 1059784


def utc_time(t: datetime) -> datetime:
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("AWARE_DATETIME_REQUIRED")
    return t.astimezone(UTC)


def missing_intervals(
    history: tuple[M1Bar, ...], start: datetime, end: datetime,
) -> tuple[tuple[datetime, datetime], ...]:
    """Return maximal contiguous missing UTC M1 spans between source and as_of.

    All data are compared at exact M1 boundaries; no OHLC reconstruction.
    History may contain earlier bars, but never future bars. Sort/order/length
    validation is owned by original collector and the native COG.
    """
    a, z = utc_time(start), utc_time(end)
    if a > z or a.second or a.microsecond or z.second or z.microsecond:
        raise ValueError("INVALID_SOURCE_OR_ASOF_MINUTE")
    if a == z:
        return ()
    stamps = [utc_time(bar.opened_at) for bar in history]
    if any(x >= y for x, y in zip(stamps, stamps[1:], strict=False)):
        raise ValueError("DUPLICATE_OR_UNSORTED_M1")
    pos = bisect_left(stamps, a)
    cursor = a
    out: list[tuple[datetime, datetime]] = []
    while pos < len(history):
        bar = history[pos]
        opened, closed = utc_time(bar.opened_at), utc_time(bar.closed_at)
        if opened >= z:
            break
        if closed > z:
            raise ValueError("INCOMPLETE_AFTER_ASOF_OR_FUTURE_SOURCE_M1")
        if opened > cursor:
            out.append((cursor, opened))
        if opened < cursor:
            raise ValueError("OVERLAPPING_POST_SOURCE_M1")
        cursor = closed
        pos += 1
    if cursor < z:
        out.append((cursor, z))
    return tuple(out)


def span_label(start: datetime, end: datetime) -> dict[str, Any]:
    a, z = utc_time(start), utc_time(end)
    if a >= z or (z-a) % ONE != timedelta(0):
        raise ValueError("INVALID_POSITIVE_MINUTE_SPAN")
    local_first = a.astimezone(NY).date()
    local_last = (z-ONE).astimezone(NY).date()
    days = tuple(
        local_first + timedelta(days=i)
        for i in range((local_last-local_first).days+1)
    )
    weekend = any(d.weekday() >= 5 for d in days)
    label = (
        "INTERSECTS_NY_WEEKEND" if weekend
        else "CROSSES_NY_DATE_NO_WEEKEND" if local_first != local_last
        else "WITHIN_ONE_NY_DATE"
    )
    return {
        "start_utc": a.isoformat(),
        "end_exclusive_utc": z.isoformat(),
        "missing_m1_count": int((z-a)/ONE),
        "topology": label,
        "intersects_nasdaq_cash_holiday_reference_only": (
            REFERENCE_HOLIDAY in days
        ),
        "broker_closed_verified": False,
        "source_pool_available_verified": False,
    }


def examine_groups(
    groups: dict[str, tuple[M1Bar, ...]],
    prior: dict[str, Any],
) -> dict[str, Any]:
    occurrences: Counter[str] = Counter()
    source_families: Counter[str] = Counter()
    missing_days: Counter[str] = Counter()
    first_theses: Counter[str] = Counter()
    topology_per_emission: Counter[str] = Counter()
    unique_gaps: dict[tuple[str, str], dict[str, Any]] = {}
    cases: list[dict[str, Any]] = []
    for day_report in prior["days"]:
        day = day_report["ny_date"]
        history = groups[day]
        for em in day_report["emissions"]:
            if em["real_native_decision"] is not True:
                raise AssertionError("NON_NATIVE_COG_EMISSION_FORBIDDEN")
            source_end = datetime.fromisoformat(em["dol_confirmed_at"])
            as_of = datetime.fromisoformat(em["as_of"])
            gaps = missing_intervals(history, source_end, as_of)
            pair = em["p3_state"]+"|"+em["v1_state"]
            if pair == "SUPPORTED|SUPPORTED" and gaps:
                raise AssertionError("SUPPORTED_SOURCE_WITH_MISSING_M1")
            if em["p3_state"] == "UNKNOWN":
                if "POST_CONFIRMATION_M1_MONITORING_GAP" not in em["p3_reasons"]:
                    raise AssertionError("NEW_P3_UNKNOWN_REASON_REQUIRES_PREREG")
                if not gaps:
                    raise AssertionError("P3_MONITORING_GAP_WITH_FULL_M1_COVERAGE")
            elif gaps:
                raise AssertionError("GAP_WITH_P3_NONUNKNOWN_NOT_PREREGISTERED")
            occurrences[pair] += 1
            source_families[em["dol_family"]] += 1
            if em["first_native_thesis_not_trade"]:
                first_theses[pair] += 1
            if gaps:
                missing_days[day] += 1
            categories = set()
            for first, last in gaps:
                descr = span_label(first, last)
                categories.add(descr["topology"])
                key = (descr["start_utc"], descr["end_exclusive_utc"])
                unique_gaps.setdefault(key, descr)
            for tag in categories:
                topology_per_emission[tag] += 1
            cases.append({
                "ny_date": day,
                "session": em["session"],
                "as_of": em["as_of"],
                "dol_family": em["dol_family"],
                "p3_v1_pair": pair,
                "first_native_thesis_not_trade": (
                    em["first_native_thesis_not_trade"]
                ),
                "missing_span_count": len(gaps),
                "total_missing_minutes_as_of": sum(
                    int((b-a)/ONE) for a, b in gaps
                ),
                "missing_spans": [span_label(a, b) for a, b in gaps],
                "not_a_trade": True,
                "method_certified": False,
                "cognition_certified": False,
                "execution_authorized": False,
            })
    if len(cases) != prior["native_emission_prefixes_not_trades"]:
        raise AssertionError("ORIGINAL_NATIVE_EMISSION_COUNT_MISMATCH")
    if dict(sorted(occurrences.items())) != prior["pair_matrix_actual_emitted_cog_only"]:
        raise AssertionError("ORIGINAL_SOURCE_WITNESS_STATE_CHANGED")
    if sum(first_theses.values()) != prior["native_unique_first_theses_not_trades"]:
        raise AssertionError("FIRST_NATIVE_THESIS_DENOMINATOR_DRIFT")
    if occurrences.get("UNKNOWN|UNKNOWN", 0) != 485:
        raise AssertionError("FROZEN_UNKNOWN_UNKNOWN_DRIFT")
    if occurrences.get("UNKNOWN|REJECTED", 0) != 78:
        raise AssertionError("FROZEN_UNKNOWN_REJECTED_DRIFT")
    if occurrences.get("SUPPORTED|SUPPORTED", 0) != 541:
        raise AssertionError("FROZEN_SUPPORTED_SUPPORTED_DRIFT")
    all_unique = list(unique_gaps.values())
    unique_classified: Counter[str] = Counter(
        x["topology"] for x in all_unique
    )
    return {
        "identity": MODEL,
        "prereg_commit": PREREG_SHA,
        "market_sha256": MARKET_SHA,
        "historical_dev_not_fresh_oos": True,
        "fixed_dates": list(DATES),
        "source_total_m1": EXPECTED_SOURCE_M1,
        "native_emissions_not_trades": len(cases),
        "native_unique_first_theses_not_trades": sum(first_theses.values()),
        "p3_v1_pairs": dict(sorted(occurrences.items())),
        "first_thesis_pair_counts": dict(sorted(first_theses.items())),
        "emission_counts_by_dol_family": dict(sorted(source_families.items())),
        "emissions_with_missing_m1_by_date": dict(sorted(missing_days.items())),
        "topology_categories_not_disjoint_by_emission": dict(
            sorted(topology_per_emission.items())
        ),
        "unique_exact_missing_interval_count": len(all_unique),
        "unique_exact_intervals_by_topology": dict(
            sorted(unique_classified.items())
        ),
        "unique_interval_minutes_observed_absent": sum(
            x["missing_m1_count"] for x in all_unique
        ),
        "unique_intervals": all_unique,
        "emissions": cases,
        "gaps_reclassified_as_market_closed": 0,
        "gaps_filled_or_imputed": 0,
        "broker_calendar_verified": False,
        "broker_ack_or_fills": 0,
        "method_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "economic_pnl": None,
        "profit_factor": None,
        "execution_authorized": False,
        "live_authorized": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if checksum(args.market) != MARKET_SHA:
        raise ValueError("FROZEN_DATA_SHA_MISMATCH")
    groups, n = collect_frozen_days(args.market)
    if n != EXPECTED_SOURCE_M1:
        raise AssertionError("FROZEN_M1_COUNT_DRIFT")
    prior = audit_groups(groups)
    out = examine_groups(groups, prior)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False)+"\n",
                        encoding="utf-8")
    headline = {
        key: out[key] for key in (
            "source_total_m1", "native_emissions_not_trades",
            "native_unique_first_theses_not_trades", "p3_v1_pairs",
            "first_thesis_pair_counts", "emission_counts_by_dol_family",
            "emissions_with_missing_m1_by_date",
            "topology_categories_not_disjoint_by_emission",
            "unique_exact_missing_interval_count",
            "unique_exact_intervals_by_topology",
            "unique_interval_minutes_observed_absent",
            "broker_calendar_verified", "gaps_reclassified_as_market_closed",
            "method_certified", "cognition_certified",
        )
    }
    print(json.dumps(headline, sort_keys=True))


if __name__ == "__main__":
    main()
