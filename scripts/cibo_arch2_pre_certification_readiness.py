#!/usr/bin/env python3
"""Build Architect-2 pre-certification readiness from canonical evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconciliation", type=Path, required=True)
    parser.add_argument("--scoreboard", type=Path, action="append", required=True)
    parser.add_argument("--redundancy-probe", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    reconciliation = _load(args.reconciliation)
    scoreboards = [_load(path) for path in args.scoreboard]
    redundancy = [_load(path) for path in args.redundancy_probe]

    if len(scoreboards) != 3 or len(redundancy) != 3:
        raise ValueError("pre-certification audit requires exactly three groups")

    groups = {
        str(board["group_id"]): board
        for board in scoreboards
    }
    redundancy_by_group = {
        str(row["group_id"]): row
        for row in redundancy
    }
    expected_groups = {"GROUP_1", "GROUP_2", "GROUP_3"}
    if set(groups) != expected_groups or set(redundancy_by_group) != expected_groups:
        raise ValueError("pre-certification group surface drift")

    functional_gate = all(
        board.get("functional_completeness") is True
        and board.get("mandatory_gap_count") == 0
        and board.get("row_count") == 60
        and board.get("exact_runtime_signature_collision_count") == 0
        for board in groups.values()
    )
    t13_t15_gate = all(
        probe.get("functional_seam_closed") is True
        and (probe.get("T13") or {}).get("classification")
        == "NO_MEASURABLE_EFFECT"
        and (probe.get("T15") or {}).get("classification")
        == "NO_MEASURABLE_EFFECT"
        for probe in redundancy_by_group.values()
    )
    phase22 = reconciliation.get("phase22_causal_availability") or {}
    phase22_causal_gate = (
        phase22.get("status") == "RESOLVED_INTERNAL_ENGINEERING"
        and phase22.get("train_prior_backdated_to_market_time") is False
    )
    internal_blockers = reconciliation.get("architect2_internal_blockers") or []
    interface_blockers = (
        reconciliation.get("architect1_economic_interface_blockers") or []
    )
    no_internal_blockers = not internal_blockers and not interface_blockers

    master = reconciliation.get("master_ledger") or {}
    external_count = int(master.get("external_dependency_blocked_count") or 0)
    nonterminal_ids = tuple(master.get("nonterminal_ids") or ())
    certification_dependencies_clear = (
        external_count == 0 and not nonterminal_ids
    )

    phase22_v4 = reconciliation.get("phase22_v4_preexecution") or {}
    fresh_oos_opened = (
        (reconciliation.get("governance") or {}).get("fresh_oos_opened") is True
    )
    preexecution_ready = phase22_v4.get("manifest_preexecution_ready") is True

    functional_pre_certification_ready = (
        functional_gate
        and t13_t15_gate
        and phase22_causal_gate
        and no_internal_blockers
        and preexecution_ready
        and not fresh_oos_opened
    )
    certification_execution_ready = (
        functional_pre_certification_ready
        and certification_dependencies_clear
    )

    payload = {
        "schema": "qore.cibo.arch2-pre-certification-readiness.v1",
        "functional_pre_certification_ready": functional_pre_certification_ready,
        "certification_execution_ready": certification_execution_ready,
        "disposition": (
            "FUNCTIONAL_GATE_CLEARED__CERTIFICATION_DEPENDENCIES_REMAIN"
            if functional_pre_certification_ready
            and not certification_execution_ready
            else (
                "READY_FOR_CERTIFICATION_EXECUTION"
                if certification_execution_ready
                else "PRE_CERTIFICATION_NOT_READY"
            )
        ),
        "gates": {
            "functional_completeness_all_groups": functional_gate,
            "t13_t15_functional_classification_closed": t13_t15_gate,
            "phase22_causal_availability_resolved": phase22_causal_gate,
            "architect2_internal_blockers_zero": not internal_blockers,
            "architect1_interface_blockers_zero": not interface_blockers,
            "phase22_v4_manifest_preexecution_ready": preexecution_ready,
            "fresh_oos_not_opened": not fresh_oos_opened,
            "certification_external_dependencies_clear": (
                certification_dependencies_clear
            ),
        },
        "groups": {
            group: {
                "row_count": board.get("row_count"),
                "mandatory_gap_count": board.get("mandatory_gap_count"),
                "functional_completeness": board.get("functional_completeness"),
                "T13": redundancy_by_group[group]["T13"]["classification"],
                "T15": redundancy_by_group[group]["T15"]["classification"],
            }
            for group, board in sorted(groups.items())
        },
        "remaining_certification_dependencies": {
            "external_dependency_blocked_count": external_count,
            "external_dependency_blocked_ids": master.get(
                "external_dependency_blocked_ids"
            ),
            "nonterminal_ids": list(nonterminal_ids),
        },
        "owner_rule": {
            "fresh_oos_opened": False,
            "fresh_oos_execution_authorized_by_this_audit": False,
            "certification_claimed": False,
            "merge_authorized": False,
            "live": False,
            "production": False,
            "real_capital": False,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "functional_pre_certification_ready": (
                    payload["functional_pre_certification_ready"]
                ),
                "certification_execution_ready": (
                    payload["certification_execution_ready"]
                ),
                "disposition": payload["disposition"],
                "external_dependency_blocked_count": external_count,
                "nonterminal_ids": list(nonterminal_ids),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
