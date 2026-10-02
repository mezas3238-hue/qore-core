"""Causal path representation for Shared Core V2.

Shared already owns several causal scalar and categorical assessments. This
module preserves how those assessments change together through time instead of
collapsing one observation into a larger threshold score.

The representation is deliberately outcome-blind and authority-free:
- no realized PnL or terminal trade outcome;
- no future bars;
- no sizing, capital, Risk, order, stop or target authority;
- no trader-specific methodology primitives.

It converts an ordered causal sequence into a small relational state describing
whether terminal pressure is accelerating, recovery is reasserting, target
capacity is reasserting, or the path remains contested. Research layers may
learn which motifs are useful, but the representation itself never learns from
outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PathDirection(StrEnum):
    FALLING = "FALLING"
    FLAT = "FLAT"
    RISING = "RISING"


class CausalPathPhase(StrEnum):
    TERMINAL_ACCELERATION = "TERMINAL_ACCELERATION"
    RECOVERY_REASSERTION = "RECOVERY_REASSERTION"
    TARGET_REASSERTION = "TARGET_REASSERTION"
    CONTESTED_ROTATION = "CONTESTED_ROTATION"
    STABLE_MIXED = "STABLE_MIXED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class CausalPathPoint:
    """One point-in-time, outcome-blind Shared path observation."""

    stop_pressure_bps: int
    target_capacity_bps: int
    recovery_strength_bps: int
    uncertainty_bps: int
    path_support_bps: int
    path_adverse_bps: int
    path_recovery_bps: int
    path_terminal_risk_bps: int
    trajectory_support_bps: int
    trajectory_adversity_bps: int
    trajectory_deterioration_bps: int
    trajectory_recovery_bps: int
    environment_support_bps: int
    environment_adverse_bps: int
    futures_terminal_bps: int
    futures_recovery_bps: int

    def __post_init__(self) -> None:
        for name in (
            "stop_pressure_bps",
            "target_capacity_bps",
            "recovery_strength_bps",
            "uncertainty_bps",
            "path_support_bps",
            "path_adverse_bps",
            "path_recovery_bps",
            "path_terminal_risk_bps",
            "trajectory_support_bps",
            "trajectory_adversity_bps",
            "trajectory_deterioration_bps",
            "trajectory_recovery_bps",
            "environment_support_bps",
            "environment_adverse_bps",
            "futures_terminal_bps",
            "futures_recovery_bps",
        ):
            value = getattr(self, name)
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be inside [0, 10000]")


@dataclass(frozen=True, slots=True)
class CausalPathRepresentation:
    """Relation-preserving representation of an ordered causal path."""

    evidence_count: int
    stop_target_gap_bps: int
    terminal_recovery_gap_bps: int
    adversity_support_gap_bps: int
    stop_direction: PathDirection
    target_direction: PathDirection
    recovery_direction: PathDirection
    support_direction: PathDirection
    terminal_direction: PathDirection
    deterioration_direction: PathDirection
    stop_acceleration_bps: int
    recovery_acceleration_bps: int
    target_acceleration_bps: int
    phase: CausalPathPhase
    outcome_input_used: bool = False
    future_market_used: bool = False
    sizing_used: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")
        if (
            self.outcome_input_used
            or self.future_market_used
            or self.sizing_used
            or self.risk_authority
            or self.execution_authority
        ):
            raise ValueError("causal path representation must remain authority-free")

    def motif_token(self) -> str:
        """Return a deterministic, outcome-blind transition token."""

        return "|".join(
            (
                self.phase.value,
                f"ST:{self.stop_direction.value}",
                f"TG:{self.target_direction.value}",
                f"RC:{self.recovery_direction.value}",
                f"SP:{self.support_direction.value}",
                f"TR:{self.terminal_direction.value}",
                f"DT:{self.deterioration_direction.value}",
                f"R_STGT:{_relation(self.stop_target_gap_bps)}",
                f"R_TRRC:{_relation(self.terminal_recovery_gap_bps)}",
                f"R_ADSP:{_relation(self.adversity_support_gap_bps)}",
            )
        )


def _relation(value: int) -> str:
    if value > 0:
        return "POS"
    if value < 0:
        return "NEG"
    return "EQ"


def _direction(delta: int) -> PathDirection:
    if delta > 0:
        return PathDirection.RISING
    if delta < 0:
        return PathDirection.FALLING
    return PathDirection.FLAT


def _delta(points: tuple[CausalPathPoint, ...], field: str) -> int:
    return int(getattr(points[-1], field)) - int(getattr(points[0], field))


def _acceleration(points: tuple[CausalPathPoint, ...], field: str) -> int:
    if len(points) < 3:
        return 0
    previous = int(getattr(points[-2], field)) - int(getattr(points[-3], field))
    latest = int(getattr(points[-1], field)) - int(getattr(points[-2], field))
    return latest - previous


def represent_causal_path(
    points: tuple[CausalPathPoint, ...],
    *,
    maximum_points: int = 5,
) -> CausalPathRepresentation:
    """Represent joint path evolution without consuming future outcomes.

    Only the most recent maximum_points causal observations are used so the
    representation is bounded and suitable for a resident hot-path producer.
    """

    if not points:
        raise ValueError("at least one causal path point is required")
    if maximum_points < 2:
        raise ValueError("maximum_points must be at least 2")

    window = points[-maximum_points:]
    latest = window[-1]

    stop_delta = _delta(window, "stop_pressure_bps")
    target_delta = _delta(window, "target_capacity_bps")
    recovery_delta = _delta(window, "recovery_strength_bps")
    support_delta = _delta(window, "path_support_bps")
    terminal_delta = _delta(window, "path_terminal_risk_bps")
    deterioration_delta = _delta(window, "trajectory_deterioration_bps")

    stop_direction = _direction(stop_delta)
    target_direction = _direction(target_delta)
    recovery_direction = _direction(recovery_delta)
    support_direction = _direction(support_delta)
    terminal_direction = _direction(terminal_delta)
    deterioration_direction = _direction(deterioration_delta)

    stop_target_gap = latest.stop_pressure_bps - latest.target_capacity_bps
    terminal_recovery_gap = (
        latest.path_terminal_risk_bps - latest.recovery_strength_bps
    )
    adversity_support_gap = max(
        latest.path_adverse_bps - latest.path_support_bps,
        latest.trajectory_adversity_bps - latest.trajectory_support_bps,
        latest.environment_adverse_bps - latest.environment_support_bps,
        latest.futures_terminal_bps - latest.futures_recovery_bps,
    )

    if len(window) < 2:
        phase = CausalPathPhase.INSUFFICIENT
    elif (
        stop_direction is PathDirection.RISING
        and terminal_direction is PathDirection.RISING
        and target_direction is not PathDirection.RISING
        and recovery_direction is not PathDirection.RISING
        and stop_target_gap > 0
        and terminal_recovery_gap > 0
    ):
        phase = CausalPathPhase.TERMINAL_ACCELERATION
    elif (
        recovery_direction is PathDirection.RISING
        and support_direction is PathDirection.RISING
        and stop_direction is not PathDirection.RISING
        and terminal_recovery_gap <= 0
    ):
        phase = CausalPathPhase.RECOVERY_REASSERTION
    elif (
        target_direction is PathDirection.RISING
        and support_direction is PathDirection.RISING
        and stop_direction is not PathDirection.RISING
        and stop_target_gap <= 0
    ):
        phase = CausalPathPhase.TARGET_REASSERTION
    elif (
        stop_direction is not target_direction
        or terminal_direction is not recovery_direction
        or deterioration_direction is PathDirection.RISING
    ):
        phase = CausalPathPhase.CONTESTED_ROTATION
    else:
        phase = CausalPathPhase.STABLE_MIXED

    return CausalPathRepresentation(
        evidence_count=len(window),
        stop_target_gap_bps=stop_target_gap,
        terminal_recovery_gap_bps=terminal_recovery_gap,
        adversity_support_gap_bps=adversity_support_gap,
        stop_direction=stop_direction,
        target_direction=target_direction,
        recovery_direction=recovery_direction,
        support_direction=support_direction,
        terminal_direction=terminal_direction,
        deterioration_direction=deterioration_direction,
        stop_acceleration_bps=_acceleration(window, "stop_pressure_bps"),
        recovery_acceleration_bps=_acceleration(window, "recovery_strength_bps"),
        target_acceleration_bps=_acceleration(window, "target_capacity_bps"),
        phase=phase,
    )
