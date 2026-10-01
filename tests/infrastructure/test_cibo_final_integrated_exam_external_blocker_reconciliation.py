from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

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
from qore.infrastructure.cibo_final_integrated_exam_arch_b_ledger_transition import (
    ArchitectBPhase22DispositionReceipt,
)
from qore.infrastructure.cibo_final_integrated_exam_external_blocker_reconciliation import (
    reconcile_all_external_blockers,
)

_LEDGER_PATH = (
    Path(__file__).parents[2]
    / "docs"
    / "research"
    / "CIBO-MASTER-OPEN-WORK-LEDGER-V1.json"
)
_B_IDS = (
    "T02",
    "T03",
    "T11",
    "T16",
    "T20",
    "PROVIDER_ECONOMICS",
    "FORWARD_QUALIFICATION",
    "FRESH_OOS",
    "USD60_CAPABILITY_PROGRAM",
    "INTEGRATED_CAPITAL_TRUTH",
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _a_receipts():
    result = []
    for workstream_id in _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM:
        passed = workstream_id != "GEN-C12"
        result.append(
            ArchitectAPhase22V2ScientificDispositionReceipt(
                schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
                workstream_id=workstream_id,
                phase22_manifest_sha256=_sha("manifest"),
                source_gate_id=f"a:{workstream_id}",
                source_gate_evidence_sha256=_sha("a:" + workstream_id),
                source_gate_status="PASS" if passed else "FAIL",
                passed=passed,
                recommended_disposition=(
                    "COMPLETED_AND_PROVEN"
                    if passed else "FALSIFIED_AND_CLOSED"
                ),
                blockers=() if passed else ("FALSIFIED",),
                failed_dimensions=() if passed else ("economic_value",),
                owner_review_approved=workstream_id == "GEN-C14",
            )
        )
    return tuple(result)


def _a_batch(receipts):
    completed = tuple(
        item.workstream_id
        for item in receipts
        if item.recommended_disposition == "COMPLETED_AND_PROVEN"
    )
    falsified = tuple(
        item.workstream_id
        for item in receipts
        if item.recommended_disposition == "FALSIFIED_AND_CLOSED"
    )
    return ArchitectAPhase22V2ScientificClosureBatch(
        phase22_manifest_sha256=_sha("manifest"),
        receipt_count=35,
        resolved_count=35,
        completed_ids=completed,
        falsified_ids=falsified,
        external_ids=(),
        missing_ids=(),
        all_scientific_workstreams_resolved=True,
    )


def _b_receipts():
    return tuple(
        ArchitectBPhase22DispositionReceipt(
            schema="qore.cibo.arch-b.phase22-disposition.v1",
            workstream_id=workstream_id,
            phase22_manifest_sha256=_sha("manifest"),
            source_gate_id=f"b:{workstream_id}",
            source_gate_evidence_sha256=_sha("b:" + workstream_id),
            source_gate_status=(
                "FAIL" if workstream_id == "T03" else "PASS"
            ),
            passed=workstream_id != "T03",
            recommended_disposition=(
                "FALSIFIED_AND_CLOSED"
                if workstream_id == "T03"
                else "COMPLETED_AND_PROVEN"
            ),
            blockers=("NO_EQUIVALENT_EXPRESSION",)
            if workstream_id == "T03"
            else (),
            failed_dimensions=("equivalent_expression",)
            if workstream_id == "T03"
            else (),
        )
        for workstream_id in _B_IDS
    )


def test_reconciliation_resolves_all_45_and_leaves_only_two_exams() -> None:
    ledger = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    a_receipts = _a_receipts()
    post, receipt = reconcile_all_external_blockers(
        ledger=ledger,
        architect_a_batch=_a_batch(a_receipts),
        architect_a_receipts=a_receipts,
        architect_b_receipts=_b_receipts(),
    )
    assert receipt.external_before_count == 45
    assert receipt.external_after_count == 0
    assert receipt.resolved_external_count == 45
    assert receipt.open_ids == (
        "FINAL_INTEGRATED_CIBO_EXAM",
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    )
    assert receipt.fingerprint().startswith("sha256:")
    assert post["current_summary"] == {
        "mandatory_count": 64,
        "terminal_count": 62,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }


def test_reconciliation_rejects_a_b_manifest_drift() -> None:
    ledger = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    a_receipts = _a_receipts()
    b_receipts = list(_b_receipts())
    first = b_receipts[0]
    b_receipts[0] = ArchitectBPhase22DispositionReceipt(
        schema=first.schema,
        workstream_id=first.workstream_id,
        phase22_manifest_sha256=_sha("other-manifest"),
        source_gate_id=first.source_gate_id,
        source_gate_evidence_sha256=first.source_gate_evidence_sha256,
        source_gate_status=first.source_gate_status,
        passed=first.passed,
        recommended_disposition=first.recommended_disposition,
        blockers=first.blockers,
        failed_dimensions=first.failed_dimensions,
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="Phase22 manifest drift",
    ):
        reconcile_all_external_blockers(
            ledger=ledger,
            architect_a_batch=_a_batch(a_receipts),
            architect_a_receipts=a_receipts,
            architect_b_receipts=tuple(b_receipts),
        )
