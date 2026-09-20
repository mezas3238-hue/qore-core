"""Pre-strategy opportunity competition state for QORE Capitalizer.

This module does not choose a winner. It determines which DECISION-state opportunities are
eligible to enter arbitration and whether demand exceeds the remaining MAX3 session slots.
The actual source-faithful selection policy is frozen only after ICT/TTrades strategy closure.
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
    CapitalizerHypothesisStage,
)


@dataclass(frozen=True, slots=True)
class CapitalizerCompetitionCandidate:
    symbol: str
    hypothesis_id: str
    source_event_id: str
    knowledge: CapitalizerKnowledgeState
    contradictions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapitalizerOpportunityCompetitionState:
    current_session: str
    available_slots: int
    eligible_candidates: tuple[CapitalizerCompetitionCandidate, ...]
    blocked_symbols: tuple[str, ...]
    block_reasons: tuple[tuple[str, tuple[str, ...]], ...]
    arbitration_required: bool
    winner_selected: bool = False
    outcome_aware_ranking_used: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.winner_selected:
            raise ValueError("pre-strategy competition state cannot select a winner")
        if self.outcome_aware_ranking_used:
            raise ValueError("opportunity competition cannot use future outcomes")
        if self.grants_capital_authority:
            raise ValueError("opportunity competition cannot grant capital authority")


def build_opportunity_competition_state(
    world: CapitalizerGlobalWorldModel,
) -> CapitalizerOpportunityCompetitionState:
    eligible: list[CapitalizerCompetitionCandidate] = []
    blocked: list[tuple[str, tuple[str, ...]]] = []

    for market in sorted(world.markets, key=lambda item: item.symbol):
        if market.attention is not CapitalizerAttentionState.DECISION:
            continue

        reasons: list[str] = []
        if market.brain.session is not world.current_session:
            reasons.append("OUTSIDE_CURRENT_SESSION")
        if market.knowledge is not CapitalizerKnowledgeState.KNOWN:
            reasons.append("KNOWLEDGE_NOT_KNOWN")
        if market.contradictions:
            reasons.append("CONTRADICTIONS_PRESENT")
        if market.hypothesis_stage not in {
            CapitalizerHypothesisStage.CONFIRMED,
            CapitalizerHypothesisStage.EXECUTABLE,
        }:
            reasons.append("HYPOTHESIS_NOT_DECISION_READY")
        if market.hypothesis_id is None or market.source_event_id is None:
            reasons.append("HYPOTHESIS_IDENTITY_MISSING")

        if reasons:
            blocked.append((market.symbol, tuple(reasons)))
            continue

        eligible.append(
            CapitalizerCompetitionCandidate(
                symbol=market.symbol,
                hypothesis_id=market.hypothesis_id,
                source_event_id=market.source_event_id,
                knowledge=market.knowledge,
                contradictions=market.contradictions,
            )
        )

    available_slots = world.execution_slots_remaining
    return CapitalizerOpportunityCompetitionState(
        current_session=world.current_session.value,
        available_slots=available_slots,
        eligible_candidates=tuple(eligible),
        blocked_symbols=tuple(symbol for symbol, _ in blocked),
        block_reasons=tuple(blocked),
        arbitration_required=len(eligible) > available_slots,
    )
