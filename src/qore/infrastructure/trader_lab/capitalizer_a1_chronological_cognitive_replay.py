"""Opt-in A1 chronological cognition spine: evidence in, WHY out, never trades.

Does not build synthetic nine-market evidence from M5 or retrospective census states.
Each observed barrier must be provided independently from causal synchronized feeds.
The replay is an observation/ablation harness, not an economic portfolio simulator.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_frame import (
    CapitalizerCandidateCognitiveContext,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerMarketPerceptionSnapshot,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeHypothesis,
)

IDENTITY = "QORE_SCALPER_A1_CHRONOLOGICAL_EVIDENCE_REPLAY_RESEARCH_ONLY"


@dataclass(frozen=True, slots=True)
class A1ObservedNineMarketBarrier:
    """One genuine as-of global evidence batch, never a manufactured snapshot."""

    world: CapitalizerGlobalWorldModel
    perceptions: tuple[CapitalizerMarketPerceptionSnapshot, ...]
    regime_hypotheses: tuple[CapitalizerRegimeHypothesis, ...]
    cross_market_graph: CapitalizerCrossMarketCausalGraph
    pressure_facts: CapitalizerCognitivePressureFacts
    contexts: tuple[CapitalizerCandidateCognitiveContext, ...]
    source_bindings: tuple[A1SourceBinding, ...]

    @property
    def observed_at(self) -> datetime:
        return self.world.observed_at


@dataclass(frozen=True, slots=True)
class A1CognitiveReplayEvidence:
    identity: str
    decisions: tuple[A1FullFrameResearchDecision, ...]
    source_opportunities: int
    barriers_evaluated: int
    pass_to_strategy: int
    wait: int
    abstain: int
    no_execution_performed: bool = True
    no_economic_admission_changed: bool = True

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected A1 research replay identity")
        if len(self.decisions) != self.source_opportunities:
            raise ValueError("cognitive replay silently lost source opportunities")
        if self.pass_to_strategy + self.wait + self.abstain != len(self.decisions):
            raise ValueError("cognitive replay disposition accounting mismatch")
        if not self.no_execution_performed or not self.no_economic_admission_changed:
            raise ValueError("A1 cognition replay cannot grant execution or change economics")


def replay_observed_cognitive_barriers(
    *,
    barriers: tuple[A1ObservedNineMarketBarrier, ...],
    chosen_settlements: A1CausalSettledMemory,
) -> A1CognitiveReplayEvidence:
    """Run the REAL Master Frame once per observed barrier, not simulated fills.

    Tie policy: same-timestamp candidates across markets belong in ONE barrier.
    Multiple source candidates for one market/time are NOT arbitrarily dropped;
    they require a distinct research contract and fail closed here.
    """
    if not barriers:
        raise ValueError("A1 chronological replay requires observed evidence")
    prev: datetime | None = None
    seen: set[str] = set()
    results: list[A1FullFrameResearchDecision] = []
    total = 0
    for barrier in barriers:
        at = barrier.observed_at
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("chronological barrier time must be timezone-aware")
        if prev is not None and at <= prev:
            raise ValueError("barriers must be strictly chronological, ties grouped")
        prev = at
        if not barrier.source_bindings:
            raise ValueError("A1 barrier must name every source opportunity")
        ids = tuple(item.source_opportunity_id for item in barrier.source_bindings)
        if len(set(ids)) != len(ids) or set(ids) & seen:
            raise ValueError("reused source opportunity across cognitive barriers")
        seen.update(ids)
        decisions = evaluate_full_frame_research_batch(
            world=barrier.world,
            perceptions=barrier.perceptions,
            regime_hypotheses=barrier.regime_hypotheses,
            cross_market_graph=barrier.cross_market_graph,
            pressure_facts=barrier.pressure_facts,
            contexts=barrier.contexts,
            source_bindings=barrier.source_bindings,
            settled_memory=chosen_settlements,
        )
        if {item.source_opportunity_id for item in decisions} != set(ids):
            raise ValueError("cognitive evidence source identity parity failed")
        total += len(ids)
        results.extend(decisions)

    return A1CognitiveReplayEvidence(
        identity=IDENTITY,
        decisions=tuple(results),
        source_opportunities=total,
        barriers_evaluated=len(barriers),
        pass_to_strategy=sum(x.cognitive_gate == "PASS_TO_STRATEGY" for x in results),
        wait=sum(x.cognitive_gate == "WAIT" for x in results),
        abstain=sum(x.cognitive_gate == "ABSTAIN" for x in results),
    )
