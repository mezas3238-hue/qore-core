# ruff: noqa: I001
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_fundednext_provider import (
    FundedNextCiboSymbolSpecification,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
    ctrader_demo_economic_observation,
    fundednext_economic_observation,
    evaluate_minimum_seed_feasibility,
    normalize_provider_economics,
)
from qore.infrastructure.ctrader_demo_compat import CTraderDemoSymbolSpecification


NOW = datetime(2026, 9, 26, 14, 0, tzinfo=UTC)


def _opportunity(
    *,
    stop_per_volume: str = "10",
    minimum_volume: str = "0.01",
    volume_step: str = "0.01",
    maximum_volume: str = "100",
    margin_per_volume: str = "20",
    minimum_execution_steps: int = 1,
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="signal-1",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal(stop_per_volume),
        margin_per_volume=Decimal(margin_per_volume),
        volume_step=Decimal(volume_step),
        minimum_volume=Decimal(minimum_volume),
        maximum_volume=Decimal(maximum_volume),
        minimum_execution_steps=minimum_execution_steps,
    )


def _observation(
    *,
    tick_size: str = "0.1",
    tick_value: str = "1",
    contract_size: str = "100",
    minimum_volume: str = "0.01",
    volume_step: str = "0.01",
    maximum_volume: str = "100",
    margin_per_volume: str = "20",
    bid: str = "99.9",
    ask: str = "100.1",
    commission: str = "0",
    slippage: str = "0",
) -> ProviderEconomicObservation:
    return ProviderEconomicObservation(
        provider_key="provider-a",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        bid=Decimal(bid),
        ask=Decimal(ask),
        contract_size=Decimal(contract_size),
        tick_size=Decimal(tick_size),
        tick_value=Decimal(tick_value),
        minimum_volume=Decimal(minimum_volume),
        maximum_volume=Decimal(maximum_volume),
        volume_step=Decimal(volume_step),
        margin_per_volume=Decimal(margin_per_volume),
        commission_per_volume_usd=Decimal(commission),
        slippage_reserve_per_volume_usd=Decimal(slippage),
        observed_at=NOW,
    )


def test_equivalent_provider_stop_economics_normalize_to_same_usd_risk() -> None:
    left = normalize_provider_economics(
        opportunity=_opportunity(stop_per_volume="10"),
        observation=_observation(
            tick_size="0.1",
            tick_value="1",
            contract_size="100",
        ),
    )
    right = normalize_provider_economics(
        opportunity=_opportunity(stop_per_volume="10"),
        observation=_observation(
            tick_size="0.01",
            tick_value="0.1",
            contract_size="1000",
        ),
    )

    assert left.raw_stop_loss_per_volume_usd == Decimal("10")
    assert right.raw_stop_loss_per_volume_usd == Decimal("10")
    assert left.minimum_stop_risk_usd == right.minimum_stop_risk_usd
    assert left.provider_units_per_volume != right.provider_units_per_volume


def test_minimum_execution_steps_raise_provider_floor_without_trader_sizing() -> None:
    envelope = normalize_provider_economics(
        opportunity=_opportunity(
            minimum_volume="0.10",
            volume_step="0.10",
            stop_per_volume="10",
            minimum_execution_steps=4,
        ),
        observation=_observation(
            minimum_volume="0.10",
            volume_step="0.10",
        ),
    )

    assert envelope.minimum_executable_volume == Decimal("0.40")
    assert envelope.minimum_stop_risk_usd == Decimal("4.00")
    assert envelope.minimum_margin_usd == Decimal("8.00")


def test_provider_spread_commission_and_slippage_are_normalized_separately() -> None:
    envelope = normalize_provider_economics(
        opportunity=_opportunity(),
        observation=_observation(
            bid="99.9",
            ask="100.1",
            commission="2",
            slippage="1",
        ),
    )

    assert envelope.spread_cost_per_volume_usd == Decimal("2")
    assert envelope.execution_cost_per_volume_usd == Decimal("5")
    assert envelope.minimum_execution_cost_usd == Decimal("0.05")


