"""Causal continuation and positive-tail intelligence for open positions.

This engine consumes only position/world evidence available at the current
observation time. It produces cognition, never a HOLD or execution command.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedSupportState,
    SharedTraderIntelligenceValidationError,
)


def _bps(name: str, value: int) -> None:
    if type(value) is not int or not 0 <= value <= 10_000:
        raise SharedTraderIntelligenceValidationError(
            f"{name} must be int within 0..10000"
        )


def _signed_bps(name: str, value: int) -> None:
    if type(value) is not int or not -10_000 <= value <= 10_000:
        raise SharedTraderIntelligenceValidationError(
            f"{name} must be int within -10000..10000"
        )


def _mean(values: tuple[int, ...]) -> int:
    return sum(values) // len(values)


def _state(value: int) -> SharedSupportState:
    if value >= 8_000:
        return SharedSupportState.STRONG
    if value >= 6_500:
        return SharedSupportState.ELEVATED
    if value >= 4_500:
        return SharedSupportState.MODERATE
    if value >= 2_500:
        return SharedSupportState.LOW
    return SharedSupportState.VERY_LOW


@dataclass(frozen=True, slots=True)
class SharedPositionCausalObservation:
    observation_id: str
    position_id: str
    asset: str
    as_of: datetime
    evidence_cutoff_at: datetime
    minutes_since_fill: int
    progress_bps: int
    signed_close_r_bps: int
    efficiency_bps: int
    overlap_bps: int
    signed_body_r_bps: int
    peer_confirmation_bps: int
    breadth_bps: int
    peer_transition_adverse_bps: int
    world_support_bps: int
    world_fragility_bps: int
    data_integrity_bps: int
    provenance_refs: tuple[str, ...]
    future_market_used: bool = False
    future_outcome_used: bool = False
    pnl_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("observation_id", "position_id", "asset"):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        for value in (self.as_of, self.evidence_cutoff_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    "position observation timestamps must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.as_of:
            raise SharedTraderIntelligenceValidationError(
                "position observation cannot use future evidence"
            )
        if self.minutes_since_fill < 0:
            raise SharedTraderIntelligenceValidationError(
                "minutes_since_fill cannot be negative"
            )
        for name in (
            "progress_bps",
            "overlap_bps",
            "peer_confirmation_bps",
            "breadth_bps",
            "peer_transition_adverse_bps",
            "world_support_bps",
            "world_fragility_bps",
            "data_integrity_bps",
        ):
            _bps(name, getattr(self, name))
        for name in (
            "signed_close_r_bps",
            "efficiency_bps",
            "signed_body_r_bps",
        ):
            _signed_bps(name, getattr(self, name))
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "position observation provenance must be non-empty and canonical"
            )
        if (
            self.future_market_used
            or self.future_outcome_used
            or self.pnl_used
            or self.productive_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "position causal observation may contain source-time evidence only"
            )


@dataclass(frozen=True, slots=True)
class SharedContinuationPositiveTailPolicy:
    policy_id: str
    continuation_threshold_bps: int
    positive_tail_threshold_bps: int
    minimum_integrity_bps: int
    source_only_calibration: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "continuation policy_id must be non-empty"
            )
        for name in (
            "continuation_threshold_bps",
            "positive_tail_threshold_bps",
            "minimum_integrity_bps",
        ):
            _bps(name, getattr(self, name))
        if self.continuation_threshold_bps >= self.positive_tail_threshold_bps:
            raise SharedTraderIntelligenceValidationError(
                "positive-tail threshold must exceed continuation threshold"
            )
        if not self.source_only_calibration:
            raise SharedTraderIntelligenceValidationError(
                "continuation policy calibration must be source-only"
            )
        if not self.evidence_refs:
            raise SharedTraderIntelligenceValidationError(
                "continuation policy requires evidence refs"
            )


@dataclass(frozen=True, slots=True)
class SharedContinuationPositiveTailAssessment:
    as_of: datetime
    continuation_score_bps: int
    positive_tail_score_bps: int
    failure_hazard_bps: int
    world_coherence_bps: int
    uncertainty_bps: int
    continuation_support: SharedSupportState
    positive_tail_support: SharedSupportState
    failure_hazard: SharedSupportState
    materially_supported: bool
    positive_tail_candidate: bool
    reason_codes: tuple[str, ...]
    mandatory_hold: bool = False
    position_management_authority: bool = False
    execution_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "continuation_score_bps",
            "positive_tail_score_bps",
            "failure_hazard_bps",
            "world_coherence_bps",
            "uncertainty_bps",
        ):
            _bps(name, getattr(self, name))
        if not self.reason_codes:
            raise SharedTraderIntelligenceValidationError(
                "continuation assessment requires reason codes"
            )
        if (
            self.mandatory_hold
            or self.position_management_authority
            or self.execution_authority
            or self.sizing_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "continuation intelligence cannot command position management"
            )


def continuation_source_scores(
    observation: SharedPositionCausalObservation,
) -> tuple[int, int, int, int, int]:
    """Return continuation, positive-tail, failure, coherence and uncertainty."""

    positive_close = max(0, observation.signed_close_r_bps)
    positive_efficiency = max(0, observation.efficiency_bps)
    adverse_close = max(0, -observation.signed_close_r_bps)
    adverse_efficiency = max(0, -observation.efficiency_bps)
    adverse_body = max(0, -observation.signed_body_r_bps)
    low_overlap = 10_000 - observation.overlap_bps
    peer_health = 10_000 - observation.peer_transition_adverse_bps
    low_fragility = 10_000 - observation.world_fragility_bps

    coherence = _mean(
        (
            observation.peer_confirmation_bps,
            observation.breadth_bps,
            observation.world_support_bps,
            peer_health,
            low_fragility,
        )
    )
    continuation = _mean(
        (
            observation.progress_bps,
            positive_close,
            positive_efficiency,
            low_overlap,
            observation.peer_confirmation_bps,
            observation.breadth_bps,
            observation.world_support_bps,
        )
    )
    positive_tail = _mean(
        (
            observation.progress_bps,
            positive_close,
            positive_efficiency,
            observation.peer_confirmation_bps,
            observation.world_support_bps,
            low_fragility,
        )
    )
    failure = _mean(
        (
            adverse_close,
            adverse_efficiency,
            adverse_body,
            observation.overlap_bps,
            observation.peer_transition_adverse_bps,
            observation.world_fragility_bps,
            10_000 - observation.peer_confirmation_bps,
        )
    )
    conflict = min(continuation, failure)
    uncertainty = _mean(
        (
            10_000 - observation.data_integrity_bps,
            conflict,
            observation.world_fragility_bps,
            observation.peer_transition_adverse_bps,
        )
    )
    return continuation, positive_tail, failure, coherence, uncertainty


def assess_continuation_positive_tail(
    observation: SharedPositionCausalObservation,
    *,
    policy: SharedContinuationPositiveTailPolicy,
) -> SharedContinuationPositiveTailAssessment:
    continuation, positive_tail, failure, coherence, uncertainty = (
        continuation_source_scores(observation)
    )
    reasons: list[str] = []

    if observation.data_integrity_bps < policy.minimum_integrity_bps:
        continuation_state = SharedSupportState.INSUFFICIENT
        tail_state = SharedSupportState.INSUFFICIENT
        failure_state = SharedSupportState.INSUFFICIENT
        material = False
        tail_candidate = False
        reasons.append("DATA_INTEGRITY_INSUFFICIENT")
    else:
        continuation_state = _state(continuation)
        tail_state = _state(positive_tail)
        failure_state = _state(failure)
        material = (
            continuation >= policy.continuation_threshold_bps
            and continuation > failure
        )
        tail_candidate = (
            positive_tail >= policy.positive_tail_threshold_bps
            and positive_tail > failure
        )
        reasons.append(
            "CONTINUATION_SOURCE_SUPPORT"
            if material
            else "CONTINUATION_NOT_MATERIAL"
        )
        if tail_candidate:
            reasons.append("POSITIVE_TAIL_SOURCE_SUPPORT")
        if failure >= continuation:
            reasons.append("FAILURE_HAZARD_DOMINATES")
        if coherence >= 6_500:
            reasons.append("WORLD_COHERENCE_SUPPORTIVE")
        if observation.peer_transition_adverse_bps >= 6_000:
            reasons.append("PEER_TRANSITION_ADVERSE")
        if uncertainty >= 6_000:
            reasons.append("UNCERTAINTY_HIGH")

    return SharedContinuationPositiveTailAssessment(
        as_of=observation.as_of,
        continuation_score_bps=continuation,
        positive_tail_score_bps=positive_tail,
        failure_hazard_bps=failure,
        world_coherence_bps=coherence,
        uncertainty_bps=uncertainty,
        continuation_support=continuation_state,
        positive_tail_support=tail_state,
        failure_hazard=failure_state,
        materially_supported=material,
        positive_tail_candidate=tail_candidate,
        reason_codes=tuple(sorted(set(reasons))),
    )
