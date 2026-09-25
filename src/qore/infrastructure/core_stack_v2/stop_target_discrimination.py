"""Shadow-only stop-vs-target path discrimination for Shared Core.

Phase 1 answers one question before any trailing-stop or target-extension
research may contribute to a drawdown claim:

    Does the causal market/trade path look more like a possible terminal stop,
    a possible target-reaching continuation, or a recoverable/contested path?

This module is deliberately relation-preserving. It does not reduce the market
to a scalar average and it has no stop, target, sizing, risk, order or execution
authority. Realized outcomes are never inputs. Historical outcomes may be used
offline only to score these classifications after the fact.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

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


class StopTargetHypothesis(StrEnum):
    STOP_LIKELY = "STOP_LIKELY"
    TARGET_LIKELY = "TARGET_LIKELY"
    RECOVERABLE = "RECOVERABLE"
    CONTESTED = "CONTESTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class StopTargetDiscrimination:
    as_of: datetime
    hypothesis: StopTargetHypothesis
    evidence_count: int
    structural_agreement_bps: int
    terminal_relation_count: int
    target_relation_count: int
    recovery_relation_count: int
    reasons: tuple[str, ...]
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
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")
        if not 0 <= self.structural_agreement_bps <= 10_000:
            raise ValueError("structural_agreement_bps must be within 0..10000")
        for name in (
            "terminal_relation_count",
            "target_relation_count",
            "recovery_relation_count",
        ):
            if int(getattr(self, name)) < 0:
                raise ValueError(f"{name} cannot be negative")
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
            raise ValueError(
                "stop-target discrimination is shadow cognition only"
            )


def _agreement_bps(*, terminal: int, target: int, recovery: int) -> int:
    total = terminal + target + recovery
    if total <= 0:
        return 0
    return max(terminal, target, recovery) * 10_000 // total


def assess_stop_target_path(
    environment: MarketEnvironmentAssessment,
    trajectory: MarketTrajectoryAssessment,
    geometry: FutureGeometryAssessment,
    futures: CompetingFutureAssessment,
    *,
    path: PositionPathAssessment | None = None,
) -> StopTargetDiscrimination:
    """Classify the causal path without using realized or future outcomes."""
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

    core_insufficient = (
        environment.state is MarketEnvironmentState.INSUFFICIENT
        or trajectory.state is MarketTrajectoryState.INSUFFICIENT
        or geometry.state is FutureGeometryState.INSUFFICIENT
        or futures.state is CompetingFutureState.INSUFFICIENT
    )

    terminal = 0
    target = 0
    recovery = 0
    evidence = 4
    reasons: list[str] = []

    environment_terminal = environment.state in {
        MarketEnvironmentState.ADVERSE_FORMING,
        MarketEnvironmentState.DEFENSIVE,
    }
    environment_supportive = environment.state in {
        MarketEnvironmentState.SUPPORTIVE,
        MarketEnvironmentState.RESTORED,
    }
    environment_recovering = environment.state is MarketEnvironmentState.STABILIZING

    trajectory_terminal = trajectory.state in {
        MarketTrajectoryState.DETERIORATING,
        MarketTrajectoryState.FAILURE,
    }
    trajectory_supportive = trajectory.state is MarketTrajectoryState.HEALTHY
    trajectory_recovering = trajectory.state in {
        MarketTrajectoryState.STABILIZING,
        MarketTrajectoryState.RECOVERING,
    }

    geometry_terminal = geometry.state is FutureGeometryState.TERMINAL_COLLAPSE
    geometry_target = geometry.state is FutureGeometryState.SUPPORTIVE_CONTINUATION
    geometry_recovery = geometry.state is FutureGeometryState.RECOVERABLE_ADVERSITY

    futures_terminal = futures.state is CompetingFutureState.TERMINAL_ADVERSE
    futures_target = futures.state is CompetingFutureState.SUPPORTIVE
    futures_recovery = futures.state is CompetingFutureState.RECOVERABLE_ADVERSE

    terminal += int(environment_terminal)
    terminal += int(trajectory_terminal)
    terminal += int(geometry_terminal)
    terminal += int(futures_terminal)

    target += int(environment_supportive)
    target += int(trajectory_supportive)
    target += int(geometry_target)
    target += int(futures_target)

    recovery += int(environment_recovering)
    recovery += int(trajectory_recovering)
    recovery += int(geometry_recovery)
    recovery += int(futures_recovery)

    path_terminal = False
    path_target = False
    path_recovery = False
    if path is not None and path.state is not PositionPathState.INSUFFICIENT:
        evidence += 1
        path_terminal = path.state in {
            PositionPathState.ADVERSE_DOMINANCE,
            PositionPathState.FAILURE_RISK,
        }
        path_target = path.state is PositionPathState.FAVORABLE_EXPANSION
        path_recovery = path.state in {
            PositionPathState.HEALTHY_PULLBACK,
            PositionPathState.RECOVERING,
        }
        terminal += int(path_terminal)
        target += int(path_target)
        recovery += int(path_recovery)

    agreement = _agreement_bps(
        terminal=terminal,
        target=target,
        recovery=recovery,
    )

    explicit_recovery = geometry_recovery or futures_recovery or path_recovery
    future_terminal_pair = geometry_terminal and futures_terminal
    future_target_pair = geometry_target and futures_target
    current_terminal_pair = environment_terminal and trajectory_terminal
    current_target_pair = environment_supportive and trajectory_supportive

    if core_insufficient:
        hypothesis = StopTargetHypothesis.INSUFFICIENT
        reasons.append("CORE_CAUSAL_EVIDENCE_INSUFFICIENT")
    elif (
        path is not None
        and path.state is PositionPathState.FAILURE_RISK
        and not (
            geometry_recovery
            and futures_recovery
            and (environment_recovering or trajectory_recovering)
        )
    ):
        hypothesis = StopTargetHypothesis.STOP_LIKELY
        reasons.extend(
            (
                "POSITION_PATH_FAILURE_RISK_PRIMARY",
                "TRADE_SPECIFIC_PATH_OVERRIDES_BROAD_AMBIGUITY",
            )
        )
        if geometry_terminal or futures_terminal:
            reasons.append("PROSPECTIVE_TERMINAL_CONFIRMATION_PRESENT")
    elif (
        path is not None
        and path.state is PositionPathState.ADVERSE_DOMINANCE
        and (
            environment_terminal
            or trajectory_terminal
            or geometry_terminal
            or futures_terminal
        )
        and not explicit_recovery
    ):
        hypothesis = StopTargetHypothesis.STOP_LIKELY
        reasons.extend(
            (
                "POSITION_PATH_ADVERSE_DOMINANCE_PRIMARY",
                "ADVERSE_CONTEXT_CONFIRMS_STOP_PATH",
            )
        )
    elif path_recovery and not future_terminal_pair:
        hypothesis = StopTargetHypothesis.RECOVERABLE
        reasons.extend(
            (
                "POSITION_PATH_RECOVERY_PRIMARY",
                "STOP_HYPOTHESIS_VETOED_BY_TRADE_PATH_RECOVERY",
            )
        )
    elif (
        path_target
        and not future_terminal_pair
        and not current_terminal_pair
        and (
            geometry_target
            or futures_target
            or environment_supportive
            or trajectory_supportive
        )
    ):
        hypothesis = StopTargetHypothesis.TARGET_LIKELY
        reasons.extend(
            (
                "POSITION_PATH_FAVORABLE_EXPANSION_PRIMARY",
                "TARGET_CAPACITY_CONFIRMED_BY_MARKET_CONTEXT",
            )
        )
    elif explicit_recovery and not future_terminal_pair:
        hypothesis = StopTargetHypothesis.RECOVERABLE
        reasons.extend(
            (
                "RECOVERY_RELATION_EXPLICIT",
                "STOP_HYPOTHESIS_VETOED_BY_RECOVERY",
            )
        )
    elif future_terminal_pair and current_terminal_pair and not path_target:
        hypothesis = StopTargetHypothesis.STOP_LIKELY
        reasons.extend(
            (
                "FUTURE_GEOMETRY_TERMINAL",
                "COMPETING_FUTURES_TERMINAL",
                "CURRENT_MARKET_FAILURE_CONFIRMED",
                "PREENTRY_TERMINAL_RELATION_ONLY",
            )
        )
    else:
        hypothesis = StopTargetHypothesis.CONTESTED
        reasons.append("STOP_TARGET_RELATION_NOT_SEPARATED")

    reasons.extend(
        (
            f"TERMINAL_RELATIONS_{terminal}",
            f"TARGET_RELATIONS_{target}",
            f"RECOVERY_RELATIONS_{recovery}",
        )
    )

    return StopTargetDiscrimination(
        as_of=as_of,
        hypothesis=hypothesis,
        evidence_count=evidence,
        structural_agreement_bps=agreement,
        terminal_relation_count=terminal,
        target_relation_count=target,
        recovery_relation_count=recovery,
        reasons=tuple(dict.fromkeys(reasons)),
    )
