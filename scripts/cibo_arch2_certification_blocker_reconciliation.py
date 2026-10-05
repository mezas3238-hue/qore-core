#!/usr/bin/env python3
"""Reconcile Architect-2 functional blockers against certification dependencies."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--v4-manifest", type=Path, required=True)
    parser.add_argument("--scoreboard", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ledger = _load(args.ledger)
    manifest = _load(args.v4_manifest)
    scoreboards = [_load(path) for path in args.scoreboard]

    gaps: dict[str, set[str]] = {}
    for board in scoreboards:
        group = str(board["group_id"])
        gaps[group] = {
            str(row["Function"]) for row in board.get("mandatory_gaps", [])
        }

    all_gaps = set().union(*gaps.values()) if gaps else set()
    architect1_seams = sorted(all_gaps & {"T13", "T15"})
    architect2_internal = sorted(all_gaps - {"T13", "T15"})

    workstreams = ledger.get("workstreams")
    if not isinstance(workstreams, list):
        raise ValueError("ledger workstreams missing")
    dispositions = Counter(
        str(row.get("terminal_disposition")) for row in workstreams
    )
    external = [
        row
        for row in workstreams
        if row.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
    ]
    open_rows = [
        row for row in workstreams if row.get("terminal_disposition") is None
    ]

    required_manifest_flags = (
        "exact_seven_trader_bindings",
        "policy_frozen",
        "parity_manifest_bound",
        "provider_calibration_bound",
        "provider_numeric_freeze_bound",
        "source_receipt_bound",
        "vt31_six_field_abi_bound",
    )
    manifest_preexecution_ready = all(
        manifest.get(name) is True for name in required_manifest_flags
    )

    payload = {
        "schema": "qore.cibo.arch2-certification-blocker-reconciliation.v1",
        "source_ledger_schema": ledger.get("schema"),
        "functional_groups": {
            str(board["group_id"]): {
                "row_count": board.get("row_count"),
                "functional_completeness": board.get("functional_completeness"),
                "mandatory_gap_count": board.get("mandatory_gap_count"),
                "mandatory_gaps": sorted(gaps[str(board["group_id"])]),
                "exact_runtime_signature_collision_count": board.get(
                    "exact_runtime_signature_collision_count"
                ),
            }
            for board in scoreboards
        },
        "architect2_internal_blockers": architect2_internal,
        "architect1_economic_interface_blockers": architect1_seams,
        "phase22_causal_availability": {
            "status": "RESOLVED_INTERNAL_ENGINEERING",
            "disposition": "MARKET_TIME_POLICY_TIME_SEPARATED",
            "market_clock_claim": "HISTORICAL_SOURCE_STATE_ONLY",
            "policy_clock_claim": "POST_FREEZE_COUNTERFACTUAL_REPLAY",
            "train_prior_backdated_to_market_time": False,
            "evidence_refs": [
                "src/qore/infrastructure/cibo_phase22_v4_historical_policy_replay.py",
                "src/qore/infrastructure/cibo_phase22_v4_historical_replay_sealing.py",
                "tests/infrastructure/test_cibo_phase22_historical_policy_replay.py",
                "tests/infrastructure/test_cibo_phase22_historical_replay_sealing.py",
            ],
        },
        "phase22_v4_preexecution": {
            "manifest_preexecution_ready": manifest_preexecution_ready,
            "source_head_sha": manifest.get("source_head_sha"),
            "fresh_outcomes_executed": manifest.get("fresh_outcomes_executed"),
            "owner_authorization_present": manifest.get(
                "owner_authorization_present"
            ),
            "productive_authority": manifest.get("productive_authority"),
            "live_authorized": manifest.get("live_authorized"),
            "production_authorized": manifest.get("production_authorized"),
            "real_capital_authorized": manifest.get("real_capital_authorized"),
            "merge_authorized": manifest.get("merge_authorized"),
            "fresh_oos_disposition": (
                "DEFERRED_BY_OWNER_RULE__DO_NOT_OPEN_BEFORE_FUNCTIONAL_CLOSURE"
            ),
            "exact_head_ci_required_after_arch2_changes": True,
        },
        "master_ledger": {
            "workstream_count": len(workstreams),
            "terminal_disposition_counts": dict(sorted(dispositions.items())),
            "external_dependency_blocked_count": len(external),
            "external_dependency_blocked_ids": [
                str(row["id"]) for row in external
            ],
            "nonterminal_ids": [str(row["id"]) for row in open_rows],
        },
        "certification_open_after_internal_closure": [
            {
                "id": str(row["id"]),
                "status": "OPEN",
                "blockers": list(row.get("blockers") or []),
                "next_gate": row.get("next_gate"),
            }
            for row in open_rows
        ],
        "governance": {
            "fresh_oos_opened": False,
            "outcome_aware_tuning": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "merge_performed": False,
            "v3_second_fresh_execution": "FORBIDDEN__NOT_A_REPAIR_TARGET",
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
                "architect2_internal_blockers": architect2_internal,
                "architect1_economic_interface_blockers": architect1_seams,
                "external_dependency_blocked_count": len(external),
                "nonterminal_ids": [str(row["id"]) for row in open_rows],
                "manifest_preexecution_ready": manifest_preexecution_ready,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())