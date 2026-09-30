#!/usr/bin/env python3
"""Evaluate frozen STI-2 V1 vs V2 on the preregistered short research OOS."""

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

IDENTITY = "QORE_SHARED_STI2_V2_SHORT_RESEARCH_OOS_EVAL_001"
PARTITION = "sti2_v2_short_research_oos"
MIN_PRECISION_BPS = 5_000
MIN_RECALL_BPS = 3_500
MAX_FALSE_ALERT_BPS = 5_000
MAX_MISSED_BPS = 6_500
MIN_V2_RECALL_UPLIFT_BPS = 1_500


def _ratio(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def _metrics(
    *,
    tp: int,
    fp: int,
    fn: int,
    tn: int,
    alert_count: int,
    sample_count: int,
) -> dict[str, int]:
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "alert_count": alert_count,
        "sample_count": sample_count,
        "precision_bps": _ratio(tp, tp + fp),
        "recall_bps": _ratio(tp, tp + fn),
        "false_alert_rate_bps": _ratio(fp, tp + fp),
        "missed_opportunity_rate_bps": _ratio(fn, tp + fn),
        "attention_density_bps": _ratio(alert_count, sample_count),
    }


def run(
    *,
    r8_paths: dict[str, Path],
    oos_paths: dict[str, Path],
) -> dict[str, object]:
    v1_frozen = v1.freeze_policy(r8_paths=r8_paths)
    v1_policy = v1._policy_from_payload(v1_frozen)
    v2_policy, v2_calibration = v2._source_policy(r8_paths)

    rows = v1._aligned_source_rows(
        oos_paths,
        partition=PARTITION,
        require_future=True,
    )
    if not rows:
        raise ValueError("STI-2 V2 short OOS contains no aligned observations")

    v1_history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=v1_policy.sequence_window
    )
    v2_history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=v2_policy.sequence_window
    )

    v1_tp = v1_fp = v1_fn = v1_tn = v1_alerts = 0
    v2_tp = v2_fp = v2_fn = v2_tn = v2_alerts = 0
    source_materialized_count = 0

    materialized: list[
        tuple[
            bool,
            bool,
            dict[object, int],
        ]
    ] = []

    for observation, _states, pre, future in rows:
        if future is None:
            raise AssertionError("STI-2 short OOS requires future labels")

        v1_history.append(observation)
        v2_history.append(observation)

        v1_assessment = assess_global_opportunity(
            tuple(v1_history),
            policy=v1_policy,
        )
        v2_assessment = assess_opportunity_trajectory(
            tuple(v2_history),
            policy=v2_policy,
        )
        v1_alert = v1_assessment.maturity in {
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.MATURE,
        }
        v2_alert = v2_assessment.maturity in {
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.MATURE,
        }
        source_materialized_count += 1

        # Target state is attached only after both source-time arms are sealed.
        target_scores = v2._target_mechanism_scores(v1._target_state(pre, future))
        materialized.append((v1_alert, v2_alert, target_scores))

    for v1_alert, v2_alert, target_scores in materialized:
        future_material = max(target_scores.values()) >= v2.TARGET_BPS

        v1_alerts += int(v1_alert)
        if v1_alert and future_material:
            v1_tp += 1
        elif v1_alert:
            v1_fp += 1
        elif future_material:
            v1_fn += 1
        else:
            v1_tn += 1

        v2_alerts += int(v2_alert)
        if v2_alert and future_material:
            v2_tp += 1
        elif v2_alert:
            v2_fp += 1
        elif future_material:
            v2_fn += 1
        else:
            v2_tn += 1

    control = _metrics(
        tp=v1_tp,
        fp=v1_fp,
        fn=v1_fn,
        tn=v1_tn,
        alert_count=v1_alerts,
        sample_count=len(materialized),
    )
    treatment = _metrics(
        tp=v2_tp,
        fp=v2_fp,
        fn=v2_fn,
        tn=v2_tn,
        alert_count=v2_alerts,
        sample_count=len(materialized),
    )
    recall_uplift = treatment["recall_bps"] - control["recall_bps"]
    gates = {
        "minimum_precision": treatment["precision_bps"] >= MIN_PRECISION_BPS,
        "minimum_recall": treatment["recall_bps"] >= MIN_RECALL_BPS,
        "maximum_false_alert": (
            treatment["false_alert_rate_bps"] <= MAX_FALSE_ALERT_BPS
        ),
        "maximum_missed_opportunity": (
            treatment["missed_opportunity_rate_bps"] <= MAX_MISSED_BPS
        ),
        "minimum_recall_uplift_vs_v1_same_oos": (
            recall_uplift >= MIN_V2_RECALL_UPLIFT_BPS
        ),
    }
    passed = all(gates.values())

    return {
        "identity": IDENTITY,
        "partition": PARTITION,
        "status": (
            "STI2_V2_SHORT_RESEARCH_OOS_PASS"
            if passed
            else "STI2_V2_SHORT_RESEARCH_OOS_FALSIFIED"
        ),
        "research_oos_pass": passed,
        "sample_count": len(materialized),
        "source_materialized_count": source_materialized_count,
        "v1_control": control,
        "v2_treatment": treatment,
        "v2_recall_uplift_vs_v1_same_oos_bps": recall_uplift,
        "gates": gates,
        "frozen_gate_values": {
            "minimum_precision_bps": MIN_PRECISION_BPS,
            "minimum_recall_bps": MIN_RECALL_BPS,
            "maximum_false_alert_rate_bps": MAX_FALSE_ALERT_BPS,
            "maximum_missed_opportunity_rate_bps": MAX_MISSED_BPS,
            "minimum_v2_recall_uplift_vs_v1_same_oos_bps": (
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
            "oos_used_for_policy_fit": False,
            "oos_burned_after_open": True,
            "temporal_replication_claim_authorized": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "oos"):
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
        oos_paths={
            "NAS100": args.oos_nas,
            "SP500": args.oos_sp,
            "US30": args.oos_us,
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "research_oos_pass": payload["research_oos_pass"],
                "v1_control": payload["v1_control"],
                "v2_treatment": payload["v2_treatment"],
                "recall_uplift_bps": payload[
                    "v2_recall_uplift_vs_v1_same_oos_bps"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
