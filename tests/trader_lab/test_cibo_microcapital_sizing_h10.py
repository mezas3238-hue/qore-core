"""H10 microcapital risk gates, synthetic only; never historic outcome-driven."""
from decimal import Decimal as D
from qore.infrastructure.trader_lab.cibo_microcapital_sizing_h10 import (
    MicroAccountState, plan_microcapital_entry,
)


def state(balance: str, floor: str, peak: str | None = None,
          day: str | None = None, margin: str = "0") -> MicroAccountState:
    return MicroAccountState(
        balance_usd=D(balance),
        settled_peak_usd=D(peak or balance),
        trailing_floor_usd=D(floor),
        reserved_open_stop_and_exit_fees_usd=D("0"),
        day_open_balance_usd=D(day or balance),
        daily_internal_cap_usd=D(day or balance)*D(".03"),
        already_committed_margin_usd=D(margin),
    )


def test_sixty_dollars_means_fifteen_cents_not_ten_dollars():
    result=plan_microcapital_entry(
        state("60","56.4"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D(".10"),
        broker_minimum_margin_usd=D("5"),
    )
    assert result.entry_stop_and_roundtrip_fee_ceiling_usd == D(".1500")
    assert result.can_fund_broker_minimum
    assert result.aggregate_risk_ceiling_usd == D(".60")


def test_two_thousand_dollars_means_five_dollars_not_unbounded_ten():
    result=plan_microcapital_entry(
        state("2000","1880"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D("4"),
        broker_minimum_margin_usd=D("40"),
    )
    assert result.entry_stop_and_roundtrip_fee_ceiling_usd == D("5.0000")
    assert result.can_fund_broker_minimum


def test_scale_gradually_with_actual_balance():
    caps=[]
    for balance in ["60","100","500","2000"]:
        account=D(balance)
        result=plan_microcapital_entry(
            state(balance,str(account*D(".94"))),
            broker_minimum_stop_plus_roundtrip_fees_usd=D(".05"),
            broker_minimum_margin_usd=D(".01"),
        )
        caps.append(result.entry_stop_and_roundtrip_fee_ceiling_usd)
    assert caps == [D(".15"),D(".25"),D("1.25"),D("5")]


def test_drawdown_reduces_risk_before_trade():
    a=plan_microcapital_entry(
        state("2000","1880"),broker_minimum_stop_plus_roundtrip_fees_usd=D("1"),
        broker_minimum_margin_usd=D("10"))
    b=plan_microcapital_entry(
        state("1940","1880",peak="2000",day="2000"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D("1"),
        broker_minimum_margin_usd=D("10"))
    assert b.entry_stop_and_roundtrip_fee_ceiling_usd < a.entry_stop_and_roundtrip_fee_ceiling_usd
    assert b.scale_multiplier == D(".25")


def test_actual_minimum_60_dollars_fails_without_fabricating_fill():
    result=plan_microcapital_entry(
        state("60","56.4"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D("1.695"),
        broker_minimum_margin_usd=D("77.7885"),
    )
    assert not result.can_fund_broker_minimum
    assert result.hard_fail_reason == "BROKER_MIN_MARGIN_UNFUNDED"
    assert result.shortfall_to_broker_minimum_usd == D("1.545")


def test_protect_remaining_daily_and_trailing_headroom():
    result=plan_microcapital_entry(
        state("1880.1","1880",peak="2000",day="2000"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D(".10"),
        broker_minimum_margin_usd=D("1"),
    )
    assert result.entry_stop_and_roundtrip_fee_ceiling_usd == D("0")
    assert not result.can_fund_broker_minimum


def test_minimum_cost_cannot_be_hidden_by_compounding():
    result=plan_microcapital_entry(
        state("500","470"),
        broker_minimum_stop_plus_roundtrip_fees_usd=D("1.695"),
        broker_minimum_margin_usd=D("77.7885"),
    )
    assert not result.can_fund_broker_minimum
    assert result.hard_fail_reason == "BROKER_MIN_STOP_PLUS_FEES_ABOVE_MICRO_BUDGET"
