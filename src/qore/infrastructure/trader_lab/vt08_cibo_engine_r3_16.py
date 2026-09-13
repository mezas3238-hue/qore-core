"""Risk-sovereign account simulation engine for VT-08 R3.16."""
from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from qore.infrastructure.trader_lab.vt08_cibo_data_r3_16 import (
    CiboCapitalProtectionError,
    ReplayTrade,
    portfolio_record,
)

HARD_DRAWDOWN = 0.05
PHASE_DAYS = 30
TOTAL_CHALLENGE_DAYS = 60
BLOCK_DAYS = 5
SEARCH_PATHS = 2_500
FINAL_PATHS = 10_000
SEED = 2026091304
PRIMARY_PHASE1_TARGET = 0.10
PRIMARY_PHASE2_TARGET = 0.05
SENSITIVITY_PHASE1_TARGET = 0.11
SENSITIVITY_PHASE2_TARGET = 0.06


@dataclass(frozen=True, slots=True)
class RiskLevel:
    name: str
    a_risk: float
    gbpjpy_risk: float
    heat: float


RISK_LEVELS = (
    RiskLevel("r075", 0.0075, 0.0060, 0.0200),
    RiskLevel("r100", 0.0100, 0.0080, 0.0250),
    RiskLevel("r125", 0.0125, 0.0100, 0.0300),
    RiskLevel("r150", 0.0150, 0.0120, 0.0350),
    RiskLevel("r200", 0.0200, 0.0150, 0.0450),
    RiskLevel("r225", 0.0225, 0.0170, 0.0500),
    RiskLevel("r250", 0.0250, 0.0190, 0.0550),
)


@dataclass(frozen=True, slots=True)
class CapitalGuard:
    name: str
    bank_fraction: float
    drawdown_steps: tuple[tuple[float, float], ...]
    target_progress_steps: tuple[tuple[float, float], ...]


CAPITAL_GUARDS = (
    CapitalGuard("hard5-only", 0.0, (), ()),
    CapitalGuard(
        "target-late",
        0.0,
        (),
        ((0.70, 0.85), (0.85, 0.60), (0.95, 0.30)),
    ),
    CapitalGuard(
        "bank50-late",
        0.50,
        (),
        ((0.70, 0.85), (0.85, 0.60), (0.95, 0.30)),
    ),
    CapitalGuard(
        "bank50-ddlate",
        0.50,
        ((0.035, 0.75), (0.0425, 0.50), (0.0475, 0.25)),
        ((0.70, 0.85), (0.85, 0.60), (0.95, 0.30)),
    ),
)


@dataclass(frozen=True, slots=True)
class SequenceMetrics:
    success: bool
    completion_day: int | None
    terminal_return: float
    maximum_drawdown: float
    generated_signals: int
    executed_trades: int
    risk_lockouts: int
    cibo_protected_exits: int
    full_stop_losses: int


def day_map(
    records: Sequence[ReplayTrade],
    portfolio: str,
) -> dict[date, dict[int, list[ReplayTrade]]]:
    result: dict[date, dict[int, list[ReplayTrade]]] = defaultdict(lambda: defaultdict(list))
    for item in records:
        if portfolio_record(item, portfolio):
            result[item.day][item.anchor].append(item)
    return result


def weekdays(opened: date, closed: date) -> list[date]:
    result: list[date] = []
    cursor = opened
    while cursor < closed:
        if cursor.weekday() < 5:
            result.append(cursor)
        cursor += timedelta(days=1)
    return result


def _guard_multiplier(
    *,
    equity: float,
    peak: float,
    target: float | None,
    guard: CapitalGuard,
) -> float:
    result = 1.0
    drawdown = (peak - equity) / peak if peak > 0 else 1.0
    for threshold, multiplier in guard.drawdown_steps:
        if drawdown >= threshold:
            result = min(result, multiplier)
    if target is not None and target > 0:
        progress = (equity - 1.0) / target
        for threshold, multiplier in guard.target_progress_steps:
            if progress >= threshold:
                result = min(result, multiplier)
    return result


