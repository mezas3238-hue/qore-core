from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2 import (
    CausalHorizonSnapshot,
    MarketEnvironmentAssessment,
    MarketEnvironmentState,
    MarketTrajectoryAssessment,
    MarketTrajectoryState,
    ResidentConvergenceState,
    assess_competing_futures,
    assess_resident_convergence,
)
from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    assess_future_geometry,
    build_horizon_geometry,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTransitionObservation,
)

NOW = datetime(2026, 9, 25, 3, 30, tzinfo=UTC)


def _obs(
    minute: int,
    *,
    support: int,
    adverse: int,
) -> MarketTransitionObservation:
    return MarketTransitionObservation(
        as_of=datetime(2026, 9, 25, 3, minute, tzinfo=UTC),
        data_integrity_bps=10_000,
        trend_support_bps=support,
        momentum_bps=support,
        displacement_bps=support,
        liquidity_capacity_bps=support,
        volatility_stability_bps=support,
        cross_market_confirmation_bps=support,
        correlation_stability_bps=support,
        contradiction_bps=adverse,
        anomaly_bps=adverse,
        uncertainty_bps=adverse,
        opposite_pressure_bps=adverse,
    )


def _environment(*, support: int, adverse: int) -> MarketEnvironmentAssessment:
    return MarketEnvironmentAssessment(
        as_of=NOW,
        state=(
            MarketEnvironmentState.DEFENSIVE
            if adverse > support
            else MarketEnvironmentState.RESTORED
        ),
        evidence_count=8,
        market_support_bps=support,
        adverse_environment_bps=adverse,
        adverse_velocity_bps=adverse,
        recovery_velocity_bps=support,
        adverse_persistence_bps=adverse,
        recovery_persistence_bps=support,
        cross_market_fragility_bps=adverse,
        structural_fragility_bps=adverse,
        reasons=("TEST",),
    )


def _trajectory(*, support: int, adverse: int) -> MarketTrajectoryAssessment:
    return MarketTrajectoryAssessment(
        as_of=NOW,
        state=(
            MarketTrajectoryState.FAILURE
            if adverse > support
            else MarketTrajectoryState.RECOVERING
        ),
        evidence_count=8,
        support_bps=support,
        adversity_bps=adverse,
        deterioration_pressure_bps=adverse,
        deterioration_velocity_bps=adverse,
        recovery_velocity_bps=support,
        deterioration_persistence_bps=adverse,
        recovery_persistence_bps=support,
        reasons=("TEST",),
    )


def _future_snapshot(
    minutes: int,
    *,
    support: int,
    adverse: int,
) -> CausalHorizonSnapshot:
    return CausalHorizonSnapshot(
        horizon_minutes=minutes,
        as_of=NOW,
        evidence_count=8,
        data_integrity_bps=10_000,
        support_bps=support,
        adversity_bps=adverse,
        deterioration_velocity_bps=adverse,
        recovery_velocity_bps=support,
        deterioration_persistence_bps=adverse,
        recovery_persistence_bps=support,
        cross_market_confirmation_bps=support,
        cross_market_fragility_bps=adverse,
        structural_fragility_bps=adverse,
        trend_support_bps=support,
        uncertainty_bps=adverse,
    )


def test_resident_convergence_detects_multi_head_terminal_failure() -> None:
    collapse_rows = (
        _obs(28, support=8000, adverse=2000),
        _obs(29, support=1800, adverse=8500),
    )
    geometry = assess_future_geometry(
        (
            build_horizon_geometry(collapse_rows, horizon_minutes=15),
            build_horizon_geometry(collapse_rows, horizon_minutes=60),
        )
    )
    futures = assess_competing_futures(
        tuple(
            _future_snapshot(minutes, support=1800, adverse=8500)
            for minutes in (5, 15, 30, 60)
        )
    )

    result = assess_resident_convergence(
        _environment(support=1800, adverse=8500),
        _trajectory(support=1800, adverse=8500),
        geometry,
        futures,
    )

    assert result.state is ResidentConvergenceState.TERMINAL_FAILURE
    assert result.terminal_vote_count >= 3
    assert result.terminal_risk_bps > result.recovery_strength_bps
    assert result.outcome_used is False
    assert result.future_market_used is False
    assert result.sizing_authority is False
    assert result.execution_authority is False


def test_resident_convergence_protects_recoverable_adversity() -> None:
    recovery_rows = (
        _obs(28, support=2200, adverse=8200),
        _obs(29, support=8200, adverse=1800),
    )
    geometry = assess_future_geometry(
        (
            build_horizon_geometry(recovery_rows, horizon_minutes=15),
            build_horizon_geometry(recovery_rows, horizon_minutes=60),
        )
    )
    futures = assess_competing_futures(
        tuple(
            _future_snapshot(minutes, support=8200, adverse=1800)
            for minutes in (5, 15, 30, 60)
        )
    )

    result = assess_resident_convergence(
        _environment(support=8200, adverse=1800),
        _trajectory(support=8200, adverse=1800),
        geometry,
        futures,
    )

    assert result.state in {
        ResidentConvergenceState.RECOVERABLE_ADVERSITY,
        ResidentConvergenceState.SUPPORTIVE_CONTINUATION,
    }
    assert result.recovery_strength_bps > result.terminal_risk_bps
    assert result.terminal_vote_count < result.recovery_vote_count + result.support_vote_count
