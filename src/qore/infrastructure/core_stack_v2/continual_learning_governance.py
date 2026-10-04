"""MC-24 continual-learning knowledge separation and regression governance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ContinualKnowledgeTier(StrEnum):
    STABLE_CERTIFIED = "STABLE_CERTIFIED"
    RECENT_VALIDATED_ADAPTATION = "RECENT_VALIDATED_ADAPTATION"
    EXPERIMENTAL = "EXPERIMENTAL"


@dataclass(frozen=True, slots=True)
class KnowledgeCapabilityScore:
    capability_id: str
    score_bps: int

    def __post_init__(self) -> None:
        if not self.capability_id:
            raise ValueError("capability id required")
        if type(self.score_bps) is not int or not 0 <= self.score_bps <= 10_000:
            raise ValueError("capability score must be int within 0..10000")


@dataclass(frozen=True, slots=True)
class ContinualLearningCandidate:
    candidate_id: str
    source_tier: ContinualKnowledgeTier
    target_tier: ContinualKnowledgeTier
    baseline: tuple[KnowledgeCapabilityScore, ...]
    candidate: tuple[KnowledgeCapabilityScore, ...]
    transportability_bps: int
    knowledge_half_life_days: int
    maximum_allowed_regression_bps: int
    evidence_refs: tuple[str, ...]
    silent_certified_overwrite: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("continual candidate id required")
        if (
            self.source_tier is ContinualKnowledgeTier.EXPERIMENTAL
            and self.target_tier is ContinualKnowledgeTier.STABLE_CERTIFIED
        ):
            raise ValueError("experimental knowledge cannot jump to certified")
        if self.silent_certified_overwrite:
            raise ValueError("certified knowledge cannot be silently overwritten")
        for value in (
            self.transportability_bps,
            self.maximum_allowed_regression_bps,
        ):
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError("continual-learning bps out of range")
        if self.knowledge_half_life_days < 1:
            raise ValueError("knowledge half-life must be positive")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("continual-learning evidence refs must be canonical")
        if {x.capability_id for x in self.baseline} != {
            x.capability_id for x in self.candidate
        }:
            raise ValueError("baseline/candidate capability sets must match")


@dataclass(frozen=True, slots=True)
class ContinualLearningAssessment:
    candidate_id: str
    maximum_regression_bps: int
    catastrophic_forgetting_detected: bool
    transportability_pass: bool
    half_life_recorded: bool
    promotion_allowed: bool


def assess_continual_candidate(
    candidate: ContinualLearningCandidate,
    *,
    minimum_transportability_bps: int = 7_500,
) -> ContinualLearningAssessment:
    baseline = {x.capability_id: x.score_bps for x in candidate.baseline}
    proposed = {x.capability_id: x.score_bps for x in candidate.candidate}
    max_regression = max(
        max(0, baseline[key] - proposed[key]) for key in baseline
    )
    forgetting = max_regression > candidate.maximum_allowed_regression_bps
    transport = candidate.transportability_bps >= minimum_transportability_bps
    return ContinualLearningAssessment(
        candidate_id=candidate.candidate_id,
        maximum_regression_bps=max_regression,
        catastrophic_forgetting_detected=forgetting,
        transportability_pass=transport,
        half_life_recorded=True,
        promotion_allowed=not forgetting and transport,
    )
