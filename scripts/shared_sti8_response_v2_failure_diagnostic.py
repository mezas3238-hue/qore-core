#!/usr/bin/env python3
"""Failure-knowledge diagnostic for falsified STI-8 economic response V2.

This script may inspect the burned V2 research OOS and terminal outcomes ONLY to
generate new mechanistic hypotheses. It cannot demonstrate V3 value and cannot
retune the frozen STI-8 signal engine or V2 response.
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
    assess_position_threat,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_research import (
    Vt31ThreatConsumerAction,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_v2_research import (
    decide_vt31_threat_response_v2,
    local_thesis_state,
)

IDENTITY = "QORE_SHARED_STI8_RESPONSE_V2_FAILURE_KNOWLEDGE_001"


def _run_length(actions: list[bool], start: int) -> int:
    count = 0
    for actionable in actions[start:]:
        if not actionable:
            break
        count += 1
    return count


def _median(values: list[int]) -> int | None:
    return None if not values else int(median(values))


def run(
    *,
    frozen_policy_path: Path,
    trades_path: Path,
    nas_path: Path,
    sp_path: Path,
    us_path: Path,
) -> dict[str, object]:
    frozen = json.loads(frozen_policy_path.read_text())
    if frozen.get("identity") != base.IDENTITY:
        raise ValueError("unexpected frozen STI-8 policy identity")
    if frozen.get("mode") != "SOURCE_ONLY_POLICY_FREEZE":
        raise ValueError("diagnostic requires source-only frozen STI-8 policy")

    policy = base._sti8_policy(frozen)
    sequences = base._source_sequences(
        partition="sti8_v2_failure_knowledge",
        trades_path=trades_path,
        nas_path=nas_path,
        sp_path=sp_path,
        us_path=us_path,
    )
    if not sequences:
        raise ValueError("V2 failure diagnostic has no valid source sequences")

    # Materialize all source-time decisions before terminal outcome grouping.
    materialized: list[dict[str, object]] = []
    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(tuple[Any, ...], sequence["observations"])
        decisions: list[dict[str, object]] = []
        action_flags: list[bool] = []

        for observation in observations:
            assessment = assess_position_threat(observation, policy=policy)
            response = decide_vt31_threat_response_v2(
                observation=observation,
                assessment=assessment,
                shared_intelligence_ref=(
                    "sti8:v2:burned-diagnostic:"
                    f"{observation.observation_id}"
                ),
            )
            resilience, failure = local_thesis_state(observation)
            actionable = (
                response.action is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
            )
            action_flags.append(actionable)
            decisions.append(
                {
                    "as_of": observation.as_of.isoformat(),
                    "actionable": actionable,
                    "level": assessment.threat_level.value,
                    "scope": assessment.threat_scope.value,
                    "threat_score_bps": assessment.threat_score_bps,
                    "continuation_support_bps": (
                        assessment.continuation_support_bps
                    ),
                    "failure_hazard_bps": assessment.failure_hazard_bps,
                    "local_resilience_bps": resilience,
                    "local_failure_bps": failure,
                    "local_failure_margin_bps": failure - resilience,
                    "hazard_margin_bps": (
                        assessment.failure_hazard_bps
                        - assessment.continuation_support_bps
                    ),
                }
            )

        first_index = next(
            (index for index, value in enumerate(action_flags) if value),
            None,
        )
        first_run = (
            0 if first_index is None else _run_length(action_flags, first_index)
        )
        materialized.append(
            {
                "row": row,
                "decisions": decisions,
                "first_actionable_index": first_index,
                "first_actionable_run_length": first_run,
                "actionable_observation_count": sum(action_flags),
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

    summary: dict[str, object] = {}
    for name, items in groups.items():
        with_exit = [
            item for item in items if item["first_actionable_index"] is not None
        ]
        run_lengths = [
            int(item["first_actionable_run_length"]) for item in with_exit
        ]
        actionable_counts = [
            int(item["actionable_observation_count"]) for item in with_exit
        ]
        local_margins: list[int] = []
        hazard_margins: list[int] = []
        scopes: Counter[str] = Counter()
        levels: Counter[str] = Counter()

        for item in with_exit:
            decisions = cast(list[dict[str, object]], item["decisions"])
            index = int(cast(int, item["first_actionable_index"]))
            first = decisions[index]
            local_margins.append(int(first["local_failure_margin_bps"]))
            hazard_margins.append(int(first["hazard_margin_bps"]))
            scopes[str(first["scope"])] += 1
            levels[str(first["level"])] += 1

        summary[name] = {
            "trade_count": len(items),
            "v2_exit_candidate_count": len(with_exit),
            "v2_exit_candidate_rate_bps": (
                0 if not items else len(with_exit) * 10_000 // len(items)
            ),
            "median_first_actionable_run_length": _median(run_lengths),
            "median_actionable_observation_count": _median(actionable_counts),
            "median_first_local_failure_margin_bps": _median(local_margins),
            "median_first_hazard_margin_bps": _median(hazard_margins),
            "first_scope_counts": dict(sorted(scopes.items())),
            "first_level_counts": dict(sorted(levels.items())),
        }

    confirmation_sensitivity: dict[str, object] = {}
    for confirmations in (1, 2, 3):
        per_group: dict[str, object] = {}
        for name, items in groups.items():
            candidates = sum(
                int(item["first_actionable_run_length"]) >= confirmations
                for item in items
            )
            per_group[name] = {
                "candidate_count": candidates,
                "candidate_rate_bps": (
                    0 if not items else candidates * 10_000 // len(items)
                ),
            }
        confirmation_sensitivity[str(confirmations)] = per_group

    losses = cast(dict[str, object], summary["BASELINE_LOSS"])
    winners = cast(dict[str, object], summary["BASELINE_WINNER"])
    candidates: list[str] = []
    loss_run = losses["median_first_actionable_run_length"]
    winner_run = winners["median_first_actionable_run_length"]
    if (
        isinstance(loss_run, int)
        and isinstance(winner_run, int)
        and loss_run > winner_run
    ):
        candidates.append("V3_SEQUENTIAL_THREAT_PERSISTENCE_CONFIRMATION")
    loss_local = losses["median_first_local_failure_margin_bps"]
    winner_local = winners["median_first_local_failure_margin_bps"]
    if (
        isinstance(loss_local, int)
        and isinstance(winner_local, int)
        and loss_local > winner_local
    ):
        candidates.append("V3_LOCAL_FAILURE_MARGIN_TRAJECTORY")
    loss_hazard = losses["median_first_hazard_margin_bps"]
    winner_hazard = winners["median_first_hazard_margin_bps"]
    if (
        isinstance(loss_hazard, int)
        and isinstance(winner_hazard, int)
        and loss_hazard > winner_hazard
    ):
        candidates.append("V3_HAZARD_OVER_CONTINUATION_PERSISTENCE")

    return {
        "identity": IDENTITY,
        "status": "STI8_V2_FAILURE_KNOWLEDGE_COMPLETE",
        "burned_v2_oos_used": True,
        "v2_reopened": False,
        "sti8_signal_engine_changed": False,
        "sti8_thresholds_changed": False,
        "v2_response_changed": False,
        "trade_count": len(materialized),
        "groups": summary,
        "fixed_confirmation_sensitivity": confirmation_sensitivity,
        "mechanistic_hypothesis_candidates": sorted(set(candidates)),
        "v3_policy_selected": False,
        "v3_value_demonstrated": False,
        "governance": {
            "outcomes_used_for_failure_knowledge_only": True,
            "burned_evidence_may_demonstrate_v3_value": False,
            "threshold_rescue_authorized": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    parser.add_argument("--nas", type=Path, required=True)
    parser.add_argument("--sp", type=Path, required=True)
    parser.add_argument("--us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        frozen_policy_path=args.policy,
        trades_path=args.trades,
        nas_path=args.nas,
        sp_path=args.sp,
        us_path=args.us,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "trade_count": payload["trade_count"],
                "candidates": payload["mechanistic_hypothesis_candidates"],
                "v3_policy_selected": payload["v3_policy_selected"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
