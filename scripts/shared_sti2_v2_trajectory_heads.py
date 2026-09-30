#!/usr/bin/env python3
"""STI-2 V2 trajectory-head causal historical replay.

Policy thresholds are frozen from R8 source-only mechanism distributions.
R6 and R5 are consumed validation/replication folds. No future market state or
terminal outcome participates in inference or policy freeze.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

import shared_sti2_real_opportunity_discovery as v1

from qore.infrastructure.core_stack_v2.dynamic_causal_graph import CausalConcept
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityHeadThreshold,
    SharedOpportunityMechanism,
    SharedOpportunityTrajectoryPolicy,
    assess_opportunity_trajectory,
    opportunity_mechanism_scores,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
)

IDENTITY = "QORE_SHARED_STI2_V2_TRAJECTORY_HEADS_001"
TARGET_BPS = v1.FUTURE_MATERIAL_TARGET_BPS
MIN_PRECISION_BPS = 5_000
MIN_RECALL_BPS = 3_500
MAX_FALSE_ALERT_BPS = 5_000
MAX_MISSED_BPS = 6_500
MIN_V1_RECALL_UPLIFT_BPS = 1_500
V1_RECALL = {"r6": 1_259, "r5": 1_195}
SEQUENCE_WINDOW = 6
PERSISTENCE_BPS = 5_000


def _quantile(values: list[int], fraction: float) -> int:
    ordered = sorted(set(values))
    if not ordered:
        raise ValueError("empty source-only calibration distribution")
    index = int(round((len(ordered) - 1) * fraction))
    return ordered[max(0, min(len(ordered) - 1, index))]


def _strict_levels(values: list[int]) -> tuple[int, int, int]:
    distinct = sorted(set(values))
    if len(distinct) < 3:
        raise ValueError("mechanism head lacks source-only score diversity")
    selected = (
        _quantile(distinct, 0.55),
        _quantile(distinct, 0.70),
        _quantile(distinct, 0.85),
    )
    if selected[0] < selected[1] < selected[2]:
        return selected
    return distinct[-3], distinct[-2], distinct[-1]


def _source_policy(
    r8_paths: dict[str, Path],
) -> tuple[SharedOpportunityTrajectoryPolicy, dict[str, object]]:
    rows = v1._aligned_source_rows(
        r8_paths,
        partition="r8",
        require_future=False,
    )
    observations = [row[0] for row in rows]
    if len(observations) < SEQUENCE_WINDOW:
        raise ValueError("insufficient R8 observations for trajectory calibration")

    levels: dict[SharedOpportunityMechanism, list[int]] = {
        mechanism: [] for mechanism in SharedOpportunityMechanism
    }
    positive_velocity: dict[SharedOpportunityMechanism, list[int]] = {
        mechanism: [] for mechanism in SharedOpportunityMechanism
    }
    history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=SEQUENCE_WINDOW
    )
    for observation in observations:
        history.append(observation)
        scores = opportunity_mechanism_scores(observation)
        for mechanism, score in scores.items():
            levels[mechanism].append(score)
        if len(history) >= 2:
            score_rows = [
                opportunity_mechanism_scores(item) for item in history
            ]
            for mechanism in SharedOpportunityMechanism:
                current = score_rows[-1][mechanism]
                prior = [row[mechanism] for row in score_rows[:-1]]
                velocity = current - sum(prior) // len(prior)
                if velocity > 0:
                    positive_velocity[mechanism].append(velocity)

    heads: list[SharedOpportunityHeadThreshold] = []
    frozen: dict[str, object] = {}
    for mechanism in SharedOpportunityMechanism:
        early, developing, mature = _strict_levels(levels[mechanism])
        velocity = _quantile(
            positive_velocity[mechanism] or [1],
            0.65,
        )
        velocity = max(1, velocity)
        head = SharedOpportunityHeadThreshold(
            mechanism=mechanism,
            early_level_bps=early,
            developing_level_bps=developing,
            mature_level_bps=mature,
            positive_velocity_bps=velocity,
            persistence_bps=PERSISTENCE_BPS,
        )
        heads.append(head)
        frozen[mechanism.value] = {
            "early_level_bps": early,
            "developing_level_bps": developing,
            "mature_level_bps": mature,
            "positive_velocity_bps": velocity,
            "persistence_bps": PERSISTENCE_BPS,
        }

    policy = SharedOpportunityTrajectoryPolicy(
        policy_id="QORE_SHARED_STI2_V2_R8_SOURCE_ONLY_POLICY_001",
        sequence_window=SEQUENCE_WINDOW,
        heads=tuple(heads),
        minimum_integrity_bps=9_500,
        source_only_calibration=True,
        evidence_refs=(
            "immutable-r8-source-only-mechanism-distributions",
            "sti2-v2-preregistration-001",
        ),
    )
    return policy, {
        "r8_source_observation_count": len(observations),
        "head_thresholds": frozen,
        "future_market_used_for_freeze": False,
        "outcome_used_for_freeze": False,
    }


def _target_mechanism_scores(
    target: dict[CausalConcept, int],
) -> dict[SharedOpportunityMechanism, int]:
    return {
        SharedOpportunityMechanism.EXPANSION: max(
            target[CausalConcept.EXPANSION_READINESS],
            target[CausalConcept.DISPLACEMENT],
        ),
        SharedOpportunityMechanism.CONTINUATION: target[
            CausalConcept.CONTINUATION
        ],
        SharedOpportunityMechanism.REVERSAL: target[CausalConcept.REVERSAL],
        SharedOpportunityMechanism.RELATIONSHIP_TRANSITION: max(
            target[CausalConcept.REVERSAL],
            target[CausalConcept.EXPANSION_READINESS],
        ),
    }


def _ratio(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def _evaluate(
    *,
    partition: str,
    paths: dict[str, Path],
    policy: SharedOpportunityTrajectoryPolicy,
) -> dict[str, object]:
    rows = v1._aligned_source_rows(
        paths,
        partition=partition,
        require_future=True,
    )
    history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=policy.sequence_window
    )
    tp = fp = fn = tn = 0
    alert_count = 0
    mechanism_counts: dict[str, dict[str, int]] = {
        mechanism.value: {"signals": 0, "tp": 0, "fp": 0, "fn": 0}
        for mechanism in SharedOpportunityMechanism
    }

    for observation, _states, pre, future in rows:
        if future is None:
            raise AssertionError("V2 evaluation requires future labels")
        history.append(observation)
        assessment = assess_opportunity_trajectory(
            tuple(history),
            policy=policy,
        )
        target = v1._target_state(pre, future)
        target_scores = _target_mechanism_scores(target)
        future_material = max(target_scores.values()) >= TARGET_BPS
        alert = assessment.maturity in {
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.MATURE,
        }
        alert_count += int(alert)

        if alert and future_material:
            tp += 1
        elif alert:
            fp += 1
        elif future_material:
            fn += 1
        else:
            tn += 1

        dominant = assessment.dominant_mechanism
        for mechanism in SharedOpportunityMechanism:
            predicted = alert and dominant is mechanism
            actual = target_scores[mechanism] >= TARGET_BPS
            bucket = mechanism_counts[mechanism.value]
            bucket["signals"] += int(predicted)
            if predicted and actual:
                bucket["tp"] += 1
            elif predicted and not actual:
                bucket["fp"] += 1
            elif not predicted and actual:
                bucket["fn"] += 1

    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    false_alert = _ratio(fp, tp + fp)
    missed = _ratio(fn, tp + fn)
    v1_uplift = recall - V1_RECALL[partition]
    gate = (
        precision >= MIN_PRECISION_BPS
        and recall >= MIN_RECALL_BPS
        and false_alert <= MAX_FALSE_ALERT_BPS
        and missed <= MAX_MISSED_BPS
        and v1_uplift >= MIN_V1_RECALL_UPLIFT_BPS
    )

    mechanism_metrics = {}
    for mechanism, bucket in mechanism_counts.items():
        mechanism_metrics[mechanism] = {
            **bucket,
            "precision_bps": _ratio(
                bucket["tp"],
                bucket["tp"] + bucket["fp"],
            ),
            "recall_bps": _ratio(
                bucket["tp"],
                bucket["tp"] + bucket["fn"],
            ),
        }

    return {
        "partition": partition,
        "sample_count": len(rows),
        "alert_count": alert_count,
        "attention_density_bps": _ratio(alert_count, len(rows)),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision_bps": precision,
        "recall_bps": recall,
        "false_alert_rate_bps": false_alert,
        "missed_opportunity_rate_bps": missed,
        "v1_recall_bps": V1_RECALL[partition],
        "recall_uplift_vs_v1_bps": v1_uplift,
        "target_window_lead_minutes": 30,
        "event_level_lead_time_identifiable": False,
        "lead_time_metric_status": "WINDOW_LEVEL_LEAD_ONLY",
        "mechanism_metrics": mechanism_metrics,
        "gate_pass": gate,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--r5-nas", type=Path, required=True)
    parser.add_argument("--r5-sp", type=Path, required=True)
    parser.add_argument("--r5-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy, calibration = _source_policy(
        {
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        }
    )
    r6 = _evaluate(
        partition="r6",
        paths={
            "NAS100": args.r6_nas,
            "SP500": args.r6_sp,
            "US30": args.r6_us,
        },
        policy=policy,
    )
    r5 = _evaluate(
        partition="r5",
        paths={
            "NAS100": args.r5_nas,
            "SP500": args.r5_sp,
            "US30": args.r5_us,
        },
        policy=policy,
    )
    passed = bool(r6["gate_pass"] and r5["gate_pass"])
    payload = {
        "identity": IDENTITY,
        "generation": "V2",
        "hypothesis": "MECHANISM_SPECIFIC_TEMPORAL_TRAJECTORY_HEADS",
        "scientific_status": (
            "STI2_V2_VALUE_DEMONSTRATED_CONSUMED_R6_R5"
            if passed
            else "STI2_V2_FALSIFIED_ON_CONSUMED_R6_R5"
        ),
        "value_demonstrated": passed,
        "calibration": calibration,
        "policy": {
            "policy_id": policy.policy_id,
            "sequence_window": policy.sequence_window,
            "minimum_integrity_bps": policy.minimum_integrity_bps,
            "heads": [
                {
                    "mechanism": head.mechanism.value,
                    "early_level_bps": head.early_level_bps,
                    "developing_level_bps": head.developing_level_bps,
                    "mature_level_bps": head.mature_level_bps,
                    "positive_velocity_bps": head.positive_velocity_bps,
                    "persistence_bps": head.persistence_bps,
                }
                for head in policy.heads
            ],
        },
        "evaluations": {"r6": r6, "r5": r5},
        "frozen_gates": {
            "minimum_precision_bps": MIN_PRECISION_BPS,
            "minimum_recall_bps": MIN_RECALL_BPS,
            "maximum_false_alert_rate_bps": MAX_FALSE_ALERT_BPS,
            "maximum_missed_opportunity_rate_bps": MAX_MISSED_BPS,
            "minimum_v1_recall_uplift_bps": MIN_V1_RECALL_UPLIFT_BPS,
            "both_r6_and_r5_required": True,
        },
        "governance": {
            "v1_threshold_rescue_used": False,
            "r8_source_only_calibration": True,
            "r6_threshold_fit": False,
            "r5_threshold_fit": False,
            "future_market_used_for_inference": False,
            "future_market_used_offline_for_evaluation": True,
            "trader_methodology_used": False,
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
                "r5": r5,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
