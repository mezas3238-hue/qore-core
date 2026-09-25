"""Minimal shadow-only Competing-Risk Path Core for Shared.

This is the first CCRPC layer. It does not emit broker actions and it does not
pretend to output calibrated probabilities yet. It produces transparent,
bounded causal pressure/capacity proxies from point-in-time market state plus
the trade-specific path.

The trade path is primary. Broad market context may confirm or contradict it,
but cannot manufacture TARGET_LIKELY without favorable path evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.core_stack_v2.competing_future_intelligence import (
    CompetingFutureAssessment,
    CompetingFutureState,
)
from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentAssessment,
    MarketEnvironmentState,
)
from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    FutureGeometryAssessment,
    FutureGeometryState,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathAssessment,
    PositionPathState,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryAssessment,
    MarketTrajectoryState,
)


@dataclass(frozen=True, slots=True)
class CompetingRiskBeliefState:
    as_of: datetime
    stop_pressure_bps: int
    target_capacity_bps: int
    recovery_strength_bps: int
    uncertainty_bps: int
    stop_hazard_proxy_bps: int
    target_hazard_proxy_bps: int
    separation_margin_bps: int
    path_evidence_available: bool
    calibrated_probability: bool = False
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    stop_mutation_authority: bool = False
    target_mutation_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "stop_pressure_bps",
            "target_capacity_bps",
            "recovery_strength_bps",
            "uncertainty_bps",
            "stop_hazard_proxy_bps",
            "target_hazard_proxy_bps",
            "separation_margin_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.calibrated_probability:
            raise ValueError("phase-one competing-risk outputs are not calibrated probabilities")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.stop_mutation_authority
            or self.target_mutation_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("CCRPC phase one is shadow cognition only")


def _clamp(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _geometry_terminal(geometry: FutureGeometryAssessment) -> int:
    return {
        FutureGeometryState.TERMINAL_COLLAPSE: 9_000,
        FutureGeometryState.RECOVERABLE_ADVERSITY: 1_500,
        FutureGeometryState.SUPPORTIVE_CONTINUATION: 500,
        FutureGeometryState.CONFLICTED: 4_500,
        FutureGeometryState.INSUFFICIENT: 5_000,
    }[geometry.state]


def _geometry_target(geometry: FutureGeometryAssessment) -> int:
    return {
        FutureGeometryState.TERMINAL_COLLAPSE: 500,
        FutureGeometryState.RECOVERABLE_ADVERSITY: 3_500,
        FutureGeometryState.SUPPORTIVE_CONTINUATION: 9_000,
        FutureGeometryState.CONFLICTED: 4_500,
        FutureGeometryState.INSUFFICIENT: 5_000,
    }[geometry.state]


def _geometry_recovery(geometry: FutureGeometryAssessment) -> int:
    return {
        FutureGeometryState.TERMINAL_COLLAPSE: 500,
        FutureGeometryState.RECOVERABLE_ADVERSITY: 9_000,
        FutureGeometryState.SUPPORTIVE_CONTINUATION: 2_000,
        FutureGeometryState.CONFLICTED: 4_500,
        FutureGeometryState.INSUFFICIENT: 5_000,
    }[geometry.state]


def _future_target(futures: CompetingFutureAssessment) -> int:
    return {
        CompetingFutureState.TERMINAL_ADVERSE: 500,
        CompetingFutureState.RECOVERABLE_ADVERSE: 3_500,
        CompetingFutureState.SUPPORTIVE: 9_000,
        CompetingFutureState.CONFLICTED: 4_500,
        CompetingFutureState.INSUFFICIENT: 5_000,
    }[futures.state]


def _future_recovery(futures: CompetingFutureAssessment) -> int:
    if futures.state is CompetingFutureState.RECOVERABLE_ADVERSE:
        return futures.recovery_evidence_bps
    if futures.state is CompetingFutureState.CONFLICTED:
        return min(futures.recovery_evidence_bps, 4_500)
    if futures.state is CompetingFutureState.INSUFFICIENT:
        return 5_000
    return 1_500


def assess_competing_risk_path(
    environment: MarketEnvironmentAssessment,
    trajectory: MarketTrajectoryAssessment,
    geometry: FutureGeometryAssessment,
    futures: CompetingFutureAssessment,
    *,
    path: PositionPathAssessment | None = None,
) -> CompetingRiskBeliefState:
    """Build an uncalibrated STOP-vs-TARGET belief state from causal evidence."""
    as_of = environment.as_of
    for name, stamp in (
        ("trajectory", trajectory.as_of),
        ("geometry", geometry.as_of),
        ("futures", futures.as_of),
    ):
        if stamp != as_of:
            raise ValueError(f"{name} assessment must share as_of")
    if path is not None and path.as_of != as_of:
        raise ValueError("path assessment must share as_of")

    current_terminal = min(
        max(
            environment.adverse_environment_bps,
            trajectory.deterioration_pressure_bps,
        ),
        max(
            environment.adverse_persistence_bps,
            trajectory.deterioration_persistence_bps,
        ),
    )
    prospective_terminal = min(
        _geometry_terminal(geometry),
        futures.terminal_evidence_bps,
    )

    current_target = min(
        environment.market_support_bps,
        trajectory.support_bps,
    )
    prospective_target = min(
        _geometry_target(geometry),
        _future_target(futures),
    )
    recovery_state_present = (
        environment.state
        in {
            MarketEnvironmentState.STABILIZING,
            MarketEnvironmentState.RESTORED,
        }
        or trajectory.state
        in {
            MarketTrajectoryState.STABILIZING,
            MarketTrajectoryState.RECOVERING,
        }
    )
    current_recovery = (
        max(
            environment.recovery_velocity_bps,
            trajectory.recovery_velocity_bps,
            environment.recovery_persistence_bps,
            trajectory.recovery_persistence_bps,
        )
        if recovery_state_present
        else 0
    )
    prospective_recovery = min(
        _geometry_recovery(geometry),
        _future_recovery(futures),
    )

    path_available = (
        path is not None and path.state is not PositionPathState.INSUFFICIENT
    )
    if not path_available:
        stop_pressure = min(5_000, max(current_terminal, prospective_terminal))
        target_capacity = min(4_000, max(current_target, prospective_target))
        recovery_strength = min(5_000, max(current_recovery, prospective_recovery))
        uncertainty = max(
            7_500,
            10_000 - abs(stop_pressure - target_capacity),
        )
        stop_hazard = min(stop_pressure, 4_500)
        target_hazard = min(target_capacity, 3_500)
    else:
        assert path is not None
        path_terminal = path.terminal_failure_risk_bps
        path_target = min(
            path.path_support_bps,
            path.winner_protection_bps,
        )
        path_recovery = max(
            path.recovery_persistence_bps,
            (
                path.winner_protection_bps
                if path.state
                in {
                    PositionPathState.HEALTHY_PULLBACK,
                    PositionPathState.RECOVERING,
                }
                else 0
            ),
        )

        stop_pressure = min(
            path_terminal,
            max(current_terminal, prospective_terminal),
        )
        target_capacity = min(
            path_target,
            max(current_target, prospective_target),
        )
        recovery_strength = (
            max(path_recovery, current_recovery, prospective_recovery)
            if path.state
            in {
                PositionPathState.HEALTHY_PULLBACK,
                PositionPathState.RECOVERING,
            }
            else min(5_000, max(current_recovery, prospective_recovery))
        )

        if path.state not in {
            PositionPathState.FAVORABLE_EXPANSION,
            PositionPathState.HEALTHY_PULLBACK,
        }:
            target_capacity = min(target_capacity, 4_500)
        if path.state in {
            PositionPathState.HEALTHY_PULLBACK,
            PositionPathState.RECOVERING,
        }:
            stop_pressure = min(stop_pressure, 5_000)

        stop_hazard = stop_pressure
        target_hazard = (
            target_capacity
            if path.state is PositionPathState.FAVORABLE_EXPANSION
            else min(target_capacity, 5_000)
        )

        conflict = abs(stop_hazard - target_hazard)
        explicit_conflict = (
            geometry.state is FutureGeometryState.CONFLICTED
            or futures.state is CompetingFutureState.CONFLICTED
            or path.state is PositionPathState.CONTESTED
        )
        uncertainty = max(
            10_000 - conflict,
            7_000 if explicit_conflict else 0,
            6_500 if recovery_strength >= 6_500 else 0,
        )

    margin = abs(stop_hazard - target_hazard)
    return CompetingRiskBeliefState(
        as_of=as_of,
        stop_pressure_bps=_clamp(stop_pressure),
        target_capacity_bps=_clamp(target_capacity),
        recovery_strength_bps=_clamp(recovery_strength),
        uncertainty_bps=_clamp(uncertainty),
        stop_hazard_proxy_bps=_clamp(stop_hazard),
        target_hazard_proxy_bps=_clamp(target_hazard),
        separation_margin_bps=_clamp(margin),
        path_evidence_available=path_available,
    )
