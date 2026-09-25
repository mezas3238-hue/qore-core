from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.architecture_freeze import (
    superintelligence_freeze_contract,
)
from qore.infrastructure.core_stack_v2.competing_future_intelligence import (
    CompetingFutureAssessment,
    CompetingFutureState,
)
from qore.infrastructure.core_stack_v2.competing_risk_path_core import (
    assess_competing_risk_path,
)
from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentAssessment,
    MarketEnvironmentState,
)
from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    FutureGeometryAssessment,
    FutureGeometryState,
    HorizonGeometryState,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathAssessment,
    PositionPathState,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryAssessment,
    MarketTrajectoryState,
)

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _environment(state: MarketEnvironmentState) -> MarketEnvironmentAssessment:
    supportive = state in {
        MarketEnvironmentState.SUPPORTIVE,
        MarketEnvironmentState.RESTORED,
        MarketEnvironmentState.STABILIZING,
    }
    return MarketEnvironmentAssessment(
        as_of=NOW,
        state=state,
        evidence_count=8,
        market_support_bps=8200 if supportive else 2200,
        adverse_environment_bps=1800 if supportive else 8200,
        adverse_velocity_bps=1800 if supportive else 7800,
        recovery_velocity_bps=7600 if supportive else 1800,
        adverse_persistence_bps=1800 if supportive else 7800,
        recovery_persistence_bps=7600 if supportive else 1800,
        cross_market_fragility_bps=1800 if supportive else 7600,
        structural_fragility_bps=1800 if supportive else 7600,
        reasons=("TEST",),
    )


def _trajectory(state: MarketTrajectoryState) -> MarketTrajectoryAssessment:
    supportive = state in {
        MarketTrajectoryState.HEALTHY,
        MarketTrajectoryState.RECOVERING,
        MarketTrajectoryState.STABILIZING,
    }
    return MarketTrajectoryAssessment(
        as_of=NOW,
        state=state,
        evidence_count=8,
        support_bps=8300 if supportive else 1700,
        adversity_bps=1700 if supportive else 8300,
        deterioration_pressure_bps=1700 if supportive else 8300,
        deterioration_velocity_bps=1700 if supportive else 7800,
        recovery_velocity_bps=7800 if supportive else 1700,
        deterioration_persistence_bps=1700 if supportive else 7800,
        recovery_persistence_bps=7800 if supportive else 1700,
        reasons=("TEST",),
    )


def _geometry(state: FutureGeometryState) -> FutureGeometryAssessment:
    broad = (
        HorizonGeometryState.COLLAPSING
        if state is FutureGeometryState.TERMINAL_COLLAPSE
        else HorizonGeometryState.RECOVERING
        if state is FutureGeometryState.RECOVERABLE_ADVERSITY
        else HorizonGeometryState.RESILIENT
        if state is FutureGeometryState.SUPPORTIVE_CONTINUATION
        else HorizonGeometryState.CONFLICTED
    )
    return FutureGeometryAssessment(
        as_of=NOW,
        state=state,
        horizons=(),
        collapse_horizon_count=int(state is FutureGeometryState.TERMINAL_COLLAPSE),
        recovery_horizon_count=int(state is FutureGeometryState.RECOVERABLE_ADVERSITY),
        resilient_horizon_count=int(state is FutureGeometryState.SUPPORTIVE_CONTINUATION),
        conflicted_horizon_count=int(state is FutureGeometryState.CONFLICTED),
        broad_state=broad,
        fast_state=broad,
        structural_agreement_bps=8500,
        reasons=("TEST",),
    )


def _futures(state: CompetingFutureState) -> CompetingFutureAssessment:
    terminal = state is CompetingFutureState.TERMINAL_ADVERSE
    recovery = state in {
        CompetingFutureState.RECOVERABLE_ADVERSE,
        CompetingFutureState.SUPPORTIVE,
    }
    return CompetingFutureAssessment(
        as_of=NOW,
        state=state,
        horizon_votes=(),
        terminal_horizon_count=3 if terminal else 0,
        recovery_horizon_count=3 if recovery else 0,
        conflicted_horizon_count=3 if state is CompetingFutureState.CONFLICTED else 0,
        terminal_evidence_bps=8800 if terminal else 1600,
        recovery_evidence_bps=8500 if recovery else 1600,
        separation_margin_bps=7000,
        horizon_agreement_bps=8500,
        confidence_bps=8500,
        reasons=("TEST",),
    )


