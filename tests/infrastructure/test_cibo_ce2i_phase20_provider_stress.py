from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboReplayCausalTrade,
    ReplayEconomicsStatus,
    ReplaySignalFingerprintOrigin,
)
from qore.infrastructure.cibo_ce2i_phase20_provider_stress import (
    Phase20ProviderStressScenario,
    build_phase20_counterfactual_provider_stress,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)


def _causal() -> CiboReplayCausalTrade:
    return CiboReplayCausalTrade(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="signal-1",
        signal_fingerprint_origin=(
            ReplaySignalFingerprintOrigin.PHASE18_RECONSTRUCTED
        ),
        qore_symbol="EURUSD",
        side="long",
        signal_at=datetime(2021, 10, 1, 12, 0, tzinfo=UTC),
        entry_at=datetime(2021, 10, 1, 12, 1, tzinfo=UTC),
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        legacy_risk_scale=Decimal("1"),
        minimum_execution_steps=1,
        pre_trade_state=(),
        source_evidence_ids=("phase18:eurusd",),
        economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
    )


def _observation(*, qore_symbol: str = "EURUSD") -> ProviderEconomicObservation:
    return ProviderEconomicObservation(
        provider_key="ctrader-demo-current",
        qore_symbol=qore_symbol,
        provider_symbol=qore_symbol,
        bid=Decimal("99.9"),
        ask=Decimal("100.1"),
        contract_size=Decimal("100"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        margin_per_volume=Decimal("20"),
        commission_per_volume_usd=Decimal("2"),
        slippage_reserve_per_volume_usd=Decimal("1"),
        observed_at=datetime(2026, 9, 26, 18, 0, tzinfo=UTC),
    )


def _scenario() -> Phase20ProviderStressScenario:
    return Phase20ProviderStressScenario(
        scenario_id="ADVERSE_CURRENT_PROVIDER_V1",
        evidence_id="experiment:phase20:predeclared",
        minimum_spread_ticks=Decimal("3"),
        spread_multiplier=Decimal("2"),
        commission_multiplier=Decimal("1.5"),
        minimum_slippage_reserve_per_volume_usd=Decimal("2"),
        margin_multiplier=Decimal("2"),
        broker_risk_buffer=Decimal("1.1"),
    )


def test_counterfactual_stress_preserves_geometry_and_stresses_economics() -> None:
    result = build_phase20_counterfactual_provider_stress(
        causal=_causal(),
        observation=_observation(),
        scenario=_scenario(),
    )

    assert result.opportunity.intended_entry == Decimal("100")
    assert result.opportunity.stop_loss == Decimal("99")
    assert result.opportunity.take_profit == Decimal("102")
    assert result.economics.stressed_spread_ticks == Decimal("4")
    assert result.economics.stressed_spread_cost_per_volume_usd == Decimal("4")
    assert result.economics.stressed_commission_per_volume_usd == Decimal("3.0")
    assert (
        result.economics.stressed_slippage_reserve_per_volume_usd
        == Decimal("2")
    )
    assert result.economics.stressed_execution_cost_per_volume_usd == Decimal("9.0")
    assert result.economics.stressed_margin_per_volume_usd == Decimal("40")
    assert result.opportunity.stop_loss_per_volume == Decimal("20.90")
    assert result.opportunity.margin_per_volume == Decimal("40")


def test_current_snapshot_remains_explicitly_counterfactual_for_old_trade() -> None:
    result = build_phase20_counterfactual_provider_stress(
        causal=_causal(),
        observation=_observation(),
        scenario=_scenario(),
    )

    assert _observation().observed_at > _causal().entry_at
    assert result.economics.historical_provider_economics_claimed is False
    assert result.economics.historical_causality_claimed is False
    assert result.economics.allocation_authority is False
    assert result.economics.risk_authority is False
    assert result.economics.execution_authority is False
    assert result.research_only is True
    assert result.demo_execution_authorized is False
    assert result.live_authorized is False
    assert result.real_capital_authorized is False


def test_stress_parameters_cannot_improve_provider_economics() -> None:
    with pytest.raises(CiboCapitalManagementError, match=">= 1"):
        Phase20ProviderStressScenario(
            scenario_id="bad",
            evidence_id="bad",
            minimum_spread_ticks=Decimal("0"),
            spread_multiplier=Decimal("0.9"),
            commission_multiplier=Decimal("1"),
            minimum_slippage_reserve_per_volume_usd=Decimal("0"),
            margin_multiplier=Decimal("1"),
            broker_risk_buffer=Decimal("1"),
        )


def test_provider_symbol_mismatch_fails_closed() -> None:
    with pytest.raises(CiboCapitalManagementError, match="QORE symbol mismatch"):
        build_phase20_counterfactual_provider_stress(
            causal=_causal(),
            observation=_observation(qore_symbol="GBPUSD"),
            scenario=_scenario(),
        )
