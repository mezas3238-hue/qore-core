"""Master Brain synthesis for QORE Capitalizer.

This layer does not rank candidates or authorize execution. It converts the complete Global
World Model into one auditable cognitive overview so downstream reasoning cannot treat a market
as if the rest of the trading day did not exist.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_global_world_model import (
    CapitalizerGlobalWorldModel,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerAttentionState,
)


@dataclass(frozen=True, slots=True)
class CapitalizerMasterBrainAssessment:
    current_session: str
    execution_slots_remaining: int
    background_symbols: tuple[str, ...]
    watch_symbols: tuple[str, ...]
    focused_symbols: tuple[str, ...]
    decision_symbols: tuple[str, ...]
    position_symbols: tuple[str, ...]
    known_symbols: tuple[str, ...]
    partial_symbols: tuple[str, ...]
    unknown_symbols: tuple[str, ...]
    conflicted_symbols: tuple[str, ...]
    active_hypothesis_ids: tuple[str, ...]
    unresolved_failure_fingerprints: tuple[str, ...]
    exposed_factors: tuple[str, ...]
    causal_warnings: tuple[str, ...]
    grants_capital_authority: bool = False
    ranks_opportunities: bool = False

    def __post_init__(self) -> None:
        if self.grants_capital_authority:
            raise ValueError("Master Brain assessment cannot grant capital authority")
        if self.ranks_opportunities:
            raise ValueError("Master Brain synthesis cannot rank opportunities before arbiter")


def _symbols_by_attention(
    world: CapitalizerGlobalWorldModel,
    attention: CapitalizerAttentionState,
) -> tuple[str, ...]:
    return tuple(
        sorted(item.symbol for item in world.markets if item.attention is attention)
    )


def _symbols_by_knowledge(
    world: CapitalizerGlobalWorldModel,
    knowledge: CapitalizerKnowledgeState,
) -> tuple[str, ...]:
    return tuple(
        sorted(item.symbol for item in world.markets if item.knowledge is knowledge)
    )


def assess_master_brain(
    world: CapitalizerGlobalWorldModel,
) -> CapitalizerMasterBrainAssessment:
    """Summarize complete-day causal state without selecting an opportunity."""

    warnings: list[str] = []
    if world.execution_slots_remaining <= 0:
        warnings.append("SESSION_EXECUTION_BUDGET_EXHAUSTED")
    if world.unresolved_failure_fingerprints:
        warnings.append("UNRESOLVED_FAILURE_MEMORY_PRESENT")
    if any(item.contradictions for item in world.markets):
        warnings.append("MARKET_CONTRADICTIONS_PRESENT")
    if any(
        item.knowledge in {
            CapitalizerKnowledgeState.UNKNOWN,
            CapitalizerKnowledgeState.CONFLICTED,
        }
        and item.attention
        in {
            CapitalizerAttentionState.FOCUSED,
            CapitalizerAttentionState.DECISION,
            CapitalizerAttentionState.POSITION,
        }
        for item in world.markets
    ):
        warnings.append("HIGH_ATTENTION_WITH_UNCERTAIN_KNOWLEDGE")
    if len(world.decision_symbols) > world.execution_slots_remaining:
        warnings.append("DECISION_DEMAND_EXCEEDS_AVAILABLE_SLOTS")

    active_hypothesis_ids = tuple(
        sorted(
            item.hypothesis_id
            for item in world.markets
            if item.hypothesis_id is not None
        )
    )
    exposed_factors = tuple(
        item.factor for item in world.factor_exposure_state if item.gross_r > 0
    )

    return CapitalizerMasterBrainAssessment(
        current_session=world.current_session.value,
        execution_slots_remaining=world.execution_slots_remaining,
        background_symbols=_symbols_by_attention(
            world,
            CapitalizerAttentionState.BACKGROUND,
        ),
        watch_symbols=_symbols_by_attention(world, CapitalizerAttentionState.WATCH),
        focused_symbols=_symbols_by_attention(
            world,
            CapitalizerAttentionState.FOCUSED,
        ),
        decision_symbols=world.decision_symbols,
        position_symbols=world.position_symbols,
        known_symbols=_symbols_by_knowledge(world, CapitalizerKnowledgeState.KNOWN),
        partial_symbols=_symbols_by_knowledge(world, CapitalizerKnowledgeState.PARTIAL),
        unknown_symbols=_symbols_by_knowledge(world, CapitalizerKnowledgeState.UNKNOWN),
        conflicted_symbols=_symbols_by_knowledge(
            world,
            CapitalizerKnowledgeState.CONFLICTED,
        ),
        active_hypothesis_ids=active_hypothesis_ids,
        unresolved_failure_fingerprints=tuple(
            sorted(world.unresolved_failure_fingerprints)
        ),
        exposed_factors=exposed_factors,
        causal_warnings=tuple(warnings),
    )
