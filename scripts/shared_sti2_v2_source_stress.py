#!/usr/bin/env python3
"""STI-2 V2 source-evidence stress on consumed R6/R5.

The frozen V2 policy is calibrated from R8 source-only evidence exactly as in
the authoritative V2 replay. Stress mutates only source-time evidence before
inference; target labels remain untouched and are read only for offline scoring.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import replace
from pathlib import Path

import shared_sti2_v2_trajectory_heads as v2
import shared_sti2_real_opportunity_discovery as v1

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityMechanism,
    assess_opportunity_trajectory,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
)

IDENTITY = "QORE_SHARED_STI2_V2_SOURCE_STRESS_001"
STRESSES = (
    "BASELINE",
    "RELATIONSHIP_STRESS",
    "STRUCTURAL_STRESS",
    "LIQUIDITY_STRESS",
    "COMBINED_WORLD_STRESS",
    "DATA_INTEGRITY_BELOW_GATE",
)


def _clip(value: int) -> int:
    return max(0, min(10_000, value))


def _stress(
    observation: SharedOpportunitySourceObservation,
    name: str,
) -> SharedOpportunitySourceObservation:
    if name == "BASELINE":
        return observation
    if name == "DATA_INTEGRITY_BELOW_GATE":
        return replace(observation, data_integrity_bps=9_000)

    changes: dict[str, int] = {}
    if name in {"RELATIONSHIP_STRESS", "COMBINED_WORLD_STRESS"}:
        changes.update(
            leader_confirmation_bps=_clip(
                observation.leader_confirmation_bps - 1_000
            ),
            leader_divergence_bps=_clip(
                observation.leader_divergence_bps + 1_000
            ),
        )
    if name in {"STRUCTURAL_STRESS", "COMBINED_WORLD_STRESS"}:
        changes.update(
            structural_fragility_bps=_clip(
                observation.structural_fragility_bps + 1_000
            ),
            anomaly_bps=_clip(observation.anomaly_bps + 500),
            momentum_decay_bps=_clip(
                observation.momentum_decay_bps + 500
            ),
        )
    if name in {"LIQUIDITY_STRESS", "COMBINED_WORLD_STRESS"}:
        changes.update(
            liquidity_accumulation_bps=_clip(
                observation.liquidity_accumulation_bps - 1_000
            ),
            liquidity_vacuum_bps=_clip(
                observation.liquidity_vacuum_bps + 1_000
            ),
            failed_auction_bps=_clip(
                observation.failed_auction_bps + 500
            ),
        )
    return replace(observation, **changes)


def _ratio(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def _evaluate(
    *,
    partition: str,
    stress_name: str,
    paths: dict[str, Path],
    policy: object,
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
    alerts = insufficient = 0

    for observation, _states, pre, future in rows:
        if future is None:
            raise AssertionError("stress evaluation requires target evidence")
        history.append(_stress(observation, stress_name))
        assessment = assess_opportunity_trajectory(
            tuple(history),
            policy=policy,
        )
        insufficient += int(
            assessment.maturity is SharedOpportunityMaturity.INSUFFICIENT
        )
        target_scores = v2._target_mechanism_scores(
            v1._target_state(pre, future)
        )
        future_material = max(target_scores.values()) >= v2.TARGET_BPS
        alert = assessment.maturity in {
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.MATURE,
        }
        alerts += int(alert)
        if alert and future_material:
            tp += 1
        elif alert:
            fp += 1
        elif future_material:
            fn += 1
        else:
            tn += 1

    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    false_alert = _ratio(fp, tp + fp)
    missed = _ratio(fn, tp + fn)
    v1_uplift = recall - v2.V1_RECALL[partition]
    if stress_name == "DATA_INTEGRITY_BELOW_GATE":
        gate = insufficient == len(rows) and alerts == 0
    else:
        gate = (
            precision >= v2.MIN_PRECISION_BPS
            and recall >= v2.MIN_RECALL_BPS
            and false_alert <= v2.MAX_FALSE_ALERT_BPS
            and missed <= v2.MAX_MISSED_BPS
            and v1_uplift >= v2.MIN_V1_RECALL_UPLIFT_BPS
        )
    return {
        "partition": partition,
        "stress": stress_name,
        "sample_count": len(rows),
        "alert_count": alerts,
        "insufficient_count": insufficient,
        "precision_bps": precision,
        "recall_bps": recall,
        "false_alert_rate_bps": false_alert,
        "missed_opportunity_rate_bps": missed,
        "recall_uplift_vs_v1_bps": v1_uplift,
        "gate_pass": gate,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy, calibration = v2._source_policy(
        {
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        }
    )
    evaluations: dict[str, dict[str, dict[str, object]]] = {}
    for partition in ("r6", "r5"):
        paths = {
            "NAS100": getattr(args, f"{partition}_nas"),
            "SP500": getattr(args, f"{partition}_sp"),
            "US30": getattr(args, f"{partition}_us"),
        }
        evaluations[partition] = {
            stress: _evaluate(
                partition=partition,
                stress_name=stress,
                paths=paths,
                policy=policy,
            )
            for stress in STRESSES
        }

    non_integrity = tuple(
        stress for stress in STRESSES if stress != "DATA_INTEGRITY_BELOW_GATE"
    )
    robust = all(
        evaluations[partition][stress]["gate_pass"]
        for partition in ("r6", "r5")
        for stress in non_integrity
    )
    fail_closed = all(
        evaluations[partition]["DATA_INTEGRITY_BELOW_GATE"]["gate_pass"]
        for partition in ("r6", "r5")
    )
    payload = {
        "identity": IDENTITY,
        "scientific_status": (
            "STI2_V2_SOURCE_STRESS_PASS"
            if robust and fail_closed
            else "STI2_V2_SOURCE_STRESS_FALSIFIED"
        ),
        "stress_pass": robust and fail_closed,
        "calibration": calibration,
        "evaluations": evaluations,
        "governance": {
            "v2_policy_retuned": False,
            "r8_source_only_calibration": True,
            "target_labels_stressed": False,
            "future_market_used_for_inference": False,
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
                "stress_pass": payload["stress_pass"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
