#!/usr/bin/env python3
"""Materialize the canonical Shared maximum-ceiling open-work ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_zero_open_work import (
    assess_zero_open_work,
    build_shared_master_open_work_ledger,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ledger = build_shared_master_open_work_ledger()
    assessment = assess_zero_open_work(ledger)
    payload = {
        "identity": "QORE_SHARED_MASTER_OPEN_WORK_LEDGER_001",
        "status": "BLOCKED_UNTIL_ZERO_REQUIRED_OPEN_WORK",
        "items": [
            {
                "work_id": item.work_id,
                "family": item.family,
                "title": item.title,
                "mandatory": item.mandatory,
                "state": item.state.value,
                "evidence_refs": item.evidence_refs,
                "replacement_required_if_falsified": (
                    item.replacement_required_if_falsified
                ),
            }
            for item in ledger
        ],
        "assessment": {
            "ledger_identity": assessment.ledger_identity,
            "total_items": assessment.total_items,
            "mandatory_items": assessment.mandatory_items,
            "mandatory_closed": assessment.mandatory_closed,
            "optional_items": assessment.optional_items,
            "optional_closed": assessment.optional_closed,
            "blocker_count": len(assessment.blocker_ids),
            "blocker_ids": assessment.blocker_ids,
            "zero_open_required_work": assessment.zero_open_required_work,
            "pre_certification_ready": assessment.pre_certification_ready,
            "final_certification_exam_authorized": (
                assessment.final_certification_exam_authorized
            ),
            "protected_holdout_opening_authorized": (
                assessment.protected_holdout_opening_authorized
            ),
            "productive_authority": assessment.productive_authority,
        },
        "owner_laws": {
            "mandatory_falsified_v1_closes_capability": False,
            "architecture_or_contract_counts_as_completion": False,
            "ci_green_counts_as_certification": False,
            "external_dependency_blocked_counts_as_completion": False,
            "one_successful_sti_can_compensate_for_missing_sti": False,
            "unfinished_work_allows_pre_certification": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "total_items": assessment.total_items,
                "mandatory_closed": assessment.mandatory_closed,
                "blocker_count": len(assessment.blocker_ids),
                "zero_open_required_work": assessment.zero_open_required_work,
                "pre_certification_ready": assessment.pre_certification_ready,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
