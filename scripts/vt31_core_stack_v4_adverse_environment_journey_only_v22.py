"""VT31 Shared adverse-environment journey-only laboratory V22.

Owner objective added after V21:
- Shared must raise Profit Factor;
- Shared should drive observed drawdown toward 4-6R, ideally below 4R;
- Shared must not obtain that result by destroying trade density.

V22 therefore keeps the entire R8/R6 methodology-valid opportunity universe.
It ignores V15 entry abstention decisions and evaluates only causal journey
support. The new generic Shared market-environment intelligence is fed solely
with market evidence available as of each post-fill observation.

R8 and R6 are consumed research folds. R5 and any fresh holdout remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_failure_sequence_topology_v21 as v21
from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentObservation,
    MarketEnvironmentState,
    assess_market_environment,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryState,
)

SCHEMA = "qore.core_stack_v4.vt31.adverse_environment_journey_only.v22"
IDENTITY = "VT31_NAS100_SHARED_ADVERSE_ENVIRONMENT_JOURNEY_ONLY_V22"
ZERO = Decimal("0")
DD_ACCEPTABLE_MAX_R = Decimal("6")
DD_EXCEPTIONAL_R = Decimal("4")
ENVIRONMENT_WINDOW = 7


@dataclass(frozen=True, slots=True)
class JourneyPolicy:
    name: str
    environment_states: frozenset[MarketEnvironmentState]
    trajectory_states: frozenset[MarketTrajectoryState]
    require_deteriorating_to_failure: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "environment_states": tuple(sorted(x.value for x in self.environment_states)),
            "trajectory_states": tuple(sorted(x.value for x in self.trajectory_states)),
            "require_deteriorating_to_failure": self.require_deteriorating_to_failure,
            "entry_abstention_allowed": False,
            "numeric_threshold_grid_search": False,
        }


POLICIES = (
    JourneyPolicy(
        "ENV_DEFENSIVE_ONLY",
        frozenset({MarketEnvironmentState.DEFENSIVE}),
        frozenset(),
    ),
    JourneyPolicy(
        "ENV_ADVERSE_WITH_TRAJECTORY_FAILURE",
        frozenset(
            {
                MarketEnvironmentState.ADVERSE_FORMING,
                MarketEnvironmentState.DEFENSIVE,
            }
        ),
        frozenset({MarketTrajectoryState.FAILURE}),
    ),
    JourneyPolicy(
        "ENV_ADVERSE_WITH_DTF_SEQUENCE",
        frozenset(
            {
                MarketEnvironmentState.ADVERSE_FORMING,
                MarketEnvironmentState.DEFENSIVE,
            }
        ),
        frozenset({MarketTrajectoryState.FAILURE}),
        require_deteriorating_to_failure=True,
    ),
    JourneyPolicy(
        "ENV_DEGRADING_WITH_TRAJECTORY_RISK",
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
    ),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _environment_observation(
    row: dict[str, object],
    event: dict[str, object],
) -> MarketEnvironmentObservation:
    transition = v21.v20.v19._to_observation(row, event)
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
        trajectory_support_bps=int(event["trajectory_support_bps"]),
        trajectory_adversity_bps=int(event["trajectory_adversity_bps"]),
        deterioration_velocity_bps=int(
            event["trajectory_deterioration_velocity_bps"]
        ),
        recovery_velocity_bps=int(event["trajectory_recovery_velocity_bps"]),
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


def _annotate_environment(
    prepared: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    annotated: list[dict[str, object]] = []
    state_histogram: Counter[str] = Counter()
    transition_histogram: Counter[str] = Counter()

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        history: list[MarketEnvironmentObservation] = []
        events: list[dict[str, object]] = []
        previous: str | None = None

        for raw in cast(list[dict[str, object]], item["events"]):
            observation = _environment_observation(row, raw)
            history.append(observation)
            assessment = assess_market_environment(
                tuple(history[-ENVIRONMENT_WINDOW:])
            )
            state = assessment.state.value
            state_histogram[state] += 1
            if previous is not None and previous != state:
                transition_histogram[f"{previous}->{state}"] += 1
            previous = state
            events.append(
                {
                    **raw,
                    "environment_state": state,
                    "environment_support_bps": assessment.market_support_bps,
                    "environment_adverse_bps": assessment.adverse_environment_bps,
                    "environment_adverse_velocity_bps": assessment.adverse_velocity_bps,
                    "environment_recovery_velocity_bps": assessment.recovery_velocity_bps,
                    "environment_adverse_persistence_bps": assessment.adverse_persistence_bps,
                    "environment_recovery_persistence_bps": assessment.recovery_persistence_bps,
                    "environment_cross_fragility_bps": assessment.cross_market_fragility_bps,
                    "environment_structural_fragility_bps": assessment.structural_fragility_bps,
                    "environment_reasons": assessment.reasons,
                }
            )
        annotated.append({**item, "events": events})

    return annotated, {
        "environment_window": ENVIRONMENT_WINDOW,
        "state_histogram": dict(sorted(state_histogram.items())),
        "transition_histogram": dict(sorted(transition_histogram.items())),
        "runtime_trade_outcomes_used": False,
        "runtime_pnl_used": False,
        "entry_abstention_used": False,
    }


def _matches(event: dict[str, object], policy: JourneyPolicy) -> bool:
    environment = MarketEnvironmentState(str(event["environment_state"]))
    if environment not in policy.environment_states:
        return False

    trajectory = MarketTrajectoryState(str(event["trajectory_state"]))
    if policy.trajectory_states and trajectory not in policy.trajectory_states:
        return False

    if policy.require_deteriorating_to_failure:
        history = cast(tuple[str, ...], event["trajectory_state_history"])
        if len(history) < 2 or history[-2:] != ("DETERIORATING", "FAILURE"):
            return False
    return True


def _metrics(values: list[Decimal]) -> dict[str, object]:
    return v21.v20.v19.v18.v17._metrics(values)


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    policy: JourneyPolicy,
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
                    "environment_state": event["environment_state"],
                    "trajectory_state": event["trajectory_state"],
                    "trajectory_state_history": event["trajectory_state_history"],
                    "environment_adverse_bps": event["environment_adverse_bps"],
                    "environment_adverse_persistence_bps": event[
                        "environment_adverse_persistence_bps"
                    ],
                    "environment_reasons": event["environment_reasons"],
                }
            )
            break
        shared_values.append(shared_r)

    baseline = _metrics(baseline_values)
    shared = _metrics(shared_values)
    defended_losers = [
        item for item in defended if _d(item["baseline_r"]) < 0
    ]
    defended_winners = [
        item for item in defended if _d(item["baseline_r"]) > 0
    ]
    baseline_winner_r = _d(baseline["gross_winner_r"])
    shared_winner_r = _d(shared["gross_winner_r"])
    winner_r_retention = (
        Decimal("1")
        if baseline_winner_r == 0
        else shared_winner_r / baseline_winner_r
    )
    loser_uplift = sum(
        (_d(item["uplift_r"]) for item in defended_losers),
        ZERO,
    )
    winner_damage = -min(
        ZERO,
        sum((_d(item["uplift_r"]) for item in defended_winners), ZERO),
    )
    return {
        "baseline": baseline,
        "shared_v22": shared,
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
            "loser_uplift_r": format(loser_uplift, "f"),
            "winner_damage_r": format(winner_damage, "f"),
            "winner_r_retention": format(winner_r_retention, "f"),
            "net_journey_uplift_r": format(
                sum((_d(item["uplift_r"]) for item in defended), ZERO),
                "f",
            ),
            "best_examples": sorted(
                defended,
                key=lambda item: _d(item["uplift_r"]),
                reverse=True,
            )[:20],
            "worst_examples": sorted(
                defended,
                key=lambda item: _d(item["uplift_r"]),
            )[:20],
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v22"])
    journey = cast(dict[str, object], result["journey"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    baseline_pf = _d(baseline["profit_factor"])
    shared_pf = _d(shared["profit_factor"])
    dd = _d(shared["max_drawdown_r"])
    return {
        "profit_factor_above_baseline": shared_pf > baseline_pf,
        "profit_factor_plus_25pct": shared_pf >= baseline_pf * Decimal("1.25"),
        "drawdown_at_most_6r": dd <= DD_ACCEPTABLE_MAX_R,
        "drawdown_below_4r_exceptional": dd < DD_EXCEPTIONAL_R,
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "density_exactly_preserved": cast(dict[str, object], result["density"])[
            "retained"
        ]
        == "1",
        "winner_r_retention_at_least_95pct": _d(
            journey["winner_r_retention"]
        )
        >= Decimal("0.95"),
    }


def _hard_pass(gates: dict[str, bool]) -> bool:
    required = (
        "profit_factor_above_baseline",
        "drawdown_at_most_6r",
        "total_r_not_lower",
        "density_exactly_preserved",
        "winner_r_retention_at_least_95pct",
    )
    return all(gates.get(key, False) for key in required)


def _diagnostic_score(result: dict[str, object]) -> Decimal:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v22"])
    journey = cast(dict[str, object], result["journey"])
    baseline_pf = max(_d(baseline["profit_factor"]), Decimal("0.000001"))
    shared_pf = _d(shared["profit_factor"])
    baseline_dd = max(_d(baseline["max_drawdown_r"]), Decimal("0.000001"))
    shared_dd = max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
    return (
        shared_pf
        / baseline_pf
        * baseline_dd
        / shared_dd
        * _d(journey["winner_r_retention"])
    )


def _governance() -> dict[str, bool]:
    return {
        "vt31_is_falsification_lab_only": True,
        "shared_generic_environment_engine_used": True,
        "journey_only_no_entry_abstention": True,
        "density_preservation_is_hard_gate": True,
        "runtime_trade_outcomes_used": False,
        "runtime_pnl_used": False,
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
    daily = v21.v20.v19.v18.v2.v3._load_daily(daily_path)
    r8 = v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6 = v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v21.v20.v19.v18.v8._negative_tables(r8)
    r8_n1 = [
        row
        for row in r8
        if v21.v20.v19.v18.v13._negative_views(row, negative) == 1
    ]
    model, _ = v21.v20.v19.v18.v13._learn_model(r8_n1)

    p8 = v21.v20.v19.v18._prepare_fold(
        r8,
        negative=negative,
        model=model,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6 = v21.v20.v19.v18._prepare_fold(
        r6,
        negative=negative,
        model=model,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    a8, trajectory_r8 = v21.v20.v19._annotate_trajectory(p8)
    a6, trajectory_r6 = v21.v20.v19._annotate_trajectory(p6)
    h8 = v21._with_state_history(a8)
    h6 = v21._with_state_history(a6)
    e8, environment_r8 = _annotate_environment(h8)
    e6, environment_r6 = _annotate_environment(h6)

    results: list[dict[str, object]] = []
    passing: list[tuple[Decimal, JourneyPolicy]] = []
    for policy in POLICIES:
        r8_result = _evaluate(e8, policy=policy)
        r6_result = _evaluate(e6, policy=policy)
        g8 = _gates(r8_result)
        g6 = _gates(r6_result)
        passed = _hard_pass(g8) and _hard_pass(g6)
        diagnostic = (
            _diagnostic_score(r8_result) + _diagnostic_score(r6_result)
        ) / Decimal("2")
        results.append(
            {
                "policy": policy.payload(),
                "r8": {"evaluation": r8_result, "gates": g8},
                "r6": {"evaluation": r6_result, "gates": g6},
                "passes_both_consumed_folds": passed,
                "diagnostic_score": format(diagnostic, "f"),
            }
        )
        if passed:
            passing.append((diagnostic, policy))

    results.sort(key=lambda item: _d(item["diagnostic_score"]), reverse=True)
    frozen_policy: dict[str, object] | None = None
    if passing:
        passing.sort(key=lambda item: item[0], reverse=True)
        score, policy = passing[0]
        frozen_policy = {
            "journey_policy": policy.payload(),
            "generic_environment_defaults": "FROZEN_DEFAULTS",
            "joint_score": format(score, "f"),
            "density_retained": "1",
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
        "representation": {
            "trajectory_r8": trajectory_r8,
            "trajectory_r6": trajectory_r6,
            "environment_r8": environment_r8,
            "environment_r6": environment_r6,
            "entry_filtering_disabled_for_v22": True,
            "density_preserved_by_design": True,
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
                "policy_results": payload["policy_results"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
