"""Seven CRT family *hypothetical* order templates; no execution system.

Pine R4-A is a detector and DOES NOT specify orders / stops / targets.
All these templates are research hypotheses. Without event parity, verified
broker costs and untouched OOS they are not eligible for certified PnL.
This module has NO network/broker API, NO live/demo execution capability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from research.crt_r4a_holdout.seven_family_contract import Family

H4 = timedelta(hours=4)


@dataclass(frozen=True)
class MarketGeometry:
    """Fully known at signal availability; independent geometry per family."""

    c1_high: Decimal
    c1_low: Decimal
    setup_open: Decimal
    setup_close: Decimal
    sweep_high: Decimal
    sweep_low: Decimal
    retest_high: Decimal | None = None
    retest_low: Decimal | None = None
    retest_close: Decimal | None = None
    retest_closed_at: datetime | None = None

    def __post_init__(self) -> None:
        if any(
            not x.is_finite() or x <= 0
            for x in (
                self.c1_high, self.c1_low, self.setup_open,
                self.setup_close, self.sweep_high, self.sweep_low,
            )
        ):
            raise ValueError("price not positive and finite")
        if self.c1_high <= self.c1_low or self.sweep_high <= self.sweep_low:
            raise ValueError("invalid C1/sweep geometry")


@dataclass(frozen=True)
class PaperPlan:
    family: Family
    direction: int
    source_event_id: str
    available_at: datetime
    planned_entry_type: str
    entry_price: Decimal
    stop_price: Decimal
    take_profit_price: Decimal
    risk_price_distance: Decimal
    reward_to_risk: Decimal
    expiry_at: datetime
    broker_orders_executed: int = 0
    pine_parity_certified: bool = False
    broker_net_costs_certified: bool = False


def _tick(price: Decimal, tick: Decimal, rounding: str) -> Decimal:
    return (price / tick).to_integral_value(rounding=rounding) * tick


def plan_research_order(
    family: Family, *, direction: int, source_event_id: str,
    geometry: MarketGeometry, available_at: datetime, mss_at: datetime,
    ratified_at: datetime, atr_h4: Decimal, price_tick: Decimal,
    spread_quote: Decimal | None = None,
    max_entry_offset_atr: Decimal = Decimal("0.50"),
    sl_buffer_atr: Decimal = Decimal("0.25"),
    expiry_h4: int = 3,
) -> PaperPlan:
    """Make non-executable SL/TP hypothesis with causal timestamp guards.

    Non-retest: limit 50% of family-owned H4 setup candle body.
    Retest: use the OWN M15 retest close as a REFERENCE PRICE only.
    A market fill can occur no earlier than the following tradable quote.
    Buffers widen AWAY from trade direction; tick rounding conservative.
    """
    if not isinstance(family, Family):
        raise ValueError("not a registered seven-family CRT model")
    if direction not in (1, -1) or not source_event_id.strip():
        raise ValueError("invalid independent source-cycle identity or side")
    if any(
        t.tzinfo is None
        for t in (available_at, mss_at, ratified_at)
    ):
        raise ValueError("all event times require UTC offset")
    if available_at < max(mss_at, ratified_at):
        raise ValueError("future-looking order before its own MSS/ratification")
    if (
        atr_h4 <= 0 or not atr_h4.is_finite() or
        price_tick <= 0 or not price_tick.is_finite()
    ):
        raise ValueError("invalid ATR/tick")
    if (
        max_entry_offset_atr <= 0 or sl_buffer_atr <= 0
        or not (1 <= expiry_h4 <= 3)
    ):
        raise ValueError("unfrozen hypothetical order-parameter range")
    if (
        spread_quote is not None and (
            spread_quote < 0 or not spread_quote.is_finite()
        )
    ):
        raise ValueError("invalid optional spread quote")
    is_retest = family is Family.M15_RETEST
    if is_retest and (
        geometry.retest_high is None or geometry.retest_low is None
        or geometry.retest_close is None
        or geometry.retest_closed_at is None
        or geometry.retest_closed_at.tzinfo is None
        or not geometry.retest_close.is_finite()
        or geometry.retest_low <= 0
        or geometry.retest_high <= geometry.retest_low
        or not geometry.retest_low <= geometry.retest_close <= geometry.retest_high
        or geometry.retest_closed_at <= mss_at
        or geometry.retest_closed_at > available_at
    ):
        raise ValueError(
            "M15 retest requires OWN closed M15 OHLC/time, strictly "
            "after MSS and not after order availability"
        )
    midpoint = (geometry.setup_open + geometry.setup_close) / 2
    base_entry = geometry.retest_close if is_retest else midpoint
    tick_entry = _tick(
        base_entry, price_tick, ROUND_FLOOR if direction == 1
        else ROUND_CEILING
    )
    # If the level is far from the H4 close when the signal is known, it
    # is not the same bounded research trade. No automatic parameter fitting.
    if not is_retest and (
        abs(base_entry - geometry.setup_close)
        > max_entry_offset_atr * atr_h4
    ):
        raise ValueError("limit entry too far from closed H4 setup")
    buffer = max(
        sl_buffer_atr * atr_h4, spread_quote or Decimal("0")
    )
    # Must use exact OWN terminal sweep and for retest its own M15 wick.
    extreme_low = (
        geometry.retest_low if is_retest else geometry.sweep_low
    )
    extreme_high = (
        geometry.retest_high if is_retest else geometry.sweep_high
    )
    if direction == 1:
        sl = _tick(extreme_low - buffer, price_tick, ROUND_FLOOR)
        tp = _tick(geometry.c1_high, price_tick, ROUND_FLOOR)
        risk = tick_entry - sl
        reward = tp - tick_entry
    else:
        sl = _tick(extreme_high + buffer, price_tick, ROUND_CEILING)
        tp = _tick(geometry.c1_low, price_tick, ROUND_CEILING)
        risk = sl - tick_entry
        reward = tick_entry - tp
    if tick_entry <= 0 or sl <= 0 or tp <= 0 or risk <= 0 or reward <= 0:
        raise ValueError("invalid bracket: stop or TP on wrong side of entry")
    return PaperPlan(
        family, direction, source_event_id, available_at,
        "HYPOTHETICAL_M15_CLOSE" if is_retest else "HYPOTHETICAL_H4_BODY_LIMIT",
        tick_entry, sl, tp, risk, reward / risk,
        available_at + H4 * expiry_h4,
    )
