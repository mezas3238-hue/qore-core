#!/usr/bin/env python3
"""STI-5 V1 failure diagnostic on already-consumed R6/R5.

The diagnostic materializes all source-time regime features before future
30-minute transition labels are touched. It extracts mechanism-level failure
knowledge and proposes V2 hypotheses without changing V1 policy or thresholds.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import shared_sti5_real_regime_transition as v1

from qore.infrastructure.core_stack_v2.dynamic_causal_graph import CausalConcept
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTransitionObservation,
    assess_market_trajectory,
)

IDENTITY = "QORE_SHARED_STI5_V1_FAILURE_DIAGNOSTIC_001"


def _mean(values: list[int]) -> int:
    return 0 if not values else sum(values) // len(values)


def _source_features(
    history: tuple[MarketTransitionObservation, ...],
) -> dict[str, int]:
    latest = history[-1]
    trajectory = assess_market_trajectory(history)
    relationship_break = (
        (10_000 - latest.cross_market_confirmation_bps)
        + (10_000 - latest.correlation_stability_bps)
        + latest.contradiction_bps
    ) // 3
    liquidity_transition = (
        (10_000 - latest.liquidity_capacity_bps)
        + (10_000 - latest.volatility_stability_bps)
        + latest.anomaly_bps
    ) // 3
    macro_transition = (
        trajectory.deterioration_pressure_bps
        + latest.uncertainty_bps
        + latest.opposite_pressure_bps
    ) // 3
    return {
        "support_bps": trajectory.support_bps,
        "adversity_bps": trajectory.adversity_bps,
        "deterioration_pressure_bps": trajectory.deterioration_pressure_bps,
        "deterioration_velocity_bps": trajectory.deterioration_velocity_bps,
        "deterioration_persistence_bps": trajectory.deterioration_persistence_bps,
        "recovery_velocity_bps": trajectory.recovery_velocity_bps,
        "recovery_persistence_bps": trajectory.recovery_persistence_bps,
        "relationship_break_bps": relationship_break,
        "liquidity_transition_bps": liquidity_transition,
        "macro_transition_bps": macro_transition,
        "anomaly_bps": latest.anomaly_bps,
        "uncertainty_bps": latest.uncertainty_bps,
        "opposite_pressure_bps": latest.opposite_pressure_bps,
        "cross_market_confirmation_bps": latest.cross_market_confirmation_bps,
        "correlation_stability_bps": latest.correlation_stability_bps,
        "liquidity_capacity_bps": latest.liquidity_capacity_bps,
        "volatility_stability_bps": latest.volatility_stability_bps,
    }


def _profile(rows: list[dict[str, int]]) -> dict[str, int]:
    if not rows:
        return {}
    return {
        key: _mean([row[key] for row in rows])
        for key in rows[0]
    }


def _delta(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    return {
        key: left[key] - right[key]
        for key in sorted(set(left) & set(right))
    }


def _diagnose_partition(
    *,
    partition: str,
    paths: dict[str, Path],
) -> dict[str, object]:
    rows = v1._aligned_source_rows(
        paths,
        partition=partition,
        require_future=True,
    )
    history: deque[MarketTransitionObservation] = deque(
        maxlen=v1.SEQUENCE_WINDOW
    )
    materialized: list[
        tuple[dict[str, int], bool]
    ] = []

    for source, states, pre, future in rows:
        if future is None:
            raise AssertionError("STI-5 diagnostic requires future evidence")
        transition = v1._transition_observation(source, states)
        history.append(transition)
        features = _source_features(tuple(history))

        # Future label is attached only after source-time features exist.
        target_states = v1._target_state(pre, future)
        future_transition = max(
            target_states[CausalConcept.REVERSAL],
            target_states[CausalConcept.STRUCTURAL_FAILURE],
            target_states[CausalConcept.ANOMALY],
        ) >= v1.FUTURE_TRANSITION_TARGET_BPS
        materialized.append((features, future_transition))

    grouped: dict[str, list[dict[str, int]]] = defaultdict(list)
    for features, target in materialized:
        grouped["FUTURE_TRANSITION" if target else "NO_TRANSITION"].append(
            features
        )
    transition_profile = _profile(grouped["FUTURE_TRANSITION"])
    no_transition_profile = _profile(grouped["NO_TRANSITION"])
    transition_minus_control = _delta(
        transition_profile,
        no_transition_profile,
    )

    hypotheses: list[dict[str, object]] = []
    mechanism_deltas = {
        "RELATIONSHIP_BREAK": transition_minus_control.get(
            "relationship_break_bps", 0
        ),
        "LIQUIDITY_TRANSITION": transition_minus_control.get(
            "liquidity_transition_bps", 0
        ),
        "MACRO_TRANSITION": transition_minus_control.get(
            "macro_transition_bps", 0
        ),
        "ANOMALY": transition_minus_control.get("anomaly_bps", 0),
        "DETERIORATION_VELOCITY": transition_minus_control.get(
            "deterioration_velocity_bps", 0
        ),
        "DETERIORATION_PRESSURE": transition_minus_control.get(
            "deterioration_pressure_bps", 0
        ),
    }
    ranked = sorted(
        mechanism_deltas.items(),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )
    positive = [item for item in ranked if item[1] >= 300]
    if positive:
        hypotheses.append(
            {
                "hypothesis": "V2_MECHANISM_SPECIFIC_TRANSITION_HEADS",
                "evidence": dict(positive),
                "meaning": (
                    "V1 may lose early-warning information by collapsing distinct "
                    "relationship, liquidity, macro and anomaly mechanisms into one "
                    "trajectory state before arbitration."
                ),
            }
        )

    velocity_delta = transition_minus_control.get(
        "deterioration_velocity_bps",
        0,
    )
    persistence_delta = transition_minus_control.get(
        "deterioration_persistence_bps",
        0,
    )
    if max(velocity_delta, persistence_delta) >= 300:
        hypotheses.append(
            {
                "hypothesis": "V2_TRANSITION_PROCESS_NOT_STATIC_STATE",
                "evidence": {
                    "deterioration_velocity_delta_bps": velocity_delta,
                    "deterioration_persistence_delta_bps": persistence_delta,
                },
                "meaning": (
                    "Future transitions may be better identified from the process "
                    "of deterioration than from a thresholded regime label."
                ),
            }
        )

    if not hypotheses:
        hypotheses.append(
            {
                "hypothesis": "V2_CURRENT_SENSOR_REPRESENTATION_INSUFFICIENT",
                "evidence": transition_minus_control,
                "meaning": (
                    "Consumed source representation does not materially separate "
                    "future transitions; V2 should seek new causal sensors instead "
                    "of retuning V1 thresholds."
                ),
            }
        )

    return {
        "partition": partition,
        "sample_count": len(materialized),
        "group_counts": {
            key: len(value) for key, value in sorted(grouped.items())
        },
        "future_transition_profile_bps": transition_profile,
        "no_transition_profile_bps": no_transition_profile,
        "future_transition_minus_control_bps": transition_minus_control,
        "ranked_mechanism_deltas_bps": ranked,
        "hypothesis_candidates": hypotheses,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = {}
    for partition in ("r6", "r5"):
        results[partition] = _diagnose_partition(
            partition=partition,
            paths={
                "NAS100": getattr(args, f"{partition}_nas"),
                "SP500": getattr(args, f"{partition}_sp"),
                "US30": getattr(args, f"{partition}_us"),
            },
        )

    candidate_sets = [
        {
            item["hypothesis"]
            for item in results[partition]["hypothesis_candidates"]
        }
        for partition in ("r6", "r5")
    ]
    cross_partition = tuple(sorted(candidate_sets[0] & candidate_sets[1]))
    payload = {
        "identity": IDENTITY,
        "status": "STI5_V1_FAILURE_KNOWLEDGE_EXTRACTED_NO_RETUNING",
        "partitions": results,
        "cross_partition_hypothesis_candidates": cross_partition,
        "governance": {
            "v1_policy_changed": False,
            "v1_thresholds_changed": False,
            "v1_reopened": False,
            "v2_policy_selected": False,
            "r6_r5_already_consumed": True,
            "future_market_used_for_source_features": False,
            "future_label_attached_only_after_source_features": True,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "cross_partition_hypothesis_candidates": cross_partition,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
