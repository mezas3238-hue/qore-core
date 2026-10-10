"""P0 CEO CIBO ADMINISTRATOR contract -- received != executed.

Every *valid* Trader opportunity is received, including historical cognitive /
capital blocked ones. CIBO may propose a budgeted economic protective stop.
Only QDLE has physical volume authority; provider, treasury and QORE Risk retain
independent safeguards. NO SEND, NO FAKE FILL, NO IMPLIED EARLY-EXIT GUARANTEE.

This is a pure research/contract adapter. Do NOT reinterpret its price-linear
risk valuation as MT5 order_calc_profit or as LIVE broker authority.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR, localcontext

_EVIDENCE = re.compile(r"^sha256:[a-f0-9]{64}$")


class CiboAdministrationError(ValueError):
    """Invalid chronology or Trader/broker facts; never a market selection vote."""


def _cash(name: str, value: Decimal, *, allow_zero: bool = False) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboAdministrationError(f"{name}: finite Decimal required")
    if value < 0 or (value == 0 and not allow_zero):
        raise CiboAdministrationError(f"{name}: positive Decimal required")


def _timestamp(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CiboAdministrationError(f"{name}: timezone-aware event required")


@dataclass(frozen=True, slots=True)
class TraderSignalIntake:
    """Unconditional *economic reception* of an independently valid Trader trade.

    A Trader-created intent is NOT a broker fill. A preexisting broker fill
    instead needs an authenticated reconciliation contract before management.
    """

    signal_fingerprint: str
    trader_id: str
    symbol: str
    side: str
    entry_price: Decimal
    structural_stop_price: Decimal
    take_profit_price: Decimal
    decided_at: datetime
    trader_evidence_sha256: str

    def __post_init__(self) -> None:
        for key in ("signal_fingerprint", "trader_id", "symbol"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise CiboAdministrationError(f"{key}: required")
        if self.side not in ("BUY", "SELL"):
            raise CiboAdministrationError("side must be BUY or SELL")
        if not isinstance(self.trader_evidence_sha256, str) or not _EVIDENCE.fullmatch(
            self.trader_evidence_sha256
        ):
            raise CiboAdministrationError("authentic Trader source digest required")
        _timestamp("decided_at", self.decided_at)
        for name in ("entry_price", "structural_stop_price", "take_profit_price"):
            _cash(name, getattr(self, name))
        if self.side == "BUY":
            geometry = self.structural_stop_price < self.entry_price < self.take_profit_price
        else:
            geometry = self.take_profit_price < self.entry_price < self.structural_stop_price
        if not geometry:
            raise CiboAdministrationError("Trader entry/SL/TP structural geometry invalid")


@dataclass(frozen=True, slots=True)
class EconomicStopBudget:
    """Research price-valuation scenario, not a provider-proven MT5 quote.

    price_loss_usd_per_price_unit_per_lot must be a *conservative* broker
    snapshot value covering account FX conversion. Every cost component is per
    WHOLE lot, round trip, including all-in loss at a protective stop.
    """

    qore_reconciled_nav_usd: Decimal
    cibo_max_loss_usd: Decimal
    source_unreserved_loss_capacity_usd: Decimal
    broker_min_lot: Decimal
    broker_lot_step: Decimal
    tick_size_price: Decimal
    broker_min_stop_distance_price: Decimal
    price_loss_usd_per_price_unit_per_lot: Decimal
    opening_commission_usd_per_lot: Decimal
    closing_commission_usd_per_lot: Decimal
    execution_buffer_usd_per_lot: Decimal
    broker_data_as_of: datetime
    price_valuation_evidence_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "qore_reconciled_nav_usd", "cibo_max_loss_usd",
            "source_unreserved_loss_capacity_usd", "broker_min_stop_distance_price",
            "opening_commission_usd_per_lot", "closing_commission_usd_per_lot",
            "execution_buffer_usd_per_lot",
        ):
            _cash(name, getattr(self, name), allow_zero=True)
        for name in (
            "broker_min_lot", "broker_lot_step", "tick_size_price",
            "price_loss_usd_per_price_unit_per_lot",
        ):
            _cash(name, getattr(self, name))
        if self.broker_min_lot % self.broker_lot_step:
            raise CiboAdministrationError("broker minimum must belong to volume grid")
        _timestamp("broker_data_as_of", self.broker_data_as_of)
        if not isinstance(self.price_valuation_evidence_sha256, str) or not _EVIDENCE.fullmatch(
            self.price_valuation_evidence_sha256
        ):
            raise CiboAdministrationError("price valuation evidence digest required")


@dataclass(frozen=True, slots=True)
class CiboAdministrationReceipt:
    """One per Trader intake even when no admissible executable volume exists."""

    signal_fingerprint: str
    status: str
    budget_usd: Decimal
    structural_stop_price: Decimal
    proposed_protective_stop_price: Decimal | None
    min_lot_stop_plus_all_costs_usd: Decimal | None
    broker_min_lot: Decimal
    qdle_lots: None
    reason_codes: tuple[str, ...]
    is_broker_order: bool = False
    broker_fill_proven: bool = False


def propose_received_trader_management(
    *, signal: TraderSignalIntake, budget: EconomicStopBudget | None,
) -> CiboAdministrationReceipt:
    """Receive and attempt SL affordability, never a CIBO admission filter.

    If min lot cannot fit (including fees and min stop distance), receipt stays
    RECEIVED_UNFUNDABLE. A promised early close is NOT legal risk collateral.
    If input lacks provider evidence, retain the received signal, not a fill.
    Final volumes and MT5 order validity are for QDLE / broker gateway.
    """
    if not isinstance(signal, TraderSignalIntake):
        raise CiboAdministrationError("validated Trader signal required")
    if budget is None:
        return CiboAdministrationReceipt(
            signal.signal_fingerprint, "RECEIVED_NEEDS_BROKER_VALUATION",
            Decimal(0), signal.structural_stop_price, None, None,
            Decimal(0), None, ("BROKER_VALUATION_MISSING",),
        )
    if not isinstance(budget, EconomicStopBudget):
        raise CiboAdministrationError("EconomicStopBudget required")
    if budget.broker_data_as_of > signal.decided_at:
        raise CiboAdministrationError("future broker price evidence forbidden")
    with localcontext() as ctx:
        ctx.prec = 100
        cap = min(
            budget.qore_reconciled_nav_usd * Decimal("0.05"),
            budget.cibo_max_loss_usd,
            budget.source_unreserved_loss_capacity_usd,
        )
        per_lot_fixed = (
            budget.opening_commission_usd_per_lot
            + budget.closing_commission_usd_per_lot
            + budget.execution_buffer_usd_per_lot
        )
        risk_per_lot_unit = budget.price_loss_usd_per_price_unit_per_lot
        original_distance = abs(signal.entry_price - signal.structural_stop_price)
        original_risk_min = budget.broker_min_lot * (
            original_distance * risk_per_lot_unit + per_lot_fixed
        )
        if cap <= 0:
            return CiboAdministrationReceipt(
                signal.signal_fingerprint, "RECEIVED_UNFUNDABLE", cap,
                signal.structural_stop_price, None, original_risk_min,
                budget.broker_min_lot, None, ("ZERO_ALLOCATED_RISK_CAPACITY",),
            )
        if (original_distance >= budget.broker_min_stop_distance_price
            and original_risk_min <= cap):
            return CiboAdministrationReceipt(
                signal.signal_fingerprint, "RECEIVED_READY_FOR_QDLE",
                cap, signal.structural_stop_price,
                signal.structural_stop_price, original_risk_min,
                budget.broker_min_lot, None, ("STRUCTURAL_STOP_AFFORDABLE_MIN_LOT",),
            )
        after_fixed = cap / budget.broker_min_lot - per_lot_fixed
        if after_fixed <= 0:
            return CiboAdministrationReceipt(
                signal.signal_fingerprint, "RECEIVED_UNFUNDABLE", cap,
                signal.structural_stop_price, None, original_risk_min,
                budget.broker_min_lot, None, ("FEES_AND_BUFFERS_EXCEED_CAP",),
            )
        max_distance = after_fixed / risk_per_lot_unit
        # Distance quantization is toward ZERO (risk never rounded up).
        aligned_distance = (
            (max_distance / budget.tick_size_price).to_integral_value(
                rounding=ROUND_FLOOR
            ) * budget.tick_size_price
        )
        # Entry must be on the provider tick grid; otherwise exact stop
        # construction would be a synthetic untradable price.
        if signal.entry_price % budget.tick_size_price:
            return CiboAdministrationReceipt(
                signal.signal_fingerprint, "RECEIVED_NEEDS_BROKER_VALUATION",
                cap, signal.structural_stop_price, None, original_risk_min,
                budget.broker_min_lot, None, ("ENTRY_NOT_BROKER_TICK_ALIGNED",),
            )
        if aligned_distance < budget.broker_min_stop_distance_price or aligned_distance <= 0:
            return CiboAdministrationReceipt(
                signal.signal_fingerprint, "RECEIVED_UNFUNDABLE", cap,
                signal.structural_stop_price, None, original_risk_min,
                budget.broker_min_lot, None, ("PROTECTIVE_STOP_BELOW_BROKER_MIN",),
            )
        if aligned_distance >= original_distance:
            # Original geometry or min stop is invalid; no silent widening
            # or relabeling of structural invalidation.
            return CiboAdministrationReceipt(
                signal.signal_fingerprint, "RECEIVED_UNFUNDABLE", cap,
                signal.structural_stop_price, None, original_risk_min,
                budget.broker_min_lot, None, ("ORIGINAL_STOP_BELOW_BROKER_MIN",),
            )
        stop = (
            signal.entry_price - aligned_distance if signal.side == "BUY"
            else signal.entry_price + aligned_distance
        )
        per_min_lot = budget.broker_min_lot * (
            aligned_distance * risk_per_lot_unit + per_lot_fixed
        )
        if per_min_lot > cap:
            raise CiboAdministrationError("economic protective stop violates risk cap")
        return CiboAdministrationReceipt(
            signal.signal_fingerprint, "RECEIVED_READY_FOR_QDLE", cap,
            signal.structural_stop_price, stop, per_min_lot,
            budget.broker_min_lot, None,
            ("ECONOMIC_PROTECTIVE_STOP_PROPOSED",
             "STRUCTURAL_STOP_RETAINED_AS_REFERENCE",
             "REPRICE_AND_ORDER_CHECK_REQUIRED"),
        )
