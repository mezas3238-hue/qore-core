"""STI-6 V2 trajectory acceleration and positive-tail intelligence.

This generation replaces the falsified V1 static-level hypothesis with a
sequential source-only hypothesis:
- improving continuation / tail trajectory matters;
- persistent local expansion matters;
- elevated failure hazard vetoes continuation support.

No trade outcome, future market state or productive authority is consumed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
    continuation_source_scores,
)
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
class SharedContinuationTrajectoryV2Policy:
    policy_id: str
    sequence_window: int
    continuation_velocity_threshold_bps: int
    tail_velocity_threshold_bps: int
    local_expansion_threshold_bps: int
    persistence_threshold_bps: int
    max_failure_hazard_bps: int
    minimum_integrity_bps: int
    source_only_calibration: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V2 policy_id must be non-empty"
            )
        if self.sequence_window < 3:
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V2 sequence_window must be >= 3"
            )
        for name in (
            "continuation_velocity_threshold_bps",
            "tail_velocity_threshold_bps",
            "local_expansion_threshold_bps",
            "persistence_threshold_bps",
            "max_failure_hazard_bps",
            "minimum_integrity_bps",
        ):
            _bps(name, getattr(self, name))
        if not self.source_only_calibration:
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V2 calibration must be source-only"
            )
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V2 evidence refs must be non-empty and canonical"
            )


@dataclass(frozen=True, slots=True)
class SharedContinuationTrajectoryV2Assessment:
    continuation_velocity_bps: int
    tail_velocity_bps: int
    local_expansion_bps: int
    expansion_persistence_bps: int
    failure_hazard_bps: int
    world_coherence_bps: int
    uncertainty_bps: int
    continuation_support: SharedSupportState
    positive_tail_support: SharedSupportState
    failure_hazard: SharedSupportState
    materially_supported: bool
    positive_tail_candidate: bool
    failure_veto: bool
    reason_codes: tuple[str, ...]
    mandatory_hold: bool = False
    position_management_authority: bool = False
    execution_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "local_expansion_bps",
            "expansion_persistence_bps",
            "failure_hazard_bps",
            "world_coherence_bps",
            "uncertainty_bps",
        ):
            _bps(name, getattr(self, name))
        for name in (
            "continuation_velocity_bps",
            "tail_velocity_bps",
        ):
            _signed_bps(name, getattr(self, name))
        if not self.reason_codes:
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V2 assessment requires reason codes"
            )
        if (
            self.mandatory_hold
            or self.position_management_authority
            or self.execution_authority
            or self.sizing_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V2 cannot command position management"
            )


def _local_expansion(observation: SharedPositionCausalObservation) -> int:
    positive_close = max(0, observation.signed_close_r_bps)
    positive_efficiency = max(0, observation.efficiency_bps)
    low_overlap = 10_000 - observation.overlap_bps
    return (
        observation.progress_bps
        + positive_close
        + positive_efficiency
        + low_overlap
    ) // 4


def continuation_trajectory_v2_features(
    observations: Sequence[SharedPositionCausalObservation],
    *,
    sequence_window: int,
) -> tuple[int, int, int, int, int, int, int]:
    """Return source-only sequential features for STI-6 V2."""

    if not observations:
        raise SharedTraderIntelligenceValidationError(
            "STI-6 V2 requires observations"
        )
    recent = tuple(observations[-sequence_window:])
    for left, right in zip(recent, recent[1:], strict=False):
        if right.as_of <= left.as_of:
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V2 observations must be chronological"
            )
        if right.position_id != left.position_id:
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V2 sequence must use one position"
            )

    scores = [continuation_source_scores(item) for item in recent]
    continuation = [item[0] for item in scores]
    tails = [item[1] for item in scores]
    failures = [item[2] for item in scores]
    coherences = [item[3] for item in scores]
    uncertainties = [item[4] for item in scores]

    if len(recent) == 1:
        continuation_velocity = 0
        tail_velocity = 0
    else:
        prior_continuation = sum(continuation[:-1]) // len(continuation[:-1])
        prior_tail = sum(tails[:-1]) // len(tails[:-1])
        continuation_velocity = continuation[-1] - prior_continuation
        tail_velocity = tails[-1] - prior_tail

    expansion = [_local_expansion(item) for item in recent]
    local_expansion = expansion[-1]
    expanding = 0
    for index, item in enumerate(recent):
        positive = (
            item.signed_close_r_bps > 0
            and item.efficiency_bps > 0
            and item.progress_bps > 0
        )
        nondecaying = index == 0 or expansion[index] >= expansion[index - 1]
        expanding += int(positive and nondecaying)
    persistence = expanding * 10_000 // len(recent)

    return (
        max(-10_000, min(10_000, continuation_velocity)),
        max(-10_000, min(10_000, tail_velocity)),
        local_expansion,
        persistence,
        failures[-1],
        coherences[-1],
        uncertainties[-1],
    )


def assess_continuation_trajectory_v2(
    observations: Sequence[SharedPositionCausalObservation],
    *,
    policy: SharedContinuationTrajectoryV2Policy,
) -> SharedContinuationTrajectoryV2Assessment:
    (
        continuation_velocity,
        tail_velocity,
        local_expansion,
        persistence,
        failure,
        coherence,
        uncertainty,
    ) = continuation_trajectory_v2_features(
        observations,
        sequence_window=policy.sequence_window,
    )
    latest = observations[-1]
    reasons: list[str] = []

    if latest.data_integrity_bps < policy.minimum_integrity_bps:
        material = False
        tail_candidate = False
        failure_veto = True
        continuation_state = SharedSupportState.INSUFFICIENT
        tail_state = SharedSupportState.INSUFFICIENT
        failure_state = SharedSupportState.INSUFFICIENT
        reasons.append("DATA_INTEGRITY_INSUFFICIENT")
    else:
        failure_veto = failure > policy.max_failure_hazard_bps
        continuation_accelerating = (
            continuation_velocity
            >= policy.continuation_velocity_threshold_bps
        )
        tail_accelerating = tail_velocity >= policy.tail_velocity_threshold_bps
        local_expansion_supported = (
            local_expansion >= policy.local_expansion_threshold_bps
        )
        persistent = persistence >= policy.persistence_threshold_bps

        material = (
            continuation_accelerating
            and local_expansion_supported
            and persistent
            and not failure_veto
        )
        tail_candidate = (
            tail_accelerating
            and local_expansion_supported
            and persistent
            and not failure_veto
        )
        continuation_level = max(
            0,
            min(
                10_000,
                5_000
                + continuation_velocity // 2
                + local_expansion // 4
                + persistence // 4,
            ),
        )
        tail_level = max(
            0,
            min(
                10_000,
                5_000
                + tail_velocity // 2
                + local_expansion // 4
                + persistence // 4,
            ),
        )
        continuation_state = _state(continuation_level)
        tail_state = _state(tail_level)
        failure_state = _state(failure)

        reasons.append(
            "TRAJECTORY_ACCELERATION_SUPPORTED"
            if continuation_accelerating
            else "TRAJECTORY_ACCELERATION_NOT_SUPPORTED"
        )
        reasons.append(
            "LOCAL_EXPANSION_SUPPORTED"
            if local_expansion_supported
            else "LOCAL_EXPANSION_NOT_SUPPORTED"
        )
        reasons.append(
            "EXPANSION_PERSISTENT"
            if persistent
            else "EXPANSION_NOT_PERSISTENT"
        )
        if tail_accelerating:
            reasons.append("POSITIVE_TAIL_ACCELERATION_SUPPORTED")
        if failure_veto:
            reasons.append("FAILURE_HAZARD_VETO")

    return SharedContinuationTrajectoryV2Assessment(
        continuation_velocity_bps=continuation_velocity,
        tail_velocity_bps=tail_velocity,
        local_expansion_bps=local_expansion,
        expansion_persistence_bps=persistence,
        failure_hazard_bps=failure,
        world_coherence_bps=coherence,
        uncertainty_bps=uncertainty,
        continuation_support=continuation_state,
        positive_tail_support=tail_state,
        failure_hazard=failure_state,
        materially_supported=material,
        positive_tail_candidate=tail_candidate,
        failure_veto=failure_veto,
        reason_codes=tuple(sorted(set(reasons))),
    )