def _path(state: PositionPathState) -> PositionPathAssessment:
    terminal = state in {
        PositionPathState.ADVERSE_DOMINANCE,
        PositionPathState.FAILURE_RISK,
    }
    target = state is PositionPathState.FAVORABLE_EXPANSION
    recovery = state in {
        PositionPathState.HEALTHY_PULLBACK,
        PositionPathState.RECOVERING,
    }
    return PositionPathAssessment(
        as_of=NOW,
        state=state,
        evidence_count=6,
        path_support_bps=8500 if target else 7000 if recovery else 1800,
        adverse_dominance_bps=8500 if terminal else 2000,
        adverse_persistence_bps=8200 if terminal else 1800,
        recovery_persistence_bps=8200 if recovery else 1800,
        winner_protection_bps=8500 if target or recovery else 1800,
        terminal_failure_risk_bps=8800 if terminal else 1800,
        reasons=("TEST",),
    )


def test_preentry_context_cannot_manufacture_target_conviction() -> None:
    result = assess_competing_risk_path(
        _environment(MarketEnvironmentState.SUPPORTIVE),
        _trajectory(MarketTrajectoryState.HEALTHY),
        _geometry(FutureGeometryState.SUPPORTIVE_CONTINUATION),
        _futures(CompetingFutureState.SUPPORTIVE),
    )

    assert result.path_evidence_available is False
    assert result.target_capacity_bps <= 4000
    assert result.target_hazard_proxy_bps <= 3500
    assert result.uncertainty_bps >= 7500
    assert result.calibrated_probability is False


def test_failure_path_makes_stop_hazard_dominate_under_adverse_context() -> None:
    result = assess_competing_risk_path(
        _environment(MarketEnvironmentState.DEFENSIVE),
        _trajectory(MarketTrajectoryState.FAILURE),
        _geometry(FutureGeometryState.TERMINAL_COLLAPSE),
        _futures(CompetingFutureState.TERMINAL_ADVERSE),
        path=_path(PositionPathState.FAILURE_RISK),
    )

    assert result.path_evidence_available is True
    assert result.stop_hazard_proxy_bps >= 7000
    assert result.stop_hazard_proxy_bps > result.target_hazard_proxy_bps
    assert result.separation_margin_bps >= 2500


def test_recoverable_pullback_caps_stop_pressure_and_preserves_recovery() -> None:
    result = assess_competing_risk_path(
        _environment(MarketEnvironmentState.STABILIZING),
        _trajectory(MarketTrajectoryState.RECOVERING),
        _geometry(FutureGeometryState.RECOVERABLE_ADVERSITY),
        _futures(CompetingFutureState.RECOVERABLE_ADVERSE),
        path=_path(PositionPathState.HEALTHY_PULLBACK),
    )

    assert result.stop_pressure_bps <= 5000
    assert result.recovery_strength_bps >= 6500
    assert result.uncertainty_bps >= 6500


def test_favorable_expansion_allows_target_hazard_only_with_path_evidence() -> None:
    result = assess_competing_risk_path(
        _environment(MarketEnvironmentState.SUPPORTIVE),
        _trajectory(MarketTrajectoryState.HEALTHY),
        _geometry(FutureGeometryState.SUPPORTIVE_CONTINUATION),
        _futures(CompetingFutureState.SUPPORTIVE),
        path=_path(PositionPathState.FAVORABLE_EXPANSION),
    )

    assert result.path_evidence_available is True
    assert result.target_hazard_proxy_bps >= 7000
    assert result.target_hazard_proxy_bps > result.stop_hazard_proxy_bps


def test_ccrpc_has_no_management_or_sizing_authority() -> None:
    result = assess_competing_risk_path(
        _environment(MarketEnvironmentState.SUPPORTIVE),
        _trajectory(MarketTrajectoryState.HEALTHY),
        _geometry(FutureGeometryState.SUPPORTIVE_CONTINUATION),
        _futures(CompetingFutureState.SUPPORTIVE),
        path=_path(PositionPathState.FAVORABLE_EXPANSION),
    )

    assert result.outcome_used is False
    assert result.future_market_used is False
    assert result.stop_mutation_authority is False
    assert result.target_mutation_authority is False
    assert result.sizing_authority is False
    assert result.risk_authority is False
    assert result.execution_authority is False


def test_freeze_requires_shadow_competing_risk_path_core() -> None:
    contract = superintelligence_freeze_contract()
    core = contract["shared_essential_intelligence"]["competing_risk_path_core"]

    assert core["required"] is True
    assert core["phase"] == "PHASE_1_SHADOW_ONLY"
    assert core["path_state_is_primary"] is True
    assert core["stop_and_target_are_competing_destinations"] is True
    assert core["recoverable_is_first_class_state"] is True
    assert core["contested_is_first_class_state"] is True
    assert core["target_conviction_requires_favorable_path_evidence"] is True
    assert core["uncalibrated_proxy_must_not_be_called_probability"] is True
    assert core["stop_target_mutation_authority"] is False
