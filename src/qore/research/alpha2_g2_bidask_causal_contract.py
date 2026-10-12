"""Alpha2 G2 BID/ASK causal source contract -- no economic authority or orders.

This module can validate prospective broker quote provenance and as-of
visibility. It is NOT an historical quote download, execution simulator,
commission schedule or proof of NET profitability.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from qore.research.alpha2_intermarket import MARKETS

MAX_QUOTE_AGE = timedelta(seconds=5)
SOURCE_BLOCKED = "NET_BLOCKED_NO_VERIFIED_BROKER_BIDASK_HISTORY_OR_PIT"


class BrokerEvidenceError(ValueError):
    """Causal, identity, freshness or scope boundary failed closed."""


@dataclass(frozen=True, slots=True)
class QuoteObservation:
    symbol: str
    broker_source_id: str
    account_scope_id: str
    quote_at: datetime
    available_at: datetime
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if (self.symbol not in MARKETS
                or not self.broker_source_id.strip()
                or not self.account_scope_id.strip()):
            raise BrokerEvidenceError("source broker/account/symbol provenance missing")
        for name, at in (("quote_at", self.quote_at),
                         ("available_at", self.available_at)):
            if not isinstance(at, datetime) or at.tzinfo is None:
                raise BrokerEvidenceError(f"{name} must be UTC-aware")
            if at.utcoffset() != timedelta(0):
                raise BrokerEvidenceError(f"{name} must use exact UTC offset")
        if self.quote_at > self.available_at:
            raise BrokerEvidenceError("provider quote timestamp after availability")
        if (not math.isfinite(self.bid) or not math.isfinite(self.ask)
                or self.bid <= 0 or self.ask <= 0 or self.ask < self.bid):
            raise BrokerEvidenceError("inverted/negative/nonfinite bid ask quotation")

    @property
    def spread(self) -> float:
        return self.ask - self.bid


def verify_quote_series(
    series: tuple[QuoteObservation, ...], *,
    expected_symbol: str,
    broker_source_id: str,
    account_scope_id: str,
) -> None:
    if not series:
        raise BrokerEvidenceError(SOURCE_BLOCKED)
    if expected_symbol not in MARKETS or not broker_source_id or not account_scope_id:
        raise BrokerEvidenceError("expected exact broker source and account")
    previous_received: datetime | None = None
    previous_quote_at: datetime | None = None
    for quote in series:
        if type(quote) is not QuoteObservation:
            raise BrokerEvidenceError("unverified broker quote object")
        QuoteObservation.__post_init__(quote)
        if (quote.symbol != expected_symbol
                or quote.broker_source_id != broker_source_id
                or quote.account_scope_id != account_scope_id):
            raise BrokerEvidenceError("market/broker/account mismatch or mixing cohorts")
        if (previous_received is not None and quote.available_at <= previous_received
                or previous_quote_at is not None and quote.quote_at < previous_quote_at):
            raise BrokerEvidenceError("received order nonmonotonic or stale revision")
        previous_received, previous_quote_at = quote.available_at, quote.quote_at


def asof_quote(
    series: tuple[QuoteObservation, ...], *,
    decision_at: datetime,
    expected_symbol: str,
    broker_source_id: str,
    account_scope_id: str,
) -> QuoteObservation:
    """Visible only after receipt, never after quote update or over five seconds old."""
    verify_quote_series(
        series, expected_symbol=expected_symbol,
        broker_source_id=broker_source_id, account_scope_id=account_scope_id,
    )
    if (not isinstance(decision_at, datetime) or decision_at.tzinfo is None
            or decision_at.utcoffset() != timedelta(0)):
        raise BrokerEvidenceError("decision timestamp must be UTC-aware")
    eligible = [q for q in series if q.available_at <= decision_at]
    if not eligible:
        raise BrokerEvidenceError("no quote visible when decision taken")
    latest = eligible[-1]
    if latest.quote_at > decision_at:
        raise BrokerEvidenceError("future quote used for historical decision")
    age = decision_at - latest.quote_at
    if age < timedelta(0) or age > MAX_QUOTE_AGE:
        raise BrokerEvidenceError("stale bid/ask unavailable at decision")
    return latest


def causal_side_reference(
    quote: QuoteObservation,
    *,
    position_direction: Literal[-1, 1],
    action: Literal["entry", "exit"],
) -> float:
    """Reference quotation only; NOT a fill or a net-cost calculation."""
    if type(quote) is not QuoteObservation:
        raise BrokerEvidenceError("broker quote not authenticated")
    QuoteObservation.__post_init__(quote)
    if quote.spread <= 0:
        raise BrokerEvidenceError("SOURCE_ZERO_OR_CROSSED_SPREAD_QUARANTINED_NO_FILL")
    if (type(position_direction) is not int or position_direction not in (-1, 1)
            or action not in ("entry", "exit")):
        raise BrokerEvidenceError("invalid trading side/action")
    if action == "entry":
        return quote.ask if position_direction == 1 else quote.bid
    return quote.bid if position_direction == 1 else quote.ask


@dataclass(frozen=True, slots=True)
class NetDataReadiness:
    full_bidask_quotes_asof: bool = False
    broker_symbol_contract_verified: bool = False
    commissions_asof_verified: bool = False
    swap_rollover_asof_verified: bool = False
    quote_to_fill_slippage_verified: bool = False
    macro_release_asof_verified: bool = False
    independent_fresh_holdout_verified: bool = False

    def gate(self) -> str:
        return (
            "G2_DATA_PREREQUISITES_PRESENT_NOT_CERTIFIED"
            if all((
                self.full_bidask_quotes_asof,
                self.broker_symbol_contract_verified,
                self.commissions_asof_verified,
                self.swap_rollover_asof_verified,
                self.quote_to_fill_slippage_verified,
                self.macro_release_asof_verified,
                self.independent_fresh_holdout_verified,
            ))
            else SOURCE_BLOCKED
        )
