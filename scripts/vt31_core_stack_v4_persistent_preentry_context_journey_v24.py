"""VT31 Shared persistent pre-entry context journey laboratory V24.

V23 proved that reconstructing every methodology-valid trade removes an
important coverage blind spot, but Shared still rebuilt its market context from
zero after each fill. That delays recognition of adverse conditions and leaves
fast stop-loss paths largely unprotected.

V24 seeds Shared with causal CLOSED-M1 NAS100/SP500/US30 context available before
fill, then carries that context into the live post-fill trajectory. Trade count
is unchanged: no entry abstention is allowed. The experiment asks whether the
same density can receive earlier, market-first defensive help without cutting
large winners.

Only consumed R8/R6 are used. R5 and fresh holdouts remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_full_universe_asymmetric_journey_v23 as v23

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

SCHEMA = "qore.core_stack_v4.vt31.persistent_preentry_context_journey.v24"
IDENTITY = "VT31_NAS100_SHARED_PERSISTENT_PREENTRY_CONTEXT_JOURNEY_V24"
ZERO = Decimal("0")
DD_ACCEPTABLE_MAX_R = Decimal("6")
DD_EXCEPTIONAL_R = Decimal("4")
PREENTRY_BARS = 8
TRAJECTORY_WINDOW = 6
ENVIRONMENT_WINDOW = 7
v18 = v23.v18
v19 = v23.v22.v21.v20.v19


@dataclass(frozen=True, slots=True)
class PersistentJourneyPolicy:
    name: str
    environment_states: frozenset[MarketEnvironmentState]
    trajectory_states: frozenset[MarketTrajectoryState]
    require_deteriorating_to_failure: bool = False
    require_efficiency_nonpositive: bool = False
    require_body_nonpositive: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "environment_states": tuple(sorted(x.value for x in self.environment_states)),
            "trajectory_states": tuple(sorted(x.value for x in self.trajectory_states)),
            "require_deteriorating_to_failure": self.require_deteriorating_to_failure,
            "require_close_nonpositive": True,
            "require_efficiency_nonpositive": self.require_efficiency_nonpositive,
            "require_body_nonpositive": self.require_body_nonpositive,
            "entry_abstention_allowed": False,
            "numeric_threshold_grid_search": False,
            "persistent_preentry_context_required": True,
        }


POLICIES = (
    PersistentJourneyPolicy(
        "PERSISTENT_DEFENSIVE_NONPOSITIVE",
        frozenset({MarketEnvironmentState.DEFENSIVE}),
        frozenset(
            {
                MarketTrajectoryState.DETERIORATING,
                MarketTrajectoryState.FAILURE,
            }
        ),
    ),
    PersistentJourneyPolicy(
        "PERSISTENT_ADVERSE_FAILURE_NONPOSITIVE",
        frozenset(
            {
                MarketEnvironmentState.ADVERSE_FORMING,
                MarketEnvironmentState.DEFENSIVE,
            }
        ),
        frozenset({MarketTrajectoryState.FAILURE}),
    ),
    PersistentJourneyPolicy(
        "PERSISTENT_ADVERSE_DTF_NONPOSITIVE",
        frozenset(
            {
                MarketEnvironmentState.ADVERSE_FORMING,
                MarketEnvironmentState.DEFENSIVE,
            }
        ),
        frozenset({MarketTrajectoryState.FAILURE}),
        require_deteriorating_to_failure=True,
    ),
    PersistentJourneyPolicy(
        "PERSISTENT_DEGRADING_MULTIAXIS",
        frozenset(
            {
                MarketEnvironmentState.DEGRADING,
                MarketEnvironmentState.ADVERSE_FORMING,
                MarketEnvironmentState.DEFENSIVE,
            }
        ),
        frozenset(
            {
                MarketTrajectoryState.DETERIORATING,
                MarketTrajectoryState.FAILURE,
            }
        ),
        require_efficiency_nonpositive=True,
        require_body_nonpositive=True,
    ),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _sign_stability(short: Decimal | None, long: Decimal | None) -> int:
    if short is None or long is None:
        return 5000
    if short == ZERO or long == ZERO:
        return 6500
    return 8500 if (short > ZERO) == (long > ZERO) else 3500


def _market_transition_observation(
    *,
    as_of: object,
    side: str,
    nas: tuple[object, ...],
    sp: tuple[object, ...],
    us: tuple[object, ...],
) -> MarketTransitionObservation:
    nas3 = v18.v13._signed_move(nas, side=side, window=3)
    nas10 = v18.v13._signed_move(nas, side=side, window=10)
    sp3 = v18.v13._signed_move(sp, side=side, window=3)
    sp10 = v18.v13._signed_move(sp, side=side, window=10)
    us3 = v18.v13._signed_move(us, side=side, window=3)
    us10 = v18.v13._signed_move(us, side=side, window=10)

    breadth3 = v18.v13._breadth((nas3, sp3, us3))
    breadth10 = v18.v13._breadth((nas10, sp10, us10))
    peer = v18.v13._sync(sp3, us3)

    nas3_support = 5000 if nas3 is None else v19._signed_bps(nas3)
    nas10_support = 5000 if nas10 is None else v19._signed_bps(nas10)
    cross3 = v19._breadth_support(breadth3)
    cross10 = v19._breadth_support(breadth10)
    cross_confirmation = (cross3 + cross10) // 2

    trend_support = (nas10_support + nas3_support + cross10) // 3
    momentum = (nas3_support + cross3) // 2
    displacement = nas3_support
    volatility_stability = _sign_stability(nas3, nas10)
    correlation_stability = v19._peer_correlation(peer)

    nas3_adverse = 5000 if nas3 is None else v19._adverse_bps(nas3)
    nas10_adverse = 5000 if nas10 is None else v19._adverse_bps(nas10)
    breadth_adverse = max(
        v19._breadth_adverse(breadth3),
        v19._breadth_adverse(breadth10),
    )
    contradiction = max(
        breadth_adverse,
        10_000 - volatility_stability,
        10_000 - correlation_stability,
    )

    breadth_transition = v18.v13._transition(
        None if nas3 is None else nas3,
        None if nas10 is None else nas10,
    )
    anomaly = 7000 if "REVERSING" in breadth_transition else 2500
    if breadth3 == "SPLIT" or breadth10 == "SPLIT":
        anomaly = max(anomaly, 6500)
    uncertainty = 7000 if peer == "INCOMPLETE" else 2500
    if peer == "DIVERGENT":
        uncertainty = max(uncertainty, 5500)

    complete = all(
        value is not None
        for value in (nas3, nas10, sp3, sp10, us3, us10)
    )
    data_integrity = 10_000 if complete else 7000

    return MarketTransitionObservation(
        as_of=cast(object, as_of),
        data_integrity_bps=data_integrity,
        trend_support_bps=trend_support,
        momentum_bps=momentum,
        displacement_bps=displacement,
        liquidity_capacity_bps=5000,
        volatility_stability_bps=volatility_stability,
        cross_market_confirmation_bps=cross_confirmation,
        correlation_stability_bps=correlation_stability,
        contradiction_bps=contradiction,
        anomaly_bps=anomaly,
        uncertainty_bps=uncertainty,
        opposite_pressure_bps=max(
            nas3_adverse,
            nas10_adverse,
            breadth_adverse,
        ),
    )


def _environment_observation(
    transition: MarketTransitionObservation,
    trajectory: object,
) -> MarketEnvironmentObservation:
    assessment = cast(object, trajectory)
    regime_stability = (
        transition.trend_support_bps
        + transition.momentum_bps
        + transition.displacement_bps
    ) // 3
    leadership_stability = (
        transition.cross_market_confirmation_bps
        + transition.correlation_stability_bps
    ) // 2
    return MarketEnvironmentObservation(
        as_of=transition.as_of,
        data_integrity_bps=transition.data_integrity_bps,
        trajectory_support_bps=assessment.support_bps,
        trajectory_adversity_bps=assessment.adversity_bps,
        deterioration_velocity_bps=assessment.deterioration_velocity_bps,
        recovery_velocity_bps=assessment.recovery_velocity_bps,
        cross_market_breadth_bps=transition.cross_market_confirmation_bps,
        leadership_stability_bps=leadership_stability,
        correlation_stability_bps=transition.correlation_stability_bps,
        volatility_stability_bps=transition.volatility_stability_bps,
        liquidity_stability_bps=transition.liquidity_capacity_bps,
        regime_stability_bps=regime_stability,
        anomaly_bps=transition.anomaly_bps,
        uncertainty_bps=transition.uncertainty_bps,
        opposite_pressure_bps=transition.opposite_pressure_bps,
    )


def _seed_transition_history(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    fill_index: int,
    sp_by_day: object,
    us_by_day: object,
) -> list[MarketTransitionObservation]:
    side = cast(str, row["side"])
    local_day = datetime.fromisoformat(cast(str, row["filled_at"])).date()
    start = max(0, fill_index - PREENTRY_BARS)
    history: list[MarketTransitionObservation] = []

    for index in range(start, fill_index):
        bar = day_bars[index]
        as_of = cast(object, bar).closed_at
        nas = tuple(day_bars[: index + 1])
        sp = tuple(v18.v13._eligible(sp_by_day, local_day, as_of))
        us = tuple(v18.v13._eligible(us_by_day, local_day, as_of))
        history.append(
            _market_transition_observation(
                as_of=as_of,
                side=side,
                nas=nas,
                sp=sp,
                us=us,
            )
        )
    return history


def _annotate_persistent_context(
    prepared: list[dict[str, object]],
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

    output: list[dict[str, object]] = []
    entry_environment_histogram: Counter[str] = Counter()
    first_postfill_environment_histogram: Counter[str] = Counter()
    first_postfill_trajectory_histogram: Counter[str] = Counter()
    seeded_observation_counts: Counter[int] = Counter()

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        signal = cast(str, row["signal_at"])
        setup, day_bars = paths[signal]
        fill_index, _ = v18.counter._fill_and_exit_indices(setup, day_bars, row)

        transition_history = _seed_transition_history(
            row=row,
            setup=setup,
            day_bars=day_bars,
            fill_index=fill_index,
            sp_by_day=sp_by_day,
            us_by_day=us_by_day,
        )
        seeded_observation_counts[len(transition_history)] += 1

        environment_history: list[MarketEnvironmentObservation] = []
        state_history: list[str] = []
        last_entry_environment = MarketEnvironmentState.INSUFFICIENT

        for index, transition in enumerate(transition_history):
            trajectory = assess_market_trajectory(
                tuple(
                    transition_history[
                        max(0, index - TRAJECTORY_WINDOW + 1) : index + 1
                    ]
                )
            )
            state_history.append(trajectory.state.value)
            environment_observation = _environment_observation(
                transition,
                trajectory,
            )
            environment_history.append(environment_observation)
            environment = assess_market_environment(
                tuple(environment_history[-ENVIRONMENT_WINDOW:])
            )
            last_entry_environment = environment.state

        entry_environment_histogram[last_entry_environment.value] += 1

        events: list[dict[str, object]] = []
        first_post = True
        for raw in cast(list[dict[str, object]], item["events"]):
            transition = v19._to_observation(row, raw)
            transition_history.append(transition)
            trajectory = assess_market_trajectory(
                tuple(transition_history[-TRAJECTORY_WINDOW:])
            )
            state_history.append(trajectory.state.value)

            env_observation = _environment_observation(transition, trajectory)
            environment_history.append(env_observation)
            environment = assess_market_environment(
                tuple(environment_history[-ENVIRONMENT_WINDOW:])
            )

            if first_post:
                first_postfill_environment_histogram[environment.state.value] += 1
                first_postfill_trajectory_histogram[trajectory.state.value] += 1
                first_post = False

            events.append(
                {
                    **raw,
                    "trajectory_state": trajectory.state.value,
                    "trajectory_state_history": tuple(state_history[-TRAJECTORY_WINDOW:]),
                    "trajectory_support_bps": trajectory.support_bps,
                    "trajectory_adversity_bps": trajectory.adversity_bps,
                    "trajectory_deterioration_velocity_bps": trajectory.deterioration_velocity_bps,
                    "trajectory_recovery_velocity_bps": trajectory.recovery_velocity_bps,
                    "trajectory_deterioration_persistence_bps": trajectory.deterioration_persistence_bps,
                    "trajectory_recovery_persistence_bps": trajectory.recovery_persistence_bps,
                    "environment_state": environment.state.value,
                    "environment_support_bps": environment.market_support_bps,
                    "environment_adverse_bps": environment.adverse_environment_bps,
                    "environment_adverse_velocity_bps": environment.adverse_velocity_bps,
                    "environment_recovery_velocity_bps": environment.recovery_velocity_bps,
                    "environment_adverse_persistence_bps": environment.adverse_persistence_bps,
                    "environment_recovery_persistence_bps": environment.recovery_persistence_bps,
                    "environment_cross_fragility_bps": environment.cross_market_fragility_bps,
                    "environment_structural_fragility_bps": environment.structural_fragility_bps,
                    "preentry_context_seeded": True,
                    "entry_environment_state": last_entry_environment.value,
                }
            )

        output.append({**item, "events": events})

    return output, {
        "preentry_bars_requested": PREENTRY_BARS,
        "seeded_observation_counts": dict(
            sorted((str(key), value) for key, value in seeded_observation_counts.items())
        ),
        "entry_environment_histogram": dict(sorted(entry_environment_histogram.items())),
        "first_postfill_environment_histogram": dict(
            sorted(first_postfill_environment_histogram.items())
        ),
        "first_postfill_trajectory_histogram": dict(
            sorted(first_postfill_trajectory_histogram.items())
        ),
        "context_resets_at_fill": False,
        "future_m1_used": False,
        "trade_outcome_used_for_state": False,
    }


def _matches(
    event: dict[str, object],
    policy: PersistentJourneyPolicy,
) -> bool:
    if MarketEnvironmentState(str(event["environment_state"])) not in policy.environment_states:
        return False
    if MarketTrajectoryState(str(event["trajectory_state"])) not in policy.trajectory_states:
        return False
    if _d(event["close_r"]) > ZERO:
        return False

    if policy.require_deteriorating_to_failure:
        history = tuple(str(x) for x in cast(object, event["trajectory_state_history"]))
        if len(history) < 2 or history[-2:] != ("DETERIORATING", "FAILURE"):
            return False

    if policy.require_efficiency_nonpositive and _d(event["efficiency"]) > ZERO:
        return False
    if policy.require_body_nonpositive and _d(event["signed_body_r"]) > ZERO:
        return False
    return True


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    policy: PersistentJourneyPolicy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    defended: list[dict[str, object]] = []

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        baseline_values.append(baseline_r)
        shared_r = baseline_r

        for event in cast(list[dict[str, object]], item["events"]):
            if not _matches(event, policy):
                continue
            shared_r = _d(event["defense_r_after_friction"])
            defended.append(
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": format(baseline_r, "f"),
                    "defense_r": format(shared_r, "f"),
                    "uplift_r": format(shared_r - baseline_r, "f"),
                    "minutes_since_fill": event["minutes_since_fill"],
                    "entry_environment_state": event["entry_environment_state"],
                    "environment_state": event["environment_state"],
                    "trajectory_state": event["trajectory_state"],
                    "trajectory_state_history": event["trajectory_state_history"],
                    "close_r": event["close_r"],
                    "efficiency": event["efficiency"],
                    "signed_body_r": event["signed_body_r"],
                }
            )
            break
        shared_values.append(shared_r)

    baseline = v23._metrics(baseline_values)
    shared = v23._metrics(shared_values)
    defended_losers = [x for x in defended if _d(x["baseline_r"]) < ZERO]
    defended_winners = [x for x in defended if _d(x["baseline_r"]) > ZERO]
    base_losses = int(baseline["losses"])
    baseline_winner_r = _d(baseline["gross_winner_r"])
    shared_winner_r = _d(shared["gross_winner_r"])
    winner_r_retention = (
        Decimal("1")
        if baseline_winner_r == ZERO
        else shared_winner_r / baseline_winner_r
    )
    loser_uplift = sum((_d(x["uplift_r"]) for x in defended_losers), ZERO)
    winner_damage = -min(
        ZERO,
        sum((_d(x["uplift_r"]) for x in defended_winners), ZERO),
    )

    return {
        "baseline": baseline,
        "shared_v24": shared,
        "density": {
            "input": len(baseline_values),
            "kept": len(shared_values),
            "retained": "1",
            "entry_abstentions": 0,
        },
        "journey": {
            "defended_trades": len(defended),
            "defended_baseline_losses": len(defended_losers),
            "defended_baseline_winners": len(defended_winners),
            "baseline_loss_defense_recall": (
                "0"
                if base_losses == 0
                else format(Decimal(len(defended_losers)) / Decimal(base_losses), "f")
            ),
            "loser_uplift_r": format(loser_uplift, "f"),
            "winner_damage_r": format(winner_damage, "f"),
            "winner_r_retention": format(winner_r_retention, "f"),
            "net_journey_uplift_r": format(
                sum((_d(x["uplift_r"]) for x in defended), ZERO),
                "f",
            ),
            "best_examples": sorted(
                defended,
                key=lambda x: _d(x["uplift_r"]),
                reverse=True,
            )[:20],
            "worst_examples": sorted(
                defended,
                key=lambda x: _d(x["uplift_r"]),
            )[:20],
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v24"])
    journey = cast(dict[str, object], result["journey"])
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
            _d(journey["winner_r_retention"]) >= Decimal("0.95")
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


def _diagnostic_score(result: dict[str, object]) -> Decimal:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v24"])
    journey = cast(dict[str, object], result["journey"])
    return (
        _d(shared["profit_factor"])
        / max(_d(baseline["profit_factor"]), Decimal("0.000001"))
        * _d(baseline["max_drawdown_r"])
        / max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
        * _d(journey["winner_r_retention"])
        * (Decimal("1") + _d(journey["baseline_loss_defense_recall"]))
    )


def _governance() -> dict[str, bool]:
    return {
        "vt31_is_falsification_lab_only": True,
        "persistent_preentry_context_used": True,
        "context_reset_at_fill": False,
        "closed_m1_only": True,
        "full_methodology_valid_universe_reconstructed": True,
        "entry_abstention_used": False,
        "density_preservation_is_hard_gate": True,
        "runtime_terminal_trade_outcome_used": False,
        "runtime_prior_trade_pnl_used": False,
        "runtime_prior_loss_streak_used": False,
        "future_m1_used": False,
        "r5_opened": False,
        "new_holdout_opened": False,
        "capital_risk_weighting_used": False,
        "methodology_entry_modified": False,
        "shared_order_authority": False,
        "shared_risk_authority": False,
        "shared_execution_authority": False,
        "stop_widening_used": False,
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

    p8 = v23._prepare_full_universe(
        r8,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6 = v23._prepare_full_universe(
        r6,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    a8, context_r8 = _annotate_persistent_context(
        p8,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    a6, context_r6 = _annotate_persistent_context(
        p6,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )

    results: list[dict[str, object]] = []
    passing: list[tuple[Decimal, PersistentJourneyPolicy]] = []
    for policy in POLICIES:
        r8_result = _evaluate(a8, policy=policy)
        r6_result = _evaluate(a6, policy=policy)
        g8 = _gates(r8_result)
        g6 = _gates(r6_result)
        passed = _hard_pass(g8) and _hard_pass(g6)
        score = (
            _diagnostic_score(r8_result) + _diagnostic_score(r6_result)
        ) / Decimal("2")
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
            "journey_policy": policy.payload(),
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
        "challenge_set": {"r8": 228, "r6": 278},
        "r5_opened": False,
        "new_holdout_opened": False,
        "passes_calibration": frozen_policy is not None,
        "frozen_policy": frozen_policy,
        "policy_results": results,
        "best_diagnostic_policy": None if not results else results[0]["policy"],
        "persistent_context": {
            "r8": context_r8,
            "r6": context_r6,
        },
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
                "persistent_context": payload["persistent_context"],
                "policy_results": payload["policy_results"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
