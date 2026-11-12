"""Single-order, closed-M5 bid/ask research replay. NO broker order interfaces.

Fills and cost arithmetic are isolated from CRT pattern recognition. Prices,
contract conversions and cost schedules MUST be supplied independently; missing
provider evidence never produces an authorized net performance claim.
No portfolio-level netting or multi-asset currency conversion is implemented.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable, Protocol

M5 = timedelta(minutes=5)
D0 = Decimal("0")


class PaperPlanLike(Protocol):
    source_event_id: str
    family: object
    direction: int
    planned_entry_type: str
    available_at: datetime
    expiry_at: datetime
    entry_price: Decimal
    stop_price: Decimal
    take_profit_price: Decimal


def _price(p: Decimal) -> bool:
    return isinstance(p, Decimal) and p.is_finite() and p > 0


@dataclass(frozen=True)
class BidAskM5:
    opened_at: datetime
    bid_open: Decimal
    bid_high: Decimal
    bid_low: Decimal
    bid_close: Decimal
    ask_open: Decimal
    ask_high: Decimal
    ask_low: Decimal
    ask_close: Decimal

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None:
            raise ValueError("offset-aware quote M5 required")
        vals = (
            self.bid_open, self.bid_high, self.bid_low, self.bid_close,
            self.ask_open, self.ask_high, self.ask_low, self.ask_close
        )
        if not all(_price(v) for v in vals):
            raise ValueError("positive finite Decimal quotes required")
        if not (
            self.bid_low <= min(self.bid_open, self.bid_close)
            <= max(self.bid_open, self.bid_close) <= self.bid_high
            and self.ask_low <= min(self.ask_open, self.ask_close)
            <= max(self.ask_open, self.ask_close) <= self.ask_high
            and self.bid_open <= self.ask_open
            and self.bid_close <= self.ask_close
        ):
            raise ValueError("invalid bid/ask OHLC")

    @property
    def closed_at(self) -> datetime:
        return self.opened_at + M5


@dataclass(frozen=True)
class CostAssumptions:
    commission_per_unit_per_side_quote: Decimal
    adverse_slippage_price: Decimal

    def __post_init__(self) -> None:
        if any(
            not isinstance(x, Decimal) or not x.is_finite() or x < 0
            for x in (
                self.commission_per_unit_per_side_quote,
                self.adverse_slippage_price
            )
        ):
            raise ValueError("nonnegative finite explicit cost inputs required")


@dataclass(frozen=True)
class SwapDebit:
    charged_at: datetime
    quote_amount_per_unit: Decimal

    def __post_init__(self) -> None:
        if (
            self.charged_at.tzinfo is None
            or not isinstance(self.quote_amount_per_unit, Decimal)
            or not self.quote_amount_per_unit.is_finite()
        ):
            raise ValueError("invalid timestamped swap debit/credit")


@dataclass(frozen=True)
class PaperResult:
    status: str
    source_event_id: str
    family: str
    entry_at: datetime | None = None
    exit_at: datetime | None = None
    entry_fill: Decimal | None = None
    exit_fill: Decimal | None = None
    gross_quote: Decimal | None = None
    commission_quote: Decimal | None = None
    swap_quote: Decimal | None = None
    net_quote: Decimal | None = None
    net_r: Decimal | None = None
    broker_orders_executed: int = 0
    provider_costs_certified: bool = False
    original_pine_parity_certified: bool = False


def simulate_single(
    plan: PaperPlanLike, quotes: Iterable[BidAskM5], *,
    quantity: Decimal, costs: CostAssumptions,
    swap_debits: Iterable[SwapDebit] = (),
) -> PaperResult:
    """Conservative single-trade experiment; no same-bar favorable TP.

    Limit entries use ASK-low for longs / BID-high for shorts and fill no
    better than the order limit. Market-reference M15 retest uses the NEXT
    available M5 quote OPEN, never retro-fills at the M15 close.
    Same-bar entry and stop: assume adverse stop occurs after entry.
    Same-bar entry and target: never award the target without sequencing.
    Later bar SL and TP: stop wins. Gapped stops fill at worse OPEN;
    all stop and market fills suffer adverse input slippage.
    Net values are in quote-price units times quantity, NOT account USD.
    """
    if (
        not isinstance(quantity, Decimal) or not _price(quantity)
        or not isinstance(plan.source_event_id, str)
        or not plan.source_event_id.strip()
        or plan.direction not in (1, -1)
        or plan.available_at.tzinfo is None
        or plan.expiry_at.tzinfo is None
        or plan.expiry_at <= plan.available_at
        or not all(_price(x) for x in (
            plan.entry_price, plan.stop_price, plan.take_profit_price
        ))
    ):
        raise ValueError("invalid bounded causal paper plan/quantity")
    if plan.planned_entry_type not in (
        "HYPOTHETICAL_M15_CLOSE", "HYPOTHETICAL_H4_BODY_LIMIT"
    ):
        raise ValueError("unknown paper entry hypothesis")
    if not (
        (plan.stop_price < plan.entry_price < plan.take_profit_price)
        if plan.direction == 1 else
        (plan.take_profit_price < plan.entry_price < plan.stop_price)
    ):
        raise ValueError("invalid protective bracket")
    debits = tuple(swap_debits)
    if any(not isinstance(x, SwapDebit) for x in debits):
        raise ValueError("swap event must carry a timestamp and Decimal")
    ref = {"source_event_id": plan.source_event_id, "family": str(plan.family)}
    entry_at: datetime | None = None
    entry: Decimal | None = None
    previous: datetime | None = None
    last_end: datetime | None = None
    market = plan.planned_entry_type == "HYPOTHETICAL_M15_CLOSE"

    for bar in quotes:
        if not isinstance(bar, BidAskM5):
            raise ValueError("requires actual bid/ask M5 quote bars")
        if previous is not None and bar.opened_at <= previous:
            raise ValueError("nonmonotone quote tape")
        previous, last_end = bar.opened_at, bar.closed_at
        if bar.opened_at < plan.available_at:
            continue  # No intrabar fill from a candle already open at signal.
        just_filled = False
        if entry is None:
            if bar.opened_at >= plan.expiry_at:
                return PaperResult("EXPIRED_NO_FILL", **ref)
            if market:
                entry = (
                    bar.ask_open + costs.adverse_slippage_price
                    if plan.direction == 1 else
                    bar.bid_open - costs.adverse_slippage_price
                )
            elif plan.direction == 1 and bar.ask_low <= plan.entry_price:
                entry = plan.entry_price
            elif plan.direction == -1 and bar.bid_high >= plan.entry_price:
                entry = plan.entry_price
            if entry is None:
                continue
            if entry <= 0 or not (
                (plan.stop_price < entry < plan.take_profit_price)
                if plan.direction == 1 else
                (plan.take_profit_price < entry < plan.stop_price)
            ):
                return PaperResult("REJECTED_CHANGED_PRICE", **ref)
            entry_at = bar.closed_at if not market else bar.opened_at
            just_filled = True

        if plan.direction == 1:
            stop_hit = bar.bid_low <= plan.stop_price
            target_hit = bar.bid_high >= plan.take_profit_price
            stop_fill = min(plan.stop_price, bar.bid_open) - costs.adverse_slippage_price
        else:
            stop_hit = bar.ask_high >= plan.stop_price
            target_hit = bar.ask_low <= plan.take_profit_price
            stop_fill = max(plan.stop_price, bar.ask_open) + costs.adverse_slippage_price

        if stop_hit:
            exit_price = stop_fill
            status = "CLOSED_STOP"
        elif target_hit and not just_filled:
            exit_price = plan.take_profit_price
            status = "CLOSED_TARGET"
        else:
            continue

        assert entry is not None and entry_at is not None
        exit_at = bar.closed_at
        gross = (exit_price - entry) * plan.direction * quantity
        commission = costs.commission_per_unit_per_side_quote * quantity * 2
        swap = sum(
            (d.quote_amount_per_unit * quantity for d in debits
             if entry_at < d.charged_at <= exit_at),
            D0,
        )
        net = gross - commission - swap
        initial_risk = abs(entry - plan.stop_price) * quantity
        return PaperResult(
            status, **ref, entry_at=entry_at, exit_at=exit_at,
            entry_fill=entry, exit_fill=exit_price, gross_quote=gross,
            commission_quote=commission, swap_quote=swap,
            net_quote=net, net_r=net / initial_risk,
        )
    if entry is None:
        expired = last_end is not None and last_end >= plan.expiry_at
        return PaperResult("EXPIRED_NO_FILL" if expired else "NO_FILL_TAPE_END", **ref)
    return PaperResult(
        "OPEN_UNSETTLED", **ref, entry_at=entry_at, entry_fill=entry,
    )
