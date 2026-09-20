"""Causal situation, metacognition, adversarial reasoning and sovereignty for CRT PURE.

No CRT entry rule is encoded here.  This layer reasons only from causal state and the
frozen cognitive contract.  Strategy-validity fields must later be populated by the
source-certified CRT methodology.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureAttentionState,
    CrtPureEpistemicReadiness,
    CrtPureHypothesisStage,
    CrtPureKnowledgeState,
    CrtPureReasoningAction,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


class CrtPureAdversarialVerdict(StrEnum):
    PASSED = "PASSED"
    CHALLENGED = "CHALLENGED"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True, slots=True)
class CrtPureCausalObservation:
    name: str
    observed_at: datetime
    value_token: str

    def __post_init__(self) -> None:
        if not self.name or not self.value_token:
            raise ValueError("causal observation name/value must be non-empty")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("causal observation timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CrtPureSituationModel:
    market: CrtPureMarket
    observed_at: datetime
    hypothesis_id: str
    source_event_id: str
    event_generation: int
    attention_state: CrtPureAttentionState
    hypothesis_stage: CrtPureHypothesisStage

    data_integrity_ok: bool
    strategy_identity_ready: bool
    source_event_present: bool
    confirmation_complete: bool

    destination_context_known: bool
    destination_available: bool
    execution_data_fresh: bool

    knowledge_state: CrtPureKnowledgeState
    contradictions: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    market_context_tokens: tuple[str, ...] = ()
    observations: tuple[CrtPureCausalObservation, ...] = ()

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id must be non-empty")
        if not self.source_event_id:
            raise ValueError("source_event_id must be non-empty")
        if self.event_generation < 1:
            raise ValueError("event_generation must be >= 1")
        for observation in self.observations:
            if observation.observed_at > self.observed_at:
                raise ValueError("future observation cannot enter CRT Situation Model")


@dataclass(frozen=True, slots=True)
class CrtPureMetacognitiveAssessment:
    readiness: CrtPureEpistemicReadiness
    reasons: tuple[str, ...]
    numeric_confidence_used: bool = False
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.numeric_confidence_used:
            raise ValueError("CRT metacognition cannot fabricate numeric confidence")
        if self.grants_entry_authority:
            raise ValueError("metacognition cannot grant entry authority")
        if self.grants_capital_authority:
            raise ValueError("metacognition cannot grant capital authority")


@dataclass(frozen=True, slots=True)
class CrtPureAdversarialAssessment:
    verdict: CrtPureAdversarialVerdict
    hard_findings: tuple[str, ...]
    challenge_findings: tuple[str, ...]
    counterfactual_questions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CrtPureReasoningDecision:
    action: CrtPureReasoningAction
    thesis: str
    supporting_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    adversarial_verdict: CrtPureAdversarialVerdict
    metacognitive_readiness: CrtPureEpistemicReadiness
    auditable_why: tuple[str, ...]
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_capital_authority:
            raise ValueError("CRT Reasoning cannot grant capital authority")
        if not self.thesis:
            raise ValueError("CRT Reasoning thesis must be non-empty")
        if not self.auditable_why:
            raise ValueError("CRT Reasoning requires an auditable WHY")


def assess_metacognition(
    state: CrtPureSituationModel,
) -> CrtPureMetacognitiveAssessment:
    reasons: list[str] = []

    if state.knowledge_state is CrtPureKnowledgeState.CONFLICTED or state.contradictions:
        return CrtPureMetacognitiveAssessment(
            readiness=CrtPureEpistemicReadiness.CONFLICTED,
            reasons=("CONFLICTING_EVIDENCE", *state.contradictions),
        )

    if not state.data_integrity_ok or not state.execution_data_fresh:
        reasons.append("PERCEPTION_NOT_RELIABLE")
    if not state.strategy_identity_ready:
        reasons.append("SOURCE_CERTIFIED_STRATEGY_IDENTITY_NOT_READY")
    if not state.destination_context_known:
        reasons.append("DESTINATION_CONTEXT_UNKNOWN")

    if state.knowledge_state is CrtPureKnowledgeState.UNKNOWN:
        reasons.append("KNOWLEDGE_STATE_UNKNOWN")
        readiness = CrtPureEpistemicReadiness.UNRESOLVED
    elif reasons:
        readiness = CrtPureEpistemicReadiness.CONDITIONALLY_SUPPORTED
    elif state.uncertainties:
        readiness = CrtPureEpistemicReadiness.CONDITIONALLY_SUPPORTED
        reasons.extend(state.uncertainties)
    else:
        readiness = CrtPureEpistemicReadiness.WELL_SUPPORTED
        reasons.append("EVIDENCE_COMPLETE_AT_DECISION_TIME")

    return CrtPureMetacognitiveAssessment(
        readiness=readiness,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def adversarial_assessment(
    state: CrtPureSituationModel,
    metacognition: CrtPureMetacognitiveAssessment,
) -> CrtPureAdversarialAssessment:
    hard: list[str] = []
    challenge: list[str] = []

    if not state.data_integrity_ok:
        hard.append("DATA_INTEGRITY_FAILED")
    if not state.execution_data_fresh:
        hard.append("EXECUTION_DATA_STALE")
    if not state.strategy_identity_ready:
        hard.append("CRT_SOURCE_STRATEGY_NOT_CLOSED")
    if not state.source_event_present:
        hard.append("NO_ACTIVE_CRT_SOURCE_EVENT")
    if state.hypothesis_stage in {
        CrtPureHypothesisStage.THESIS_INVALIDATED,
        CrtPureHypothesisStage.THESIS_KILLED,
    }:
        hard.append("CRT_THESIS_DEAD")
    if state.destination_context_known and not state.destination_available:
        hard.append("AUTHORIZED_DESTINATION_UNAVAILABLE")
    hard.extend(state.contradictions)

    if not state.confirmation_complete:
        challenge.append("CRT_CONFIRMATION_INCOMPLETE")
    if metacognition.readiness in {
        CrtPureEpistemicReadiness.UNRESOLVED,
        CrtPureEpistemicReadiness.CONDITIONALLY_SUPPORTED,
    }:
        challenge.append("METACOGNITION_NOT_WELL_SUPPORTED")
    challenge.extend(state.uncertainties)

    verdict = (
        CrtPureAdversarialVerdict.FALSIFIED
        if hard
        else CrtPureAdversarialVerdict.CHALLENGED
        if challenge
        else CrtPureAdversarialVerdict.PASSED
    )

    return CrtPureAdversarialAssessment(
        verdict=verdict,
        hard_findings=tuple(dict.fromkeys(hard)),
        challenge_findings=tuple(dict.fromkeys(challenge)),
        counterfactual_questions=(
            "WHAT_OBSERVATION_WOULD_INVALIDATE_THIS_CRT_THESIS",
            "IS_THE_AUTHORIZED_DESTINATION_STILL_AVAILABLE",
            "IS_THIS_A_GENUINELY_NEW_CAUSAL_EVENT",
            "IS_THE_CRT_CONFIRMATION_COMPLETE",
            "IS_EVIDENCE_COMPLETE_AT_DECISION_TIME",
        ),
    )


def reason(state: CrtPureSituationModel) -> CrtPureReasoningDecision:
    """Return sovereign EXECUTE / WAIT / ABSTAIN without inventing CRT rules."""
    meta = assess_metacognition(state)
    adversarial = adversarial_assessment(state, meta)

    support: list[str] = []
    if state.source_event_present:
        support.append("ACTIVE_CRT_SOURCE_EVENT")
    if state.confirmation_complete:
        support.append("CRT_CONFIRMATION_COMPLETE")
    if state.destination_context_known and state.destination_available:
        support.append("AUTHORIZED_DESTINATION_AVAILABLE")
    if meta.readiness is CrtPureEpistemicReadiness.WELL_SUPPORTED:
        support.append("EVIDENCE_WELL_SUPPORTED")

    if adversarial.verdict is CrtPureAdversarialVerdict.FALSIFIED:
        action = CrtPureReasoningAction.ABSTAIN
        thesis = "CRT hypothesis rejected by causal/adversarial evidence"
    elif (
        adversarial.verdict is CrtPureAdversarialVerdict.CHALLENGED
        or state.hypothesis_stage
        not in {
            CrtPureHypothesisStage.CONFIRMED,
            CrtPureHypothesisStage.EXECUTABLE,
        }
    ):
        action = CrtPureReasoningAction.WAIT
        thesis = "CRT hypothesis remains alive but is not yet executable"
    else:
        action = CrtPureReasoningAction.EXECUTE
        thesis = "source-certified CRT hypothesis passed causal and adversarial checks"

    why = (
        f"ACTION:{action.value}",
        f"ADVERSARIAL:{adversarial.verdict.value}",
        f"METACOGNITION:{meta.readiness.value}",
        *support,
        *adversarial.hard_findings,
        *adversarial.challenge_findings,
    )

    return CrtPureReasoningDecision(
        action=action,
        thesis=thesis,
        supporting_evidence=tuple(support),
        contradictions=adversarial.hard_findings,
        uncertainty=adversarial.challenge_findings,
        adversarial_verdict=adversarial.verdict,
        metacognitive_readiness=meta.readiness,
        auditable_why=tuple(dict.fromkeys(why)),
    )


_ALLOWED_TRANSITIONS: dict[
    CrtPureHypothesisStage,
    tuple[CrtPureHypothesisStage, ...],
] = {
    CrtPureHypothesisStage.OBSERVED_EVENT: (
        CrtPureHypothesisStage.HYPOTHESIS_FORMING,
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.HYPOTHESIS_FORMING: (
        CrtPureHypothesisStage.AWAITING_CONFIRMATION,
        CrtPureHypothesisStage.THESIS_INVALIDATED,
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.AWAITING_CONFIRMATION: (
        CrtPureHypothesisStage.CONFIRMED,
        CrtPureHypothesisStage.THESIS_INVALIDATED,
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.CONFIRMED: (
        CrtPureHypothesisStage.EXECUTABLE,
        CrtPureHypothesisStage.THESIS_WEAKENING,
        CrtPureHypothesisStage.THESIS_INVALIDATED,
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.EXECUTABLE: (
        CrtPureHypothesisStage.POSITION_ACTIVE,
        CrtPureHypothesisStage.THESIS_INVALIDATED,
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.POSITION_ACTIVE: (
        CrtPureHypothesisStage.THESIS_STRENGTHENING,
        CrtPureHypothesisStage.THESIS_STABLE,
        CrtPureHypothesisStage.THESIS_WEAKENING,
        CrtPureHypothesisStage.THESIS_INVALIDATED,
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.THESIS_STRENGTHENING: (
        CrtPureHypothesisStage.THESIS_STABLE,
        CrtPureHypothesisStage.THESIS_WEAKENING,
        CrtPureHypothesisStage.THESIS_INVALIDATED,
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.THESIS_STABLE: (
        CrtPureHypothesisStage.THESIS_STRENGTHENING,
        CrtPureHypothesisStage.THESIS_WEAKENING,
        CrtPureHypothesisStage.THESIS_INVALIDATED,
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.THESIS_WEAKENING: (
        CrtPureHypothesisStage.THESIS_STABLE,
        CrtPureHypothesisStage.THESIS_INVALIDATED,
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.THESIS_INVALIDATED: (
        CrtPureHypothesisStage.THESIS_KILLED,
    ),
    CrtPureHypothesisStage.THESIS_KILLED: (),
}


def transition_hypothesis(
    current: CrtPureHypothesisStage,
    next_stage: CrtPureHypothesisStage,
) -> CrtPureHypothesisStage:
    if next_stage not in _ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"invalid CRT hypothesis transition: {current}->{next_stage}")
    return next_stage
