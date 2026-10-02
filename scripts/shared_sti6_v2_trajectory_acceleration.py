#!/usr/bin/env python3
"""STI-6 V2 source-only calibration and consumed-R6 causal evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import cast

import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)
from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_v2 import (
    SharedContinuationTrajectoryV2Policy,
    assess_continuation_trajectory_v2,
    continuation_trajectory_v2_features,
)

IDENTITY = "QORE_SHARED_STI6_TRAJECTORY_ACCELERATION_V2"
SEQUENCE_WINDOW = 5


def _quantile(values: list[int], fraction: float) -> int:
    if not values:
        raise ValueError("STI-6 V2 source distribution is empty")
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * fraction))
    return ordered[max(0, min(len(ordered) - 1, index))]


def _ratio(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def _freeze_policy(
    *,
    r8_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
) -> tuple[SharedContinuationTrajectoryV2Policy, dict[str, object]]:
    sequences = base._source_sequences(
        partition="r8",
        trades_path=r8_trades,
        nas_path=r8_nas,
        sp_path=r8_sp,
        us_path=r8_us,
    )
    continuation_velocity: list[int] = []
    tail_velocity: list[int] = []
    local_expansion: list[int] = []
    persistence: list[int] = []
    failure: list[int] = []
    observations_seen = 0

    for sequence in sequences:
        observations = cast(
            tuple[SharedPositionCausalObservation, ...],
            sequence["observations"],
        )
        history: list[SharedPositionCausalObservation] = []
        for observation in observations:
            history.append(observation)
            features = continuation_trajectory_v2_features(
                tuple(history),
                sequence_window=SEQUENCE_WINDOW,
            )
            observations_seen += 1
            if features[0] > 0:
                continuation_velocity.append(features[0])
            if features[1] > 0:
                tail_velocity.append(features[1])
            local_expansion.append(features[2])
            persistence.append(features[3])
            failure.append(features[4])

    policy = SharedContinuationTrajectoryV2Policy(
        policy_id="QORE_SHARED_STI6_V2_R8_SOURCE_ONLY_POLICY_001",
        sequence_window=SEQUENCE_WINDOW,
        continuation_velocity_threshold_bps=max(
            1,
            _quantile(continuation_velocity or [1], 0.65),
        ),
        tail_velocity_threshold_bps=max(
            1,
            _quantile(tail_velocity or [1], 0.75),
        ),
        local_expansion_threshold_bps=_quantile(local_expansion, 0.70),
        persistence_threshold_bps=_quantile(persistence, 0.60),
        max_failure_hazard_bps=_quantile(failure, 0.65),
        minimum_integrity_bps=9_500,
        source_only_calibration=True,
        evidence_refs=(
            "immutable-r8-open-position-source-trajectories",
            "sti6-v2-preregistration-001",
        ),
    )
    return policy, {
        "r8_trade_count": len(sequences),
        "r8_source_observation_count": observations_seen,
        "future_market_used_for_freeze": False,
        "terminal_outcome_used_for_freeze": False,
        "pnl_used_for_freeze": False,
        "thresholds": {
            "continuation_velocity_threshold_bps": (
                policy.continuation_velocity_threshold_bps
            ),
            "tail_velocity_threshold_bps": (
                policy.tail_velocity_threshold_bps
            ),
            "local_expansion_threshold_bps": (
                policy.local_expansion_threshold_bps
            ),
            "persistence_threshold_bps": policy.persistence_threshold_bps,
            "max_failure_hazard_bps": policy.max_failure_hazard_bps,
            "minimum_integrity_bps": policy.minimum_integrity_bps,
        },
    }


def _evaluate_r6(
    *,
    policy: SharedContinuationTrajectoryV2Policy,
    r6_trades: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
) -> dict[str, object]:
    sequences = base._source_sequences(
        partition="r6",
        trades_path=r6_trades,
        nas_path=r6_nas,
        sp_path=r6_sp,
        us_path=r6_us,
    )
    materialized: list[
        tuple[dict[str, object], int | None, int | None, int]
    ] = []
    source_observation_count = 0

    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(
            tuple[SharedPositionCausalObservation, ...],
            sequence["observations"],
        )
        source_observation_count += len(observations)
        first_continuation: int | None = None
        first_tail: int | None = None
        history: list[SharedPositionCausalObservation] = []
        for index, observation in enumerate(observations):
            history.append(observation)
            assessment = assess_continuation_trajectory_v2(
                tuple(history),
                policy=policy,
            )
            if (
                first_continuation is None
                and assessment.materially_supported
            ):
                first_continuation = index
            if (
                first_tail is None
                and assessment.positive_tail_candidate
            ):
                first_tail = index
        materialized.append(
            (row, first_continuation, first_tail, len(observations))
        )

    winners = tails = losses = 0
    cont_tp = cont_fp = cont_fn = 0
    tail_tp = tail_fp = tail_fn = 0
    continuation_signals = tail_signals = 0
    continuation_leads: list[int] = []
    tail_leads: list[int] = []

    for row, first_continuation, first_tail, observation_count in materialized:
        final_r = base.Decimal(str(row["net_r_after_friction"]))
        is_winner = final_r > 0
        is_tail = final_r >= base.POSITIVE_TAIL_R
        is_loss = final_r < 0
        winners += int(is_winner)
        tails += int(is_tail)
        losses += int(is_loss)

        cont_signal = first_continuation is not None
        tail_signal = first_tail is not None
        continuation_signals += int(cont_signal)
        tail_signals += int(tail_signal)

        if cont_signal and is_winner:
            cont_tp += 1
            continuation_leads.append(
                observation_count - 1 - cast(int, first_continuation)
            )
        elif cont_signal and not is_winner:
            cont_fp += 1
        elif not cont_signal and is_winner:
            cont_fn += 1

        if tail_signal and is_tail:
            tail_tp += 1
            tail_leads.append(
                observation_count - 1 - cast(int, first_tail)
            )
        elif tail_signal and not is_tail:
            tail_fp += 1
        elif not tail_signal and is_tail:
            tail_fn += 1

    cont_precision = _ratio(cont_tp, cont_tp + cont_fp)
    cont_recall = _ratio(cont_tp, cont_tp + cont_fn)
    tail_precision = _ratio(tail_tp, tail_tp + tail_fp)
    tail_recall = _ratio(tail_tp, tail_tp + tail_fn)
    false_continuation = _ratio(cont_fp, cont_tp + cont_fp)

    gate = (
        cont_precision >= base.STI6_WINNER_MIN_PRECISION_BPS
        and cont_recall >= base.STI6_WINNER_MIN_RECALL_BPS
        and tail_precision >= base.STI6_TAIL_MIN_PRECISION_BPS
        and tail_recall >= base.STI6_TAIL_MIN_RECALL_BPS
        and false_continuation
        <= base.STI6_MAX_FALSE_CONTINUATION_ON_LOSERS_BPS
    )
    return {
        "trade_count": len(sequences),
        "source_observation_count": source_observation_count,
        "outcome_population": {
            "winners": winners,
            "positive_tail_ge_2r": tails,
            "losses": losses,
        },
        "continuation_signal_count": continuation_signals,
        "positive_tail_signal_count": tail_signals,
        "winner_precision_bps": cont_precision,
        "winner_recall_bps": cont_recall,
        "positive_tail_precision_bps": tail_precision,
        "positive_tail_recall_bps": tail_recall,
        "false_continuation_on_nonwinners_bps": false_continuation,
        "median_true_winner_lead_minutes": (
            None if not continuation_leads else median(continuation_leads)
        ),
        "median_true_tail_lead_minutes": (
            None if not tail_leads else median(tail_leads)
        ),
        "gate_pass": gate,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy, calibration = _freeze_policy(
        r8_trades=args.r8_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
    )
    r6 = _evaluate_r6(
        policy=policy,
        r6_trades=args.r6_trades,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
    )
    payload = {
        "identity": IDENTITY,
        "generation": "V2",
        "hypothesis": (
            "TRAJECTORY_ACCELERATION_LOCAL_EXPANSION_WITH_FAILURE_VETO"
        ),
        "scientific_status": (
            "STI6_V2_SIGNAL_VALUE_DEMONSTRATED_R6"
            if r6["gate_pass"]
            else "STI6_V2_FALSIFIED_ON_CONSUMED_R6"
        ),
        "r6_pass": r6["gate_pass"],
        "calibration": calibration,
        "policy": {
            "policy_id": policy.policy_id,
            "sequence_window": policy.sequence_window,
            "continuation_velocity_threshold_bps": (
                policy.continuation_velocity_threshold_bps
            ),
            "tail_velocity_threshold_bps": (
                policy.tail_velocity_threshold_bps
            ),
            "local_expansion_threshold_bps": (
                policy.local_expansion_threshold_bps
            ),
            "persistence_threshold_bps": policy.persistence_threshold_bps,
            "max_failure_hazard_bps": policy.max_failure_hazard_bps,
            "minimum_integrity_bps": policy.minimum_integrity_bps,
        },
        "r6": r6,
        "frozen_gates": {
            "winner_precision_bps_min": base.STI6_WINNER_MIN_PRECISION_BPS,
            "winner_recall_bps_min": base.STI6_WINNER_MIN_RECALL_BPS,
            "positive_tail_precision_bps_min": (
                base.STI6_TAIL_MIN_PRECISION_BPS
            ),
            "positive_tail_recall_bps_min": (
                base.STI6_TAIL_MIN_RECALL_BPS
            ),
            "false_continuation_on_nonwinners_bps_max": (
                base.STI6_MAX_FALSE_CONTINUATION_ON_LOSERS_BPS
            ),
        },
        "governance": {
            "v1_threshold_rescue_used": False,
            "r8_source_only_calibration": True,
            "r6_threshold_fit": False,
            "r5_opened": False,
            "future_market_used_for_inference": False,
            "terminal_outcome_used_only_after_source_materialization": True,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "scientific_status": payload["scientific_status"],
                "r6": r6,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
