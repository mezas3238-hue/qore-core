"""Architect 1: deterministic batch replay and immutable advisory journal.

Consumes externally supplied canonical observations, never prices fills,
creates volume, claims a broker balance, or authorizes execution.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC
from hashlib import sha256
from json import dumps

from qore.infrastructure.cibo_trade_ops_director import (
    ManagementDecision,
    Stage,
    TradeOpsError,
    TradeOpsEvent,
    TradeOpsState,
    apply_trade_event,
)


def _sha(payload: object) -> str:
    return "sha256:" + sha256(
        dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class TradeOpsReplayAudit:
    snapshots: tuple[TradeOpsState, ...]
    signal_ids: tuple[str, ...]
    events_seen: int
    broker_deals_seen: int
    stage_counts: tuple[tuple[str, int], ...]
    manifest_verified: bool
    audit_sha256: str
    financial_certified: bool = False


def replay_trade_ops_events(
    events: Iterable[TradeOpsEvent],
    *,
    expected_signal_ids: Sequence[str] | None = None,
) -> TradeOpsReplayAudit:
    """Require exact signal manifest and global deal uniqueness, if supplied.

    Counting N arbitrary signals alone never establishes research coverage.
    """
    states: dict[str, TradeOpsState] = {}
    globally_seen_events: set[str] = set()
    globally_seen_deals: set[str] = set()
    count = 0
    for event in events:
        if type(event) is not TradeOpsEvent:
            raise TradeOpsError("replay requires canonical event stream")
        if event.event_id in globally_seen_events:
            raise TradeOpsError("duplicate global event_id")
        if event.deal_id and event.deal_id in globally_seen_deals:
            raise TradeOpsError("broker deal reused across signals")
        state = apply_trade_event(states.get(event.signal_id), event)
        states[event.signal_id] = state
        globally_seen_events.add(event.event_id)
        if event.deal_id:
            globally_seen_deals.add(event.deal_id)
        count += 1
    expected_ok = expected_signal_ids is not None
    if expected_signal_ids is not None:
        expected = tuple(expected_signal_ids)
        if any(type(x) is not str or not x for x in expected) or len(set(expected)) != len(expected):
            raise TradeOpsError("expected signal manifest must contain unique nonblank IDs")
        if set(expected) != set(states):
            missing = len(set(expected) - set(states))
            extras = len(set(states) - set(expected))
            raise TradeOpsError(f"signal coverage mismatch: missing={missing}, extra={extras}")
    snap = tuple(states[k] for k in sorted(states))
    counts = tuple((stage.value, sum(x.stage is stage for x in snap)) for stage in Stage)
    digest = _sha({
        "states": [(s.signal_id, s.audit_hash, s.stage.value) for s in snap],
        "events": count, "broker_deals": len(globally_seen_deals),
        "expected_manifest_verified": expected_ok,
    })
    return TradeOpsReplayAudit(
        snapshots=snap, signal_ids=tuple(x.signal_id for x in snap),
        events_seen=count, broker_deals_seen=len(globally_seen_deals),
        stage_counts=counts, manifest_verified=expected_ok, audit_sha256=digest,
    )


@dataclass(frozen=True, slots=True)
class ManagementAuditJournal:
    signal_id: str
    position_id: str
    last_at_utc: str
    decision_ids: tuple[str, ...]
    audit_sha256: str
    execution_authorized: bool = False


def record_management_proposal(
    journal: ManagementAuditJournal | None,
    state: TradeOpsState,
    decision: ManagementDecision,
) -> ManagementAuditJournal:
    """Chain proposals and source position state; never mutate a broker order.

    Hashes prove input integrity only. Broker authority needs external signatures.
    """
    if type(state) is not TradeOpsState or type(decision) is not ManagementDecision:
        raise TradeOpsError("management journal requires canonical objects")
    if state.stage not in {Stage.PARTIAL, Stage.FILLED, Stage.MANAGED} or state.filled_lots <= 0:
        raise TradeOpsError("management proposals only on open filled positions")
    if decision.signal_id != state.signal_id or decision.position_id != state.position_id:
        raise TradeOpsError("decision refers to different signal or position")
    if decision.execution_authorized is not False:
        raise TradeOpsError("advisory proposal cannot authorize execution")
    if not decision.decision_id.startswith("sha256:") or len(decision.decision_id) != 71:
        raise TradeOpsError("decision needs deterministic digest")
    if decision.risk_after_usd is not None and decision.risk_before_usd is None:
        raise TradeOpsError("no after-risk without before-risk")
    at = decision.occurred_at
    if at.tzinfo is None or at.utcoffset() is None:
        raise TradeOpsError("decision needs aware timestamp")
    utc_at = at.astimezone(UTC)
    if utc_at < state.last_at.astimezone(UTC):
        raise TradeOpsError("decision before position receipt")
    if journal is not None:
        if journal.signal_id != state.signal_id or journal.position_id != state.position_id:
            raise TradeOpsError("journal identity mismatch")
        if decision.decision_id in journal.decision_ids:
            raise TradeOpsError("duplicate management proposal")
        if utc_at.isoformat() < journal.last_at_utc:
            raise TradeOpsError("management decision out of chronological order")
    hash_value = _sha({
        "prev": journal.audit_sha256 if journal else None,
        "source_position_hash": state.audit_hash,
        "decision_id": decision.decision_id,
        "signal": state.signal_id, "position": state.position_id,
        "at_utc": utc_at.isoformat(), "action": decision.action.value,
        "evidence": decision.evidence_sha256,
        "risk_before": str(decision.risk_before_usd),
        "risk_after": str(decision.risk_after_usd),
        "stop_proposal": str(decision.proposed_stop),
        "reason": decision.rationale,
    })
    return ManagementAuditJournal(
        signal_id=state.signal_id, position_id=state.position_id or "",
        last_at_utc=utc_at.isoformat(),
        decision_ids=(journal.decision_ids if journal else ()) + (decision.decision_id,),
        audit_sha256=hash_value,
    )
