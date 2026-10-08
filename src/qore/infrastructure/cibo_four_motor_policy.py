"""P0 four-motor shadow economics: common evidence schema, never order authority.

The four DISTINCT policy functions reside in their native CIBO modules. This
file supplies immutable causal observations and producer-side signed receipts
accepted by QDLE. Broker-deal provenance must be authenticated upstream.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType

HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
PRODUCERS = frozenset(("SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND"))
ZERO = Decimal("0")


class FourMotorPolicyError(ValueError):
    """Non-causal/unauthenticated economic input; do not propose an order."""


def nonnegative(name: str, x: Decimal) -> Decimal:
    if not isinstance(x, Decimal) or not x.is_finite() or x < ZERO:
        raise FourMotorPolicyError(f"{name} must be nonnegative finite Decimal")
    return x


def positive(name: str, x: Decimal) -> Decimal:
    if nonnegative(name, x) == ZERO:
        raise FourMotorPolicyError(f"{name} must be positive")
    return x


def roundtrip_commission_usd_per_lot(
    *, open_side_usd_per_lot: Decimal, close_side_usd_per_lot: Decimal
) -> Decimal:
    """Physical entry + exit fee per whole lot; not a broker schedule guess.

    A 7 USD/lot charge EACH side is 14 USD/lot roundtrip; for 0.03 lot
    this costs 0.42 USD. Feed must authenticate both sides before LIVE.
    """
    nonnegative("open_side_usd_per_lot", open_side_usd_per_lot)
    nonnegative("close_side_usd_per_lot", close_side_usd_per_lot)
    return open_side_usd_per_lot + close_side_usd_per_lot


def utc(name: str, t: datetime) -> datetime:
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise FourMotorPolicyError(f"{name} must be timezone-aware")
    return t.astimezone(UTC)


def digest(name: str, h: str) -> str:
    if not isinstance(h, str) or not HASH.fullmatch(h):
        raise FourMotorPolicyError(f"{name} requires source sha256")
    return h


@dataclass(frozen=True, slots=True)
class ReconciledQoreCashflow:
    """Net realized economic cashflow, including fees or losses (not float)."""
    event_id: str
    realized_at: datetime
    net_usd: Decimal
    source_settlement_sha256: str
    reconciled: bool

    def __post_init__(self) -> None:
        if not self.event_id or self.reconciled is not True:
            raise FourMotorPolicyError("cashflow must be reconciled and identified")
        utc("realized_at", self.realized_at)
        if not isinstance(self.net_usd, Decimal) or not self.net_usd.is_finite():
            raise FourMotorPolicyError("cashflow amount invalid")
        digest("settlement", self.source_settlement_sha256)


@dataclass(frozen=True, slots=True)
class FourMotorObservation:
    """One immutable causal epoch shared by four independent producers.

    QORE capital is NOT broker MT5 equity. Broker-loss USD/lot and margin
    USD/lot must come from contemporaneous broker observations.
    """
    request_id: str
    trader_id: str
    symbol: str
    side: str
    source_lane: str
    observed_at: datetime
    account_sequence: int
    broker_evidence_sha256: str
    initial_qore_nav_usd: Decimal
    reconciled_cashflows: tuple[ReconciledQoreCashflow, ...]
    protected_capital_usd: Decimal
    floating_loss_reserve_usd: Decimal
    risk_reservations_usd: Decimal
    bank_unreserved_usd: Decimal
    cushion_unreserved_usd: Decimal
    total_open_stop_risk_usd: Decimal
    correlated_open_stop_risk_usd: Decimal
    trader_open_stop_risk_usd: Decimal
    broker_free_margin_usd: Decimal
    broker_margin_reservations_usd: Decimal
    stop_loss_usd_per_lot: Decimal
    roundtrip_fees_usd_per_lot: Decimal
    execution_buffer_usd_per_lot: Decimal
    stress_extra_loss_usd_per_lot: Decimal
    broker_margin_usd_per_lot: Decimal
    symbol_max_lots: Decimal
    provider_direction_max_lots: Decimal
    open_and_reserved_direction_lots: Decimal
    broker_quote_at: datetime | None = None
    broker_fees_complete: bool = False
    broker_profit_valuation_complete: bool = False
    broker_margin_valuation_complete: bool = False

    def __post_init__(self) -> None:
        if not all(
            isinstance(x, str) and x for x in (self.request_id, self.trader_id, self.symbol)
        ):
            raise FourMotorPolicyError("signal, trader and symbol required")
        if self.side not in ("BUY", "SELL") or self.source_lane not in (
            "SOVEREIGN_BANK", "PORTFOLIO_CUSHION"
        ):
            raise FourMotorPolicyError("invalid trade side/source lane")
        if type(self.account_sequence) is not int or self.account_sequence <= 0:
            raise FourMotorPolicyError("causal account_sequence required")
        now = utc("observed_at", self.observed_at)
        quote = utc("broker_quote_at", self.broker_quote_at)
        age = (now - quote).total_seconds()
        if not 0 <= age <= 10:
            raise FourMotorPolicyError("broker valuation stale or from the future")
        for provenance in ("broker_fees_complete", "broker_profit_valuation_complete",
                           "broker_margin_valuation_complete"):
            if getattr(self, provenance) is not True:
                raise FourMotorPolicyError(f"{provenance} required: no incomplete broker economics")
        digest("broker_evidence_sha256", self.broker_evidence_sha256)
        if not isinstance(self.reconciled_cashflows, tuple) or any(
            not isinstance(e, ReconciledQoreCashflow) for e in self.reconciled_cashflows
        ):
            raise FourMotorPolicyError("reconciled cashflow tuple required")
        ids = [e.event_id for e in self.reconciled_cashflows]
        if len(ids) != len(set(ids)):
            raise FourMotorPolicyError("double-counted settled event")
        if any(utc("cashflow", e.realized_at) > now for e in self.reconciled_cashflows):
            raise FourMotorPolicyError("future realized PnL leaked into QORE NAV")
        for key in (
            "initial_qore_nav_usd", "protected_capital_usd", "floating_loss_reserve_usd",
            "risk_reservations_usd", "bank_unreserved_usd", "cushion_unreserved_usd",
            "total_open_stop_risk_usd", "correlated_open_stop_risk_usd",
            "trader_open_stop_risk_usd", "broker_free_margin_usd",
            "broker_margin_reservations_usd", "stop_loss_usd_per_lot",
            "roundtrip_fees_usd_per_lot", "execution_buffer_usd_per_lot",
            "stress_extra_loss_usd_per_lot", "broker_margin_usd_per_lot",
            "symbol_max_lots", "provider_direction_max_lots", "open_and_reserved_direction_lots",
        ):
            nonnegative(key, getattr(self, key))
        positive("initial_qore_nav_usd", self.initial_qore_nav_usd)
        positive("stop_loss_usd_per_lot", self.stop_loss_usd_per_lot)
        positive("broker_margin_usd_per_lot", self.broker_margin_usd_per_lot)
        if (self.correlated_open_stop_risk_usd > self.total_open_stop_risk_usd
                or self.trader_open_stop_risk_usd > self.total_open_stop_risk_usd):
            raise FourMotorPolicyError("risk subsets exceed global exposure")
        if self.risk_reservations_usd > self.initial_qore_nav_usd + sum(
            (e.net_usd for e in self.reconciled_cashflows), ZERO
        ):
            raise FourMotorPolicyError("reservations exceed causal capital")

    @property
    def qore_nav_usd(self) -> Decimal:
        return max(ZERO, self.initial_qore_nav_usd + sum(
            (e.net_usd for e in self.reconciled_cashflows), ZERO
        ))

    @property
    def base_entry_budget_usd(self) -> Decimal:
        return self.qore_nav_usd * Decimal("0.05")

    @property
    def risk_cash_remaining_usd(self) -> Decimal:
        return max(ZERO, self.qore_nav_usd - self.protected_capital_usd
                   - self.floating_loss_reserve_usd - self.risk_reservations_usd)

    @property
    def full_stop_cost_per_lot_usd(self) -> Decimal:
        return (self.stop_loss_usd_per_lot + self.roundtrip_fees_usd_per_lot
                + self.execution_buffer_usd_per_lot)

    @property
    def source_available_usd(self) -> Decimal:
        return (self.bank_unreserved_usd if self.source_lane == "SOVEREIGN_BANK"
                else self.cushion_unreserved_usd)


@dataclass(frozen=True, slots=True)
class FourMotorProposal:
    producer: str
    observation: FourMotorObservation
    limits: dict[str, str]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.producer not in PRODUCERS:
            raise FourMotorPolicyError("unknown economic producer")
        required = {
            "SIZING": {"approved_risk_usd"},
            "CIBO_COMPOUND": {"approved_risk_usd"},
            "ADAPTIVE_LEVERAGE": {"approved_max_lots", "approved_margin_usd"},
            "PORTFOLIO_COMPOUND": {"approved_source_funds_usd"},
        }[self.producer]
        if (
            set(self.limits) != required
            or not isinstance(self.reason_codes, tuple)
            or not self.reason_codes
        ):
            raise FourMotorPolicyError("producer limits or explanation missing")
        if any(not isinstance(reason, str) or not reason for reason in self.reason_codes):
            raise FourMotorPolicyError("reason code must identify an independent decision")
        object.__setattr__(self, "limits", MappingProxyType(dict(self.limits)))
        for name, value in self.limits.items():
            try:
                nonnegative(name, Decimal(value))
            except (ValueError, TypeError) as exc:
                raise FourMotorPolicyError("invalid economic limit") from exc

    def payload(self) -> dict[str, object]:
        s = self.observation
        return dict(producer=self.producer, request_id=s.request_id,
                    account_sequence=s.account_sequence,
                    observed_at=utc("observed_at", s.observed_at).isoformat(),
                    trader_id=s.trader_id, symbol=s.symbol, side=s.side,
                    source_lane=s.source_lane, qore_nav_usd=str(s.qore_nav_usd),
                    dynamic_entry_budget_usd=str(s.base_entry_budget_usd),
                    upstream_event_sha256=s.broker_evidence_sha256,
                    broker_quote_at=utc("broker_quote_at", s.broker_quote_at).isoformat(),
                    broker_fees_complete=s.broker_fees_complete,
                    broker_profit_valuation_complete=s.broker_profit_valuation_complete,
                    broker_margin_valuation_complete=s.broker_margin_valuation_complete,
                    realized_event_ids=[x.event_id for x in s.reconciled_cashflows],
                    decision_state="SHADOW_ADVISORY_ONLY",
                    rationale="; ".join(self.reason_codes),
                    reason_codes=list(self.reason_codes), **self.limits)


def sign_producer_receipt(
    proposal: FourMotorProposal, *, producer: str, secret: bytes
) -> dict[str, object]:
    """Call in the producer trust boundary; never give a coordinator all keys."""
    if proposal.producer != producer or producer not in PRODUCERS:
        raise FourMotorPolicyError("cross-producer receipt signing forbidden")
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise FourMotorPolicyError("producer HMAC key unavailable")
    payload = proposal.payload()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return dict(payload, source_event_sha256="sha256:" + hashlib.sha256(canonical).hexdigest(),
                hmac_sha256=hmac.new(secret, canonical, hashlib.sha256).hexdigest())
