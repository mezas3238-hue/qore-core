"""VT31 falsification lab: terminal failure vs recoverable deterioration V20.

V19 proved that a rich dynamic trajectory representation can identify adverse
market sequences and save R on losers, but a small number of recoverable
pullbacks inside very large winners still triggered FAILURE.  V20 does not tune
numeric thresholds.  It tests semantic topology: whether a trajectory FAILURE
is corroborated by slower cross-market structural deterioration before Shared
emits DEFEND.

VT31 remains a laboratory only.  No trader-specific primitive is promoted into
Shared Core by this experiment.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_dynamic_deterioration_recovery_v19 as v19

SCHEMA = "qore.core_stack_v4.vt31.terminal_vs_recoverable_failure.v20"
IDENTITY = "VT31_NAS100_SHARED_TERMINAL_VS_RECOVERABLE_FAILURE_V20"
ZERO = Decimal("0")
DD_HARD_MAX_R = Decimal("6")


@dataclass(frozen=True, slots=True)
class FailureTopologyPolicy:
    name: str

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "numeric_threshold_grid_search": False,
            "semantic_failure_topology_only": True,
        }


POLICIES = (
    FailureTopologyPolicy("FULL_CROSS_TERMINAL"),
    FailureTopologyPolicy("SLOW_BREAK_CONVERGENCE"),
    FailureTopologyPolicy("NO_SLOW_SUPPORT_CONVERGENCE"),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _is_adverse_breadth(value: object) -> bool:
    return str(value) in {"2_ADVERSE", "3_ADVERSE"}


def _is_support_breadth(value: object) -> bool:
    return str(value) in {"2_SUPPORT", "3_SUPPORT"}


def _transition_adverse(value: object) -> bool:
    text = str(value)
    return (
        "ADVERSE" in text
        and "REVERSING_TO_SUPPORT" not in text
    )


def _terminal_match(
    event: dict[str, object],
    policy: FailureTopologyPolicy,
) -> bool:
    if str(event["trajectory_state"]) != "FAILURE":
        return False

    breadth3_bad = _is_adverse_breadth(event["breadth3"])
    breadth10_bad = _is_adverse_breadth(event["breadth10"])
    breadth10_support = _is_support_breadth(event["breadth10"])
    peers_bad = str(event["peer_sync3"]) == "BOTH_ADVERSE"
    sp_bad = _transition_adverse(event["sp500_transition"])
    us_bad = _transition_adverse(event["us30_transition"])
    slow_peer_breaks = int(sp_bad) + int(us_bad)

    if policy.name == "FULL_CROSS_TERMINAL":
        return breadth3_bad and breadth10_bad and peers_bad

    if policy.name == "SLOW_BREAK_CONVERGENCE":
        return breadth10_bad and (
            peers_bad or slow_peer_breaks == 2
        )

    if policy.name == "NO_SLOW_SUPPORT_CONVERGENCE":
        confirmations = (
            int(breadth3_bad)
            + int(peers_bad)
            + int(sp_bad)
            + int(us_bad)
        )
        return not breadth10_support and confirmations >= 2

    raise ValueError(f"unknown failure topology {policy.name}")


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    policy: FailureTopologyPolicy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    selected_baseline: list[Decimal] = []
    shared_values: list[Decimal] = []
    rejected: list[dict[str, object]] = []
    defended: list[dict[str, object]] = []
    defended_topology: Counter[str] = Counter()

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        baseline_values.append(baseline_r)
        if not bool(item["entry_keep"]):
            rejected.append(row)
            continue

        selected_baseline.append(baseline_r)
        shared_r = baseline_r
        for event in cast(list[dict[str, object]], item["events"]):
            if not _terminal_match(event, policy):
                continue
            shared_r = _d(event["defense_r_after_friction"])
            topology = policy.name
            defended_topology[topology] += 1
            defended.append(
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": format(baseline_r, "f"),
                    "defense_r": format(shared_r, "f"),
                    "uplift_r": format(shared_r - baseline_r, "f"),
                    "minutes_since_fill": event["minutes_since_fill"],
                    "trajectory_state": event["trajectory_state"],
                    "trajectory_pressure_bps": event[
                        "trajectory_pressure_bps"
                    ],
                    "trajectory_deterioration_velocity_bps": event[
                        "trajectory_deterioration_velocity_bps"
                    ],
                    "breadth3": event["breadth3"],
                    "breadth10": event["breadth10"],
                    "peer_sync3": event["peer_sync3"],
                    "sp500_transition": event["sp500_transition"],
                    "us30_transition": event["us30_transition"],
                }
            )
            break
        shared_values.append(shared_r)

    baseline = v19.v18.v17._metrics(baseline_values)
    selected = v19.v18.v17._metrics(selected_baseline)
    shared = v19.v18.v17._metrics(shared_values)

    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(
        _d(row["net_r_after_friction"]) < 0 for row in rejected
    )
    winners_sacrificed = sum(
        _d(row["net_r_after_friction"]) > 0 for row in rejected
    )
    gross_winner_r = _d(baseline["gross_winner_r"])
    sacrificed_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in rejected
            if _d(row["net_r_after_friction"]) > 0
        ),
        ZERO,
    )
    selected_winner_r = _d(selected["gross_winner_r"])
    journey_winner_retention = (
        Decimal("1")
        if selected_winner_r == 0
        else _d(shared["gross_winner_r"]) / selected_winner_r
    )
    defended_losers = [
        item for item in defended if _d(item["baseline_r"]) < 0
    ]
    defended_winners = [
        item for item in defended if _d(item["baseline_r"]) > 0
    ]

    return {
        "baseline": baseline,
        "selected_baseline_before_journey": selected,
        "shared_v20": shared,
        "selection": {
            "input": len(prepared),
            "kept": len(shared_values),
            "abstained": len(rejected),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": "0"
            if base_losses == 0
            else format(
                Decimal(losses_avoided) / Decimal(base_losses),
                "f",
            ),
            "winner_count_retention": "0"
            if base_wins == 0
            else format(
                Decimal(base_wins - winners_sacrificed) / Decimal(base_wins),
                "f",
            ),
            "winner_r_retention": "1"
            if gross_winner_r == 0
            else format(
                (gross_winner_r - sacrificed_r) / gross_winner_r,
                "f",
            ),
            "density_retained": "0"
            if not prepared
            else format(
                Decimal(len(shared_values)) / Decimal(len(prepared)),
                "f",
            ),
        },
        "journey": {
            "defended_trades": len(defended),
            "defended_baseline_losses": len(defended_losers),
            "defended_baseline_winners": len(defended_winners),
            "defense_topology_histogram": dict(
                sorted(defended_topology.items())
            ),
            "defense_total_uplift_r": format(
                sum((_d(item["uplift_r"]) for item in defended), ZERO),
                "f",
            ),
            "loser_defense_uplift_r": format(
                sum(
                    (_d(item["uplift_r"]) for item in defended_losers),
                    ZERO,
                ),
                "f",
            ),
            "winner_damage_r": format(
                -min(
                    ZERO,
                    sum(
                        (_d(item["uplift_r"]) for item in defended_winners),
                        ZERO,
                    ),
                ),
                "f",
            ),
            "selected_winner_r_retention_after_defense": format(
                journey_winner_retention,
                "f",
            ),
            "best_defense_examples": sorted(
                defended,
                key=lambda item: _d(item["uplift_r"]),
                reverse=True,
            )[:20],
            "worst_defense_examples": sorted(
                defended,
                key=lambda item: _d(item["uplift_r"]),
            )[:20],
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v20"])
    selection = cast(dict[str, object], result["selection"])
    journey = cast(dict[str, object], result["journey"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    return {
        "pf_plus_25pct": _d(shared["profit_factor"])
        >= _d(baseline["profit_factor"]) * Decimal("1.25"),
        "dd_at_most_6r": _d(shared["max_drawdown_r"]) <= DD_HARD_MAX_R,
        "total_r_not_lower": _d(shared["total_r"])
        >= _d(baseline["total_r"]),
        "loss_recall_at_least_25pct": _d(
            selection["loss_rejection_recall"]
        )
        >= Decimal("0.25"),
        "winner_count_retention_at_least_80pct": _d(
            selection["winner_count_retention"]
        )
        >= Decimal("0.80"),
        "entry_winner_r_retention_at_least_90pct": _d(
            selection["winner_r_retention"]
        )
        >= Decimal("0.90"),
        "journey_winner_r_retention_at_least_90pct": _d(
            journey["selected_winner_r_retention_after_defense"]
        )
        >= Decimal("0.90"),
        "density_at_least_55pct": _d(selection["density_retained"])
        >= Decimal("0.55"),
    }


def _diagnostic_score(result: dict[str, object]) -> Decimal:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v20"])
    journey = cast(dict[str, object], result["journey"])
    pf = (
        ZERO
        if shared["profit_factor"] is None
        else _d(shared["profit_factor"])
    )
    baseline_pf = (
        Decimal("0.000001")
        if baseline["profit_factor"] is None
        else max(_d(baseline["profit_factor"]), Decimal("0.000001"))
    )
    dd = max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
    return (
        pf
        / baseline_pf
        * Decimal("12")
        / dd
        * _d(journey["selected_winner_r_retention_after_defense"])
    )


def _governance() -> dict[str, bool]:
    return {
        "vt31_is_falsification_lab_only": True,
        "v19_dynamic_trajectory_base": True,
        "terminal_vs_recoverable_topology_tested": True,
        "slower_cross_market_confirmation_used": True,
        "semantic_topology_policies_only": True,
        "numeric_threshold_grid_search_used": False,
        "r5_opened": False,
        "new_holdout_opened": False,
        "three_index_post_entry_closed_m1_used": True,
        "defense_next_m1_open_only": True,
        "runtime_equity_curve_used": False,
        "runtime_prior_trade_outcomes_used": False,
        "runtime_current_outcome_used": False,
        "future_m1_used": False,
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
    daily = v19.v18.v2.v3._load_daily(daily_path)
    r8 = v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6 = v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v19.v18.v8._negative_tables(r8)
    r8_n1 = [
        row
        for row in r8
        if v19.v18.v13._negative_views(row, negative) == 1
    ]
    model, feature_diagnostics = v19.v18.v13._learn_model(r8_n1)

    p8 = v19.v18._prepare_fold(
        r8,
        negative=negative,
        model=model,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6 = v19.v18._prepare_fold(
        r6,
        negative=negative,
        model=model,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    a8, trajectory_r8 = v19._annotate_trajectory(p8)
    a6, trajectory_r6 = v19._annotate_trajectory(p6)

    results: list[dict[str, object]] = []
    passing: list[
        tuple[
            Decimal,
            FailureTopologyPolicy,
            dict[str, object],
            dict[str, object],
        ]
    ] = []

    for policy in POLICIES:
        e8 = _evaluate(a8, policy=policy)
        e6 = _evaluate(a6, policy=policy)
        g8 = _gates(e8)
        g6 = _gates(e6)
        passed = all(g8.values()) and all(g6.values())
        diagnostic = (
            _diagnostic_score(e8) + _diagnostic_score(e6)
        ) / Decimal("2")
        results.append(
            {
                "policy": policy.payload(),
                "r8": {"evaluation": e8, "gates": g8},
                "r6": {"evaluation": e6, "gates": g6},
                "passes_both_consumed_folds": passed,
                "diagnostic_score": format(diagnostic, "f"),
            }
        )
        if passed:
            passing.append((diagnostic, policy, e8, e6))

    results.sort(
        key=lambda item: _d(item["diagnostic_score"]),
        reverse=True,
    )

    frozen_policy: dict[str, object] | None = None
    if passing:
        passing.sort(key=lambda item: item[0], reverse=True)
        score, policy, _, _ = passing[0]
        frozen_policy = {
            "v15_entry_policy": v19.v18.v15.POLICY.payload(),
            "v15_coherence_veto": sorted(
                v19.v18.v15.UNILATERAL_LEADERS
            ),
            "v19_dynamic_transition_base": "FROZEN_DEFAULTS",
            "terminal_failure_topology": policy.payload(),
            "joint_score": format(score, "f"),
        }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "CALIBRATION_PASSED_NEW_HOLDOUT_REQUIRED"
            if frozen_policy is not None
            else "FALSIFIED_BEFORE_NEW_HOLDOUT"
        ),
        "owner_dd_target": {
            "preferred_band_r": [4, 6],
            "hard_max_r": "6",
        },
        "challenge_set": {"r8": 228, "r6": 278},
        "r5_opened": False,
        "new_holdout_opened": False,
        "passes_calibration": frozen_policy is not None,
        "frozen_policy": frozen_policy,
        "topology_results": results,
        "best_diagnostic_policy": (
            None if not results else results[0]["policy"]
        ),
        "representation": {
            "trajectory_r8": trajectory_r8,
            "trajectory_r6": trajectory_r6,
            "feature_model": feature_diagnostics,
            "terminal_failure_requires_slow_context": True,
            "numeric_threshold_grid_search": False,
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
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_calibration": payload["passes_calibration"],
                "frozen_policy": payload["frozen_policy"],
                "best_diagnostic_policy": payload[
                    "best_diagnostic_policy"
                ],
                "topology_results": payload["topology_results"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
