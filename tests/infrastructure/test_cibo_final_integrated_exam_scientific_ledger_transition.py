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
from qore.infrastructure.cibo_final_integrated_exam_scientific_ledger_transition import (
    apply_architect_a_scientific_dispositions_to_ledger,
)

_LEDGER_PATH = (
    Path(__file__).parents[2]
    / "docs"
    / "research"
    / "CIBO-MASTER-OPEN-WORK-LEDGER-V1.json"
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _receipts(*, falsified_id: str | None = None):
    result = []
    for workstream_id in _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM:
        passed = workstream_id != falsified_id
        result.append(
            ArchitectAPhase22V2ScientificDispositionReceipt(
                schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
                workstream_id=workstream_id,
                phase22_manifest_sha256=_sha("manifest"),
                source_gate_id=f"gate:{workstream_id}",
                source_gate_evidence_sha256=_sha(workstream_id),
                source_gate_status="PASS" if passed else "FAIL",
                passed=passed,
                recommended_disposition=(
                    "COMPLETED_AND_PROVEN"
                    if passed else "FALSIFIED_AND_CLOSED"
                ),
                blockers=() if passed else ("FALSIFIED_DIMENSION",),
                failed_dimensions=() if passed else ("economic_value",),
                owner_review_approved=workstream_id == "GEN-C14",
            )
        )
    return tuple(result)


def _batch(receipts):
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
        receipt_count=len(receipts),
        resolved_count=len(receipts),
        completed_ids=completed,
        falsified_ids=falsified,
        external_ids=(),
        missing_ids=(),
        all_scientific_workstreams_resolved=True,
    )


def test_transition_resolves_exact_35_a_rows_and_preserves_two_exams() -> None:
    ledger = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    receipts = _receipts(falsified_id="GEN-C12")
    post, transition = apply_architect_a_scientific_dispositions_to_ledger(
        ledger=ledger,
        batch=_batch(receipts),
        receipts=receipts,
    )

    by_id = {row["id"]: row for row in post["workstreams"]}
    assert by_id["GEN-C12"]["terminal_disposition"] == "FALSIFIED_AND_CLOSED"
    assert all(
        by_id[workstream_id]["terminal_disposition"]
        in {"COMPLETED_AND_PROVEN", "FALSIFIED_AND_CLOSED"}
        for workstream_id in _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM
    )
    assert by_id["FINAL_INTEGRATED_CIBO_EXAM"]["terminal_disposition"] is None
    assert by_id["WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"]["terminal_disposition"] is None
    assert post["current_summary"] == {
        "mandatory_count": 64,
        "terminal_count": 62,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    assert len(transition.residual_external_ids) == 10
    assert not (
        set(transition.residual_external_ids)
        & set(_PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM)
    )


def test_transition_rejects_partial_a_closure() -> None:
    ledger = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    receipts = _receipts()
    batch = _batch(receipts)
    partial = ArchitectAPhase22V2ScientificClosureBatch(
        phase22_manifest_sha256=batch.phase22_manifest_sha256,
        receipt_count=34,
        resolved_count=34,
        completed_ids=batch.completed_ids[:-1],
        falsified_ids=(),
        external_ids=(),
        missing_ids=(batch.completed_ids[-1],),
        all_scientific_workstreams_resolved=False,
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="terminal 35-of-35 A closure",
    ):
        apply_architect_a_scientific_dispositions_to_ledger(
            ledger=ledger,
            batch=partial,
            receipts=receipts[:-1],
        )


def test_transition_rejects_promoting_non_external_source_row() -> None:
    ledger = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    target = next(
        row
        for row in ledger["workstreams"]
        if row["id"] == "GEN-C2"
    )
    target["terminal_disposition"] = "COMPLETED_AND_PROVEN"
    receipts = _receipts()
    with pytest.raises(
        CiboCapitalManagementError,
        match="source disposition drift: GEN-C2",
    ):
        apply_architect_a_scientific_dispositions_to_ledger(
            ledger=ledger,
            batch=_batch(receipts),
            receipts=receipts,
        )
