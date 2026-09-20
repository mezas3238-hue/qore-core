"""Attention-state reasoning for QORE Capitalizer."""

from __future__ import annotations

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerAttentionState,
    CapitalizerHypothesisStage,
)

_POSITION_STAGES = {
    CapitalizerHypothesisStage.POSITION_ACTIVE,
    CapitalizerHypothesisStage.THESIS_STRENGTHENING,
    CapitalizerHypothesisStage.THESIS_STABLE,
    CapitalizerHypothesisStage.THESIS_WEAKENING,
}

_DECISION_STAGES = {
    CapitalizerHypothesisStage.CONFIRMED,
    CapitalizerHypothesisStage.EXECUTABLE,
}

_FOCUSED_STAGES = {
    CapitalizerHypothesisStage.HYPOTHESIS_FORMING,
    CapitalizerHypothesisStage.AWAITING_CONFIRMATION,
}


def derive_attention_state(
    *,
    has_relevant_event: bool,
    hypothesis_stage: CapitalizerHypothesisStage | None,
    knowledge: CapitalizerKnowledgeState,
    position_open: bool,
) -> CapitalizerAttentionState:
    """Allocate cognition without ranking markets or using future outcomes."""

    if position_open:
        if hypothesis_stage not in _POSITION_STAGES:
            raise ValueError("open position requires an active position-stage hypothesis")
        return CapitalizerAttentionState.POSITION

    if hypothesis_stage in {
        CapitalizerHypothesisStage.THESIS_INVALIDATED,
        CapitalizerHypothesisStage.THESIS_KILLED,
    }:
        return CapitalizerAttentionState.BACKGROUND

    if hypothesis_stage in _DECISION_STAGES:
        if knowledge is CapitalizerKnowledgeState.KNOWN:
            return CapitalizerAttentionState.DECISION
        return CapitalizerAttentionState.FOCUSED

    if hypothesis_stage in _FOCUSED_STAGES:
        return CapitalizerAttentionState.FOCUSED

    if (
        hypothesis_stage is CapitalizerHypothesisStage.OBSERVED_EVENT
        or has_relevant_event
    ):
        return CapitalizerAttentionState.WATCH

    return CapitalizerAttentionState.BACKGROUND
