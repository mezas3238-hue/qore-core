"""VT31 laboratory for generic dynamic deterioration / recovery intelligence.

VT31 remains a falsification laboratory only.  The market-transition model under
test lives in generic Shared Core and knows nothing about this trader.  This
adapter translates the already-causal journey observations from the consumed
R8/R6 research sets into the generic transition contract.

No R5 or fresh holdout is opened here.  No numeric threshold grid is tuned.
Three semantic policies test whether the richer trajectory representation can
separate genuine deterioration from temporary adverse movement while preserving
V15 entry selection.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_cross_market_journey_defense_v18 as v18

from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryState,
    MarketTransitionObservation,
    assess_market_trajectory,
)

SCHEMA = "qore.core_stack_v4.vt31.dynamic_deterioration_recovery.v19"
IDENTITY = "VT31_NAS100_SHARED_DYNAMIC_DETERIORATION_RECOVERY_V19"
ZERO = Decimal("0")
DD_HARD_MAX_R = Decimal("6")
TRAJECTORY_WINDOW = 6


@dataclass(frozen=True, slots=True)
class SemanticDefensePolicy:
    name: str
    defend_states: tuple[MarketTrajectoryState, ...]

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "defend_states": tuple(state.value for state in self.defend_states),
            "numeric_threshold_grid_search": False,
        }


POLICIES = (
    SemanticDefensePolicy(
        "FAILURE_ONLY",
        (MarketTrajectoryState.FAILURE,),
    ),
    SemanticDefensePolicy(
        "DETERIORATION_OR_FAILURE",
        (
            MarketTrajectoryState.DETERIORATING,
            MarketTrajectoryState.FAILURE,
        ),
    ),
    SemanticDefensePolicy(
        "DIVERGENCE_ESCALATION",
        (
            MarketTrajectoryState.DIVERGING,
            MarketTrajectoryState.DETERIORATING,
            MarketTrajectoryState.FAILURE,
        ),
    ),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _clamp_bps(value: int) -> int:
    return max(0, min(10_000, value))


def _signed_bps(value: Decimal, *, span: Decimal = Decimal("1")) -> int:
    if span <= 0:
        raise ValueError("span must be positive")
    clipped = max(-span, min(span, value))
    normalized = clipped / span
    return _clamp_bps(int((normalized + Decimal("1")) * Decimal("5000")))


def _adverse_bps(value: Decimal, *, span: Decimal = Decimal("1")) -> int:
    if value >= 0:
        return 0
    return _clamp_bps(int(min(Decimal("1"), -value / span) * Decimal("10000")))


def _breadth_support(value: str) -> int:
    return {
        "3_SUPPORT": 9500,
        "2_SUPPORT": 8000,
        "SPLIT": 5000,
        "NEUTRAL": 5000,
        "2_ADVERSE": 2500,
        "3_ADVERSE": 1000,
    }.get(value, 3500)


def _breadth_adverse(value: str) -> int:
    return {
        "3_SUPPORT": 500,
        "2_SUPPORT": 1500,
        "SPLIT": 5000,
        "NEUTRAL": 3500,
        "2_ADVERSE": 7500,
        "3_ADVERSE": 9500,
    }.get(value, 5000)


def _peer_correlation(value: str) -> int:
    return {
        "BOTH_SUPPORT": 9000,
        "BOTH_ADVERSE": 9000,
        "DIVERGENT": 1500,
        "MIXED_NEUTRAL": 4500,
        "INCOMPLETE": 2000,
    }.get(value, 3500)


def _mode_stability(value: str) -> int:
    upper = value.upper()
    if "ANOM" in upper:
        return 1500
    if "TRANSITION" in upper:
        return 3500
    if "TREND" in upper:
        return 8500
    if "RANGE" in upper:
        return 6500
    return 5000


def _transition_sign(value: str) -> int:
    upper = value.upper()
    if "ADVERSE" in upper:
        return -1
    if "SUPPORT" in upper:
        return 1
    return 0


def _contradiction_bps(event: dict[str, object]) -> int:
    peer = str(event["peer_sync3"])
    breadth3 = str(event["breadth3"])
    breadth10 = str(event["breadth10"])
    sp = str(event["sp500_transition"])
    us = str(event["us30_transition"])
    if peer == "DIVERGENT":
        return 8500
    b3 = _transition_sign(breadth3)
    b10 = _transition_sign(breadth10)
    if b3 and b10 and b3 != b10:
        return 8200
    sp_sign = _transition_sign(sp)
    us_sign = _transition_sign(us)
    if sp_sign and us_sign and sp_sign != us_sign:
        return 7200
    if peer == "MIXED_NEUTRAL" or breadth3 == "SPLIT":
        return 5000
    return 1800


def _uncertainty_bps(event: dict[str, object]) -> int:
    peer = str(event["peer_sync3"])
    breadth3 = str(event["breadth3"])
    breadth10 = str(event["breadth10"])
    mode = str(event["mode"]).upper()
    uncertainty = 1800
    if peer == "INCOMPLETE":
        uncertainty = 9000
    elif peer == "DIVERGENT":
        uncertainty = 6800
    elif peer == "MIXED_NEUTRAL":
        uncertainty = 5200
    if breadth3 == "SPLIT" or breadth10 == "SPLIT":
        uncertainty = max(uncertainty, 6200)
    if "TRANSITION" in mode:
        uncertainty = max(uncertainty, 5800)
    if "ANOM" in mode:
        uncertainty = max(uncertainty, 8000)
    return uncertainty


def _anomaly_bps(event: dict[str, object]) -> int:
    mode = str(event["mode"]).upper()
    if "ANOM" in mode:
        return 9000
    if "TRANSITION" in mode:
        return 4500
    return 1200


def _to_observation(
    row: dict[str, object],
    event: dict[str, object],
) -> MarketTransitionObservation:
    efficiency = _d(event["efficiency"])
    signed_body = _d(event["signed_body_r"])
    close_r = _d(event["close_r"])
    overlap = max(ZERO, min(Decimal("1"), _d(event["overlap"])))
    breadth3 = str(event["breadth3"])
    breadth10 = str(event["breadth10"])
    peer = str(event["peer_sync3"])

    cross_confirmation = (
        _breadth_support(breadth3) + _breadth_support(breadth10)
    ) // 2
    trend_support = (
        _signed_bps(efficiency)
        + _signed_bps(close_r)
        + cross_confirmation
    ) // 3
    momentum = (
        _signed_bps(efficiency) + _signed_bps(signed_body)
    ) // 2
    displacement = _signed_bps(signed_body)
    liquidity_capacity = _clamp_bps(
        10_000 - int(overlap * Decimal("5000"))
    )
    volatility_stability = _mode_stability(str(event["mode"]))
    correlation_stability = _peer_correlation(peer)
    contradiction = _contradiction_bps(event)
    anomaly = _anomaly_bps(event)
    uncertainty = _uncertainty_bps(event)
    opposite_pressure = max(
        _adverse_bps(close_r),
        _adverse_bps(efficiency),
        _adverse_bps(signed_body),
        _breadth_adverse(breadth3),
    )
    data_integrity = 7000 if peer == "INCOMPLETE" else 10_000

    filled_at = v18.v2.v3._dt(cast(object, row["filled_at"]))
    as_of = filled_at + timedelta(minutes=int(event["minutes_since_fill"]))
    return MarketTransitionObservation(
        as_of=as_of,
        data_integrity_bps=data_integrity,
        trend_support_bps=trend_support,
        momentum_bps=momentum,
        displacement_bps=displacement,
        liquidity_capacity_bps=liquidity_capacity,
        volatility_stability_bps=volatility_stability,
        cross_market_confirmation_bps=cross_confirmation,
        correlation_stability_bps=correlation_stability,
        contradiction_bps=contradiction,
        anomaly_bps=anomaly,
        uncertainty_bps=uncertainty,
        opposite_pressure_bps=opposite_pressure,
    )


def _annotate_trajectory(
    prepared: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    annotated: list[dict[str, object]] = []
    state_histogram: Counter[str] = Counter()
    transition_histogram: Counter[str] = Counter()
    first_risk_state: Counter[str] = Counter()

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        history: list[MarketTransitionObservation] = []
        events: list[dict[str, object]] = []
        previous_state: str | None = None
        first_risk: str | None = None

        for raw_event in cast(list[dict[str, object]], item["events"]):
            observation = _to_observation(row, raw_event)
            history.append(observation)
            assessment = assess_market_trajectory(
                tuple(history[-TRAJECTORY_WINDOW:])
            )
            state = assessment.state.value
            state_histogram[state] += 1
            if previous_state is not None and previous_state != state:
                transition_histogram[f"{previous_state}->{state}"] += 1
            previous_state = state
            if (
                first_risk is None
                and assessment.state
                in {
                    MarketTrajectoryState.DIVERGING,
                    MarketTrajectoryState.DETERIORATING,
                    MarketTrajectoryState.FAILURE,
                }
            ):
                first_risk = state
                first_risk_state[state] += 1
            events.append(
                {
                    **raw_event,
                    "trajectory_state": state,
                    "trajectory_support_bps": assessment.support_bps,
                    "trajectory_adversity_bps": assessment.adversity_bps,
                    "trajectory_pressure_bps": (
                        assessment.deterioration_pressure_bps
                    ),
                    "trajectory_deterioration_velocity_bps": (
                        assessment.deterioration_velocity_bps
                    ),
                    "trajectory_recovery_velocity_bps": (
                        assessment.recovery_velocity_bps
                    ),
                    "trajectory_deterioration_persistence_bps": (
                        assessment.deterioration_persistence_bps
                    ),
                    "trajectory_recovery_persistence_bps": (
                        assessment.recovery_persistence_bps
                    ),
                    "trajectory_reasons": assessment.reasons,
                }
            )

        annotated.append({**item, "events": events})

    diagnostics = {
        "trajectory_window": TRAJECTORY_WINDOW,
        "state_histogram": dict(sorted(state_histogram.items())),
        "transition_histogram": dict(sorted(transition_histogram.items())),
        "first_risk_state_histogram": dict(sorted(first_risk_state.items())),
        "numeric_threshold_grid_search": False,
        "representation": (
            "CAUSAL_MULTI_OBSERVATION_SUPPORT_ADVERSITY_VELOCITY_"
            "PERSISTENCE_RECOVERY"
        ),
    }
    return annotated, diagnostics


def _event_matches(
    event: dict[str, object],
    policy: SemanticDefensePolicy,
) -> bool:
    state = MarketTrajectoryState(str(event["trajectory_state"]))
    return state in policy.defend_states


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    policy: SemanticDefensePolicy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    selected_baseline: list[Decimal] = []
    shared_values: list[Decimal] = []
    rejected: list[dict[str, object]] = []
    defended: list[dict[str, object]] = []
    defense_states: Counter[str] = Counter()

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
            if _event_matches(event, policy):
                shared_r = _d(event["defense_r_after_friction"])
                state = str(event["trajectory_state"])
                defense_states[state] += 1
                defended.append(
                    {
                        "signal_at": row["signal_at"],
                        "baseline_r": format(baseline_r, "f"),
                        "defense_r": format(shared_r, "f"),
                        "uplift_r": format(shared_r - baseline_r, "f"),
                        "trajectory_state": state,
                        "minutes_since_fill": event["minutes_since_fill"],
                        "trajectory_pressure_bps": event[
                            "trajectory_pressure_bps"
                        ],
                        "trajectory_deterioration_velocity_bps": event[
                            "trajectory_deterioration_velocity_bps"
                        ],
                        "trajectory_reasons": event["trajectory_reasons"],
                    }
                )
                break
        shared_values.append(shared_r)

    baseline = v18.v17._metrics(baseline_values)
    selected = v18.v17._metrics(selected_baseline)
    shared = v18.v17._metrics(shared_values)
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
        "shared_v19": shared,
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
            "defense_state_histogram": dict(sorted(defense_states.items())),
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
    shared = cast(dict[str, object], result["shared_v19"])
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


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not gates or not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v19"])
    journey = cast(dict[str, object], result["journey"])
    dd = max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
    return (
        _d(shared["profit_factor"])
        / _d(baseline["profit_factor"])
        * DD_HARD_MAX_R
        / dd
        * _d(journey["selected_winner_r_retention_after_defense"])
    )


def _diagnostic_score(result: dict[str, object]) -> Decimal:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v19"])
    selection = cast(dict[str, object], result["selection"])
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
        * _d(selection["winner_r_retention"])
        * _d(journey["selected_winner_r_retention_after_defense"])
    )


def _governance() -> dict[str, bool]:
    return {
        "vt31_is_falsification_lab_only": True,
        "generic_shared_transition_module_used": True,
        "v15_entry_identity_base": True,
        "sequence_representation_used": True,
        "transition_velocity_used": True,
        "transition_persistence_used": True,
        "recovery_intelligence_present": True,
        "semantic_state_policies_only": True,
        "numeric_threshold_grid_search_used": False,
        "r5_opened": False,
        "new_holdout_opened": False,
        "three_index_post_entry_closed_m1_used": True,
        "defense_next_m1_open_only": True,
        "runtime_equity_curve_used": False,
        "runtime_prior_trade_outcomes_used": False,
        "runtime_current_outcome_used": False,
        "historical_outcomes_offline_evaluation_only": True,
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
    daily = v18.v2.v3._load_daily(daily_path)
    r8 = v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6 = v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v18.v8._negative_tables(r8)
    r8_n1 = [
        row
        for row in r8
        if v18.v13._negative_views(row, negative) == 1
    ]
    model, feature_diagnostics = v18.v13._learn_model(r8_n1)

    p8 = v18._prepare_fold(
        r8,
        negative=negative,
        model=model,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6 = v18._prepare_fold(
        r6,
        negative=negative,
        model=model,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    a8, trajectory_r8 = _annotate_trajectory(p8)
    a6, trajectory_r6 = _annotate_trajectory(p6)

    policy_results: list[dict[str, object]] = []
    passing: list[
        tuple[
            Decimal,
            SemanticDefensePolicy,
            dict[str, object],
            dict[str, object],
        ]
    ] = []

    for policy in POLICIES:
        r8_result = _evaluate(a8, policy=policy)
        r6_result = _evaluate(a6, policy=policy)
        r8_gates = _gates(r8_result)
        r6_gates = _gates(r6_result)
        joint_pass = all(r8_gates.values()) and all(r6_gates.values())
        r8_score = _score(r8_result)
        r6_score = _score(r6_result)
        diagnostic = (
            _diagnostic_score(r8_result) + _diagnostic_score(r6_result)
        ) / Decimal("2")
        policy_results.append(
            {
                "policy": policy.payload(),
                "r8": {
                    "evaluation": r8_result,
                    "gates": r8_gates,
                    "score": None
                    if r8_score is None
                    else format(r8_score, "f"),
                },
                "r6": {
                    "evaluation": r6_result,
                    "gates": r6_gates,
                    "score": None
                    if r6_score is None
                    else format(r6_score, "f"),
                },
                "passes_both_consumed_folds": joint_pass,
                "diagnostic_score": format(diagnostic, "f"),
            }
        )
        if joint_pass:
            assert r8_score is not None
            assert r6_score is not None
            passing.append(
                (
                    (r8_score + r6_score) / Decimal("2"),
                    policy,
                    r8_result,
                    r6_result,
                )
            )

    policy_results.sort(
        key=lambda item: _d(item["diagnostic_score"]),
        reverse=True,
    )

    frozen_policy: dict[str, object] | None = None
    if passing:
        passing.sort(key=lambda item: item[0], reverse=True)
        score, policy, _, _ = passing[0]
        frozen_policy = {
            "v15_entry_policy": v18.v15.POLICY.payload(),
            "v15_coherence_veto": sorted(v18.v15.UNILATERAL_LEADERS),
            "dynamic_transition_defense": policy.payload(),
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
        "representation": {
            "generic_module": (
                "qore.infrastructure.core_stack_v2.transition_intelligence"
            ),
            "continuous_evidence_primary": True,
            "semantic_state_summary_secondary": True,
            "trajectory_r8": trajectory_r8,
            "trajectory_r6": trajectory_r6,
            "feature_model": feature_diagnostics,
        },
        "semantic_policy_results": policy_results,
        "best_diagnostic_policy": (
            None if not policy_results else policy_results[0]["policy"]
        ),
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
                "semantic_policy_results": payload[
                    "semantic_policy_results"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
