"""Multi-axis causal future geometry for Shared Core.

This layer preserves the shape of the market state instead of compressing many
causal dimensions into one support/adversity average.

It compares, horizon by horizon:
- trend support
- momentum
- displacement
- liquidity capacity
- volatility stability
- cross-market confirmation
- correlation stability
against:
- contradiction
- anomaly
- uncertainty
- opposite pressure

The result is a causal structural hypothesis only. It never receives outcomes,
PnL, sizing, risk budgets, order quantity, stops, targets or execution state.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTransitionObservation,
)


class AxisDirection(StrEnum):
    RISING = "RISING"
    FALLING = "FALLING"
    FLAT = "FLAT"


class HorizonGeometryState(StrEnum):
    COLLAPSING = "COLLAPSING"
    RECOVERING = "RECOVERING"
    RESILIENT = "RESILIENT"
    CONFLICTED = "CONFLICTED"


class FutureGeometryState(StrEnum):
    TERMINAL_COLLAPSE = "TERMINAL_COLLAPSE"
    RECOVERABLE_ADVERSITY = "RECOVERABLE_ADVERSITY"
    SUPPORTIVE_CONTINUATION = "SUPPORTIVE_CONTINUATION"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"


_SUPPORT_AXES = (
    "trend_support_bps",
    "momentum_bps",
    "displacement_bps",
    "liquidity_capacity_bps",
    "volatility_stability_bps",
    "cross_market_confirmation_bps",
    "correlation_stability_bps",
)

_ADVERSE_AXES = (
    "contradiction_bps",
    "anomaly_bps",
    "uncertainty_bps",
    "opposite_pressure_bps",
)


@dataclass(frozen=True, slots=True)
class AxisGeometry:
    name: str
    start_bps: int
    end_bps: int
    direction: AxisDirection


@dataclass(frozen=True, slots=True)
class CausalHorizonGeometry:
    horizon_minutes: int
    as_of: datetime
    evidence_count: int
    data_integrity_bps: int
    state: HorizonGeometryState
    support_axes: tuple[AxisGeometry, ...]
    adverse_axes: tuple[AxisGeometry, ...]
    supportive_level_count: int
    adverse_level_count: int
    support_improving_count: int
    support_weakening_count: int
    adversity_rising_count: int
    adversity_falling_count: int
    recovery_core_count: int
    terminal_core_count: int

    def __post_init__(self) -> None:
        if self.horizon_minutes <= 0:
            raise ValueError("horizon_minutes must be positive")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.evidence_count <= 0:
            raise ValueError("evidence_count must be positive")
        if not 0 <= self.data_integrity_bps <= 10_000:
            raise ValueError("data_integrity_bps must be within 0..10000")


@dataclass(frozen=True, slots=True)
class FutureGeometryAssessment:
    as_of: datetime
    state: FutureGeometryState
    horizons: tuple[CausalHorizonGeometry, ...]
    collapse_horizon_count: int
    recovery_horizon_count: int
    resilient_horizon_count: int
    conflicted_horizon_count: int
    broad_state: HorizonGeometryState
    fast_state: HorizonGeometryState
    structural_agreement_bps: int
    reasons: tuple[str, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if not 0 <= self.structural_agreement_bps <= 10_000:
            raise ValueError("structural_agreement_bps must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("future geometry cannot use outcomes or trading authority")


def _direction(start: int, end: int) -> AxisDirection:
    if end > start:
        return AxisDirection.RISING
    if end < start:
        return AxisDirection.FALLING
    return AxisDirection.FLAT


def _axis_geometry(
    observations: Sequence[MarketTransitionObservation],
    name: str,
) -> AxisGeometry:
    start = int(getattr(observations[0], name))
    end = int(getattr(observations[-1], name))
    return AxisGeometry(
        name=name,
        start_bps=start,
        end_bps=end,
        direction=_direction(start, end),
    )


def build_horizon_geometry(
    observations: Sequence[MarketTransitionObservation],
    *,
    horizon_minutes: int,
) -> CausalHorizonGeometry:
    if not observations:
        raise ValueError("at least one causal observation is required")
    for left, right in zip(observations, observations[1:], strict=False):
        if right.as_of <= left.as_of:
            raise ValueError("observations must be strictly increasing and causal")

    support = tuple(
        _axis_geometry(observations, name) for name in _SUPPORT_AXES
    )
    adverse = tuple(
        _axis_geometry(observations, name) for name in _ADVERSE_AXES
    )

    supportive_level = sum(axis.end_bps > 5_000 for axis in support)
    adverse_level = sum(axis.end_bps > 5_000 for axis in adverse)
    improving = sum(axis.direction is AxisDirection.RISING for axis in support)
    weakening = sum(axis.direction is AxisDirection.FALLING for axis in support)
    adverse_rising = sum(axis.direction is AxisDirection.RISING for axis in adverse)
    adverse_falling = sum(axis.direction is AxisDirection.FALLING for axis in adverse)

    latest = observations[-1]
    recovery_core = sum(
        (
            latest.momentum_bps > 5_000,
            latest.displacement_bps > 5_000,
            latest.liquidity_capacity_bps > 5_000,
            latest.cross_market_confirmation_bps > 5_000,
            latest.correlation_stability_bps > 5_000,
        )
    )
    terminal_core = sum(
        (
            latest.opposite_pressure_bps > 5_000,
            latest.contradiction_bps > 5_000,
            latest.anomaly_bps > 5_000,
            latest.liquidity_capacity_bps < 5_000,
            latest.cross_market_confirmation_bps < 5_000,
            latest.correlation_stability_bps < 5_000,
        )
    )

    collapse_shape = (
        weakening > improving
        and adverse_rising > adverse_falling
        and terminal_core > recovery_core
    )
    recovery_shape = (
        improving > weakening
        and adverse_falling >= adverse_rising
        and recovery_core > terminal_core
    )
    resilient_shape = (
        recovery_core > terminal_core
        and supportive_level >= 4
        and adverse_level <= 2
    )

    if collapse_shape:
        state = HorizonGeometryState.COLLAPSING
    elif recovery_shape:
        state = HorizonGeometryState.RECOVERING
    elif resilient_shape:
        state = HorizonGeometryState.RESILIENT
    else:
        state = HorizonGeometryState.CONFLICTED

    return CausalHorizonGeometry(
        horizon_minutes=horizon_minutes,
        as_of=latest.as_of.astimezone(UTC),
        evidence_count=len(observations),
        data_integrity_bps=min(item.data_integrity_bps for item in observations),
        state=state,
        support_axes=support,
        adverse_axes=adverse,
        supportive_level_count=supportive_level,
        adverse_level_count=adverse_level,
        support_improving_count=improving,
        support_weakening_count=weakening,
        adversity_rising_count=adverse_rising,
        adversity_falling_count=adverse_falling,
        recovery_core_count=recovery_core,
        terminal_core_count=terminal_core,
    )


def assess_future_geometry(
    horizons: Sequence[CausalHorizonGeometry],
) -> FutureGeometryAssessment:
    if not horizons:
        raise ValueError("at least one horizon is required")

    ordered = tuple(sorted(horizons, key=lambda item: item.horizon_minutes))
    as_of = ordered[0].as_of.astimezone(UTC)
    if any(item.as_of.astimezone(UTC) != as_of for item in ordered):
        raise ValueError("all horizons must share the same causal as_of")
    if len({item.horizon_minutes for item in ordered}) != len(ordered):
        raise ValueError("horizon_minutes must be unique")

    if len(ordered) < 2:
        return FutureGeometryAssessment(
            as_of=as_of,
            state=FutureGeometryState.INSUFFICIENT,
            horizons=ordered,
            collapse_horizon_count=0,
            recovery_horizon_count=0,
            resilient_horizon_count=0,
            conflicted_horizon_count=len(ordered),
            broad_state=ordered[-1].state,
            fast_state=ordered[0].state,
            structural_agreement_bps=0,
            reasons=("MULTI_HORIZON_GEOMETRY_INSUFFICIENT",),
        )

    collapse = sum(
        item.state is HorizonGeometryState.COLLAPSING for item in ordered
    )
    recovery = sum(
        item.state is HorizonGeometryState.RECOVERING for item in ordered
    )
    resilient = sum(
        item.state is HorizonGeometryState.RESILIENT for item in ordered
    )
    conflicted = len(ordered) - collapse - recovery - resilient

    fast = ordered[0]
    broad = ordered[-1]
    non_conflicted = collapse + recovery + resilient
    dominant = max(collapse, recovery + resilient)
    agreement = (
        0
        if non_conflicted == 0
        else min(10_000, dominant * 10_000 // non_conflicted)
    )
    reasons: list[str] = []

    broad_recovery = broad.state in {
        HorizonGeometryState.RECOVERING,
        HorizonGeometryState.RESILIENT,
    }
    fast_collapse = fast.state is HorizonGeometryState.COLLAPSING

    if (
        broad.state is HorizonGeometryState.COLLAPSING
        and collapse > recovery + resilient
        and broad.terminal_core_count > broad.recovery_core_count
    ):
        state = FutureGeometryState.TERMINAL_COLLAPSE
        reasons.extend(
            (
                "BROAD_STRUCTURAL_COLLAPSE",
                "COLLAPSE_HORIZON_MAJORITY",
                "TERMINAL_CORE_DOMINANT",
            )
        )
    elif fast_collapse and broad_recovery:
        state = FutureGeometryState.RECOVERABLE_ADVERSITY
        reasons.extend(
            (
                "FAST_COLLAPSE_PRESENT",
                "BROAD_RECOVERY_OR_RESILIENCE",
            )
        )
    elif broad_recovery and recovery + resilient > collapse:
        if collapse:
            state = FutureGeometryState.RECOVERABLE_ADVERSITY
            reasons.extend(
                (
                    "ADVERSITY_EXISTS_WITH_BROAD_RESILIENCE",
                    "RECOVERY_RESILIENCE_MAJORITY",
                )
            )
        else:
            state = FutureGeometryState.SUPPORTIVE_CONTINUATION
            reasons.extend(
                (
                    "BROAD_RESILIENCE",
                    "NO_COLLAPSE_HORIZON",
                )
            )
    else:
        state = FutureGeometryState.CONFLICTED
        reasons.append("WORLD_STATE_FUTURES_NOT_SEPARATED")

    if conflicted:
        reasons.append("CONFLICTED_HORIZON_PRESENT")

    return FutureGeometryAssessment(
        as_of=as_of,
        state=state,
        horizons=ordered,
        collapse_horizon_count=collapse,
        recovery_horizon_count=recovery,
        resilient_horizon_count=resilient,
        conflicted_horizon_count=conflicted,
        broad_state=broad.state,
        fast_state=fast.state,
        structural_agreement_bps=agreement,
        reasons=tuple(dict.fromkeys(reasons)),
    )
