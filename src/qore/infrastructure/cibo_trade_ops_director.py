"""CIBO Architect 1: causal trade-operations ledger and defensive proposal engine.

Provider neutral, deterministic, advisory only. It does not send orders,
select physical lots, mutate broker stops, create fills, or book PnL.
A trusted adapter must verify broker source BEFORE publishing any receipt.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


class TradeOpsError(ValueError):
    """Invalid event provenance, chronology, funding, or position state."""


class Stage(StrEnum):
    SIGNAL_RECEIVED = "SIGNAL_RECEIVED"
    ECONOMICALLY_VALUED = "ECONOMICALLY_VALUED"
    ECONOMICALLY_FUNDED = "ECONOMICALLY_FUNDED"
    UNFUNDABLE = "UNFUNDABLE"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    MANAGED = "MANAGED"
    CLOSED = "CLOSED"


class Action(StrEnum):
    OBSERVE = "OBSERVE"
    REQUEST_STOP_TO_BREAKEVEN = "REQUEST_STOP_TO_BREAKEVEN"
    ESCALATE_STOP_BREACH = "ESCALATE_STOP_BREACH"
    REQUEST_DEFENSIVE_REVIEW = "REQUEST_DEFENSIVE_REVIEW"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"


_ALLOWED: dict[Stage | None, frozenset[Stage]] = {
    None: frozenset({Stage.SIGNAL_RECEIVED}),
    Stage.SIGNAL_RECEIVED: frozenset({Stage.ECONOMICALLY_VALUED}),
    Stage.ECONOMICALLY_VALUED: frozenset({Stage.ECONOMICALLY_FUNDED, Stage.UNFUNDABLE}),
    Stage.ECONOMICALLY_FUNDED: frozenset({Stage.ORDER_SUBMITTED}),
    Stage.ORDER_SUBMITTED: frozenset({Stage.ORDER_REJECTED, Stage.PARTIAL, Stage.FILLED}),
    Stage.PARTIAL: frozenset({Stage.PARTIAL, Stage.FILLED, Stage.MANAGED}),
    Stage.FILLED: frozenset({Stage.MANAGED, Stage.CLOSED}),
    Stage.MANAGED: frozenset({Stage.MANAGED, Stage.CLOSED}),
    Stage.UNFUNDABLE: frozenset(),
    Stage.ORDER_REJECTED: frozenset(),
    Stage.CLOSED: frozenset(),
}
_SHA = "sha256:"


def _aware(t: datetime, label: str) -> datetime:
    if type(t) is not datetime or t.tzinfo is None or t.utcoffset() is None:
        raise TradeOpsError(f"{label} must be timezone-aware")
    return t.astimezone(UTC)


def _money(x: Decimal, label: str, *, allow_zero: bool = True) -> Decimal:
    if type(x) is not Decimal or not x.is_finite() or x < 0 or (not allow_zero and x == 0):
        raise TradeOpsError(f"{label} requires nonnegative finite Decimal")
    return x


def _digest(value: str, label: str) -> None:
    if type(value) is not str or len(value) != 71 or not value.startswith(_SHA):
        raise TradeOpsError(f"{label} requires sha256 digest")
    if any(ch not in "0123456789abcdef" for ch in value[7:]):
        raise TradeOpsError(f"{label} requires lowercase hex digest")


def _nonblank(value: str, label: str) -> None:
    if type(value) is not str or not value.strip() or len(value) > 256:
        raise TradeOpsError(f"{label} required")


def _hash(payload: object) -> str:
    return _SHA + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        .encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class TradeOpsEvent:
    event_id: str
    signal_id: str
    trader_id: str
    symbol: str
    side: str  # BUY / SELL
    stage: Stage
    occurred_at: datetime
    evidence_as_of: datetime
    evidence_sha256: str
    reason: str
    requested_lots: Decimal | None = None  # externally funded; never CIBO-sized
    cumulative_filled_lots: Decimal | None = None  # broker-observed
    order_id: str | None = None
    deal_id: str | None = None
    position_id: str | None = None
    broker_verified: bool = False  # ASSERTION from authenticated broker adapter, not proof
    remainder_cancelled: bool = False

    def __post_init__(self) -> None:
        for field in ("event_id", "signal_id", "trader_id", "symbol", "reason"):
            _nonblank(getattr(self, field), field)
        if self.side not in ("BUY", "SELL") or type(self.stage) is not Stage:
            raise TradeOpsError("side must be BUY/SELL and stage must be Stage")
        if _aware(self.evidence_as_of, "evidence_as_of") > _aware(self.occurred_at, "occurred_at"):
            raise TradeOpsError("future evidence is forbidden")
        _digest(self.evidence_sha256, "source evidence")
        for label in ("requested_lots", "cumulative_filled_lots"):
            value = getattr(self, label)
            if value is not None:
                _money(value, label, allow_zero=False)
        for label in ("order_id", "deal_id", "position_id"):
            value = getattr(self, label)
            if value is not None:
                _nonblank(value, label)
        if type(self.broker_verified) is not bool or type(self.remainder_cancelled) is not bool:
            raise TradeOpsError("receipt flags must be exact booleans")


@dataclass(frozen=True, slots=True)
class TradeOpsState:
    signal_id: str
    trader_id: str
    symbol: str
    side: str
    stage: Stage
    last_at: datetime
    requested_lots: Decimal | None
    filled_lots: Decimal
    order_id: str | None
    position_id: str | None
    remainder_cancelled: bool
    event_ids: tuple[str, ...]
    broker_deal_ids: tuple[str, ...]
    audit_hash: str


def apply_trade_event(state: TradeOpsState | None, event: TradeOpsEvent) -> TradeOpsState:
    """Pure append-only logical transition; duplicate IDs and fake broker states fail closed."""
    if type(event) is not TradeOpsEvent:
        raise TradeOpsError("canonical TradeOpsEvent required")
    current = state.stage if state else None
    if event.stage not in _ALLOWED[current]:
        raise TradeOpsError(f"forbidden lifecycle transition {current} -> {event.stage}")
    if state:
        if (event.signal_id, event.trader_id, event.symbol, event.side) != (
            state.signal_id, state.trader_id, state.symbol, state.side
        ):
            raise TradeOpsError("immutable signal identity mismatch")
        if _aware(event.occurred_at, "occurred_at") < _aware(state.last_at, "last_at"):
            raise TradeOpsError("retroactive transition forbidden")
        if event.event_id in state.event_ids or (
            event.deal_id and event.deal_id in state.broker_deal_ids
        ):
            raise TradeOpsError("duplicate event or broker deal")
    broker_stage = event.stage in {
        Stage.ORDER_SUBMITTED, Stage.ORDER_REJECTED, Stage.PARTIAL, Stage.FILLED, Stage.CLOSED
    }
    if broker_stage and not event.broker_verified:
        raise TradeOpsError("broker lifecycle needs verified adapter receipt")
    if event.stage is Stage.ECONOMICALLY_FUNDED:
        if event.requested_lots is None:
            raise TradeOpsError("funding must cite externally approved lots")
    elif event.requested_lots is not None:
        raise TradeOpsError("only funded event may declare requested lots")
    lots = state.requested_lots if state else None
    if event.stage is Stage.ECONOMICALLY_FUNDED:
        lots = event.requested_lots
    filled = state.filled_lots if state else Decimal(0)
    if event.stage in {Stage.PARTIAL, Stage.FILLED}:
        if not (event.order_id and event.deal_id and event.position_id):
            raise TradeOpsError("fill needs broker order, deal and position identifiers")
        if not state or event.order_id != state.order_id or lots is None:
            raise TradeOpsError("fill has no matching funded order")
        new_filled = event.cumulative_filled_lots
        if new_filled is None or not (filled < new_filled <= lots):
            raise TradeOpsError("fill must advance and remain within approved volume")
        if event.stage is Stage.FILLED and new_filled != lots:
            raise TradeOpsError("FILLED requires exact approved cumulative lots")
        if event.stage is Stage.PARTIAL and new_filled >= lots:
            raise TradeOpsError("PARTIAL must leave unfilled volume")
        if state.position_id and state.position_id != event.position_id:
            raise TradeOpsError("position ID cannot change during fill")
        filled = new_filled
    elif event.cumulative_filled_lots is not None:
        raise TradeOpsError("only fill may report cumulative executed lots")
    if event.stage is Stage.ORDER_SUBMITTED and not event.order_id:
        raise TradeOpsError("order submission must carry order ID")
    if event.stage in {Stage.ORDER_REJECTED, Stage.CLOSED}:
        if not state or not event.order_id or event.order_id != state.order_id:
            raise TradeOpsError("broker resolution must match submitted order")
    if event.stage is Stage.CLOSED:
        if (not state or state.filled_lots <= 0 or not event.deal_id
                or event.position_id != state.position_id):
            raise TradeOpsError("close needs actual broker exit deal and matching position")
    if event.stage is Stage.MANAGED:
        if not state or state.filled_lots <= 0:
            raise TradeOpsError("cannot manage an unfilled position")
        if state.stage is Stage.PARTIAL and not event.remainder_cancelled:
            raise TradeOpsError("partial order needs broker remainder cancellation")
        if state.stage is Stage.PARTIAL and not event.broker_verified:
            raise TradeOpsError("remainder cancellation requires broker receipt")
    if event.remainder_cancelled and (
        event.stage is not Stage.MANAGED or not event.broker_verified
    ):
        raise TradeOpsError("cancellation only via broker-verified management transition")
    if event.stage is Stage.ORDER_REJECTED and filled:
        raise TradeOpsError("filled order cannot be rejected")
    if event.deal_id is not None and event.stage not in {
        Stage.PARTIAL, Stage.FILLED, Stage.CLOSED
    }:
        raise TradeOpsError("deal ID only valid for executed broker deals")
    order_id = event.order_id or (state.order_id if state else None)
    position_id = event.position_id or (state.position_id if state else None)
    new_hash = _hash({
        "parent": state.audit_hash if state else None,
        "id": event.event_id, "signal": event.signal_id,
        "trader": event.trader_id, "symbol": event.symbol, "side": event.side,
        "stage": event.stage.value,
        "at": _aware(event.occurred_at, "at").isoformat(),
        "source_at": _aware(event.evidence_as_of, "source_at").isoformat(),
        "source": event.evidence_sha256, "reason": event.reason,
        "requested": str(event.requested_lots), "filled": str(filled),
        "order": order_id, "deal": event.deal_id, "position": position_id,
        "broker_verified": event.broker_verified,
        "remainder_cancelled": event.remainder_cancelled,
    })
    return TradeOpsState(
        signal_id=event.signal_id, trader_id=event.trader_id,
        symbol=event.symbol, side=event.side, stage=event.stage,
        last_at=event.occurred_at, requested_lots=lots,
        filled_lots=filled, order_id=order_id, position_id=position_id,
        remainder_cancelled=(state.remainder_cancelled if state else False)
        or event.remainder_cancelled,
        event_ids=(state.event_ids if state else ()) + (event.event_id,),
        broker_deal_ids=(state.broker_deal_ids if state else ())
        + ((event.deal_id,) if event.deal_id else ()),
        audit_hash=new_hash,
    )


@dataclass(frozen=True, slots=True)
class ManagementEvidence:
    observed_at: datetime
    quote_as_of: datetime
    quote_sha256: str
    bid: Decimal
    ask: Decimal
    entry_price: Decimal
    structural_stop: Decimal
    current_stop: Decimal
    target_price: Decimal
    atr_as_of: datetime | None = None
    atr_price: Decimal | None = None
    news_risk: bool = False
    provider_floor_pressure: bool = False
    correlation_pressure: bool = False
    current_stop_risk_usd: Decimal | None = None
    breakeven_stop_risk_usd: Decimal | None = None
    valuation_as_of: datetime | None = None
    valuation_sha256: str | None = None

    def __post_init__(self) -> None:
        at = _aware(self.observed_at, "observed_at")
        if _aware(self.quote_as_of, "quote_as_of") > at:
            raise TradeOpsError("future quote forbidden")
        _digest(self.quote_sha256, "quote evidence")
        for label in ("bid", "ask", "entry_price", "structural_stop",
                      "current_stop", "target_price"):
            _money(getattr(self, label), label, allow_zero=False)
        if self.ask < self.bid:
            raise TradeOpsError("inverted bid/ask")
        if (self.atr_as_of is None) != (self.atr_price is None):
            raise TradeOpsError("ATR timestamp and value must come together")
        if self.atr_as_of is not None:
            if _aware(self.atr_as_of, "atr_as_of") > at:
                raise TradeOpsError("future ATR forbidden")
            _money(self.atr_price, "atr_price", allow_zero=False)  # type: ignore[arg-type]
        risk_inputs = (self.current_stop_risk_usd, self.breakeven_stop_risk_usd,
                       self.valuation_as_of, self.valuation_sha256)
        if any(x is not None for x in risk_inputs):
            if not all(x is not None for x in risk_inputs):
                raise TradeOpsError("broker risk valuation must provide complete paired evidence")
            _money(self.current_stop_risk_usd, "current_stop_risk_usd")  # type: ignore[arg-type]
            _money(self.breakeven_stop_risk_usd, "breakeven_stop_risk_usd")  # type: ignore[arg-type]
            _digest(self.valuation_sha256, "valuation evidence")  # type: ignore[arg-type]
            if _aware(self.valuation_as_of, "valuation_as_of") > at:  # type: ignore[arg-type]
                raise TradeOpsError("future broker risk valuation forbidden")
            if self.breakeven_stop_risk_usd > self.current_stop_risk_usd:  # type: ignore[operator]
                raise TradeOpsError("breakeven valuation cannot increase stop risk")
        for label in ("news_risk", "provider_floor_pressure", "correlation_pressure"):
            if type(getattr(self, label)) is not bool:
                raise TradeOpsError("pressure flags must be exact booleans")


@dataclass(frozen=True, slots=True)
class ManagementDecision:
    decision_id: str
    signal_id: str
    position_id: str
    occurred_at: datetime
    action: Action
    rationale: str
    invalidation: str
    evidence_sha256: str
    proposed_stop: Decimal | None
    risk_before_usd: Decimal | None = None
    risk_after_usd: Decimal | None = None
    requires_broker_valuation: bool = True
    execution_authorized: bool = False


def decide_position_management(
    state: TradeOpsState,
    evidence: ManagementEvidence,
    *,
    max_quote_age_seconds: int = 30,
) -> ManagementDecision:
    """Propose only: monetary after-risk is never fabricated from price geometry."""
    if type(state) is not TradeOpsState or type(evidence) is not ManagementEvidence:
        raise TradeOpsError("canonical management state and market evidence required")
    if state.stage not in {Stage.PARTIAL, Stage.FILLED, Stage.MANAGED} or state.filled_lots <= 0:
        raise TradeOpsError("management needs an actually filled open position")
    if type(max_quote_age_seconds) is not int or max_quote_age_seconds <= 0:
        raise TradeOpsError("max quote age must be positive integer")
    at = _aware(evidence.observed_at, "observed_at")
    if at < _aware(state.last_at, "last_at"):
        raise TradeOpsError("management cannot predate position event")
    spread = evidence.ask - evidence.bid
    long = state.side == "BUY"
    if long and not (evidence.structural_stop < evidence.entry_price < evidence.target_price):
        raise TradeOpsError("BUY geometry invalid")
    if not long and not (evidence.target_price < evidence.entry_price < evidence.structural_stop):
        raise TradeOpsError("SELL geometry invalid")
    if long and evidence.current_stop < evidence.structural_stop:
        raise TradeOpsError("BUY stop loosening forbidden")
    if not long and evidence.current_stop > evidence.structural_stop:
        raise TradeOpsError("SELL stop loosening forbidden")
    executable_exit = evidence.bid if long else evidence.ask
    risk_distance = abs(evidence.entry_price - evidence.structural_stop)
    favorable_r = (
        (executable_exit - evidence.entry_price)
        if long else (evidence.entry_price - executable_exit)
    ) / risk_distance
    quote_age = (at - _aware(evidence.quote_as_of, "quote_as_of")).total_seconds()
    atr_age = (
        (at - _aware(evidence.atr_as_of, "atr_as_of")).total_seconds()
        if evidence.atr_as_of is not None else None
    )
    if quote_age > max_quote_age_seconds or (atr_age is not None and atr_age > 300):
        action, why, proposed = Action.EVIDENCE_INSUFFICIENT, "STALE_MARKET_EVIDENCE", None
    elif executable_exit <= evidence.current_stop if long else executable_exit >= evidence.current_stop:
        action, why, proposed = Action.ESCALATE_STOP_BREACH, "EXIT_SIDE_TOUCHES_STOP_VERIFY_BROKER", None
    elif evidence.provider_floor_pressure or evidence.news_risk or evidence.correlation_pressure:
        action, why, proposed = Action.REQUEST_DEFENSIVE_REVIEW, "FLOOR_NEWS_OR_CORRELATION_PRESSURE", None
    elif evidence.atr_price is None:
        action, why, proposed = Action.EVIDENCE_INSUFFICIENT, "ATR_UNAVAILABLE", None
    elif spread > evidence.atr_price / Decimal(2):
        action, why, proposed = Action.REQUEST_DEFENSIVE_REVIEW, "SPREAD_EXCEEDS_HALF_ATR", None
    elif favorable_r >= Decimal(1) and (
        (long and evidence.current_stop < evidence.entry_price and executable_exit > evidence.entry_price + spread)
        or (not long and evidence.current_stop > evidence.entry_price and executable_exit < evidence.entry_price - spread)
    ):
        action, why, proposed = (
            Action.REQUEST_STOP_TO_BREAKEVEN, "FAVORABLE_MARK_EXCEEDS_ONE_STRUCTURAL_R",
            evidence.entry_price,
        )
    else:
        action, why, proposed = Action.OBSERVE, "STRUCTURE_INTACT_MONITOR", None
    digest = _hash({
        "signal": state.signal_id, "position": state.position_id,
        "ledger": state.audit_hash, "at": at.isoformat(),
        "quote_at": _aware(evidence.quote_as_of, "quote_as_of").isoformat(),
        "quote": evidence.quote_sha256, "bid": str(evidence.bid), "ask": str(evidence.ask),
        "entry": str(evidence.entry_price), "structural_stop": str(evidence.structural_stop),
        "stop": str(evidence.current_stop), "target": str(evidence.target_price),
        "atr": str(evidence.atr_price),
        "atr_at": (
            _aware(evidence.atr_as_of, "atr_as_of").isoformat()
            if evidence.atr_as_of else None
        ),
        "news": evidence.news_risk, "floor": evidence.provider_floor_pressure,
        "correlation": evidence.correlation_pressure,
        "risk_before": str(evidence.current_stop_risk_usd),
        "risk_be": str(evidence.breakeven_stop_risk_usd),
        "risk_valuation": evidence.valuation_sha256,
        "valuation_as_of": (
            _aware(evidence.valuation_as_of, "valuation_as_of").isoformat()
            if evidence.valuation_as_of else None
        ),
        "action": action.value, "reason": why, "proposal": str(proposed),
    })
    return ManagementDecision(
        decision_id=digest, signal_id=state.signal_id,
        position_id=state.position_id or "", occurred_at=evidence.observed_at,
        action=action, rationale=why,
        invalidation="Recompute on newer bid/ask, stop, broker deal or economic receipt",
        evidence_sha256=evidence.quote_sha256, proposed_stop=proposed,
        risk_before_usd=evidence.current_stop_risk_usd,
        risk_after_usd=(
            evidence.breakeven_stop_risk_usd
            if action is Action.REQUEST_STOP_TO_BREAKEVEN else None
        ),
        requires_broker_valuation=(evidence.breakeven_stop_risk_usd is None),
    )
