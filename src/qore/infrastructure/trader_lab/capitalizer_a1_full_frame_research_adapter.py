"""A1 research-only bridge from frozen source identities to real nine-market cognition.

This adapter requires the caller to supply *observed*, synchronized market evidence.
It never builds fake market states, invents epistemic readiness, admits source orders,
ranks trades, mutates memory, sizes risk, or changes the V49/V50-G baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_cognitive_explanation import (
    explain_all_candidates,
)
from qore.infrastructure.trader_lab.capitalizer_cognitive_pressure import (
    CapitalizerCognitivePressureFacts,
)
from qore.infrastructure.trader_lab.capitalizer_cross_market_causality import (
    CapitalizerCrossMarketCausalGraph,
)
from qore.infrastructure.trader_lab.capitalizer_global_world_model import (
    CapitalizerGlobalWorldModel,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_frame import (
    CapitalizerCandidateCognitiveContext,
    build_master_cognitive_frame,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerMarketPerceptionSnapshot,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeHypothesis,
)

IDENTITY = "QORE_SCALPER_A1_NINE_MARKET_FRAME_RESEARCH_ONLY"


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("A1 evidence timestamps must be timezone-aware")
    return value


@dataclass(frozen=True, slots=True)
class A1SourceBinding:
    """A single independently generated source candidate, not a selection."""

    source_opportunity_id: str
    symbol: str
    confirmed_at: datetime

    def __post_init__(self) -> None:
        if not self.source_opportunity_id:
            raise ValueError("source identity is mandatory")
        _aware(self.confirmed_at)


@dataclass(frozen=True, slots=True)
class A1SettledChosenTrade:
    """Only externally proven *executed and settled* trades may be recorded."""

    execution_id: str
    entry_at: datetime
    exit_at: datetime

    def __post_init__(self) -> None:
        if not self.execution_id:
            raise ValueError("settled execution ID is mandatory")
        if _aware(self.exit_at) < _aware(self.entry_at):
            raise ValueError("trade cannot settle before entry")


@dataclass(frozen=True, slots=True)
class A1CausalSettledMemory:
    """Immutable, append-only settlement ledger; no counterfactual outcomes."""

    chosen_settlements: tuple[A1SettledChosenTrade, ...] = ()

    def __post_init__(self) -> None:
        ids = tuple(item.execution_id for item in self.chosen_settlements)
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate settled execution ID")

    def as_of(self, decision_at: datetime) -> tuple[A1SettledChosenTrade, ...]:
        """Strictly earlier closes only: same-clock ties are NOT yet visible."""
        _aware(decision_at)
        return tuple(
            sorted(
                (item for item in self.chosen_settlements if item.exit_at < decision_at),
                key=lambda item: (item.exit_at, item.execution_id),
            )
        )


@dataclass(frozen=True, slots=True)
class A1FullFrameResearchDecision:
    identity: str
    source_opportunity_id: str
    symbol: str
    decision_at: str
    cognitive_gate: str
    why_tokens: tuple[str, ...]
    uncertainty_tokens: tuple[str, ...]
    closed_chosen_history_count: int
    nine_market_frame_invoked: bool = True
    economic_admission_changed: bool = False
    winner_selected: bool = False
    outcome_visible: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or not self.source_opportunity_id:
            raise ValueError("invalid A1 research decision")
        if not self.why_tokens or self.closed_chosen_history_count < 0:
            raise ValueError("A1 trace requires causal explanation/history")
        if (
            not self.nine_market_frame_invoked
            or self.economic_admission_changed
            or self.winner_selected
            or self.outcome_visible
            or self.grants_capital_authority
        ):
            raise ValueError("A1 research bridge cannot claim or grant execution")


def evaluate_full_frame_research_batch(
    *,
    world: CapitalizerGlobalWorldModel,
    perceptions: tuple[CapitalizerMarketPerceptionSnapshot, ...],
    regime_hypotheses: tuple[CapitalizerRegimeHypothesis, ...],
    cross_market_graph: CapitalizerCrossMarketCausalGraph,
    pressure_facts: CapitalizerCognitivePressureFacts,
    contexts: tuple[CapitalizerCandidateCognitiveContext, ...],
    source_bindings: tuple[A1SourceBinding, ...],
    settled_memory: A1CausalSettledMemory,
) -> tuple[A1FullFrameResearchDecision, ...]:
    """Invoke the existing full frame on evidenced snapshots, WITHOUT trading.

    The caller must construct nine actual market snapshots and causal contexts.
    This is not a V50-G economic replay and must not be used to claim PF or density.
    """
    at = _aware(world.observed_at)
    ids = tuple(item.source_opportunity_id for item in source_bindings)
    symbols = tuple(item.symbol for item in source_bindings)
    if len(set(ids)) != len(ids) or len(set(symbols)) != len(symbols):
        raise ValueError("duplicate source ID or competing bindings for one market")
    if frozenset(symbols) != frozenset(world.decision_symbols):
        raise ValueError("source binding must cover exact DECISION markets")
    if any(item.confirmed_at != at for item in source_bindings):
        raise ValueError("source candidate confirmation must match time barrier")
    if any(context.observed_at != at for context in contexts):
        raise ValueError("candidate context must match decision-time barrier")
    if any(not context.evidence_provenance_complete for context in contexts):
        raise ValueError("missing candidate evidence provenance; fail closed")

    # The pre-existing full frame checks nine markets, no future perceptions,
    # regimes, cross-market state and candidate-to-decision identity.
    frame = build_master_cognitive_frame(
        world=world,
        perceptions=perceptions,
        regime_hypotheses=regime_hypotheses,
        cross_market_graph=cross_market_graph,
        pressure_facts=pressure_facts,
        candidate_contexts=contexts,
    )
    explanations = {
        item.symbol: item for item in explain_all_candidates(frame)
    }
    evaluations = {item.symbol: item for item in frame.candidate_evaluations}
    historical_count = len(settled_memory.as_of(at))
    return tuple(
        A1FullFrameResearchDecision(
            identity=IDENTITY,
            source_opportunity_id=binding.source_opportunity_id,
            symbol=binding.symbol,
            decision_at=at.isoformat(),
            cognitive_gate=evaluations[binding.symbol].gate.decision.value,
            why_tokens=explanations[binding.symbol].why_tokens,
            uncertainty_tokens=explanations[binding.symbol].uncertainty_tokens,
            closed_chosen_history_count=historical_count,
        )
        for binding in sorted(source_bindings, key=lambda item: item.source_opportunity_id)
    )
