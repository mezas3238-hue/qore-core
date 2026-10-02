#!/usr/bin/env python3
"""MC-09 V2 explicit calibration layer with temporally later research OOS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import shared_mc09_belief_state_real_position_replay as replay
import shared_sti6_sti8_real_position_intelligence as base
from sklearn.linear_model import LogisticRegression

from qore.infrastructure.core_stack_v2.causal_hypothesis_belief import (
    CausalHypothesisEvidence,
    accumulate_causal_hypotheses,
)

IDENTITY = "QORE_SHARED_MC09_BELIEF_STATE_CALIBRATION_V2_001"
SNAPSHOT_FRAMES = 5
BIN_EDGES = (0, 2_000, 4_000, 6_000, 8_000, 10_000)
MAX_ECE_BPS = 2_500


def _examples(
    *,
    partition: str,
    trades: Path,
    nas: Path,
    sp: Path,
    us: Path,
) -> list[tuple[int, int]]:
    sequences = base._source_sequences(
        partition=partition,
        trades_path=trades,
        nas_path=nas,
        sp_path=sp,
        us_path=us,
    )
    sealed: list[tuple[int, dict[str, object]]] = []
    for sequence in sequences:
        observations = cast(tuple[Any, ...], sequence["observations"])
        if len(observations) < 2:
            continue
        frames: list[CausalHypothesisEvidence] = []
        for observation in observations[:SNAPSHOT_FRAMES]:
            if (
                observation.future_market_used
                or observation.future_outcome_used
                or observation.pnl_used
            ):
                raise AssertionError("MC-09 V2 received noncausal belief evidence")
            frames.append(replay._frame(observation))
        belief = accumulate_causal_hypotheses(tuple(frames))
        sealed.append((belief.terminal_bps, cast(dict[str, object], sequence["row"])))

    # Read terminal outcomes only after all causal beliefs have been sealed.
    return [
        (terminal_bps, int(float(row["net_r_after_friction"]) < 0.0))
        for terminal_bps, row in sealed
    ]


def _bin_index(probability_bps: int) -> int:
    if probability_bps == 10_000:
        return len(BIN_EDGES) - 2
    for index, (left, right) in enumerate(
        zip(BIN_EDGES, BIN_EDGES[1:], strict=True)
    ):
        if left <= probability_bps < right:
            return index
    raise ValueError("probability outside frozen bins")


def _metrics(probabilities_bps: list[int], labels: list[int]) -> dict[str, object]:
    if len(probabilities_bps) != len(labels) or not labels:
        raise ValueError("calibration metrics require aligned nonempty data")
    n = len(labels)
    brier = sum(
        ((probability / 10_000.0) - label) ** 2
        for probability, label in zip(probabilities_bps, labels, strict=True)
    ) / n
    bins = []
    ece_weighted = 0
    for index in range(len(BIN_EDGES) - 1):
        members = [
            (p, y)
            for p, y in zip(probabilities_bps, labels, strict=True)
            if _bin_index(p) == index
        ]
        if not members:
            bins.append(
                {
                    "left_bps": BIN_EDGES[index],
                    "right_bps": BIN_EDGES[index + 1],
                    "count": 0,
                    "mean_predicted_bps": 0,
                    "observed_adverse_rate_bps": 0,
                    "absolute_error_bps": 0,
                }
            )
            continue
        mean_prediction = sum(p for p, _ in members) // len(members)
        observed = sum(y for _, y in members) * 10_000 // len(members)
        error = abs(mean_prediction - observed)
        ece_weighted += error * len(members)
        bins.append(
            {
                "left_bps": BIN_EDGES[index],
                "right_bps": BIN_EDGES[index + 1],
                "count": len(members),
                "mean_predicted_bps": mean_prediction,
                "observed_adverse_rate_bps": observed,
                "absolute_error_bps": error,
            }
        )
    ordered = sorted(zip(probabilities_bps, labels, strict=True))
    q = max(1, n // 4)
    bottom = ordered[:q]
    top = ordered[-q:]
    return {
        "sample_count": n,
        "brier_score": brier,
        "ece_bps": ece_weighted // n,
        "bottom_quartile_adverse_rate_bps": (
            sum(y for _, y in bottom) * 10_000 // len(bottom)
        ),
        "top_quartile_adverse_rate_bps": (
            sum(y for _, y in top) * 10_000 // len(top)
        ),
        "bins": bins,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5", "oos"):
        parser.add_argument(f"--{partition}-trades", type=Path, required=True)
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    train = []
    for partition in ("r6", "r5"):
        train.extend(
            _examples(
                partition=f"mc09_v2_fit_{partition}",
                trades=getattr(args, f"{partition}_trades"),
                nas=getattr(args, f"{partition}_nas"),
                sp=getattr(args, f"{partition}_sp"),
                us=getattr(args, f"{partition}_us"),
            )
        )
    if not train:
        raise ValueError("MC-09 V2 calibration fit set is empty")

    x_train = np.asarray([[score / 10_000.0] for score, _ in train], dtype=float)
    y_train = np.asarray([label for _, label in train], dtype=int)
    model = LogisticRegression(C=1.0, solver="lbfgs", random_state=638)
    model.fit(x_train, y_train)

    oos = _examples(
        partition="mc09_v2_temporal_oos",
        trades=args.oos_trades,
        nas=args.oos_nas,
        sp=args.oos_sp,
        us=args.oos_us,
    )
    raw = [score for score, _ in oos]
    labels = [label for _, label in oos]
    x_oos = np.asarray([[score / 10_000.0] for score in raw], dtype=float)
    calibrated = [
        max(0, min(10_000, int(round(probability * 10_000))))
        for probability in model.predict_proba(x_oos)[:, 1]
    ]

    raw_metrics = _metrics(raw, labels)
    calibrated_metrics = _metrics(calibrated, labels)
    train_prevalence = sum(label for _, label in train) / len(train)
    prevalence_brier = sum(
        (train_prevalence - label) ** 2 for label in labels
    ) / len(labels)

    coefficient = float(model.coef_[0][0])
    gates = {
        "calibrated_brier_lt_raw": (
            float(calibrated_metrics["brier_score"])
            < float(raw_metrics["brier_score"])
        ),
        "calibrated_brier_lt_train_prevalence_baseline": (
            float(calibrated_metrics["brier_score"]) < prevalence_brier
        ),
        "calibrated_ece_lt_raw": (
            int(calibrated_metrics["ece_bps"]) < int(raw_metrics["ece_bps"])
        ),
        "calibrated_ece_lte_frozen_gate": (
            int(calibrated_metrics["ece_bps"]) <= MAX_ECE_BPS
        ),
        "positive_monotonic_coefficient": coefficient > 0.0,
        "top_quartile_adverse_rate_gt_bottom_quartile": (
            int(calibrated_metrics["top_quartile_adverse_rate_bps"])
            > int(calibrated_metrics["bottom_quartile_adverse_rate_bps"])
        ),
    }
    passed = all(gates.values())

    payload = {
        "identity": IDENTITY,
        "status": (
            "MC09_BELIEF_STATE_CALIBRATION_V2_TEMPORAL_OOS_PASS"
            if passed
            else "MC09_BELIEF_STATE_CALIBRATION_V2_TEMPORAL_OOS_FALSIFIED"
        ),
        "fit_count": len(train),
        "fit_prevalence": train_prevalence,
        "platt_intercept": float(model.intercept_[0]),
        "platt_coefficient": coefficient,
        "oos_raw": raw_metrics,
        "oos_calibrated": calibrated_metrics,
        "oos_train_prevalence_baseline_brier": prevalence_brier,
        "gates": gates,
        "all_gates_pass": passed,
        "belief_engine_changed": False,
        "belief_ranking_changed": False,
        "temporal_oos_used_for_fit": False,
        "source_decisions_materialized_before_outcome_scoring": True,
        "future_market_used_for_belief": False,
        "future_outcome_used_for_belief": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
        "mc09_completed_and_proven": passed,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