def capital_floor(*, peak: float, guard: CapitalGuard) -> float:
    hard_floor = max(1.0 - HARD_DRAWDOWN, peak * (1.0 - HARD_DRAWDOWN))
    if peak <= 1.0 or guard.bank_fraction <= 0:
        return hard_floor
    return max(hard_floor, 1.0 + guard.bank_fraction * (peak - 1.0))


def run_sequence(
    days: Sequence[date],
    mapped: Mapping[date, Mapping[int, Sequence[ReplayTrade]]],
    *,
    risk: RiskLevel,
    guard: CapitalGuard,
    target: float | None,
    stop_on_target: bool,
) -> SequenceMetrics:
    equity = 1.0
    peak = 1.0
    maximum_drawdown = 0.0
    generated = 0
    executed = 0
    lockouts = 0
    protected = 0
    full_stops = 0
    for day_number, trading_day in enumerate(days, start=1):
        for anchor in sorted(mapped.get(trading_day, {})):
            group = list(mapped[trading_day][anchor])
            generated += len(group)
            multiplier = _guard_multiplier(
                equity=equity,
                peak=peak,
                target=target,
                guard=guard,
            )
            desired = [
                (risk.gbpjpy_risk if item.sleeve == "G" else risk.a_risk) * multiplier
                for item in group
            ]
            floor = capital_floor(peak=peak, guard=guard)
            headroom = max(0.0, (equity - floor) / equity) if equity > 0 else 0.0
            worst = [
                amount * (1.0 + max(0.0, item.gross_r - item.net_r))
                for amount, item in zip(desired, group, strict=True)
            ]
            desired_total = sum(desired)
            worst_total = sum(worst)
            heat_cap = risk.heat * multiplier
            heat_scale = (
                1.0
                if desired_total <= heat_cap or desired_total == 0
                else heat_cap / desired_total
            )
            floor_scale = (
                1.0
                if worst_total <= headroom or worst_total == 0
                else headroom / worst_total
            )
            scale = min(heat_scale, floor_scale)
            if scale <= 1e-12:
                lockouts += len(group)
                continue
            pnl = 0.0
            for amount, item in zip(desired, group, strict=True):
                allocated = amount * scale
                if allocated <= 1e-12:
                    lockouts += 1
                    continue
                pnl += equity * allocated * item.net_r
                executed += 1
                protected += int(item.exit_reason == "cibo_protected_stop")
                full_stops += int(item.net_r <= -1.0)
            equity += pnl
            peak = max(peak, equity)
            maximum_drawdown = max(maximum_drawdown, (peak - equity) / peak)
            if maximum_drawdown > HARD_DRAWDOWN + 1e-9:
                raise CiboCapitalProtectionError("5% hard drawdown invariant was violated")
            if target is not None and stop_on_target and equity >= 1.0 + target:
                return SequenceMetrics(
                    True,
                    day_number,
                    equity - 1.0,
                    maximum_drawdown,
                    generated,
                    executed,
                    lockouts,
                    protected,
                    full_stops,
                )
    return SequenceMetrics(
        target is not None and equity >= 1.0 + target,
        None,
        equity - 1.0,
        maximum_drawdown,
        generated,
        executed,
        lockouts,
        protected,
        full_stops,
    )


def moving_block_draws(day_count: int, *, paths: int) -> list[list[int]]:
    if day_count < BLOCK_DAYS:
        raise CiboCapitalProtectionError("challenge evidence has too few trading days")
    rng = random.Random(SEED)
    result: list[list[int]] = []
    max_start = day_count - BLOCK_DAYS
    for _ in range(paths):
        indices: list[int] = []
        while len(indices) < TOTAL_CHALLENGE_DAYS:
            start = rng.randint(0, max_start)
            indices.extend(range(start, start + BLOCK_DAYS))
        result.append(indices[:TOTAL_CHALLENGE_DAYS])
    return result


def quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise CiboCapitalProtectionError("quantile requires observations")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight
