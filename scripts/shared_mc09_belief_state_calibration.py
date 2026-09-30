#!/usr/bin/env python3
"""Consumed-partition calibration audit for MC-09 explicit belief state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import shared_mc09_belief_state_real_position_replay as replay
import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.causal_hypothesis_belief import (
    CausalHypothesisEvidence,
    accumulate_causal_hypotheses,
)

IDENTITY = "QORE_SHARED_MC09_BELIEF_STATE_CALIBRATION_001"
SNAPSHOT_FRAMES = 5
MINIMUM_POSITIONS = 150
MAXIMUM_ECE_BPS = 2_500
BIN_EDGES = (0, 2_000, 4_000, 6_000, 8_000, 10_000)


def _ratio_bps(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def _bin_index(probability_bps: int) -> int:
    if probability_bps == 10_000:
        return len(BIN_EDGES) - 2
    for index, (left, right) in enumerate(
        zip(BIN_EDGES, BIN_EDGES[1:], strict=True)
    ):
        if left <= probability_bps < right:
            return index
    raise ValueError("terminal probability outside frozen calibration bins")


def _partition(
    *,
    partition: str,
    trades: Path,
    nas: Path,
    sp: Path,
    us: Path,
) -> dict[str, object]:
    sequences = base._source_sequences(
        partition=f"mc09_calibration_{partition}",
        trades_path=trades,
        nas_path=nas,
        sp_path=sp,
        us_path=us,
    )
    if not sequences:
        raise ValueError(f"{partition}: no position sequences")

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
                raise AssertionError("MC-09 calibration received noncausal evidence")
            frames.append(replay._frame(observation))
        belief = accumulate_causal_hypotheses(tuple(frames))
        if belief.outcome_used or belief.pnl_used or belief.future_market_used:
            raise AssertionError("MC-09 belief consumed forbidden evidence")
        sealed.append((belief.terminal_bps, cast(dict[str, object], sequence["row"])))

    # Terminal outcomes are read only after every belief snapshot is sealed.
    scored: list[tuple[int, int]] = []
    for terminal_bps, row in sealed:
        adverse = int(float(row["net_r_after_friction"]) < 0.0)
        scored.append((terminal_bps, adverse))

    if not scored:
        raise ValueError(f"{partition}: no scoreable beliefs")

    n = len(scored)
    adverse_count = sum(label for _, label in scored)
    prevalence_bps = _ratio_bps(adverse_count, n)

    brier_sum = 0.0
    prevalence_probability = adverse_count / n
    baseline_brier = prevalence_probability * (1.0 - prevalence_probability)
    for probability_bps, label in scored:
        probability = probability_bps / 10_000.0
        brier_sum += (probability - label) ** 2
    brier = brier_sum / n
    brier_skill_bps = (
        0
        if baseline_brier <= 0
        else int(round((baseline_brier - brier) / baseline_brier * 10_000))
    )

    bins: list[dict[str, int]] = []
    ece_weighted = 0
    for index in range(len(BIN_EDGES) - 1):
        members = [
            (probability, label)
            for probability, label in scored
            if _bin_index(probability) == index
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
        mean_predicted = sum(p for p, _ in members) // len(members)
        observed = _ratio_bps(sum(y for _, y in members), len(members))
        error = abs(mean_predicted - observed)
        ece_weighted += error * len(members)
        bins.append(
            {
                "left_bps": BIN_EDGES[index],
                "right_bps": BIN_EDGES[index + 1],
                "count": len(members),
                "mean_predicted_bps": mean_predicted,
                "observed_adverse_rate_bps": observed,
                "absolute_error_bps": error,
            }
        )
    ece_bps = ece_weighted // n

    ordered = sorted(scored, key=lambda item: item[0])
    quartile_size = max(1, n // 4)
    bottom = ordered[:quartile_size]
    top = ordered[-quartile_size:]
    bottom_rate = _ratio_bps(sum(y for _, y in bottom), len(bottom))
    top_rate = _ratio_bps(sum(y for _, y in top), len(top))

    gates = {
        "minimum_positions": n >= MINIMUM_POSITIONS,
        "positive_brier_skill_vs_prevalence": brier_skill_bps > 0,
        "maximum_ece": ece_bps <= MAXIMUM_ECE_BPS,
        "top_quartile_adverse_rate_gt_bottom_quartile": top_rate > bottom_rate,
    }
    passed = all(gates.values())
    return {
        "partition": partition,
        "position_count": n,
        "adverse_count": adverse_count,
        "prevalence_bps": prevalence_bps,
        "brier_score": brier,
        "prevalence_brier_score": baseline_brier,
        "brier_skill_vs_prevalence_bps": brier_skill_bps,
        "ece_bps": ece_bps,
        "calibration_bins": bins,
        "bottom_quartile_adverse_rate_bps": bottom_rate,
        "top_quartile_adverse_rate_bps": top_rate,
        "gates": gates,
        "pass": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-trades", type=Path, required=True)
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = {
        partition: _partition(
            partition=partition,
            trades=getattr(args, f"{partition}_trades"),
            nas=getattr(args, f"{partition}_nas"),
            sp=getattr(args, f"{partition}_sp"),
            us=getattr(args, f"{partition}_us"),
        )
        for partition in ("r6", "r5")
    }
    passed = all(cast(dict[str, object], row)["pass"] for row in results.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC09_BELIEF_STATE_CALIBRATION_REPLICATED_PASS"
            if passed
            else "MC09_BELIEF_STATE_CALIBRATION_FALSIFIED"
        ),
        "results": results,
        "all_partitions_pass": passed,
        "belief_engine_changed": False,
        "belief_parameters_retuned": False,
        "source_decisions_materialized_before_outcome_scoring": True,
        "future_market_used_for_belief": False,
        "future_outcome_used_for_belief": False,
        "pnl_used_for_belief": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
        "mc09_completed_and_proven": passed,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
