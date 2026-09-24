"""Dynamic market deterioration and recovery intelligence for Shared Core.

The model is intentionally trader-agnostic.  It reasons over an ordered causal
trajectory of market observations and produces continuous deterioration /
recovery evidence plus an explainable state.  It never consumes PnL, trade
outcomes, strategy-specific primitives, sizing, capital or execution state.

Continuous evidence is primary.  The discrete state is only a compact summary
for adapters and downstream cognition.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class MarketTrajectoryState(StrEnum):
    HEALTHY = "HEALTHY"
    WEAKENING = "WEAKENING"
    DIVERGING = "DIVERGING"
    DETERIORATING = "DETERIORATING"
    FAILURE = "FAILURE"
    STABILIZING = "STABILIZING"
    RECOVERING = "RECOVERING"
    INSUFFICIENT = "INSUFFICIENT"


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _check_bps(name: str, value: int) -> None:
    if not 0 <= value <= 10_000:
        raise ValueError(f"{name} must be within 0..10000")


def _mean(values: Sequence[int]) -> int:
    if not values:
        raise ValueError("mean requires at least one value")
    return sum(values) // len(values)


def _clamp_bps(value: int) -> int:
    return max(0, min(10_000, value))


@dataclass(frozen=True, slots=True)
class MarketTransitionObservation:
    as_of: datetime
    data_integrity_bps: int
    trend_support_bps: int
    momentum_bps: int
    displacement_bps: int
    liquidity_capacity_bps: int
    volatility_stability_bps: int
    cross_market_confirmation_bps: int
    correlation_stability_bps: int
    contradiction_bps: int
    anomaly_bps: int
    uncertainty_bps: int
    opposite_pressure_bps: int

    def __post_init__(self) -> None:
        _iso(self.as_of)
        for name in (
            "data_integrity_bps",
            "trend_support_bps",
            "momentum_bps",
            "displacement_bps",
            "liquidity_capacity_bps",
            "volatility_stability_bps",
            "cross_market_confirmation_bps",
            "correlation_stability_bps",
            "contradiction_bps",
            "anomaly_bps",
            "uncertainty_bps",
            "opposite_pressure_bps",
        ):
            _check_bps(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class DynamicTransitionPolicy:
    minimum_observations: int = 4
    minimum_integrity_bps: int = 7_500
    weakening_velocity_bps: int = 650
    deterioration_velocity_bps: int = 900
    failure_velocity_bps: int = 1_300
    deterioration_pressure_bps: int = 6_000
    failure_pressure_bps: int = 7_400
    divergence_confirmation_bps: int = 3_750
    divergence_correlation_bps: int = 3_750
    recovery_velocity_bps: int = 900
    recovery_support_bps: int = 5_800
    persistence_bps: int = 5_500

    def __post_init__(self) -> None:
        if self.minimum_observations < 3:
            raise ValueError("minimum_observations must be at least 3")
        for name in (
            "minimum_integrity_bps",
            "weakening_velocity_bps",
            "deterioration_velocity_bps",
            "failure_velocity_bps",
            "deterioration_pressure_bps",
            "failure_pressure_bps",
            "divergence_confirmation_bps",
            "divergence_correlation_bps",
            "recovery_velocity_bps",
            "recovery_support_bps",
            "persistence_bps",
        ):
            _check_bps(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class MarketTrajectoryAssessment:
    as_of: datetime
    state: MarketTrajectoryState
    evidence_count: int
    support_bps: int
    adversity_bps: int
    deterioration_pressure_bps: int
    deterioration_velocity_bps: int
    recovery_velocity_bps: int
    deterioration_persistence_bps: int
    recovery_persistence_bps: int
    reasons: tuple[str, ...]
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    execution_authority: bool = False
    strategy_mutation_authority: bool = False

    def __post_init__(self) -> None:
        _iso(self.as_of)
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")
        for name in (
            "support_bps",
            "adversity_bps",
            "deterioration_pressure_bps",
            "deterioration_velocity_bps",
            "recovery_velocity_bps",
            "deterioration_persistence_bps",
            "recovery_persistence_bps",
        ):
            _check_bps(name, getattr(self, name))
        if (
            self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.execution_authority
            or self.strategy_mutation_authority
        ):
            raise ValueError(
                "Shared transition intelligence cannot carry trading authority"
            )


def _support(observation: MarketTransitionObservation) -> int:
    return _mean(
        (
            observation.trend_support_bps,
            observation.momentum_bps,
            observation.displacement_bps,
            observation.liquidity_capacity_bps,
            observation.volatility_stability_bps,
            observation.cross_market_confirmation_bps,
            observation.correlation_stability_bps,
        )
    )


def _adversity(observation: MarketTransitionObservation) -> int:
    return _mean(
        (
            observation.contradiction_bps,
            observation.anomaly_bps,
            observation.uncertainty_bps,
            observation.opposite_pressure_bps,
            10_000 - observation.cross_market_confirmation_bps,
            10_000 - observation.momentum_bps,
        )
    )


def _pressure(observation: MarketTransitionObservation) -> int:
    support = _support(observation)
    adversity = _adversity(observation)
    return _mean((adversity, 10_000 - support))


def _persistence(values: Sequence[int], *, increasing: bool) -> int:
    if len(values) < 2:
        return 0
    qualifying = 0
    for left, right in zip(values, values[1:], strict=True):
        if (right > left) if increasing else (right < left):
            qualifying += 1
    return qualifying * 10_000 // (len(values) - 1)


def assess_market_trajectory(
    observations: Sequence[MarketTransitionObservation],
    *,
    policy: DynamicTransitionPolicy | None = None,
) -> MarketTrajectoryAssessment:
    if not observations:
        raise ValueError("at least one market observation is required")
    effective = policy or DynamicTransitionPolicy()

    for left, right in zip(observations, observations[1:], strict=False):
        if right.as_of <= left.as_of:
            raise ValueError(
                "market observations must be strictly increasing and causal"
            )

    latest = observations[-1]
    supports = [_support(item) for item in observations]
    adversities = [_adversity(item) for item in observations]
    pressures = [_pressure(item) for item in observations]
    support = supports[-1]
    adversity = adversities[-1]
    pressure = pressures[-1]

    deterioration_velocity = _clamp_bps(
        max(0, supports[0] - supports[-1])
        + max(0, adversities[-1] - adversities[0])
    )
    recovery_velocity = _clamp_bps(
        max(0, supports[-1] - supports[0])
        + max(0, adversities[0] - adversities[-1])
    )
    deterioration_persistence = _persistence(pressures, increasing=True)
    recovery_persistence = _persistence(pressures, increasing=False)

    reasons: list[str] = []
    insufficient = (
        len(observations) < effective.minimum_observations
        or min(item.data_integrity_bps for item in observations)
        < effective.minimum_integrity_bps
    )

    if insufficient:
        state = MarketTrajectoryState.INSUFFICIENT
        reasons.append("TRAJECTORY_EVIDENCE_INSUFFICIENT")
    elif (
        pressure >= effective.failure_pressure_bps
        and deterioration_velocity >= effective.failure_velocity_bps
        and deterioration_persistence >= effective.persistence_bps
    ):
        state = MarketTrajectoryState.FAILURE
        reasons.extend(
            (
                "ADVERSITY_PRESSURE_EXTREME",
                "DETERIORATION_ACCELERATING",
                "DETERIORATION_PERSISTENT",
            )
        )
    elif (
        pressure >= effective.deterioration_pressure_bps
        and deterioration_velocity >= effective.deterioration_velocity_bps
        and deterioration_persistence >= effective.persistence_bps
    ):
        state = MarketTrajectoryState.DETERIORATING
        reasons.extend(
            (
                "ADVERSITY_PRESSURE_HIGH",
                "DETERIORATION_PERSISTENT",
            )
        )
    elif (
        recovery_velocity >= effective.recovery_velocity_bps
        and recovery_persistence >= effective.persistence_bps
        and support >= effective.recovery_support_bps
    ):
        state = MarketTrajectoryState.RECOVERING
        reasons.extend(
            (
                "SUPPORT_RECOVERING",
                "ADVERSITY_RECEDING",
            )
        )
    elif (
        pressures[0] >= effective.deterioration_pressure_bps
        and recovery_velocity >= effective.weakening_velocity_bps
        and recovery_persistence >= effective.persistence_bps
    ):
        state = MarketTrajectoryState.STABILIZING
        reasons.extend(
            (
                "PRIOR_PRESSURE_HIGH",
                "DETERIORATION_DECELERATING",
            )
        )
    elif (
        latest.cross_market_confirmation_bps
        <= effective.divergence_confirmation_bps
        or latest.correlation_stability_bps
        <= effective.divergence_correlation_bps
    ) and (
        latest.contradiction_bps >= 5_500
        or deterioration_velocity >= effective.weakening_velocity_bps
    ):
        state = MarketTrajectoryState.DIVERGING
        reasons.append("CROSS_MARKET_COHERENCE_DIVERGING")
    elif deterioration_velocity >= effective.weakening_velocity_bps:
        state = MarketTrajectoryState.WEAKENING
        reasons.append("MARKET_SUPPORT_DECAYING")
    else:
        state = MarketTrajectoryState.HEALTHY
        reasons.append("CURRENT_MARKET_SUPPORT_STABLE")

    if latest.anomaly_bps >= 7_000:
        reasons.append("ANOMALY_PRESSURE_HIGH")
    if latest.uncertainty_bps >= 6_500:
        reasons.append("UNCERTAINTY_HIGH")
    if latest.opposite_pressure_bps >= 6_500:
        reasons.append("OPPOSITE_PRESSURE_HIGH")
    if latest.cross_market_confirmation_bps <= 3_500:
        reasons.append("CROSS_MARKET_CONFIRMATION_WEAK")

    return MarketTrajectoryAssessment(
        as_of=latest.as_of,
        state=state,
        evidence_count=len(observations),
        support_bps=support,
        adversity_bps=adversity,
        deterioration_pressure_bps=pressure,
        deterioration_velocity_bps=deterioration_velocity,
        recovery_velocity_bps=recovery_velocity,
        deterioration_persistence_bps=deterioration_persistence,
        recovery_persistence_bps=recovery_persistence,
        reasons=tuple(dict.fromkeys(reasons)),
    )
