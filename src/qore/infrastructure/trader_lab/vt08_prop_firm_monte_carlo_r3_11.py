"""VT-08 R3.11 prop-firm Monte Carlo on consumed evidence only.

Research-only. This module never opens the reserved 2020-2022 candidate holdout.
It resamples the already-consumed 2022-2026 daily opportunity stream with moving
blocks and evaluates fixed-risk portfolio policies against internal and external
prop-firm loss envelopes.
"""

from __future__ import annotations

import argparse
import json
import random
from bisect import bisect_right
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

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


@dataclass(frozen=True, slots=True)
class PathResult:
    terminal_return: float
    max_drawdown: float
    internal_breach: bool
    external_breach: bool
    max_losing_trade_streak: int
    targets_hit_day: tuple[int | None, ...]
    targets_hit_before_internal_day: tuple[int | None, ...]


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

    open_risk: list[tuple[datetime, int]] = []
    effective: list[EffectiveTrade] = []
    for trade, sleeve in selected:
        open_risk = [item for item in open_risk if item[0] > trade.signal_at]
        committed = sum(item[1] for item in open_risk)
        desired = _risk_bps(policy, sleeve)
        available = policy.portfolio_heat_bps - committed
        allocated = min(desired, max(0, available))
        if allocated <= 0:
            continue
        effective.append(
            EffectiveTrade(
                observation=trade,
                sleeve=sleeve,
                effective_risk_bps=allocated,
                net_r=_net_r(trade, cost_bps=cost_bps, indices=indices),
            )
        )
        open_risk.append((trade.exited_at, allocated))
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
        records.append(DayRecord(returns, adverse))
    return tuple(records)


def moving_block_sample(
    records: Sequence[DayRecord],
    *,
    horizon_days: int,
    block_days: int,
    rng: random.Random,
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


def simulate_path(records: Sequence[DayRecord]) -> PathResult:
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    internal_breach = False
    external_breach = False
    losing_streak = 0
    max_losing_streak = 0
    target_days: list[int | None] = [None] * len(TARGETS)
    target_before_internal: list[int | None] = [None] * len(TARGETS)

    for day_index, record in enumerate(records, start=1):
        start_equity = equity
        adverse_equity = start_equity * (1.0 - record.worst_case_loss_fraction)
        adverse_drawdown = 0.0 if peak <= 0 else (peak - adverse_equity) / peak
        max_drawdown = max(max_drawdown, adverse_drawdown)
        if record.worst_case_loss_fraction >= INTERNAL_DAILY_LOSS_LIMIT:
            internal_breach = True
        if adverse_drawdown >= INTERNAL_PEAK_DRAWDOWN_LIMIT:
            internal_breach = True
        if record.worst_case_loss_fraction >= EXTERNAL_DAILY_LOSS_LIMIT:
            external_breach = True
        if adverse_equity <= 1.0 - EXTERNAL_MAX_LOSS_LIMIT:
            external_breach = True
        if external_breach:
            equity = adverse_equity
            break

        for trade_return in record.trade_returns:
            equity *= 1.0 + trade_return
            if trade_return < 0:
                losing_streak += 1
                max_losing_streak = max(max_losing_streak, losing_streak)
            elif trade_return > 0:
                losing_streak = 0
        peak = max(peak, equity)
        end_drawdown = 0.0 if peak <= 0 else (peak - equity) / peak
        max_drawdown = max(max_drawdown, end_drawdown)
        if end_drawdown >= INTERNAL_PEAK_DRAWDOWN_LIMIT:
            internal_breach = True
        if equity <= 1.0 - EXTERNAL_MAX_LOSS_LIMIT:
            external_breach = True
            break
        for index, target in enumerate(TARGETS):
            if target_days[index] is None and equity >= 1.0 + target:
                target_days[index] = day_index
                if not internal_breach:
                    target_before_internal[index] = day_index

    return PathResult(
        terminal_return=equity - 1.0,
        max_drawdown=max_drawdown,
        internal_breach=internal_breach,
        external_breach=external_breach,
        max_losing_trade_streak=max_losing_streak,
        targets_hit_day=tuple(target_days),
        targets_hit_before_internal_day=tuple(target_before_internal),
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


def run_monte_carlo(
    records: Sequence[DayRecord],
    *,
    paths: int,
    horizon_days: int,
    block_days: int,
    seed: int,
) -> dict[str, object]:
    if paths <= 0:
        raise PropFirmMonteCarloError("paths must be positive")
    rng = random.Random(seed)
    results = [
        simulate_path(
            moving_block_sample(
                records,
                horizon_days=horizon_days,
                block_days=block_days,
                rng=rng,
            )
        )
        for _ in range(paths)
    ]
    terminals = [item.terminal_return for item in results]
    drawdowns = [item.max_drawdown for item in results]
    streaks = [float(item.max_losing_trade_streak) for item in results]
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
        "targets": target_summary,
    }


def _observed_metrics(records: Sequence[DayRecord]) -> dict[str, object]:
    result = simulate_path(records)
    return {
        "business_days": len(records),
        "terminal_return": result.terminal_return,
        "max_drawdown": result.max_drawdown,
        "internal_breach": result.internal_breach,
        "external_breach": result.external_breach,
        "max_losing_trade_streak": result.max_losing_trade_streak,
        "worst_case_daily_loss": max(record.worst_case_loss_fraction for record in records),
        "trade_count": sum(len(record.trade_returns) for record in records),
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
                "a_risk_bps": policy.a_risk_bps,
                "gbpjpy_risk_bps": policy.gbpjpy_risk_bps,
                "portfolio_heat_bps": policy.portfolio_heat_bps,
            },
            "primary_cost_bps": format(PRIMARY_COST_BPS, "f"),
            "observed": _observed_metrics(daily),
            "monte_carlo": run_monte_carlo(
                daily,
                paths=DEFAULT_PATHS,
                horizon_days=DEFAULT_HORIZON_DAYS,
                block_days=DEFAULT_BLOCK_DAYS,
                seed=BASE_SEED + policy_index * 1000,
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
            "observed": _observed_metrics(daily),
            "monte_carlo": run_monte_carlo(
                daily,
                paths=SENSITIVITY_PATHS,
                horizon_days=DEFAULT_HORIZON_DAYS,
                block_days=DEFAULT_BLOCK_DAYS,
                seed=BASE_SEED + 10_000 + portfolio_index * 1000,
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
        )

    horizon_sensitivity: dict[str, object] = {}
    for horizon_index, horizon_days in enumerate(HORIZON_SENSITIVITY):
        horizon_sensitivity[str(horizon_days)] = run_monte_carlo(
            reference_daily,
            paths=SENSITIVITY_PATHS,
            horizon_days=horizon_days,
            block_days=DEFAULT_BLOCK_DAYS,
            seed=BASE_SEED + 40_000 + horizon_index * 1000,
        )

    return {
        "schema": "qore.vt08.r3.11.prop-firm-monte-carlo.v1",
        "research_only": True,
        "demo_eligible": False,
        "protected_holdout_2020_2022_accessed": False,
        "primary_cost_bps_proxy": format(PRIMARY_COST_BPS, "f"),
        "risk_envelope": {
            "internal_daily_loss_limit": INTERNAL_DAILY_LOSS_LIMIT,
            "internal_peak_drawdown_limit": INTERNAL_PEAK_DRAWDOWN_LIMIT,
            "external_daily_loss_limit": EXTERNAL_DAILY_LOSS_LIMIT,
            "external_max_loss_limit": EXTERNAL_MAX_LOSS_LIMIT,
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
