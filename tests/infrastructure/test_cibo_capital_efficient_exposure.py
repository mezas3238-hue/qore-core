from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_efficient_exposure import (
    CiboStressedLossScenarioEvidence,
    build_capital_efficient_exposure_state,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
    normalize_provider_economics,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

NOW = datetime(2026, 9, 29, 22, 50, tzinfo=UTC)


def _envelope():
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="cel-signal",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("1.1000"),
        stop_loss=Decimal("1.0990"),
        take_profit=Decimal("1.1030"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("1000"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        minimum_execution_steps=1,
    )
    observation = ProviderEconomicObservation(
        provider_key="ctrader-demo",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        bid=Decimal("1.0999"),
        ask=Decimal("1.1001"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.0001"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        margin_per_volume=Decimal("1000"),
        commission_per_volume_usd=Decimal("2"),
        slippage_reserve_per_volume_usd=Decimal("1"),
        observed_at=NOW - timedelta(seconds=2),
    )
    return normalize_provider_economics(
        opportunity=opportunity,
        observation=observation,
    )


def _marginal(envelope, volume: Decimal) -> MarginalCapitalUtilityEvidence:
    return MarginalCapitalUtilityEvidence(
        evidence_id="cel-marginal-001",
        decision_at=NOW,
        account_identity=CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="cel-research",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="cel-signal",
        source_opportunity_decision_sha256="sha256:" + "1" * 64,
        source_baseline_policy_record_sha256="sha256:" + "2" * 64,
        current_compound_capacity_usd=Decimal("60"),
        requested_incremental_capital_usd=Decimal("20"),
        expected_incremental_return_usd=Decimal("3"),
        incremental_stop_risk_usd=(
            envelope.cibo_stop_loss_per_volume_usd * volume
        ),
        incremental_margin_usd=envelope.margin_per_volume_usd * volume,
        incremental_execution_cost_usd=(
            envelope.execution_cost_per_volume_usd * volume
        ),
        incremental_concentration_risk_usd=Decimal("0.20"),
        incremental_drawdown_risk_proxy_usd=Decimal("0.30"),
        incremental_optionality_consumed_usd=Decimal("0.10"),
        expected_capital_minutes=Decimal("30"),
        epistemic_uncertainty=Decimal("0.10"),
        provider_evidence_sha256="sha256:" + "3" * 64,
        expectation_evidence_sha256="sha256:" + "4" * 64,
        factor_evidence_sha256="sha256:" + "5" * 64,
        duration_evidence_sha256="sha256:" + "6" * 64,
        execution_evidence_sha256="sha256:" + "7" * 64,
        optionality_evidence_sha256="sha256:" + "8" * 64,
    )


def _stress() -> CiboStressedLossScenarioEvidence:
    return CiboStressedLossScenarioEvidence(
        scenario_id="cel-stress-001",
        observed_at=NOW - timedelta(seconds=2),
        produced_at=NOW - timedelta(seconds=1),
        gap_through_stop_loss_usd=Decimal("0.25"),
        stressed_execution_cost_usd=Decimal("0.08"),
        liquidity_shock_loss_usd=Decimal("0.20"),
        portfolio_convergence_increment_usd=Decimal("0.15"),
        forced_liquidation_loss_usd=Decimal("0.40"),
        evidence_sha256="sha256:" + "9" * 64,
        source="CEL_RESEARCH_STRESS_FIXTURE",
    )


def test_cel_separates_notional_margin_and_stressed_loss() -> None:
    envelope = _envelope()
    volume = Decimal("0.01")
    state = build_capital_efficient_exposure_state(
        state_id="cel-state-001",
        decision_at=NOW,
        envelope=envelope,
        executable_volume=volume,
        marginal_evidence=_marginal(envelope, volume),
        stress=_stress(),
    )

    assert state.notional_exposure_usd == Decimal("1100.000000")
    assert state.margin_occupancy_usd == Decimal("10.00")
    assert state.structural_stop_loss_usd == Decimal("0.10")
    assert state.notional_exposure_usd != state.margin_occupancy_usd
    assert state.margin_occupancy_usd != state.stressed_economic_loss_usd
    assert state.low_margin_is_low_risk is False
    assert state.stressed_economic_loss_usd >= state.base_plausible_loss_usd
    assert len(state.fingerprint()) == 71


def test_cel_uses_worst_explicit_loss_scenario_not_margin_as_risk() -> None:
    envelope = _envelope()
    volume = Decimal("0.01")
    stress = _stress()
    state = build_capital_efficient_exposure_state(
        state_id="cel-state-002",
        decision_at=NOW,
        envelope=envelope,
        executable_volume=volume,
        marginal_evidence=_marginal(envelope, volume),
        stress=stress,
    )

    expected = max(
        state.base_plausible_loss_usd,
        stress.gap_through_stop_loss_usd
        + stress.stressed_execution_cost_usd,
        stress.liquidity_shock_loss_usd
        + stress.stressed_execution_cost_usd,
        state.base_plausible_loss_usd
        + stress.portfolio_convergence_increment_usd,
        stress.forced_liquidation_loss_usd
        + stress.stressed_execution_cost_usd,
    )
    assert state.stressed_economic_loss_usd == expected
    assert state.margin_occupancy_usd > state.stressed_economic_loss_usd


def test_cel_rejects_gen_c4_provider_risk_binding_drift() -> None:
    envelope = _envelope()
    volume = Decimal("0.01")
    marginal = _marginal(envelope, volume)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="stop-risk binding drift",
    ):
        build_capital_efficient_exposure_state(
            state_id="cel-state-drift",
            decision_at=NOW,
            envelope=envelope,
            executable_volume=volume,
            marginal_evidence=replace(
                marginal,
                incremental_stop_risk_usd=Decimal("999"),
            ),
            stress=_stress(),
        )


def test_cel_rejects_future_stress_evidence() -> None:
    envelope = _envelope()
    volume = Decimal("0.01")

    with pytest.raises(
        CiboCompoundCapitalError,
        match="arrives from the future",
    ):
        build_capital_efficient_exposure_state(
            state_id="cel-state-future",
            decision_at=NOW,
            envelope=envelope,
            executable_volume=volume,
            marginal_evidence=_marginal(envelope, volume),
            stress=replace(
                _stress(),
                observed_at=NOW + timedelta(seconds=1),
                produced_at=NOW + timedelta(seconds=2),
            ),
        )


def test_cel_stress_evidence_cannot_contain_outcome_or_authority() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="pre-outcome research evidence",
    ):
        replace(_stress(), outcome_present=True)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="pre-outcome research evidence",
    ):
        replace(_stress(), productive_authority=True)


def test_cel_does_not_change_cibo_or_risk_authority() -> None:
    envelope = _envelope()
    volume = Decimal("0.01")
    state = build_capital_efficient_exposure_state(
        state_id="cel-state-authority",
        decision_at=NOW,
        envelope=envelope,
        executable_volume=volume,
        marginal_evidence=_marginal(envelope, volume),
        stress=_stress(),
    )
    assert state.sizing_authority is False
    assert state.capital_authority is False
    assert state.risk_authority is False
    assert state.execution_authority is False
