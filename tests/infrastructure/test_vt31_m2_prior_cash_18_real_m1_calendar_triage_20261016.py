"""Counterfactual cash-day source proof for 18 fixed G3 mismatches."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import NEW_YORK, M1Bar
from scripts.vt31_m2_prior_cash_18_real_m1_calendar_triage_20261016 import (
    CASES,
    CashDispute,
    cash_390_day,
    cash_days_for_case,
    classify_case,
    nominal_previous_weekday,
)


def row(day: str, i: int, *, lo: str = "98", hi: str = "102") -> M1Bar:
    at = datetime.fromisoformat(day).replace(
        tzinfo=NEW_YORK, hour=9, minute=30,
    ).astimezone(UTC) + timedelta(minutes=i)
    return M1Bar(
        at, at + timedelta(minutes=1),
        Decimal("100"), Decimal(hi), Decimal(lo), Decimal("100"),
    )


@pytest.mark.parametrize("day", ["2025-01-15", "2025-07-15"])
def test_complete_cash_is_exact_390_m1_with_correct_dst(day):
    source = cash_390_day(day, tuple(row(day, i) for i in range(390)))
    assert source["cash_390_M1_closed_contiguous"]
    assert source["cash_ny_0930_1600_M1"] == 390
    assert Decimal(source["high"]) == Decimal("102")
    assert Decimal(source["low"]) == Decimal("98")
    assert not source["broker_calendar_closed_proven"]
    expected_hour = 21 if day.endswith("01-15") else 20
    assert datetime.fromisoformat(source["source_cash_close_utc"]).hour == expected_hour


@pytest.mark.parametrize("missing", [0, 17, 389])
def test_389_m1_cash_is_not_a_complete_day_or_valid_price(missing):
    day = "2025-07-03"
    source = cash_390_day(
        day, tuple(row(day, i) for i in range(390) if i != missing),
    )
    assert not source["cash_390_M1_closed_contiguous"]
    assert source["high"] is None and source["low"] is None


def test_more_than_390_m1_cannot_be_silent_duplicate():
    with pytest.raises(ValueError, match="MORE_THAN_390"):
        cash_390_day(
            "2025-07-03",
            tuple(row("2025-07-03", i) for i in range(391)),
        )


def test_g3_older_complete_price_match_nominal_cash_missing_is_not_future_leak():
    case = CashDispute("2025-07-07", "VT31_NY_AM", "2025-07-02", "LOW", "98")
    days = cash_days_for_case(case)
    assert days == ("2025-07-02", "2025-07-03", "2025-07-04")
    cash = {
        days[0]: cash_390_day(
            days[0], tuple(row(days[0], i) for i in range(390)),
        ),
        days[1]: cash_390_day(days[1], ()),
        days[2]: cash_390_day(days[2], ()),
    }
    result = classify_case(case, cash)
    assert result["original_G3_cash_source_price_state"] == (
        "OLDER_G3_CASH_SOURCE_COMPLETE_AND_PRICE_MATCH"
    )
    assert result["original_cash_selection_context"] == (
        "OLDER_ONLY_COMPLETE_IN_OBSERVED_SOURCE_CONTEXT"
    )
    assert result["newer_complete_cash_dates_than_G3"] == []
    assert not result["g3_lookahead_proven"]


def test_g3_older_source_with_newer_complete_cash_is_explicit_conflict():
    case = CashDispute("2025-07-07", "VT31_NY_AM", "2025-07-02", "LOW", "98")
    days = cash_days_for_case(case)
    cash = {
        days[0]: cash_390_day(
            days[0], tuple(row(days[0], i) for i in range(390)),
        ),
        days[1]: cash_390_day(
            days[1], tuple(row(days[1], i) for i in range(390)),
        ),
        days[2]: cash_390_day(days[2], ()),
    }
    result = classify_case(case, cash)
    assert result["newer_complete_cash_dates_than_G3"] == ["2025-07-03"]
    assert result["original_cash_selection_context"] == (
        "NEWER_COMPLETE_CASH_DAY_EXISTS_NEEDS_METHOD"
    )
    assert not result["cash_DOCTRINE_certified"]


def test_g3_cash_original_price_not_reconstructed_is_not_accepted():
    case = CashDispute("2025-07-07", "VT31_NY_AM", "2025-07-02", "LOW", "97")
    days = cash_days_for_case(case)
    cash = {
        days[0]: cash_390_day(
            days[0], tuple(row(days[0], i) for i in range(390)),
        ),
        days[1]: cash_390_day(days[1], ()),
        days[2]: cash_390_day(days[2], ()),
    }
    result = classify_case(case, cash)
    assert result["original_G3_cash_source_price_state"] == (
        "OLDER_G3_CASH_SOURCE_PRICE_DISAGREES"
    )


def test_fixed_18_cases_not_changed_after_previous_sealed_run():
    assert len(CASES) == 18
    assert len({(c.day, c.session) for c in CASES}) == 18
    assert sum(c.session == "VT31_LONDON" for c in CASES) == 2
    assert sum(c.session == "VT31_NY_AM" for c in CASES) == 8
    assert sum(c.session == "VT31_NY_PM" for c in CASES) == 8


def test_nominal_previous_weekday_never_assumes_market_open():
    d = datetime.fromisoformat("2025-07-07").date()
    assert nominal_previous_weekday(d).isoformat() == "2025-07-04"
    # July 4 is just a nominal weekday, NOT broker hours evidence.
    assert not cash_390_day("2025-07-04", ())["cash_390_M1_closed_contiguous"]


def test_bad_case_rejected_without_broker_calendar_guess():
    with pytest.raises(ValueError, match="SOURCE_DAY_MUST_PREDATE"):
        cash_days_for_case(CashDispute(
            "2025-07-07", "VT31_LONDON", "2025-07-07", "HIGH", "102",
        ))
