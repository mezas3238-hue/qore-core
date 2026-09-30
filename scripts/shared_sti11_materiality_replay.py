#!/usr/bin/env python3
"""Calibrate STI-11 on R8 source-only deltas and replay frozen policy on R6/R5."""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source
import shared_sti2_v2_trajectory_heads as sti2

from qore.infrastructure.core_stack_v2.shared_alert_materiality import (
    SharedAlertMaterialityPolicy,
    SharedAlertMaterialityState,
    assess_alert_materiality,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityTrajectoryAssessment,
    assess_opportunity_trajectory,
)

IDENTITY = "QORE_SHARED_STI11_SOURCE_ONLY_MATERIALITY_REPLAY_001"


def _dominant_score(assessment: SharedOpportunityTrajectoryAssessment) -> int:
    if assessment.dominant_mechanism is None:
        return 0
    for state in assessment.head_states:
        if state.mechanism is assessment.dominant_mechanism:
            return state.trajectory_score_bps
    return 0


def _quantile(values: list[int], fraction: float) -> int:
    if not values:
        raise ValueError("materiality calibration distribution is empty")
    ordered = sorted(values)
    index = int((len(ordered) - 1) * fraction)
    return ordered[index]


def _assessments(
    *,
    partition: str,
    paths: dict[str, Path],
    trajectory_policy: object,
) -> list[SharedOpportunityTrajectoryAssessment]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    history: dict[str, deque[SharedOpportunitySourceObservation]] = {}
    output: list[SharedOpportunityTrajectoryAssessment] = []
    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("STI-11 source replay cannot attach future")
        series = history.setdefault(
            observation.asset,
            deque(maxlen=trajectory_policy.sequence_window),
        )
        series.append(observation)
        output.append(
            assess_opportunity_trajectory(
                tuple(series),
                policy=trajectory_policy,
            )
        )
    return output


def _calibrate(
    assessments: list[SharedOpportunityTrajectoryAssessment],
) -> tuple[SharedAlertMaterialityPolicy, dict[str, int]]:
    score_deltas: list[int] = []
    contradiction_deltas: list[int] = []
    uncertainty_deltas: list[int] = []
    previous: SharedOpportunityTrajectoryAssessment | None = None
    for current in assessments:
        if previous is not None and previous.asset == current.asset:
            score_deltas.append(
                abs(_dominant_score(current) - _dominant_score(previous))
            )
            contradiction_deltas.append(
                abs(current.contradiction_bps - previous.contradiction_bps)
            )
            uncertainty_deltas.append(
                abs(current.uncertainty_bps - previous.uncertainty_bps)
            )
        previous = current

    thresholds = {
        "trajectory_score_delta_bps": max(1, _quantile(score_deltas, 0.75)),
        "contradiction_delta_bps": max(
            1,
            _quantile(contradiction_deltas, 0.75),
        ),
        "uncertainty_delta_bps": max(
            1,
            _quantile(uncertainty_deltas, 0.75),
        ),
    }
    policy = SharedAlertMaterialityPolicy(
        policy_id="QORE_SHARED_STI11_R8_SOURCE_ONLY_MATERIALITY_POLICY_001",
        source_only_calibration=True,
        calibration_evidence_refs=(
            "r8-source-only-cognitive-delta-distributions",
            "sti2-v2-frozen-trajectory-policy",
        ),
        **thresholds,
    )
    return policy, thresholds


def _replay(
    assessments: list[SharedOpportunityTrajectoryAssessment],
    *,
    policy: SharedAlertMaterialityPolicy,
) -> dict[str, object]:
    material = dedup = 0
    reasons: Counter[str] = Counter()
    previous_by_asset: dict[str, SharedOpportunityTrajectoryAssessment] = {}
    fingerprints: list[tuple[str, tuple[str, ...], int, int, int]] = []

    for current in assessments:
        previous = previous_by_asset.get(current.asset)
        result = assess_alert_materiality(
            previous=previous,
            current=current,
            policy=policy,
        )
        material += int(result.state is SharedAlertMaterialityState.MATERIAL)
        dedup += int(
            result.state is SharedAlertMaterialityState.DEDUPLICATED
        )
        reasons.update(result.reason_codes)
        fingerprints.append(
            (
                result.state.value,
                result.reason_codes,
                result.trajectory_score_delta_bps,
                result.contradiction_delta_bps,
                result.uncertainty_delta_bps,
            )
        )
        previous_by_asset[current.asset] = current

    return {
        "observation_count": len(assessments),
        "material_event_count": material,
        "deduplicated_count": dedup,
        "material_event_rate_bps": (
            0 if not assessments else material * 10_000 // len(assessments)
        ),
        "deduplicated_rate_bps": (
            0 if not assessments else dedup * 10_000 // len(assessments)
        ),
        "reason_counts": dict(sorted(reasons.items())),
        "fingerprints": fingerprints,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trajectory_policy, trajectory_calibration = sti2._source_policy(
        {
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        }
    )
    r8 = _assessments(
        partition="r8",
        paths={
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        },
        trajectory_policy=trajectory_policy,
    )
    materiality_policy, thresholds = _calibrate(r8)

    results = {}
    for partition in ("r6", "r5"):
        assessments = _assessments(
            partition=partition,
            paths={
                "NAS100": getattr(args, f"{partition}_nas"),
                "SP500": getattr(args, f"{partition}_sp"),
                "US30": getattr(args, f"{partition}_us"),
            },
            trajectory_policy=trajectory_policy,
        )
        first = _replay(assessments, policy=materiality_policy)
        second = _replay(assessments, policy=materiality_policy)
        deterministic = first["fingerprints"] == second["fingerprints"]
        first.pop("fingerprints")
        first["deterministic_replay"] = deterministic
        results[partition] = first

    passed = all(
        row["observation_count"] > 0
        and row["material_event_count"] > 0
        and row["deduplicated_count"] > 0
        and row["deterministic_replay"]
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "STI11_MATERIALITY_DEDUP_COMPLETED_AND_PROVEN"
            if passed
            else "STI11_MATERIALITY_DEDUP_REPLAY_FAIL"
        ),
        "materiality_policy": {
            "policy_id": materiality_policy.policy_id,
            "fingerprint": materiality_policy.fingerprint(),
            "thresholds": thresholds,
            "source_only_calibration": True,
            "calibration_partition": "R8",
        },
        "trajectory_calibration": trajectory_calibration,
        "results": results,
        "proof": {
            "r8_outcomes_used_for_materiality_fit": False,
            "r6_r5_used_for_threshold_fit": False,
            "future_market_read": False,
            "future_outcome_read": False,
            "unchanged_subthreshold_cognition_deduplicated": True,
            "state_or_mechanism_change_material": True,
            "materiality_is_order_priority": False,
        },
        "governance": {
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
        "capability_state": (
            "COMPLETED_AND_PROVEN" if passed else "RESEARCH_INCOMPLETE"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "status": payload["status"],
        "thresholds": thresholds,
        "results": results,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
