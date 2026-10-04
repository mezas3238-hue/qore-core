#!/usr/bin/env python3
"""STI-8 V3 failure-knowledge diagnostic across burned research evidence.

V2 burned OOS and V3 fresh-but-now-burned OOS are used only to understand why
V3 interventions truncate winner-R. They can generate a V4 mechanism candidate,
never demonstrate V4 value.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, cast

import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    SharedPositionThreatEngineAssessment,
    assess_position_threat,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_research import (
    Vt31ThreatConsumerAction,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_v2_research import (
    local_thesis_state,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_v3_research import (
    _margins,
    decide_vt31_threat_response_v3,
)

IDENTITY = "QORE_SHARED_STI8_V3_FAILURE_KNOWLEDGE_001"


def _median(values: list[int]) -> int | None:
    return None if not values else int(median(values))


def _dataset(
    *,
    identity: str,
    policy_path: Path,
    trades_path: Path,
    nas_path: Path,
    sp_path: Path,
    us_path: Path,
) -> dict[str, object]:
    frozen = json.loads(policy_path.read_text())
    if frozen.get("identity") != base.IDENTITY:
        raise ValueError("unexpected frozen STI-8 signal policy identity")
    sti8_policy = base._sti8_policy(frozen)
    sequences = base._source_sequences(
        partition=identity,
        trades_path=trades_path,
        nas_path=nas_path,
        sp_path=sp_path,
        us_path=us_path,
    )
    if not sequences:
        raise ValueError(f"{identity}: no valid source sequences")

    materialized: list[dict[str, object]] = []
    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(tuple[Any, ...], sequence["observations"])
        first: dict[str, object] | None = None
        previous_observation: Any | None = None
        previous_assessment: SharedPositionThreatEngineAssessment | None = None

        for index, observation in enumerate(observations):
            assessment = assess_position_threat(observation, policy=sti8_policy)
            decision = decide_vt31_threat_response_v3(
                previous_observation=previous_observation,
                previous_assessment=previous_assessment,
                observation=observation,
                assessment=assessment,
                shared_intelligence_ref=(
                    f"sti8:v3:failure-knowledge:{identity}:"
                    f"{observation.observation_id}"
                ),
            )
            if (
                first is None
                and decision.action is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
            ):
                current_local, current_hazard = _margins(
                    observation,
                    assessment,
                )
                assert previous_observation is not None
                assert previous_assessment is not None
                previous_local, previous_hazard = _margins(
                    previous_observation,
                    previous_assessment,
                )
                resilience, failure = local_thesis_state(observation)
                first = {
                    "index": index,
                    "scope": assessment.threat_scope.value,
                    "level": assessment.threat_level.value,
                    "current_local_margin_bps": current_local,
                    "current_hazard_margin_bps": current_hazard,
                    "local_margin_delta_bps": current_local - previous_local,
                    "hazard_margin_delta_bps": current_hazard - previous_hazard,
                    "resilience_bps": resilience,
                    "local_failure_bps": failure,
                    "continuation_bps": assessment.continuation_support_bps,
                    "failure_hazard_bps": assessment.failure_hazard_bps,
                    "progress_bps": observation.progress_bps,
                    "signed_close_r_bps": observation.signed_close_r_bps,
                    "efficiency_bps": observation.efficiency_bps,
                }
            previous_observation = observation
            previous_assessment = assessment

        # Only after every source-time decision is sealed do we attach outcome.
        materialized.append(
            {
                "row": row,
                "observations": observations,
                "first": first,
            }
        )

    groups: dict[str, list[dict[str, object]]] = {
        "BASELINE_LOSS": [],
        "BASELINE_WINNER": [],
        "BASELINE_FLAT": [],
    }
    for item in materialized:
        row = cast(dict[str, object], item["row"])
        outcome = float(row["net_r_after_friction"])
        group = (
            "BASELINE_LOSS"
            if outcome < 0
            else "BASELINE_WINNER"
            if outcome > 0
            else "BASELINE_FLAT"
        )
        groups[group].append(item)

    result_groups: dict[str, object] = {}
    for group, items in groups.items():
        interventions = [
            item for item in items if item["first"] is not None
        ]
        next_persistent = 0
        next_recovered = 0
        local: list[int] = []
        hazard: list[int] = []
        local_delta: list[int] = []
        hazard_delta: list[int] = []
        progress: list[int] = []
        close_r: list[int] = []
        efficiency: list[int] = []
        scopes: Counter[str] = Counter()

        for item in interventions:
            observations = cast(tuple[Any, ...], item["observations"])
            first = cast(dict[str, object], item["first"])
            index = int(first["index"])
            local.append(int(first["current_local_margin_bps"]))
            hazard.append(int(first["current_hazard_margin_bps"]))
            local_delta.append(int(first["local_margin_delta_bps"]))
            hazard_delta.append(int(first["hazard_margin_delta_bps"]))
            progress.append(int(first["progress_bps"]))
            close_r.append(int(first["signed_close_r_bps"]))
            efficiency.append(int(first["efficiency_bps"]))
            scopes[str(first["scope"])] += 1

            if index + 1 < len(observations):
                current = observations[index]
                nxt = observations[index + 1]
                current_assessment = assess_position_threat(
                    current,
                    policy=sti8_policy,
                )
                next_assessment = assess_position_threat(
                    nxt,
                    policy=sti8_policy,
                )
                current_local, current_hazard = _margins(
                    current,
                    current_assessment,
                )
                next_local, next_hazard = _margins(
                    nxt,
                    next_assessment,
                )
                persistent = (
                    next_local > 0
                    and next_hazard > 0
                    and next_local >= current_local
                    and next_hazard >= current_hazard
                )
                recovered = next_local <= 0 or next_hazard <= 0
                next_persistent += int(persistent)
                next_recovered += int(recovered)

        count = len(items)
        interventions_count = len(interventions)
        result_groups[group] = {
            "trade_count": count,
            "intervention_count": interventions_count,
            "intervention_rate_bps": (
                0 if not count else interventions_count * 10_000 // count
            ),
            "next_observation_persistence_count": next_persistent,
            "next_observation_persistence_rate_bps": (
                0
                if not interventions_count
                else next_persistent * 10_000 // interventions_count
            ),
            "next_observation_recovery_count": next_recovered,
            "next_observation_recovery_rate_bps": (
                0
                if not interventions_count
                else next_recovered * 10_000 // interventions_count
            ),
            "median_current_local_margin_bps": _median(local),
            "median_current_hazard_margin_bps": _median(hazard),
            "median_local_margin_delta_bps": _median(local_delta),
            "median_hazard_margin_delta_bps": _median(hazard_delta),
            "median_progress_bps": _median(progress),
            "median_signed_close_r_bps": _median(close_r),
            "median_efficiency_bps": _median(efficiency),
            "scope_counts": dict(sorted(scopes.items())),
        }

    return {
        "identity": identity,
        "trade_count": len(materialized),
        "groups": result_groups,
        "source_decisions_sealed_before_outcome_grouping": True,
    }


def _candidate_consistent(
    datasets: dict[str, dict[str, object]],
    *,
    metric: str,
    winner_gt_loss: bool,
) -> bool:
    for dataset in datasets.values():
        groups = cast(dict[str, dict[str, object]], dataset["groups"])
        loss = groups["BASELINE_LOSS"].get(metric)
        winner = groups["BASELINE_WINNER"].get(metric)
        if not isinstance(loss, int) or not isinstance(winner, int):
            return False
        if winner_gt_loss and not winner > loss:
            return False
        if not winner_gt_loss and not loss > winner:
            return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    for prefix in ("v2", "v3"):
        parser.add_argument(f"--{prefix}-trades", type=Path, required=True)
        parser.add_argument(f"--{prefix}-nas", type=Path, required=True)
        parser.add_argument(f"--{prefix}-sp", type=Path, required=True)
        parser.add_argument(f"--{prefix}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    datasets = {
        "BURNED_V2_OOS": _dataset(
            identity="sti8_v3_failure_knowledge_v2",
            policy_path=args.policy,
            trades_path=args.v2_trades,
            nas_path=args.v2_nas,
            sp_path=args.v2_sp,
            us_path=args.v2_us,
        ),
        "BURNED_V3_OOS": _dataset(
            identity="sti8_v3_failure_knowledge_v3",
            policy_path=args.policy,
            trades_path=args.v3_trades,
            nas_path=args.v3_nas,
            sp_path=args.v3_sp,
            us_path=args.v3_us,
        ),
    }

    candidates: list[str] = []
    if _candidate_consistent(
        datasets,
        metric="next_observation_recovery_rate_bps",
        winner_gt_loss=True,
    ):
        candidates.append("V4_ONE_STEP_RECOVERY_VETO")
    if _candidate_consistent(
        datasets,
        metric="next_observation_persistence_rate_bps",
        winner_gt_loss=False,
    ):
        candidates.append("V4_ONE_STEP_PERSISTENCE_CONFIRMATION")
    if _candidate_consistent(
        datasets,
        metric="median_current_local_margin_bps",
        winner_gt_loss=False,
    ) and _candidate_consistent(
        datasets,
        metric="median_current_hazard_margin_bps",
        winner_gt_loss=False,
    ):
        candidates.append("V4_JOINT_MARGIN_SEVERITY_TRAJECTORY")

    payload = {
        "identity": IDENTITY,
        "status": "STI8_V3_FAILURE_KNOWLEDGE_COMPLETE",
        "datasets": datasets,
        "mechanistic_hypothesis_candidates": sorted(set(candidates)),
        "v3_reopened": False,
        "v3_policy_changed": False,
        "v4_policy_selected": False,
        "v4_value_demonstrated": False,
        "governance": {
            "outcomes_used_for_failure_knowledge_only": True,
            "burned_v2_or_v3_may_demonstrate_v4_value": False,
            "threshold_rescue_authorized": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "status": payload["status"],
        "candidates": payload["mechanistic_hypothesis_candidates"],
        "datasets": datasets,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
