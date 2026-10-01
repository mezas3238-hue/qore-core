from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_exam_control_receipt import (
    bind_final_exam_control_artifact,
    require_final_exam_control_receipts,
)

T0 = datetime(2026, 10, 1, 18, 0, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64
PHASE22 = "sha256:" + "c" * 64
KIND = "FINAL_INTEGRATED_EXAM_CONTROL"


def _artifact(
    *,
    receipt_id: str = "P1",
    status: str = "PASS",
    head: str = HEAD,
    phase22: str = PHASE22,
    contaminated: bool = False,
) -> str:
    payload = {
        "schema": "qore.cibo.final-exam-control.test.v2",
        "evidence_binding_id": receipt_id,
        "evidence_kind": KIND,
        "producer_gate_id": f"gate:{receipt_id}",
        "integrated_git_sha": head,
        "policy_identity_sha256": POLICY,
        "phase22_qualification_artifact_sha256": phase22,
        "certification_stage": "POST_PHASE22",
        "observed_at": T0.isoformat(),
        "status": status,
        "failures": [] if status == "PASS" else ["FAILED"],
        "productive_authority": False,
        "synthetic_evidence_used": contaminated,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _receipt(receipt_id: str = "P1"):
    return bind_final_exam_control_artifact(
        receipt_id=receipt_id,
        evidence_kind=KIND,
        source_artifact_json=_artifact(receipt_id=receipt_id),
    )


def test_final_control_binds_exact_post_phase22_chain() -> None:
    receipt = _receipt()
    assert receipt.phase22_qualification_artifact_sha256 == PHASE22
    assert receipt.source_artifact_sha256 == (
        "sha256:" + hashlib.sha256(_artifact().encode("utf-8")).hexdigest()
    )


def test_final_control_rejects_non_pass_and_contamination() -> None:
    with pytest.raises(CiboCapitalManagementError, match="not PASS"):
        bind_final_exam_control_artifact(
            receipt_id="P1",
            evidence_kind=KIND,
            source_artifact_json=_artifact(status="FAIL"),
        )
    with pytest.raises(CiboCapitalManagementError, match="governance contamination"):
        bind_final_exam_control_artifact(
            receipt_id="P1",
            evidence_kind=KIND,
            source_artifact_json=_artifact(contaminated=True),
        )


def test_final_control_rejects_digest_tamper() -> None:
    receipt = _receipt()
    with pytest.raises(CiboCapitalManagementError, match="digest mismatch"):
        replace(receipt, source_artifact_sha256="sha256:" + "f" * 64)


def test_final_controls_require_same_head_policy_and_phase22() -> None:
    receipt = _receipt()
    require_final_exam_control_receipts(
        receipts=(receipt,),
        required_receipt_ids=("P1",),
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
        phase22_qualification_artifact_sha256=PHASE22,
    )
    with pytest.raises(CiboCapitalManagementError, match="Phase22-artifact drift"):
        require_final_exam_control_receipts(
            receipts=(receipt,),
            required_receipt_ids=("P1",),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
            phase22_qualification_artifact_sha256="sha256:" + "d" * 64,
        )
