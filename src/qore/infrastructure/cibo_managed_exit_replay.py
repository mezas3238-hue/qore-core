"""CIBO P0 causal post-fill managed exit replay, provider-neutral SHADOW.

Unlike a historical scalar R outcome, this needs a complete ordered executable
bid/ask OHLC path from the true assumed fill until a verifiable exit. STOP-FIRST
if both SL and TP occur within one bar. Management decisions at bar close can
only apply from NEXT bar's opening; OPEN gaps can be worse than stop.
No fabricated intrabar ordering, broker execution, actual fills, or certifications.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR, localcontext


class ManagedReplayError(ValueError):
    """Missing causal path, invalid risk geometry, or broker-lot violation."""


def _p(v: Decimal, name: str, zero: bool = False) -> None:
    if not isinstance(v, Decimal) or not v.is_finite() or (v < 0 if zero else v <= 0):
        raise ManagedReplayError(f"{name} must be finite and {'nonnegative' if zero else 'positive'}")


def _at(v: datetime, name: str) -> None:
    if not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None:
        raise ManagedReplayError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ExecutableOhlcBar:
    """Executable bid and ask observations, not historical MID guesswork.

    Each OHLC is a broker-observed/declared executable side; the whole bar is
    a coarse path. Indeterminate stop/TP intrabar order always goes STOP first.
    """
    opened_at: datetime
    closed_at: datetime
    bid_open: Decimal
    bid_high: Decimal
    bid_low: Decimal
    bid_close: Decimal
    ask_open: Decimal
    ask_high: Decimal
    ask_low: Decimal
    ask_close: Decimal
    evidence_sha256: str

    def __post_init__(self) -> None:
        _at(self.opened_at, "opened_at")
        _at(self.closed_at, "closed_at")
        if self.closed_at <= self.opened_at:
            raise ManagedReplayError("bar close must follow open")
        for label in ("bid_open", "bid_high", "bid_low", "bid_close",
                      "ask_open", "ask_high", "ask_low", "ask_close"):
            _p(getattr(self, label), label)
        if not (self.bid_low <= min(self.bid_open, self.bid_close)
                <= max(self.bid_open, self.bid_close) <= self.bid_high
                and self.ask_low <= min(self.ask_open, self.ask_close)
                <= max(self.ask_open, self.ask_close) <= self.ask_high):
            raise ManagedReplayError("invalid executable OHLC range")
        if any(getattr(self, "bid_" + suffix) > getattr(self, "ask_" + suffix)
               for suffix in ("open", "high", "low", "close")):
            raise ManagedReplayError("negative executable spread")
        if not isinstance(self.evidence_sha256, str) or len(self.evidence_sha256) != 71 or (
            not self.evidence_sha256.startswith("sha256:")
            or any(x not in "0123456789abcdef" for x in self.evidence_sha256[7:])
        ):
            raise ManagedReplayError("bar needs provenance SHA256")


@dataclass(frozen=True, slots=True)
class CiboExitPolicy:
    partial_at_r: Decimal = Decimal("1")
    partial_fraction: Decimal = Decimal("0.5")
    breakeven_at_r: Decimal = Decimal("1")
    trailing_activate_at_r: Decimal = Decimal("1.5")
    trailing_distance_r: Decimal = Decimal("0.75")
    defensive_close_at_r: Decimal = Decimal("-0.5")

    def __post_init__(self) -> None:
        for field in ("partial_at_r", "partial_fraction", "breakeven_at_r",
                      "trailing_activate_at_r", "trailing_distance_r"):
            _p(getattr(self, field), field)
        if self.partial_fraction >= 1:
            raise ManagedReplayError("partial fraction must be < 1")
        if not isinstance(self.defensive_close_at_r, Decimal) or not (
            self.defensive_close_at_r.is_finite() and
            Decimal("-1") < self.defensive_close_at_r < 0
        ):
            raise ManagedReplayError("defensive threshold must be between -1R and 0")


@dataclass(frozen=True, slots=True)
class CiboManagedTrade:
    signal_id: str
    symbol: str
    side: str
    entry_at: datetime
    entry_price: Decimal
    trader_structural_stop_price: Decimal
    economic_stop_price: Decimal
    trader_take_profit_price: Decimal
    lots: Decimal
    min_lot: Decimal
    lot_step: Decimal
    price_pnl_usd_per_lot_per_unit: Decimal
    roundtrip_commission_usd_per_lot: Decimal
    maximum_all_in_risk_usd: Decimal

    def __post_init__(self) -> None:
        if not self.signal_id or not self.symbol or self.side not in ("BUY", "SELL"):
            raise ManagedReplayError("identified long/short trade required")
        _at(self.entry_at, "entry_at")
        for field in ("entry_price", "trader_structural_stop_price",
                      "economic_stop_price", "trader_take_profit_price",
                      "lots", "min_lot", "lot_step",
                      "price_pnl_usd_per_lot_per_unit",
                      "maximum_all_in_risk_usd"):
            _p(getattr(self, field), field)
        _p(self.roundtrip_commission_usd_per_lot, "commission", zero=True)
        if self.lots < self.min_lot or (self.lots-self.min_lot) % self.lot_step:
            raise ManagedReplayError("nonphysical volume grid")
        if self.side == "BUY":
            valid = (self.trader_structural_stop_price <= self.economic_stop_price
                     < self.entry_price < self.trader_take_profit_price)
        else:
            valid = (self.trader_take_profit_price < self.entry_price
                     < self.economic_stop_price <= self.trader_structural_stop_price)
        if not valid:
            raise ManagedReplayError("economic stop cannot move outside Trader structural risk")
        with localcontext() as ctx:
            ctx.prec = 100
            risk = self.lots * (
                abs(self.entry_price-self.economic_stop_price)
                * self.price_pnl_usd_per_lot_per_unit
                + self.roundtrip_commission_usd_per_lot
            )
        if risk > self.maximum_all_in_risk_usd:
            raise ManagedReplayError("risk at economic protective stop exceeds budget")


@dataclass(frozen=True, slots=True)
class CiboManagedExitResult:
    status: str
    signal_id: str
    exit_reason: str | None
    exit_at: datetime | None
    net_pnl_usd_proxy: Decimal | None
    gross_pnl_usd_proxy: Decimal | None
    commission_usd_proxy: Decimal | None
    remaining_lots: Decimal
    partial_count: int
    stop_update_count: int
    defensive_trigger_count: int
    intratrade_worst_pnl_usd_proxy: Decimal | None
    bars_consumed: int
    actions: tuple[str, ...]
    certified: bool = False
    mt5_fills_proven: int = 0


def replay_cibo_managed_position(
    trade: CiboManagedTrade, bars: tuple[ExecutableOhlcBar, ...],
    *, policy: CiboExitPolicy | None = None,
) -> CiboManagedExitResult:
    """Causal OHLC result iff complete consecutive price path ends at SL/TP.

    If no hit before source bars end, return NOT_MEASURABLE (no closing PnL).
    A missing/incomplete path must NEVER be treated as a winning outcome.
    """
    if not isinstance(trade, CiboManagedTrade) or not isinstance(bars, tuple):
        raise ManagedReplayError("trade and immutable bar tuple required")
    policy = policy or CiboExitPolicy()
    if not isinstance(policy, CiboExitPolicy):
        raise ManagedReplayError("CiboExitPolicy required")
    if not bars:
        return CiboManagedExitResult(
            "NEEDS_PRICE_PATH", trade.signal_id, None, None, None, None, None,
            trade.lots, 0, 0, 0, None, 0, ("NO_EXECUTABLE_BID_ASK_BARS",)
        )
    if any(not isinstance(b, ExecutableOhlcBar) for b in bars):
        raise ManagedReplayError("typed executable bars required")
    if bars[0].opened_at != trade.entry_at:
        raise ManagedReplayError("price path must start exactly at hypothetical fill")
    for prev, nxt in zip(bars, bars[1:]):
        if prev.closed_at != nxt.opened_at:
            raise ManagedReplayError("gaps or overlaps in market path cannot be silently joined")
    long = trade.side == "BUY"
    structural_r = abs(trade.entry_price-trade.trader_structural_stop_price)
    protective_stop = trade.economic_stop_price
    lots = trade.lots
    with localcontext() as ctx:
        ctx.prec = 100
        gross = Decimal(0)
        fees = Decimal(0)
        actions: list[str] = []
        worst = Decimal(0)
        partials = stop_updates = defensive = 0
        pending_partial = pending_defensive = False
        pending_stop: Decimal | None = None
        closed_at: datetime | None = None
        exit_reason: str | None = None

        def settle(exit_price: Decimal, qty: Decimal, reason: str, at: datetime) -> None:
            nonlocal gross, fees, lots, closed_at, exit_reason
            pnl = (exit_price-trade.entry_price if long
                   else trade.entry_price-exit_price)
            gross += pnl * trade.price_pnl_usd_per_lot_per_unit * qty
            fees += qty * trade.roundtrip_commission_usd_per_lot
            lots -= qty
            actions.append(reason + ":" + str(qty) + "@" + str(exit_price))
            if lots == 0:
                closed_at, exit_reason = at, reason

        for i, bar in enumerate(bars):
            side_open = bar.bid_open if long else bar.ask_open
            side_close = bar.bid_close if long else bar.ask_close
            side_low = bar.bid_low if long else bar.ask_high
            side_high = bar.bid_high if long else bar.ask_low
            # Broker/open gap evaluated against ALREADY PRESENT stop. A pending
            # new stop cannot be retroactively executed in this gap.
            old_stop_hit_at_open = side_open <= protective_stop if long else side_open >= protective_stop
            if old_stop_hit_at_open:
                settle(side_open, lots, "GAP_OPEN_STOP", bar.opened_at)
                break
            if (side_open >= trade.trader_take_profit_price if long
                else side_open <= trade.trader_take_profit_price):
                settle(trade.trader_take_profit_price, lots, "GAP_OPEN_TARGET", bar.opened_at)
                break
            if pending_stop is not None:
                protective_stop = (
                    max(protective_stop, pending_stop) if long
                    else min(protective_stop, pending_stop)
                )
                stop_updates += 1
                actions.append("APPLY_PROTECTIVE_STOP_NEXT_OPEN:" + str(protective_stop))
                pending_stop = None
                if side_open <= protective_stop if long else side_open >= protective_stop:
                    settle(side_open, lots, "OPEN_GAP_AFTER_STOP_UPDATE", bar.opened_at)
                    break
            if pending_defensive:
                defensive += 1
                settle(side_open, lots, "DEFENSIVE_CLOSE_NEXT_OPEN", bar.opened_at)
                break
            if pending_partial:
                qty = (trade.lots * policy.partial_fraction / trade.lot_step).to_integral_value(
                    rounding=ROUND_FLOOR
                ) * trade.lot_step
                # Physical lot grid for BOTH residual and partial.
                if qty >= trade.min_lot and lots-qty >= trade.min_lot:
                    settle(side_open, qty, "PARTIAL_NEXT_OPEN", bar.opened_at)
                    partials += 1
                else:
                    actions.append("PARTIAL_SKIPPED_BROKER_MIN_GRID")
                pending_partial = False
            # Touch sequencing is UNKNOWN inside the bar: STOP before TP, even
            # if this sacrifices gains; no hindsight-friendly path selection.
            loss_side_extreme = bar.bid_low if long else bar.ask_high
            mark_min = (
                (loss_side_extreme-trade.entry_price if long
                 else trade.entry_price-loss_side_extreme)
                * trade.price_pnl_usd_per_lot_per_unit * lots
                + gross - fees - lots * trade.roundtrip_commission_usd_per_lot
            )
            worst = min(worst, mark_min)
            hit_stop = (bar.bid_low <= protective_stop if long
                        else bar.ask_high >= protective_stop)
            hit_target = (bar.bid_high >= trade.trader_take_profit_price if long
                          else bar.ask_low <= trade.trader_take_profit_price)
            if hit_stop:
                settle(protective_stop, lots, "STOP_FIRST_OR_SL_ONLY", bar.closed_at)
                break
            if hit_target:
                settle(trade.trader_take_profit_price, lots, "TAKE_PROFIT", bar.closed_at)
                break
            # At CLOSE compute actions effective NEXT OPEN only.
            favorable_r = ((side_close-trade.entry_price) if long
                           else (trade.entry_price-side_close)) / structural_r
            if favorable_r <= policy.defensive_close_at_r:
                pending_defensive = True
                actions.append("DEFENSIVE_TRIGGER_AT_CLOSE:" + bar.closed_at.isoformat())
            elif favorable_r >= policy.partial_at_r and partials == 0 and not pending_partial:
                pending_partial = True
                actions.append("PARTIAL_TRIGGER_AT_CLOSE:" + bar.closed_at.isoformat())
            if favorable_r >= policy.breakeven_at_r:
                pending = trade.entry_price
                if favorable_r >= policy.trailing_activate_at_r:
                    trail_distance = structural_r * policy.trailing_distance_r
                    candidate = side_close-trail_distance if long else side_close+trail_distance
                    pending = max(pending,candidate) if long else min(pending,candidate)
                pending_stop = (
                    max(protective_stop,pending) if long
                    else min(protective_stop,pending)
                )
        else:
            # Incomplete history (or target never hit) -> no synthetic PnL
            return CiboManagedExitResult(
                "NEEDS_PRICE_PATH", trade.signal_id, None, None, None, None, None,
                lots, partials, stop_updates, defensive, None, len(bars),
                tuple(actions)+("NO_TERMINAL_EXIT_IN_SUPPLIED_PRICE_PATH",)
            )
        return CiboManagedExitResult(
            "SHADOW_SETTLED", trade.signal_id, exit_reason, closed_at,
            gross-fees, gross, fees, lots, partials, stop_updates, defensive,
            worst, i+1, tuple(actions),
        )
