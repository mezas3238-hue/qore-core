"""VT-08 R3.11 adaptive prop-firm Monte Carlo on consumed evidence only.

Research-only. This module never opens the reserved 2020-2022 candidate holdout.
It resamples the already-consumed 2022-2026 daily opportunity stream with moving
blocks and evaluates equity-aware portfolio policies against internal and external
prop-firm loss envelopes. Reference sleeve percentages are inputs to a dynamic Risk
authority; the actually authorized percentage is recalculated before every entry.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from qore.infrastructure.deterministic_random import DeterministicRandom
from qore.infrastructure.trader_lab.vt08_b01_risk_economic_replay_r3_11 import (
    TradeObservation,
    load_consumed_evidence,
)

PRIMARY_COST_BPS = Decimal("0.5")
COST_GRID_BPS = (Decimal("0"), Decimal("0.25"), Decimal("0.5"), Decimal("1"))
DEFAULT_PATHS = 10_000
SENSITIVITY_PATHS = 5_000
DEFAULT_HORIZON_DAYS = 250
DEFAULT_BLOCK_DAYS = 20
BLOCK_SENSITIVITY = (5, 20, 60)
HORIZON_SENSITIVITY = (60, 120, 250)
BASE_SEED = 20260912
PROP_TZ = ZoneInfo("Europe/Prague")
INTERNAL_DAILY_LOSS_LIMIT = 0.02
INTERNAL_PEAK_DRAWDOWN_LIMIT = 0.05
EXTERNAL_DAILY_LOSS_LIMIT = 0.05
EXTERNAL_MAX_LOSS_LIMIT = 0.10
TARGETS = (0.05, 0.08, 0.10)
SIMULATION_MONTH_BUSINESS_DAYS = 21
MAX_PROFIT_MULTIPLIER = 1.50
MIN_DRAWDOWN_MULTIPLIER = 0.40
PROFIT_CUSHION_FOR_MAX_MULTIPLIER = 0.10
DRAWDOWN_BRAKE_STRENGTH = 0.60


class PropFirmMonteCarloError(ValueError):
    """Raised when Monte Carlo evidence or configuration is invalid."""


@dataclass(frozen=True, slots=True)
class PortfolioPolicy:
    name: str
    a_risk_bps: int
    gbpjpy_risk_bps: int
    portfolio_heat_bps: int = 90

    def __post_init__(self) -> None:
        if not 0 < self.a_risk_bps <= self.portfolio_heat_bps:
            raise PropFirmMonteCarloError("A risk must fit inside portfolio heat")
        if not 0 < self.gbpjpy_risk_bps <= self.portfolio_heat_bps:
            raise PropFirmMonteCarloError("GBPJPY risk must fit inside portfolio heat")
        if not 0 < self.portfolio_heat_bps <= 10_000:
            raise PropFirmMonteCarloError("portfolio heat must be positive")


POLICIES = (
    PortfolioPolicy("conservative-reference", 25, 20, 90),
    PortfolioPolicy("balanced-research", 30, 25, 90),
    PortfolioPolicy("upper-research", 35, 25, 90),
)


@dataclass(frozen=True, slots=True)
class EffectiveTrade:
    observation: TradeObservation
    sleeve: str
    effective_risk_bps: int
    net_r: float

    @property
    def return_fraction(self) -> float:
        return self.effective_risk_bps / 10_000.0 * self.net_r

    @property
    def adverse_fraction(self) -> float:
        realized_loss = max(0.0, -self.return_fraction)
        bounded_loss = self.effective_risk_bps / 10_000.0
        return max(realized_loss, bounded_loss)


@dataclass(frozen=True, slots=True)
class DayRecord:
    trade_returns: tuple[float, ...]
    worst_case_loss_fraction: float
    calendar_day: date | None = None
    trades: tuple[EffectiveTrade, ...] = ()


@dataclass(frozen=True, slots=True)
class MonthResult:
    key: str
    return_fraction: float
    max_drawdown: float
    worst_daily_loss: float
    trade_count: int
    positive: bool
    a_contribution_fraction: float
    gbpjpy_contribution_fraction: float
    average_authorized_risk_bps: float
    max_authorized_risk_bps: float
    max_portfolio_heat_bps: float
    growth_efficiency: float | None


@dataclass(frozen=True, slots=True)
class PathResult:
    terminal_return: float
    max_drawdown: float
    internal_breach: bool
    external_breach: bool
    max_losing_trade_streak: int
    targets_hit_day: tuple[int | None, ...]
    targets_hit_before_internal_day: tuple[int | None, ...]
    months: tuple[MonthResult, ...]
    average_authorized_risk_bps: float
    max_authorized_risk_bps: float
    max_portfolio_heat_bps: float
    max_daily_loss_fraction: float


@dataclass(slots=True)
class _OpenRisk:
    trade: EffectiveTrade
    risk_amount: float
    authorized_risk_bps: float


@dataclass(slots=True)
class _MonthAccumulator:
    key: str
    start_equity: float
    peak_equity: float
    max_drawdown: float = 0.0
    worst_daily_loss: float = 0.0
    trade_count: int = 0
    a_pnl: float = 0.0
    gbpjpy_pnl: float = 0.0
    risk_bps_sum: float = 0.0
    risk_observations: int = 0
    max_risk_bps: float = 0.0
    max_heat_bps: float = 0.0


def _scope(trade: TradeObservation) -> str | None:
    if trade.side == "short" and trade.symbol in {"AUDJPY", "GBPUSD"}:
        return "a"
    if trade.symbol == "GBPJPY":
        return "gbpjpy"
    return None


def _risk_bps(policy: PortfolioPolicy, sleeve: str) -> int:
    if sleeve == "a":
        return policy.a_risk_bps
    if sleeve == "gbpjpy":
        return policy.gbpjpy_risk_bps
    raise PropFirmMonteCarloError(f"unknown sleeve {sleeve}")


def adaptive_risk_multiplier(
    *,
    equity: float,
    peak_equity: float,
    initial_equity: float = 1.0,
) -> float:
    """Return the continuously recomputed Risk multiplier for the current account state.

    Clean profit cushion raises the requested percentage gradually. Drawdown from the
    achieved equity peak contracts it faster than it expands. This is only the request
    multiplier: daily-loss, peak-DD, external-loss and portfolio-heat headroom can reduce
    the final authorization further.
    """
    if equity <= 0 or peak_equity <= 0 or initial_equity <= 0:
        raise PropFirmMonteCarloError("equity inputs must be positive")
    profit_cushion = max(0.0, equity / initial_equity - 1.0)
    profit_progress = min(1.0, profit_cushion / PROFIT_CUSHION_FOR_MAX_MULTIPLIER)
    growth_multiplier = 1.0 + (MAX_PROFIT_MULTIPLIER - 1.0) * profit_progress
    drawdown = max(0.0, (peak_equity - equity) / peak_equity)
    brake_progress = min(1.0, drawdown / INTERNAL_PEAK_DRAWDOWN_LIMIT)
    drawdown_multiplier = max(
        MIN_DRAWDOWN_MULTIPLIER,
        1.0 - DRAWDOWN_BRAKE_STRENGTH * brake_progress,
    )
    return max(
        MIN_DRAWDOWN_MULTIPLIER,
        min(MAX_PROFIT_MULTIPLIER, growth_multiplier * drawdown_multiplier),
    )


def _build_price_index(
    bars: Mapping[datetime, Decimal],
) -> tuple[list[datetime], list[Decimal]]:
    ordered = sorted(bars.items(), key=lambda item: item[0])
    return [item[0] for item in ordered], [item[1] for item in ordered]


def _price_at_or_before(
    index: tuple[list[datetime], list[Decimal]], at: datetime
) -> Decimal:
    times, prices = index
    pos = bisect_right(times, at) - 1
    if pos < 0:
        raise PropFirmMonteCarloError("missing conversion evidence")
    return prices[pos]


def _quote_to_usd(
    trade: TradeObservation,
    *,
    at_entry: bool,
    indices: Mapping[str, tuple[list[datetime], list[Decimal]]],
) -> Decimal:
    symbol = trade.symbol
    base = symbol[:3]
    quote = symbol[3:]
    instrument_price = trade.entry if at_entry else trade.exit_price
    at = trade.signal_at if at_entry else trade.exited_at
    if quote == "USD":
        return Decimal(1)
    if base == "USD":
        if instrument_price <= 0:
            raise PropFirmMonteCarloError("non-positive instrument price")
        return Decimal(1) / instrument_price
    if quote == "JPY":
        index = indices.get("USDJPY")
        if index is None:
            raise PropFirmMonteCarloError("USDJPY conversion evidence missing")
        px = _price_at_or_before(index, at)
        if px <= 0:
            raise PropFirmMonteCarloError("non-positive USDJPY conversion price")
        return Decimal(1) / px
    raise PropFirmMonteCarloError(f"unsupported quote conversion for {symbol}")


def _net_r(
    trade: TradeObservation,
    *,
    cost_bps: Decimal,
    indices: Mapping[str, tuple[list[datetime], list[Decimal]]],
) -> float:
    risk_price = trade.risk_price
    if risk_price <= 0:
        raise PropFirmMonteCarloError("trade risk must be positive")
    delta = trade.exit_price - trade.entry
    if trade.side == "short":
        delta = -delta
    elif trade.side != "long":
        raise PropFirmMonteCarloError(f"unsupported side {trade.side}")
    factor_entry = _quote_to_usd(trade, at_entry=True, indices=indices)
    factor_exit = _quote_to_usd(trade, at_entry=False, indices=indices)
    gross_r = delta * factor_exit / (risk_price * factor_entry)
    cost_r = trade.entry * cost_bps / Decimal(10_000) / risk_price
    return float(gross_r - cost_r)


def build_effective_trades(
    trades: Sequence[TradeObservation],
    conversion_bars: Mapping[str, Mapping[datetime, Decimal]],
    *,
    policy: PortfolioPolicy,
    cost_bps: Decimal,
    portfolio: str = "b",
) -> tuple[EffectiveTrade, ...]:
    if portfolio not in {"a", "gbpjpy", "b"}:
        raise PropFirmMonteCarloError(f"unknown portfolio {portfolio}")
    indices = {symbol: _build_price_index(bars) for symbol, bars in conversion_bars.items()}
    selected: list[tuple[TradeObservation, str]] = []
    for trade in sorted(trades, key=lambda item: (item.signal_at, item.symbol, item.side)):
        sleeve = _scope(trade)
        if sleeve is None:
            continue
        if portfolio != "b" and sleeve != portfolio:
            continue
        selected.append((trade, sleeve))

    effective: list[EffectiveTrade] = []
    for trade, sleeve in selected:
        effective.append(
            EffectiveTrade(
                observation=trade,
                sleeve=sleeve,
                effective_risk_bps=_risk_bps(policy, sleeve),
                net_r=_net_r(trade, cost_bps=cost_bps, indices=indices),
            )
        )
    return tuple(effective)


def _business_days(start: date, end: date) -> list[date]:
    if end < start:
        raise PropFirmMonteCarloError("invalid date range")
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def build_daily_series(trades: Sequence[EffectiveTrade]) -> tuple[DayRecord, ...]:
    if not trades:
        raise PropFirmMonteCarloError("daily series requires trades")
    by_day: dict[date, list[EffectiveTrade]] = defaultdict(list)
    for trade in trades:
        local_day = trade.observation.signal_at.astimezone(PROP_TZ).date()
        by_day[local_day].append(trade)
    start = min(by_day)
    end = max(by_day)
    records: list[DayRecord] = []
    for day in _business_days(start, end):
        items = sorted(
            by_day.get(day, []),
            key=lambda item: (item.observation.signal_at, item.observation.symbol),
        )
        returns = tuple(item.return_fraction for item in items)
        adverse = sum(item.adverse_fraction for item in items)
        records.append(DayRecord(returns, adverse, day, tuple(items)))
    return tuple(records)


def moving_block_sample(
    records: Sequence[DayRecord],
    *,
    horizon_days: int,
    block_days: int,
    rng: DeterministicRandom,
) -> tuple[DayRecord, ...]:
    if horizon_days <= 0 or block_days <= 0:
        raise PropFirmMonteCarloError("horizon and block must be positive")
    if block_days > len(records):
        raise PropFirmMonteCarloError("block cannot exceed observed series")
    sampled: list[DayRecord] = []
    last_start = len(records) - block_days
    while len(sampled) < horizon_days:
        start = rng.randint(0, last_start)
        sampled.extend(records[start : start + block_days])
    return tuple(sampled[:horizon_days])


def _month_key(record: DayRecord, day_index: int, *, calendar_months: bool) -> str:
    if calendar_months:
        if record.calendar_day is None:
            raise PropFirmMonteCarloError("calendar monthly reporting requires calendar dates")
        return record.calendar_day.strftime("%Y-%m")
    month_index = (day_index - 1) // SIMULATION_MONTH_BUSINESS_DAYS + 1
    return f"M{month_index:02d}"


def _finish_month(acc: _MonthAccumulator, end_equity: float) -> MonthResult:
    return_fraction = end_equity / acc.start_equity - 1.0
    efficiency = None if acc.max_drawdown <= 0 else return_fraction / acc.max_drawdown
    average_risk = (
        0.0 if acc.risk_observations == 0 else acc.risk_bps_sum / acc.risk_observations
    )
    return MonthResult(
        key=acc.key,
        return_fraction=return_fraction,
        max_drawdown=acc.max_drawdown,
        worst_daily_loss=acc.worst_daily_loss,
        trade_count=acc.trade_count,
        positive=return_fraction > 0,
        a_contribution_fraction=acc.a_pnl / acc.start_equity,
        gbpjpy_contribution_fraction=acc.gbpjpy_pnl / acc.start_equity,
        average_authorized_risk_bps=average_risk,
        max_authorized_risk_bps=acc.max_risk_bps,
        max_portfolio_heat_bps=acc.max_heat_bps,
        growth_efficiency=efficiency,
    )


def _headroom_amount(
    *,
    equity: float,
    peak_equity: float,
    day_start_equity: float,
    active_risk_amount: float,
) -> float:
    realized_daily_loss = max(0.0, day_start_equity - equity)
    internal_daily = max(
        0.0,
        day_start_equity * INTERNAL_DAILY_LOSS_LIMIT
        - realized_daily_loss
        - active_risk_amount,
    )
    external_daily = max(
        0.0,
        day_start_equity * EXTERNAL_DAILY_LOSS_LIMIT
        - realized_daily_loss
        - active_risk_amount,
    )
    internal_floor = peak_equity * (1.0 - INTERNAL_PEAK_DRAWDOWN_LIMIT)
    internal_dd = max(0.0, equity - internal_floor - active_risk_amount)
    external_floor = 1.0 - EXTERNAL_MAX_LOSS_LIMIT
    external_max = max(0.0, equity - external_floor - active_risk_amount)
    return min(internal_daily, external_daily, internal_dd, external_max)


def _realize_positions_until(
    open_positions: list[_OpenRisk],
    *,
    cutoff: datetime | None,
    equity: float,
    peak: float,
    losing_streak: int,
    max_losing_streak: int,
    month: _MonthAccumulator,
    day_worst_equity: float,
) -> tuple[float, float, int, int, float]:
    ready = [
        item
        for item in open_positions
        if cutoff is None or item.trade.observation.exited_at <= cutoff
    ]
    ready.sort(key=lambda item: item.trade.observation.exited_at)
    for position in ready:
        open_positions.remove(position)
        pnl = position.risk_amount * position.trade.net_r
        equity += pnl
        if pnl < 0:
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        elif pnl > 0:
            losing_streak = 0
        if position.trade.sleeve == "a":
            month.a_pnl += pnl
        elif position.trade.sleeve == "gbpjpy":
            month.gbpjpy_pnl += pnl
        day_worst_equity = min(day_worst_equity, equity)
        peak = max(peak, equity)
        month.peak_equity = max(month.peak_equity, equity)
    return equity, peak, losing_streak, max_losing_streak, day_worst_equity


def _max_consecutive_negative_months(months: Sequence[MonthResult]) -> int:
    longest = 0
    current = 0
    for month in months:
        if month.return_fraction < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def simulate_path(
    records: Sequence[DayRecord],
    *,
    policy: PortfolioPolicy | None = None,
    calendar_months: bool = False,
) -> PathResult:
    if not records:
        raise PropFirmMonteCarloError("path requires records")
    active_policy = policy or POLICIES[0]
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    internal_breach = False
    external_breach = False
    losing_streak = 0
    max_losing_streak = 0
    target_days: list[int | None] = [None] * len(TARGETS)
    target_before_internal: list[int | None] = [None] * len(TARGETS)
    months: list[MonthResult] = []
    all_risk_bps: list[float] = []
    max_portfolio_heat_bps = 0.0
    max_daily_loss_fraction = 0.0
    month_key = _month_key(records[0], 1, calendar_months=calendar_months)
    month = _MonthAccumulator(month_key, equity, equity)

    for day_index, record in enumerate(records, start=1):
        current_month_key = _month_key(record, day_index, calendar_months=calendar_months)
        if current_month_key != month.key:
            months.append(_finish_month(month, equity))
            month = _MonthAccumulator(current_month_key, equity, equity)

        day_start_equity = equity
        day_worst_equity = equity
        if record.trades:
            pending = sorted(
                record.trades,
                key=lambda item: (item.observation.signal_at, item.observation.symbol),
            )
            open_positions: list[_OpenRisk] = []
            for trade in pending:
                (
                    equity,
                    peak,
                    losing_streak,
                    max_losing_streak,
                    day_worst_equity,
                ) = _realize_positions_until(
                    open_positions,
                    cutoff=trade.observation.signal_at,
                    equity=equity,
                    peak=peak,
                    losing_streak=losing_streak,
                    max_losing_streak=max_losing_streak,
                    month=month,
                    day_worst_equity=day_worst_equity,
                )
                active_risk_amount = sum(item.risk_amount for item in open_positions)
                multiplier = adaptive_risk_multiplier(equity=equity, peak_equity=peak)
                requested_bps = trade.effective_risk_bps * multiplier
                requested_amount = equity * requested_bps / 10_000.0
                heat_headroom = max(
                    0.0,
                    equity * active_policy.portfolio_heat_bps / 10_000.0
                    - active_risk_amount,
                )
                loss_headroom = _headroom_amount(
                    equity=equity,
                    peak_equity=peak,
                    day_start_equity=day_start_equity,
                    active_risk_amount=active_risk_amount,
                )
                risk_amount = min(requested_amount, heat_headroom, loss_headroom)
                if risk_amount <= 0:
                    continue
                authorized_bps = risk_amount / equity * 10_000.0
                open_positions.append(_OpenRisk(trade, risk_amount, authorized_bps))
                active_risk_amount = sum(item.risk_amount for item in open_positions)
                adverse_equity = equity - active_risk_amount
                day_worst_equity = min(day_worst_equity, adverse_equity)
                adverse_drawdown = max(0.0, (peak - adverse_equity) / peak)
                month_adverse_drawdown = max(
                    0.0, (month.peak_equity - adverse_equity) / month.peak_equity
                )
                max_drawdown = max(max_drawdown, adverse_drawdown)
                month.max_drawdown = max(month.max_drawdown, month_adverse_drawdown)
                heat_bps = active_risk_amount / equity * 10_000.0
                max_portfolio_heat_bps = max(max_portfolio_heat_bps, heat_bps)
                month.max_heat_bps = max(month.max_heat_bps, heat_bps)
                all_risk_bps.append(authorized_bps)
                month.risk_bps_sum += authorized_bps
                month.risk_observations += 1
                month.max_risk_bps = max(month.max_risk_bps, authorized_bps)
                month.trade_count += 1
            (
                equity,
                peak,
                losing_streak,
                max_losing_streak,
                day_worst_equity,
            ) = _realize_positions_until(
                open_positions,
                cutoff=None,
                equity=equity,
                peak=peak,
                losing_streak=losing_streak,
                max_losing_streak=max_losing_streak,
                month=month,
                day_worst_equity=day_worst_equity,
            )
        else:
            for trade_return in record.trade_returns:
                equity *= 1.0 + trade_return
                if trade_return < 0:
                    losing_streak += 1
                    max_losing_streak = max(max_losing_streak, losing_streak)
                elif trade_return > 0:
                    losing_streak = 0
            day_worst_equity = min(
                day_worst_equity,
                day_start_equity * (1.0 - record.worst_case_loss_fraction),
            )

        day_worst_equity = min(day_worst_equity, equity)
        peak = max(peak, equity)
        month.peak_equity = max(month.peak_equity, equity)
        realized_drawdown = max(0.0, (peak - equity) / peak)
        adverse_drawdown = max(0.0, (peak - day_worst_equity) / peak)
        month_realized_drawdown = max(
            0.0, (month.peak_equity - equity) / month.peak_equity
        )
        month_adverse_drawdown = max(
            0.0, (month.peak_equity - day_worst_equity) / month.peak_equity
        )
        max_drawdown = max(max_drawdown, realized_drawdown, adverse_drawdown)
        month.max_drawdown = max(
            month.max_drawdown, month_realized_drawdown, month_adverse_drawdown
        )
        day_loss_fraction = max(0.0, (day_start_equity - day_worst_equity) / day_start_equity)
        max_daily_loss_fraction = max(max_daily_loss_fraction, day_loss_fraction)
        month.worst_daily_loss = max(month.worst_daily_loss, day_loss_fraction)

        if day_loss_fraction >= INTERNAL_DAILY_LOSS_LIMIT:
            internal_breach = True
        if max_drawdown >= INTERNAL_PEAK_DRAWDOWN_LIMIT:
            internal_breach = True
        if day_loss_fraction >= EXTERNAL_DAILY_LOSS_LIMIT:
            external_breach = True
        if day_worst_equity <= 1.0 - EXTERNAL_MAX_LOSS_LIMIT:
            external_breach = True
        if equity <= 1.0 - EXTERNAL_MAX_LOSS_LIMIT:
            external_breach = True

        for index, target in enumerate(TARGETS):
            if target_days[index] is None and equity >= 1.0 + target:
                target_days[index] = day_index
                if not internal_breach:
                    target_before_internal[index] = day_index
        if external_breach:
            break

    months.append(_finish_month(month, equity))
    average_risk = 0.0 if not all_risk_bps else sum(all_risk_bps) / len(all_risk_bps)
    max_risk = 0.0 if not all_risk_bps else max(all_risk_bps)
    return PathResult(
        terminal_return=equity - 1.0,
        max_drawdown=max_drawdown,
        internal_breach=internal_breach,
        external_breach=external_breach,
        max_losing_trade_streak=max_losing_streak,
        targets_hit_day=tuple(target_days),
        targets_hit_before_internal_day=tuple(target_before_internal),
        months=tuple(months),
        average_authorized_risk_bps=average_risk,
        max_authorized_risk_bps=max_risk,
        max_portfolio_heat_bps=max_portfolio_heat_bps,
        max_daily_loss_fraction=max_daily_loss_fraction,
    )


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        raise PropFirmMonteCarloError("percentile requires observations")
    if not 0 <= q <= 1:
        raise PropFirmMonteCarloError("percentile q must be in [0,1]")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _distribution(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {"p05": 0.0, "median": 0.0, "p95": 0.0}
    return {
        "p05": _percentile(values, 0.05),
        "median": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
    }


def _rolling_month_returns(months: Sequence[MonthResult], width: int) -> list[float]:
    if width <= 0:
        raise PropFirmMonteCarloError("rolling width must be positive")
    values: list[float] = []
    for start in range(0, len(months) - width + 1):
        compounded = 1.0
        for month in months[start : start + width]:
            compounded *= 1.0 + month.return_fraction
        values.append(compounded - 1.0)
    return values


def _summarize_months(results: Sequence[PathResult]) -> dict[str, object]:
    months = [month for result in results for month in result.months]
    returns = [month.return_fraction for month in months]
    drawdowns = [month.max_drawdown for month in months]
    efficiencies: list[float] = []
    for month in months:
        if month.growth_efficiency is not None:
            efficiencies.append(month.growth_efficiency)
    a_contributions = [month.a_contribution_fraction for month in months]
    gbpjpy_contributions = [month.gbpjpy_contribution_fraction for month in months]
    negative_streaks = [
        float(_max_consecutive_negative_months(result.months)) for result in results
    ]
    rolling_3 = [value for result in results for value in _rolling_month_returns(result.months, 3)]
    rolling_6 = [value for result in results for value in _rolling_month_returns(result.months, 6)]
    return {
        "definition": "21-business-day simulation month; return uses each month opening equity",
        "return": _distribution(returns),
        "positive_month_probability": (
            0.0 if not months else sum(item.positive for item in months) / len(months)
        ),
        "negative_month_probability": (
            0.0
            if not months
            else sum(item.return_fraction < 0 for item in months) / len(months)
        ),
        "max_drawdown": _distribution(drawdowns),
        "growth_efficiency_return_over_drawdown": _distribution(efficiencies),
        "max_consecutive_negative_months": _distribution(negative_streaks),
        "rolling_3_month_return": _distribution(rolling_3),
        "rolling_6_month_return": _distribution(rolling_6),
        "sleeve_monthly_contribution": {
            "a": _distribution(a_contributions),
            "gbpjpy": _distribution(gbpjpy_contributions),
        },
    }


def run_monte_carlo(
    records: Sequence[DayRecord],
    *,
    paths: int,
    horizon_days: int,
    block_days: int,
    seed: int,
    policy: PortfolioPolicy | None = None,
) -> dict[str, object]:
    if paths <= 0:
        raise PropFirmMonteCarloError("paths must be positive")
    active_policy = policy or POLICIES[0]
    rng = DeterministicRandom(seed)
    results = [
        simulate_path(
            moving_block_sample(
                records,
                horizon_days=horizon_days,
                block_days=block_days,
                rng=rng,
            ),
            policy=active_policy,
        )
        for _ in range(paths)
    ]
    terminals = [item.terminal_return for item in results]
    drawdowns = [item.max_drawdown for item in results]
    streaks = [float(item.max_losing_trade_streak) for item in results]
    average_risks = [item.average_authorized_risk_bps for item in results]
    max_risks = [item.max_authorized_risk_bps for item in results]
    max_heats = [item.max_portfolio_heat_bps for item in results]
    max_daily_losses = [item.max_daily_loss_fraction for item in results]
    target_summary: dict[str, object] = {}
    for index, target in enumerate(TARGETS):
        hit_days: list[int] = []
        safe_hit_days: list[int] = []
        for item in results:
            hit_day = item.targets_hit_day[index]
            if hit_day is not None:
                hit_days.append(hit_day)
            safe_hit_day = item.targets_hit_before_internal_day[index]
            if safe_hit_day is not None:
                safe_hit_days.append(safe_hit_day)
        target_summary[f"{int(target * 100)}pct"] = {
            "hit_before_external_breach_probability": len(hit_days) / paths,
            "hit_before_internal_breach_probability": len(safe_hit_days) / paths,
            "median_days_to_hit_when_hit": median(hit_days) if hit_days else None,
        }
    return {
        "paths": paths,
        "horizon_business_days": horizon_days,
        "block_business_days": block_days,
        "seed": seed,
        "external_breach_probability": sum(item.external_breach for item in results) / paths,
        "internal_breach_probability": sum(item.internal_breach for item in results) / paths,
        "terminal_return": {
            "p05": _percentile(terminals, 0.05),
            "median": _percentile(terminals, 0.50),
            "p95": _percentile(terminals, 0.95),
            "probability_positive": sum(value > 0 for value in terminals) / paths,
        },
        "max_drawdown": {
            "median": _percentile(drawdowns, 0.50),
            "p95": _percentile(drawdowns, 0.95),
            "p99": _percentile(drawdowns, 0.99),
        },
        "max_losing_trade_streak": {
            "median": _percentile(streaks, 0.50),
            "p95": _percentile(streaks, 0.95),
            "p99": _percentile(streaks, 0.99),
        },
        "risk_dynamics": {
            "authorization": "recomputed before every entry from current equity and headroom",
            "average_authorized_risk_bps": _distribution(average_risks),
            "max_authorized_risk_bps": _distribution(max_risks),
            "max_portfolio_heat_bps": _distribution(max_heats),
            "max_daily_loss_fraction": _distribution(max_daily_losses),
        },
        "monthly_performance": _summarize_months(results),
        "targets": target_summary,
    }


def _month_to_dict(month: MonthResult) -> dict[str, object]:
    return {
        "return_fraction": month.return_fraction,
        "max_drawdown": month.max_drawdown,
        "worst_daily_loss": month.worst_daily_loss,
        "trade_count": month.trade_count,
        "positive": month.positive,
        "a_contribution_fraction": month.a_contribution_fraction,
        "gbpjpy_contribution_fraction": month.gbpjpy_contribution_fraction,
        "average_authorized_risk_bps": month.average_authorized_risk_bps,
        "max_authorized_risk_bps": month.max_authorized_risk_bps,
        "max_portfolio_heat_bps": month.max_portfolio_heat_bps,
        "growth_efficiency_return_over_drawdown": month.growth_efficiency,
    }


def _observed_metrics(
    records: Sequence[DayRecord],
    *,
    policy: PortfolioPolicy,
) -> dict[str, object]:
    result = simulate_path(records, policy=policy, calendar_months=True)
    return {
        "business_days": len(records),
        "terminal_return": result.terminal_return,
        "max_drawdown": result.max_drawdown,
        "internal_breach": result.internal_breach,
        "external_breach": result.external_breach,
        "max_losing_trade_streak": result.max_losing_trade_streak,
        "worst_case_daily_loss": result.max_daily_loss_fraction,
        "trade_count": sum(month.trade_count for month in result.months),
        "average_authorized_risk_bps": result.average_authorized_risk_bps,
        "max_authorized_risk_bps": result.max_authorized_risk_bps,
        "max_portfolio_heat_bps": result.max_portfolio_heat_bps,
        "monthly": {month.key: _month_to_dict(month) for month in result.months},
        "rolling_3_month_return": _distribution(_rolling_month_returns(result.months, 3)),
        "rolling_6_month_return": _distribution(_rolling_month_returns(result.months, 6)),
    }


def build_report(baseline_root: Path, fresh_root: Path) -> dict[str, object]:
    trades, _constraints, bars = load_consumed_evidence(baseline_root, fresh_root)
    policy_results: dict[str, object] = {}
    for policy_index, policy in enumerate(POLICIES):
        effective = build_effective_trades(
            trades,
            bars,
            policy=policy,
            cost_bps=PRIMARY_COST_BPS,
            portfolio="b",
        )
        daily = build_daily_series(effective)
        policy_results[policy.name] = {
            "policy": {
                "a_reference_risk_bps": policy.a_risk_bps,
                "gbpjpy_reference_risk_bps": policy.gbpjpy_risk_bps,
                "portfolio_heat_bps": policy.portfolio_heat_bps,
                "authorization_is_dynamic": True,
            },
            "primary_cost_bps": format(PRIMARY_COST_BPS, "f"),
            "observed": _observed_metrics(daily, policy=policy),
            "monte_carlo": run_monte_carlo(
                daily,
                paths=DEFAULT_PATHS,
                horizon_days=DEFAULT_HORIZON_DAYS,
                block_days=DEFAULT_BLOCK_DAYS,
                seed=BASE_SEED + policy_index * 1000,
                policy=policy,
            ),
        }

    reference = POLICIES[0]
    sleeves: dict[str, object] = {}
    for portfolio_index, portfolio in enumerate(("a", "gbpjpy", "b")):
        effective = build_effective_trades(
            trades,
            bars,
            policy=reference,
            cost_bps=PRIMARY_COST_BPS,
            portfolio=portfolio,
        )
        daily = build_daily_series(effective)
        sleeves[portfolio] = {
            "observed": _observed_metrics(daily, policy=reference),
            "monte_carlo": run_monte_carlo(
                daily,
                paths=SENSITIVITY_PATHS,
                horizon_days=DEFAULT_HORIZON_DAYS,
                block_days=DEFAULT_BLOCK_DAYS,
                seed=BASE_SEED + 10_000 + portfolio_index * 1000,
                policy=reference,
            ),
        }

    cost_sensitivity: dict[str, object] = {}
    for cost_index, cost in enumerate(COST_GRID_BPS):
        effective = build_effective_trades(
            trades,
            bars,
            policy=reference,
            cost_bps=cost,
            portfolio="b",
        )
        daily = build_daily_series(effective)
        cost_sensitivity[format(cost, "f")] = run_monte_carlo(
            daily,
            paths=SENSITIVITY_PATHS,
            horizon_days=DEFAULT_HORIZON_DAYS,
            block_days=DEFAULT_BLOCK_DAYS,
            seed=BASE_SEED + 20_000 + cost_index * 1000,
            policy=reference,
        )

    block_sensitivity: dict[str, object] = {}
    reference_effective = build_effective_trades(
        trades,
        bars,
        policy=reference,
        cost_bps=PRIMARY_COST_BPS,
        portfolio="b",
    )
    reference_daily = build_daily_series(reference_effective)
    for block_index, block_days in enumerate(BLOCK_SENSITIVITY):
        block_sensitivity[str(block_days)] = run_monte_carlo(
            reference_daily,
            paths=SENSITIVITY_PATHS,
            horizon_days=DEFAULT_HORIZON_DAYS,
            block_days=block_days,
            seed=BASE_SEED + 30_000 + block_index * 1000,
            policy=reference,
        )

    horizon_sensitivity: dict[str, object] = {}
    for horizon_index, horizon_days in enumerate(HORIZON_SENSITIVITY):
        horizon_sensitivity[str(horizon_days)] = run_monte_carlo(
            reference_daily,
            paths=SENSITIVITY_PATHS,
            horizon_days=horizon_days,
            block_days=DEFAULT_BLOCK_DAYS,
            seed=BASE_SEED + 40_000 + horizon_index * 1000,
            policy=reference,
        )

    return {
        "schema": "qore.vt08.r3.11.adaptive-prop-firm-monte-carlo.v2",
        "research_only": True,
        "demo_eligible": False,
        "protected_holdout_2020_2022_accessed": False,
        "primary_cost_bps_proxy": format(PRIMARY_COST_BPS, "f"),
        "adaptive_risk": {
            "recomputed_before_every_trade": True,
            "equity_not_static_balance_is_sizing_base": True,
            "profit_cushion_for_max_multiplier": PROFIT_CUSHION_FOR_MAX_MULTIPLIER,
            "max_profit_multiplier": MAX_PROFIT_MULTIPLIER,
            "minimum_drawdown_multiplier": MIN_DRAWDOWN_MULTIPLIER,
            "drawdown_brake_strength": DRAWDOWN_BRAKE_STRENGTH,
            "principle": "scale capital exposure with account growth; de-risk faster on drawdown",
        },
        "risk_envelope": {
            "internal_daily_loss_limit": INTERNAL_DAILY_LOSS_LIMIT,
            "internal_peak_drawdown_limit": INTERNAL_PEAK_DRAWDOWN_LIMIT,
            "external_daily_loss_limit": EXTERNAL_DAILY_LOSS_LIMIT,
            "external_max_loss_limit": EXTERNAL_MAX_LOSS_LIMIT,
        },
        "monthly_reporting": {
            "observed": (
                "calendar months on consumed evidence; each month rebases to opening equity"
            ),
            "monte_carlo": "21-business-day months; each month rebases to simulated opening equity",
            "includes": [
                "return",
                "max_drawdown",
                "worst_daily_loss",
                "growth_efficiency",
                "positive_negative_month_probability",
                "consecutive_negative_months",
                "rolling_3_month_return",
                "rolling_6_month_return",
                "A_contribution",
                "GBPJPY_contribution",
                "average_and_max_authorized_risk",
                "max_portfolio_heat",
            ],
        },
        "targets": list(TARGETS),
        "policies": policy_results,
        "reference_sleeves": sleeves,
        "reference_cost_sensitivity": cost_sensitivity,
        "reference_block_sensitivity": block_sensitivity,
        "reference_horizon_sensitivity": horizon_sensitivity,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--fresh-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(args.baseline_root, args.fresh_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
