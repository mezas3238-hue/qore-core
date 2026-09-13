"""Account-level CIBO capital study for frozen VT-08 Index C2 R1 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_c2_r1_cibo_capital_t1.v1"
PARENT_SCHEMA = "qore.trader_lab.vt08_index_c2_r1_cibo_stop_protection.v1"
PARENT_R1_HEAD = "5232540cdb444473ddf0bfae01beb2e672cea344"
PARENT_R1_ARTIFACT_ID = 10323025742
PARENT_CIBO_STOP_HEAD = "9c072a582d11943dc2c32c77627f1aa96ea32a52"
PARENT_CIBO_STOP_RUN_ID = 34773753125
PARENT_CIBO_STOP_ARTIFACT_ID = 10322827806
PARENT_CIBO_STOP_DIGEST = (
    "sha256:aa497744bb988ac64acd34dd9191e26d764d620ddc7c1058e6e369b4b451e707"
)
PARENT_SIGNAL_COUNT = 152
PARENT_SIGNAL_IDENTITY_SHA256 = (
    "f29bb0c1877b38f535671730c34623df9210465ae7743b640dac2c2d2c8e7d7d"
)
PARENT_STOP_FREEZE = "404b163b096b9927b145d5ea446755d50e2d99e3"
CAPITAL_T1_FREEZE = "9d9d37652555e08d6ee25ee9e7dea6eeb53cf80d"

STOP_POLICIES = (
    "off",
    "soft",
    "be050-lock050-at100",
    "aggressive",
)
CONTROLLERS = (
    "risk_only_r100",
    "cibo_bank_attack_r317_transfer",
    "cibo_full_guard_t1",
)

STARTING_EQUITY = 1.0
BASE_SIGNAL_RISK = 0.0100
BASE_HEAT = 0.0250
ATTACK_SIGNAL_RISK = 0.0200
ATTACK_HEAT = 0.0450
INTERNAL_DAILY_LIMIT = 0.0475
INTERNAL_CAPITAL_LIMIT = 0.0495
PROVIDER_LIMIT = 0.0500
BANK_TRIGGER = 0.0200
BANK_FRACTION = 0.25
MINIMUM_FREE_CUSHION = 0.0050
REDUCE_STEPS = (
    (0.0350, 0.75),
    (0.0425, 0.50),
    (0.0475, 0.25),
)
SOURCE_OPEN = date(2024, 8, 13)
SOURCE_CLOSED = date(2026, 9, 12)
MC_BLOCK_DAYS = 5
MC_TRADING_DAYS = 60
MC_PATHS = 10_000
MC_SEED = 2026091318
_EPSILON = 1e-12
_NY = ZoneInfo("America/New_York")


class Vt08IndexCiboCapitalT1Error(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ObservedTrade:
    signal_key: tuple[str, str, str]
    day: date
    anchor: int
    symbol: str
    side: str
    r_multiple: float


@dataclass(frozen=True, slots=True)
class SequenceMetrics:
    terminal_return: float
    peak_equity: float
    minimum_equity: float
    maximum_capital_drawdown: float
    maximum_daily_drawdown: float
    generated_signals: int
    executed_trades: int
    risk_reduced_groups: int
    risk_rejected_signals: int
    bank_decisions: int
    attack_groups: int
    attack_trades: int
    cibo_reduce_groups: int
    cibo_suspend_groups: int
    touched_five_percent: bool
    touched_ten_percent: bool
    posture_counts: tuple[tuple[str, int], ...]

    def payload(self) -> dict[str, object]:
        return {
            "terminal_return": self.terminal_return,
            "peak_equity": self.peak_equity,
            "minimum_equity": self.minimum_equity,
            "maximum_capital_drawdown": self.maximum_capital_drawdown,
            "maximum_daily_drawdown": self.maximum_daily_drawdown,
            "generated_signals": self.generated_signals,
            "executed_trades": self.executed_trades,
            "risk_reduced_groups": self.risk_reduced_groups,
            "risk_rejected_signals": self.risk_rejected_signals,
            "bank_decisions": self.bank_decisions,
            "attack_groups": self.attack_groups,
            "attack_trades": self.attack_trades,
            "cibo_reduce_groups": self.cibo_reduce_groups,
            "cibo_suspend_groups": self.cibo_suspend_groups,
            "touched_five_percent": self.touched_five_percent,
            "touched_ten_percent": self.touched_ten_percent,
            "posture_counts": dict(self.posture_counts),
        }


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08IndexCiboCapitalT1Error(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08IndexCiboCapitalT1Error(f"{name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise Vt08IndexCiboCapitalT1Error(f"{name} must be non-empty text")
    return value


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise Vt08IndexCiboCapitalT1Error(f"{name} must be int")
    return value


def _float(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise Vt08IndexCiboCapitalT1Error(f"{name} must be numeric")
    try:
        result = float(value)
    except ValueError as error:
        raise Vt08IndexCiboCapitalT1Error(f"{name} must be numeric") from error
    if not math.isfinite(result):
        raise Vt08IndexCiboCapitalT1Error(f"{name} must be finite")
    return result


def _timestamp(value: object, *, name: str) -> datetime:
    raw = _text(value, name=name)
    try:
        result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise Vt08IndexCiboCapitalT1Error(f"{name} must be RFC3339") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise Vt08IndexCiboCapitalT1Error(f"{name} must be timezone-aware")
    return result


def _signal_key(value: object) -> tuple[str, str, str]:
    items = _array(value, name="signal_key")
    if len(items) != 3 or any(type(item) is not str or not item for item in items):
        raise Vt08IndexCiboCapitalT1Error("signal_key must contain three strings")
    return cast(tuple[str, str, str], tuple(items))


def load_parent(path: Path) -> dict[str, tuple[ObservedTrade, ...]]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08IndexCiboCapitalT1Error("cannot read parent CIBO artifact") from error
    payload = _object(decoded, name="parent artifact")
    if payload.get("schema") != PARENT_SCHEMA:
        raise Vt08IndexCiboCapitalT1Error("unexpected parent schema")
    if payload.get("parent_r1_head") != PARENT_R1_HEAD:
        raise Vt08IndexCiboCapitalT1Error("parent R1 HEAD drifted")
    if payload.get("parent_r1_artifact_id") != PARENT_R1_ARTIFACT_ID:
        raise Vt08IndexCiboCapitalT1Error("parent R1 artifact drifted")
    if payload.get("cibo_transfer_freeze") != PARENT_STOP_FREEZE:
        raise Vt08IndexCiboCapitalT1Error("parent CIBO stop freeze drifted")
    if payload.get("signal_count") != PARENT_SIGNAL_COUNT:
        raise Vt08IndexCiboCapitalT1Error("parent signal count drifted")
    if payload.get("signal_identity_sha256") != PARENT_SIGNAL_IDENTITY_SHA256:
        raise Vt08IndexCiboCapitalT1Error("parent signal identity drifted")
    if payload.get("off_reconciles_parent_r1_exactly") is not True:
        raise Vt08IndexCiboCapitalT1Error("parent OFF control did not reconcile")
    policies = _object(payload.get("policies"), name="policies")
    if tuple(sorted(policies)) != tuple(sorted(STOP_POLICIES)):
        raise Vt08IndexCiboCapitalT1Error("parent stop-policy set drifted")

    result: dict[str, tuple[ObservedTrade, ...]] = {}
    expected_keys: tuple[tuple[str, str, str], ...] | None = None
    for policy_name in STOP_POLICIES:
        policy = _object(policies[policy_name], name=policy_name)
        if policy.get("signal_count") != PARENT_SIGNAL_COUNT:
            raise Vt08IndexCiboCapitalT1Error("policy signal count drifted")
        if policy.get("signal_identity_sha256") != PARENT_SIGNAL_IDENTITY_SHA256:
            raise Vt08IndexCiboCapitalT1Error("policy signal identity drifted")
        trades: list[ObservedTrade] = []
        for raw in _array(policy.get("trades"), name="trades"):
            item = _object(raw, name="trade")
            signal_at = _timestamp(item.get("signal_at"), name="signal_at")
            local = signal_at.astimezone(_NY)
            anchor = _integer(
                item.get("anchor_hour_new_york"),
                name="anchor_hour_new_york",
            )
            if local.hour != anchor:
                raise Vt08IndexCiboCapitalT1Error("anchor does not match signal time")
            trades.append(
                ObservedTrade(
                    signal_key=_signal_key(item.get("signal_key")),
                    day=local.date(),
                    anchor=anchor,
                    symbol=_text(item.get("symbol"), name="symbol"),
                    side=_text(item.get("side"), name="side"),
                    r_multiple=_float(item.get("r_multiple"), name="r_multiple"),
                )
            )
        ordered = tuple(sorted(trades, key=lambda item: item.signal_key))
        if len(ordered) != PARENT_SIGNAL_COUNT:
            raise Vt08IndexCiboCapitalT1Error("policy must contain exactly 152 trades")
        keys = tuple(item.signal_key for item in ordered)
        if len(set(keys)) != len(keys):
            raise Vt08IndexCiboCapitalT1Error("duplicate signal key")
        if expected_keys is None:
            expected_keys = keys
        elif keys != expected_keys:
            raise Vt08IndexCiboCapitalT1Error("signal identity differs by stop policy")
        if min(item.r_multiple for item in ordered) < -1.0 - _EPSILON:
            raise Vt08IndexCiboCapitalT1Error("observed trade exceeds frozen stop loss")
        result[policy_name] = ordered
    return result


def weekday_calendar() -> tuple[date, ...]:
    result: list[date] = []
    cursor = SOURCE_OPEN
    while cursor < SOURCE_CLOSED:
        if cursor.weekday() < 5:
            result.append(cursor)
        cursor += timedelta(days=1)
    return tuple(result)


def group_trades(
    records: Sequence[ObservedTrade],
) -> dict[date, dict[int, tuple[ObservedTrade, ...]]]:
    grouped: dict[date, dict[int, list[ObservedTrade]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in records:
        grouped[item.day][item.anchor].append(item)
    return {
        day: {
            anchor: tuple(sorted(items, key=lambda item: item.signal_key))
            for anchor, items in by_anchor.items()
        }
        for day, by_anchor in grouped.items()
    }


def _risk_floor(peak_equity: float) -> float:
    return max(
        STARTING_EQUITY * (1.0 - INTERNAL_CAPITAL_LIMIT),
        peak_equity * (1.0 - INTERNAL_CAPITAL_LIMIT),
    )


def _banked_floor(peak_equity: float, current_banked_floor: float) -> float:
    if peak_equity < STARTING_EQUITY * (1.0 + BANK_TRIGGER):
        return current_banked_floor
    candidate = STARTING_EQUITY + BANK_FRACTION * (
        peak_equity - STARTING_EQUITY
    )
    return max(current_banked_floor, candidate)


def full_guard_multiplier(capital_drawdown: float) -> float:
    if not 0.0 <= capital_drawdown <= 1.0:
        raise Vt08IndexCiboCapitalT1Error("capital drawdown must be in [0,1]")
    result = 1.0
    for threshold, multiplier in REDUCE_STEPS:
        if capital_drawdown >= threshold:
            result = min(result, multiplier)
    return result


def _controller_uses_cibo(controller: str) -> bool:
    if controller not in CONTROLLERS:
        raise Vt08IndexCiboCapitalT1Error(f"unknown controller {controller}")
    return controller != "risk_only_r100"


def run_sequence(
    days: Sequence[date],
    mapped: Mapping[date, Mapping[int, Sequence[ObservedTrade]]],
    *,
    controller: str,
) -> SequenceMetrics:
    uses_cibo = _controller_uses_cibo(controller)
    equity = STARTING_EQUITY
    peak = STARTING_EQUITY
    minimum_equity = STARTING_EQUITY
    current_banked_floor = 0.0
    maximum_capital_drawdown = 0.0
    maximum_daily_drawdown = 0.0
    generated_signals = 0
    executed_trades = 0
    risk_reduced_groups = 0
    risk_rejected_signals = 0
    bank_decisions = 0
    attack_groups = 0
    attack_trades = 0
    cibo_reduce_groups = 0
    cibo_suspend_groups = 0
    touched_five_percent = False
    touched_ten_percent = False
    posture_counts: Counter[str] = Counter()

    for trading_day in days:
        day_start_equity = equity
        daily_floor = day_start_equity * (1.0 - INTERNAL_DAILY_LIMIT)
        for anchor in sorted(mapped.get(trading_day, {})):
            group = tuple(mapped[trading_day][anchor])
            generated_signals += len(group)
            risk_floor = _risk_floor(peak)
            previous_bank = current_banked_floor
            desired_bank = (
                _banked_floor(peak, previous_bank) if uses_cibo else previous_bank
            )
            new_bank = desired_bank > previous_bank + _EPSILON
            current_banked_floor = desired_bank
            effective_floor = max(
                risk_floor,
                current_banked_floor if uses_cibo else 0.0,
            )
            free_cushion = max(0.0, equity - effective_floor)
            attack_available = (
                uses_cibo
                and current_banked_floor > STARTING_EQUITY + _EPSILON
                and free_cushion / max(equity, _EPSILON) >= MINIMUM_FREE_CUSHION
            )
            capital_drawdown_before = (peak - equity) / peak
            request_multiplier = (
                full_guard_multiplier(capital_drawdown_before)
                if controller == "cibo_full_guard_t1"
                else 1.0
            )
            daily_headroom = max(0.0, equity - daily_floor)
            capital_headroom = max(0.0, equity - effective_floor)
            absolute_headroom = min(daily_headroom, capital_headroom)

            if uses_cibo and absolute_headroom <= _EPSILON:
                posture_counts["SUSPEND"] += 1
                cibo_suspend_groups += 1
                risk_rejected_signals += len(group)
                continue

            if new_bank:
                bank_decisions += 1
            if attack_available:
                attack_groups += 1

            if controller == "cibo_full_guard_t1" and request_multiplier < 1.0:
                posture_counts["REDUCE"] += 1
                cibo_reduce_groups += 1
            elif attack_available:
                posture_counts["ATTACK"] += 1
            elif new_bank:
                posture_counts["BANK"] += 1
            elif uses_cibo and equity > STARTING_EQUITY:
                posture_counts["PROTECT"] += 1
            elif uses_cibo:
                posture_counts["BUILD"] += 1
            else:
                posture_counts["RISK_ONLY"] += 1

            requested_signal_risk = (
                ATTACK_SIGNAL_RISK if attack_available else BASE_SIGNAL_RISK
            ) * request_multiplier
            heat_ceiling = (
                ATTACK_HEAT if attack_available else BASE_HEAT
            ) * request_multiplier
            desired_total = requested_signal_risk * len(group)
            heat_scale = (
                1.0
                if desired_total <= heat_ceiling or desired_total == 0.0
                else heat_ceiling / desired_total
            )
            worst_case_total = desired_total
            headroom_fraction = absolute_headroom / max(equity, _EPSILON)
            floor_scale = (
                1.0
                if worst_case_total <= headroom_fraction or worst_case_total == 0.0
                else headroom_fraction / worst_case_total
            )
            risk_scale = min(heat_scale, floor_scale)
            if risk_scale <= _EPSILON:
                risk_rejected_signals += len(group)
                continue
            if risk_scale < 1.0 - _EPSILON:
                risk_reduced_groups += 1

            pnl = 0.0
            for trade in group:
                authorized_risk = requested_signal_risk * risk_scale
                if authorized_risk <= _EPSILON:
                    risk_rejected_signals += 1
                    continue
                pnl += equity * authorized_risk * trade.r_multiple
                executed_trades += 1
                if attack_available:
                    attack_trades += 1

            equity += pnl
            if equity <= 0.0 or not math.isfinite(equity):
                raise Vt08IndexCiboCapitalT1Error("equity became invalid")
            peak = max(peak, equity)
            minimum_equity = min(minimum_equity, equity)
            capital_drawdown = (peak - equity) / peak
            daily_drawdown = max(0.0, (day_start_equity - equity) / day_start_equity)
            maximum_capital_drawdown = max(
                maximum_capital_drawdown,
                capital_drawdown,
            )
            maximum_daily_drawdown = max(maximum_daily_drawdown, daily_drawdown)
            touched_five_percent = touched_five_percent or peak >= 1.05
            touched_ten_percent = touched_ten_percent or peak >= 1.10

            if daily_drawdown >= PROVIDER_LIMIT - _EPSILON:
                raise Vt08IndexCiboCapitalT1Error(
                    "provider 5% daily boundary was touched"
                )
            if capital_drawdown >= PROVIDER_LIMIT - _EPSILON:
                raise Vt08IndexCiboCapitalT1Error(
                    "provider 5% capital boundary was touched"
                )
            if daily_drawdown > INTERNAL_DAILY_LIMIT + _EPSILON:
                raise Vt08IndexCiboCapitalT1Error(
                    "internal daily drawdown ceiling was violated"
                )
            if capital_drawdown > INTERNAL_CAPITAL_LIMIT + _EPSILON:
                raise Vt08IndexCiboCapitalT1Error(
                    "internal capital drawdown ceiling was violated"
                )

    return SequenceMetrics(
        terminal_return=equity - STARTING_EQUITY,
        peak_equity=peak,
        minimum_equity=minimum_equity,
        maximum_capital_drawdown=maximum_capital_drawdown,
        maximum_daily_drawdown=maximum_daily_drawdown,
        generated_signals=generated_signals,
        executed_trades=executed_trades,
        risk_reduced_groups=risk_reduced_groups,
        risk_rejected_signals=risk_rejected_signals,
        bank_decisions=bank_decisions,
        attack_groups=attack_groups,
        attack_trades=attack_trades,
        cibo_reduce_groups=cibo_reduce_groups,
        cibo_suspend_groups=cibo_suspend_groups,
        touched_five_percent=touched_five_percent,
        touched_ten_percent=touched_ten_percent,
        posture_counts=tuple(sorted(posture_counts.items())),
    )


def _deterministic_start(seed: int, counter: int, max_start: int) -> int:
    if max_start < 0:
        raise Vt08IndexCiboCapitalT1Error("max_start cannot be negative")
    digest = hashlib.sha256(f"{seed}:{counter}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % (max_start + 1)


def moving_block_draws(day_count: int) -> tuple[tuple[int, ...], ...]:
    if day_count < MC_BLOCK_DAYS:
        raise Vt08IndexCiboCapitalT1Error("source calendar is too short")
    result: list[tuple[int, ...]] = []
    max_start = day_count - MC_BLOCK_DAYS
    counter = 0
    for _ in range(MC_PATHS):
        indices: list[int] = []
        while len(indices) < MC_TRADING_DAYS:
            start = _deterministic_start(MC_SEED, counter, max_start)
            counter += 1
            indices.extend(range(start, start + MC_BLOCK_DAYS))
        result.append(tuple(indices[:MC_TRADING_DAYS]))
    return tuple(result)


def quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise Vt08IndexCiboCapitalT1Error("quantile requires values")
    if not 0.0 <= probability <= 1.0:
        raise Vt08IndexCiboCapitalT1Error("probability must be in [0,1]")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def monte_carlo_summary(
    draws: Sequence[Sequence[int]],
    calendar: Sequence[date],
    mapped: Mapping[date, Mapping[int, Sequence[ObservedTrade]]],
    *,
    controller: str,
) -> dict[str, object]:
    metrics: list[SequenceMetrics] = []
    for draw in draws:
        days = tuple(calendar[index] for index in draw)
        metrics.append(run_sequence(days, mapped, controller=controller))
    returns = [item.terminal_return for item in metrics]
    drawdowns = [item.maximum_capital_drawdown for item in metrics]
    daily_drawdowns = [item.maximum_daily_drawdown for item in metrics]
    return {
        "paths": len(metrics),
        "trading_days_per_path": MC_TRADING_DAYS,
        "block_days": MC_BLOCK_DAYS,
        "seed": MC_SEED,
        "terminal_return_p05": quantile(returns, 0.05),
        "terminal_return_median": quantile(returns, 0.50),
        "terminal_return_mean": sum(returns) / len(returns),
        "terminal_return_p95": quantile(returns, 0.95),
        "probability_terminal_positive": sum(value > 0.0 for value in returns)
        / len(returns),
        "probability_touch_five_percent": sum(
            item.touched_five_percent for item in metrics
        )
        / len(metrics),
        "probability_touch_ten_percent": sum(
            item.touched_ten_percent for item in metrics
        )
        / len(metrics),
        "maximum_drawdown_median": quantile(drawdowns, 0.50),
        "maximum_drawdown_p95": quantile(drawdowns, 0.95),
        "maximum_drawdown_p99": quantile(drawdowns, 0.99),
        "maximum_observed_capital_drawdown": max(drawdowns),
        "maximum_observed_daily_drawdown": max(daily_drawdowns),
        "mean_executed_trades": sum(item.executed_trades for item in metrics)
        / len(metrics),
        "mean_risk_rejected_signals": sum(
            item.risk_rejected_signals for item in metrics
        )
        / len(metrics),
        "mean_risk_reduced_groups": sum(
            item.risk_reduced_groups for item in metrics
        )
        / len(metrics),
        "mean_bank_decisions": sum(item.bank_decisions for item in metrics)
        / len(metrics),
        "probability_attack_activation": sum(
            item.attack_groups > 0 for item in metrics
        )
        / len(metrics),
        "mean_attack_trades": sum(item.attack_trades for item in metrics)
        / len(metrics),
        "mean_cibo_reduce_groups": sum(
            item.cibo_reduce_groups for item in metrics
        )
        / len(metrics),
        "mean_cibo_suspend_groups": sum(
            item.cibo_suspend_groups for item in metrics
        )
        / len(metrics),
        "provider_boundary_breaches": 0,
    }


def build_report(path: Path) -> dict[str, object]:
    policies = load_parent(path)
    calendar = weekday_calendar()
    draws = moving_block_draws(len(calendar))
    studies: dict[str, object] = {}
    deltas: dict[str, object] = {}

    for policy_name in STOP_POLICIES:
        mapped = group_trades(policies[policy_name])
        controller_results: dict[str, object] = {}
        chronology: dict[str, SequenceMetrics] = {}
        monte_carlo: dict[str, dict[str, object]] = {}
        for controller in CONTROLLERS:
            chronological = run_sequence(calendar, mapped, controller=controller)
            mc = monte_carlo_summary(
                draws,
                calendar,
                mapped,
                controller=controller,
            )
            chronology[controller] = chronological
            monte_carlo[controller] = mc
            controller_results[controller] = {
                "chronological": chronological.payload(),
                "monte_carlo_60d": mc,
            }
        baseline = chronology["risk_only_r100"]
        baseline_mc = monte_carlo["risk_only_r100"]
        deltas[policy_name] = {
            controller: {
                "chronological_terminal_return_delta": (
                    chronology[controller].terminal_return
                    - baseline.terminal_return
                ),
                "chronological_max_drawdown_delta": (
                    chronology[controller].maximum_capital_drawdown
                    - baseline.maximum_capital_drawdown
                ),
                "mc_terminal_median_delta": (
                    cast(float, monte_carlo[controller]["terminal_return_median"])
                    - cast(float, baseline_mc["terminal_return_median"])
                ),
                "mc_probability_positive_delta": (
                    cast(
                        float,
                        monte_carlo[controller]["probability_terminal_positive"],
                    )
                    - cast(float, baseline_mc["probability_terminal_positive"])
                ),
            }
            for controller in CONTROLLERS
            if controller != "risk_only_r100"
        }
        studies[policy_name] = controller_results

    return {
        "schema": SCHEMA,
        "research_only": True,
        "consumed_evidence": True,
        "fresh_holdout": False,
        "capital_t1_freeze": CAPITAL_T1_FREEZE,
        "parent_r1_head": PARENT_R1_HEAD,
        "parent_r1_artifact_id": PARENT_R1_ARTIFACT_ID,
        "parent_cibo_stop_head": PARENT_CIBO_STOP_HEAD,
        "parent_cibo_stop_run_id": PARENT_CIBO_STOP_RUN_ID,
        "parent_cibo_stop_artifact_id": PARENT_CIBO_STOP_ARTIFACT_ID,
        "parent_cibo_stop_digest": PARENT_CIBO_STOP_DIGEST,
        "signal_count": PARENT_SIGNAL_COUNT,
        "signal_identity_sha256": PARENT_SIGNAL_IDENTITY_SHA256,
        "stop_policies": list(STOP_POLICIES),
        "controllers": list(CONTROLLERS),
        "risk_contract": {
            "base_signal_risk": BASE_SIGNAL_RISK,
            "base_heat": BASE_HEAT,
            "attack_signal_risk": ATTACK_SIGNAL_RISK,
            "attack_heat": ATTACK_HEAT,
            "internal_daily_limit": INTERNAL_DAILY_LIMIT,
            "internal_capital_limit": INTERNAL_CAPITAL_LIMIT,
            "provider_boundary": PROVIDER_LIMIT,
        },
        "bank_contract": {
            "profit_trigger": BANK_TRIGGER,
            "bank_fraction": BANK_FRACTION,
            "minimum_free_cushion": MINIMUM_FREE_CUSHION,
        },
        "full_guard_reduce_steps": [list(item) for item in REDUCE_STEPS],
        "source_calendar": {
            "opened": SOURCE_OPEN.isoformat(),
            "closed_exclusive": SOURCE_CLOSED.isoformat(),
            "weekdays": len(calendar),
        },
        "studies": studies,
        "deltas_vs_same_stop_risk_only": deltas,
        "governance": {
            "trader_signal_mutation": False,
            "market_filtering_authorized": False,
            "anchor_filtering_authorized": False,
            "direction_filtering_authorized": False,
            "stop_policy_selection_from_consumed_result_authorized": False,
            "capital_controller_selection_from_consumed_result_authorized": False,
            "cibo_request_is_risk_authorization": False,
            "risk_remains_sovereign": True,
            "fresh_unseen_validation_required": True,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.input)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        report,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    args.out.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
