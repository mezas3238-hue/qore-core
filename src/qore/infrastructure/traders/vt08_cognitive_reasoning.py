"""Sovereign deterministic reasoning for VT08 Forex Cognitive V1.

The engine does not invent strategy thresholds. It adjudicates only explicit
methodology state, causal contradictions, and unresolved material evidence from
the Situation Model. Market/anchor memories are bound for audit/context but are
not direct execution gates.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

from qore.infrastructure.traders.vt08_cognitive_memory import (
    cognitive_memory_fingerprint,
    market_anchor_context,
)
from qore.infrastructure.traders.vt08_cognitive_situation_model import (
    Vt08ForexSituationModel,
)
from qore.infrastructure.traders.vt08_cognitive_strategy_identity_memory import (
    strategy_identity_fingerprint,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08CognitiveAction,
    Vt08KnowledgeState,
)

SCHEMA: Final = "qore.vt08.forex.cognitive.reasoning.v1"


@dataclass(frozen=True, slots=True)
class Vt08AdversarialAssessment:
    material_challenges: tuple[str, ...]
    unresolved_material_challenges: tuple[str, ...]

    @property
    def blocks_execution(self) -> bool:
        return bool(self.material_challenges or self.unresolved_material_challenges)


@dataclass(frozen=True, slots=True)
class Vt08MetacognitiveAssessment:
    state: Vt08KnowledgeState
    material_unknowns: tuple[str, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class Vt08ReasoningDecision:
    action: Vt08CognitiveAction
    reason_codes: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    adversarial: Vt08AdversarialAssessment
    metacognition: Vt08MetacognitiveAssessment
    situation_fingerprint: str
    strategy_identity_fingerprint: str
    cognitive_memory_fingerprint: str
    market_anchor_context_fingerprint: str

    def fingerprint(self) -> str:
        payload = {
            "schema": SCHEMA,
            "action": self.action.value,
            "reason_codes": self.reason_codes,
            "supporting_evidence": self.supporting_evidence,
            "contradictions": self.contradictions,
            "uncertainty": self.uncertainty,
            "adversarial_material_challenges": self.adversarial.material_challenges,
            "adversarial_unresolved_material_challenges": (
                self.adversarial.unresolved_material_challenges
            ),
            "metacognitive_state": self.metacognition.state.value,
            "metacognitive_material_unknowns": self.metacognition.material_unknowns,
            "situation_fingerprint": self.situation_fingerprint,
            "strategy_identity_fingerprint": self.strategy_identity_fingerprint,
            "cognitive_memory_fingerprint": self.cognitive_memory_fingerprint,
            "market_anchor_context_fingerprint": (
                self.market_anchor_context_fingerprint
            ),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def adversarial_assessment(
    situation: Vt08ForexSituationModel,
) -> Vt08AdversarialAssessment:
    challenges = list(situation.material_contradictions)
    unresolved = list(situation.material_uncertainties)
    if not situation.methodology_valid:
        challenges.append("ADVERSARIAL:METHODOLOGY_INVALID")
    if not situation.source_identity_complete:
        unresolved.append("ADVERSARIAL:SOURCE_IDENTITY_INCOMPLETE")
    if not situation.h4_lifecycle_valid:
        challenges.append("ADVERSARIAL:H4_LIFECYCLE_INVALID")
    if situation.risk_geometry_state == "INVALID":
        challenges.append("ADVERSARIAL:RISK_GEOMETRY_INVALID")
    if situation.entry_state == "CONTRADICTED":
        challenges.append("ADVERSARIAL:ENTRY_CONTRADICTED")
    if situation.structural_destination_state == "CONTRADICTED":
        challenges.append("ADVERSARIAL:DESTINATION_CONTRADICTED")
    return Vt08AdversarialAssessment(
        material_challenges=tuple(dict.fromkeys(challenges)),
        unresolved_material_challenges=tuple(dict.fromkeys(unresolved)),
    )


def metacognitive_assessment(
    situation: Vt08ForexSituationModel,
    adversarial: Vt08AdversarialAssessment,
) -> Vt08MetacognitiveAssessment:
    if adversarial.material_challenges:
        return Vt08MetacognitiveAssessment(
            state=Vt08KnowledgeState.CONTRADICTED,
            material_unknowns=adversarial.unresolved_material_challenges,
            explanation="material causal contradiction present",
        )
    if adversarial.unresolved_material_challenges:
        return Vt08MetacognitiveAssessment(
            state=Vt08KnowledgeState.AMBIGUOUS,
            material_unknowns=adversarial.unresolved_material_challenges,
            explanation="material evidence remains unresolved",
        )
    if not situation.supporting_evidence:
        return Vt08MetacognitiveAssessment(
            state=Vt08KnowledgeState.UNKNOWN,
            material_unknowns=(),
            explanation="no explicit supporting evidence supplied",
        )
    return Vt08MetacognitiveAssessment(
        state=Vt08KnowledgeState.SUPPORTED,
        material_unknowns=(),
        explanation="causal support present with no material contradiction",
    )


def reason(
    situation: Vt08ForexSituationModel,
) -> Vt08ReasoningDecision:
    memory_context = market_anchor_context(
        situation.market,
        situation.anchor_hour_ny,
    )
    context_fingerprint = str(memory_context["fingerprint"])
    adversarial = adversarial_assessment(situation)
    meta = metacognitive_assessment(situation, adversarial)
    reasons: list[str] = []

    if adversarial.material_challenges:
        action = Vt08CognitiveAction.ABSTAIN
        reasons.append("REASONING:MATERIAL_CONTRADICTION")
    elif adversarial.unresolved_material_challenges:
        action = Vt08CognitiveAction.WAIT
        reasons.append("REASONING:MATERIAL_UNCERTAINTY")
    elif situation.cisd_state not in {"CONFIRMED", "NOT_REQUIRED_BY_BOUND_PROFILE"}:
        action = Vt08CognitiveAction.WAIT
        reasons.append("REASONING:CISD_NOT_COMPLETE")
    elif situation.protected_swing_state not in {
        "CONFIRMED",
        "NOT_REQUIRED_BY_BOUND_PROFILE",
    }:
        action = Vt08CognitiveAction.WAIT
        reasons.append("REASONING:PROTECTED_SWING_NOT_COMPLETE")
    elif situation.entry_state != "ACTIONABLE":
        action = Vt08CognitiveAction.WAIT
        reasons.append("REASONING:ENTRY_NOT_ACTIONABLE")
    elif situation.entry_freshness_state != "CURRENT":
        action = Vt08CognitiveAction.WAIT
        reasons.append("REASONING:ENTRY_NOT_CURRENT")
    else:
        action = Vt08CognitiveAction.EXECUTE
        reasons.append("REASONING:CAUSAL_HYPOTHESIS_EXECUTABLE")

    return Vt08ReasoningDecision(
        action=action,
        reason_codes=tuple(reasons),
        supporting_evidence=situation.supporting_evidence,
        contradictions=adversarial.material_challenges,
        uncertainty=adversarial.unresolved_material_challenges,
        adversarial=adversarial,
        metacognition=meta,
        situation_fingerprint=situation.fingerprint(),
        strategy_identity_fingerprint=strategy_identity_fingerprint(),
        cognitive_memory_fingerprint=cognitive_memory_fingerprint(),
        market_anchor_context_fingerprint=context_fingerprint,
    )
