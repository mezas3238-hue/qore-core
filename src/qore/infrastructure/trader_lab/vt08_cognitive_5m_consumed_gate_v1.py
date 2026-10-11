"""Research-only cognitive consumption gate for VT08 5M candidate snapshots.

This does NOT construct/source-select an entry, submit orders, model execution,
choose daily fills or consume a sealed holdout. Architect A supplies causal,
machine-authorized source events; this module only reasons over their observed
Situation snapshots and retains testable per-event cognitive decision lineage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final
from zoneinfo import ZoneInfo

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
    Vt08KnowledgeState,
    Vt08PositionAction,
)

GATE_SCHEMA: Final = "qore.vt08.cognitive_5m.consumed_gate.research.v1"


def _instant(timestamp: datetime) -> datetime:
    """UTC ordering: same-ZoneInfo NY wall-time comparison ignores fold."""
    return timestamp.astimezone(UTC)


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
    metacognitive_state: Vt08KnowledgeState
    adversarial_challenges: tuple[str, ...]
    adversarial_unknowns: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
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
    journey_state: str
    destination_state: str
    next_stop: Decimal | None
    policy_calibrated: bool
    fill_id: str
    fill_evidence_sha256: str
    original_initial_stop: Decimal
    original_bound_destination: Decimal
    observed_current_stop: Decimal
    research_only: bool = True
    broker_order_authorized: bool = False


@dataclass(frozen=True, slots=True)
class Vt08ResearchFillEvidence:
    """Externally produced, research-only simulated fill acknowledgement.

    An entry EXECUTE is only an intention. This evidence MUST come from a
    separate deterministic execution model, not be inferred by cognition.
    """
    source_event_id: str
    market: str
    side: str
    source_cycle_id: str
    fill_id: str
    filled_at: datetime
    entry_price: Decimal
    evidence_sha256: str
    research_only: bool = True
    broker_order_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.source_event_id or not self.source_cycle_id or not self.fill_id:
            raise ValueError("VT08 fill requires source, cycle and unique fill identity")
        if self.side not in {"long", "short"} or not self.market:
            raise ValueError("VT08 fill requires valid market/side")
        if self.filled_at.tzinfo is None or self.filled_at.utcoffset() is None:
            raise ValueError("VT08 fill time must be timezone-aware")
        if (
            not isinstance(self.entry_price, Decimal)
            or not self.entry_price.is_finite()
            or self.entry_price <= 0
        ):
            raise ValueError("VT08 fill entry price must be positive finite Decimal")
        if re.fullmatch(r"[0-9a-f]{64}", self.evidence_sha256) is None:
            raise ValueError("VT08 fill requires SHA256 evidence digest")
        if type(self.research_only) is not bool or type(self.broker_order_authorized) is not bool:
            raise ValueError("VT08 fill authority flags must be exact bool")
        if not self.research_only or self.broker_order_authorized:
            raise ValueError("VT08 cognitive fill is research-only")


@dataclass(frozen=True, slots=True)
class Vt08ResearchFillTrace:
    source_event_id: str
    market: str
    fill_id: str
    filled_at: datetime
    entry_price: Decimal
    evidence_sha256: str
    related_decision_fingerprint: str
    research_only: bool = True
    broker_order_authorized: bool = False


@dataclass(frozen=True, slots=True)
class Vt08ResearchTerminalEvidence:
    """External research terminal settlement; cognition never manufactures it."""

    source_event_id: str
    market: str
    fill_id: str
    fill_evidence_sha256: str
    closed_at: datetime
    exit_price: Decimal
    terminal_reason: str
    evidence_sha256: str
    research_only: bool = True
    broker_order_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.source_event_id or not self.market or not self.fill_id:
            raise ValueError("VT08 terminal settlement needs source/market/fill identity")
        if self.closed_at.tzinfo is None or self.closed_at.utcoffset() is None:
            raise ValueError("VT08 terminal settlement requires timezone-aware close")
        if (
            not isinstance(self.exit_price, Decimal)
            or not self.exit_price.is_finite()
            or self.exit_price <= 0
        ):
            raise ValueError("VT08 terminal exit price must be positive finite Decimal")
        if self.terminal_reason not in {
            "STOP", "TARGET", "H4_LIFECYCLE", "EXTERNAL_CLOSE", "OTHER",
        }:
            raise ValueError("VT08 terminal reason outside declared categories")
        if (
            re.fullmatch(r"[0-9a-f]{64}", self.evidence_sha256) is None
            or re.fullmatch(r"[0-9a-f]{64}", self.fill_evidence_sha256) is None
        ):
            raise ValueError("VT08 terminal evidence requires SHA256 lineage")
        if type(self.research_only) is not bool or type(self.broker_order_authorized) is not bool:
            raise ValueError("VT08 terminal authority flags must be exact bool")
        if not self.research_only or self.broker_order_authorized:
            raise ValueError("VT08 terminal settlement is research-only")


@dataclass(frozen=True, slots=True)
class Vt08ResearchTerminalTrace:
    source_event_id: str
    market: str
    fill_id: str
    closed_at: datetime
    exit_price: Decimal
    terminal_reason: str
    evidence_sha256: str
    related_fill_evidence_sha256: str
    last_position_fingerprint: str | None
    research_only: bool = True
    broker_order_authorized: bool = False


class Vt08FiveMarketCognitiveGate:
    """Stateful causal source-event cognition, no economic/broker authority."""

    def __init__(self) -> None:
        self._hypotheses: dict[str, Vt08Hypothesis] = {}
        self._event_identity: dict[str, tuple[str, ...]] = {}
        self._last_decision_at: dict[str, datetime] = {}
        self._last_position_at: dict[str, datetime] = {}
        self._position_terms: dict[str, tuple[Decimal, Decimal]] = {}
        self._last_observed_stops: dict[str, Decimal] = {}
        self._terminal: dict[str, Vt08ResearchTerminalTrace] = {}
        self._terminals: list[Vt08ResearchTerminalTrace] = []
        self._executed: set[str] = set()
        self._fill_ids: set[str] = set()
        self._filled: dict[str, Vt08ResearchFillTrace] = {}
        self._fills: list[Vt08ResearchFillTrace] = []
        self._last_global_as_of: datetime | None = None
        self._decisions: list[Vt08CognitiveDecisionTrace] = []
        self._positions: list[Vt08CognitivePositionTrace] = []

    @property
    def decisions(self) -> tuple[Vt08CognitiveDecisionTrace, ...]:
        return tuple(self._decisions)

    @property
    def positions(self) -> tuple[Vt08CognitivePositionTrace, ...]:
        return tuple(self._positions)

    @property
    def fills(self) -> tuple[Vt08ResearchFillTrace, ...]:
        return tuple(self._fills)

    @property
    def terminals(self) -> tuple[Vt08ResearchTerminalTrace, ...]:
        return tuple(self._terminals)

    def _check_source_identity(
        self, situation: Vt08FiveMarketResearchSituation
    ) -> tuple[str, tuple[str, ...]]:
        """Freeze structural identity across WAIT snapshots; no source-side drift."""
        event_id = situation.source_evidence_id
        expiry = situation.cycle_expires_at
        if expiry is None:
            raise ValueError("VT08 event requires bounded H4 source cycle")
        source_identity = (
            situation.market,
            situation.side,
            str(situation.anchor_hour_ny),
            situation.ltf_profile,
            situation.source_cycle_id,
            expiry.isoformat(),
            situation.as_of.astimezone(ZoneInfo("America/New_York"))
            .date().isoformat(),
        )
        prior = self._event_identity.get(event_id)
        if prior is not None and prior != source_identity:
            raise ValueError("VT08 source identity cannot drift across event updates")
        return event_id, source_identity

    def evaluate(
        self, situation: Vt08FiveMarketResearchSituation
    ) -> Vt08CognitiveDecisionTrace:
        """Consume an as-of source snapshot, preserving WAIT and killed events."""
        event_id, source_identity = self._check_source_identity(situation)
        if (
            self._last_global_as_of is not None
            and _instant(situation.as_of) < self._last_global_as_of
        ):
            raise ValueError("VT08 global replay clock cannot move backwards")
        if situation.cycle_expires_at is None or (
            _instant(situation.as_of) >= _instant(situation.cycle_expires_at)
        ):
            raise ValueError("VT08 WAIT/entry event expired at H4 source cycle end")
        earlier = self._last_decision_at.get(event_id)
        if earlier is not None and _instant(situation.as_of) <= earlier:
            raise ValueError("VT08 replay source decision timestamp must advance")
        if event_id in self._executed:
            raise ValueError("VT08 same source event may execute only once")
        assessed = evaluate_cognitive_hypothesis(
            situation=situation,
            source_fingerprint=event_id,
            hypothesis=self._hypotheses.get(event_id),
        )
        self._hypotheses[event_id] = assessed.hypothesis
        self._last_decision_at[event_id] = _instant(situation.as_of)
        self._event_identity[event_id] = source_identity
        self._last_global_as_of = _instant(situation.as_of)
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
            metacognitive_state=d.metacognition.state,
            adversarial_challenges=d.adversarial.material_challenges,
            adversarial_unknowns=d.adversarial.unresolved_material_challenges,
            supporting_evidence=d.supporting_evidence,
        )
        self._decisions.append(trace)
        return trace

    def record_fill(self, evidence: Vt08ResearchFillEvidence) -> Vt08ResearchFillTrace:
        """Attach simulated execution to a previously EXECUTE-approved source.

        Strictly no inference from an EXECUTE, synthetic price or later PnL.
        The source/execution architect still owns full price-path verification.
        """
        event_id = evidence.source_event_id
        if event_id not in self._executed:
            raise ValueError("VT08 cannot record fill without cognitive EXECUTE")
        if event_id in self._filled or evidence.fill_id in self._fill_ids:
            raise ValueError("VT08 duplicate fill or source execution")
        identity = self._event_identity[event_id]
        if (
            evidence.market != identity[0]
            or evidence.side != identity[1]
            or evidence.source_cycle_id != identity[4]
        ):
            raise ValueError("VT08 fill evidence contradicts source identity")
        if _instant(evidence.filled_at) < self._last_decision_at[event_id]:
            raise ValueError("VT08 fill cannot precede cognitive decision")
        if _instant(evidence.filled_at) >= _instant(datetime.fromisoformat(identity[5])):
            raise ValueError("VT08 pending fill after H4 expiry")
        if (
            self._last_global_as_of is not None
            and _instant(evidence.filled_at) < self._last_global_as_of
        ):
            raise ValueError("VT08 fill global replay clock cannot move backwards")
        source_decision = next(
            d for d in reversed(self._decisions)
            if d.source_event_id == event_id
            and d.action is Vt08CognitiveAction.EXECUTE
        )
        trace = Vt08ResearchFillTrace(
            source_event_id=event_id,
            market=evidence.market,
            fill_id=evidence.fill_id,
            filled_at=evidence.filled_at,
            entry_price=evidence.entry_price,
            evidence_sha256=evidence.evidence_sha256,
            related_decision_fingerprint=source_decision.decision_fingerprint,
        )
        self._filled[event_id] = trace
        self._fill_ids.add(evidence.fill_id)
        self._fills.append(trace)
        self._last_global_as_of = _instant(evidence.filled_at)
        return trace

    def record_terminal(
        self, evidence: Vt08ResearchTerminalEvidence
    ) -> Vt08ResearchTerminalTrace:
        """Record external observed closure; an EXIT suggestion is NOT a fill.

        Requires the original fill identity and digest. Never computes PnL,
        broker orders, or an outcome from unverified OHLC/source price.
        """
        event_id = evidence.source_event_id
        fill = self._filled.get(event_id)
        if fill is None:
            raise ValueError("VT08 terminal requires registered research fill")
        if event_id in self._terminal:
            raise ValueError("VT08 source position already terminal")
        if (
            evidence.market != fill.market
            or evidence.fill_id != fill.fill_id
            or evidence.fill_evidence_sha256 != fill.evidence_sha256
        ):
            raise ValueError("VT08 terminal evidence contradicts fill lineage")
        if _instant(evidence.closed_at) <= _instant(fill.filled_at):
            raise ValueError("VT08 terminal close must follow original fill")
        if (
            self._last_global_as_of is not None
            and _instant(evidence.closed_at) < self._last_global_as_of
        ):
            raise ValueError("VT08 terminal replay clock cannot move backwards")
        latest = next(
            (p for p in reversed(self._positions) if p.source_event_id == event_id),
            None,
        )
        trace = Vt08ResearchTerminalTrace(
            source_event_id=event_id,
            market=evidence.market,
            fill_id=evidence.fill_id,
            closed_at=evidence.closed_at,
            exit_price=evidence.exit_price,
            terminal_reason=evidence.terminal_reason,
            evidence_sha256=evidence.evidence_sha256,
            related_fill_evidence_sha256=evidence.fill_evidence_sha256,
            last_position_fingerprint=(
                latest.position_fingerprint if latest is not None else None
            ),
        )
        self._terminal[event_id] = trace
        self._terminals.append(trace)
        self._last_global_as_of = _instant(evidence.closed_at)
        return trace

    def evaluate_position(
        self,
        situation: Vt08FiveMarketResearchSituation,
        position: Vt08PositionSnapshot,
    ) -> Vt08CognitivePositionTrace:
        """Read-only position advice. It never edits a trade or executes an exit."""
        event_id, _ = self._check_source_identity(situation)
        if (
            self._last_global_as_of is not None
            and _instant(situation.as_of) < self._last_global_as_of
        ):
            raise ValueError("VT08 global replay clock cannot move backwards")
        if event_id not in self._executed:
            raise ValueError("VT08 cannot assess unadmitted research position")
        if event_id not in self._filled:
            raise ValueError("VT08 cannot assess position without recorded fill")
        if event_id in self._terminal:
            raise ValueError("VT08 cannot assess a terminal-closed position")
        fill = self._filled[event_id]
        if position.entry_price != fill.entry_price:
            raise ValueError("VT08 position entry price differs from recorded fill")
        if _instant(situation.as_of) <= _instant(fill.filled_at):
            raise ValueError("VT08 position assessment must follow recorded fill")
        if _instant(situation.as_of) != _instant(position.as_of):
            raise ValueError("VT08 position and Situation as_of must match")
        if situation.side != position.side:
            raise ValueError("VT08 in-trade source/position side mismatch")
        if situation.position_state not in {"OPEN", "ACTIVE", "PROTECTED", "REDUCED"}:
            raise ValueError("VT08 in-trade cognition requires open position state")
        if situation.entry_state != "FILLED":
            raise ValueError("VT08 in-trade cognition requires filled entry state")
        initial = self._last_decision_at[event_id]
        if _instant(situation.as_of) <= initial:
            raise ValueError("VT08 in-trade cognition requires post-admission bar")
        previous = self._last_position_at.get(event_id)
        if previous is not None and _instant(situation.as_of) <= previous:
            raise ValueError("VT08 in-trade assessment timestamp must advance")
        # First observed position terms become immutable within THIS research
        # replay. This is continuity, not independent external risk provenance:
        # initial SL and TP remain unverified until execution sends signed terms.
        terms = (position.initial_stop, position.bound_destination)
        original = self._position_terms.get(event_id)
        if original is not None and original != terms:
            raise ValueError("VT08 initial SL and destination cannot drift in position")
        prior_stop = self._last_observed_stops.get(event_id)
        if prior_stop is not None and (
            (position.side == "long" and position.current_stop < prior_stop)
            or (position.side == "short" and position.current_stop > prior_stop)
        ):
            raise ValueError("VT08 observed stop cannot widen between M15 snapshots")
        result = evaluate_in_trade_cognition(
            situation=situation,
            position=position,
            policy=RESEARCH_UNCALIBRATED_POSITION_POLICY,
        )
        self._last_position_at[event_id] = _instant(situation.as_of)
        self._position_terms.setdefault(event_id, terms)
        self._last_observed_stops[event_id] = position.current_stop
        self._last_global_as_of = _instant(situation.as_of)
        trace = Vt08CognitivePositionTrace(
            market=situation.market,
            source_event_id=event_id,
            as_of=situation.as_of,
            action=result.position_decision.action,
            reason_codes=result.position_decision.reason_codes,
            journey_fingerprint=result.journey.fingerprint(),
            position_fingerprint=result.position_decision.fingerprint(),
            journey_state=result.journey.journey_state.value,
            destination_state=result.journey.destination_state.value,
            next_stop=result.position_decision.next_stop,
            policy_calibrated=result.position_decision.policy_calibrated,
            fill_id=fill.fill_id,
            fill_evidence_sha256=fill.evidence_sha256,
            original_initial_stop=terms[0],
            original_bound_destination=terms[1],
            observed_current_stop=position.current_stop,
        )
        self._positions.append(trace)
        return trace
