"""Causal adverse-market environment intelligence for Shared Core.

This module operates above an individual setup or position. It observes a
causal sequence of generic market conditions and asks whether the broader
environment is becoming fragile, adverse, defensive, or restored.

It is intentionally trader-agnostic and outcome-blind at runtime: no PnL,
trade result, loss streak, sizing, capital, order, or execution data is
accepted. Realized outcomes may be used later by offline labs only to evaluate
whether the market-first environment state was useful.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class MarketEnvironmentState(StrEnum):
    SUPPORTIVE = "SUPPORTIVE"
    FRAGILE = "FRAGILE"
    DEGRADING = "DEGRADING"
    ADVERSE_FORMING = "ADVERSE_FORMING"
    DEFENSIVE = "DEFENSIVE"
    STABILIZING = "STABILIZING"
    RESTORED = "RESTORED"
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


def _persistence(values: Sequence[int], *, increasing: bool) -> int:
    if len(values) < 2:
        return 0
    qualifying = 0
    for left, right in zip(values, values[1:], strict=False):
        if (right > left) if increasing else (right < left):
            qualifying += 1
    return qualifying * 10_000 // (len(values) - 1)


def _clamp(value: int) -> int:
    return max(0, min(10_000, value))


@dataclass(frozen=True, slots=True)
class MarketEnvironmentObservation:
    as_of: datetime
    data_integrity_bps: int
    trajectory_support_bps: int
    trajectory_adversity_bps: int
    deterioration_velocity_bps: int
    recovery_velocity_bps: int
    cross_market_breadth_bps: int
    leadership_stability_bps: int
    correlation_stability_bps: int
    volatility_stability_bps: int
    liquidity_stability_bps: int
    regime_stability_bps: int
    anomaly_bps: int
    uncertainty_bps: int
    opposite_pressure_bps: int

    def __post_init__(self) -> None:
        _iso(self.as_of)
        for name in (
            "data_integrity_bps",
            "trajectory_support_bps",
            "trajectory_adversity_bps",
            "deterioration_velocity_bps",
            "recovery_velocity_bps",
            "cross_market_breadth_bps",
            "leadership_stability_bps",
            "correlation_stability_bps",
            "volatility_stability_bps",
            "liquidity_stability_bps",
            "regime_stability_bps",
            "anomaly_bps",
            "uncertainty_bps",
            "opposite_pressure_bps",
        ):
            _check_bps(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class MarketEnvironmentPolicy:
    minimum_observations: int = 5
    minimum_integrity_bps: int = 7_500
    fragile_pressure_bps: int = 4_500
    degrading_pressure_bps: int = 5_500
    adverse_forming_pressure_bps: int = 6_300
    defensive_pressure_bps: int = 7_200
    persistence_bps: int = 6_000
    recovery_support_bps: int = 6_200
    recovery_velocity_bps: int = 850
    restored_pressure_bps: int = 3_800

    def __post_init__(self) -> None:
        if self.minimum_observations < 4:
            raise ValueError("minimum_observations must be at least 4")
        for name in (
            "minimum_integrity_bps",
            "fragile_pressure_bps",
            "degrading_pressure_bps",
            "adverse_forming_pressure_bps",
            "defensive_pressure_bps",
            "persistence_bps",
            "recovery_support_bps",
            "recovery_velocity_bps",
            "restored_pressure_bps",
        ):
            _check_bps(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class MarketEnvironmentAssessment:
    as_of: datetime
    state: MarketEnvironmentState
    evidence_count: int
    market_support_bps: int
    adverse_environment_bps: int
    adverse_velocity_bps: int
    recovery_velocity_bps: int
    adverse_persistence_bps: int
    recovery_persistence_bps: int
    cross_market_fragility_bps: int
    structural_fragility_bps: int
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
            "market_support_bps",
            "adverse_environment_bps",
            "adverse_velocity_bps",
            "recovery_velocity_bps",
            "adverse_persistence_bps",
            "recovery_persistence_bps",
            "cross_market_fragility_bps",
            "structural_fragility_bps",
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
                "Shared environment intelligence cannot carry trading authority"
            )


def _support(observation: MarketEnvironmentObservation) -> int:
    return _mean(
        (
            observation.trajectory_support_bps,
            observation.cross_market_breadth_bps,
            observation.leadership_stability_bps,
            observation.correlation_stability_bps,
            observation.volatility_stability_bps,
            observation.liquidity_stability_bps,
            observation.regime_stability_bps,
            10_000 - observation.uncertainty_bps,
        )
    )


def _cross_market_fragility(observation: MarketEnvironmentObservation) -> int:
    return _mean(
        (
            10_000 - observation.cross_market_breadth_bps,
            10_000 - observation.leadership_stability_bps,
            10_000 - observation.correlation_stability_bps,
        )
    )


def _structural_fragility(observation: MarketEnvironmentObservation) -> int:
    return _mean(
        (
            observation.trajectory_adversity_bps,
            observation.deterioration_velocity_bps,
            10_000 - observation.volatility_stability_bps,
            10_000 - observation.liquidity_stability_bps,
            10_000 - observation.regime_stability_bps,
            observation.anomaly_bps,
            observation.uncertainty_bps,
            observation.opposite_pressure_bps,
        )
    )


def _pressure(observation: MarketEnvironmentObservation) -> int:
    return _mean(
        (
            _cross_market_fragility(observation),
            _structural_fragility(observation),
            10_000 - _support(observation),
        )
    )


def assess_market_environment(
    observations: Sequence[MarketEnvironmentObservation],
    *,
    policy: MarketEnvironmentPolicy | None = None,
) -> MarketEnvironmentAssessment:
    if not observations:
        raise ValueError("at least one market environment observation is required")
    effective = policy or MarketEnvironmentPolicy()

    for left, right in zip(observations, observations[1:], strict=False):
        if right.as_of <= left.as_of:
            raise ValueError(
                "market environment observations must be strictly increasing "
                "and causal"
            )

    latest = observations[-1]
    supports = [_support(item) for item in observations]
    pressures = [_pressure(item) for item in observations]
    support = supports[-1]
    pressure = pressures[-1]
    adverse_velocity = _clamp(
        max(0, pressures[-1] - pressures[0])
        + max(0, supports[0] - supports[-1])
    )
    recovery_velocity = _clamp(
        max(0, pressures[0] - pressures[-1])
        + max(0, supports[-1] - supports[0])
        + latest.recovery_velocity_bps
    )
    adverse_persistence = _persistence(pressures, increasing=True)
    recovery_persistence = _persistence(pressures, increasing=False)
    cross_fragility = _cross_market_fragility(latest)
    structural_fragility = _structural_fragility(latest)

    reasons: list[str] = []
    insufficient = (
        len(observations) < effective.minimum_observations
        or min(item.data_integrity_bps for item in observations)
        < effective.minimum_integrity_bps
    )
    if insufficient:
        state = MarketEnvironmentState.INSUFFICIENT
        reasons.append("ENVIRONMENT_EVIDENCE_INSUFFICIENT")
    elif (
        pressure >= effective.defensive_pressure_bps
        and adverse_persistence >= effective.persistence_bps
    ):
        state = MarketEnvironmentState.DEFENSIVE
        reasons.extend(
            (
                "ADVERSE_ENVIRONMENT_PERSISTENT",
                "MULTI_DIMENSIONAL_MARKET_FRAGILITY_HIGH",
            )
        )
    elif (
        pressure >= effective.adverse_forming_pressure_bps
        and adverse_persistence >= effective.persistence_bps
    ):
        state = MarketEnvironmentState.ADVERSE_FORMING
        reasons.extend(
            (
                "ADVERSE_ENVIRONMENT_FORMING",
                "MARKET_DETERIORATION_PERSISTENT",
            )
        )
    elif (
        recovery_velocity >= effective.recovery_velocity_bps
        and recovery_persistence >= effective.persistence_bps
        and support >= effective.recovery_support_bps
    ):
        if pressure <= effective.restored_pressure_bps:
            state = MarketEnvironmentState.RESTORED
            reasons.extend(
                (
                    "MARKET_SUPPORT_RESTORED",
                    "ADVERSE_ENVIRONMENT_RECEDING",
                )
            )
        else:
            state = MarketEnvironmentState.STABILIZING
            reasons.extend(
                (
                    "MARKET_STABILIZING",
                    "RECOVERY_EVIDENCE_BUILDING",
                )
            )
    elif pressure >= effective.degrading_pressure_bps:
        state = MarketEnvironmentState.DEGRADING
        reasons.append("MARKET_ENVIRONMENT_DEGRADING")
    elif pressure >= effective.fragile_pressure_bps:
        state = MarketEnvironmentState.FRAGILE
        reasons.append("MARKET_ENVIRONMENT_FRAGILE")
    else:
        state = MarketEnvironmentState.SUPPORTIVE
        reasons.append("MARKET_ENVIRONMENT_SUPPORTIVE")

    if cross_fragility >= 6_000:
        reasons.append("CROSS_MARKET_FRAGILITY_HIGH")
    if structural_fragility >= 6_000:
        reasons.append("STRUCTURAL_FRAGILITY_HIGH")
    if latest.anomaly_bps >= 7_000:
        reasons.append("ANOMALY_CLUSTER_HIGH")
    if latest.uncertainty_bps >= 6_500:
        reasons.append("UNCERTAINTY_HIGH")
    if latest.opposite_pressure_bps >= 6_500:
        reasons.append("OPPOSITE_PRESSURE_HIGH")

    return MarketEnvironmentAssessment(
        as_of=latest.as_of,
        state=state,
        evidence_count=len(observations),
        market_support_bps=support,
        adverse_environment_bps=pressure,
        adverse_velocity_bps=adverse_velocity,
        recovery_velocity_bps=recovery_velocity,
        adverse_persistence_bps=adverse_persistence,
        recovery_persistence_bps=recovery_persistence,
        cross_market_fragility_bps=cross_fragility,
        structural_fragility_bps=structural_fragility,
        reasons=tuple(dict.fromkeys(reasons)),
    )
