#!/usr/bin/env python3
"""18 fixed G3 prior-cash disputes: what does REAL M1 actually prove?

This checks only the source identity + source coverage/price of a cash pool,
not the liquidity doctrine, broker hours, a signal, or trading performance.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import NEW_YORK, M1Bar
from scripts.vt31_ict_cleanroom_cog_real_3y_fast_v1 import _bar, _dt, _stream
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    hash_file,
)

PREREG = "cd49fc53a80700449e229121e39f7a306c968e88"
FIXED_FIRST_M1_CASEBOOK = (
    "d74b24242c4b8c5656547727b88886ecd1a18243c362d9d366825880bddbfc21"
)
VERSION = "VT31_M2_18_G3_PRIOR_CASH_390_M1_SOURCE_CALENDAR_TRIAGE_V1"


@dataclass(frozen=True, slots=True)
class CashDispute:
    day: str
    session: str
    original_cash_date: str
    side: str
    original_draw_price: str


# Exact 18, FIXED BEFORE this runner, from #38975891228 archived casebook.
CASES = (
    CashDispute("2023-10-13", "VT31_NY_AM", "2023-10-10", "LOW", "15040.60"),
    CashDispute("2023-11-08", "VT31_NY_PM", "2023-11-03", "LOW", "14964.30"),
    CashDispute("2023-11-27", "VT31_NY_AM", "2023-11-22", "HIGH", "16122.80"),
    CashDispute("2023-12-14", "VT31_NY_AM", "2023-12-12", "LOW", "16175.80"),
    CashDispute("2023-12-27", "VT31_NY_PM", "2023-12-22", "LOW", "16697.10"),
    CashDispute("2023-12-29", "VT31_NY_AM", "2023-12-27", "LOW", "16856.10"),
    CashDispute("2024-01-16", "VT31_NY_PM", "2024-01-12", "HIGH", "16900.10"),
    CashDispute("2024-05-28", "VT31_NY_AM", "2024-05-24", "LOW", "18666.13"),
    CashDispute("2024-06-20", "VT31_NY_AM", "2024-06-18", "LOW", "19848.46"),
    CashDispute("2024-12-26", "VT31_NY_PM", "2024-12-23", "LOW", "21188.95"),
    CashDispute("2025-07-04", "VT31_NY_AM", "2025-07-02", "LOW", "22440.00"),
    CashDispute("2025-07-07", "VT31_NY_AM", "2025-07-02", "LOW", "22440.00"),
    CashDispute("2025-08-04", "VT31_NY_PM", "2025-07-31", "HIGH", "23613.50"),
    CashDispute("2025-12-26", "VT31_NY_PM", "2025-12-23", "LOW", "25395.30"),
    CashDispute("2026-01-02", "VT31_LONDON", "2025-12-31", "HIGH", "25481.00"),
    CashDispute("2026-01-20", "VT31_NY_PM", "2026-01-16", "HIGH", "25733.60"),
    CashDispute("2026-02-17", "VT31_LONDON", "2026-02-13", "HIGH", "24920.80"),
    CashDispute("2026-04-06", "VT31_NY_PM", "2026-04-02", "LOW", "23501.40"),
)


def nominal_previous_weekday(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def cash_days_for_case(case: CashDispute) -> tuple[str, ...]:
    origin = date.fromisoformat(case.original_cash_date)
    target = date.fromisoformat(case.day)
    if origin >= target or case.session not in (
        "VT31_LONDON", "VT31_NY_AM", "VT31_NY_PM",
    ) or case.side not in ("HIGH", "LOW"):
        raise ValueError("SOURCE_DAY_MUST_PREDATE_SILVER_BULLET_COHORT")
    days: list[str] = []
    while origin < target:
        if origin.weekday() < 5:
            days.append(origin.isoformat())
        origin += timedelta(days=1)
    return tuple(days)


def cash_390_day(
    day: str, bars: tuple[M1Bar, ...],
) -> dict[str, Any]:
    local_day = date.fromisoformat(day)
    begin = datetime.combine(
        local_day, time(9, 30), tzinfo=NEW_YORK,
    ).astimezone(UTC)
    if len(bars) > 390:
        raise ValueError("CASH_SOURCE_MORE_THAN_390_M1")
    complete = len(bars) == 390 and all(
        b.opened_at == begin + timedelta(minutes=i)
        and b.closed_at == begin + timedelta(minutes=i + 1)
        for i, b in enumerate(bars)
    )
    return {
        "day": day,
        "cash_ny_0930_1600_M1": len(bars),
        "cash_390_M1_closed_contiguous": complete,
        "high": str(max(b.high for b in bars)) if complete else None,
        "low": str(min(b.low for b in bars)) if complete else None,
        "source_cash_close_utc": (begin + timedelta(minutes=390)).isoformat(),
        "broker_calendar_closed_proven": False,
    }


def classify_case(
    case: CashDispute,
    cash: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    required = cash_days_for_case(case)
    if not required or required[0] != case.original_cash_date:
        raise AssertionError("PREREG_CASE_SOURCE_DATES_CHANGED")
    older = cash[case.original_cash_date]
    nominal_day = nominal_previous_weekday(date.fromisoformat(case.day))
    nominal = cash[nominal_day.isoformat()]
    newer = [
        x for x in required[1:] if cash[x]["cash_390_M1_closed_contiguous"]
    ]
    if not older["cash_390_M1_closed_contiguous"]:
        price_state = "OLDER_G3_CASH_SOURCE_INCOMPLETE_UNKNOWN"
    elif Decimal(
        older["high" if case.side == "HIGH" else "low"]
    ) == Decimal(case.original_draw_price):
        price_state = "OLDER_G3_CASH_SOURCE_COMPLETE_AND_PRICE_MATCH"
    else:
        price_state = "OLDER_G3_CASH_SOURCE_PRICE_DISAGREES"
    if older["cash_390_M1_closed_contiguous"] and not newer:
        selection_context = "OLDER_ONLY_COMPLETE_IN_OBSERVED_SOURCE_CONTEXT"
    elif older["cash_390_M1_closed_contiguous"] and newer:
        selection_context = "NEWER_COMPLETE_CASH_DAY_EXISTS_NEEDS_METHOD"
    else:
        selection_context = "OLDER_SOURCE_CASH_M1_INCOMPLETE_UNKNOWN"
    return {
        "ny_session_date": case.day,
        "session": case.session,
        "G3_draw_family": f"PRIOR_NY_CASH_SESSION_{case.side}",
        "G3_original_cash_date": case.original_cash_date,
        "G3_original_draw_price": case.original_draw_price,
        "G3_original_cash_390_M1": older,
        "nominal_previous_weekday": nominal_day.isoformat(),
        "nominal_previous_weekday_cash_390_M1": nominal,
        "newer_complete_cash_dates_than_G3": newer,
        "most_recent_observed_complete_cash_day": (
            max(
                (x for x in required if cash[x]["cash_390_M1_closed_contiguous"]),
                default=None,
            )
        ),
        "original_G3_cash_source_price_state": price_state,
        "original_cash_selection_context": selection_context,
        "cash_DOCTRINE_certified": False,
        "broker_calendar_PIT_available": False,
        "g3_lookahead_proven": False,
        "trades": 0,
        "sizing": 0,
    }


def audit_real_18_cash_calendar(
    rows: Any, *, expected_m1: int,
) -> dict[str, Any]:
    if len(CASES) != 18 or len({(c.day, c.session) for c in CASES}) != 18:
        raise AssertionError("PREREG_EXACT_18_DATED_G3_CASH_DISPUTES")
    required = {d for c in CASES for d in cash_days_for_case(c)}
    source: dict[str, list[M1Bar]] = defaultdict(list)
    previous: datetime | None = None
    n = 0
    for raw in rows:
        opened = _dt(raw["opened_at"])
        closed = _dt(raw["closed_at"])
        if (
            closed != opened + timedelta(minutes=1)
            or previous is not None and opened <= previous
        ):
            raise ValueError("PRIOR_CASH_REAL_M1_ORDER_SOURCE_BROKEN")
        previous = opened
        n += 1
        ny = opened.astimezone(NEW_YORK)
        if ny.date().isoformat() not in required:
            continue
        if not (
            (ny.hour == 9 and ny.minute >= 30)
            or (10 <= ny.hour < 16)
        ):
            continue
        source[ny.date().isoformat()].append(_bar(raw))
    if n != expected_m1:
        raise AssertionError("SOURCE_REAL_M1_COUNT_CHANGED")
    summaries = {
        day: cash_390_day(day, tuple(source.get(day, ())))
        for day in sorted(required)
    }
    cases = [classify_case(c, summaries) for c in CASES]
    outcomes = Counter(c["original_G3_cash_source_price_state"] for c in cases)
    selection = Counter(c["original_cash_selection_context"] for c in cases)
    full = json.dumps(cases, sort_keys=True, separators=(",", ":")).encode()
    return {
        "version": VERSION,
        "prereg_before_code_sha": PREREG,
        "fixed_prior_casebook_sha": FIXED_FIRST_M1_CASEBOOK,
        "real_market_M1_hash": MARKET_SHA,
        "real_market_M1_consumed": n,
        "fixed_G3_temporal_disputes": len(cases),
        "unique_cash_weekdays_reconstructed": len(summaries),
        "source_price_evidence_states": dict(sorted(outcomes.items())),
        "source_selection_context_states": dict(sorted(selection.items())),
        "all_18_cash_source_falsifiers": cases,
        "all_18_casebook_json_sha256": sha256(full).hexdigest(),
        "QORE_context_source_audit_only": True,
        "ICT_author_cash_selection_method_certified": False,
        "source_broker_NAS100_calendar_PIT_confirmed": False,
        "M2_author_certified": False,
        "M3_M4_M5_author_certified": False,
        "M6_two_human_signatures": False,
        "M7_VT31_three_silver_bullets_certified": False,
        "broker_orders": 0,
        "sizing": 0,
        "PnL": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("REAL_NAS100_SOURCE_SHA_MISMATCH")
    report = audit_real_18_cash_calendar(_stream(args.market), expected_m1=M1_TOTAL)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "state_counts": report["source_price_evidence_states"],
        "selection_context": report["source_selection_context_states"],
        "casebook_sha": report["all_18_casebook_json_sha256"],
        "full_cases": report["all_18_cash_source_falsifiers"],
        "author_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
