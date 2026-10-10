"""Evidence-bound uncertainty and metacognition for QORE Capitalizer V2.

This layer answers "what do I actually know?" before strategy-source logic is allowed to act.
It never fabricates a win probability and never grants entry/capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerPerceptionStatus,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeResolution,
)


class CapitalizerEpistemicReadiness(StrEnum):
    WELL_SUPPORTED = "WELL_SUPPORTED"
    CONDITIONALLY_SUPPORTED = "CONDITIONALLY_SUPPORTED"
    UNRESOLVED = "UNRESOLVED"
    CONFLICTED = "CONFLICTED"


@dataclass(frozen=True, slots=True)
class CapitalizerMetacognitiveFacts:
    knowledge: CapitalizerKnowledgeState
    perception_status: CapitalizerPerceptionStatus
    regime_resolution: CapitalizerRegimeResolution
    contradictions: tuple[str, ...] = ()
    evidence_provenance_complete: bool = False
    destination_context_known: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerMetacognitiveAssessment:
    readiness: CapitalizerEpistemicReadiness
    reasons: tuple[str, ...]
    numeric_confidence_used: bool = False
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.numeric_confidence_used:
            raise ValueError("Capitalizer metacognition cannot fabricate numeric confidence")
        if self.grants_entry_authority:
            raise ValueError("metacognition cannot grant entry authority")
        if self.grants_capital_authority:
            raise ValueError("metacognition cannot grant capital authority")


def assess_metacognition(
    facts: CapitalizerMetacognitiveFacts,
) -> CapitalizerMetacognitiveAssessment:
    """Classify epistemic readiness using only decision-time evidence classes."""

    conflicted: list[str] = []
    if facts.contradictions:
        conflicted.extend(f"CONTRADICTION:{item}" for item in facts.contradictions)
    if facts.knowledge is CapitalizerKnowledgeState.CONFLICTED:
        conflicted.append("KNOWLEDGE_CONFLICTED")
    if facts.regime_resolution is CapitalizerRegimeResolution.CONFLICTED:
        conflicted.append("REGIME_CONFLICTED")
    if conflicted:
        return CapitalizerMetacognitiveAssessment(
            readiness=CapitalizerEpistemicReadiness.CONFLICTED,
            reasons=tuple(dict.fromkeys(conflicted)),
        )

    unresolved: list[str] = []
    if facts.perception_status is CapitalizerPerceptionStatus.BAD:
        unresolved.append("PERCEPTION_BAD")
    if facts.knowledge is CapitalizerKnowledgeState.UNKNOWN:
        unresolved.append("KNOWLEDGE_UNKNOWN")
    if facts.regime_resolution is CapitalizerRegimeResolution.UNRESOLVED:
        unresolved.append("REGIME_UNRESOLVED")
    if not facts.evidence_provenance_complete:
        unresolved.append("EVIDENCE_PROVENANCE_INCOMPLETE")
    if unresolved:
        return CapitalizerMetacognitiveAssessment(
            readiness=CapitalizerEpistemicReadiness.UNRESOLVED,
            reasons=tuple(unresolved),
        )

    conditional: list[str] = []
    if facts.perception_status is CapitalizerPerceptionStatus.DEGRADED:
        conditional.append("PERCEPTION_DEGRADED")
    if facts.knowledge is CapitalizerKnowledgeState.PARTIAL:
        conditional.append("KNOWLEDGE_PARTIAL")
    if not facts.destination_context_known:
        conditional.append("DESTINATION_CONTEXT_UNKNOWN")
    if conditional:
        return CapitalizerMetacognitiveAssessment(
            readiness=CapitalizerEpistemicReadiness.CONDITIONALLY_SUPPORTED,
            reasons=tuple(conditional),
        )

    return CapitalizerMetacognitiveAssessment(
        readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
        reasons=("EVIDENCE_STATE_WELL_SUPPORTED",),
    )
