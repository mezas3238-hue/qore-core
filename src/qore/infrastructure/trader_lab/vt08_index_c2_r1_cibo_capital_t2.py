"""CIBO T2 budget-reactivation study for frozen VT-08 Index C2 R1 evidence."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab import vt08_index_c2_r1_cibo_capital_t1 as t1
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_c2_r1_cibo_capital_t2.v1"
CAPITAL_T2_FREEZE = "182b1418826b6d695966e36d70a7b97d9d780840"
PARENT_T1_HEAD = "0a07f6294d501613650f70fbf36e160606d62b47"
PARENT_T1_ARTIFACT_ID = 10323490893
PARENT_T1_DIGEST = (
    "sha256:e95d7744bd8fb2e7481f308792c878338e0038c569bec688a816ee175dc21491"
)
CONTROLLERS = (
    "risk_only_r100",
    "cibo_t1_absorbing_control",
    "cibo_t2_budget_reactivation",
    "cibo_t2_budget_reactivation_full_guard",
)
_EPSILON = 1e-12


class Vt08IndexCiboCapitalT2Error(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ControllerMetrics:
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
    cibo_lock_groups: int
    cibo_reactivate_groups: int
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
            "cibo_lock_groups": self.cibo_lock_groups,
            "cibo_reactivate_groups": self.cibo_reactivate_groups,
            "touched_five_percent": self.touched_five_percent,
            "touched_ten_percent": self.touched_ten_percent,
            "posture_counts": dict(self.posture_counts),
        }


def _from_t1(value: t1.SequenceMetrics) -> ControllerMetrics:
    return ControllerMetrics(
        terminal_return=value.terminal_return,
        peak_equity=value.peak_equity,
        minimum_equity=value.minimum_equity,
        maximum_capital_drawdown=value.maximum_capital_drawdown,
        maximum_daily_drawdown=value.maximum_daily_drawdown,
        generated_signals=value.generated_signals,
        executed_trades=value.executed_trades,
        risk_reduced_groups=value.risk_reduced_groups,
        risk_rejected_signals=value.risk_rejected_signals,
        bank_decisions=value.bank_decisions,
        attack_groups=value.attack_groups,
        attack_trades=value.attack_trades,
        cibo_reduce_groups=value.cibo_reduce_groups,
        cibo_suspend_groups=value.cibo_suspend_groups,
        cibo_lock_groups=0,
        cibo_reactivate_groups=0,
        touched_five_percent=value.touched_five_percent,
        touched_ten_percent=value.touched_ten_percent,
        posture_counts=value.posture_counts,
    )


def _capital_floor(peak_equity: float) -> float:
    return max(
        t1.STARTING_EQUITY * (1.0 - t1.INTERNAL_CAPITAL_LIMIT),
        peak_equity * (1.0 - t1.INTERNAL_CAPITAL_LIMIT),
    )


def _bank_reference(peak_equity: float, current_reference: float) -> float:
    if peak_equity < t1.STARTING_EQUITY * (1.0 + t1.BANK_TRIGGER):
        return current_reference
    candidate = t1.STARTING_EQUITY + t1.BANK_FRACTION * (
        peak_equity - t1.STARTING_EQUITY
    )
    return max(current_reference, candidate)


def _authorization_scale(
    *,
    signal_risk: float,
    heat_ceiling: float,
    group_size: int,
    equity: float,
    absolute_headroom: float,
) -> float:
    if group_size <= 0:
        raise Vt08IndexCiboCapitalT2Error("group_size must be positive")
    desired_total = signal_risk * group_size
    if desired_total <= 0.0:
        return 0.0
    heat_scale = min(1.0, heat_ceiling / desired_total)
    headroom_fraction = absolute_headroom / max(equity, _EPSILON)
    floor_scale = min(1.0, headroom_fraction / desired_total)
    return min(heat_scale, floor_scale)


def run_sequence_t2(
    days: Sequence[date],
    mapped: Mapping[date, Mapping[int, Sequence[t1.ObservedTrade]]],
    *,
    full_guard: bool,
) -> ControllerMetrics:
    equity = t1.STARTING_EQUITY
    peak = t1.STARTING_EQUITY
    minimum_equity = t1.STARTING_EQUITY
    bank_reference = 0.0
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
    cibo_lock_groups = 0
    cibo_reactivate_groups = 0
    touched_five_percent = False
    touched_ten_percent = False
    posture_counts: Counter[str] = Counter()
    previous_blocked = False

    for trading_day in days:
        day_start_equity = equity
        daily_floor = day_start_equity * (1.0 - t1.INTERNAL_DAILY_LIMIT)
        for anchor in sorted(mapped.get(trading_day, {})):
            group = tuple(mapped[trading_day][anchor])
            generated_signals += len(group)

            previous_bank = bank_reference
            bank_reference = _bank_reference(peak, bank_reference)
            new_bank = bank_reference > previous_bank + _EPSILON
            if new_bank:
                bank_decisions += 1

            capital_floor = _capital_floor(peak)
            daily_headroom = max(0.0, equity - daily_floor)
            capital_headroom = max(0.0, equity - capital_floor)
            absolute_headroom = min(daily_headroom, capital_headroom)

            base_scale = _authorization_scale(
                signal_risk=t1.BASE_SIGNAL_RISK,
                heat_ceiling=t1.BASE_HEAT,
                group_size=len(group),
                equity=equity,
                absolute_headroom=absolute_headroom,
            )

            if base_scale <= _EPSILON:
                if capital_headroom <= _EPSILON:
                    posture_counts["LOCK"] += 1
                    cibo_lock_groups += 1
                else:
                    posture_counts["SUSPEND"] += 1
                    cibo_suspend_groups += 1
                risk_rejected_signals += len(group)
                previous_blocked = True
                continue

            if previous_blocked:
                cibo_reactivate_groups += 1
                previous_blocked = False

            capital_drawdown_before = (peak - equity) / peak
            reduce_multiplier = (
                t1.full_guard_multiplier(capital_drawdown_before)
                if full_guard
                else 1.0
            )
            hard_cushion_fraction = absolute_headroom / max(equity, _EPSILON)
            bank_active = bank_reference > t1.STARTING_EQUITY + _EPSILON
            attack_available = (
                bank_active
                and reduce_multiplier >= 1.0 - _EPSILON
                and hard_cushion_fraction >= t1.MINIMUM_FREE_CUSHION
            )

            if full_guard and reduce_multiplier < 1.0 - _EPSILON:
                posture = "REDUCE"
                requested_signal_risk = t1.BASE_SIGNAL_RISK * reduce_multiplier
                heat_ceiling = t1.BASE_HEAT * reduce_multiplier
                cibo_reduce_groups += 1
            elif attack_available:
                posture = "ATTACK"
                requested_signal_risk = t1.ATTACK_SIGNAL_RISK
                heat_ceiling = t1.ATTACK_HEAT
                attack_groups += 1
            elif new_bank:
                posture = "BANK"
                requested_signal_risk = t1.BASE_SIGNAL_RISK
                heat_ceiling = t1.BASE_HEAT
            elif bank_active or equity > t1.STARTING_EQUITY:
                posture = "PROTECT"
                requested_signal_risk = t1.BASE_SIGNAL_RISK
                heat_ceiling = t1.BASE_HEAT
            else:
                posture = "BUILD"
                requested_signal_risk = t1.BASE_SIGNAL_RISK
                heat_ceiling = t1.BASE_HEAT
            posture_counts[posture] += 1

            risk_scale = _authorization_scale(
                signal_risk=requested_signal_risk,
                heat_ceiling=heat_ceiling,
                group_size=len(group),
                equity=equity,
                absolute_headroom=absolute_headroom,
            )
            if risk_scale <= _EPSILON:
                risk_rejected_signals += len(group)
                previous_blocked = True
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
                if posture == "ATTACK":
                    attack_trades += 1

            equity += pnl
            if equity <= 0.0 or not math.isfinite(equity):
                raise Vt08IndexCiboCapitalT2Error("equity became invalid")
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

            if daily_drawdown >= t1.PROVIDER_LIMIT - _EPSILON:
                raise Vt08IndexCiboCapitalT2Error(
                    "provider 5% daily boundary was touched"
                )
            if capital_drawdown >= t1.PROVIDER_LIMIT - _EPSILON:
                raise Vt08IndexCiboCapitalT2Error(
                    "provider 5% capital boundary was touched"
                )
            if daily_drawdown > t1.INTERNAL_DAILY_LIMIT + _EPSILON:
                raise Vt08IndexCiboCapitalT2Error(
                    "internal daily drawdown ceiling was violated"
                )
            if capital_drawdown > t1.INTERNAL_CAPITAL_LIMIT + _EPSILON:
                raise Vt08IndexCiboCapitalT2Error(
                    "internal capital drawdown ceiling was violated"
                )

    return ControllerMetrics(
        terminal_return=equity - t1.STARTING_EQUITY,
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
        cibo_lock_groups=cibo_lock_groups,
        cibo_reactivate_groups=cibo_reactivate_groups,
        touched_five_percent=touched_five_percent,
        touched_ten_percent=touched_ten_percent,
        posture_counts=tuple(sorted(posture_counts.items())),
    )


def run_controller(
    days: Sequence[date],
    mapped: Mapping[date, Mapping[int, Sequence[t1.ObservedTrade]]],
    *,
    controller: str,
) -> ControllerMetrics:
    if controller == "risk_only_r100":
        return _from_t1(t1.run_sequence(days, mapped, controller="risk_only_r100"))
    if controller == "cibo_t1_absorbing_control":
        return _from_t1(
            t1.run_sequence(
                days,
                mapped,
                controller="cibo_bank_attack_r317_transfer",
            )
        )
    if controller == "cibo_t2_budget_reactivation":
        return run_sequence_t2(days, mapped, full_guard=False)
    if controller == "cibo_t2_budget_reactivation_full_guard":
        return run_sequence_t2(days, mapped, full_guard=True)
    raise Vt08IndexCiboCapitalT2Error(f"unknown controller {controller}")


def monte_carlo_summary(
    draws: Sequence[Sequence[int]],
    calendar: Sequence[date],
    mapped: Mapping[date, Mapping[int, Sequence[t1.ObservedTrade]]],
    *,
    controller: str,
) -> dict[str, object]:
    metrics: list[ControllerMetrics] = []
    for draw in draws:
        days = tuple(calendar[index] for index in draw)
        metrics.append(run_controller(days, mapped, controller=controller))
    returns = [item.terminal_return for item in metrics]
    drawdowns = [item.maximum_capital_drawdown for item in metrics]
    daily_drawdowns = [item.maximum_daily_drawdown for item in metrics]
    return {
        "paths": len(metrics),
        "trading_days_per_path": t1.MC_TRADING_DAYS,
        "block_days": t1.MC_BLOCK_DAYS,
        "seed": t1.MC_SEED,
        "terminal_return_p05": t1.quantile(returns, 0.05),
        "terminal_return_median": t1.quantile(returns, 0.50),
        "terminal_return_mean": sum(returns) / len(returns),
        "terminal_return_p95": t1.quantile(returns, 0.95),
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
        "maximum_drawdown_median": t1.quantile(drawdowns, 0.50),
        "maximum_drawdown_p95": t1.quantile(drawdowns, 0.95),
        "maximum_drawdown_p99": t1.quantile(drawdowns, 0.99),
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
        "mean_cibo_lock_groups": sum(item.cibo_lock_groups for item in metrics)
        / len(metrics),
        "mean_cibo_reactivate_groups": sum(
            item.cibo_reactivate_groups for item in metrics
        )
        / len(metrics),
        "provider_boundary_breaches": 0,
    }


def _load_t1_reference(path: Path) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08IndexCiboCapitalT2Error("cannot read T1 reference artifact") from error
    if type(decoded) is not dict:
        raise Vt08IndexCiboCapitalT2Error("T1 reference must be an object")
    payload = cast(dict[str, object], decoded)
    if payload.get("schema") != t1.SCHEMA:
        raise Vt08IndexCiboCapitalT2Error("unexpected T1 reference schema")
    if payload.get("capital_t1_freeze") != t1.CAPITAL_T1_FREEZE:
        raise Vt08IndexCiboCapitalT2Error("T1 freeze drifted")
    if payload.get("signal_identity_sha256") != t1.PARENT_SIGNAL_IDENTITY_SHA256:
        raise Vt08IndexCiboCapitalT2Error("T1 signal identity drifted")
    return payload


def _assert_t1_reconciliation(
    report: Mapping[str, object],
    reference: Mapping[str, object],
) -> None:
    studies = cast(dict[str, object], report["studies"])
    reference_studies = cast(dict[str, object], reference["studies"])
    for policy_name in t1.STOP_POLICIES:
        ours = cast(dict[str, object], studies[policy_name])
        theirs = cast(dict[str, object], reference_studies[policy_name])
        risk_only = cast(dict[str, object], ours["risk_only_r100"])
        absorbing = cast(dict[str, object], ours["cibo_t1_absorbing_control"])
        their_risk = cast(dict[str, object], theirs["risk_only_r100"])
        their_absorbing = cast(
            dict[str, object],
            theirs["cibo_bank_attack_r317_transfer"],
        )
        for section in ("chronological", "monte_carlo_60d"):
            if risk_only[section] != their_risk[section]:
                raise Vt08IndexCiboCapitalT2Error(
                    f"T1 risk-only control drifted for {policy_name}/{section}"
                )
            absorbing_payload = cast(dict[str, object], absorbing[section])
            absorbing_legacy = {
                key: value
                for key, value in absorbing_payload.items()
                if key
                not in {
                    "cibo_lock_groups",
                    "cibo_reactivate_groups",
                    "mean_cibo_lock_groups",
                    "mean_cibo_reactivate_groups",
                }
            }
            if absorbing_legacy != their_absorbing[section]:
                raise Vt08IndexCiboCapitalT2Error(
                    f"T1 absorbing control drifted for {policy_name}/{section}"
                )


def build_report(parent_stop: Path, t1_reference: Path) -> dict[str, object]:
    policies = t1.load_parent(parent_stop)
    reference = _load_t1_reference(t1_reference)
    calendar = t1.weekday_calendar()
    draws = t1.moving_block_draws(len(calendar))
    studies: dict[str, object] = {}
    deltas: dict[str, object] = {}

    for policy_name in t1.STOP_POLICIES:
        mapped = t1.group_trades(policies[policy_name])
        controller_results: dict[str, object] = {}
        chronology: dict[str, ControllerMetrics] = {}
        monte_carlo: dict[str, dict[str, object]] = {}
        for controller in CONTROLLERS:
            chronological = run_controller(calendar, mapped, controller=controller)
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
        t1_control = chronology["cibo_t1_absorbing_control"]
        t1_control_mc = monte_carlo["cibo_t1_absorbing_control"]
        deltas[policy_name] = {
            controller: {
                "chronological_terminal_return_delta_vs_t1": (
                    chronology[controller].terminal_return
                    - t1_control.terminal_return
                ),
                "chronological_max_drawdown_delta_vs_t1": (
                    chronology[controller].maximum_capital_drawdown
                    - t1_control.maximum_capital_drawdown
                ),
                "chronological_executed_trade_delta_vs_t1": (
                    chronology[controller].executed_trades
                    - t1_control.executed_trades
                ),
                "mc_terminal_median_delta_vs_t1": (
                    cast(float, monte_carlo[controller]["terminal_return_median"])
                    - cast(float, t1_control_mc["terminal_return_median"])
                ),
                "mc_probability_positive_delta_vs_t1": (
                    cast(
                        float,
                        monte_carlo[controller]["probability_terminal_positive"],
                    )
                    - cast(
                        float,
                        t1_control_mc["probability_terminal_positive"],
                    )
                ),
            }
            for controller in CONTROLLERS
            if controller.startswith("cibo_t2_")
        }
        studies[policy_name] = controller_results

    report: dict[str, object] = {
        "schema": SCHEMA,
        "research_only": True,
        "consumed_evidence": True,
        "fresh_holdout": False,
        "capital_t2_freeze": CAPITAL_T2_FREEZE,
        "parent_t1_head": PARENT_T1_HEAD,
        "parent_t1_artifact_id": PARENT_T1_ARTIFACT_ID,
        "parent_t1_digest": PARENT_T1_DIGEST,
        "signal_count": t1.PARENT_SIGNAL_COUNT,
        "signal_identity_sha256": t1.PARENT_SIGNAL_IDENTITY_SHA256,
        "stop_policies": list(t1.STOP_POLICIES),
        "controllers": list(CONTROLLERS),
        "numerical_contract_unchanged_from_t1": True,
        "semantic_change": {
            "bank_reference_is_hard_risk_floor": False,
            "risk_daily_capital_provider_floors_are_sovereign": True,
            "attack_uses_risk_hard_cushion": True,
            "suspend_is_transient": True,
            "lock_requires_zero_capital_budget": True,
            "reactivation_requires_risk_authorizable_budget": True,
            "full_guard_reduce_precedes_attack": True,
        },
        "risk_contract": {
            "base_signal_risk": t1.BASE_SIGNAL_RISK,
            "base_heat": t1.BASE_HEAT,
            "attack_signal_risk": t1.ATTACK_SIGNAL_RISK,
            "attack_heat": t1.ATTACK_HEAT,
            "internal_daily_limit": t1.INTERNAL_DAILY_LIMIT,
            "internal_capital_limit": t1.INTERNAL_CAPITAL_LIMIT,
            "provider_boundary": t1.PROVIDER_LIMIT,
        },
        "bank_contract": {
            "profit_trigger": t1.BANK_TRIGGER,
            "bank_fraction": t1.BANK_FRACTION,
            "minimum_risk_hard_cushion_for_attack": t1.MINIMUM_FREE_CUSHION,
        },
        "full_guard_reduce_steps": [list(item) for item in t1.REDUCE_STEPS],
        "source_calendar": {
            "opened": t1.SOURCE_OPEN.isoformat(),
            "closed_exclusive": t1.SOURCE_CLOSED.isoformat(),
            "weekdays": len(calendar),
        },
        "studies": studies,
        "deltas_vs_t1_absorbing_control": deltas,
        "t1_control_reconciles_parent_exactly": True,
        "governance": {
            "owner_semantic_clarification_pre_registered": True,
            "threshold_search_performed": False,
            "trader_signal_mutation": False,
            "market_filtering_authorized": False,
            "anchor_filtering_authorized": False,
            "direction_filtering_authorized": False,
            "cibo_request_is_risk_authorization": False,
            "risk_remains_sovereign": True,
            "controller_selection_from_consumed_result_authorized": False,
            "fresh_unseen_validation_required": True,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }
    _assert_t1_reconciliation(report, reference)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-stop", type=Path, required=True)
    parser.add_argument("--t1-reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.parent_stop, args.t1_reference)
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
