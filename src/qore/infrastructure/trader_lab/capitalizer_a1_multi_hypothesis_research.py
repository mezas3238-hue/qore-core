"""Lossless multi-hypothesis A1 research census; never slot arbitration.

The single-hypothesis World Model cannot represent two DECISION hypotheses
for one market and instant. Evaluate each evidenced alternative independently
against the same immutable nine-market as-of evidence instead of dropping any.
Other DECISION markets are temporarily FOCUSED in each *projection*, not
rejected. Consequently these gates are NOT globally arbitrated trade choices.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_a1_full_frame_research_adapter import (
    A1CausalSettledMemory,
    A1FullFrameResearchDecision,
    A1SourceBinding,
    evaluate_full_frame_research_batch,
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
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerAttentionState,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_frame import (
    CapitalizerCandidateCognitiveContext,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerMarketPerceptionSnapshot,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeHypothesis,
)

IDENTITY = "QORE_SCALPER_A1_MULTI_HYPOTHESIS_CENSUS_RESEARCH_ONLY"


def _aware(at: datetime) -> datetime:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("source ancestry must be timezone-aware")
    return at


@dataclass(frozen=True, slots=True)
class A1SourceHypothesisAlternative:
    """One true source candidate with its own H1 / M15 / M1 causal ancestry."""

    binding: A1SourceBinding
    context: CapitalizerCandidateCognitiveContext
    hypothesis_id: str
    source_event_id: str
    source_rule_id: str
    h1_confirmed_at: datetime
    m15_confirmed_at: datetime
    m1_confirmed_at: datetime

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.source_event_id or not self.source_rule_id:
            raise ValueError("hypothesis and source rule provenance required")
        if self.binding.symbol != self.context.symbol:
            raise ValueError("candidate source/context market mismatch")
        if not self.context.evidence_provenance_complete:
            raise ValueError("candidate requires actual evidence provenance")
        if not (
            _aware(self.h1_confirmed_at)
            <= _aware(self.m15_confirmed_at)
            <= _aware(self.m1_confirmed_at)
            == _aware(self.binding.confirmed_at)
            == _aware(self.context.observed_at)
        ):
            raise ValueError("H1/M15/M1 ancestry must be closed before decision")


@dataclass(frozen=True, slots=True)
class A1MultiHypothesisBarrier:
    world: CapitalizerGlobalWorldModel
    perceptions: tuple[CapitalizerMarketPerceptionSnapshot, ...]
    regime_hypotheses: tuple[CapitalizerRegimeHypothesis, ...]
    cross_market_graph: CapitalizerCrossMarketCausalGraph
    pressure_facts: CapitalizerCognitivePressureFacts
    alternatives: tuple[A1SourceHypothesisAlternative, ...]
    expected_source_ids: tuple[str, ...]

    @property
    def observed_at(self) -> datetime:
        return self.world.observed_at


@dataclass(frozen=True, slots=True)
class A1MultiHypothesisEvidence:
    identity: str
    decisions: tuple[A1FullFrameResearchDecision, ...]
    evaluated_alternatives: int
    barriers_evaluated: int
    source_ids: tuple[str, ...]
    pass_to_strategy: int
    wait: int
    abstain: int
    global_opportunity_arbitration_resolved: bool = False
    trade_selected: bool = False
    economic_admission_changed: bool = False
    actual_historical_replay_completed: bool = False

    def __post_init__(self) -> None:
        ids = tuple(row.source_opportunity_id for row in self.decisions)
        if self.identity != IDENTITY or ids != self.source_ids:
            raise ValueError("multi-hypothesis source identity parity broken")
        if len(ids) != self.evaluated_alternatives or len(set(ids)) != len(ids):
            raise ValueError("source opportunities were duplicated or lost")
        if self.pass_to_strategy + self.wait + self.abstain != len(ids):
            raise ValueError("cognitive disposition totals must include every source")
        if (
            self.global_opportunity_arbitration_resolved
            or self.trade_selected
            or self.economic_admission_changed
            or self.actual_historical_replay_completed
        ):
            raise ValueError("independent A1 projections cannot claim real execution")


def replay_multi_hypothesis_evidence(
    *,
    barriers: tuple[A1MultiHypothesisBarrier, ...],
    chosen_settlements: A1CausalSettledMemory,
) -> A1MultiHypothesisEvidence:
    """Keep every M1 alternative under exact time ordering, without selecting.

    A candidate-specific world projection calls the real nine-market cognitive
    frame but cannot arbitrate simultaneous alternatives against one another.
    The experimental results must NOT be interpreted as portfolio admissions.
    """
    if not barriers:
        raise ValueError("multi-hypothesis replay requires observed barriers")
    last_at: datetime | None = None
    seen_ids: set[str] = set()
    decisions: list[A1FullFrameResearchDecision] = []
    for barrier in barriers:
        at = _aware(barrier.observed_at)
        if last_at is not None and at <= last_at:
            raise ValueError("time reversal or ungrouped simultaneous barrier")
        last_at = at
        if not barrier.alternatives:
            raise ValueError("evidence barrier cannot have zero candidates")
        provided_ids = tuple(
            item.binding.source_opportunity_id for item in barrier.alternatives
        )
        if (
            len(set(provided_ids)) != len(provided_ids)
            or set(provided_ids) & seen_ids
            or len(barrier.expected_source_ids) != len(barrier.alternatives)
            or len(set(barrier.expected_source_ids)) != len(barrier.expected_source_ids)
            or set(provided_ids) != set(barrier.expected_source_ids)
        ):
            raise ValueError("source census mismatch, duplication or dropped M1 alternative")
        seen_ids.update(provided_ids)
        source_symbols = {item.binding.symbol for item in barrier.alternatives}
        if source_symbols != set(barrier.world.decision_symbols):
            raise ValueError("DECISION markets and source alternatives must match")

        markets = {item.symbol: item for item in barrier.world.markets}
        for alt in sorted(
            barrier.alternatives,
            key=lambda item: (item.binding.symbol, item.binding.source_opportunity_id),
        ):
            if alt.binding.confirmed_at != at or alt.context.observed_at != at:
                raise ValueError("source candidate outside as-of M1 decision barrier")
            reference = markets[alt.binding.symbol]
            if reference.attention is not CapitalizerAttentionState.DECISION:
                raise ValueError("candidate market must already be DECISION")
            projected_markets = tuple(
                (
                    replace(
                        row,
                        hypothesis_id=alt.hypothesis_id,
                        source_event_id=alt.source_event_id,
                    )
                    if row.symbol == alt.binding.symbol
                    else replace(row, attention=CapitalizerAttentionState.FOCUSED)
                    if row.attention is CapitalizerAttentionState.DECISION
                    else row
                )
                for row in barrier.world.markets
            )
            projected_world = replace(barrier.world, markets=projected_markets)
            assessed = evaluate_full_frame_research_batch(
                world=projected_world,
                perceptions=barrier.perceptions,
                regime_hypotheses=barrier.regime_hypotheses,
                cross_market_graph=barrier.cross_market_graph,
                pressure_facts=barrier.pressure_facts,
                contexts=(alt.context,),
                source_bindings=(alt.binding,),
                settled_memory=chosen_settlements,
            )
            if len(assessed) != 1:
                raise ValueError("hypothesis projection did not yield exactly one WHY")
            decisions.extend(assessed)

    return A1MultiHypothesisEvidence(
        identity=IDENTITY,
        decisions=tuple(decisions),
        evaluated_alternatives=len(decisions),
        barriers_evaluated=len(barriers),
        source_ids=tuple(item.source_opportunity_id for item in decisions),
        pass_to_strategy=sum(d.cognitive_gate == "PASS_TO_STRATEGY" for d in decisions),
        wait=sum(d.cognitive_gate == "WAIT" for d in decisions),
        abstain=sum(d.cognitive_gate == "ABSTAIN" for d in decisions),
    )
