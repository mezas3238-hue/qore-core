"""MC-23 Meta-Learning and Rapid Regime Adaptation governance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.uncertainty_decomposition_v2 import (
    SharedUncertaintyEvidenceV2,
)


class NoveltyState(StrEnum):
    KNOWN = "KNOWN"
    NEAR_KNOWN = "NEAR_KNOWN"
    NOVEL = "NOVEL"
    UNRESOLVED = "UNRESOLVED"


class AdaptationDisposition(StrEnum):
    RESEARCH_ONLY = "RESEARCH_ONLY"
    VALIDATED_ADAPTATION = "VALIDATED_ADAPTATION"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class RegimeNoveltyAssessment:
    state: NoveltyState
    novelty_bps: int
    historical_distance_bps: int
    regime_unfamiliarity_bps: int
    model_disagreement_bps: int
    closest_known_structures: tuple[str, ...]
    unknown_treated_as_known: bool = False

    def __post_init__(self) -> None:
        for name in (
            "novelty_bps",
            "historical_distance_bps",
            "regime_unfamiliarity_bps",
            "model_disagreement_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if self.closest_known_structures != tuple(
            sorted(set(self.closest_known_structures))
        ):
            raise ValueError("closest known structures must be canonical")
        if self.unknown_treated_as_known:
            raise ValueError("novel/unknown state cannot masquerade as known")


@dataclass(frozen=True, slots=True)
class AdaptiveHypothesisProposal:
    proposal_id: str
    novelty: RegimeNoveltyAssessment
    hypothesis_ref: str
    validation_refs: tuple[str, ...]
    disposition: AdaptationDisposition
    fresh_holdout_contaminated: bool = False
    certified_knowledge_mutation: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.proposal_id or not self.hypothesis_ref:
            raise ValueError("adaptation proposal identity/hypothesis required")
        if self.validation_refs != tuple(sorted(set(self.validation_refs))):
            raise ValueError("adaptation validation refs must be canonical")
        if self.fresh_holdout_contaminated:
            raise ValueError("adaptation cannot contaminate fresh holdout")
        if self.certified_knowledge_mutation or self.productive_authority:
            raise ValueError("adaptation research cannot mutate certified knowledge")
        if self.disposition is AdaptationDisposition.VALIDATED_ADAPTATION:
            if not self.validation_refs:
                raise ValueError("validated adaptation requires validation evidence")
            if self.novelty.state not in {NoveltyState.NOVEL, NoveltyState.NEAR_KNOWN}:
                raise ValueError("validated adaptation must answer novelty")


def assess_regime_novelty(
    evidence: SharedUncertaintyEvidenceV2,
    *,
    closest_known_structures: tuple[str, ...],
) -> RegimeNoveltyAssessment:
    novelty = evidence.novelty_bps
    distance = evidence.historical_distance_bps
    unfamiliarity = evidence.regime_unfamiliarity_bps
    disagreement = evidence.model_disagreement_bps
    composite = max(novelty, distance, unfamiliarity)
    if evidence.data_missingness_bps >= 6_500:
        state = NoveltyState.UNRESOLVED
    elif composite >= 7_000:
        state = NoveltyState.NOVEL
    elif composite >= 4_000 or disagreement >= 5_000:
        state = NoveltyState.NEAR_KNOWN
    else:
        state = NoveltyState.KNOWN
    return RegimeNoveltyAssessment(
        state=state,
        novelty_bps=novelty,
        historical_distance_bps=distance,
        regime_unfamiliarity_bps=unfamiliarity,
        model_disagreement_bps=disagreement,
        closest_known_structures=tuple(sorted(set(closest_known_structures))),
    )
