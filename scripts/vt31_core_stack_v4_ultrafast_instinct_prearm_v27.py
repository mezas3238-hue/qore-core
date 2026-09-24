"""VT31 Shared ultra-fast instinct prearmed protection laboratory V27.

V27 consumes the resident causal pre-entry state built by V26 and routes it
through the generic O(1) Shared Instinct Intelligence hot path. The hot path
selects an authority-free support methodology immediately. Consumer-side
counterfactual protection is then tested without entry abstention, sizing,
capital weighting, realized outcome input, future M1, or trader-specific logic.

R8/R6 are consumed research folds. R5 and fresh holdouts remain closed.
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

import vt31_core_stack_v4_causal_prearmed_protection_v26 as v26

from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentAssessment,
    MarketEnvironmentState,
)
from qore.infrastructure.core_stack_v2.instinct_intelligence import (
    InstinctAssessment,
    SupportMethodology,
    assess_instinct,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryAssessment,
    MarketTrajectoryState,
)

SCHEMA = "qore.core_stack_v4.vt31.ultrafast_instinct_prearm.v27"
IDENTITY = "VT31_NAS100_SHARED_ULTRAFAST_INSTINCT_PREARM_V27"
ZERO = Decimal("0")
ONE = Decimal("1")
DD_ACCEPTABLE_MAX_R = Decimal("6")
DD_EXCEPTIONAL_R = Decimal("4")


@dataclass(frozen=True, slots=True)
class InstinctPrearmPolicy:
    name: str
    immediate_fraction: Decimal
    progressive_fraction: Decimal | None

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "immediate_fraction_r": format(self.immediate_fraction, "f"),
            "progressive_fraction_r": (
                None
                if self.progressive_fraction is None
                else format(self.progressive_fraction, "f")
            ),
            "entry_abstention_allowed": False,
            "density_preserved": True,
            "shared_stop_authority": False,
            "numeric_threshold_grid_search": False,
            "instinct_hot_path": "O(1)_RESIDENT_STATE_ONLY",
        }


POLICIES = (
    InstinctPrearmPolicy(
        "INSTINCT_IMMEDIATE_HALF",
        Decimal("0.50"),
        None,
    ),
    InstinctPrearmPolicy(
        "INSTINCT_IMMEDIATE_QUARTER",
        Decimal("0.25"),
        None,
    ),
    InstinctPrearmPolicy(
        "INSTINCT_LAYERED_CONSERVATIVE",
        Decimal("0.50"),
        Decimal("0.75"),
    ),
    InstinctPrearmPolicy(
        "INSTINCT_LAYERED_STRONG",
        Decimal("0.25"),
        Decimal("0.50"),
    ),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _mean4(a: int, b: int, c: int, d: int) -> int:
    return (a + b + c + d) // 4


def _resident_assessments(
    context: dict[str, object],
) -> tuple[MarketEnvironmentAssessment, MarketTrajectoryAssessment]:
    as_of = datetime.fromisoformat(str(context["as_of"]))
    count = int(context["preentry_observation_count"])
    environment = MarketEnvironmentAssessment(
        as_of=as_of,
        state=MarketEnvironmentState(str(context["environment_state"])),
        evidence_count=count,
        market_support_bps=int(context["environment_support_bps"]),
        adverse_environment_bps=int(context["environment_adverse_bps"]),
        adverse_velocity_bps=int(context["environment_adverse_velocity_bps"]),
        recovery_velocity_bps=int(context["environment_recovery_velocity_bps"]),
        adverse_persistence_bps=int(
            context["environment_adverse_persistence_bps"]
        ),
        recovery_persistence_bps=int(
            context["environment_recovery_persistence_bps"]
        ),
        cross_market_fragility_bps=int(context["cross_market_fragility_bps"]),
        structural_fragility_bps=int(context["structural_fragility_bps"]),
        reasons=("RESIDENT_PREENTRY_CONTEXT",),
    )
    trajectory = MarketTrajectoryAssessment(
        as_of=as_of,
        state=MarketTrajectoryState(str(context["trajectory_state"])),
        evidence_count=count,
        support_bps=int(context["trajectory_support_bps"]),
        adversity_bps=int(context["trajectory_adversity_bps"]),
        deterioration_pressure_bps=int(context["trajectory_pressure_bps"]),
        deterioration_velocity_bps=int(
            context["trajectory_deterioration_velocity_bps"]
        ),
        recovery_velocity_bps=int(context["trajectory_recovery_velocity_bps"]),
        deterioration_persistence_bps=int(
            context["trajectory_deterioration_persistence_bps"]
        ),
        recovery_persistence_bps=int(
            context["trajectory_recovery_persistence_bps"]
        ),
        reasons=("RESIDENT_PREENTRY_CONTEXT",),
    )
    return environment, trajectory


def _instinct(context: dict[str, object]) -> InstinctAssessment:
    environment, trajectory = _resident_assessments(context)
    opportunity_quality = _mean4(
        environment.market_support_bps,
        trajectory.support_bps,
        10_000 - environment.cross_market_fragility_bps,
        10_000 - environment.structural_fragility_bps,
    )
    expansion_capacity = _mean4(
        environment.market_support_bps,
        trajectory.support_bps,
        10_000 - environment.adverse_environment_bps,
        10_000 - trajectory.adversity_bps,
    )
    return assess_instinct(
        environment,
        trajectory,
        opportunity_quality_bps=opportunity_quality,
        expansion_capacity_bps=expansion_capacity,
    )


def _fraction(
    instinct: InstinctAssessment,
    policy: InstinctPrearmPolicy,
) -> Decimal | None:
    if instinct.support_methodology is SupportMethodology.IMMEDIATE_DEFENSE:
        return policy.immediate_fraction
    if (
        instinct.support_methodology is SupportMethodology.PROGRESSIVE_DEFENSE
        and policy.progressive_fraction is not None
    ):
        return policy.progressive_fraction
    return None


def _metrics(values: list[Decimal]) -> dict[str, object]:
    return v26._metrics(values)


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    policy: InstinctPrearmPolicy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    actions: list[dict[str, object]] = []
    situation_histogram: Counter[str] = Counter()
    methodology_histogram: Counter[str] = Counter()

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        baseline_values.append(baseline_r)
        context = cast(dict[str, object], item["entry_context"])
        instinct = _instinct(context)
        situation_histogram[instinct.situation.value] += 1
        methodology_histogram[instinct.support_methodology.value] += 1
        fraction = _fraction(instinct, policy)

        if fraction is None:
            shared_r = baseline_r
        else:
            result = v26._simulate_prearmed(
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
                    "instinct": {
                        "situation": instinct.situation.value,
                        "support_methodology": instinct.support_methodology.value,
                        "market_support_bps": instinct.market_support_bps,
                        "threat_bps": instinct.threat_bps,
                        "urgency_bps": instinct.urgency_bps,
                        "confidence_bps": instinct.confidence_bps,
                        "reasons": instinct.reasons,
                    },
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
    unobservable_losses = [
        x for x in improved_losses if not bool(x["baseline_observable_postfill"])
    ]
    baseline_winner_r = _d(baseline["gross_winner_r"])
    winner_retention = (
        ONE
        if baseline_winner_r == ZERO
        else _d(shared["gross_winner_r"]) / baseline_winner_r
    )
    base_losses = int(baseline["losses"])

    return {
        "baseline": baseline,
        "shared_v27": shared,
        "density": {
            "input": len(baseline_values),
            "kept": len(shared_values),
            "retained": "1",
            "entry_abstentions": 0,
        },
        "instinct": {
            "situation_histogram": dict(sorted(situation_histogram.items())),
            "methodology_histogram": dict(sorted(methodology_histogram.items())),
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
            "unobservable_losses_protected": len(unobservable_losses),
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
            "winner_r_retention": format(winner_retention, "f"),
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
    shared = cast(dict[str, object], result["shared_v27"])
    instinct = cast(dict[str, object], result["instinct"])
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
            _d(instinct["winner_r_retention"]) >= Decimal("0.95")
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
    shared = cast(dict[str, object], result["shared_v27"])
    instinct = cast(dict[str, object], result["instinct"])
    return (
        _d(shared["profit_factor"])
        / max(_d(baseline["profit_factor"]), Decimal("0.000001"))
        * _d(baseline["max_drawdown_r"])
        / max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
        * _d(instinct["winner_r_retention"])
        * (
            ONE
            + Decimal(int(instinct["unobservable_losses_protected"]))
            / Decimal(max(1, int(baseline["losses"])))
        )
    )


def _governance() -> dict[str, bool]:
    return {
        "vt31_is_falsification_lab_only": True,
        "generic_instinct_engine_used": True,
        "instinct_hot_path_constant_time": True,
        "resident_preentry_state_used": True,
        "history_scan_inside_instinct_used": False,
        "io_inside_instinct_used": False,
        "runtime_terminal_trade_outcome_used": False,
        "runtime_prior_trade_pnl_used": False,
        "future_m1_used": False,
        "every_methodology_entry_preserved": True,
        "entry_abstention_used": False,
        "capital_risk_weighting_used": False,
        "sizing_changed": False,
        "shared_stop_authority": False,
        "shared_order_authority": False,
        "shared_risk_authority": False,
        "shared_execution_authority": False,
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
    daily = v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(daily_path)
    r8 = v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6 = v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v26._prepare(
        r8,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v26._prepare(
        r6,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )

    results: list[dict[str, object]] = []
    passing: list[tuple[Decimal, InstinctPrearmPolicy]] = []
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
            "instinct_policy": policy.payload(),
            "joint_score": format(score, "f"),
            "density_retained": "1",
            "hot_path": "O(1)_RESIDENT_STATE_ONLY",
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
        "engineering_objective": {
            "resident_state": True,
            "constant_time_instinct_fusion": True,
            "hot_path_history_scan": False,
            "hot_path_io": False,
            "methodology_selected_immediately": True,
        },
        "challenge_set": {"r8": 228, "r6": 278},
        "r5_opened": False,
        "new_holdout_opened": False,
        "passes_calibration": frozen_policy is not None,
        "frozen_policy": frozen_policy,
        "policy_results": results,
        "best_diagnostic_policy": None if not results else results[0]["policy"],
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
