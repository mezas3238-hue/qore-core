from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_b01_risk_economic_replay_r3_11 import (
    BrokerVolumeConstraints,
    RiskEconomicReplayError,
    RiskReplayPolicy,
    broker_valid_fixed_risk_quantity,
    quote_to_usd_factor,
)


def _constraints() -> BrokerVolumeConstraints:
    return BrokerVolumeConstraints(
        symbol="EURUSD",
        min_quantity=Decimal("1000"),
        max_quantity=Decimal("1000000"),
        step_quantity=Decimal("1000"),
    )


def test_fixed_risk_quantity_for_usd_quote_pair_is_exact() -> None:
    outcome, quantity, bounded_loss = broker_valid_fixed_risk_quantity(
        desired_loss_usd=Decimal("500"),
        per_unit_loss_usd=Decimal("0.005"),
        constraints=_constraints(),
    )
    assert outcome == "ALLOW"
    assert quantity == Decimal("100000")
    assert bounded_loss == Decimal("500")


def test_fixed_risk_quantity_rejects_below_broker_minimum() -> None:
    outcome, quantity, bounded_loss = broker_valid_fixed_risk_quantity(
        desired_loss_usd=Decimal("1"),
        per_unit_loss_usd=Decimal("0.005"),
        constraints=_constraints(),
    )
    assert outcome == "REJECT"
    assert quantity == Decimal(0)
    assert bounded_loss == Decimal(0)


def test_fixed_risk_quantity_reduces_at_broker_maximum() -> None:
    outcome, quantity, bounded_loss = broker_valid_fixed_risk_quantity(
        desired_loss_usd=Decimal("10000"),
        per_unit_loss_usd=Decimal("0.005"),
        constraints=_constraints(),
    )
    assert outcome == "REDUCE"
    assert quantity == Decimal("1000000")
    assert bounded_loss == Decimal("5000")


def test_quote_to_usd_factor_handles_usd_base_and_jpy_crosses() -> None:
    at = datetime(2026, 1, 1, tzinfo=UTC)
    indices = {"USDJPY": ([at], [Decimal("150")])}
    assert quote_to_usd_factor(
        "EURUSD", at, instrument_price=Decimal("1.10"), indices=indices
    ) == Decimal(1)
    assert quote_to_usd_factor(
        "USDJPY", at, instrument_price=Decimal("150"), indices=indices
    ) == Decimal(1) / Decimal("150")
    assert quote_to_usd_factor(
        "GBPJPY", at, instrument_price=Decimal("190"), indices=indices
    ) == Decimal(1) / Decimal("150")


def test_primary_policy_freezes_half_percent_trade_risk_and_one_point_five_heat() -> None:
    policy = RiskReplayPolicy()
    assert policy.starting_equity_usd == Decimal("100000")
    assert policy.per_trade_risk_bps == 50
    assert policy.portfolio_heat_bps == 150
    assert policy.price_cost_bps == Decimal(0)


def test_policy_rejects_portfolio_heat_below_per_trade_risk() -> None:
    try:
        RiskReplayPolicy(per_trade_risk_bps=50, portfolio_heat_bps=49)
    except RiskEconomicReplayError as error:
        assert "portfolio heat" in str(error)
    else:
        raise AssertionError("invalid Risk policy must fail closed")
