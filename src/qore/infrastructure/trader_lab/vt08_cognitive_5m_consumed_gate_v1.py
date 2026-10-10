"""Research-only cognitive consumption gate for VT08 5M candidate snapshots.

This does NOT construct/source-select an entry, submit orders, model execution,
choose daily fills or consume a sealed holdout. Architect A supplies causal,
machine-authorized source events; this module only reasons over their observed
Situation snapshots and retains testable per-event cognitive decision lineage.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from qore.infrastructure.traders.vt08_cognitive_5m_research_scope import (
    Vt08FiveMarketResearchSituation,
)
from qore.infrastructure.traders.vt08_cognitive_hypothesis import Vt08Hypothesis
from qore.infrastructure.traders.vt08_cognitive_orchestrator import (
    evaluate_cognitive_hypothesis,
    evaluate_in_trade_cognition,
)
from qore.infrastructure.traders.vt08_cognitive_position_intelligence import (
    RESEARCH_UNCALIBRATED_POSITION_POLICY,
    Vt08PositionSnapshot,
)
from qore.infrastructure.traders.vt08_cognitive_v1_contracts import (
    Vt08CognitiveAction,
    Vt08HypothesisState,
    Vt08PositionAction,
)

GATE_SCHEMA: Final = "qore.vt08.cognitive_5m.consumed_gate.research.v1"


@dataclass(frozen=True, slots=True)
class Vt08CognitiveDecisionTrace:
    market: str
    source_event_id: str
    as_of: datetime
    action: Vt08CognitiveAction
    hypothesis_state: Vt08HypothesisState
    reason_codes: tuple[str, ...]
    situation_fingerprint: str
    decision_fingerprint: str
    strategy_identity_fingerprint: str
    memory_fingerprint: str
    market_context_fingerprint: str
    research_only: bool = True
    broker_order_authorized: bool = False


@dataclass(frozen=True, slots=True)
class Vt08CognitivePositionTrace:
    market: str
    source_event_id: str
    as_of: datetime
    action: Vt08PositionAction
    reason_codes: tuple[str, ...]
    journey_fingerprint: str
    position_fingerprint: str
    research_only: bool = True
    broker_order_authorized: bool = False


class Vt08FiveMarketCognitiveGate:
    """Stateful causal source-event cognition, no economic/broker authority."""

    def __init__(self) -> None:
        self._hypotheses: dict[str, Vt08Hypothesis] = {}
        self._event_market: dict[str, str] = {}
        self._last_decision_at: dict[str, datetime] = {}
        self._last_position_at: dict[str, datetime] = {}
        self._executed: set[str] = set()
        self._decisions: list[Vt08CognitiveDecisionTrace] = []
        self._positions: list[Vt08CognitivePositionTrace] = []

    @property
    def decisions(self) -> tuple[Vt08CognitiveDecisionTrace, ...]:
        return tuple(self._decisions)

    @property
    def positions(self) -> tuple[Vt08CognitivePositionTrace, ...]:
        return tuple(self._positions)

    def _check_source_market(
        self, situation: Vt08FiveMarketResearchSituation
    ) -> str:
        event_id = situation.source_evidence_id
        previous = self._event_market.get(event_id)
        if previous is not None and previous != situation.market:
            raise ValueError("VT08 source identity cannot migrate across markets")
        return event_id

    def evaluate(
        self, situation: Vt08FiveMarketResearchSituation
    ) -> Vt08CognitiveDecisionTrace:
        """Consume an as-of source snapshot, preserving WAIT and killed events."""
        event_id = self._check_source_market(situation)
        earlier = self._last_decision_at.get(event_id)
        if earlier is not None and situation.as_of <= earlier:
            raise ValueError("VT08 replay source decision timestamp must advance")
        if event_id in self._executed:
            raise ValueError("VT08 same source event may execute only once")
        assessed = evaluate_cognitive_hypothesis(
            situation=situation,
            source_fingerprint=event_id,
            hypothesis=self._hypotheses.get(event_id),
        )
        self._hypotheses[event_id] = assessed.hypothesis
        self._last_decision_at[event_id] = situation.as_of
        self._event_market[event_id] = situation.market
        if assessed.decision.action is Vt08CognitiveAction.EXECUTE:
            self._executed.add(event_id)
        d = assessed.decision
        trace = Vt08CognitiveDecisionTrace(
            market=situation.market,
            source_event_id=event_id,
            as_of=situation.as_of,
            action=d.action,
            hypothesis_state=assessed.hypothesis.state,
            reason_codes=d.reason_codes,
            situation_fingerprint=d.situation_fingerprint,
            decision_fingerprint=d.fingerprint(),
            strategy_identity_fingerprint=d.strategy_identity_fingerprint,
            memory_fingerprint=d.cognitive_memory_fingerprint,
            market_context_fingerprint=d.market_anchor_context_fingerprint,
        )
        self._decisions.append(trace)
        return trace

    def evaluate_position(
        self,
        situation: Vt08FiveMarketResearchSituation,
        position: Vt08PositionSnapshot,
    ) -> Vt08CognitivePositionTrace:
        """Read-only position advice. It never edits a trade or executes an exit."""
        event_id = self._check_source_market(situation)
        if event_id not in self._executed:
            raise ValueError("VT08 cannot assess unadmitted research position")
        if situation.as_of != position.as_of:
            raise ValueError("VT08 position and Situation as_of must match")
        initial = self._last_decision_at[event_id]
        if situation.as_of <= initial:
            raise ValueError("VT08 in-trade cognition requires post-admission bar")
        previous = self._last_position_at.get(event_id)
        if previous is not None and situation.as_of <= previous:
            raise ValueError("VT08 in-trade assessment timestamp must advance")
        result = evaluate_in_trade_cognition(
            situation=situation,
            position=position,
            policy=RESEARCH_UNCALIBRATED_POSITION_POLICY,
        )
        self._last_position_at[event_id] = situation.as_of
        trace = Vt08CognitivePositionTrace(
            market=situation.market,
            source_event_id=event_id,
            as_of=situation.as_of,
            action=result.position_decision.action,
            reason_codes=result.position_decision.reason_codes,
            journey_fingerprint=result.journey.fingerprint(),
            position_fingerprint=result.position_decision.fingerprint(),
        )
        self._positions.append(trace)
        return trace
