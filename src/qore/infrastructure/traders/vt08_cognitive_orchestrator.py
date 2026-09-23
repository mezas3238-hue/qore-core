"""Research/shadow-only cognitive orchestration for VT08 Forex V1."""
from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.traders.vt08_cognitive_hypothesis import (
    Vt08Hypothesis,
    advance_hypothesis,
)
from qore.infrastructure.traders.vt08_cognitive_journey_intelligence import (
    Vt08JourneyAssessment,
    assess_journey,
)
from qore.infrastructure.traders.vt08_cognitive_position_intelligence import (
    RESEARCH_UNCALIBRATED_POSITION_POLICY,
    Vt08PositionDecision,
    Vt08PositionPolicy,
    Vt08PositionSnapshot,
    decide_position,
)
from qore.infrastructure.traders.vt08_cognitive_reasoning import (
    Vt08ReasoningDecision,
    reason,
)
from qore.infrastructure.traders.vt08_cognitive_situation_model import (
    Vt08ForexSituationModel,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08HypothesisState,
)


@dataclass(frozen=True, slots=True)
class Vt08CognitiveEvaluation:
    situation: Vt08ForexSituationModel
    decision: Vt08ReasoningDecision
    hypothesis: Vt08Hypothesis


@dataclass(frozen=True, slots=True)
class Vt08InTradeCognitiveEvaluation:
    situation: Vt08ForexSituationModel
    journey: Vt08JourneyAssessment
    position_decision: Vt08PositionDecision


def evaluate_cognitive_hypothesis(
    *,
    situation: Vt08ForexSituationModel,
    source_fingerprint: str,
    hypothesis: Vt08Hypothesis | None = None,
) -> Vt08CognitiveEvaluation:
    current = hypothesis or Vt08Hypothesis(
        source_fingerprint=source_fingerprint,
        state=Vt08HypothesisState.FORMING,
    )
    if current.source_fingerprint != source_fingerprint:
        raise ValueError("VT08 cognitive evaluation source fingerprint drift")
    decision = reason(situation)
    confirmation_complete = (
        situation.cisd_state in {"CONFIRMED", "NOT_REQUIRED_BY_BOUND_PROFILE"}
        and situation.protected_swing_state
        in {"CONFIRMED", "NOT_REQUIRED_BY_BOUND_PROFILE"}
    )
    updated = advance_hypothesis(
        current,
        action=decision.action,
        confirmation_complete=confirmation_complete,
    )
    return Vt08CognitiveEvaluation(
        situation=situation,
        decision=decision,
        hypothesis=updated,
    )


def evaluate_in_trade_cognition(
    *,
    situation: Vt08ForexSituationModel,
    position: Vt08PositionSnapshot,
    policy: Vt08PositionPolicy = RESEARCH_UNCALIBRATED_POSITION_POLICY,
) -> Vt08InTradeCognitiveEvaluation:
    if situation.side != position.side:
        raise ValueError("VT08 in-trade cognition side mismatch")
    journey = assess_journey(situation)
    position_decision = decide_position(
        position=position,
        journey=journey,
        policy=policy,
    )
    return Vt08InTradeCognitiveEvaluation(
        situation=situation,
        journey=journey,
        position_decision=position_decision,
    )
