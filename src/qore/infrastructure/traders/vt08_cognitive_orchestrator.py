"""Research/shadow-only cognitive orchestration for VT08 Forex V1."""
from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.traders.vt08_cognitive_hypothesis import (
    Vt08Hypothesis,
    advance_hypothesis,
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
