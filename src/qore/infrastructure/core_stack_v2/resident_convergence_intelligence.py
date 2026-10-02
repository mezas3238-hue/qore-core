"""Relation-preserving resident convergence intelligence for Shared Core.

Shared has several independent causal heads. Their job is not to vote by
averaging everything into one threat score. Terminal adversity and recoverable
adversity are different *relations* between market state, future geometry and
position path.

This module therefore uses categorical topology as the primary discriminator:
- Future Geometry and Competing Futures preserve the prospective shape.
- Environment and Trajectory confirm current deterioration/recovery.
- Position Path confirms whether an open trade is failing or recovering.
- Closed analog memory, drawdown phenotype memory and stability are advisory
  context only; they cannot create a terminal/defensive state by themselves.

The layer is QORE-wide, trader-agnostic, outcome-blind for the current trade,
future-blind, and has no sizing/risk/order/execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from qore.infrastructure.core_stack_v2.competing_future_intelligence import (
    CompetingFutureAssessment,
    CompetingFutureState,
)
from qore.infrastructure.core_stack_v2.drawdown_phenotype_memory import (
    DrawdownPhenotypeAssessment,
    DrawdownPhenotypeRecognition,
)
from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentAssessment,
    MarketEnvironmentState,
)
from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    FutureGeometryAssessment,
    FutureGeometryState,
)
from qore.infrastructure.core_stack_v2.intelligence import AnalogSummary
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathAssessment,
    PositionPathState,
)
from qore.infrastructure.core_stack_v2.stability_intelligence import (
    DrawdownStabilityAssessment,
    StabilityMode,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryAssessment,
    MarketTrajectoryState,
)


class ResidentConvergenceState(StrEnum):
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    RAPID_DETERIORATION = "RAPID_DETERIORATION"
    RECOVERABLE_ADVERSITY = "RECOVERABLE_ADVERSITY"
    SUPPORTIVE_CONTINUATION = "SUPPORTIVE_CONTINUATION"
    CONTESTED = "CONTESTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class ResidentConvergencePolicy:
    minimum_active_heads: int = 4
    memory_minimum_confidence_bps: int = 2_500
    advisory_loss_rate_bps: int = 6_500
    advisory_winner_rate_bps: int = 6_500

    def __post_init__(self) -> None:
        if self.minimum_active_heads < 4:
            raise ValueError("minimum_active_heads must be at least 4")
        for name in (
            "memory_minimum_confidence_bps",
            "advisory_loss_rate_bps",
            "advisory_winner_rate_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class ResidentConvergenceAssessment:
    as_of: datetime
    state: ResidentConvergenceState
    active_head_count: int
    terminal_vote_count: int
    recovery_vote_count: int
    support_vote_count: int
    terminal_risk_bps: int
    recovery_strength_bps: int
    support_strength_bps: int
    head_agreement_bps: int
    reasons: tuple[str, ...]
    outcome_used: bool = False
    future_market_used: bool = False
    pnl_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.active_head_count < 0:
            raise ValueError("active_head_count cannot be negative")
        for name in (
            "terminal_risk_bps",
            "recovery_strength_bps",
            "support_strength_bps",
            "head_agreement_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if (
            self.outcome_used
            or self.future_market_used
            or self.pnl_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
            or self.stop_authority
            or self.target_authority
        ):
            raise ValueError("resident convergence cannot carry trading authority")


def _decimal_bps(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    return max(0, min(10_000, int(parsed * Decimal(10_000))))


def _ratio_bps(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return max(0, min(10_000, numerator * 10_000 // denominator))


def _categorical_votes(
    environment: MarketEnvironmentAssessment,
    trajectory: MarketTrajectoryAssessment,
    geometry: FutureGeometryAssessment,
    futures: CompetingFutureAssessment,
    path: PositionPathAssessment | None,
) -> tuple[int, int, int, int]:
    terminal = 0
    recovery = 0
    support = 0
    active = 4

    if environment.state in {
        MarketEnvironmentState.ADVERSE_FORMING,
        MarketEnvironmentState.DEFENSIVE,
    }:
        terminal += 1
    elif environment.state in {
        MarketEnvironmentState.STABILIZING,
        MarketEnvironmentState.RESTORED,
    }:
        recovery += 1
    elif environment.state is MarketEnvironmentState.SUPPORTIVE:
        support += 1

    if trajectory.state in {
        MarketTrajectoryState.DETERIORATING,
        MarketTrajectoryState.FAILURE,
    }:
        terminal += 1
    elif trajectory.state in {
        MarketTrajectoryState.STABILIZING,
        MarketTrajectoryState.RECOVERING,
    }:
        recovery += 1
    elif trajectory.state is MarketTrajectoryState.HEALTHY:
        support += 1

    if geometry.state is FutureGeometryState.TERMINAL_COLLAPSE:
        terminal += 1
    elif geometry.state is FutureGeometryState.RECOVERABLE_ADVERSITY:
        recovery += 1
    elif geometry.state is FutureGeometryState.SUPPORTIVE_CONTINUATION:
        support += 1

    if futures.state is CompetingFutureState.TERMINAL_ADVERSE:
        terminal += 1
    elif futures.state is CompetingFutureState.RECOVERABLE_ADVERSE:
        recovery += 1
    elif futures.state is CompetingFutureState.SUPPORTIVE:
        support += 1

    if path is not None and path.state is not PositionPathState.INSUFFICIENT:
        active += 1
        if path.state is PositionPathState.FAILURE_RISK:
            terminal += 1
        elif path.state in {
            PositionPathState.RECOVERING,
            PositionPathState.HEALTHY_PULLBACK,
        }:
            recovery += 1
        elif path.state is PositionPathState.FAVORABLE_EXPANSION:
            support += 1

    return terminal, recovery, support, active


def _advisory_reasons(
    *,
    analog: AnalogSummary | None,
    phenotype: DrawdownPhenotypeAssessment | None,
    stability: DrawdownStabilityAssessment | None,
    policy: ResidentConvergencePolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []

    if analog is not None and analog.confidence_bps >= policy.memory_minimum_confidence_bps:
        loss_rate = _decimal_bps(analog.weighted_loss_rate)
        if loss_rate is not None:
            if loss_rate >= policy.advisory_loss_rate_bps:
                reasons.append("CAUSAL_MEMORY_ADVERSE_CONTEXT_ONLY")
            elif 10_000 - loss_rate >= policy.advisory_winner_rate_bps:
                reasons.append("CAUSAL_MEMORY_WINNER_CONTEXT_ONLY")

    if phenotype is not None and phenotype.confidence_bps >= policy.memory_minimum_confidence_bps:
        if phenotype.recognition in {
            DrawdownPhenotypeRecognition.KNOWN_PURE_LOSS,
            DrawdownPhenotypeRecognition.KNOWN_LOSS_BIASED,
        }:
            reasons.append("DRAWDOWN_PHENOTYPE_ADVERSE_CONTEXT_ONLY")
        elif phenotype.recognition is DrawdownPhenotypeRecognition.KNOWN_WINNER_OVERLAP:
            reasons.append("DRAWDOWN_PHENOTYPE_WINNER_CONTEXT_ONLY")

    if stability is not None:
        if stability.mode is StabilityMode.DEFENSIVE:
            reasons.append("DRAWDOWN_STABILITY_DEFENSIVE_CONTEXT_ONLY")
        elif stability.mode is StabilityMode.RECOVERY:
            reasons.append("DRAWDOWN_STABILITY_RECOVERY_CONTEXT_ONLY")

    return tuple(reasons)


def assess_resident_convergence(
    environment: MarketEnvironmentAssessment,
    trajectory: MarketTrajectoryAssessment,
    geometry: FutureGeometryAssessment,
    futures: CompetingFutureAssessment,
    *,
    path: PositionPathAssessment | None = None,
    analog: AnalogSummary | None = None,
    phenotype: DrawdownPhenotypeAssessment | None = None,
    stability: DrawdownStabilityAssessment | None = None,
    policy: ResidentConvergencePolicy | None = None,
) -> ResidentConvergenceAssessment:
    """Resolve resident Shared state by causal relation, never scalar averaging."""
    effective = policy or ResidentConvergencePolicy()
    as_of = environment.as_of
    for name, stamp in (
        ("trajectory", trajectory.as_of),
        ("geometry", geometry.as_of),
        ("futures", futures.as_of),
    ):
        if stamp != as_of:
            raise ValueError(f"{name} assessment must share resident as_of")
    if path is not None and path.as_of != as_of:
        raise ValueError("path assessment must share resident as_of")
    if analog is not None and analog.as_of != as_of:
        raise ValueError("analog assessment must share resident as_of")
    if stability is not None and stability.as_of != as_of:
        raise ValueError("stability assessment must share resident as_of")

    terminal_votes, recovery_votes, support_votes, active = _categorical_votes(
        environment,
        trajectory,
        geometry,
        futures,
        path,
    )
    reasons: list[str] = []

    insufficient = (
        environment.state is MarketEnvironmentState.INSUFFICIENT
        or trajectory.state is MarketTrajectoryState.INSUFFICIENT
        or geometry.state is FutureGeometryState.INSUFFICIENT
        or futures.state is CompetingFutureState.INSUFFICIENT
        or active < effective.minimum_active_heads
    )

    future_terminal_pair = (
        geometry.state is FutureGeometryState.TERMINAL_COLLAPSE
        and futures.state is CompetingFutureState.TERMINAL_ADVERSE
    )
    current_failure_pair = (
        environment.state
        in {
            MarketEnvironmentState.ADVERSE_FORMING,
            MarketEnvironmentState.DEFENSIVE,
        }
        and trajectory.state
        in {
            MarketTrajectoryState.DETERIORATING,
            MarketTrajectoryState.FAILURE,
        }
    )
    future_recovery_present = (
        geometry.state is FutureGeometryState.RECOVERABLE_ADVERSITY
        or futures.state is CompetingFutureState.RECOVERABLE_ADVERSE
    )
    path_recovery_present = (
        path is not None
        and path.state
        in {
            PositionPathState.RECOVERING,
            PositionPathState.HEALTHY_PULLBACK,
            PositionPathState.FAVORABLE_EXPANSION,
        }
    )
    path_failure_present = (
        path is not None and path.state is PositionPathState.FAILURE_RISK
    )
    one_terminal_future = (
        geometry.state is FutureGeometryState.TERMINAL_COLLAPSE
        or futures.state is CompetingFutureState.TERMINAL_ADVERSE
    )
    future_support_pair = (
        geometry.state is FutureGeometryState.SUPPORTIVE_CONTINUATION
        and futures.state is CompetingFutureState.SUPPORTIVE
    )
    current_support_present = (
        environment.state
        in {
            MarketEnvironmentState.SUPPORTIVE,
            MarketEnvironmentState.STABILIZING,
            MarketEnvironmentState.RESTORED,
        }
        and trajectory.state
        in {
            MarketTrajectoryState.HEALTHY,
            MarketTrajectoryState.STABILIZING,
            MarketTrajectoryState.RECOVERING,
        }
    )

    if insufficient:
        state = ResidentConvergenceState.INSUFFICIENT
        reasons.append("RESIDENT_RELATIONAL_EVIDENCE_INSUFFICIENT")
    elif future_recovery_present and not future_terminal_pair:
        state = ResidentConvergenceState.RECOVERABLE_ADVERSITY
        reasons.extend(
            (
                "RECOVERABLE_FUTURE_EXPLICIT",
                "RECOVERY_VETOES_TERMINAL_DEFENSE",
            )
        )
    elif path_recovery_present and not future_terminal_pair:
        state = ResidentConvergenceState.RECOVERABLE_ADVERSITY
        reasons.extend(
            (
                "POSITION_PATH_RECOVERY_EXPLICIT",
                "WINNER_OR_RECOVERY_PATH_VETOES_TERMINAL_DEFENSE",
            )
        )
    elif future_terminal_pair and current_failure_pair:
        state = ResidentConvergenceState.TERMINAL_FAILURE
        reasons.extend(
            (
                "FUTURE_GEOMETRY_AND_COMPETING_FUTURES_TERMINAL",
                "CURRENT_ENVIRONMENT_AND_TRAJECTORY_CONFIRM_FAILURE",
            )
        )
    elif (
        current_failure_pair
        and one_terminal_future
        and not future_recovery_present
        and (
            path_failure_present
            or geometry.state is not FutureGeometryState.SUPPORTIVE_CONTINUATION
            or futures.state is not CompetingFutureState.SUPPORTIVE
        )
    ):
        state = ResidentConvergenceState.RAPID_DETERIORATION
        reasons.extend(
            (
                "CURRENT_MARKET_FAILURE_CONFIRMED",
                "ONE_PROSPECTIVE_TERMINAL_HEAD_CONFIRMS_DANGER",
            )
        )
    elif future_support_pair and current_support_present:
        state = ResidentConvergenceState.SUPPORTIVE_CONTINUATION
        reasons.extend(
            (
                "FUTURE_SUPPORT_PAIR_CONFIRMED",
                "CURRENT_MARKET_SUPPORT_CONFIRMED",
            )
        )
    else:
        state = ResidentConvergenceState.CONTESTED
        reasons.append("RELATIONAL_TOPOLOGY_NOT_DECISIVE")

    terminal_risk = _ratio_bps(terminal_votes, active)
    recovery_strength = _ratio_bps(recovery_votes, active)
    support_strength = _ratio_bps(support_votes, active)
    dominant = max(terminal_votes, recovery_votes, support_votes)
    agreement = _ratio_bps(dominant, active)

    if state is ResidentConvergenceState.TERMINAL_FAILURE:
        terminal_risk = max(terminal_risk, 8_000)
    elif state is ResidentConvergenceState.RAPID_DETERIORATION:
        terminal_risk = max(terminal_risk, 6_500)
    elif state is ResidentConvergenceState.RECOVERABLE_ADVERSITY:
        recovery_strength = max(recovery_strength, 7_000)
        terminal_risk = min(terminal_risk, 4_500)
    elif state is ResidentConvergenceState.SUPPORTIVE_CONTINUATION:
        support_strength = max(support_strength, 7_500)
        terminal_risk = min(terminal_risk, 3_500)

    reasons.extend(
        _advisory_reasons(
            analog=analog,
            phenotype=phenotype,
            stability=stability,
            policy=effective,
        )
    )
    reasons.extend(
        (
            f"TERMINAL_CAUSAL_HEADS_{terminal_votes}",
            f"RECOVERY_CAUSAL_HEADS_{recovery_votes}",
            f"SUPPORT_CAUSAL_HEADS_{support_votes}",
        )
    )

    return ResidentConvergenceAssessment(
        as_of=as_of,
        state=state,
        active_head_count=active,
        terminal_vote_count=terminal_votes,
        recovery_vote_count=recovery_votes,
        support_vote_count=support_votes,
        terminal_risk_bps=terminal_risk,
        recovery_strength_bps=recovery_strength,
        support_strength_bps=support_strength,
        head_agreement_bps=agreement,
        reasons=tuple(dict.fromkeys(reasons)),
    )
