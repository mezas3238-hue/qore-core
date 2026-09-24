"""VT31 Shared causal prearmed protection laboratory V26.

V25 proved a hard observability floor: 48 R8 losses and 60 R6 losses terminate
before any closed-M1 post-fill Journey snapshot exists. Even an impossible
oracle that deletes every observable loss cannot reach the Owner DD <= 6R gate.

V26 tests the necessary architectural consequence without changing density:
Shared carries causal market context into the fill and may advise a tighter
protective journey stop immediately after fill. Every methodology-valid entry is
still taken. No sizing, capital weighting, entry abstention, future M1, realized
trade outcome, prior PnL or loss streak is a runtime input.

The stop change is a counterfactual consumer action in the laboratory. Shared
itself retains zero stop/order/risk/execution authority. Intrabar ambiguity is
resolved conservatively stop-first.

R8/R6 are consumed research folds. R5 and fresh holdouts remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_persistent_preentry_context_journey_v24 as v24

from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentObservation,
    MarketEnvironmentState,
    assess_market_environment,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryState,
    MarketTransitionObservation,
    assess_market_trajectory,
)

SCHEMA = "qore.core_stack_v4.vt31.causal_prearmed_protection.v26"
IDENTITY = "VT31_NAS100_SHARED_CAUSAL_PREARMED_PROTECTION_V26"
ZERO = Decimal("0")
ONE = Decimal("1")
FRICTION = Decimal("0.05")
DD_ACCEPTABLE_MAX_R = Decimal("6")
DD_EXCEPTIONAL_R = Decimal("4")
TRAJECTORY_WINDOW = v24.TRAJECTORY_WINDOW
ENVIRONMENT_WINDOW = v24.ENVIRONMENT_WINDOW
PREENTRY_BARS = v24.PREENTRY_BARS
v23 = v24.v23
v18 = v24.v18


ADVERSE_TRAJECTORIES = frozenset(
    {
        MarketTrajectoryState.WEAKENING,
        MarketTrajectoryState.DIVERGING,
        MarketTrajectoryState.DETERIORATING,
        MarketTrajectoryState.FAILURE,
    }
)
SEVERE_TRAJECTORIES = frozenset(
    {
        MarketTrajectoryState.DETERIORATING,
        MarketTrajectoryState.FAILURE,
    }
)


@dataclass(frozen=True, slots=True)
class PrearmPolicy:
    name: str
    mode: str

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "mode": self.mode,
            "entry_abstention_allowed": False,
            "density_preserved": True,
            "consumer_stop_can_only_improve": True,
            "shared_stop_authority": False,
            "numeric_threshold_grid_search": False,
        }


POLICIES = (
    PrearmPolicy("CONTEXT_GRADED_PROTECTION", "CONTEXT_GRADED"),
    PrearmPolicy("FRAGILE_ADVERSE_HALF_RISK", "FRAGILE_ADVERSE_HALF"),
    PrearmPolicy("FRAGILE_ADVERSE_QUARTER_RISK", "FRAGILE_ADVERSE_QUARTER"),
    PrearmPolicy("SEVERE_TRAJECTORY_HALF_RISK", "SEVERE_TRAJECTORY_HALF"),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _entry_context(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    fill_index: int,
    sp_by_day: object,
    us_by_day: object,
) -> dict[str, object]:
    side = cast(str, row["side"])
    local_day = date.fromisoformat(cast(str, row["local_date"]))
    start = max(0, fill_index - PREENTRY_BARS)
    transitions: list[MarketTransitionObservation] = []
    environments: list[MarketEnvironmentObservation] = []
    trajectory_states: list[str] = []
    latest_trajectory = None
    latest_environment = None

    for index in range(start, fill_index):
        bar = day_bars[index]
        as_of = cast(object, bar).closed_at
        nas = tuple(day_bars[: index + 1])
        sp = tuple(v18.v13._eligible(sp_by_day, local_day, as_of))
        us = tuple(v18.v13._eligible(us_by_day, local_day, as_of))
        observation = v24._market_transition_observation(
            as_of=as_of,
            side=side,
            nas=nas,
            sp=sp,
            us=us,
        )
        transitions.append(observation)
        latest_trajectory = assess_market_trajectory(
            tuple(transitions[-TRAJECTORY_WINDOW:])
        )
        trajectory_states.append(latest_trajectory.state.value)
        environments.append(
            v24._environment_observation(observation, latest_trajectory)
        )
        latest_environment = assess_market_environment(
            tuple(environments[-ENVIRONMENT_WINDOW:])
        )

    if latest_trajectory is None or latest_environment is None:
        raise AssertionError("missing causal pre-entry context")

    return {
        "trajectory_state": latest_trajectory.state.value,
        "trajectory_support_bps": latest_trajectory.support_bps,
        "trajectory_adversity_bps": latest_trajectory.adversity_bps,
        "trajectory_deterioration_velocity_bps": (
            latest_trajectory.deterioration_velocity_bps
        ),
        "trajectory_deterioration_persistence_bps": (
            latest_trajectory.deterioration_persistence_bps
        ),
        "trajectory_history": tuple(trajectory_states[-TRAJECTORY_WINDOW:]),
        "environment_state": latest_environment.state.value,
        "environment_support_bps": latest_environment.market_support_bps,
        "environment_adverse_bps": latest_environment.adverse_environment_bps,
        "environment_adverse_persistence_bps": (
            latest_environment.adverse_persistence_bps
        ),
        "cross_market_fragility_bps": latest_environment.cross_market_fragility_bps,
        "structural_fragility_bps": latest_environment.structural_fragility_bps,
        "preentry_observation_count": len(transitions),
    }


def _protection_fraction(
    context: dict[str, object],
    policy: PrearmPolicy,
) -> Decimal | None:
    environment = MarketEnvironmentState(str(context["environment_state"]))
    trajectory = MarketTrajectoryState(str(context["trajectory_state"]))
    fragile_or_worse = environment in {
        MarketEnvironmentState.FRAGILE,
        MarketEnvironmentState.DEGRADING,
        MarketEnvironmentState.ADVERSE_FORMING,
        MarketEnvironmentState.DEFENSIVE,
    }

    if policy.mode == "CONTEXT_GRADED":
        if environment in {
            MarketEnvironmentState.ADVERSE_FORMING,
            MarketEnvironmentState.DEFENSIVE,
        }:
            return Decimal("0.25")
        if environment is MarketEnvironmentState.DEGRADING:
            return Decimal("0.50")
        if environment is MarketEnvironmentState.FRAGILE and trajectory in ADVERSE_TRAJECTORIES:
            return Decimal("0.75")
        return None

    if policy.mode == "FRAGILE_ADVERSE_HALF":
        if fragile_or_worse and trajectory in ADVERSE_TRAJECTORIES:
            return Decimal("0.50")
        return None

    if policy.mode == "FRAGILE_ADVERSE_QUARTER":
        if fragile_or_worse and trajectory in ADVERSE_TRAJECTORIES:
            return Decimal("0.25")
        return None

    if policy.mode == "SEVERE_TRAJECTORY_HALF":
        if trajectory in SEVERE_TRAJECTORIES and environment not in {
            MarketEnvironmentState.RESTORED,
            MarketEnvironmentState.SUPPORTIVE,
        }:
            return Decimal("0.50")
        return None

    raise ValueError(f"unknown prearm policy mode: {policy.mode}")


def _simulate_prearmed(
    *,
    setup: object,
    day_bars: tuple[object, ...],
    row: dict[str, object],
    protective_fraction: Decimal,
) -> dict[str, object]:
    if not ZERO < protective_fraction < ONE:
        raise ValueError("protective fraction must improve the original stop")

    fill_index, _ = v18.counter._fill_and_exit_indices(setup, day_bars, row)
    side = cast(object, setup).side.value
    sign = v18.journey._side_sign(side)
    entry = cast(object, setup).entry_price
    risk = cast(object, setup).initial_risk
    target = cast(object, setup).target_price
    three_r = cast(object, setup).three_r_price
    protective_stop = entry - sign * risk * protective_fraction
    current_stop = protective_stop
    be_armed = False

    def terminal(value: Decimal, reason: str, bar_offset: int) -> dict[str, object]:
        return {
            "net_r_after_friction": format(value - FRICTION, "f"),
            "gross_r": format(value, "f"),
            "exit_reason": reason,
            "exit_bar_offset": bar_offset,
            "protective_fraction_r": format(protective_fraction, "f"),
        }

    for index in range(fill_index, len(day_bars)):
        bar = day_bars[index]
        if v18.journey._local_minute(bar) >= v18.journey.LIFECYCLE_MINUTE:
            break
        _, high, low, _ = v18.journey._bar_values(bar)

        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= target if side == "long" else low <= target

        # Conservative OHLC ordering. On the fill bar, a tighter prearmed stop
        # may have been touched after entry; ambiguity is charged as a stop.
        if hit_stop and hit_target:
            return terminal(
                sign * (current_stop - entry) / risk,
                "PREARM_STOP_FIRST_AMBIGUITY",
                index - fill_index,
            )
        if hit_stop:
            return terminal(
                sign * (current_stop - entry) / risk,
                "PREARM_PROTECTIVE_STOP"
                if current_stop != entry
                else "PREARM_BREAKEVEN_STOP",
                index - fill_index,
            )
        if hit_target:
            return terminal(
                abs(target - entry) / risk,
                "PREARM_ORIGINAL_TARGET",
                index - fill_index,
            )

        if not be_armed:
            touched_three_r = high >= three_r if side == "long" else low <= three_r
            if touched_three_r:
                be_armed = True
                current_stop = entry

    eligible = [
        bar
        for bar in day_bars[fill_index:]
        if v18.journey._local_minute(bar) < v18.journey.LIFECYCLE_MINUTE
    ]
    if not eligible:
        raise AssertionError("missing lifecycle bar")
    close = v18.journey._bar_values(eligible[-1])[3]
    return terminal(
        sign * (close - entry) / risk,
        "PREARM_LIFECYCLE",
        len(eligible) - 1,
    )


def _prepare(
    rows: list[dict[str, object]],
    *,
    nas_evidence: Path,
    sp_evidence: Path,
    us_evidence: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    paths = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        v18.journey._reconstruct_partition(nas_evidence),
    )
    sp_by_day = v18.v13._group_market(sp_evidence)
    us_by_day = v18.v13._group_market(us_evidence)

    prepared: list[dict[str, object]] = []
    environment_histogram: Counter[str] = Counter()
    trajectory_histogram: Counter[str] = Counter()
    outcome_atlas: Counter[str] = Counter()
    unobservable_atlas: Counter[str] = Counter()

    full = v23._prepare_full_universe(
        rows,
        nas_evidence=nas_evidence,
        sp_evidence=sp_evidence,
        us_evidence=us_evidence,
    )

    for item in full:
        row = cast(dict[str, object], item["row"])
        signal = cast(str, row["signal_at"])
        setup, day_bars = paths[signal]
        fill_index, _ = v18.counter._fill_and_exit_indices(setup, day_bars, row)
        context = _entry_context(
            row=row,
            setup=setup,
            day_bars=day_bars,
            fill_index=fill_index,
            sp_by_day=sp_by_day,
            us_by_day=us_by_day,
        )
        env = str(context["environment_state"])
        trajectory = str(context["trajectory_state"])
        environment_histogram[env] += 1
        trajectory_histogram[trajectory] += 1

        baseline_r = cast(Decimal, item["baseline_r"])
        outcome = "LOSS" if baseline_r < ZERO else "WIN" if baseline_r > ZERO else "FLAT"
        key = f"{env}|{trajectory}|{outcome}"
        outcome_atlas[key] += 1
        if not cast(list[dict[str, object]], item["events"]):
            unobservable_atlas[key] += 1

        prepared.append(
            {
                **item,
                "setup": setup,
                "day_bars": day_bars,
                "entry_context": context,
            }
        )

    return prepared, {
        "entry_environment_histogram": dict(sorted(environment_histogram.items())),
        "entry_trajectory_histogram": dict(sorted(trajectory_histogram.items())),
        "offline_outcome_atlas_evaluation_only": dict(sorted(outcome_atlas.items())),
        "offline_unobservable_atlas_evaluation_only": dict(
            sorted(unobservable_atlas.items())
        ),
        "runtime_outcome_used_for_context": False,
        "preentry_bars": PREENTRY_BARS,
    }


def _metrics(values: list[Decimal]) -> dict[str, object]:
    return v23._metrics(values)


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    policy: PrearmPolicy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    actions: list[dict[str, object]] = []

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        baseline_values.append(baseline_r)
        context = cast(dict[str, object], item["entry_context"])
        fraction = _protection_fraction(context, policy)

        if fraction is None:
            shared_r = baseline_r
        else:
            result = _simulate_prearmed(
                setup=item["setup"],
                day_bars=cast(tuple[object, ...], item["day_bars"]),
                row=row,
                protective_fraction=fraction,
            )
            shared_r = _d(result["net_r_after_friction"])
            actions.append(
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": format(baseline_r, "f"),
                    "shared_r": format(shared_r, "f"),
                    "uplift_r": format(shared_r - baseline_r, "f"),
                    "baseline_observable_postfill": bool(
                        cast(list[dict[str, object]], item["events"])
                    ),
                    "entry_context": context,
                    **result,
                }
            )
        shared_values.append(shared_r)

    baseline = _metrics(baseline_values)
    shared = _metrics(shared_values)
    acted_losses = [x for x in actions if _d(x["baseline_r"]) < ZERO]
    acted_winners = [x for x in actions if _d(x["baseline_r"]) > ZERO]
    improved_losses = [
        x for x in acted_losses if _d(x["shared_r"]) > _d(x["baseline_r"])
    ]
    damaged_winners = [
        x for x in acted_winners if _d(x["shared_r"]) < _d(x["baseline_r"])
    ]
    unobservable_losses_protected = [
        x
        for x in improved_losses
        if not bool(x["baseline_observable_postfill"])
    ]
    baseline_winner_r = _d(baseline["gross_winner_r"])
    shared_winner_r = _d(shared["gross_winner_r"])
    winner_r_retention = (
        ONE if baseline_winner_r == ZERO else shared_winner_r / baseline_winner_r
    )
    base_losses = int(baseline["losses"])

    return {
        "baseline": baseline,
        "shared_v26": shared,
        "density": {
            "input": len(baseline_values),
            "kept": len(shared_values),
            "retained": "1",
            "entry_abstentions": 0,
        },
        "prearm": {
            "actions": len(actions),
            "acted_baseline_losses": len(acted_losses),
            "acted_baseline_winners": len(acted_winners),
            "improved_losses": len(improved_losses),
            "damaged_winners": len(damaged_winners),
            "baseline_loss_coverage": (
                "0"
                if base_losses == 0
                else format(Decimal(len(acted_losses)) / Decimal(base_losses), "f")
            ),
            "unobservable_losses_protected": len(unobservable_losses_protected),
            "loser_uplift_r": format(
                sum(
                    (
                        _d(x["shared_r"]) - _d(x["baseline_r"])
                        for x in acted_losses
                    ),
                    ZERO,
                ),
                "f",
            ),
            "winner_damage_r": format(
                -min(
                    ZERO,
                    sum(
                        (
                            _d(x["shared_r"]) - _d(x["baseline_r"])
                            for x in acted_winners
                        ),
                        ZERO,
                    ),
                ),
                "f",
            ),
            "winner_r_retention": format(winner_r_retention, "f"),
            "net_uplift_r": format(
                sum(
                    (
                        _d(x["shared_r"]) - _d(x["baseline_r"])
                        for x in actions
                    ),
                    ZERO,
                ),
                "f",
            ),
            "best_examples": sorted(
                actions,
                key=lambda x: _d(x["uplift_r"]),
                reverse=True,
            )[:20],
            "worst_examples": sorted(
                actions,
                key=lambda x: _d(x["uplift_r"]),
            )[:20],
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v26"])
    prearm = cast(dict[str, object], result["prearm"])
    baseline_pf = _d(baseline["profit_factor"])
    shared_pf = _d(shared["profit_factor"])
    dd = _d(shared["max_drawdown_r"])
    return {
        "profit_factor_above_baseline": shared_pf > baseline_pf,
        "profit_factor_plus_25pct": shared_pf >= baseline_pf * Decimal("1.25"),
        "drawdown_at_most_6r": dd <= DD_ACCEPTABLE_MAX_R,
        "drawdown_below_4r_exceptional": dd < DD_EXCEPTIONAL_R,
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "density_exactly_preserved": True,
        "entry_abstentions_zero": True,
        "winner_r_retention_at_least_95pct": (
            _d(prearm["winner_r_retention"]) >= Decimal("0.95")
        ),
    }


def _hard_pass(gates: dict[str, bool]) -> bool:
    return all(
        gates.get(key, False)
        for key in (
            "profit_factor_above_baseline",
            "profit_factor_plus_25pct",
            "drawdown_at_most_6r",
            "total_r_not_lower",
            "density_exactly_preserved",
            "entry_abstentions_zero",
            "winner_r_retention_at_least_95pct",
        )
    )


def _score(result: dict[str, object]) -> Decimal:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v26"])
    prearm = cast(dict[str, object], result["prearm"])
    return (
        _d(shared["profit_factor"])
        / max(_d(baseline["profit_factor"]), Decimal("0.000001"))
        * _d(baseline["max_drawdown_r"])
        / max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
        * _d(prearm["winner_r_retention"])
        * (
            ONE
            + Decimal(int(prearm["unobservable_losses_protected"]))
            / Decimal(max(1, int(baseline["losses"])))
        )
    )


def _governance() -> dict[str, bool]:
    return {
        "vt31_is_falsification_lab_only": True,
        "full_methodology_valid_universe_reconstructed": True,
        "every_methodology_entry_preserved": True,
        "entry_abstention_used": False,
        "preentry_closed_m1_context_used": True,
        "consumer_prearmed_stop_counterfactual_used": True,
        "consumer_stop_only_improves": True,
        "shared_stop_authority": False,
        "shared_order_authority": False,
        "shared_risk_authority": False,
        "shared_sizing_authority": False,
        "shared_execution_authority": False,
        "runtime_terminal_trade_outcome_used": False,
        "runtime_prior_trade_pnl_used": False,
        "runtime_prior_loss_streak_used": False,
        "future_m1_used": False,
        "intrabar_ambiguity_stop_first": True,
        "capital_risk_weighting_used": False,
        "sizing_changed": False,
        "r5_opened": False,
        "new_holdout_opened": False,
        "live_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
    }


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v23.v22.v21.v20.v19.v18.v2.v3._load_daily(daily_path)
    r8 = v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6 = v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, atlas_r8 = _prepare(
        r8,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, atlas_r6 = _prepare(
        r6,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )

    results: list[dict[str, object]] = []
    passing: list[tuple[Decimal, PrearmPolicy]] = []
    for policy in POLICIES:
        r8_result = _evaluate(p8, policy=policy)
        r6_result = _evaluate(p6, policy=policy)
        g8 = _gates(r8_result)
        g6 = _gates(r6_result)
        passed = _hard_pass(g8) and _hard_pass(g6)
        score = (_score(r8_result) + _score(r6_result)) / Decimal("2")
        results.append(
            {
                "policy": policy.payload(),
                "r8": {"evaluation": r8_result, "gates": g8},
                "r6": {"evaluation": r6_result, "gates": g6},
                "passes_both_consumed_folds": passed,
                "diagnostic_score": format(score, "f"),
            }
        )
        if passed:
            passing.append((score, policy))

    results.sort(key=lambda x: _d(x["diagnostic_score"]), reverse=True)
    frozen_policy: dict[str, object] | None = None
    if passing:
        passing.sort(key=lambda x: x[0], reverse=True)
        score, policy = passing[0]
        frozen_policy = {
            "prearm_policy": policy.payload(),
            "joint_score": format(score, "f"),
            "density_retained": "1",
            "preentry_context": "CLOSED_M1_PERSISTENT",
        }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "CALIBRATION_PASSED_NEW_HOLDOUT_REQUIRED"
            if frozen_policy is not None
            else "FALSIFIED_BEFORE_NEW_HOLDOUT"
        ),
        "owner_objective": {
            "profit_factor_must_increase": True,
            "profit_factor_plus_25pct_reference_gate": True,
            "acceptable_drawdown_r": [4, 6],
            "exceptional_drawdown_r": "<4",
            "density_must_be_preserved": True,
        },
        "observability_floor_motivation": {
            "v25_r8_unobservable_losses": 48,
            "v25_r8_oracle_dd_r": "7.8875",
            "v25_r6_unobservable_losses": 60,
            "v25_r6_oracle_dd_r": "8.4",
            "postfill_only_cannot_reach_owner_dd_gate": True,
        },
        "challenge_set": {"r8": 228, "r6": 278},
        "r5_opened": False,
        "new_holdout_opened": False,
        "passes_calibration": frozen_policy is not None,
        "frozen_policy": frozen_policy,
        "policy_results": results,
        "best_diagnostic_policy": None if not results else results[0]["policy"],
        "entry_context_atlas": {"r8": atlas_r8, "r6": atlas_r6},
        "governance": _governance(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_calibration": payload["passes_calibration"],
                "frozen_policy": payload["frozen_policy"],
                "best_diagnostic_policy": payload["best_diagnostic_policy"],
                "entry_context_atlas": payload["entry_context_atlas"],
                "policy_results": payload["policy_results"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
