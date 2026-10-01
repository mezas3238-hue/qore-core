from __future__ import annotations

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam_arch_b_ledger_reconciliation import (
    ArchitectBPhase22FinalDisposition,
    ArchitectBPhase22FinalDispositionPackage,
    apply_architect_b_phase22_final_dispositions,
    required_arch_b_final_workstream_ids,
)

HEAD = "a" * 40
MANIFEST = "sha256:" + "b" * 64
EVIDENCE = "sha256:" + "c" * 64


def _row(row_id: str, *, external: bool = False) -> dict:
    return {
        "id": row_id,
        "kind": "SYSTEM",
        "mandatory": True,
        "certification_blocking": True,
        "current_maturity": "EXTERNAL" if external else "TERMINAL",
        "terminal_disposition": (
            "EXTERNAL_DEPENDENCY_BLOCKED"
            if external
            else "COMPLETED_AND_PROVEN"
        ),
        "evidence_refs": [],
        "blockers": ["WAIT"] if external else [],
        "next_gate": "wait" if external else "terminal",
    }


def _ledger() -> dict:
    rows = [
        _row(row_id, external=True)
        for row_id in required_arch_b_final_workstream_ids()
    ]
    rows.extend(_row(f"WORK_{index:02d}") for index in range(52))
    rows.extend(
        (
            {
                "id": "FINAL_INTEGRATED_CIBO_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "OPEN",
                "terminal_disposition": None,
                "evidence_refs": [],
                "blockers": ["EXAM_REQUIRED"],
                "next_gate": "run",
            },
            {
                "id": "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "OPEN",
                "terminal_disposition": None,
                "evidence_refs": [],
                "blockers": ["EXAM_REQUIRED"],
                "next_gate": "run",
            },
        )
    )
    return {
        "schema": "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1",
        "workstreams": rows,
        "current_summary": {
            "mandatory_count": 64,
            "terminal_count": 62,
            "open_count": 2,
            "zero_open_work_pass": False,
            "final_certification_candidate": False,
        },
    }


def _package() -> ArchitectBPhase22FinalDispositionPackage:
    dispositions = tuple(
        ArchitectBPhase22FinalDisposition(
            workstream_id=row_id,
            recommendation=(
                "SUPERSEDED_WITH_PROVEN_LINEAGE"
                if row_id == "FORWARD_QUALIFICATION"
                else "FALSIFIED_AND_CLOSED"
                if row_id == "T03"
                else "COMPLETED_AND_PROVEN"
            ),
            evidence_sha256=EVIDENCE,
            evidence_ref="artifact:" + row_id,
        )
        for row_id in required_arch_b_final_workstream_ids()
    )
    return ArchitectBPhase22FinalDispositionPackage(
        schema="QORE_CIBO_ARCH_B_PHASE22_FINAL_DISPOSITION_PACKAGE_V1",
        architect_b_head_sha=HEAD,
        phase22_manifest_sha256=MANIFEST,
        dispositions=dispositions,
        fresh_execution_complete=True,
        economic_qualification_executed=True,
    )


def test_applies_exact_ten_b_dispositions_without_certification_claim() -> None:
    result = apply_architect_b_phase22_final_dispositions(
        ledger=_ledger(),
        package=_package(),
    )
    rows = {item["id"]: item for item in result["workstreams"]}
    assert all(
        rows[row_id]["terminal_disposition"] != "EXTERNAL_DEPENDENCY_BLOCKED"
        for row_id in required_arch_b_final_workstream_ids()
    )
    assert rows["T03"]["terminal_disposition"] == "FALSIFIED_AND_CLOSED"
    assert (
        rows["FORWARD_QUALIFICATION"]["terminal_disposition"]
        == "SUPERSEDED_WITH_PROVEN_LINEAGE"
    )
    assert result["current_summary"]["terminal_count"] == 62
    assert result["current_summary"]["open_count"] == 2
    assert (
        result["phase22_b_reconciliation"][
            "remaining_certification_blocking_external_ids"
        ]
        == []
    )


def test_rejects_external_recommendation_in_final_package() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="must be terminal and non-external",
    ):
        ArchitectBPhase22FinalDisposition(
            workstream_id="T02",
            recommendation="EXTERNAL_DEPENDENCY_BLOCKED",
            evidence_sha256=EVIDENCE,
            evidence_ref="artifact:T02",
        )


def test_rejects_target_that_was_already_promoted() -> None:
    ledger = _ledger()
    target = next(item for item in ledger["workstreams"] if item["id"] == "T02")
    target["terminal_disposition"] = "COMPLETED_AND_PROVEN"
    target["blockers"] = []
    with pytest.raises(
        CiboCapitalManagementError,
        match="target is not external-blocked",
    ):
        apply_architect_b_phase22_final_dispositions(
            ledger=ledger,
            package=_package(),
        )
