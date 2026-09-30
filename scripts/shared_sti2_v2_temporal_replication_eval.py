#!/usr/bin/env python3
"""Evaluate frozen Shared STI-2 V1 vs V2 on temporal replication evidence."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

import shared_sti2_real_opportunity_discovery as v1
import shared_sti2_v2_trajectory_heads as v2

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
    assess_global_opportunity,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    assess_opportunity_trajectory,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
)

IDENTITY = "QORE_SHARED_STI2_V2_TEMPORAL_REPLICATION_EVAL_001"
PARTITION = "sti2_v2_temporal_replication_001"
MIN_SAMPLE_COUNT = 2_000
MIN_PRECISION_BPS = 5_000
MIN_RECALL_BPS = 3_500
MAX_FALSE_ALERT_BPS = 5_000
MAX_MISSED_BPS = 6_500
MIN_V2_RECALL_UPLIFT_BPS = 1_500


def _ratio(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def _metrics(*, tp: int, fp: int, fn: int, tn: int, alerts: int, samples: int) -> dict[str, int]:
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "alert_count": alerts,
        "sample_count": samples,
        "precision_bps": _ratio(tp, tp + fp),
        "recall_bps": _ratio(tp, tp + fn),
        "false_alert_rate_bps": _ratio(fp, tp + fp),
        "missed_opportunity_rate_bps": _ratio(fn, tp + fn),
        "attention_density_bps": _ratio(alerts, samples),
    }


def run(*, r8_paths: dict[str, Path], replication_paths: dict[str, Path]) -> dict[str, object]:
    v1_frozen = v1.freeze_policy(r8_paths=r8_paths)
    v1_policy = v1._policy_from_payload(v1_frozen)
    v2_policy, v2_calibration = v2._source_policy(r8_paths)

    rows = v1._aligned_source_rows(
        replication_paths,
        partition=PARTITION,
        require_future=True,
    )
    if not rows:
        raise ValueError("STI-2 temporal replication contains no aligned observations")

    v1_history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=v1_policy.sequence_window
    )
    v2_history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=v2_policy.sequence_window
    )
    materialized: list[tuple[bool, bool, dict[object, int]]] = []

    for observation, _states, pre, future in rows:
        if future is None:
            raise AssertionError("STI-2 temporal replication requires future labels")
        v1_history.append(observation)
        v2_history.append(observation)
        control_assessment = assess_global_opportunity(
            tuple(v1_history),
            policy=v1_policy,
        )
        treatment_assessment = assess_opportunity_trajectory(
            tuple(v2_history),
            policy=v2_policy,
        )
        control_alert = control_assessment.maturity in {
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.MATURE,
        }
        treatment_alert = treatment_assessment.maturity in {
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.MATURE,
        }

        # Future target is attached only after both source-time arms are materialized.
        target_scores = v2._target_mechanism_scores(v1._target_state(pre, future))
        materialized.append((control_alert, treatment_alert, target_scores))

    def summarize(index: int) -> dict[str, int]:
        tp = fp = fn = tn = alerts = 0
        for control_alert, treatment_alert, target_scores in materialized:
            alert = (control_alert, treatment_alert)[index]
            future_material = max(target_scores.values()) >= v2.TARGET_BPS
            alerts += int(alert)
            if alert and future_material:
                tp += 1
            elif alert:
                fp += 1
            elif future_material:
                fn += 1
            else:
                tn += 1
        return _metrics(
            tp=tp,
            fp=fp,
            fn=fn,
            tn=tn,
            alerts=alerts,
            samples=len(materialized),
        )

    control = summarize(0)
    treatment = summarize(1)
    uplift = treatment["recall_bps"] - control["recall_bps"]
    gates = {
        "minimum_sample_count": len(materialized) >= MIN_SAMPLE_COUNT,
        "minimum_precision": treatment["precision_bps"] >= MIN_PRECISION_BPS,
        "minimum_recall": treatment["recall_bps"] >= MIN_RECALL_BPS,
        "maximum_false_alert": treatment["false_alert_rate_bps"] <= MAX_FALSE_ALERT_BPS,
        "maximum_missed_opportunity": (
            treatment["missed_opportunity_rate_bps"] <= MAX_MISSED_BPS
        ),
        "minimum_recall_uplift_vs_v1_same_replication": (
            uplift >= MIN_V2_RECALL_UPLIFT_BPS
        ),
    }
    passed = all(gates.values())

    return {
        "identity": IDENTITY,
        "partition": PARTITION,
        "status": (
            "STI2_V2_TEMPORAL_REPLICATION_PASS"
            if passed
            else "STI2_V2_TEMPORAL_REPLICATION_FALSIFIED"
        ),
        "temporal_replication_pass": passed,
        "sample_count": len(materialized),
        "v1_control": control,
        "v2_treatment": treatment,
        "v2_recall_uplift_vs_v1_same_replication_bps": uplift,
        "gates": gates,
        "frozen_gate_values": {
            "minimum_sample_count": MIN_SAMPLE_COUNT,
            "minimum_precision_bps": MIN_PRECISION_BPS,
            "minimum_recall_bps": MIN_RECALL_BPS,
            "maximum_false_alert_rate_bps": MAX_FALSE_ALERT_BPS,
            "maximum_missed_opportunity_rate_bps": MAX_MISSED_BPS,
            "minimum_v2_recall_uplift_vs_v1_same_replication_bps": (
                MIN_V2_RECALL_UPLIFT_BPS
            ),
        },
        "policy_provenance": {
            "v1_policy_id": v1_policy.policy_id,
            "v2_policy_id": v2_policy.policy_id,
            "v1_r8_source_only": True,
            "v2_r8_source_only": True,
            "v2_calibration": v2_calibration,
        },
        "governance": {
            "same_observation_universe": True,
            "same_target_definition": True,
            "both_source_arms_materialized_before_target_scoring": True,
            "future_market_used_for_inference": False,
            "replication_used_for_policy_fit": False,
            "replication_burned_after_open": True,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "replication"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_paths={
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        },
        replication_paths={
            "NAS100": args.replication_nas,
            "SP500": args.replication_sp,
            "US30": args.replication_us,
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "temporal_replication_pass": payload["temporal_replication_pass"],
                "v1_control": payload["v1_control"],
                "v2_treatment": payload["v2_treatment"],
                "recall_uplift_bps": payload[
                    "v2_recall_uplift_vs_v1_same_replication_bps"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
