"""Integrated pre-strategy Master Cognitive Frame for QORE Capitalizer V2.

The frame unifies all cognitive context that must exist before source-faithful ICT/TTrades entry
logic is allowed to decide. It deliberately does not select a trade or grant capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_adversarial_reasoning_v2 import (
    CapitalizerAdversarialAssessment,
    CapitalizerAdversarialCandidateFacts,
    assess_adversarial_candidate,
)
from qore.infrastructure.trader_lab.capitalizer_cognitive_pressure import (
    CapitalizerCognitivePressureAssessment,
    CapitalizerCognitivePressureFacts,
    assess_cognitive_pressure,
)
from qore.infrastructure.trader_lab.capitalizer_cross_market_causality import (
    CapitalizerCrossMarketCausalGraph,
)
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateAssessment,
    CapitalizerCognitiveGateFacts,
    assess_cognitive_gate,
)
from qore.infrastructure.trader_lab.capitalizer_global_world_model import (
    CapitalizerGlobalWorldModel,
)
from qore.infrastructure.trader_lab.capitalizer_market_brain_registry import (
    CapitalizerMarketBrainRegistry,
)
from qore.infrastructure.trader_lab.capitalizer_master_brain import (
    CapitalizerMasterBrainAssessment,
    assess_master_brain,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
    CapitalizerAttentionState,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerMetacognitiveAssessment,
    CapitalizerMetacognitiveFacts,
    assess_metacognition,
)
from qore.infrastructure.trader_lab.capitalizer_opportunity_competition import (
    CapitalizerOpportunityCompetitionState,
    build_opportunity_competition_state,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerMarketPerceptionSnapshot,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_position_supervisor import (
    CapitalizerPortfolioPositionAssessment,
    assess_portfolio_positions,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeAssessment,
    CapitalizerRegimeHypothesis,
    assess_regime,
)
from qore.infrastructure.trader_lab.capitalizer_session_journey_intelligence import (
    CapitalizerSessionJourneyAssessment,
    assess_session_journey,
)

@dataclass(frozen=True, slots=True)
class CapitalizerCandidateCognitiveContext:
    symbol: str
    observed_at: datetime
    failure_state_fingerprint: str | None
    evidence_provenance_complete: bool
    destination_context_known: bool
    destination_available: bool
    event_is_fresh: bool
    genuinely_new_causal_event: bool

    def __post_init__(self) -> None:
        if self.symbol not in NINE_MARKET_UNIVERSE:
            raise ValueError("candidate context symbol outside Capitalizer universe")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("candidate context timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CapitalizerCandidateCognitiveEvaluation:
    symbol: str
    metacognition: CapitalizerMetacognitiveAssessment
    adversarial: CapitalizerAdversarialAssessment
    gate: CapitalizerCognitiveGateAssessment


@dataclass(frozen=True, slots=True)
class CapitalizerMasterCognitiveFrame:
    world: CapitalizerGlobalWorldModel
    master: CapitalizerMasterBrainAssessment
    market_registry: CapitalizerMarketBrainRegistry
    session_journey: CapitalizerSessionJourneyAssessment
    perceptions: tuple[CapitalizerMarketPerceptionSnapshot, ...]
    regimes: tuple[CapitalizerRegimeAssessment, ...]
    cross_market_graph: CapitalizerCrossMarketCausalGraph
    competition: CapitalizerOpportunityCompetitionState
    portfolio_positions: CapitalizerPortfolioPositionAssessment
    cognitive_pressure: CapitalizerCognitivePressureAssessment
    candidate_evaluations: tuple[CapitalizerCandidateCognitiveEvaluation, ...]
    strategy_decision_allowed: bool = False
    outcome_visibility: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.strategy_decision_allowed:
            raise ValueError("pre-strategy cognitive frame cannot select/authorize entries")
        if self.outcome_visibility:
            raise ValueError("pre-strategy cognitive frame cannot see future outcomes")
        if self.grants_capital_authority:
            raise ValueError("Master Cognitive Frame cannot grant capital authority")


def build_master_cognitive_frame(
    *,
    world: CapitalizerGlobalWorldModel,
    perceptions: tuple[CapitalizerMarketPerceptionSnapshot, ...],
    regime_hypotheses: tuple[CapitalizerRegimeHypothesis, ...],
    cross_market_graph: CapitalizerCrossMarketCausalGraph,
    pressure_facts: CapitalizerCognitivePressureFacts,
    candidate_contexts: tuple[CapitalizerCandidateCognitiveContext, ...] = (),
) -> CapitalizerMasterCognitiveFrame:
    """Build the complete cognitive context that precedes strategy-source reasoning."""

    perception_symbols = tuple(item.symbol for item in perceptions)
    if (
        len(perception_symbols) != 9
        or frozenset(perception_symbols) != NINE_MARKET_UNIVERSE
        or len(set(perception_symbols)) != 9
    ):
        raise ValueError("Master frame requires one perception snapshot per frozen market")
    for perception in perceptions:
        if perception.observed_at > world.observed_at:
            raise ValueError("future perception snapshot cannot enter Master frame")

    regime_symbols = tuple(item.symbol for item in regime_hypotheses)
    if (
        len(regime_symbols) != 9
        or frozenset(regime_symbols) != NINE_MARKET_UNIVERSE
        or len(set(regime_symbols)) != 9
    ):
        raise ValueError("Master frame requires one regime hypothesis per frozen market")
    for hypothesis in regime_hypotheses:
        if hypothesis.observed_at > world.observed_at:
            raise ValueError("future regime hypothesis cannot enter Master frame")

    if cross_market_graph.observed_at > world.observed_at:
        raise ValueError("future cross-market graph cannot enter Master frame")

    context_symbols = tuple(item.symbol for item in candidate_contexts)
    if len(set(context_symbols)) != len(context_symbols):
        raise ValueError("duplicate candidate cognitive context")
    if frozenset(context_symbols) != frozenset(world.decision_symbols):
        raise ValueError("candidate contexts must match DECISION markets exactly")
    for context in candidate_contexts:
        if context.observed_at > world.observed_at:
            raise ValueError("future candidate context cannot enter Master frame")

    registry = CapitalizerMarketBrainRegistry(
        tuple(item.brain for item in world.markets)
    )
    session_journey = assess_session_journey(
        session_brain=world.session_brain,
        journey=world.journey,
        loss_memory=world.loss_memory,
    )
    pressure = assess_cognitive_pressure(pressure_facts)
    competition = build_opportunity_competition_state(world)
    perception_by_symbol = {item.symbol: item for item in perceptions}
    regime_by_symbol = {
        item.symbol: assess_regime(item) for item in regime_hypotheses
    }
    world_by_symbol = {item.symbol: item for item in world.markets}

    candidate_evaluations: list[CapitalizerCandidateCognitiveEvaluation] = []
    for context in sorted(candidate_contexts, key=lambda item: item.symbol):
        market = world_by_symbol[context.symbol]
        if market.attention is not CapitalizerAttentionState.DECISION:
            raise ValueError("candidate context requires DECISION attention")
        if (
            market.hypothesis_id is None
            or market.source_event_id is None
            or market.hypothesis_stage is None
        ):
            raise ValueError("DECISION market requires complete hypothesis identity")

        perception = perception_by_symbol[context.symbol]
        regime = regime_by_symbol[context.symbol]
        metacognition = assess_metacognition(
            CapitalizerMetacognitiveFacts(
                knowledge=market.knowledge,
                perception_status=perception.assessment.status,
                regime_resolution=regime.resolution,
                contradictions=market.contradictions,
                evidence_provenance_complete=context.evidence_provenance_complete,
                destination_context_known=context.destination_context_known,
            )
        )
        adversarial = assess_adversarial_candidate(
            facts=CapitalizerAdversarialCandidateFacts(
                symbol=context.symbol,
                hypothesis_id=market.hypothesis_id,
                source_event_id=market.source_event_id,
                failure_state_fingerprint=context.failure_state_fingerprint,
                metacognition=metacognition,
                perception_status=perception.assessment.status,
                regime_resolution=regime.resolution,
                destination_context_known=context.destination_context_known,
                destination_available=context.destination_available,
                event_is_fresh=context.event_is_fresh,
                genuinely_new_causal_event=context.genuinely_new_causal_event,
                contradictions=market.contradictions,
            ),
            world=world,
            cross_market_graph=cross_market_graph,
        )
        gate = assess_cognitive_gate(
            facts=CapitalizerCognitiveGateFacts(
                symbol=context.symbol,
                attention=market.attention,
                hypothesis_stage=market.hypothesis_stage,
                metacognition=metacognition,
                adversarial=adversarial,
                cognitive_pressure=pressure.pressure,
            ),
            competition=competition,
        )
        candidate_evaluations.append(
            CapitalizerCandidateCognitiveEvaluation(
                symbol=context.symbol,
                metacognition=metacognition,
                adversarial=adversarial,
                gate=gate,
            )
        )

    return CapitalizerMasterCognitiveFrame(
        world=world,
        master=assess_master_brain(world),
        market_registry=registry,
        session_journey=session_journey,
        perceptions=tuple(sorted(perceptions, key=lambda item: item.symbol)),
        regimes=tuple(
            sorted(
                (assess_regime(item) for item in regime_hypotheses),
                key=lambda item: item.symbol,
            )
        ),
        cross_market_graph=cross_market_graph,
        competition=competition,
        portfolio_positions=assess_portfolio_positions(world),
        cognitive_pressure=pressure,
        candidate_evaluations=tuple(candidate_evaluations),
    )
