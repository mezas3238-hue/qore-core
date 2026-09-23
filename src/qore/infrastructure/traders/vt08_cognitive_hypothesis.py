"""Deterministic hypothesis lifecycle for VT08 Forex Cognitive V1."""
from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08CognitiveAction,
    Vt08HypothesisState,
)


@dataclass(frozen=True, slots=True)
class Vt08Hypothesis:
    source_fingerprint: str
    state: Vt08HypothesisState
    generation: int = 1

    def __post_init__(self) -> None:
        if not self.source_fingerprint:
            raise ValueError("VT08 hypothesis requires source fingerprint")
        if type(self.state) is not Vt08HypothesisState:
            raise ValueError("VT08 hypothesis state must be exact")
        if self.generation < 1:
            raise ValueError("VT08 hypothesis generation must be >=1")


def advance_hypothesis(
    hypothesis: Vt08Hypothesis,
    *,
    action: Vt08CognitiveAction,
    confirmation_complete: bool,
) -> Vt08Hypothesis:
    if hypothesis.state is Vt08HypothesisState.KILLED:
        raise ValueError("killed VT08 hypothesis cannot be resurrected")
    if action is Vt08CognitiveAction.ABSTAIN:
        return Vt08Hypothesis(
            source_fingerprint=hypothesis.source_fingerprint,
            state=Vt08HypothesisState.KILLED,
            generation=hypothesis.generation,
        )
    if action is Vt08CognitiveAction.EXECUTE:
        if not confirmation_complete:
            raise ValueError("VT08 EXECUTE requires complete confirmation")
        return Vt08Hypothesis(
            source_fingerprint=hypothesis.source_fingerprint,
            state=Vt08HypothesisState.EXECUTABLE,
            generation=hypothesis.generation,
        )
    target = (
        Vt08HypothesisState.WAITING
        if confirmation_complete
        else Vt08HypothesisState.FORMING
    )
    return Vt08Hypothesis(
        source_fingerprint=hypothesis.source_fingerprint,
        state=target,
        generation=hypothesis.generation,
    )


def new_rearm_hypothesis(
    killed_or_terminal: Vt08Hypothesis,
    *,
    new_source_fingerprint: str,
) -> Vt08Hypothesis:
    if not new_source_fingerprint:
        raise ValueError("VT08 rearm requires new source fingerprint")
    if new_source_fingerprint == killed_or_terminal.source_fingerprint:
        raise ValueError("VT08 rearm cannot reuse the same source event")
    return Vt08Hypothesis(
        source_fingerprint=new_source_fingerprint,
        state=Vt08HypothesisState.FORMING,
        generation=killed_or_terminal.generation + 1,
    )
