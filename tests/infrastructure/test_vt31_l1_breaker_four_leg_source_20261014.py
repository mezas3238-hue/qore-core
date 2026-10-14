"""Adversarial closed-M1 research-only four-leg source diagnostic, no orders."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_l1_breaker_four_leg_source_20261014 import (
    SUCCESS,
    audit_day,
    census_source,
    confirmed_pivots,
)

NY = ZoneInfo("America/New_York")


def make_bar(t: datetime) -> M1Bar:
    return M1Bar(
        t, t + timedelta(minutes=1),
        Decimal("100"), Decimal("104"), Decimal("98"), Decimal("101"),
    )


def with_prices(bar: M1Bar, **changes: int) -> M1Bar:
    updates = {k: Decimal(str(v)) for k, v in changes.items()}
    return replace(bar, **updates)


def source(month=7, side="LONG"):
    date = datetime(2025, month, 15, 9, tzinfo=NY)
    first = date.astimezone(UTC)
    nine = [make_bar(first + timedelta(minutes=i)) for i in range(60)]
    ten = [make_bar(first + timedelta(minutes=60+i)) for i in range(60)]
    if side == "LONG":
        nine[10] = with_prices(nine[10], low=90)
        nine[20] = with_prices(nine[20], high=110)
        nine[50] = with_prices(nine[50], high=130)
        ten[1] = with_prices(ten[1], low=89)
        ten[2] = with_prices(ten[2], low=88)
        ten[3] = with_prices(ten[3], low=97)
        ten[5] = with_prices(ten[5], high=112)
    else:
        nine[10] = with_prices(nine[10], high=110)
        nine[20] = with_prices(nine[20], low=90)
        nine[40] = with_prices(nine[40], low=70)
        nine[50] = with_prices(nine[50], high=130)
        ten[1] = with_prices(ten[1], high=131)
        ten[2] = with_prices(ten[2], high=132)
        ten[3] = with_prices(ten[3], high=103)
        ten[5] = with_prices(ten[5], low=88)
    day = date.date().isoformat()
    return day, {9: tuple(nine), 10: tuple(ten)}


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
@pytest.mark.parametrize("month", [1, 7])
def test_positive_four_legs_zone_causal_but_not_author_certified(side, month):
    day, hours = source(month=month, side=side)
    event = audit_day(day, hours)
    assert event["state"] == SUCCESS, event
    assert event["side"] == side
    assert event["h1_first_pivot"]["middle_index"] == 10
    assert event["h1_second_pivot"]["middle_index"] == 20
    assert event["third_pivot"]["middle_index"] == 2
    assert event["fourth_pivot"]["middle_index"] == 5
    assert event["third_pivot"]["available_at"] < (
        event["fourth_pivot"]["available_at"]
    )
    assert event["author_breaker_certified"] is False
    assert event["four_leg_pivot_rule_author_attributed"] is False
    assert event["retest_or_entry_executed"] is False
    assert event["zone_proxy_from_directional_candle_series"] is not None


def test_one_9am_pivot_not_a_four_leg_breaker():
    day, hours = source()
    modified = list(hours[10])
    modified[1] = with_prices(modified[1], low=95)
    modified[2] = with_prices(modified[2], low=94)
    hours[10] = tuple(modified)
    out = audit_day(day, hours)
    assert out["state"] == "NO_FIRST_RAID"
    assert len(confirmed_pivots(hours[9])) >= 2


def test_no_confirmed_lower_low_is_not_bullish_breaker():
    day, hours = source()
    changed = list(hours[10])
    changed[2] = with_prices(changed[2], low=89)
    hours[10] = tuple(changed)
    assert audit_day(day, hours)["state"] == "NO_10AM_FIRST_FAILURE_SWING"


def test_lower_low_without_higher_high_is_not_four_leg():
    day, hours = source()
    changed = list(hours[10])
    changed[5] = with_prices(changed[5], high=105)
    hours[10] = tuple(changed)
    assert audit_day(day, hours)["state"] == "NO_10AM_CONFIRMATION_SWING"


def test_double_sweep_unknown_m1_intrabar():
    day, hours = source()
    changed = list(hours[10])
    changed[1] = with_prices(changed[1], high=131)
    hours[10] = tuple(changed)
    assert audit_day(day, hours)["state"] == "DOUBLE_FIRST_RAID_UNKNOWN"


def test_opposite_sweep_before_breaker_fails_closed():
    day, hours = source()
    changed = list(hours[10])
    changed[4] = with_prices(changed[4], high=131)
    hours[10] = tuple(changed)
    assert audit_day(day, hours)["state"] == "OPPOSITE_RAID_BEFORE_CONTEXT"


def test_missing_m1_does_not_mint_false_source_evidence():
    day, hours = source()
    hours[10] = hours[10][:15] + hours[10][16:]
    assert audit_day(day, hours)["state"] == "INCOMPLETE_09_10"


def test_future_data_is_not_consulted_for_success_witness():
    day, hours = source()
    full = audit_day(day, hours)
    changed = list(hours[10])
    changed[50] = with_prices(changed[50], low=85, high=131)
    hours[10] = tuple(changed)
    # The four-leg witness is already confirmed at 10:07.
    assert audit_day(day, hours) == full


def test_no_zone_candle_causes_explicit_negative():
    day, hours = source()
    changed = list(hours[9])
    for i in range(10, 21):
        changed[i] = with_prices(changed[i], close=100)
    hours[9] = tuple(changed)
    assert audit_day(day, hours)["state"] == "NO_BLOCK_CANDLE_ZONE"


def test_synthetic_dataset_is_not_equivalent_to_full_historical_census():
    day, hours = source()
    result = census_source({day: hours}, validate_full=False)
    assert result["total_ny_days"] == 1
    assert result["status_counts"][SUCCESS] == 1
    assert result["author_breaker_certified"] is False
    assert result["broker_orders"] == result["entry_fills"] == 0
    assert result["fresh_holdout"] is False
    with pytest.raises(ValueError, match="FROZEN_775_DAYS"):
        census_source({day: hours}, validate_full=True)


def test_equal_pivot_high_not_confirmed_as_swing():
    day, hours = source()
    changed = list(hours[9])
    changed[20] = with_prices(changed[20], high=104)
    changed[50] = with_prices(changed[50], high=104)
    hours[9] = tuple(changed)
    out = audit_day(day, hours)
    assert out["state"] == "NO_H1_CONFIRMED_PAIR"


def test_pivot_is_available_only_after_right_closed_m1():
    day, hours = source()
    pivots = confirmed_pivots(hours[9])
    assert pivots
    for item in pivots:
        assert item.available_at == hours[9][item.middle_index + 1].closed_at
        assert item.available_at > hours[9][item.middle_index].closed_at
