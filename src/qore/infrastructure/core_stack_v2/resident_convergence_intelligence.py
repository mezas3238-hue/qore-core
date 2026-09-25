"""Resident multi-head convergence intelligence for Shared Core.

Shared owns many independent causal views of the same market. This module keeps
those views separate and then asks a narrow resident question:

    do independent Shared heads converge on terminal deterioration,
    recoverable adversity, or supportive continuation *right now*?

It is intentionally generic and sizing-blind. It consumes only already-causal
Shared assessments plus CLOSED historical memory summaries. It cannot place an
order, resize risk, widen a stop, mutate a target, or inspect the current
trade's terminal outcome/future market path.

The purpose of this layer is to prevent two failure modes:
1. late defense because one slow path model is still accumulating observations;
2. false defense because a single adverse head overwhelms stronger recovery /
   winner evidence from the rest of Shared.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from qore.infrastructure.core_stack_v2.competing_future_intelligence import (
    CompetingFutureAssessment,
)
from qore.infrastructure.core_stack_v2.drawdown_phenotype_memory import (
    DrawdownPhenotypeAssessment,
    DrawdownPhenotypeRecognition,
)
from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentAssessment,
)
from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    FutureGeometryAssessment,
)
from qore.infrastructure.core_stack_v2.intelligence import AnalogSummary
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathAssessment,
)
from qore.infrastructure.core_stack_v2.stability_intelligence import (
    DrawdownStabilityAssessment,
    StabilityMode,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryAssessment,
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
    terminal_vote_bps: int = 6_000
    recovery_vote_bps: int = 6_000
    support_vote_bps: int = 6_500
    terminal_risk_bps: int = 6_500
    rapid_risk_bps: int = 5_800
    recovery_strength_bps: int = 6_000
    support_strength_bps: int = 6_500
    terminal_margin_bps: int = 1_000
    rapid_margin_bps: int = 500
    recovery_margin_bps: int = 750
    memory_minimum_confidence_bps: int = 2_500

    def __post_init__(self) -> None:
        if self.minimum_active_heads < 3:
            raise ValueError("minimum_active_heads must be at least 3")
        for name in self.__dataclass_fields__:
            if name == "minimum_active_heads":
                continue
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


@dataclass(frozen=True, slots=True)
class _Head:
    name: str
    terminal_bps: int
    recovery_bps: int
    support_bps: int


def _clip(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _mean(*values: int) -> int:
    if not values:
        raise ValueError("mean requires values")
    return sum(values) // len(values)


def _blend_neutral(value_bps: int, confidence_bps: int) -> int:
    return _clip(
        (
            value_bps * confidence_bps
            + 5_000 * (10_000 - confidence_bps)
        )
        // 10_000
    )


def _decimal_bps(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    return _clip(int(parsed * Decimal(10_000)))


def _environment_head(value: MarketEnvironmentAssessment) -> _Head:
    terminal = _mean(
        value.adverse_environment_bps,
        value.adverse_velocity_bps,
        value.adverse_persistence_bps,
        value.cross_market_fragility_bps,
        value.structural_fragility_bps,
    )
    recovery = _mean(
        value.recovery_velocity_bps,
        value.recovery_persistence_bps,
        value.market_support_bps,
    )
    return _Head("ENVIRONMENT", terminal, recovery, value.market_support_bps)


def _trajectory_head(value: MarketTrajectoryAssessment) -> _Head:
    terminal = _mean(
        value.adversity_bps,
        value.deterioration_pressure_bps,
        value.deterioration_velocity_bps,
        value.deterioration_persistence_bps,
    )
    recovery = _mean(
        value.recovery_velocity_bps,
        value.recovery_persistence_bps,
        value.support_bps,
    )
    return _Head("TRAJECTORY", terminal, recovery, value.support_bps)


def _geometry_head(value: FutureGeometryAssessment) -> _Head:
    total = max(1, len(value.horizons))
    terminal = _clip(
        (
            value.collapse_horizon_count * 10_000
            + value.structural_agreement_bps
        )
        // (total + 1)
    )
    recovery = _clip(
        (
            value.recovery_horizon_count * 10_000
            + value.resilient_horizon_count * 5_000
            + value.structural_agreement_bps
        )
        // (total + 1)
    )
    support = _clip(
        (
            value.resilient_horizon_count * 10_000
            + value.recovery_horizon_count * 6_500
            + (10_000 - terminal)
        )
        // (total + 1)
    )
    return _Head("FUTURE_GEOMETRY", terminal, recovery, support)


def _future_head(value: CompetingFutureAssessment) -> _Head:
    terminal = value.terminal_evidence_bps
    recovery = value.recovery_evidence_bps
    support = _clip(
        _mean(
            10_000 - terminal,
            recovery,
            value.horizon_agreement_bps,
        )
    )
    return _Head("COMPETING_FUTURES", terminal, recovery, support)


def _path_head(value: PositionPathAssessment) -> _Head:
    terminal = value.terminal_failure_risk_bps
    recovery = _mean(
        value.recovery_persistence_bps,
        value.path_support_bps,
        value.winner_protection_bps,
    )
    support = _mean(value.path_support_bps, value.winner_protection_bps)
    return _Head("POSITION_PATH", terminal, recovery, support)


def _analog_head(
    value: AnalogSummary,
    *,
    minimum_confidence_bps: int,
) -> _Head | None:
    if value.confidence_bps < minimum_confidence_bps:
        return None
    loss_rate = _decimal_bps(value.weighted_loss_rate)
    if loss_rate is None:
        return None
    terminal = _blend_neutral(loss_rate, value.confidence_bps)
    recovery = _blend_neutral(10_000 - loss_rate, value.confidence_bps)
    return _Head("CAUSAL_ANALOG_MEMORY", terminal, recovery, recovery)


def _phenotype_head(
    value: DrawdownPhenotypeAssessment,
    *,
    minimum_confidence_bps: int,
) -> _Head | None:
    if value.confidence_bps < minimum_confidence_bps:
        return None
    base_terminal = {
        DrawdownPhenotypeRecognition.UNKNOWN: 5_000,
        DrawdownPhenotypeRecognition.KNOWN_PURE_LOSS: 8_500,
        DrawdownPhenotypeRecognition.KNOWN_LOSS_BIASED: 7_000,
        DrawdownPhenotypeRecognition.KNOWN_AMBIGUOUS: 5_000,
        DrawdownPhenotypeRecognition.KNOWN_WINNER_OVERLAP: 3_500,
    }[value.recognition]
    terminal = _blend_neutral(base_terminal, value.confidence_bps)
    recovery = _blend_neutral(10_000 - base_terminal, value.confidence_bps)
    return _Head("DRAWDOWN_PHENOTYPE_MEMORY", terminal, recovery, recovery)


def _stability_head(value: DrawdownStabilityAssessment) -> _Head:
    terminal = _mean(
        value.drawdown_pressure_bps,
        value.loss_cluster_pressure_bps,
        value.market_adversity_bps,
        value.deterioration_pressure_bps,
    )
    recovery = value.recovery_confidence_bps
    support = _clip(
        _mean(
            10_000 - value.deterioration_pressure_bps,
            value.recovery_confidence_bps,
            7_000 if value.mode in {StabilityMode.STABLE, StabilityMode.RECOVERY} else 3_000,
        )
    )
    return _Head("DRAWDOWN_STABILITY", terminal, recovery, support)


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

    heads: list[_Head] = [
        _environment_head(environment),
        _trajectory_head(trajectory),
        _geometry_head(geometry),
        _future_head(futures),
    ]
    if path is not None:
        heads.append(_path_head(path))
    if analog is not None:
        head = _analog_head(
            analog,
            minimum_confidence_bps=effective.memory_minimum_confidence_bps,
        )
        if head is not None:
            heads.append(head)
    if phenotype is not None:
        head = _phenotype_head(
            phenotype,
            minimum_confidence_bps=effective.memory_minimum_confidence_bps,
        )
        if head is not None:
            heads.append(head)
    if stability is not None:
        heads.append(_stability_head(stability))

    active = len(heads)
    terminal = _mean(*(item.terminal_bps for item in heads))
    recovery = _mean(*(item.recovery_bps for item in heads))
    support = _mean(*(item.support_bps for item in heads))
    terminal_votes = sum(
        item.terminal_bps >= effective.terminal_vote_bps
        and item.terminal_bps >= item.recovery_bps
        for item in heads
    )
    recovery_votes = sum(
        item.recovery_bps >= effective.recovery_vote_bps
        and item.recovery_bps > item.terminal_bps
        for item in heads
    )
    support_votes = sum(
        item.support_bps >= effective.support_vote_bps
        and item.terminal_bps < effective.terminal_vote_bps
        for item in heads
    )
    dominant_votes = max(terminal_votes, recovery_votes, support_votes)
    agreement = 0 if active == 0 else dominant_votes * 10_000 // active

    reasons: list[str] = []
    if active < effective.minimum_active_heads:
        state = ResidentConvergenceState.INSUFFICIENT
        reasons.append("RESIDENT_HEAD_COVERAGE_INSUFFICIENT")
    elif (
        terminal_votes >= 3
        and terminal >= effective.terminal_risk_bps
        and terminal >= recovery + effective.terminal_margin_bps
        and support < effective.support_strength_bps
    ):
        state = ResidentConvergenceState.TERMINAL_FAILURE
        reasons.extend(
            (
                "MULTI_HEAD_TERMINAL_CONVERGENCE",
                "TERMINAL_RISK_DOMINATES_RECOVERY",
            )
        )
    elif (
        recovery_votes >= 3
        and recovery >= effective.recovery_strength_bps
        and recovery >= terminal + effective.recovery_margin_bps
    ):
        state = ResidentConvergenceState.RECOVERABLE_ADVERSITY
        reasons.extend(
            (
                "MULTI_HEAD_RECOVERY_CONVERGENCE",
                "RECOVERY_DOMINATES_TERMINAL_RISK",
            )
        )
    elif (
        support_votes >= 3
        and support >= effective.support_strength_bps
        and terminal < effective.rapid_risk_bps
    ):
        state = ResidentConvergenceState.SUPPORTIVE_CONTINUATION
        reasons.append("MULTI_HEAD_SUPPORTIVE_CONTINUATION")
    elif (
        terminal_votes >= 2
        and terminal >= effective.rapid_risk_bps
        and terminal >= recovery + effective.rapid_margin_bps
    ):
        state = ResidentConvergenceState.RAPID_DETERIORATION
        reasons.extend(
            (
                "MULTI_HEAD_RAPID_DETERIORATION",
                "TERMINAL_RISK_LEADS_RECOVERY",
            )
        )
    else:
        state = ResidentConvergenceState.CONTESTED
        reasons.append("SHARED_HEADS_NOT_YET_DECISIVELY_SEPARATED")

    if terminal_votes:
        reasons.append(f"TERMINAL_HEADS_{terminal_votes}")
    if recovery_votes:
        reasons.append(f"RECOVERY_HEADS_{recovery_votes}")
    if support_votes:
        reasons.append(f"SUPPORT_HEADS_{support_votes}")

    return ResidentConvergenceAssessment(
        as_of=as_of,
        state=state,
        active_head_count=active,
        terminal_vote_count=terminal_votes,
        recovery_vote_count=recovery_votes,
        support_vote_count=support_votes,
        terminal_risk_bps=terminal,
        recovery_strength_bps=recovery,
        support_strength_bps=support,
        head_agreement_bps=agreement,
        reasons=tuple(reasons),
    )
