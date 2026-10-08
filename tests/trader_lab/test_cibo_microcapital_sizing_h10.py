"""H10 tests: $3 risk-at-stop micro curriculum; FundedNext is separate."""
from decimal import Decimal as D

import pytest

from qore.infrastructure.trader_lab.cibo_microcapital_sizing_h10 import (
    MicroAccountState,
    micro_stop_target,
    plan_microcapital_entry,
)


def state(
    balance: str, floor: str, *, peak: str | None = None,
    day: str | None = None, day_limit: str = "6",
    reserved: str = "0", margin: str = "0",
) -> MicroAccountState:
    return MicroAccountState(
        balance_usd=D(balance),
        settled_peak_usd=D(peak or balance),
        trailing_floor_usd=D(floor),
        reserved_open_stop_and_exit_fees_usd=D(reserved),
        day_open_balance_usd=D(day or balance),
        daily_internal_cap_usd=D(day_limit),
        already_committed_margin_usd=D(margin),
    )


def test_sixty_dollars_allocates_three_at_stop_plus_fee():
    result = plan_microcapital_entry(
        state("60", "45"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D("3.14"),
        broker_minimum_roundtrip_fee_usd=D(".14"),
        broker_minimum_margin_usd=D("5"),
    )
    assert result.desired_stop_risk_usd == D("3")
    assert result.maximum_fundable_stop_risk_usd == D("3")
    assert result.entry_stop_and_roundtrip_fee_ceiling_usd == D("3.14")
    assert result.aggregate_risk_ceiling_usd == D("6")
    assert result.can_fund_broker_minimum


def test_gentle_scale_uses_current_realized_balance():
    assert [micro_stop_target(D(c)) for c in ("60", "100", "500", "2000")] == [
        D("3"), D("3.32"), D("6.52"), D("18.52"),
    ]


def test_funded_2k_stays_under_sixty_aggregate():
    r = plan_microcapital_entry(
        state("2000", "1880", day_limit="60"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D("10.14"),
        broker_minimum_roundtrip_fee_usd=D(".14"),
        broker_minimum_margin_usd=D("50"),
        account_mode="stellar_instant",
    )
    assert r.desired_stop_risk_usd == D("18.52")
    assert r.entry_stop_and_roundtrip_fee_ceiling_usd == D("18.66")
    assert r.aggregate_risk_ceiling_usd == D("60")
    assert r.can_fund_broker_minimum


def test_trailing_and_daily_limit_win_over_desired_stop():
    r = plan_microcapital_entry(
        state("1880.1", "1880", peak="2000", day="2000", day_limit="60"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D(".14"),
        broker_minimum_roundtrip_fee_usd=D(".14"),
        broker_minimum_margin_usd=D("1"),
        account_mode="stellar_instant",
    )
    assert r.maximum_fundable_stop_risk_usd == D("0")
    assert not r.can_fund_broker_minimum


def test_micro_drawdown_tapers_future_risk():
    healthy = plan_microcapital_entry(
        state("60", "45"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D(".1"),
        broker_minimum_margin_usd=D("5"),
    )
    distressed = plan_microcapital_entry(
        state("57", "45", peak="60", day="60", day_limit="6"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D(".1"),
        broker_minimum_margin_usd=D("5"),
    )
    assert distressed.desired_stop_risk_usd < healthy.desired_stop_risk_usd
    assert distressed.scale_multiplier == D(".25")


def test_initial_historical_nas100_min_lot_cannot_be_financed():
    r = plan_microcapital_entry(
        state("60", "45"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D("1.695"),
        broker_minimum_roundtrip_fee_usd=D("1.40"),
        broker_minimum_margin_usd=D("77.7885"),
    )
    assert r.desired_stop_risk_usd == D("3")
    assert not r.can_fund_broker_minimum
    assert r.hard_fail_reason == "BROKER_MIN_MARGIN_UNFUNDED"


def test_micro_cannot_ignore_roundtrip_fees():
    r = plan_microcapital_entry(
        state("60", "45"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D("4.70"),
        broker_minimum_roundtrip_fee_usd=D("1.40"),
        broker_minimum_margin_usd=D("10"),
    )
    assert r.entry_stop_and_roundtrip_fee_ceiling_usd == D("4.40")
    assert not r.can_fund_broker_minimum
    assert r.shortfall_to_broker_minimum_usd == D(".30")


def test_concurrent_risk_not_double_spent():
    r = plan_microcapital_entry(
        state("60", "45", reserved="3.4"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D("3.14"),
        broker_minimum_roundtrip_fee_usd=D(".14"),
        broker_minimum_margin_usd=D("5"),
    )
    assert r.entry_stop_and_roundtrip_fee_ceiling_usd == D("2.6")
    assert not r.can_fund_broker_minimum


def test_malformed_fee_denied():
    with pytest.raises(ValueError, match="minimum fees"):
        plan_microcapital_entry(
            state("60", "45"),
            broker_minimum_stop_plus_roundtrip_fees_usd=D(".14"),
            broker_minimum_roundtrip_fee_usd=D("1.40"),
            broker_minimum_margin_usd=D("5"),
        )
