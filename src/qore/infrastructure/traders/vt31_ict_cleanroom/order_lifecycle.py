"""Single-VT31, source-eligible *research* limit-order lifecycle.

Never routes orders or trades live. A bid/ask quote touching a CE limit
is not equivalent to a broker fill. Only an externally evidenced immutable
execution acknowledgement may be labeled externally acknowledged, and
this module never creates such acknowledgements.

The ICT original source hour governs NEW pending entries, not mandatory
liquidation of a previously confirmed position. No historical VT31 imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from .contracts import FvgCandidate, Side, price, utc, window_bounds

TRADER_ID = "VT31"
SYMBOL = "NAS100"


class OrderResearchState(StrEnum):
    PENDING_UNROUTED = "PENDING_UNROUTED"
    QUOTE_CROSSED_NOT_FILLED = "QUOTE_CROSSED_NOT_FILLED"
    INVALIDATED_BEFORE_PROVEN_FILL = "INVALIDATED_BEFORE_PROVEN_FILL"
    EXPIRED_BEFORE_PROVEN_FILL = "EXPIRED_BEFORE_PROVEN_FILL"
    EXECUTION_ACK_RECONCILED = "EXECUTION_ACK_RECONCILED"
    CANCEL_ACK_RACE_REQUIRES_RECONCILIATION = "CANCEL_ACK_RACE_REQUIRES_RECONCILIATION"


@dataclass(frozen=True, slots=True)
class TwoSidedQuote:
    symbol: str
    observed_at: datetime
    bid: Decimal
    ask: Decimal
    source: str

    def __post_init__(self) -> None:
        utc(self.observed_at)
        bid, ask = price(self.bid), price(self.ask)
        if bid > ask or not self.source or self.symbol != SYMBOL:
            raise ValueError("NAS100 quote must have bid <= ask and source provenance")


@dataclass(frozen=True, slots=True)
class ExternalExecutionAck:
    """A received execution fact, NEVER inferred from candle high/low.

    Broker execution ID and receipt time are mandatory, including for
    out-of-order / late-received cancellation races. This data type is
    evidence of an external report, not the authority to place trades.
    """

    client_order_id: str
    symbol: str
    broker_execution_id: str
    executed_at: datetime
    received_at: datetime
    executed_price: Decimal
    executed_volume: Decimal
    broker: str

    def __post_init__(self) -> None:
        if utc(self.received_at) < utc(self.executed_at):
            raise ValueError("cannot receive execution before actual execution")
        price(self.executed_price)
        price(self.executed_volume)
        if self.symbol != SYMBOL:
            raise ValueError("external fill symbol does not match unique NAS100 trader")
        if not all((self.client_order_id, self.broker_execution_id, self.broker)):
            raise ValueError("execution identity and broker provenance required")


class SourceLimitOrderAudit:
    """Order eligibility observer, one source-window candidate, no actual routing.

    Source calendar and target/entry must be fixed before the first quote.
    Later candle prices never retroactively select the source candidate.
    Quotes MAY establish that the displayed buy ask or sell bid crossed the
    limit; they cannot prove sufficient volume or a broker matching fill.
    """

    def __init__(
        self,
        *,
        client_order_id: str,
        source: FvgCandidate,
        offered_at: datetime,
        source_provenance: str,
    ) -> None:
        if not client_order_id.strip() or not source_provenance.strip():
            raise ValueError("source and order identifiers required")
        created = utc(offered_at)
        formed = utc(source.formed_at)
        start, end = window_bounds(formed, source.session)
        if not start <= utc(source.first_candle_open) < formed < end:
            raise ValueError("unqualified source 3-M1 FVG time geometry")
        if not formed <= created < end:
            raise ValueError("order must be offered after FVG closes and inside ICT hour")
        if source.side is Side.LONG and source.target_price <= source.consequent_encroachment:
            raise ValueError("buy target must be beyond buy CE")
        if source.side is Side.SHORT and source.target_price >= source.consequent_encroachment:
            raise ValueError("sell target must be beyond sell CE")
        self.client_order_id = client_order_id
        self.source = source
        self.offered_at = created
        self.window_expires_at = end
        self.source_provenance = source_provenance
        self.state = OrderResearchState.PENDING_UNROUTED
        self.state_at = created
        self.last_quote_at: datetime | None = None
        self.earliest_quote_crossed_at: datetime | None = None
        self.execution: ExternalExecutionAck | None = None
        self.conflicting_cancellation_at: datetime | None = None
        self.last_quote: TwoSidedQuote | None = None

    def observe_quote(self, quote: TwoSidedQuote) -> OrderResearchState:
        observed = utc(quote.observed_at)
        if observed <= self.offered_at:
            raise ValueError("cannot infer a fill from the offer instant")
        if self.last_quote_at is not None and observed <= self.last_quote_at:
            raise ValueError("market quotes out of order or duplicated")
        # Reconciliation after external fill belongs to broker post-fill
        # position management, not to unfilled order source observation.
        if self.execution is not None:
            raise ValueError("pending quote audit cannot manage filled positions")
        if self.state in (
            OrderResearchState.INVALIDATED_BEFORE_PROVEN_FILL,
            OrderResearchState.EXPIRED_BEFORE_PROVEN_FILL,
            OrderResearchState.CANCEL_ACK_RACE_REQUIRES_RECONCILIATION,
        ):
            raise ValueError("order already ended, do not resurrect it from quotes")
        self.last_quote_at = observed
        self.last_quote = quote
        if observed >= self.window_expires_at:
            self.state = OrderResearchState.EXPIRED_BEFORE_PROVEN_FILL
            self.state_at = self.window_expires_at
            return self.state
        crossed = (
            quote.ask <= self.source.consequent_encroachment
            if self.source.side is Side.LONG
            else quote.bid >= self.source.consequent_encroachment
        )
        if crossed and self.earliest_quote_crossed_at is None:
            self.earliest_quote_crossed_at = observed
            self.state = OrderResearchState.QUOTE_CROSSED_NOT_FILLED
            self.state_at = observed
        return self.state

    def invalidate_source(self, observed_at: datetime) -> OrderResearchState:
        at = utc(observed_at)
        if at < self.offered_at:
            raise ValueError("cannot invalidate an order before creation")
        if self.last_quote_at is not None and at < self.last_quote_at:
            raise ValueError("cannot backdate invalidation behind observed bid/ask")
        if self.execution is not None:
            raise ValueError("position invalidation belongs to post-fill management")
        if self.state in (
            OrderResearchState.INVALIDATED_BEFORE_PROVEN_FILL,
            OrderResearchState.EXPIRED_BEFORE_PROVEN_FILL,
            OrderResearchState.CANCEL_ACK_RACE_REQUIRES_RECONCILIATION,
        ):
            raise ValueError("already terminal, do not rewrite cancellation")
        if at >= self.window_expires_at:
            return self.expire(at)
        self.state = OrderResearchState.INVALIDATED_BEFORE_PROVEN_FILL
        self.state_at = at
        return self.state

    def expire(self, observed_at: datetime) -> OrderResearchState:
        at = utc(observed_at)
        if at < self.window_expires_at:
            raise ValueError("cannot expire ICT source pending order early")
        if self.execution is not None:
            # ICT hour is not an automatic position exit rule.
            return self.state
        if self.state not in (
            OrderResearchState.INVALIDATED_BEFORE_PROVEN_FILL,
            OrderResearchState.EXPIRED_BEFORE_PROVEN_FILL,
        ):
            self.state = OrderResearchState.EXPIRED_BEFORE_PROVEN_FILL
            self.state_at = self.window_expires_at
        return self.state

    def reconcile_broker_ack(
        self,
        execution: ExternalExecutionAck,
    ) -> OrderResearchState:
        if self.execution is not None:
            raise ValueError("duplicate or second execution requires a fill ledger")
        if execution.client_order_id != self.client_order_id or execution.symbol != SYMBOL:
            raise ValueError("broker acknowledgement for another source order/instrument")
        traded = utc(execution.executed_at)
        if traded < self.offered_at or traded >= self.window_expires_at:
            raise ValueError("execution outside source order life; escalate reconciliation")
        # A true limit order must not fill at a worse price than its limit.
        if self.source.side is Side.LONG and (
            execution.executed_price > self.source.consequent_encroachment
        ):
            raise ValueError("reported buy fill worse than submitted limit")
        if self.source.side is Side.SHORT and (
            execution.executed_price < self.source.consequent_encroachment
        ):
            raise ValueError("reported sell fill worse than submitted limit")
        if self.state in (
            OrderResearchState.INVALIDATED_BEFORE_PROVEN_FILL,
            OrderResearchState.EXPIRED_BEFORE_PROVEN_FILL,
        ):
            # Late broker report of prior execution, or cancellation race,
            # must be audited rather than erased or accepted silently.
            self.conflicting_cancellation_at = self.state_at
            self.execution = execution
            self.state = OrderResearchState.CANCEL_ACK_RACE_REQUIRES_RECONCILIATION
            self.state_at = utc(execution.received_at)
            return self.state
        self.execution = execution
        self.state = OrderResearchState.EXECUTION_ACK_RECONCILED
        self.state_at = utc(execution.received_at)
        return self.state

    def snapshot(self) -> dict[str, object]:
        ack = self.execution
        return {
            "schema": "qore.vt31.ict_cleanroom.order_lifecycle.v1",
            "trader_id": TRADER_ID,
            "instrument": SYMBOL,
            "session_window": self.source.session.value,
            "client_order_id": self.client_order_id,
            "offered_at": self.offered_at.isoformat(),
            "expires_at": self.window_expires_at.isoformat(),
            "side": self.source.side.value,
            "ce_limit_price": str(self.source.consequent_encroachment),
            "source_fvg_formed_at": utc(self.source.formed_at).isoformat(),
            "source_provenance": self.source_provenance,
            "research_order_state": self.state.value,
            "state_at": self.state_at.isoformat(),
            "quote_crossed_at": (
                None if self.earliest_quote_crossed_at is None
                else self.earliest_quote_crossed_at.isoformat()
            ),
            "quote_crossed_not_broker_fill": self.earliest_quote_crossed_at is not None,
            "ack_id": None if ack is None else ack.broker_execution_id,
            "ack_received_at": None if ack is None else utc(ack.received_at).isoformat(),
            "broker_reported_executed_at": (
                None if ack is None else utc(ack.executed_at).isoformat()
            ),
            "broker_reported_fill_price": (
                None if ack is None else str(ack.executed_price)
            ),
            "broker_ack_conflicts_with_cancellation": (
                self.conflicting_cancellation_at is not None
            ),
            "source_order_routed": False,
            "broker_api_called": False,
            "paper_or_live_order_submitted": False,
            "replay_order_economics_proven": False,
            "live_authorized": False,
            "certified": False,
        }
