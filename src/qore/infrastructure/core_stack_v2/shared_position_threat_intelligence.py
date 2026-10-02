"""Causal position-threat intelligence for Shared.

The engine consumes the same source-time position/world evidence used by the
continuation engine and derives threat without exit, Risk or execution
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
    continuation_source_scores,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedPositionThreatLevel,
    SharedSupportState,
    SharedTraderIntelligenceValidationError,
)


class SharedPositionThreatScope(StrEnum):
    LOCAL_ASSET_THREAT = "LOCAL_ASSET_THREAT"
    CROSS_ASSET_THREAT = "CROSS_ASSET_THREAT"
    SYSTEMIC_WORLD_THREAT = "SYSTEMIC_WORLD_THREAT"


@dataclass(frozen=True, slots=True)
class SharedPositionThreatPolicy:
    policy_id: str
    moderate_threshold_bps: int
    elevated_threshold_bps: int
    high_threshold_bps: int
    critical_threshold_bps: int
    minimum_integrity_bps: int
    source_only_calibration: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "position threat policy_id must be non-empty"
            )
        values = (
            self.moderate_threshold_bps,
            self.elevated_threshold_bps,
            self.high_threshold_bps,
            self.critical_threshold_bps,
        )
        if any(type(item) is not int or not 0 <= item <= 10_000 for item in values):
            raise SharedTraderIntelligenceValidationError(
                "position threat thresholds must be int within 0..10000"
            )
        if not (
            self.moderate_threshold_bps
            < self.elevated_threshold_bps
            < self.high_threshold_bps
            < self.critical_threshold_bps
        ):
            raise SharedTraderIntelligenceValidationError(
                "position threat thresholds must be strictly ordered"
            )
        if (
            type(self.minimum_integrity_bps) is not int
            or not 0 <= self.minimum_integrity_bps <= 10_000
        ):
            raise SharedTraderIntelligenceValidationError(
                "minimum_integrity_bps must be int within 0..10000"
            )
        if not self.source_only_calibration:
            raise SharedTraderIntelligenceValidationError(
                "position threat calibration must be source-only"
            )
        if not self.evidence_refs:
            raise SharedTraderIntelligenceValidationError(
                "position threat policy requires evidence refs"
            )


@dataclass(frozen=True, slots=True)
class SharedPositionThreatEngineAssessment:
    threat_level: SharedPositionThreatLevel
    threat_scope: SharedPositionThreatScope
    threat_score_bps: int
    continuation_support_bps: int
    failure_hazard_bps: int
    relationship_break_bps: int
    systemic_stress_bps: int
    uncertainty_bps: int
    continuation_support: SharedSupportState
    failure_hazard: SharedSupportState
    reason_codes: tuple[str, ...]
    mandatory_exit: bool = False
    mandatory_protection: bool = False
    position_management_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "threat_score_bps",
            "continuation_support_bps",
            "failure_hazard_bps",
            "relationship_break_bps",
            "systemic_stress_bps",
            "uncertainty_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if not self.reason_codes:
            raise SharedTraderIntelligenceValidationError(
                "position threat assessment requires reason codes"
            )
        if (
            self.mandatory_exit
            or self.mandatory_protection
            or self.position_management_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "position threat intelligence cannot command an action"
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


def threat_source_score_bps(
    observation: SharedPositionCausalObservation,
) -> tuple[int, int, int, int, int]:
    continuation, _tail, failure, _coherence, uncertainty = (
        continuation_source_scores(observation)
    )
    relationship_break = (
        (10_000 - observation.peer_confirmation_bps)
        + observation.peer_transition_adverse_bps
    ) // 2
    systemic = (
        observation.world_fragility_bps
        + observation.peer_transition_adverse_bps
        + (10_000 - observation.world_support_bps)
    ) // 3
    threat = (
        failure * 5
        + relationship_break * 2
        + systemic * 2
        + uncertainty
    ) // 10
    threat = max(0, min(10_000, threat))
    return threat, continuation, failure, relationship_break, systemic


def assess_position_threat(
    observation: SharedPositionCausalObservation,
    *,
    policy: SharedPositionThreatPolicy,
) -> SharedPositionThreatEngineAssessment:
    threat, continuation, failure, relationship_break, systemic = (
        threat_source_score_bps(observation)
    )
    _, _, _, _, uncertainty = continuation_source_scores(observation)
    reasons: list[str] = []

    if observation.data_integrity_bps < policy.minimum_integrity_bps:
        level = SharedPositionThreatLevel.INSUFFICIENT
        reasons.append("DATA_INTEGRITY_INSUFFICIENT")
    elif threat >= policy.critical_threshold_bps:
        level = SharedPositionThreatLevel.CRITICAL
        reasons.append("CRITICAL_SOURCE_THREAT")
    elif threat >= policy.high_threshold_bps:
        level = SharedPositionThreatLevel.HIGH
        reasons.append("HIGH_SOURCE_THREAT")
    elif threat >= policy.elevated_threshold_bps:
        level = SharedPositionThreatLevel.ELEVATED
        reasons.append("ELEVATED_SOURCE_THREAT")
    elif threat >= policy.moderate_threshold_bps:
        level = SharedPositionThreatLevel.MODERATE
        reasons.append("MODERATE_SOURCE_THREAT")
    elif threat > 0:
        level = SharedPositionThreatLevel.LOW
        reasons.append("LOW_SOURCE_THREAT")
    else:
        level = SharedPositionThreatLevel.NONE
        reasons.append("NO_MATERIAL_SOURCE_THREAT")

    if systemic >= max(relationship_break, failure):
        scope = SharedPositionThreatScope.SYSTEMIC_WORLD_THREAT
        reasons.append("SYSTEMIC_WORLD_DOMINANT")
    elif relationship_break >= failure:
        scope = SharedPositionThreatScope.CROSS_ASSET_THREAT
        reasons.append("CROSS_ASSET_DOMINANT")
    else:
        scope = SharedPositionThreatScope.LOCAL_ASSET_THREAT
        reasons.append("LOCAL_ASSET_DOMINANT")

    if failure >= continuation:
        reasons.append("FAILURE_HAZARD_AT_LEAST_CONTINUATION")
    if relationship_break >= 6_000:
        reasons.append("RELATIONSHIP_BREAK_ELEVATED")
    if systemic >= 6_000:
        reasons.append("SYSTEMIC_STRESS_ELEVATED")
    if uncertainty >= 6_000:
        reasons.append("UNCERTAINTY_HIGH")

    return SharedPositionThreatEngineAssessment(
        threat_level=level,
        threat_scope=scope,
        threat_score_bps=threat,
        continuation_support_bps=continuation,
        failure_hazard_bps=failure,
        relationship_break_bps=relationship_break,
        systemic_stress_bps=systemic,
        uncertainty_bps=uncertainty,
        continuation_support=_state(continuation),
        failure_hazard=_state(failure),
        reason_codes=tuple(sorted(set(reasons))),
    )
