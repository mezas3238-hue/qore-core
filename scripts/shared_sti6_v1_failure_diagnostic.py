#!/usr/bin/env python3
"""STI-6 V1 continuation/positive-tail failure diagnostic.

The diagnostic uses already-consumed R6 only. Source-time trajectories are
materialized before terminal outcome labels are touched. It explains why V1
signaled almost every position and generates mechanism hypotheses for V2
without selecting a new policy or opening R5.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
    continuation_source_scores,
)

IDENTITY = "QORE_SHARED_STI6_V1_FAILURE_DIAGNOSTIC_001"


def _trajectory(observations: tuple[SharedPositionCausalObservation, ...]) -> dict[str, int]:
    if not observations:
        return {
            "observation_count": 0,
            "continuation_first_bps": 0,
            "continuation_last_bps": 0,
            "continuation_peak_bps": 0,
            "continuation_velocity_bps": 0,
            "tail_first_bps": 0,
            "tail_last_bps": 0,
            "tail_peak_bps": 0,
            "tail_velocity_bps": 0,
            "failure_first_bps": 0,
            "failure_last_bps": 0,
            "failure_peak_bps": 0,
            "failure_velocity_bps": 0,
            "coherence_last_bps": 0,
            "uncertainty_last_bps": 0,
            "signed_close_last_bps": 0,
            "efficiency_last_bps": 0,
            "progress_last_bps": 0,
        }

    scores = [continuation_source_scores(item) for item in observations]
    continuation = [row[0] for row in scores]
    tail = [row[1] for row in scores]
    failure = [row[2] for row in scores]
    last = observations[-1]
    return {
        "observation_count": len(observations),
        "continuation_first_bps": continuation[0],
        "continuation_last_bps": continuation[-1],
        "continuation_peak_bps": max(continuation),
        "continuation_velocity_bps": continuation[-1] - continuation[0],
        "tail_first_bps": tail[0],
        "tail_last_bps": tail[-1],
        "tail_peak_bps": max(tail),
        "tail_velocity_bps": tail[-1] - tail[0],
        "failure_first_bps": failure[0],
        "failure_last_bps": failure[-1],
        "failure_peak_bps": max(failure),
        "failure_velocity_bps": failure[-1] - failure[0],
        "coherence_last_bps": scores[-1][3],
        "uncertainty_last_bps": scores[-1][4],
        "signed_close_last_bps": last.signed_close_r_bps,
        "efficiency_last_bps": last.efficiency_bps,
        "progress_last_bps": last.progress_bps,
    }


def _mean(rows: list[dict[str, int]], key: str) -> int:
    if not rows:
        return 0
    return sum(row[key] for row in rows) // len(rows)


def _profile(rows: list[dict[str, int]]) -> dict[str, int]:
    if not rows:
        return {}
    return {key: _mean(rows, key) for key in rows[0]}


def _delta(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    keys = sorted(set(left) & set(right))
    return {key: left[key] - right[key] for key in keys}


def run(
    *,
    frozen_policy_path: Path,
    r6_trades: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
) -> dict[str, object]:
    frozen = json.loads(frozen_policy_path.read_text())
    if frozen.get("identity") != base.IDENTITY:
        raise ValueError("unexpected frozen STI-6 policy identity")
    policy = base._sti6_policy(frozen)

    sequences = base._source_sequences(
        partition="r6",
        trades_path=r6_trades,
        nas_path=r6_nas,
        sp_path=r6_sp,
        us_path=r6_us,
    )
    materialized: list[tuple[dict[str, object], dict[str, int], bool, bool]] = []
    source_observation_count = 0

    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(
            tuple[SharedPositionCausalObservation, ...],
            sequence["observations"],
        )
        source_observation_count += len(observations)
        features = _trajectory(observations)
        continuation_hit = any(
            continuation_source_scores(obs)[0]
            >= policy.continuation_threshold_bps
            and continuation_source_scores(obs)[0]
            > continuation_source_scores(obs)[2]
            for obs in observations
        )
        tail_hit = any(
            continuation_source_scores(obs)[1]
            >= policy.positive_tail_threshold_bps
            and continuation_source_scores(obs)[1]
            > continuation_source_scores(obs)[2]
            for obs in observations
        )
        materialized.append((row, features, continuation_hit, tail_hit))

    groups: dict[str, list[dict[str, int]]] = {
        "TAIL_GE_2R": [],
        "WINNER_LT_2R": [],
        "LOSS": [],
    }
    signal_histogram: Counter[str] = Counter()
    for row, features, continuation_hit, tail_hit in materialized:
        # Terminal outcome is intentionally touched only after source trajectories.
        final_r = Decimal(str(row["net_r_after_friction"]))
        if final_r >= base.POSITIVE_TAIL_R:
            group = "TAIL_GE_2R"
        elif final_r > 0:
            group = "WINNER_LT_2R"
        else:
            group = "LOSS"
        groups[group].append(features)
        signal_histogram[
            f"{group}|CONT={int(continuation_hit)}|TAIL={int(tail_hit)}"
        ] += 1

    profiles = {key: _profile(value) for key, value in groups.items()}
    tail_vs_loss = _delta(profiles["TAIL_GE_2R"], profiles["LOSS"])
    tail_vs_normal_winner = _delta(
        profiles["TAIL_GE_2R"],
        profiles["WINNER_LT_2R"],
    )

    hypotheses: list[dict[str, object]] = []
    acceleration = max(
        tail_vs_loss.get("tail_velocity_bps", 0),
        tail_vs_loss.get("continuation_velocity_bps", 0),
    )
    if acceleration >= 500:
        hypotheses.append(
            {
                "hypothesis": "V2_TRAJECTORY_ACCELERATION_NOT_LEVEL",
                "evidence": {
                    "tail_minus_loss_continuation_velocity_bps": tail_vs_loss.get(
                        "continuation_velocity_bps", 0
                    ),
                    "tail_minus_loss_positive_tail_velocity_bps": tail_vs_loss.get(
                        "tail_velocity_bps", 0
                    ),
                },
                "meaning": (
                    "Positive tails may be distinguished by improving trajectory, "
                    "not by crossing a static continuation level once."
                ),
            }
        )

    local_progress = max(
        tail_vs_loss.get("signed_close_last_bps", 0),
        tail_vs_loss.get("efficiency_last_bps", 0),
        tail_vs_loss.get("progress_last_bps", 0),
    )
    if local_progress >= 500:
        hypotheses.append(
            {
                "hypothesis": "V2_LOCAL_EXPANSION_PERSISTENCE",
                "evidence": {
                    key: tail_vs_loss.get(key, 0)
                    for key in (
                        "signed_close_last_bps",
                        "efficiency_last_bps",
                        "progress_last_bps",
                    )
                },
                "meaning": (
                    "Positive-tail support may require persistent realized local "
                    "expansion rather than generic world support."
                ),
            }
        )

    failure_separation = (
        profiles["LOSS"].get("failure_last_bps", 0)
        - profiles["TAIL_GE_2R"].get("failure_last_bps", 0)
    )
    if failure_separation >= 500:
        hypotheses.append(
            {
                "hypothesis": "V2_FAILURE_HAZARD_VETO",
                "evidence": {
                    "loss_minus_tail_failure_last_bps": failure_separation,
                },
                "meaning": (
                    "Continuation support should be vetoed when failure hazard "
                    "remains structurally high even if continuation level is elevated."
                ),
            }
        )

    tail_vs_winner_velocity = max(
        tail_vs_normal_winner.get("tail_velocity_bps", 0),
        tail_vs_normal_winner.get("continuation_velocity_bps", 0),
    )
    if tail_vs_winner_velocity >= 300:
        hypotheses.append(
            {
                "hypothesis": "V2_POSITIVE_TAIL_SEPARATE_FROM_GENERIC_WINNER",
                "evidence": {
                    "tail_minus_normal_winner_continuation_velocity_bps": (
                        tail_vs_normal_winner.get(
                            "continuation_velocity_bps", 0
                        )
                    ),
                    "tail_minus_normal_winner_tail_velocity_bps": (
                        tail_vs_normal_winner.get("tail_velocity_bps", 0)
                    ),
                },
                "meaning": (
                    "A positive-tail head should be distinct from a generic winner "
                    "continuation head rather than sharing one threshold family."
                ),
            }
        )

    if not hypotheses:
        hypotheses.append(
            {
                "hypothesis": "V2_REPRESENTATION_INSUFFICIENT_REQUIRES_NEW_SENSOR",
                "evidence": {
                    "tail_vs_loss_profile_delta": tail_vs_loss,
                    "tail_vs_normal_winner_profile_delta": tail_vs_normal_winner,
                },
                "meaning": (
                    "The current source representation does not materially separate "
                    "positive tails; V2 should seek new causal sensors rather than "
                    "retune V1 thresholds."
                ),
            }
        )

    return {
        "identity": IDENTITY,
        "status": "STI6_V1_FAILURE_KNOWLEDGE_EXTRACTED_NO_RETUNING",
        "partition": "R6_CONSUMED_ONLY",
        "trade_count": len(sequences),
        "source_observation_count": source_observation_count,
        "group_counts": {key: len(value) for key, value in groups.items()},
        "signal_histogram": dict(sorted(signal_histogram.items())),
        "trajectory_profiles_bps": profiles,
        "tail_minus_loss_delta_bps": tail_vs_loss,
        "tail_minus_normal_winner_delta_bps": tail_vs_normal_winner,
        "v2_hypothesis_candidates": hypotheses,
        "governance": {
            "v1_policy_changed": False,
            "v1_thresholds_changed": False,
            "v1_reopened": False,
            "v2_policy_selected": False,
            "r5_opened": False,
            "future_market_used_for_source_trajectory": False,
            "terminal_outcome_used_only_after_source_materialization": True,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        frozen_policy_path=args.policy,
        r6_trades=args.r6_trades,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "status": payload["status"],
                "group_counts": payload["group_counts"],
                "v2_hypothesis_candidates": payload["v2_hypothesis_candidates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