def test_opportunity_cannot_understate_raw_provider_stop_risk() -> None:
    with pytest.raises(CiboCapitalManagementError, match="understates"):
        normalize_provider_economics(
            opportunity=_opportunity(stop_per_volume="9"),
            observation=_observation(),
        )


def test_provider_contract_drift_fails_closed() -> None:
    with pytest.raises(CiboCapitalManagementError, match="volume_step drift"):
        normalize_provider_economics(
            opportunity=_opportunity(volume_step="0.01"),
            observation=_observation(volume_step="0.10"),
        )


def test_small_account_feasibility_accepts_minimum_that_fits_both_headrooms() -> None:
    envelope = normalize_provider_economics(
        opportunity=_opportunity(stop_per_volume="10"),
        observation=_observation(),
    )

    decision = evaluate_minimum_seed_feasibility(
        envelope,
        hard_risk_headroom_usd=Decimal("0.20"),
        margin_headroom_usd=Decimal("1"),
    )

    assert decision.executable is True
    assert decision.minimum_stop_risk_usd == Decimal("0.10")
    assert decision.minimum_margin_usd == Decimal("0.20")


def test_small_account_feasibility_rejects_when_broker_minimum_breaks_risk() -> None:
    envelope = normalize_provider_economics(
        opportunity=_opportunity(
            stop_per_volume="7000",
            minimum_volume="0.01",
        ),
        observation=_observation(minimum_volume="0.01"),
    )

    decision = evaluate_minimum_seed_feasibility(
        envelope,
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("1000"),
    )

    assert decision.executable is False
    assert decision.minimum_stop_risk_usd == Decimal("70.00")
    assert "hard risk" in decision.reason


def test_ctrader_adapter_preserves_native_economic_facts() -> None:
    spec = CTraderDemoSymbolSpecification(
        provider_symbol="EURUSD",
        bid=Decimal("1.1000"),
        ask=Decimal("1.1002"),
        spread_points=Decimal("2"),
        digits=5,
        point=Decimal("0.0001"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.0001"),
        tick_value=Decimal("10"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        minimum_stop_distance_points=Decimal("0"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("1000"),
        trade_enabled=True,
        session_open=True,
        observed_at=NOW,
        open_commission_per_lot_usd=Decimal("3"),
    )

    observation = ctrader_demo_economic_observation(
        qore_symbol="EURUSD",
        provider_key="ctrader-demo",
        spec=spec,
        slippage_reserve_per_volume_usd=Decimal("1"),
    )

    assert observation.contract_size == Decimal("100000")
    assert observation.commission_per_volume_usd == Decimal("3")
    assert observation.slippage_reserve_per_volume_usd == Decimal("1")



def test_fundednext_adapter_uses_same_common_economic_contract() -> None:
    spec = FundedNextCiboSymbolSpecification(
        provider_symbol="EURUSD",
        bid=Decimal("1.1000"),
        ask=Decimal("1.1002"),
        spread_points=Decimal("2"),
        digits=5,
        point=Decimal("0.0001"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.0001"),
        tick_value=Decimal("10"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        minimum_stop_distance_points=Decimal("0"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("1000"),
        trade_enabled=True,
        session_open=True,
        observed_at=NOW,
        open_commission_per_lot_usd=Decimal("7"),
    )

    observation = fundednext_economic_observation(
        qore_symbol="EURUSD",
        provider_key="fundednext",
        spec=spec,
        slippage_reserve_per_volume_usd=Decimal("1"),
    )

    assert isinstance(observation, ProviderEconomicObservation)
    assert observation.provider_key == "fundednext"
    assert observation.contract_size == Decimal("100000")
    assert observation.commission_per_volume_usd == Decimal("7")
    assert observation.slippage_reserve_per_volume_usd == Decimal("1")
