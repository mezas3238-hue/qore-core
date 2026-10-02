from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.shared_regime_transition_intelligence import (
    SharedRegimeHypothesis,
    assess_shared_regime_transition,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedRegimeTransitionState,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryState,
    MarketTransitionObservation,
)

T0 = datetime(2026, 9, 29, 22, 45, tzinfo=UTC)


def _observation(
    minute: int,
    *,
    integrity: int = 10_000,
    trend: int = 8_000,
    momentum: int = 8_000,
    displacement: int = 7_500,
    liquidity: int = 8_000,
    volatility: int = 8_000,
    confirmation: int = 8_000,
    correlation: int = 8_000,
    contradiction: int = 1_500,
    anomaly: int = 1_000,
    uncertainty: int = 1_500,
    opposite: int = 1_000,
) -> MarketTransitionObservation:
    return MarketTransitionObservation(
        as_of=T0 + timedelta(minutes=minute),
        data_integrity_bps=integrity,
        trend_support_bps=trend,
        momentum_bps=momentum,
        displacement_bps=displacement,
        liquidity_capacity_bps=liquidity,
        volatility_stability_bps=volatility,
        cross_market_confirmation_bps=confirmation,
        correlation_stability_bps=correlation,
        contradiction_bps=contradiction,
        anomaly_bps=anomaly,
        uncertainty_bps=uncertainty,
        opposite_pressure_bps=opposite,
    )


def test_regime_engine_preserves_competing_worlds_and_no_authority() -> None:
    assessment = assess_shared_regime_transition(
        tuple(_observation(i) for i in range(4)),
        expected_horizon="30M_RESEARCH",
    )

    assert assessment.state is SharedRegimeTransitionState.STABLE
    assert assessment.trajectory_state is MarketTrajectoryState.HEALTHY
    assert tuple(
        item.hypothesis for item in assessment.competing_hypotheses
    ) == tuple(SharedRegimeHypothesis)
    assert assessment.order_authority is False
    assert assessment.risk_authority is False
    assert assessment.sizing_authority is False
    assert assessment.execution_authority is False


def test_regime_engine_detects_structural_decoupling() -> None:
    observations = (
        _observation(0),
        _observation(1, confirmation=7_500, correlation=7_500),
        _observation(2, confirmation=5_000, correlation=5_000),
        _observation(
            3,
            confirmation=2_500,
            correlation=2_500,
            contradiction=7_000,
            trend=6_000,
            momentum=5_500,
        ),
    )
    assessment = assess_shared_regime_transition(
        observations,
        expected_horizon="30M_RESEARCH",
    )

    assert assessment.state is (
        SharedRegimeTransitionState.STRUCTURAL_DECOUPLING
    )
    assert assessment.relationship_decay_bps >= 5_000


def test_regime_engine_can_fail_to_insufficient() -> None:
    assessment = assess_shared_regime_transition(
        (
            _observation(0, integrity=7_000),
            _observation(1, integrity=7_000),
        ),
        expected_horizon="30M_RESEARCH",
    )

    assert assessment.state is SharedRegimeTransitionState.INSUFFICIENT
    assert assessment.trajectory_state is MarketTrajectoryState.INSUFFICIENT


def test_competing_hypotheses_retain_unknown_world() -> None:
    observations = tuple(
        _observation(
            i,
            integrity=8_000,
            uncertainty=8_500,
            anomaly=7_000,
        )
        for i in range(4)
    )
    assessment = assess_shared_regime_transition(observations)

    unknown = next(
        item
        for item in assessment.competing_hypotheses
        if item.hypothesis
        is SharedRegimeHypothesis.UNKNOWN_INSUFFICIENT
    )
    assert unknown.support_bps >= 5_000
