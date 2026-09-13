"""VT-08 R3.12 official adaptive prop-firm Monte Carlo.

Research-only.  This module combines the frozen R3.11 consumed evidence and broker
volume constraints with an explicit sovereign Risk authority.  Risk is recomputed
before every candidate entry, grows slowly with profit cushion, contracts faster
with drawdown, and is finally capped by internal guards, provider rules, sleeve /
portfolio heat, correlated exposure and broker-valid quantity.

The proposed [2020-07-01, 2022-07-01) holdout is never read by this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import fmean, median
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_b01_risk_economic_replay_r3_11 import (
    BASELINE_RUN_ID,
    CONSUMED_EVIDENCE_FLOOR,
    FRESH_RUN_ID,
    BrokerVolumeConstraints,
    TradeObservation,
    broker_valid_fixed_risk_quantity,
    load_consumed_evidence,
)
from qore.infrastructure.trader_lab.vt08_official_monte_carlo_r3_11 import (
    BLOCK_DAYS,
    HORIZON_DAYS,
    INPUT_ARTIFACTS,
    PORTFOLIOS,
    PreparedDay,
    PreparedTrade,
    paired_block_indices,
    prepare_daily_evidence,
    simulate_portfolio_path,
)
from qore.infrastructure.trader_lab.vt08_official_monte_carlo_r3_11 import (
    PathMetrics as StaticPathMetrics,
)
from qore.infrastructure.trader_lab.vt08_prop_firm_profiles_r3_12 import (
    FTMO_2STEP_2026_09_12,
    FUNDEDNEXT_STELLAR_2STEP_2026_09_12,
    PropFirmProfile,
)

SCHEMA = "qore.vt08.r3.12.official-adaptive-prop-firm-monte-carlo.v1"
PATHS = 10_000
SENSITIVITY_PATHS = 2_500
SEED = 20260912
PRIMARY_COST_BPS = Decimal("0.50")
COST_GRID_BPS = (Decimal("0.00"), Decimal("0.25"), Decimal("0.50"), Decimal("1.00"))
SIMULATION_MONTH_DAYS = 21
TARGETS = (Decimal("0.05"), Decimal("0.08"), Decimal("0.10"))
PROTECTED_HOLDOUT_START = date(2020, 7, 1)
PROTECTED_HOLDOUT_END = date(2022, 7, 1)


class AdaptiveMonteCarloError(ValueError):
    """Raised when R3.12 policy, evidence or simulation invariants fail."""


@dataclass(frozen=True, slots=True)
class AdaptiveRiskPolicy:
    name: str = "balanced-adaptive-v1"
    a_base_bps: Decimal = Decimal("25")
    gbpjpy_base_bps: Decimal = Decimal("20")
    a_floor_bps: Decimal = Decimal("10")
    gbpjpy_floor_bps: Decimal = Decimal("8")
    a_ceiling_bps: Decimal = Decimal("30")
    gbpjpy_ceiling_bps: Decimal = Decimal("25")
    portfolio_heat_bps: Decimal = Decimal("90")
    a_sleeve_heat_bps: Decimal = Decimal("60")
    gbpjpy_sleeve_heat_bps: Decimal = Decimal("45")
    correlated_heat_bps: Decimal = Decimal("50")
    internal_daily_guard_bps: Decimal = Decimal("200")
    internal_peak_drawdown_guard_bps: Decimal = Decimal("500")
    provider_safety_buffer_bps: Decimal = Decimal("10")
    full_profit_cushion_fraction: Decimal = Decimal("0.10")
    full_drawdown_brake_fraction: Decimal = Decimal("0.03")
    hysteresis_bps: Decimal = Decimal("0.25")
    upshift_step_bps: Decimal = Decimal("0.50")
    downshift_step_bps: Decimal = Decimal("5.00")

    def __post_init__(self) -> None:
        if not self.name:
            raise AdaptiveMonteCarloError("policy name is required")
        for floor, base, ceiling, sleeve in (
            (self.a_floor_bps, self.a_base_bps, self.a_ceiling_bps, "A"),
            (
                self.gbpjpy_floor_bps,
                self.gbpjpy_base_bps,
                self.gbpjpy_ceiling_bps,
                "GBPJPY",
            ),
        ):
            if not Decimal(0) < floor <= base <= ceiling:
                raise AdaptiveMonteCarloError(f"invalid {sleeve} floor/base/ceiling")
        if self.portfolio_heat_bps <= 0:
            raise AdaptiveMonteCarloError("portfolio heat must be positive")
        if self.a_sleeve_heat_bps > self.portfolio_heat_bps:
            raise AdaptiveMonteCarloError("A sleeve heat cannot exceed portfolio heat")
        if self.gbpjpy_sleeve_heat_bps > self.portfolio_heat_bps:
            raise AdaptiveMonteCarloError("GBPJPY sleeve heat cannot exceed portfolio heat")
        if self.correlated_heat_bps > self.portfolio_heat_bps:
            raise AdaptiveMonteCarloError("correlated heat cannot exceed portfolio heat")
        if not Decimal(0) < self.internal_daily_guard_bps < Decimal(10_000):
            raise AdaptiveMonteCarloError("internal daily guard must be in (0,10000)")
        if not Decimal(0) < self.internal_peak_drawdown_guard_bps < Decimal(10_000):
            raise AdaptiveMonteCarloError("internal peak DD guard must be in (0,10000)")
        if self.full_profit_cushion_fraction <= 0 or self.full_drawdown_brake_fraction <= 0:
            raise AdaptiveMonteCarloError("adaptive scaling horizons must be positive")
        if not Decimal(0) <= self.hysteresis_bps < self.downshift_step_bps:
            raise AdaptiveMonteCarloError("invalid hysteresis")
        if not Decimal(0) < self.upshift_step_bps < self.downshift_step_bps:
            raise AdaptiveMonteCarloError("downshift must be faster than upshift")

    def base_bps(self, sleeve: str) -> Decimal:
        if sleeve == "a":
            return self.a_base_bps
        if sleeve == "gbpjpy":
            return self.gbpjpy_base_bps
        raise AdaptiveMonteCarloError(f"unknown sleeve {sleeve}")

    def floor_bps(self, sleeve: str) -> Decimal:
        if sleeve == "a":
            return self.a_floor_bps
        if sleeve == "gbpjpy":
            return self.gbpjpy_floor_bps
        raise AdaptiveMonteCarloError(f"unknown sleeve {sleeve}")

    def ceiling_bps(self, sleeve: str) -> Decimal:
        if sleeve == "a":
            return self.a_ceiling_bps
        if sleeve == "gbpjpy":
            return self.gbpjpy_ceiling_bps
        raise AdaptiveMonteCarloError(f"unknown sleeve {sleeve}")

    def sleeve_heat_bps(self, sleeve: str) -> Decimal:
        if sleeve == "a":
            return self.a_sleeve_heat_bps
        if sleeve == "gbpjpy":
            return self.gbpjpy_sleeve_heat_bps
        raise AdaptiveMonteCarloError(f"unknown sleeve {sleeve}")


RESEARCH_POLICIES = (
    AdaptiveRiskPolicy(
        name="lower-plateau-v1",
        a_base_bps=Decimal("20"),
        gbpjpy_base_bps=Decimal("20"),
        a_ceiling_bps=Decimal("25"),
        gbpjpy_ceiling_bps=Decimal("22.5"),
    ),
    AdaptiveRiskPolicy(),
    AdaptiveRiskPolicy(
        name="upper-plateau-v1",
        a_base_bps=Decimal("30"),
        gbpjpy_base_bps=Decimal("25"),
        a_ceiling_bps=Decimal("30"),
        gbpjpy_ceiling_bps=Decimal("25"),
    ),
)
PRIMARY_POLICY = RESEARCH_POLICIES[1]
PROFILES = (FTMO_2STEP_2026_09_12, FUNDEDNEXT_STELLAR_2STEP_2026_09_12)


@dataclass(slots=True)
class RiskMemory:
    a_bps: Decimal
    gbpjpy_bps: Decimal

    @classmethod
    def from_policy(cls, policy: AdaptiveRiskPolicy) -> RiskMemory:
        return cls(policy.a_base_bps, policy.gbpjpy_base_bps)

    def get(self, sleeve: str) -> Decimal:
        if sleeve == "a":
            return self.a_bps
        if sleeve == "gbpjpy":
            return self.gbpjpy_bps
        raise AdaptiveMonteCarloError(f"unknown sleeve {sleeve}")

    def set(self, sleeve: str, value: Decimal) -> None:
        if sleeve == "a":
            self.a_bps = value
            return
        if sleeve == "gbpjpy":
            self.gbpjpy_bps = value
            return
        raise AdaptiveMonteCarloError(f"unknown sleeve {sleeve}")


@dataclass(frozen=True, slots=True)
class AdaptivePreparedTrade:
    prepared: PreparedTrade
    sleeve: str
    per_unit_gross_pnl_usd: Decimal
    per_unit_cost_usd: Decimal


@dataclass(frozen=True, slots=True)
class AdaptivePreparedDay:
    source_day: date
    trades: tuple[AdaptivePreparedTrade, ...]


@dataclass(slots=True)
class OpenPosition:
    exit_at: datetime
    symbol: str
    sleeve: str
    quantity: Decimal
    bounded_loss_usd: Decimal
    gross_pnl_usd: Decimal
    cost_usd: Decimal
    net_pnl_usd: Decimal
    net_r: Decimal
    authorized_risk_bps: Decimal


@dataclass(slots=True)
class MonthAccumulator:
    key: str
    start_equity: Decimal
    peak_equity: Decimal
    max_drawdown: Decimal = Decimal(0)
    best_day_return: Decimal | None = None
    worst_day_return: Decimal | None = None
    trades: int = 0
    wins: int = 0
    losses: int = 0
    positive_pnl: Decimal = Decimal(0)
    negative_pnl_abs: Decimal = Decimal(0)
    gross_pnl: Decimal = Decimal(0)
    net_pnl: Decimal = Decimal(0)
    r_total: Decimal = Decimal(0)
    risks_bps: list[Decimal] = field(default_factory=list)
    heats_bps: list[Decimal] = field(default_factory=list)
    a_pnl: Decimal = Decimal(0)
    gbpjpy_pnl: Decimal = Decimal(0)
    min_daily_headroom: Decimal | None = None
    min_max_loss_headroom: Decimal | None = None


@dataclass(frozen=True, slots=True)
class MonthResult:
    key: str
    start_equity_usd: float
    end_equity_usd: float
    gross_return: float
    net_return: float
    realized_return: float
    equity_return: float
    pnl_usd: float
    max_drawdown: float
    best_day: float
    worst_day: float
    trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float | None
    r_total: float
    average_r: float
    average_authorized_risk_bps: float
    median_authorized_risk_bps: float
    maximum_authorized_risk_bps: float
    minimum_authorized_risk_bps: float
    average_risk_usd: float
    maximum_risk_usd: float
    maximum_portfolio_heat_bps: float
    average_portfolio_heat_bps: float
    a_contribution_fraction: float
    gbpjpy_contribution_fraction: float
    total_contribution_fraction: float
    month_end_profit_cushion_fraction: float
    remaining_daily_loss_headroom_fraction: float
    remaining_maximum_loss_headroom_fraction: float
    growth_efficiency: float | None


@dataclass(frozen=True, slots=True)
class PathMetrics:
    terminal_return: float
    terminal_equity_usd: float
    max_drawdown: float
    losing_streak: int
    underwater_days: int
    max_concurrency: int
    max_heat_bps: float
    allow: int
    reduce: int
    reject: int
    risk_floor_interactions: int
    risk_ceiling_interactions: int
    provider_rule_throttles: int
    internal_daily_guard_hits: int
    internal_dd_throttle_hits: int
    heat_throttles: int
    correlation_throttles: int
    broker_throttles: int
    account_containment: bool
    daily_loss_breach: bool
    maximum_loss_breach: bool
    any_prop_firm_breach: bool
    ruin: bool
    first_breach_day: int | None
    target_days: tuple[int | None, ...]
    months: tuple[MonthResult, ...]
    authorized_risk_bps: tuple[float, ...]
    risk_after_cushion_2pct: tuple[float, ...]
    risk_after_cushion_5pct: tuple[float, ...]
    risk_after_cushion_10pct: tuple[float, ...]
    risk_during_dd_1pct: tuple[float, ...]
    risk_during_dd_2pct: tuple[float, ...]
    risk_during_dd_3pct: tuple[float, ...]
    risk_during_dd_5pct: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class Authorization:
    outcome: str
    quantity: Decimal
    bounded_loss_usd: Decimal
    authorized_risk_bps: Decimal
    regime_risk_bps: Decimal
    reasons: tuple[str, ...]


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise AdaptiveMonteCarloError("distribution cannot be empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _distribution(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": fmean(values),
        "p01": _percentile(values, 0.01),
        "p05": _percentile(values, 0.05),
        "p25": _percentile(values, 0.25),
        "median": _percentile(values, 0.50),
        "p75": _percentile(values, 0.75),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
    }


def _optional_distribution(values: Sequence[float]) -> dict[str, float] | None:
    return None if not values else _distribution(values)


def _scope_membership(trade: TradeObservation, portfolio: str) -> bool:
    return (trade.symbol, trade.side) in PORTFOLIOS[portfolio]


def _sleeve(trade: TradeObservation) -> str:
    if trade.side == "short" and trade.symbol in {"AUDJPY", "GBPUSD"}:
        return "a"
    if trade.symbol == "GBPJPY":
        return "gbpjpy"
    raise AdaptiveMonteCarloError(f"trade outside frozen sleeves: {trade.symbol} {trade.side}")


def _correlation_groups(symbol: str) -> tuple[str, ...]:
    groups: list[str] = []
    if "GBP" in symbol:
        groups.append("GBP")
    if "JPY" in symbol:
        groups.append("JPY")
    return tuple(groups)


def target_risk_bps(
    policy: AdaptiveRiskPolicy,
    *,
    sleeve: str,
    equity: Decimal,
    peak_equity: Decimal,
    starting_equity: Decimal,
) -> Decimal:
    """Continuous slow-up / fast-down target before hysteresis and hard constraints."""
    if equity <= 0 or peak_equity <= 0 or starting_equity <= 0:
        raise AdaptiveMonteCarloError("equity inputs must be positive")
    base = policy.base_bps(sleeve)
    floor = policy.floor_bps(sleeve)
    ceiling = policy.ceiling_bps(sleeve)
    cushion = max(Decimal(0), equity / starting_equity - Decimal(1))
    cushion_progress = min(Decimal(1), cushion / policy.full_profit_cushion_fraction)
    up = (ceiling - base) * cushion_progress
    drawdown = max(Decimal(0), (peak_equity - equity) / peak_equity)
    brake_progress = min(Decimal(1), drawdown / policy.full_drawdown_brake_fraction)
    down = (base - floor) * brake_progress
    return min(ceiling, max(floor, base + up - down))


def apply_hysteresis(
    policy: AdaptiveRiskPolicy,
    *,
    previous_bps: Decimal,
    target_bps_value: Decimal,
) -> Decimal:
    """Persist small changes; when movement is real, upshift slower than downshift."""
    delta = target_bps_value - previous_bps
    if abs(delta) <= policy.hysteresis_bps:
        return previous_bps
    if delta > 0:
        return min(target_bps_value, previous_bps + policy.upshift_step_bps)
    return max(target_bps_value, previous_bps - policy.downshift_step_bps)


def _adaptive_days(
    trades: Sequence[TradeObservation],
    constraints: Mapping[str, BrokerVolumeConstraints],
    conversion_bars: Mapping[str, Mapping[datetime, Decimal]],
    *,
    cost_bps: Decimal,
) -> tuple[AdaptivePreparedDay, ...]:
    net_days = prepare_daily_evidence(trades, constraints, conversion_bars, cost_bps=cost_bps)
    gross_days = prepare_daily_evidence(trades, constraints, conversion_bars, cost_bps=Decimal(0))
    if len(net_days) != len(gross_days):
        raise AdaptiveMonteCarloError("gross/net prepared evidence cardinality mismatch")
    result: list[AdaptivePreparedDay] = []
    for net_day, gross_day in zip(net_days, gross_days, strict=True):
        if net_day.source_day != gross_day.source_day or len(net_day.trades) != len(
            gross_day.trades
        ):
            raise AdaptiveMonteCarloError("gross/net prepared evidence ordering mismatch")
        day_trades: list[AdaptivePreparedTrade] = []
        for net_trade, gross_trade in zip(net_day.trades, gross_day.trades, strict=True):
            if net_trade.source != gross_trade.source:
                raise AdaptiveMonteCarloError("gross/net prepared trade mismatch")
            cost = gross_trade.per_unit_net_pnl_usd - net_trade.per_unit_net_pnl_usd
            if cost < 0:
                raise AdaptiveMonteCarloError("modeled cost cannot improve PnL")
            day_trades.append(
                AdaptivePreparedTrade(
                    prepared=net_trade,
                    sleeve=_sleeve(net_trade.source),
                    per_unit_gross_pnl_usd=gross_trade.per_unit_net_pnl_usd,
                    per_unit_cost_usd=cost,
                )
            )
        result.append(AdaptivePreparedDay(net_day.source_day, tuple(day_trades)))
    return tuple(result)


def _sum_open_risk(positions: Sequence[OpenPosition]) -> Decimal:
    return sum((item.bounded_loss_usd for item in positions), Decimal(0))


def _sleeve_open_risk(positions: Sequence[OpenPosition], sleeve: str) -> Decimal:
    return sum(
        (item.bounded_loss_usd for item in positions if item.sleeve == sleeve),
        Decimal(0),
    )


def _correlated_open_risk(positions: Sequence[OpenPosition], symbol: str) -> Decimal:
    groups = set(_correlation_groups(symbol))
    if not groups:
        return Decimal(0)
    return sum(
        (
            item.bounded_loss_usd
            for item in positions
            if groups.intersection(_correlation_groups(item.symbol))
        ),
        Decimal(0),
    )


def _authorize(
    *,
    trade: AdaptivePreparedTrade,
    policy: AdaptiveRiskPolicy,
    profile: PropFirmProfile,
    memory: RiskMemory,
    balance: Decimal,
    peak_equity: Decimal,
    reset_balance: Decimal,
    open_positions: Sequence[OpenPosition],
) -> Authorization:
    sleeve = trade.sleeve
    open_risk = _sum_open_risk(open_positions)
    adverse_equity = balance - open_risk
    target = target_risk_bps(
        policy,
        sleeve=sleeve,
        equity=adverse_equity,
        peak_equity=peak_equity,
        starting_equity=profile.starting_balance_usd,
    )
    previous = memory.get(sleeve)
    regime_bps = apply_hysteresis(policy, previous_bps=previous, target_bps_value=target)
    memory.set(sleeve, regime_bps)

    safety = profile.starting_balance_usd * policy.provider_safety_buffer_bps / Decimal(10_000)
    provider_daily_floor = profile.daily_loss_floor_usd(reset_balance) + safety
    provider_max_floor = profile.maximum_loss_floor_usd + safety
    internal_daily_floor = (
        reset_balance
        - profile.starting_balance_usd * policy.internal_daily_guard_bps / Decimal(10_000)
    )
    internal_dd_floor = peak_equity * (
        Decimal(1) - policy.internal_peak_drawdown_guard_bps / Decimal(10_000)
    )
    provider_daily_headroom = max(Decimal(0), adverse_equity - provider_daily_floor)
    provider_max_headroom = max(Decimal(0), adverse_equity - provider_max_floor)
    internal_daily_headroom = max(Decimal(0), adverse_equity - internal_daily_floor)
    internal_dd_headroom = max(Decimal(0), adverse_equity - internal_dd_floor)
    portfolio_headroom = max(
        Decimal(0),
        balance * policy.portfolio_heat_bps / Decimal(10_000) - open_risk,
    )
    sleeve_headroom = max(
        Decimal(0),
        balance * policy.sleeve_heat_bps(sleeve) / Decimal(10_000)
        - _sleeve_open_risk(open_positions, sleeve),
    )
    correlation_headroom = max(
        Decimal(0),
        balance * policy.correlated_heat_bps / Decimal(10_000)
        - _correlated_open_risk(open_positions, trade.prepared.source.symbol),
    )
    desired = balance * regime_bps / Decimal(10_000)
    limits = {
        "provider_daily": provider_daily_headroom,
        "provider_maximum": provider_max_headroom,
        "internal_daily": internal_daily_headroom,
        "internal_drawdown": internal_dd_headroom,
        "portfolio_heat": portfolio_headroom,
        "sleeve_heat": sleeve_headroom,
        "correlation_heat": correlation_headroom,
    }
    permitted = min([desired, *limits.values()])
    if permitted <= 0:
        reasons = tuple(sorted(name for name, value in limits.items() if value <= 0))
        return Authorization("REJECT", Decimal(0), Decimal(0), Decimal(0), regime_bps, reasons)
    limiting_reasons = tuple(
        sorted(
            name
            for name, value in limits.items()
            if value < desired and abs(value - permitted) <= Decimal("0.000001")
        )
    )
    broker_outcome, quantity, bounded = broker_valid_fixed_risk_quantity(
        desired_loss_usd=permitted,
        per_unit_loss_usd=trade.prepared.per_unit_loss_usd,
        constraints=trade.prepared.constraints,
    )
    if broker_outcome == "REJECT":
        return Authorization(
            "REJECT",
            Decimal(0),
            Decimal(0),
            Decimal(0),
            regime_bps,
            (*limiting_reasons, "broker_quantity"),
        )
    actual_bps = bounded / balance * Decimal(10_000)
    reduced = permitted < desired or broker_outcome == "REDUCE" or bounded < desired
    reasons = list(limiting_reasons)
    if broker_outcome == "REDUCE" or bounded < permitted - Decimal("0.000001"):
        reasons.append("broker_quantity")
    return Authorization(
        "REDUCE" if reduced else "ALLOW",
        quantity,
        bounded,
        actual_bps,
        regime_bps,
        tuple(sorted(set(reasons))),
    )


def _month_key(day_index: int) -> str:
    return f"M{((day_index - 1) // SIMULATION_MONTH_DAYS) + 1:02d}"


def _finish_month(
    month: MonthAccumulator,
    *,
    end_equity: Decimal,
    starting_equity: Decimal,
    daily_floor: Decimal,
    max_loss_floor: Decimal,
) -> MonthResult:
    net_return = end_equity / month.start_equity - Decimal(1)
    gross_return = month.gross_pnl / month.start_equity
    max_dd = month.max_drawdown
    pf: float | None
    if month.negative_pnl_abs == 0:
        pf = None
    else:
        pf = float(month.positive_pnl / month.negative_pnl_abs)
    win_rate = 0.0 if month.trades == 0 else month.wins / month.trades
    risks = [float(value) for value in month.risks_bps]
    heats = [float(value) for value in month.heats_bps]
    avg_risk_bps = 0.0 if not risks else fmean(risks)
    median_risk_bps = 0.0 if not risks else median(risks)
    max_risk_bps = 0.0 if not risks else max(risks)
    min_risk_bps = 0.0 if not risks else min(risks)
    avg_risk_usd = float(month.start_equity * Decimal(str(avg_risk_bps)) / Decimal(10_000))
    max_risk_usd = float(month.start_equity * Decimal(str(max_risk_bps)) / Decimal(10_000))
    daily_headroom = max(Decimal(0), end_equity - daily_floor) / starting_equity
    max_headroom = max(Decimal(0), end_equity - max_loss_floor) / starting_equity
    efficiency = None if max_dd <= 0 else float(net_return / max_dd)
    return MonthResult(
        key=month.key,
        start_equity_usd=float(month.start_equity),
        end_equity_usd=float(end_equity),
        gross_return=float(gross_return),
        net_return=float(net_return),
        realized_return=float(net_return),
        equity_return=float(net_return),
        pnl_usd=float(end_equity - month.start_equity),
        max_drawdown=float(max_dd),
        best_day=float(month.best_day_return or Decimal(0)),
        worst_day=float(month.worst_day_return or Decimal(0)),
        trades=month.trades,
        wins=month.wins,
        losses=month.losses,
        win_rate=win_rate,
        profit_factor=pf,
        r_total=float(month.r_total),
        average_r=0.0 if month.trades == 0 else float(month.r_total / month.trades),
        average_authorized_risk_bps=avg_risk_bps,
        median_authorized_risk_bps=median_risk_bps,
        maximum_authorized_risk_bps=max_risk_bps,
        minimum_authorized_risk_bps=min_risk_bps,
        average_risk_usd=avg_risk_usd,
        maximum_risk_usd=max_risk_usd,
        maximum_portfolio_heat_bps=0.0 if not heats else max(heats),
        average_portfolio_heat_bps=0.0 if not heats else fmean(heats),
        a_contribution_fraction=float(month.a_pnl / month.start_equity),
        gbpjpy_contribution_fraction=float(month.gbpjpy_pnl / month.start_equity),
        total_contribution_fraction=float(month.net_pnl / month.start_equity),
        month_end_profit_cushion_fraction=float(end_equity / starting_equity - Decimal(1)),
        remaining_daily_loss_headroom_fraction=float(daily_headroom),
        remaining_maximum_loss_headroom_fraction=float(max_headroom),
        growth_efficiency=efficiency,
    )


def _risk_bucket_append(
    *,
    value: float,
    cushion: Decimal,
    drawdown: Decimal,
    c2: list[float],
    c5: list[float],
    c10: list[float],
    d1: list[float],
    d2: list[float],
    d3: list[float],
    d5: list[float],
) -> None:
    if cushion >= Decimal("0.02"):
        c2.append(value)
    if cushion >= Decimal("0.05"):
        c5.append(value)
    if cushion >= Decimal("0.10"):
        c10.append(value)
    if drawdown >= Decimal("0.01"):
        d1.append(value)
    if drawdown >= Decimal("0.02"):
        d2.append(value)
    if drawdown >= Decimal("0.03"):
        d3.append(value)
    if drawdown >= Decimal("0.05"):
        d5.append(value)


def simulate_adaptive_path(
    days: Sequence[AdaptivePreparedDay],
    indices: Sequence[int],
    *,
    portfolio: str,
    policy: AdaptiveRiskPolicy,
    profile: PropFirmProfile,
) -> PathMetrics:
    if portfolio not in PORTFOLIOS:
        raise AdaptiveMonteCarloError(f"unknown frozen portfolio: {portfolio}")
    starting = profile.starting_balance_usd
    balance = starting
    peak = starting
    reset_balance = starting
    open_positions: list[OpenPosition] = []
    memory = RiskMemory.from_policy(policy)
    counts = {"ALLOW": 0, "REDUCE": 0, "REJECT": 0}
    interactions = {
        "risk_floor": 0,
        "risk_ceiling": 0,
        "provider": 0,
        "internal_daily": 0,
        "internal_dd": 0,
        "heat": 0,
        "correlation": 0,
        "broker": 0,
    }
    account_containment = False
    daily_breach = False
    maximum_breach = False
    first_breach_day: int | None = None
    ruin = False
    max_drawdown = Decimal(0)
    losing = 0
    max_losing = 0
    underwater = 0
    max_underwater = 0
    max_concurrency = 0
    max_heat_bps = Decimal(0)
    target_days: list[int | None] = [None] * len(TARGETS)
    risk_values: list[float] = []
    c2: list[float] = []
    c5: list[float] = []
    c10: list[float] = []
    d1: list[float] = []
    d2: list[float] = []
    d3: list[float] = []
    d5: list[float] = []
    months: list[MonthResult] = []
    month = MonthAccumulator("M01", balance, balance)
    provider_tz = ZoneInfo(profile.daily_reset_timezone)
    epoch_local = datetime(2000, 1, 3, tzinfo=provider_tz)

    def provider_floors() -> tuple[Decimal, Decimal]:
        safety = starting * policy.provider_safety_buffer_bps / Decimal(10_000)
        return (
            profile.daily_loss_floor_usd(reset_balance) + safety,
            profile.maximum_loss_floor_usd + safety,
        )

    def observe_adverse_equity() -> Decimal:
        nonlocal max_drawdown, max_heat_bps, ruin
        open_risk = _sum_open_risk(open_positions)
        adverse = balance - open_risk
        peak_safe = peak if peak > 0 else starting
        dd = max(Decimal(0), (peak_safe - adverse) / peak_safe)
        max_drawdown = max(max_drawdown, dd)
        month.max_drawdown = max(month.max_drawdown, dd)
        heat_bps = Decimal(0) if balance <= 0 else open_risk / balance * Decimal(10_000)
        max_heat_bps = max(max_heat_bps, heat_bps)
        month.heats_bps.append(heat_bps)
        ruin = ruin or adverse <= 0
        return adverse

    def close_due(cutoff: datetime) -> None:
        nonlocal balance, peak, losing, max_losing, open_positions
        due = sorted(
            (item for item in open_positions if item.exit_at <= cutoff),
            key=lambda item: item.exit_at,
        )
        for item in due:
            balance += item.net_pnl_usd
            month.gross_pnl += item.gross_pnl_usd
            month.net_pnl += item.net_pnl_usd
            month.r_total += item.net_r
            if item.net_pnl_usd > 0:
                month.wins += 1
                month.positive_pnl += item.net_pnl_usd
                losing = 0
            elif item.net_pnl_usd < 0:
                month.losses += 1
                month.negative_pnl_abs += -item.net_pnl_usd
                losing += 1
                max_losing = max(max_losing, losing)
            if item.sleeve == "a":
                month.a_pnl += item.net_pnl_usd
            else:
                month.gbpjpy_pnl += item.net_pnl_usd
            peak = max(peak, balance)
            month.peak_equity = max(month.peak_equity, balance)
        due_ids = {id(item) for item in due}
        open_positions = [item for item in open_positions if id(item) not in due_ids]
        observe_adverse_equity()

    breached = False
    for simulated_day, source_index in enumerate(indices, start=1):
        if breached:
            break
        local_day_start = epoch_local + timedelta(days=simulated_day - 1)
        day_start = local_day_start.astimezone(UTC)
        day_end = (local_day_start + timedelta(days=1)).astimezone(UTC)
        close_due(day_start)
        current_month = _month_key(simulated_day)
        if current_month != month.key:
            daily_floor, max_floor = provider_floors()
            months.append(
                _finish_month(
                    month,
                    end_equity=balance,
                    starting_equity=starting,
                    daily_floor=daily_floor,
                    max_loss_floor=max_floor,
                )
            )
            month = MonthAccumulator(current_month, balance, balance)
        reset_balance = balance
        day_start_balance = balance
        source_day = days[source_index]
        for trade in source_day.trades:
            if not _scope_membership(trade.prepared.source, portfolio):
                continue
            source_local = trade.prepared.source.signal_at.astimezone(provider_tz)
            source_midnight = datetime.combine(
                source_local.date(), datetime.min.time(), tzinfo=provider_tz
            )
            entry_at = day_start + (source_local - source_midnight)
            close_due(entry_at)
            auth = _authorize(
                trade=trade,
                policy=policy,
                profile=profile,
                memory=memory,
                balance=balance,
                peak_equity=peak,
                reset_balance=reset_balance,
                open_positions=open_positions,
            )
            if auth.regime_risk_bps <= policy.floor_bps(trade.sleeve) + Decimal("0.000001"):
                interactions["risk_floor"] += 1
            if auth.regime_risk_bps >= policy.ceiling_bps(trade.sleeve) - Decimal("0.000001"):
                interactions["risk_ceiling"] += 1
            for reason in auth.reasons:
                if reason.startswith("provider_"):
                    interactions["provider"] += 1
                elif reason == "internal_daily":
                    interactions["internal_daily"] += 1
                elif reason == "internal_drawdown":
                    interactions["internal_dd"] += 1
                elif reason in {"portfolio_heat", "sleeve_heat"}:
                    interactions["heat"] += 1
                elif reason == "correlation_heat":
                    interactions["correlation"] += 1
                elif reason == "broker_quantity":
                    interactions["broker"] += 1
            counts[auth.outcome] += 1
            if auth.outcome == "REJECT":
                if any(
                    reason
                    in {
                        "provider_daily",
                        "provider_maximum",
                        "internal_daily",
                        "internal_drawdown",
                    }
                    for reason in auth.reasons
                ):
                    account_containment = True
                continue
            quantity = auth.quantity
            gross_pnl = quantity * trade.per_unit_gross_pnl_usd
            cost_usd = quantity * trade.per_unit_cost_usd
            net_pnl = gross_pnl - cost_usd
            net_r = Decimal(0) if auth.bounded_loss_usd <= 0 else net_pnl / auth.bounded_loss_usd
            open_positions.append(
                OpenPosition(
                    exit_at=entry_at + trade.prepared.duration,
                    symbol=trade.prepared.source.symbol,
                    sleeve=trade.sleeve,
                    quantity=quantity,
                    bounded_loss_usd=auth.bounded_loss_usd,
                    gross_pnl_usd=gross_pnl,
                    cost_usd=cost_usd,
                    net_pnl_usd=net_pnl,
                    net_r=net_r,
                    authorized_risk_bps=auth.authorized_risk_bps,
                )
            )
            month.trades += 1
            month.risks_bps.append(auth.authorized_risk_bps)
            risk_float = float(auth.authorized_risk_bps)
            risk_values.append(risk_float)
            max_concurrency = max(max_concurrency, len(open_positions))
            adverse = observe_adverse_equity()
            cushion = max(Decimal(0), adverse / starting - Decimal(1))
            dd = max(Decimal(0), (peak - adverse) / peak)
            _risk_bucket_append(
                value=risk_float,
                cushion=cushion,
                drawdown=dd,
                c2=c2,
                c5=c5,
                c10=c10,
                d1=d1,
                d2=d2,
                d3=d3,
                d5=d5,
            )
            daily_floor, max_floor = provider_floors()
            month.min_daily_headroom = (
                adverse - daily_floor
                if month.min_daily_headroom is None
                else min(month.min_daily_headroom, adverse - daily_floor)
            )
            month.min_max_loss_headroom = (
                adverse - max_floor
                if month.min_max_loss_headroom is None
                else min(month.min_max_loss_headroom, adverse - max_floor)
            )
            if adverse < daily_floor:
                daily_breach = True
                first_breach_day = first_breach_day or simulated_day
                breached = True
                break
            if adverse < max_floor:
                maximum_breach = True
                first_breach_day = first_breach_day or simulated_day
                breached = True
                break
        close_due(day_end)
        adverse_close = observe_adverse_equity()
        daily_floor, max_floor = provider_floors()
        if adverse_close < daily_floor:
            daily_breach = True
            first_breach_day = first_breach_day or simulated_day
            breached = True
        if adverse_close < max_floor:
            maximum_breach = True
            first_breach_day = first_breach_day or simulated_day
            breached = True
        day_return = (
            Decimal(0) if day_start_balance == 0 else balance / day_start_balance - Decimal(1)
        )
        month.best_day_return = (
            day_return if month.best_day_return is None else max(month.best_day_return, day_return)
        )
        month.worst_day_return = (
            day_return
            if month.worst_day_return is None
            else min(month.worst_day_return, day_return)
        )
        if balance < peak:
            underwater += 1
            max_underwater = max(max_underwater, underwater)
        else:
            underwater = 0
        for target_index, target in enumerate(TARGETS):
            if target_days[target_index] is None and balance >= starting * (Decimal(1) + target):
                target_days[target_index] = simulated_day

    if open_positions:
        close_due(datetime.max.replace(tzinfo=UTC))
    daily_floor, max_floor = provider_floors()
    months.append(
        _finish_month(
            month,
            end_equity=balance,
            starting_equity=starting,
            daily_floor=daily_floor,
            max_loss_floor=max_floor,
        )
    )
    return PathMetrics(
        terminal_return=float(balance / starting - Decimal(1)),
        terminal_equity_usd=float(balance),
        max_drawdown=float(max_drawdown),
        losing_streak=max_losing,
        underwater_days=max_underwater,
        max_concurrency=max_concurrency,
        max_heat_bps=float(max_heat_bps),
        allow=counts["ALLOW"],
        reduce=counts["REDUCE"],
        reject=counts["REJECT"],
        risk_floor_interactions=interactions["risk_floor"],
        risk_ceiling_interactions=interactions["risk_ceiling"],
        provider_rule_throttles=interactions["provider"],
        internal_daily_guard_hits=interactions["internal_daily"],
        internal_dd_throttle_hits=interactions["internal_dd"],
        heat_throttles=interactions["heat"],
        correlation_throttles=interactions["correlation"],
        broker_throttles=interactions["broker"],
        account_containment=account_containment,
        daily_loss_breach=daily_breach,
        maximum_loss_breach=maximum_breach,
        any_prop_firm_breach=daily_breach or maximum_breach,
        ruin=ruin or balance <= 0,
        first_breach_day=first_breach_day,
        target_days=tuple(target_days),
        months=tuple(months),
        authorized_risk_bps=tuple(risk_values),
        risk_after_cushion_2pct=tuple(c2),
        risk_after_cushion_5pct=tuple(c5),
        risk_after_cushion_10pct=tuple(c10),
        risk_during_dd_1pct=tuple(d1),
        risk_during_dd_2pct=tuple(d2),
        risk_during_dd_3pct=tuple(d3),
        risk_during_dd_5pct=tuple(d5),
    )


def _rolling_month_returns(months: Sequence[MonthResult], width: int) -> list[float]:
    if width <= 0:
        raise AdaptiveMonteCarloError("rolling width must be positive")
    result: list[float] = []
    for start in range(0, len(months) - width + 1):
        compounded = 1.0
        for month in months[start : start + width]:
            compounded *= 1.0 + month.net_return
        result.append(compounded - 1.0)
    return result


def _max_streak(values: Sequence[bool]) -> int:
    longest = 0
    current = 0
    for value in values:
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _summarize_months(results: Sequence[PathMetrics]) -> dict[str, object]:
    months = [month for result in results for month in result.months]
    returns = [month.net_return for month in months]
    positive_streaks = [
        float(_max_streak([month.net_return > 0 for month in result.months])) for result in results
    ]
    negative_streaks = [
        float(_max_streak([month.net_return < 0 for month in result.months])) for result in results
    ]
    rolling3 = [value for result in results for value in _rolling_month_returns(result.months, 3)]
    rolling6 = [value for result in results for value in _rolling_month_returns(result.months, 6)]
    geometric: list[float] = []
    for result in results:
        if not result.months:
            continue
        growth = 1.0
        for month in result.months:
            growth *= 1.0 + month.net_return
        geometric.append(growth ** (1.0 / len(result.months)) - 1.0)
    efficiencies = [
        month.growth_efficiency for month in months if month.growth_efficiency is not None
    ]
    return {
        "definition": "21-business-day simulation month rebased to each month opening equity",
        "return": _distribution(returns),
        "geometric_monthly_growth": _distribution(geometric),
        "positive_month_probability": sum(value > 0 for value in returns) / len(returns),
        "negative_month_probability": sum(value < 0 for value in returns) / len(returns),
        "probability_month_below_minus_1pct": sum(value < -0.01 for value in returns)
        / len(returns),
        "probability_month_below_minus_2pct": sum(value < -0.02 for value in returns)
        / len(returns),
        "monthly_max_drawdown": _distribution([month.max_drawdown for month in months]),
        "worst_month_distribution": _distribution(
            [min(month.net_return for month in result.months) for result in results]
        ),
        "best_month_distribution": _distribution(
            [max(month.net_return for month in result.months) for result in results]
        ),
        "longest_negative_month_streak": _distribution(negative_streaks),
        "longest_positive_month_streak": _distribution(positive_streaks),
        "rolling_3_month_return": _optional_distribution(rolling3),
        "rolling_6_month_return": _optional_distribution(rolling6),
        "monthly_growth_efficiency": _optional_distribution(efficiencies),
    }


def _risk_summary(results: Sequence[PathMetrics], policy: AdaptiveRiskPolicy) -> dict[str, object]:
    all_values = [value for result in results for value in result.authorized_risk_bps]
    return {
        "starting_A_risk_bps": float(policy.a_base_bps),
        "starting_GBPJPY_risk_bps": float(policy.gbpjpy_base_bps),
        "authorized_risk_bps": _optional_distribution(all_values),
        "minimum_observed_risk_bps": None if not all_values else min(all_values),
        "maximum_observed_risk_bps": None if not all_values else max(all_values),
        "risk_after_plus_2pct_cushion_bps": _optional_distribution(
            [value for result in results for value in result.risk_after_cushion_2pct]
        ),
        "risk_after_plus_5pct_cushion_bps": _optional_distribution(
            [value for result in results for value in result.risk_after_cushion_5pct]
        ),
        "risk_after_plus_10pct_cushion_bps": _optional_distribution(
            [value for result in results for value in result.risk_after_cushion_10pct]
        ),
        "risk_during_1pct_drawdown_bps": _optional_distribution(
            [value for result in results for value in result.risk_during_dd_1pct]
        ),
        "risk_during_2pct_drawdown_bps": _optional_distribution(
            [value for result in results for value in result.risk_during_dd_2pct]
        ),
        "risk_during_3pct_drawdown_bps": _optional_distribution(
            [value for result in results for value in result.risk_during_dd_3pct]
        ),
        "risk_during_5pct_drawdown_bps": _optional_distribution(
            [value for result in results for value in result.risk_during_dd_5pct]
        ),
        "upshift_step_bps": float(policy.upshift_step_bps),
        "downshift_step_bps": float(policy.downshift_step_bps),
        "slow_up_fast_down": policy.upshift_step_bps < policy.downshift_step_bps,
    }


def _summarize_paths(
    results: Sequence[PathMetrics], policy: AdaptiveRiskPolicy
) -> dict[str, object]:
    terminal = [item.terminal_return for item in results]
    breach_days = [
        float(item.first_breach_day) for item in results if item.first_breach_day is not None
    ]
    target_summary: dict[str, object] = {}
    for index, target in enumerate(TARGETS):
        days = [item.target_days[index] for item in results if item.target_days[index] is not None]
        before_breach = [
            item.target_days[index]
            for item in results
            if item.target_days[index] is not None
            and (item.first_breach_day is None or item.target_days[index] <= item.first_breach_day)
        ]
        target_summary[f"{int(target * 100)}pct"] = {
            "probability_achieved_before_breach": len(before_breach) / len(results),
            "median_days_when_achieved": None if not days else median(days),
            "p95_days_when_achieved": None
            if not days
            else _percentile([float(v) for v in days], 0.95),
        }
    return {
        "terminal_return": _distribution(terminal),
        "terminal_equity_usd": _distribution([item.terminal_equity_usd for item in results]),
        "probability_terminal_positive": sum(value > 0 for value in terminal) / len(results),
        "maximum_drawdown": _distribution([item.max_drawdown for item in results]),
        "losing_streak": _distribution([float(item.losing_streak) for item in results]),
        "underwater_duration_days": _distribution(
            [float(item.underwater_days) for item in results]
        ),
        "max_concurrency": _distribution([float(item.max_concurrency) for item in results]),
        "max_portfolio_heat_bps": _distribution([item.max_heat_bps for item in results]),
        "risk_outcomes_total": {
            "ALLOW": sum(item.allow for item in results),
            "REDUCE": sum(item.reduce for item in results),
            "REJECT": sum(item.reject for item in results),
        },
        "risk_floor_interactions_total": sum(item.risk_floor_interactions for item in results),
        "risk_ceiling_interactions_total": sum(item.risk_ceiling_interactions for item in results),
        "provider_rule_throttles_total": sum(item.provider_rule_throttles for item in results),
        "internal_daily_guard_hits_total": sum(item.internal_daily_guard_hits for item in results),
        "internal_dd_throttle_hits_total": sum(item.internal_dd_throttle_hits for item in results),
        "heat_throttles_total": sum(item.heat_throttles for item in results),
        "correlation_throttles_total": sum(item.correlation_throttles for item in results),
        "broker_throttles_total": sum(item.broker_throttles for item in results),
        "account_containment_probability": sum(item.account_containment for item in results)
        / len(results),
        "daily_loss_breach_probability": sum(item.daily_loss_breach for item in results)
        / len(results),
        "maximum_loss_breach_probability": sum(item.maximum_loss_breach for item in results)
        / len(results),
        "any_prop_firm_breach_probability": sum(item.any_prop_firm_breach for item in results)
        / len(results),
        "ruin_probability": sum(item.ruin for item in results) / len(results),
        "median_time_to_breach_days": None if not breach_days else median(breach_days),
        "breach_cause_distribution": {
            "daily_only": sum(
                item.daily_loss_breach and not item.maximum_loss_breach for item in results
            )
            / len(results),
            "maximum_only": sum(
                item.maximum_loss_breach and not item.daily_loss_breach for item in results
            )
            / len(results),
            "both": sum(item.maximum_loss_breach and item.daily_loss_breach for item in results)
            / len(results),
        },
        "targets": target_summary,
        "monthly_growth": _summarize_months(results),
        "risk_dynamics": _risk_summary(results, policy),
    }


def _static_summary(results: Sequence[StaticPathMetrics]) -> dict[str, object]:
    # PathMetrics type comes from R3.11; keep this adapter intentionally narrow.
    terminal = [float(item.terminal_return) for item in results]
    drawdown = [float(item.max_drawdown) for item in results]
    return {
        "terminal_return": _distribution(terminal),
        "probability_terminal_positive": sum(value > 0 for value in terminal) / len(terminal),
        "maximum_drawdown": _distribution(drawdown),
        "ruin_probability": sum(bool(item.ruin) for item in results) / len(results),
    }


def _policy_material(policy: AdaptiveRiskPolicy) -> dict[str, object]:
    return {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in asdict(policy).items()
    }


def _profile_material(profile: PropFirmProfile) -> dict[str, object]:
    return {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in asdict(profile).items()
    }


def _file_digests(roots: Sequence[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for root in roots:
        for path in sorted(root.rglob("*.json")):
            key = f"{root.name}/{path.relative_to(root)}"
            result[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _evidence_fingerprints(roots: Sequence[Path]) -> dict[str, list[str]]:
    methodology: set[str] = set()
    source: set[str] = set()
    for root in roots:
        for path in root.rglob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            for key in ("methodology_fingerprint", "parent_methodology_fingerprint"):
                value = payload.get(key)
                if isinstance(value, str):
                    methodology.add(value)
            value = payload.get("source_contract_fingerprint")
            if isinstance(value, str):
                source.add(value)
    return {"methodology": sorted(methodology), "source_contract": sorted(source)}


def _paired_marginal(a: Sequence[PathMetrics], b: Sequence[PathMetrics]) -> dict[str, object]:
    if len(a) != len(b):
        raise AdaptiveMonteCarloError("paired marginal requires equal path counts")
    return {
        "terminal_return_B_minus_A": _distribution(
            [right.terminal_return - left.terminal_return for left, right in zip(a, b, strict=True)]
        ),
        "maximum_drawdown_B_minus_A": _distribution(
            [right.max_drawdown - left.max_drawdown for left, right in zip(a, b, strict=True)]
        ),
        "probability_B_terminal_return_exceeds_A": sum(
            right.terminal_return > left.terminal_return for left, right in zip(a, b, strict=True)
        )
        / len(a),
        "probability_B_drawdown_exceeds_A": sum(
            right.max_drawdown > left.max_drawdown for left, right in zip(a, b, strict=True)
        )
        / len(a),
    }


def build_report(
    baseline_root: Path,
    fresh_root: Path,
    *,
    git_sha: str,
    generated_at: str,
    paths: int = PATHS,
) -> dict[str, object]:
    if re.fullmatch(r"[0-9a-f]{40}", git_sha) is None:
        raise AdaptiveMonteCarloError("git SHA must be exact")
    trades, constraints, bars = load_consumed_evidence(baseline_root, fresh_root)
    if len(trades) != 809:
        raise AdaptiveMonteCarloError(f"expected 809 consumed trades, found {len(trades)}")
    if min(trade.signal_at for trade in trades) < CONSUMED_EVIDENCE_FLOOR:
        raise AdaptiveMonteCarloError("protected holdout evidence encountered")
    samples = {name: sum(_scope_membership(trade, name) for trade in trades) for name in PORTFOLIOS}
    expected = {"A_CORE": 117, "GBPJPY_RETURN_ENHANCER": 112, "B_COMBINED_PORTFOLIO": 229}
    if samples != expected:
        raise AdaptiveMonteCarloError(f"frozen portfolio cardinality changed: {samples}")

    primary_days = _adaptive_days(trades, constraints, bars, cost_bps=PRIMARY_COST_BPS)
    draws = paired_block_indices(
        len(primary_days),
        paths=paths,
        horizon_days=HORIZON_DAYS,
        block_days=BLOCK_DAYS,
        seed=SEED,
    )
    provider_results: dict[str, object] = {}
    for profile in PROFILES:
        raw: dict[str, list[PathMetrics]] = {name: [] for name in PORTFOLIOS}
        for indices in draws:
            for portfolio in PORTFOLIOS:
                raw[portfolio].append(
                    simulate_adaptive_path(
                        primary_days,
                        indices,
                        portfolio=portfolio,
                        policy=PRIMARY_POLICY,
                        profile=profile,
                    )
                )
        summarized = {
            portfolio: {
                "original_sample": samples[portfolio],
                "primary_0_50bp": _summarize_paths(results, PRIMARY_POLICY),
            }
            for portfolio, results in raw.items()
        }
        summarized["B_MINUS_A"] = _paired_marginal(raw["A_CORE"], raw["B_COMBINED_PORTFOLIO"])
        provider_results[profile.profile_id] = {
            "profile": _profile_material(profile),
            "results": summarized,
        }

    # Exact R3.11 static 50 bps / 150 bps replay on the same draws for comparison.
    static_days: tuple[PreparedDay, ...] = prepare_daily_evidence(
        trades, constraints, bars, cost_bps=PRIMARY_COST_BPS
    )
    static_reference: dict[str, object] = {}
    for portfolio in PORTFOLIOS:
        static_paths = [
            simulate_portfolio_path(static_days, indices, portfolio=portfolio) for indices in draws
        ]
        static_reference[portfolio] = _static_summary(static_paths)

    # Cost sensitivity: full paired structure, fewer paths, same deterministic prefix draws.
    sensitivity_draws = draws[: min(SENSITIVITY_PATHS, len(draws))]
    cost_sensitivity: dict[str, object] = {}
    profile = FTMO_2STEP_2026_09_12
    for cost in COST_GRID_BPS:
        days = _adaptive_days(trades, constraints, bars, cost_bps=cost)
        by_portfolio: dict[str, object] = {}
        for portfolio in PORTFOLIOS:
            results = [
                simulate_adaptive_path(
                    days,
                    indices,
                    portfolio=portfolio,
                    policy=PRIMARY_POLICY,
                    profile=profile,
                )
                for indices in sensitivity_draws
            ]
            by_portfolio[portfolio] = _summarize_paths(results, PRIMARY_POLICY)
        cost_sensitivity[format(cost, "f")] = by_portfolio

    # Policy plateau: B only, primary cost, FTMO profile, paired sensitivity paths.
    policy_sensitivity: dict[str, object] = {}
    for policy in RESEARCH_POLICIES:
        results = [
            simulate_adaptive_path(
                primary_days,
                indices,
                portfolio="B_COMBINED_PORTFOLIO",
                policy=policy,
                profile=FTMO_2STEP_2026_09_12,
            )
            for indices in sensitivity_draws
        ]
        policy_sensitivity[policy.name] = {
            "policy": _policy_material(policy),
            "B_COMBINED_PORTFOLIO": _summarize_paths(results, policy),
        }

    file_digests = _file_digests((baseline_root, fresh_root))
    fingerprints = _evidence_fingerprints((baseline_root, fresh_root))
    policy_material = _policy_material(PRIMARY_POLICY)
    profile_material = {profile.profile_id: _profile_material(profile) for profile in PROFILES}
    return {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "repository": "mezas3238-hue/qore-core",
        "pull_request": 528,
        "branch": "agent/vt08-r3-12-adaptive-prop-risk-001",
        "git_sha": git_sha,
        "classification": "CONSUMED-DATA RESEARCH ONLY",
        "independent_validation": False,
        "demo_eligible": False,
        "live_authorized": False,
        "holdout_not_accessed": True,
        "protected_holdout": {
            "start": PROTECTED_HOLDOUT_START.isoformat(),
            "end_exclusive": PROTECTED_HOLDOUT_END.isoformat(),
            "accessed": False,
        },
        "consumed_trade_range": {
            "first_signal": min(trade.signal_at for trade in trades).isoformat(),
            "last_exit": max(trade.exited_at for trade in trades).isoformat(),
        },
        "consumed_run_ids": [FRESH_RUN_ID, BASELINE_RUN_ID],
        "input_artifacts": {
            str(run): [{"id": artifact, "digest": digest} for artifact, digest in artifacts]
            for run, artifacts in INPUT_ARTIFACTS.items()
        },
        "input_file_sha256": file_digests,
        "input_data_digest": _canonical_digest(file_digests),
        "methodology_fingerprints": fingerprints["methodology"],
        "source_contract_fingerprints": fingerprints["source_contract"],
        "portfolio_definitions": {
            name: [list(member) for member in members] for name, members in PORTFOLIOS.items()
        },
        "primary_policy": policy_material,
        "risk_policy_fingerprint": _canonical_digest(policy_material),
        "provider_profiles": profile_material,
        "provider_profile_fingerprints": {
            name: _canonical_digest(material) for name, material in profile_material.items()
        },
        "experiment": {
            "rng": "CPython random.Random MT19937 through DeterministicRandom in R3.11 sampler",
            "rng_state_version": 3,
            "python_version": platform.python_version(),
            "seed": SEED,
            "paths": paths,
            "sensitivity_paths": len(sensitivity_draws),
            "horizon_trading_days": HORIZON_DAYS,
            "resampling": "paired moving-block bootstrap over consumed business days",
            "block_length_trading_days": BLOCK_DAYS,
            "within_block_chronology_preserved": True,
            "simultaneous_events_preserved": True,
            "primary_transaction_cost_bps_per_completed_trade": format(PRIMARY_COST_BPS, "f"),
            "cost_grid_bps": [format(value, "f") for value in COST_GRID_BPS],
            "actual_ctrader_cost_demonstrated": False,
            "swap_model": "0 USD because consumed evidence contains no realized swap series",
            "monthly_definition": (
                "21 business-day simulation months rebased to month-opening equity"
            ),
        },
        "adaptive_vs_static_reference": static_reference,
        "provider_results": provider_results,
        "cost_sensitivity_FTMO": cost_sensitivity,
        "policy_plateau_sensitivity_FTMO_B": policy_sensitivity,
    }


def write_artifacts(report: Mapping[str, object], output_dir: Path, git_sha: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "adaptive-prop-firm-monte-carlo.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    policy = {
        "primary_policy": report["primary_policy"],
        "risk_policy_fingerprint": report["risk_policy_fingerprint"],
        "provider_profiles": report["provider_profiles"],
        "provider_profile_fingerprints": report["provider_profile_fingerprints"],
        "holdout_not_accessed": True,
    }
    (output_dir / "adaptive-prop-firm-risk-policy.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    provider_results = report["provider_results"]
    if not isinstance(provider_results, Mapping):
        raise AdaptiveMonteCarloError("provider results malformed")
    ftmo = provider_results[FTMO_2STEP_2026_09_12.profile_id]
    if not isinstance(ftmo, Mapping):
        raise AdaptiveMonteCarloError("FTMO result malformed")
    ftmo_results = ftmo["results"]
    if not isinstance(ftmo_results, Mapping):
        raise AdaptiveMonteCarloError("FTMO portfolio results malformed")
    artifact_map = {
        "A-core.json": ftmo_results["A_CORE"],
        "GBPJPY-enhancer.json": ftmo_results["GBPJPY_RETURN_ENHANCER"],
        "B-combined.json": ftmo_results["B_COMBINED_PORTFOLIO"],
        "B-minus-A-marginal.json": ftmo_results["B_MINUS_A"],
    }
    for filename, payload in artifact_map.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    monthly = {
        profile_name: {
            portfolio: value["primary_0_50bp"]["monthly_growth"]
            for portfolio, value in payload["results"].items()
            if portfolio in PORTFOLIOS and isinstance(value, Mapping)
        }
        for profile_name, payload in provider_results.items()
        if isinstance(payload, Mapping)
    }
    (output_dir / "monthly-growth-distribution.json").write_text(
        json.dumps(monthly, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    breaches = {
        profile_name: {
            portfolio: {
                key: value["primary_0_50bp"][key]
                for key in (
                    "daily_loss_breach_probability",
                    "maximum_loss_breach_probability",
                    "any_prop_firm_breach_probability",
                    "account_containment_probability",
                    "internal_daily_guard_hits_total",
                    "internal_dd_throttle_hits_total",
                    "targets",
                    "median_time_to_breach_days",
                    "breach_cause_distribution",
                )
            }
            for portfolio, value in payload["results"].items()
            if portfolio in PORTFOLIOS and isinstance(value, Mapping)
        }
        for profile_name, payload in provider_results.items()
        if isinstance(payload, Mapping)
    }
    (output_dir / "prop-firm-breach-analysis.json").write_text(
        json.dumps(breaches, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "risk-policy-fingerprint.txt").write_text(
        str(report["risk_policy_fingerprint"]) + "\n", encoding="utf-8"
    )
    (output_dir / "git-sha.txt").write_text(git_sha + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--fresh-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args(argv)
    report = build_report(
        args.baseline_root,
        args.fresh_root,
        git_sha=args.git_sha,
        generated_at=args.generated_at,
    )
    write_artifacts(report, args.output_dir, args.git_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
