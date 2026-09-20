"""Integrated pre-strategy Master Cognitive Frame for QORE Capitalizer V2.

The frame unifies all cognitive context that must exist before source-faithful ICT/TTrades entry
logic is allowed to decide. It deliberately does not select a trade or grant capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_cognitive_pressure import (
    CapitalizerCognitivePressureAssessment,
    CapitalizerCognitivePressureFacts,
    assess_cognitive_pressure,
)
from qore.infrastructure.trader_lab.capitalizer_cross_market_causality import (
    CapitalizerCrossMarketCausalGraph,
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

    registry = CapitalizerMarketBrainRegistry(
        tuple(item.brain for item in world.markets)
    )
    session_journey = assess_session_journey(
        session_brain=world.session_brain,
        journey=world.journey,
        loss_memory=world.loss_memory,
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
        competition=build_opportunity_competition_state(world),
        portfolio_positions=assess_portfolio_positions(world),
        cognitive_pressure=assess_cognitive_pressure(pressure_facts),
    )
