from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    FutureGeometryState,
    HorizonGeometryState,
    assess_future_geometry,
    build_horizon_geometry,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTransitionObservation,
)


def _obs(
    minute: int,
    *,
    trend: int,
    momentum: int,
    displacement: int,
    liquidity: int,
    volatility: int,
    confirmation: int,
    correlation: int,
    contradiction: int,
    anomaly: int,
    uncertainty: int,
    opposite: int,
) -> MarketTransitionObservation:
    return MarketTransitionObservation(
        as_of=datetime(2026, 9, 24, 14, minute, tzinfo=UTC),
        data_integrity_bps=10_000,
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


def test_future_geometry_detects_structural_collapse() -> None:
    rows = (
        _obs(
            0, trend=7000, momentum=7000, displacement=7000, liquidity=7000,
            volatility=7000, confirmation=7000, correlation=7000,
            contradiction=3000, anomaly=3000, uncertainty=3000, opposite=3000,
        ),
        _obs(
            1, trend=4000, momentum=3500, displacement=3500, liquidity=3500,
            volatility=4000, confirmation=3500, correlation=3500,
            contradiction=6500, anomaly=6500, uncertainty=6000, opposite=7000,
        ),
    )
    horizon = build_horizon_geometry(rows, horizon_minutes=15)

    assert horizon.state is HorizonGeometryState.COLLAPSING
    assert horizon.support_weakening_count > horizon.support_improving_count
    assert horizon.adversity_rising_count > horizon.adversity_falling_count


def test_future_geometry_detects_recovery_shape() -> None:
    rows = (
        _obs(
            0, trend=3500, momentum=3500, displacement=3500, liquidity=3500,
            volatility=4000, confirmation=3500, correlation=3500,
            contradiction=7000, anomaly=6500, uncertainty=6000, opposite=7000,
        ),
        _obs(
            1, trend=6500, momentum=7000, displacement=6800, liquidity=6500,
            volatility=6500, confirmation=7000, correlation=7000,
            contradiction=3500, anomaly=3000, uncertainty=3500, opposite=3000,
        ),
    )
    horizon = build_horizon_geometry(rows, horizon_minutes=30)

    assert horizon.state is HorizonGeometryState.RECOVERING
    assert horizon.recovery_core_count > horizon.terminal_core_count


def test_future_geometry_separates_fast_collapse_from_broad_recovery() -> None:
    collapse = build_horizon_geometry(
        (
            _obs(
                0, trend=7000, momentum=7000, displacement=7000, liquidity=7000,
                volatility=7000, confirmation=7000, correlation=7000,
                contradiction=3000, anomaly=3000, uncertainty=3000, opposite=3000,
            ),
            _obs(
                1, trend=4000, momentum=3500, displacement=3500, liquidity=3500,
                volatility=4000, confirmation=3500, correlation=3500,
                contradiction=6500, anomaly=6500, uncertainty=6000, opposite=7000,
            ),
        ),
        horizon_minutes=5,
    )
    recovery = build_horizon_geometry(
        (
            _obs(
                0, trend=3500, momentum=3500, displacement=3500, liquidity=3500,
                volatility=4000, confirmation=3500, correlation=3500,
                contradiction=7000, anomaly=6500, uncertainty=6000, opposite=7000,
            ),
            _obs(
                1, trend=6500, momentum=7000, displacement=6800, liquidity=6500,
                volatility=6500, confirmation=7000, correlation=7000,
                contradiction=3500, anomaly=3000, uncertainty=3500, opposite=3000,
            ),
        ),
        horizon_minutes=60,
    )

    result = assess_future_geometry((collapse, recovery))

    assert result.state is FutureGeometryState.RECOVERABLE_ADVERSITY
    assert "FAST_COLLAPSE_PRESENT" in result.reasons
    assert result.outcome_used is False
    assert result.sizing_authority is False


def test_future_geometry_does_not_force_conflicted_future() -> None:
    conflicted = build_horizon_geometry(
        (
            _obs(
                0, trend=5000, momentum=5000, displacement=5000, liquidity=5000,
                volatility=5000, confirmation=5000, correlation=5000,
                contradiction=5000, anomaly=5000, uncertainty=5000, opposite=5000,
            ),
            _obs(
                1, trend=5000, momentum=5000, displacement=5000, liquidity=5000,
                volatility=5000, confirmation=5000, correlation=5000,
                contradiction=5000, anomaly=5000, uncertainty=5000, opposite=5000,
            ),
        ),
        horizon_minutes=15,
    )

    second = build_horizon_geometry(
        (
            _obs(
                0, trend=5000, momentum=5000, displacement=5000, liquidity=5000,
                volatility=5000, confirmation=5000, correlation=5000,
                contradiction=5000, anomaly=5000, uncertainty=5000, opposite=5000,
            ),
            _obs(
                1, trend=5000, momentum=5000, displacement=5000, liquidity=5000,
                volatility=5000, confirmation=5000, correlation=5000,
                contradiction=5000, anomaly=5000, uncertainty=5000, opposite=5000,
            ),
        ),
        horizon_minutes=30,
    )

    result = assess_future_geometry((conflicted, second))

    assert result.state is FutureGeometryState.CONFLICTED
