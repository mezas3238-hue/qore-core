"""VT31 Shared natural DD pre-entry sequence topology atlas V33.

Phase-1 diagnostic only.

V32 proved that a final adverse snapshot is insufficient: a +67R winner can
share the same final adverse signature as many losses. V33 therefore preserves
the complete causal eight-M1 pre-entry path and studies HOW the market arrived
at its final resident state.

No trades are changed. No sizing, capital weighting, abstention, stop/target
mutation, trailing or target extension. Outcomes remain offline labels only.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_natural_dd_winner_counter_signature_v32 as v32

from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentObservation,
    assess_market_environment,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTransitionObservation,
    assess_market_trajectory,
)

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_preentry_sequence_topology.v33"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_PREENTRY_SEQUENCE_TOPOLOGY_V33"
ZERO = Decimal("0")
v31 = v32.v31
v30 = v31.v30
v28 = v30.v28
v27 = v28.v27
v26 = v27.v26
v24 = v26.v24
v18 = v26.v18

FEATURES = (
    "trajectory_support_bps",
    "trajectory_adversity_bps",
    "trajectory_pressure_bps",
    "environment_support_bps",
    "environment_adverse_bps",
    "cross_market_confirmation_bps",
    "correlation_stability_bps",
    "momentum_bps",
    "displacement_bps",
    "contradiction_bps",
    "opposite_pressure_bps",
    "anomaly_bps",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _compress(states: list[str]) -> tuple[str, ...]:
    output: list[str] = []
    for state in states:
        if not output or output[-1] != state:
            output.append(state)
    return tuple(output)


def _delta_label(start: int, end: int) -> str:
    if end > start:
        return "RISING"
    if end < start:
        return "FALLING"
    return "FLAT"


def _path_label(values: list[int]) -> str:
    if len(values) < 2:
        return "INSUFFICIENT"
    rising = sum(right > left for left, right in zip(values, values[1:], strict=False))
    falling = sum(right < left for left, right in zip(values, values[1:], strict=False))
    if rising > falling:
        return "MOSTLY_RISING"
    if falling > rising:
        return "MOSTLY_FALLING"
    return "MIXED"


def _transition_row(
    transition: MarketTransitionObservation,
    trajectory: object,
    environment: object,
) -> dict[str, object]:
    traj = cast(object, trajectory)
    env = cast(object, environment)
    return {
        "as_of": transition.as_of.isoformat(),
        "trajectory_state": traj.state.value,
        "trajectory_support_bps": traj.support_bps,
        "trajectory_adversity_bps": traj.adversity_bps,
        "trajectory_pressure_bps": traj.deterioration_pressure_bps,
        "trajectory_deterioration_velocity_bps": traj.deterioration_velocity_bps,
        "trajectory_recovery_velocity_bps": traj.recovery_velocity_bps,
        "trajectory_deterioration_persistence_bps": traj.deterioration_persistence_bps,
        "trajectory_recovery_persistence_bps": traj.recovery_persistence_bps,
        "environment_state": env.state.value,
        "environment_support_bps": env.market_support_bps,
        "environment_adverse_bps": env.adverse_environment_bps,
        "environment_adverse_velocity_bps": env.adverse_velocity_bps,
        "environment_recovery_velocity_bps": env.recovery_velocity_bps,
        "environment_adverse_persistence_bps": env.adverse_persistence_bps,
        "environment_recovery_persistence_bps": env.recovery_persistence_bps,
        "cross_market_fragility_bps": env.cross_market_fragility_bps,
        "structural_fragility_bps": env.structural_fragility_bps,
        "trend_support_bps": transition.trend_support_bps,
        "momentum_bps": transition.momentum_bps,
        "displacement_bps": transition.displacement_bps,
        "cross_market_confirmation_bps": transition.cross_market_confirmation_bps,
        "correlation_stability_bps": transition.correlation_stability_bps,
        "contradiction_bps": transition.contradiction_bps,
        "anomaly_bps": transition.anomaly_bps,
        "uncertainty_bps": transition.uncertainty_bps,
        "opposite_pressure_bps": transition.opposite_pressure_bps,
    }


def _sequence(
    *,
    item: dict[str, object],
    sp_by_day: object,
    us_by_day: object,
) -> dict[str, object]:
    row = cast(dict[str, object], item["row"])
    setup = item["setup"]
    day_bars = cast(tuple[object, ...], item["day_bars"])
    fill_index, _ = v18.counter._fill_and_exit_indices(setup, day_bars, row)
    side = cast(str, row["side"])
    local_day = date.fromisoformat(cast(str, row["local_date"]))
    start = max(0, fill_index - v24.PREENTRY_BARS)

    transitions: list[MarketTransitionObservation] = []
    environment_observations: list[MarketEnvironmentObservation] = []
    path: list[dict[str, object]] = []

    for index in range(start, fill_index):
        bar = day_bars[index]
        as_of = cast(object, bar).closed_at
        nas = tuple(day_bars[: index + 1])
        sp = tuple(v18.v13._eligible(sp_by_day, local_day, as_of))
        us = tuple(v18.v13._eligible(us_by_day, local_day, as_of))
        transition = v24._market_transition_observation(
            as_of=as_of,
            side=side,
            nas=nas,
            sp=sp,
            us=us,
        )
        transitions.append(transition)
        trajectory = assess_market_trajectory(
            tuple(transitions[-v24.TRAJECTORY_WINDOW:])
        )
        environment_observations.append(
            v24._environment_observation(transition, trajectory)
        )
        environment = assess_market_environment(
            tuple(environment_observations[-v24.ENVIRONMENT_WINDOW:])
        )
        path.append(_transition_row(transition, trajectory, environment))

    if not path:
        raise AssertionError("missing pre-entry sequence")

    trajectory_states = [str(x["trajectory_state"]) for x in path]
    environment_states = [str(x["environment_state"]) for x in path]
    summary: dict[str, object] = {
        "observation_count": len(path),
        "trajectory_state_sequence": ">".join(_compress(trajectory_states)),
        "environment_state_sequence": ">".join(_compress(environment_states)),
        "trajectory_terminal_3": ">".join(trajectory_states[-3:]),
        "environment_terminal_3": ">".join(environment_states[-3:]),
    }

    for feature in FEATURES:
        values = [int(x[feature]) for x in path]
        summary[f"{feature}_start"] = values[0]
        summary[f"{feature}_end"] = values[-1]
        summary[f"{feature}_delta"] = values[-1] - values[0]
        summary[f"{feature}_delta_label"] = _delta_label(values[0], values[-1])
        summary[f"{feature}_path_label"] = _path_label(values)

    support_delta = int(summary["trajectory_support_bps_delta"])
    adversity_delta = int(summary["trajectory_adversity_bps_delta"])
    pressure_delta = int(summary["trajectory_pressure_bps_delta"])
    opposite_delta = int(summary["opposite_pressure_bps_delta"])
    cross_delta = int(summary["cross_market_confirmation_bps_delta"])
    momentum_delta = int(summary["momentum_bps_delta"])

    if support_delta > 0 and adversity_delta < 0 and pressure_delta < 0:
        macro_turn = "RECOVERY_CONVERGENCE"
    elif support_delta < 0 and adversity_delta > 0 and pressure_delta > 0:
        macro_turn = "DETERIORATION_CONVERGENCE"
    else:
        macro_turn = "MIXED_TRANSITION"

    if momentum_delta > 0 and cross_delta > 0 and opposite_delta < 0:
        micro_turn = "MOMENTUM_CROSS_RECOVERY"
    elif momentum_delta < 0 and cross_delta < 0 and opposite_delta > 0:
        micro_turn = "MOMENTUM_CROSS_DETERIORATION"
    else:
        micro_turn = "MIXED_MICROSTRUCTURE"

    summary["macro_turn"] = macro_turn
    summary["micro_turn"] = micro_turn
    summary["path"] = path
    return summary


def _group_stats(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {"sample": 0, "total_r": "0"}
    result: dict[str, object] = {
        "sample": len(rows),
        "total_r": format(sum((_d(x["baseline_r"]) for x in rows), ZERO), "f"),
    }
    for feature in (
        "trajectory_support_bps_delta",
        "trajectory_adversity_bps_delta",
        "trajectory_pressure_bps_delta",
        "environment_support_bps_delta",
        "environment_adverse_bps_delta",
        "cross_market_confirmation_bps_delta",
        "momentum_bps_delta",
        "opposite_pressure_bps_delta",
    ):
        values = [int(cast(dict[str, object], x["sequence"])[feature]) for x in rows]
        result[feature] = {
            "min": min(values),
            "mean": sum(values) // len(values),
            "max": max(values),
        }
    return result


def _atlas(
    rows: list[dict[str, object]],
    *,
    key: str,
) -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        seq = cast(dict[str, object], row["sequence"])
        groups[str(seq[key])].append(row)

    result: list[dict[str, object]] = []
    for value, members in groups.items():
        wins = [x for x in members if x["outcome"] == "WIN"]
        losses = [x for x in members if x["outcome"] == "LOSS"]
        winner_r = sum((_d(x["baseline_r"]) for x in wins), ZERO)
        loss_r = -sum((_d(x["baseline_r"]) for x in losses), ZERO)
        result.append(
            {
                "value": value,
                "sample": len(members),
                "wins": len(wins),
                "losses": len(losses),
                "winner_r": format(winner_r, "f"),
                "loss_r": format(loss_r, "f"),
                "top3_dd_losses": sum(bool(x["in_top3_dd_excursions"]) for x in losses),
                "unobservable_losses": sum(bool(x["unobservable_loss"]) for x in losses),
                "net_r": format(winner_r - loss_r, "f"),
            }
        )
    result.sort(
        key=lambda x: (
            int(x["top3_dd_losses"]),
            int(x["losses"]),
            -int(x["wins"]),
        ),
        reverse=True,
    )
    return result


def _fold(
    prepared: list[dict[str, object]],
    *,
    sp_evidence: Path,
    us_evidence: Path,
) -> dict[str, object]:
    excursions = v30._drawdown_excursions(prepared)
    base_rows = v30._signature_rows(prepared, excursions)
    by_signal = {str(x["signal_at"]): x for x in base_rows}
    hypothesis = next(
        h for h in v31.HYPOTHESES if h.name == "COMPOSITE_PRECISION_ORIGIN"
    )

    sp_by_day = v18.v13._group_market(sp_evidence)
    us_by_day = v18.v13._group_market(us_evidence)
    annotated: list[dict[str, object]] = []

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        base = by_signal[str(row["signal_at"])]
        if not hypothesis.matches(base):
            continue
        annotated.append(
            {
                **base,
                "sequence": _sequence(
                    item=item,
                    sp_by_day=sp_by_day,
                    us_by_day=us_by_day,
                ),
            }
        )

    losses = [x for x in annotated if x["outcome"] == "LOSS"]
    winners = [x for x in annotated if x["outcome"] == "WIN"]
    large_winners = [x for x in winners if _d(x["baseline_r"]) >= Decimal("5")]
    top3_losses = [x for x in losses if bool(x["in_top3_dd_excursions"])]

    keys = (
        "trajectory_state_sequence",
        "environment_state_sequence",
        "trajectory_terminal_3",
        "environment_terminal_3",
        "macro_turn",
        "micro_turn",
        "trajectory_pressure_bps_path_label",
        "opposite_pressure_bps_path_label",
        "cross_market_confirmation_bps_path_label",
        "momentum_bps_path_label",
    )

    return {
        "flagged_sample": len(annotated),
        "groups": {
            "FLAGGED_LOSSES": _group_stats(losses),
            "FLAGGED_TOP3_DD_LOSSES": _group_stats(top3_losses),
            "FLAGGED_WINNERS": _group_stats(winners),
            "FLAGGED_WINNERS_GE_5R": _group_stats(large_winners),
        },
        "sequence_atlases": {key: _atlas(annotated, key=key) for key in keys},
        "largest_flagged_winners": sorted(
            (
                {
                    "signal_at": x["signal_at"],
                    "baseline_r": x["baseline_r"],
                    "situation": x["situation"],
                    "environment_trajectory": x["environment_trajectory"],
                    "semantic_signature": x["semantic_signature"],
                    "sequence": x["sequence"],
                }
                for x in winners
            ),
            key=lambda x: _d(x["baseline_r"]),
            reverse=True,
        )[:20],
        "representative_top3_dd_losses": sorted(
            (
                {
                    "signal_at": x["signal_at"],
                    "baseline_r": x["baseline_r"],
                    "sequence": x["sequence"],
                }
                for x in top3_losses
            ),
            key=lambda x: str(x["signal_at"]),
        )[:30],
        "actuation_used": False,
    }


def _cross_fold(
    r8: dict[str, object],
    r6: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    a8 = cast(dict[str, list[dict[str, object]]], r8["sequence_atlases"])
    a6 = cast(dict[str, list[dict[str, object]]], r6["sequence_atlases"])
    result: dict[str, list[dict[str, object]]] = {}

    for key in a8:
        m8 = {str(x["value"]): x for x in a8[key]}
        m6 = {str(x["value"]): x for x in a6[key]}
        rows: list[dict[str, object]] = []
        for value in sorted(set(m8).intersection(m6)):
            x, y = m8[value], m6[value]
            rows.append(
                {
                    "value": value,
                    "combined_wins": int(x["wins"]) + int(y["wins"]),
                    "combined_losses": int(x["losses"]) + int(y["losses"]),
                    "combined_winner_r": format(_d(x["winner_r"]) + _d(y["winner_r"]), "f"),
                    "combined_loss_r": format(_d(x["loss_r"]) + _d(y["loss_r"]), "f"),
                    "combined_top3_dd_losses": int(x["top3_dd_losses"]) + int(y["top3_dd_losses"]),
                    "combined_unobservable_losses": int(x["unobservable_losses"]) + int(y["unobservable_losses"]),
                    "r8": x,
                    "r6": y,
                    "runtime_policy_claim": False,
                }
            )
        rows.sort(
            key=lambda x: (
                int(x["combined_top3_dd_losses"]),
                int(x["combined_losses"]),
                -int(x["combined_wins"]),
            ),
            reverse=True,
        )
        result[key] = rows
    return result


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
    daily = v32.v31.v30.v28.v27.v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(
        daily_path
    )
    r8_source = v18._load_cross_rows(
        trades=r8_trades, nas=r8_nas, sp=r8_sp, us=r8_us, daily=daily
    )
    r6_source = v18._load_cross_rows(
        trades=r6_trades, nas=r6_nas, sp=r6_sp, us=r6_us, daily=daily
    )
    if len(r8_source) != 228 or len(r6_source) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v26._prepare(
        r8_source,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v26._prepare(
        r6_source,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )

    f8 = _fold(p8, sp_evidence=r8_sp, us_evidence=r8_us)
    f6 = _fold(p6, sp_evidence=r6_sp, us_evidence=r6_us)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "DIAGNOSTIC_SEQUENCE_TOPOLOGY_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "preentry_bars": v24.PREENTRY_BARS,
        "source_hypothesis": "COMPOSITE_PRECISION_ORIGIN",
        "r8": f8,
        "r6": f6,
        "cross_fold_sequence_atlas": _cross_fold(f8, f6),
        "phase_1_contract": {
            "same_trade_universe": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "capital_weighting_used": False,
            "entry_abstention_used": False,
            "stop_geometry_mutated": False,
            "target_geometry_mutated": False,
            "trailing_used": False,
            "target_extension_used": False,
            "runtime_outcome_input_used": False,
            "future_market_input_used": False,
            "outcomes_used_offline_for_evaluation_only": True,
            "r5_opened": False,
            "new_holdout_opened": False,
        },
        "governance": {
            "vt31_is_falsification_lab_only": True,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
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
                "status": payload["status"],
                "r8_groups": payload["r8"]["groups"],
                "r6_groups": payload["r6"]["groups"],
                "cross_fold_sequence_atlas": payload["cross_fold_sequence_atlas"],
                "largest_r8_winners": payload["r8"]["largest_flagged_winners"][:10],
                "largest_r6_winners": payload["r6"]["largest_flagged_winners"][:10],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
