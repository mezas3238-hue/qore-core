from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam_arch_b_ledger_transition import (
    ArchitectBPhase22DispositionReceipt,
    apply_architect_b_dispositions_to_ledger,
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


def _receipt(workstream_id: str, *, passed: bool = True):
    return ArchitectBPhase22DispositionReceipt(
        schema="qore.cibo.arch-b.phase22-disposition.v1",
        workstream_id=workstream_id,
        phase22_manifest_sha256=_sha("manifest"),
        source_gate_id=f"gate:{workstream_id}",
        source_gate_evidence_sha256=_sha(workstream_id),
        source_gate_status="PASS" if passed else "FAIL",
        passed=passed,
        recommended_disposition=(
            "COMPLETED_AND_PROVEN" if passed else "FALSIFIED_AND_CLOSED"
        ),
        blockers=() if passed else ("FALSIFIED",),
        failed_dimensions=() if passed else ("economic_value",),
    )


def _receipts():
    return tuple(
        _receipt(workstream_id, passed=workstream_id != "T03")
        for workstream_id in _B_IDS
    )


def test_transition_resolves_exact_ten_b_rows_only() -> None:
    ledger = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    post, transition = apply_architect_b_dispositions_to_ledger(
        ledger=ledger,
        receipts=_receipts(),
    )
    by_id = {row["id"]: row for row in post["workstreams"]}
    assert by_id["T03"]["terminal_disposition"] == "FALSIFIED_AND_CLOSED"
    assert all(
        by_id[workstream_id]["terminal_disposition"]
        in {"COMPLETED_AND_PROVEN", "FALSIFIED_AND_CLOSED"}
        for workstream_id in _B_IDS
    )
    assert by_id["GEN-C2"]["terminal_disposition"] == "EXTERNAL_DEPENDENCY_BLOCKED"
    assert by_id["FINAL_INTEGRATED_CIBO_EXAM"]["terminal_disposition"] is None
    assert by_id["WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"]["terminal_disposition"] is None
    assert len(transition.residual_external_ids) == 35
    assert not (set(transition.residual_external_ids) & set(_B_IDS))


def test_transition_rejects_missing_b_receipt() -> None:
    ledger = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact ten receipt identities",
    ):
        apply_architect_b_dispositions_to_ledger(
            ledger=ledger,
            receipts=_receipts()[:-1],
        )


def test_transition_rejects_fabricated_provider_evidence() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        ArchitectBPhase22DispositionReceipt(
            schema="qore.cibo.arch-b.phase22-disposition.v1",
            workstream_id="PROVIDER_ECONOMICS",
            phase22_manifest_sha256=_sha("manifest"),
            source_gate_id="gate:provider",
            source_gate_evidence_sha256=_sha("provider"),
            source_gate_status="PASS",
            passed=True,
            recommended_disposition="COMPLETED_AND_PROVEN",
            blockers=(),
            failed_dimensions=(),
            provider_evidence_fabricated=True,
        )
