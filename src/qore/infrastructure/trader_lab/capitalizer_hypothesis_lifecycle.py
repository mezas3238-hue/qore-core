"""Deterministic hypothesis lifecycle for QORE Capitalizer."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerHypothesisStage,
)

_ALLOWED: dict[CapitalizerHypothesisStage, frozenset[CapitalizerHypothesisStage]] = {
    CapitalizerHypothesisStage.OBSERVED_EVENT: frozenset(
        {
            CapitalizerHypothesisStage.HYPOTHESIS_FORMING,
            CapitalizerHypothesisStage.THESIS_KILLED,
        }
    ),
    CapitalizerHypothesisStage.HYPOTHESIS_FORMING: frozenset(
        {
            CapitalizerHypothesisStage.AWAITING_CONFIRMATION,
            CapitalizerHypothesisStage.THESIS_INVALIDATED,
            CapitalizerHypothesisStage.THESIS_KILLED,
        }
    ),
    CapitalizerHypothesisStage.AWAITING_CONFIRMATION: frozenset(
        {
            CapitalizerHypothesisStage.CONFIRMED,
            CapitalizerHypothesisStage.THESIS_INVALIDATED,
            CapitalizerHypothesisStage.THESIS_KILLED,
        }
    ),
    CapitalizerHypothesisStage.CONFIRMED: frozenset(
        {
            CapitalizerHypothesisStage.EXECUTABLE,
            CapitalizerHypothesisStage.THESIS_INVALIDATED,
            CapitalizerHypothesisStage.THESIS_KILLED,
        }
    ),
    CapitalizerHypothesisStage.EXECUTABLE: frozenset(
        {
            CapitalizerHypothesisStage.POSITION_ACTIVE,
            CapitalizerHypothesisStage.THESIS_INVALIDATED,
            CapitalizerHypothesisStage.THESIS_KILLED,
        }
    ),
    CapitalizerHypothesisStage.POSITION_ACTIVE: frozenset(
        {
            CapitalizerHypothesisStage.THESIS_STRENGTHENING,
            CapitalizerHypothesisStage.THESIS_STABLE,
            CapitalizerHypothesisStage.THESIS_WEAKENING,
            CapitalizerHypothesisStage.THESIS_INVALIDATED,
            CapitalizerHypothesisStage.THESIS_KILLED,
        }
    ),
    CapitalizerHypothesisStage.THESIS_STRENGTHENING: frozenset(
        {
            CapitalizerHypothesisStage.THESIS_STABLE,
            CapitalizerHypothesisStage.THESIS_WEAKENING,
            CapitalizerHypothesisStage.THESIS_INVALIDATED,
            CapitalizerHypothesisStage.THESIS_KILLED,
        }
    ),
    CapitalizerHypothesisStage.THESIS_STABLE: frozenset(
        {
            CapitalizerHypothesisStage.THESIS_STRENGTHENING,
            CapitalizerHypothesisStage.THESIS_WEAKENING,
            CapitalizerHypothesisStage.THESIS_INVALIDATED,
            CapitalizerHypothesisStage.THESIS_KILLED,
        }
    ),
    CapitalizerHypothesisStage.THESIS_WEAKENING: frozenset(
        {
            CapitalizerHypothesisStage.THESIS_STABLE,
            CapitalizerHypothesisStage.THESIS_INVALIDATED,
            CapitalizerHypothesisStage.THESIS_KILLED,
        }
    ),
    CapitalizerHypothesisStage.THESIS_INVALIDATED: frozenset(
        {CapitalizerHypothesisStage.THESIS_KILLED}
    ),
    CapitalizerHypothesisStage.THESIS_KILLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class CapitalizerHypothesisState:
    hypothesis_id: str
    source_event_id: str
    event_generation: int
    stage: CapitalizerHypothesisStage
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.source_event_id:
            raise ValueError("hypothesis/source identity must be non-empty")
        if self.event_generation < 1:
            raise ValueError("event_generation must be >= 1")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("hypothesis timestamp must be timezone-aware")

    @property
    def terminal(self) -> bool:
        return self.stage is CapitalizerHypothesisStage.THESIS_KILLED


def transition_hypothesis(
    state: CapitalizerHypothesisState,
    *,
    to_stage: CapitalizerHypothesisStage,
    observed_at: datetime,
) -> CapitalizerHypothesisState:
    """Advance a thesis only through an explicitly valid causal transition."""

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("transition timestamp must be timezone-aware")
    if observed_at < state.observed_at:
        raise ValueError("hypothesis lifecycle cannot move backward in time")
    if to_stage not in _ALLOWED[state.stage]:
        raise ValueError(
            f"invalid hypothesis transition: {state.stage.value} -> {to_stage.value}"
        )
    return replace(state, stage=to_stage, observed_at=observed_at)
