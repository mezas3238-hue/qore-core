from __future__ import annotations

import pytest

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM,
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificClosureBatch,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam_scientific_ledger_reconciliation import (
    apply_architect_a_phase22_scientific_dispositions,
)

MANIFEST = "sha256:" + "a" * 64
EVIDENCE = "sha256:" + "b" * 64


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
        _row("T04", external=True),
        _row("T06", external=True),
        _row("GEN-C14", external=True),
    ]
    rows.extend(
        _row(f"WORK_{index:02d}") for index in range(59)
    )
    rows.extend(
        [
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
        ]
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


def _receipt(
    workstream_id: str,
    disposition: str,
    *,
    passed: bool,
    blockers: tuple[str, ...] = (),
) -> ArchitectAPhase22V2ScientificDispositionReceipt:
    return ArchitectAPhase22V2ScientificDispositionReceipt(
        schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
        workstream_id=workstream_id,
        phase22_manifest_sha256=MANIFEST,
        source_gate_id="gate:" + workstream_id,
        source_gate_evidence_sha256=EVIDENCE,
        source_gate_status="PASS" if passed else "FAIL",
        passed=passed,
        recommended_disposition=disposition,
        blockers=blockers,
        failed_dimensions=() if passed else ("UTILITY",),
        owner_review_approved=False,
    )


def test_applies_proven_falsified_and_retained_external() -> None:
    receipts = (
        _receipt("T04", "COMPLETED_AND_PROVEN", passed=True),
        _receipt("T06", "FALSIFIED_AND_CLOSED", passed=False),
        ArchitectAPhase22V2ScientificDispositionReceipt(
            schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
            workstream_id="GEN-C14",
            phase22_manifest_sha256=MANIFEST,
            source_gate_id="gate:GEN-C14",
            source_gate_evidence_sha256=EVIDENCE,
            source_gate_status="PASS",
            passed=True,
            recommended_disposition="EXTERNAL_DEPENDENCY_BLOCKED",
            blockers=("OWNER_REVIEW_REQUIRED",),
            failed_dimensions=(),
            owner_review_approved=False,
        ),
    )
    covered = {"T04", "T06", "GEN-C14"}
    missing = tuple(
        workstream_id
        for workstream_id in _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM
        if workstream_id not in covered
    )
    batch = ArchitectAPhase22V2ScientificClosureBatch(
        phase22_manifest_sha256=MANIFEST,
        receipt_count=3,
        resolved_count=2,
        completed_ids=("T04",),
        falsified_ids=("T06",),
        external_ids=("GEN-C14",),
        missing_ids=missing,
        all_scientific_workstreams_resolved=False,
    )

    result = apply_architect_a_phase22_scientific_dispositions(
        ledger=_ledger(),
        batch=batch,
        receipts=receipts,
    )
    rows = {item["id"]: item for item in result["workstreams"]}
    assert rows["T04"]["terminal_disposition"] == "COMPLETED_AND_PROVEN"
    assert rows["T04"]["blockers"] == []
    assert rows["T06"]["terminal_disposition"] == "FALSIFIED_AND_CLOSED"
    assert rows["T06"]["blockers"] == []
    assert rows["GEN-C14"]["terminal_disposition"] == "EXTERNAL_DEPENDENCY_BLOCKED"
    assert rows["GEN-C14"]["blockers"] == ["OWNER_REVIEW_REQUIRED"]
    assert result["current_summary"] == {
        "mandatory_count": 64,
        "terminal_count": 62,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }


def test_rejects_target_that_is_not_external_blocked() -> None:
    receipt = _receipt("T04", "COMPLETED_AND_PROVEN", passed=True)
    missing = tuple(
        workstream_id
        for workstream_id in _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM
        if workstream_id != "T04"
    )
    batch = ArchitectAPhase22V2ScientificClosureBatch(
        phase22_manifest_sha256=MANIFEST,
        receipt_count=1,
        resolved_count=1,
        completed_ids=("T04",),
        falsified_ids=(),
        external_ids=(),
        missing_ids=missing,
        all_scientific_workstreams_resolved=False,
    )
    ledger = _ledger()
    row = next(item for item in ledger["workstreams"] if item["id"] == "T04")
    row["terminal_disposition"] = "COMPLETED_AND_PROVEN"
    row["blockers"] = []

    with pytest.raises(
        CiboCapitalManagementError,
        match="target is not external-blocked",
    ):
        apply_architect_a_phase22_scientific_dispositions(
            ledger=ledger,
            batch=batch,
            receipts=(receipt,),
        )
