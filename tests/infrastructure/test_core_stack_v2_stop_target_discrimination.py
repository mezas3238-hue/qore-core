from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2 import (
    CompetingFutureAssessment,
    CompetingFutureState,
    MarketEnvironmentAssessment,
    MarketEnvironmentState,
    MarketTrajectoryAssessment,
    MarketTrajectoryState,
    PositionPathAssessment,
    PositionPathState,
    StopTargetHypothesis,
    assess_stop_target_path,
    superintelligence_freeze_contract,
)
from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    FutureGeometryAssessment,
    FutureGeometryState,
    HorizonGeometryState,
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
        market_support_bps=8000 if supportive else 2200,
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
        support_bps=8200 if supportive else 1800,
        adversity_bps=1800 if supportive else 8200,
        deterioration_pressure_bps=1800 if supportive else 8200,
        deterioration_velocity_bps=1800 if supportive else 7800,
        recovery_velocity_bps=7800 if supportive else 1800,
        deterioration_persistence_bps=1800 if supportive else 7800,
        recovery_persistence_bps=7800 if supportive else 1800,
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
    recovery = state is CompetingFutureState.RECOVERABLE_ADVERSE
    supportive = state is CompetingFutureState.SUPPORTIVE
    return CompetingFutureAssessment(
        as_of=NOW,
        state=state,
        horizon_votes=(),
        terminal_horizon_count=3 if terminal else 0,
        recovery_horizon_count=3 if recovery or supportive else 0,
        conflicted_horizon_count=0 if state is not CompetingFutureState.CONFLICTED else 3,
        terminal_evidence_bps=8500 if terminal else 1800,
        recovery_evidence_bps=8500 if recovery or supportive else 1800,
        separation_margin_bps=6500,
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
        path_support_bps=8200 if target or recovery else 1800,
        adverse_dominance_bps=8200 if terminal else 1800,
        adverse_persistence_bps=7800 if terminal else 1800,
        recovery_persistence_bps=7800 if recovery else 1800,
        winner_protection_bps=8200 if target or recovery else 1800,
        terminal_failure_risk_bps=8500 if terminal else 1800,
        reasons=("TEST",),
    )


def test_stop_likely_requires_terminal_future_and_current_market_relation() -> None:
    result = assess_stop_target_path(
        _environment(MarketEnvironmentState.DEFENSIVE),
        _trajectory(MarketTrajectoryState.FAILURE),
        _geometry(FutureGeometryState.TERMINAL_COLLAPSE),
        _futures(CompetingFutureState.TERMINAL_ADVERSE),
        path=_path(PositionPathState.FAILURE_RISK),
    )

    assert result.hypothesis is StopTargetHypothesis.STOP_LIKELY
    assert result.terminal_relation_count >= 4
    assert result.outcome_used is False
    assert result.future_market_used is False
    assert result.stop_mutation_authority is False
    assert result.target_mutation_authority is False
    assert result.sizing_authority is False



def test_broad_terminal_context_without_failed_path_is_only_stop_forming() -> None:
    result = assess_stop_target_path(
        _environment(MarketEnvironmentState.DEFENSIVE),
        _trajectory(MarketTrajectoryState.FAILURE),
        _geometry(FutureGeometryState.TERMINAL_COLLAPSE),
        _futures(CompetingFutureState.TERMINAL_ADVERSE),
    )

    assert result.hypothesis is StopTargetHypothesis.STOP_FORMING
    assert result.stop_mutation_authority is False
    assert result.target_mutation_authority is False

def test_target_likely_requires_supportive_future_and_current_market_relation() -> None:
    result = assess_stop_target_path(
        _environment(MarketEnvironmentState.SUPPORTIVE),
        _trajectory(MarketTrajectoryState.HEALTHY),
        _geometry(FutureGeometryState.SUPPORTIVE_CONTINUATION),
        _futures(CompetingFutureState.SUPPORTIVE),
        path=_path(PositionPathState.FAVORABLE_EXPANSION),
    )

    assert result.hypothesis is StopTargetHypothesis.TARGET_LIKELY
    assert result.target_relation_count >= 4
    assert result.target_mutation_authority is False



def test_supportive_preentry_context_is_not_enough_to_call_target() -> None:
    result = assess_stop_target_path(
        _environment(MarketEnvironmentState.SUPPORTIVE),
        _trajectory(MarketTrajectoryState.HEALTHY),
        _geometry(FutureGeometryState.SUPPORTIVE_CONTINUATION),
        _futures(CompetingFutureState.SUPPORTIVE),
    )

    assert result.hypothesis is StopTargetHypothesis.CONTESTED
    assert result.target_mutation_authority is False

def test_recoverable_future_vetoes_false_stop_classification() -> None:
    result = assess_stop_target_path(
        _environment(MarketEnvironmentState.ADVERSE_FORMING),
        _trajectory(MarketTrajectoryState.DETERIORATING),
        _geometry(FutureGeometryState.RECOVERABLE_ADVERSITY),
        _futures(CompetingFutureState.RECOVERABLE_ADVERSE),
        path=_path(PositionPathState.HEALTHY_PULLBACK),
    )

    assert result.hypothesis is StopTargetHypothesis.RECOVERABLE
    assert "STOP_HYPOTHESIS_VETOED_BY_RECOVERY" in result.reasons


def test_conflicting_future_shape_remains_contested() -> None:
    result = assess_stop_target_path(
        _environment(MarketEnvironmentState.FRAGILE),
        _trajectory(MarketTrajectoryState.DIVERGING),
        _geometry(FutureGeometryState.CONFLICTED),
        _futures(CompetingFutureState.CONFLICTED),
        path=_path(PositionPathState.CONTESTED),
    )

    assert result.hypothesis is StopTargetHypothesis.CONTESTED


def test_phase_one_pass_unlocks_research_only_management() -> None:
    contract = superintelligence_freeze_contract()
    path = contract["shared_essential_intelligence"]["causal_position_path_asymmetry"]
    management = contract["shared_essential_intelligence"]["realtime_trade_management"]

    assert path["must_distinguish_possible_stop_from_possible_target_before_management"] is True
    assert path["possible_stop_possible_target_discrimination_is_phase_1_primary_task"] is True
    assert path["classification_must_be_shadow_only_until_phase_1_passes"] is True
    assert management["unlock_requires_possible_stop_possible_target_discrimination_pass"] is True
    assert management["trailing_and_target_extension_forbidden_for_phase_1_primary_claim"] is True
    assert management["may_contribute_to_current_primary_dd_claim"] is True
    assert management["research_status"] == "ACTIVE_RESEARCH_ONLY_AFTER_PHASE_1_CONSUMED_PASS"
