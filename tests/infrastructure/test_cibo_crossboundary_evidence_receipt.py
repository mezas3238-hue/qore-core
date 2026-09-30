from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    CiboCrossBoundaryEvidenceReceipt,
    build_cross_boundary_evidence_receipt,
    require_cross_boundary_receipts,
)

T0 = datetime(2026, 9, 30, 20, 45, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64


def _receipt(receipt_id: str = "P1") -> CiboCrossBoundaryEvidenceReceipt:
    return build_cross_boundary_evidence_receipt(
        receipt_id=receipt_id,
        evidence_kind="FINAL_EXAM_PREREQUISITE",
        producer_gate_id="QORE_CIBO_SAMPLE_GATE",
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
        observed_at=T0,
    )


def test_builder_recomputes_canonical_artifact_digest() -> None:
    receipt = _receipt()

    artifact = json.loads(receipt.artifact_json)
    assert artifact["status"] == "PASS"
    assert artifact["integrated_git_sha"] == HEAD
    assert receipt.artifact_sha256.startswith("sha256:")
    assert receipt.passed is True
    assert receipt.productive_authority is False


def test_fake_sha_cannot_replace_bound_artifact() -> None:
    receipt = _receipt()

    with pytest.raises(
        CiboCapitalManagementError,
        match="artifact digest mismatch",
    ):
        replace(receipt, artifact_sha256="sha256:" + "c" * 64)


def test_tampered_artifact_cannot_keep_original_digest() -> None:
    receipt = _receipt()
    payload = json.loads(receipt.artifact_json)
    payload["status"] = "FAIL"
    tampered = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    with pytest.raises(
        CiboCapitalManagementError,
        match="artifact digest mismatch",
    ):
        replace(receipt, artifact_json=tampered)


def test_receipts_are_bound_to_exact_integrated_head() -> None:
    receipt = _receipt()

    with pytest.raises(
        CiboCapitalManagementError,
        match="integrated-head drift",
    ):
        require_cross_boundary_receipts(
            receipts=(receipt,),
            required_receipt_ids=("P1",),
            integrated_git_sha="d" * 40,
            policy_identity_sha256=POLICY,
        )


def test_receipts_are_bound_to_policy_identity() -> None:
    receipt = _receipt()

    with pytest.raises(
        CiboCapitalManagementError,
        match="policy-identity drift",
    ):
        require_cross_boundary_receipts(
            receipts=(receipt,),
            required_receipt_ids=("P1",),
            integrated_git_sha=HEAD,
            policy_identity_sha256="sha256:" + "e" * 64,
        )


def test_missing_or_extra_receipts_fail_closed() -> None:
    p1 = _receipt("P1")
    p2 = _receipt("P2")

    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        require_cross_boundary_receipts(
            receipts=(p1,),
            required_receipt_ids=("P1", "P2"),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )

    with pytest.raises(
        CiboCapitalManagementError,
        match="unexpected receipt ids",
    ):
        require_cross_boundary_receipts(
            receipts=(p1, p2),
            required_receipt_ids=("P1",),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )


def test_duplicate_receipt_ids_fail_closed() -> None:
    p1 = _receipt("P1")

    with pytest.raises(
        CiboCapitalManagementError,
        match="duplicate receipt id",
    ):
        require_cross_boundary_receipts(
            receipts=(p1, p1),
            required_receipt_ids=("P1",),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )
