"""Frozen Classic management, economics, forensics and Walk-Forward metrics for R5."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, getcontext
from statistics import median

from turtle_soup_r5_replay_core import (
    MARKETS,
    OOS_START,
    Bar,
    Evaluation,
    Fill,
    Market,
    decimal,
    tick_rows,
    timestamp,
)

getcontext().prec = 28
POLICIES = {
    "C_TRAIL1_H3": (1, 3),
    "C_TRAIL2_H3": (2, 3),
    "C_TRAIL1_H6": (1, 6),
    "C_TRAIL2_H6": (2, 6),
}
FOLDS = (
    ("WF1", datetime(2024, 9, 1, tzinfo=UTC), datetime(2024, 12, 1, tzinfo=UTC)),
    ("WF2", datetime(2024, 12, 1, tzinfo=UTC), datetime(2025, 3, 1, tzinfo=UTC)),
    ("WF3", datetime(2025, 3, 1, tzinfo=UTC), datetime(2025, 6, 1, tzinfo=UTC)),
    ("WF4", datetime(2025, 6, 1, tzinfo=UTC), datetime(2025, 9, 1, tzinfo=UTC)),
    ("WF5", datetime(2025, 9, 1, tzinfo=UTC), datetime(2025, 12, 1, tzinfo=UTC)),
    ("WF6", datetime(2025, 12, 1, tzinfo=UTC), OOS_START),
)
R1_TOTAL = Decimal("-19.84589655480285653235517066")
R1_STRESS = Decimal("-25.69179310960571306471034133")


@dataclass(frozen=True, slots=True)
class Trade:
    market: str
    side: str
    fill_at: datetime
    entry: Decimal
    stop: Decimal
    exit_price: Decimal | None
    exit_at: datetime | None
    gross_r: Decimal | None
    net_1bp_r: Decimal | None
    net_2bp_r: Decimal | None
    decision: str
    exit_reason: str
    policy: str
    mfe_lower_bound_r: Decimal
    mae_lower_bound_r: Decimal
    holding_bars: int
    gap_stop: bool
    resolution: str


def directional(side: str, entry: Decimal, price: Decimal) -> Decimal:
    return price - entry if side == "long" else entry - price


def bar_stop(side: str, stop: Decimal, bar: Bar) -> tuple[Decimal | None, str | None]:
    if side == "long":
        if bar.open <= stop:
            return bar.open, "gap-stop"
        if bar.low <= stop:
            return stop, "stop"
    else:
        if bar.open >= stop:
            return bar.open, "gap-stop"
        if bar.high >= stop:
            return stop, "stop"
    return None, None


def excursions(
    side: str,
    entry: Decimal,
    risk: Decimal,
    bar: Bar,
    mfe: Decimal,
    mae: Decimal,
) -> tuple[Decimal, Decimal]:
    favorable = (bar.high - entry) / risk if side == "long" else (entry - bar.low) / risk
    adverse = (entry - bar.low) / risk if side == "long" else (bar.high - entry) / risk
    return max(mfe, favorable), max(mae, adverse)


def entry_session(
    fill: Fill, context: tuple[object, ...]
) -> tuple[Decimal | None, datetime | None, str | None, Decimal, Decimal]:
    side = fill.side
    stop = fill.stop
    risk = abs(fill.entry - stop)
    mfe = Decimal(0)
    mae = Decimal(0)
    path = context[0]
    m15_index = context[1]
    mode = context[3]
    if not isinstance(path, tuple) or not isinstance(m15_index, int) or not isinstance(mode, str):
        raise ValueError("invalid fill context")
    if fill.resolution.startswith("TICK:"):
        subbars, m1_index, m1_bar, record = context[4:8]
        if (
            not isinstance(subbars, tuple)
            or not isinstance(m1_index, int)
            or not isinstance(m1_bar, Bar)
            or not isinstance(record, dict)
        ):
            raise ValueError("invalid tick context")
        started = fill.fill_at == m1_bar.opened_at
        for row in tick_rows(record):
            observed_at = timestamp(row["timestamp"])
            price = decimal(row["price"])
            if not started:
                if observed_at < fill.fill_at:
                    continue
                started = True
                if observed_at == fill.fill_at and price == fill.entry:
                    continue
            if (side == "long" and price <= stop) or (side == "short" and price >= stop):
                move = directional(side, fill.entry, price)
                mae = max(mae, -move / risk if move < 0 else Decimal(0))
                return price, observed_at, "gap-stop" if price != stop else "stop", mfe, mae
            move = directional(side, fill.entry, price) / risk
            mfe, mae = max(mfe, move), max(mae, -move)
        for bar in subbars[m1_index + 1 :]:
            if not isinstance(bar, Bar):
                raise ValueError("invalid M1 path")
            price, reason = bar_stop(side, stop, bar)
            if price is not None:
                move = directional(side, fill.entry, price)
                mae = max(mae, -move / risk if move < 0 else Decimal(0))
                return price, bar.opened_at, reason, mfe, mae
            mfe, mae = excursions(side, fill.entry, risk, bar, mfe, mae)
        next_m15 = m15_index + 1
    elif fill.resolution == "M1":
        subbars, m1_index, current = context[4:7]
        if not isinstance(subbars, tuple) or not isinstance(m1_index, int):
            raise ValueError("invalid M1 context")
        if not isinstance(current, Bar):
            raise ValueError("invalid M1 fill bar")
        if mode == "open":
            price, reason = bar_stop(side, stop, current)
            if price is not None:
                move = directional(side, fill.entry, price)
                mae = max(mae, -move / risk if move < 0 else Decimal(0))
                return price, current.opened_at, reason, mfe, mae
            mfe, mae = excursions(side, fill.entry, risk, current, mfe, mae)
        for bar in subbars[m1_index + 1 :]:
            if not isinstance(bar, Bar):
                raise ValueError("invalid M1 path")
            price, reason = bar_stop(side, stop, bar)
            if price is not None:
                move = directional(side, fill.entry, price)
                mae = max(mae, -move / risk if move < 0 else Decimal(0))
                return price, bar.opened_at, reason, mfe, mae
            mfe, mae = excursions(side, fill.entry, risk, bar, mfe, mae)
        next_m15 = m15_index + 1
    else:
        current = context[2]
        if not isinstance(current, Bar):
            raise ValueError("invalid M15 fill bar")
        if mode == "open":
            price, reason = bar_stop(side, stop, current)
            if price is not None:
                move = directional(side, fill.entry, price)
                mae = max(mae, -move / risk if move < 0 else Decimal(0))
                return price, current.opened_at, reason, mfe, mae
            mfe, mae = excursions(side, fill.entry, risk, current, mfe, mae)
        next_m15 = m15_index + 1
    for bar in path[next_m15:]:
        if not isinstance(bar, Bar):
            raise ValueError("invalid M15 path")
        price, reason = bar_stop(side, stop, bar)
        if price is not None:
            move = directional(side, fill.entry, price)
            mae = max(mae, -move / risk if move < 0 else Decimal(0))
            return price, bar.opened_at, reason, mfe, mae
        mfe, mae = excursions(side, fill.entry, risk, bar, mfe, mae)
    return None, None, None, mfe, mae


def closed_trade(
    market: str,
    fill: Fill,
    policy: str,
    exit_price: Decimal,
    exit_at: datetime,
    reason: str,
    mfe: Decimal,
    mae: Decimal,
    holding_bars: int,
) -> Trade:
    risk = abs(fill.entry - fill.stop)
    gross = directional(fill.side, fill.entry, exit_price) / risk
    return Trade(
        market,
        fill.side,
        fill.fill_at,
        fill.entry,
        fill.stop,
        exit_price,
        exit_at,
        gross,
        gross - fill.entry * Decimal("0.0001") / risk,
        gross - fill.entry * Decimal("0.0002") / risk,
        "closed",
        reason,
        policy,
        mfe,
        mae,
        holding_bars,
        reason == "gap-stop",
        fill.resolution,
    )


def censored_trade(
    market: str,
    fill: Fill,
    policy: str,
    reason: str,
    mfe: Decimal,
    mae: Decimal,
    holding_bars: int,
) -> Trade:
    return Trade(
        market,
        fill.side,
        fill.fill_at,
        fill.entry,
        fill.stop,
        None,
        None,
        None,
        None,
        None,
        "censored",
        reason,
        policy,
        mfe,
        mae,
        holding_bars,
        False,
        fill.resolution,
    )


def replay(market: Market, result: Evaluation, source_index: int, policy: str) -> Trade:
    if result.fill is None or result.context is None:
        raise ValueError("fill result required")
    fill = result.fill
    trail, horizon = POLICIES[policy]
    price, when, reason, mfe, mae = entry_session(fill, result.context)
    if price is not None and when is not None and reason is not None:
        return closed_trade(market.symbol, fill, policy, price, when, reason, mfe, mae, 0)
    active_stop = fill.stop
    observed: list[Bar] = []
    risk = abs(fill.entry - fill.stop)
    for bar_index in range(1, horizon + 1):
        index = source_index + bar_index
        if index >= len(market.d1):
            return censored_trade(
                market.symbol, fill, policy, "insufficient-data", mfe, mae, bar_index - 1
            )
        bar = market.d1[index]
        if bar.opened_at >= OOS_START or market.m15_session(bar) is None:
            return censored_trade(
                market.symbol,
                fill,
                policy,
                "data-resolution-limitation",
                mfe,
                mae,
                bar_index - 1,
            )
        exit_price, stop_reason = bar_stop(fill.side, active_stop, bar)
        if exit_price is not None and stop_reason is not None:
            move = directional(fill.side, fill.entry, exit_price)
            mae = max(mae, -move / risk if move < 0 else Decimal(0))
            resolved_reason = stop_reason
            if stop_reason == "stop" and active_stop != fill.stop:
                resolved_reason = "trail-stop"
            return closed_trade(
                market.symbol,
                fill,
                policy,
                exit_price,
                bar.opened_at,
                resolved_reason,
                mfe,
                mae,
                bar_index,
            )
        mfe, mae = excursions(fill.side, fill.entry, risk, bar, mfe, mae)
        observed.append(bar)
        if len(observed) >= trail:
            recent = observed[-trail:]
            candidate = (
                min(item.low for item in recent)
                if fill.side == "long"
                else max(item.high for item in recent)
            )
            active_stop = (
                max(active_stop, candidate)
                if fill.side == "long"
                else min(active_stop, candidate)
            )
        if bar_index == horizon:
            return closed_trade(
                market.symbol,
                fill,
                policy,
                bar.close,
                bar.closed_at,
                "time-exit",
                mfe,
                mae,
                bar_index,
            )
    raise AssertionError("unresolved management loop")


def profit_factor(values: list[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    if losses == 0:
        return None if gains == 0 else Decimal("Infinity")
    return gains / losses


def max_drawdown(values: list[Decimal]) -> Decimal:
    equity = peak = drawdown = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def longest_loss(values: list[Decimal]) -> int:
    current = longest = 0
    for value in values:
        current = current + 1 if value < 0 else 0
        longest = max(longest, current)
    return longest


def metrics(trades: list[Trade], field: str = "net_1bp_r") -> dict[str, object]:
    closed = sorted(
        (trade for trade in trades if trade.decision == "closed"),
        key=lambda trade: trade.fill_at,
    )
    values: list[Decimal] = []
    for trade in closed:
        value = getattr(trade, field)
        if not isinstance(value, Decimal):
            raise ValueError("closed trade missing realized R")
        values.append(value)
    return {
        "closed": len(closed),
        "censored": len(trades) - len(closed),
        "total_r": sum(values, Decimal(0)),
        "mean_r": sum(values, Decimal(0)) / len(values) if values else None,
        "median_r": median(values) if values else None,
        "profit_factor": profit_factor(values),
        "win_rate": Decimal(sum(value > 0 for value in values)) / len(values) if values else None,
        "max_drawdown_r": max_drawdown(values),
        "longest_loss_sequence": longest_loss(values),
    }


def fold_name(trade: Trade) -> str | None:
    for name, start, end in FOLDS:
        if start <= trade.fill_at < end:
            return name
    return None


def concentration(trades: list[Trade]) -> dict[str, object]:
    closed = [trade for trade in trades if isinstance(trade.net_1bp_r, Decimal)]
    positive = sum(
        (trade.net_1bp_r for trade in closed if trade.net_1bp_r > 0), Decimal(0)
    )
    if positive <= 0:
        return {"positive_gain_r": positive, "max_share": None, "pass": False}
    axes: dict[str, dict[str, Decimal]] = {}
    functions = {
        "market": lambda trade: trade.market,
        "year": lambda trade: str(trade.fill_at.year),
        "side": lambda trade: trade.side,
    }
    for axis, function in functions.items():
        gains: defaultdict[str, Decimal] = defaultdict(lambda: Decimal(0))
        for trade in closed:
            if trade.net_1bp_r > 0:
                gains[function(trade)] += trade.net_1bp_r
        axes[axis] = {key: value / positive for key, value in gains.items()}
    maximum = max(
        (value for axis in axes.values() for value in axis.values()),
        default=Decimal(0),
    )
    return {
        "positive_gain_r": positive,
        "shares": axes,
        "max_share": maximum,
        "pass": maximum <= Decimal("0.5"),
    }


def loss_class(trade: Trade) -> str | None:
    if not isinstance(trade.net_1bp_r, Decimal) or trade.net_1bp_r >= 0:
        return None
    if trade.gap_stop:
        return "GAP_STOP"
    if trade.exit_reason == "trail-stop":
        return "TRAIL_STOP_FAILURE"
    if trade.exit_reason == "time-exit":
        return "TIME_EXIT_LOSS"
    if trade.exit_reason == "stop":
        return (
            "FAILED_REVERSAL_AFTER_RECOVERY"
            if trade.mfe_lower_bound_r >= Decimal("0.25")
            else "IMMEDIATE_ADVERSE_CONTINUATION"
        )
    return "OTHER"


def policy_report(trades: list[Trade]) -> dict[str, object]:
    forward = [trade for trade in trades if fold_name(trade) is not None]
    primary = metrics(forward)
    stress = metrics(forward, "net_2bp_r")
    gross = metrics(forward, "gross_r")
    folds = {
        name: metrics([trade for trade in trades if fold_name(trade) == name])
        for name, _, _ in FOLDS
    }
    positive_folds = sum(
        isinstance(item["total_r"], Decimal) and item["total_r"] > 0
        for item in folds.values()
    )
    leave_one_out = {
        market: metrics([trade for trade in forward if trade.market != market])["total_r"]
        for market in MARKETS
    }
    concentrated = concentration(forward)
    gate = {
        "forward_closed_trades_gte_30": primary["closed"] >= 30,
        "forward_expectancy_gt_0": isinstance(primary["mean_r"], Decimal) and primary["mean_r"] > 0,
        "forward_profit_factor_gt_1": (
            isinstance(primary["profit_factor"], Decimal) and primary["profit_factor"] > 1
        ),
        "positive_folds_gte_4_of_6": positive_folds >= 4,
        "stress_expectancy_gte_0": isinstance(stress["mean_r"], Decimal) and stress["mean_r"] >= 0,
        "leave_one_market_out_all_positive": all(
            isinstance(value, Decimal) and value > 0 for value in leave_one_out.values()
        ),
        "positive_gain_concentration_lte_50pct": bool(concentrated["pass"]),
        "causal_integrity_fail_closed": True,
    }
    losers = [
        trade
        for trade in trades
        if isinstance(trade.net_1bp_r, Decimal) and trade.net_1bp_r < 0
    ]
    return {
        "all_development": metrics(trades),
        "walk_forward": primary,
        "walk_forward_gross_before_cost": gross,
        "walk_forward_stress_2bp": stress,
        "positive_folds": positive_folds,
        "folds": folds,
        "leave_one_market_out_total_r": leave_one_out,
        "concentration": concentrated,
        "advancement_gate": gate,
        "passes_advancement_gate": all(gate.values()),
        "exit_reasons": Counter(trade.exit_reason for trade in trades),
        "loss_forensics": Counter(
            category for trade in trades if (category := loss_class(trade)) is not None
        ),
        "loser_mfe_lower_bound_counts": {
            threshold: sum(trade.mfe_lower_bound_r >= Decimal(threshold) for trade in losers)
            for threshold in ("0.25", "0.50", "1", "2")
        },
        "market": {
            market: metrics([trade for trade in trades if trade.market == market])
            for market in MARKETS
        },
        "side": {
            side: metrics([trade for trade in trades if trade.side == side])
            for side in ("long", "short")
        },
    }
