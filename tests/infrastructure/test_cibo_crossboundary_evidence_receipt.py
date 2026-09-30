from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    bind_cross_boundary_pass_artifact,
    require_cross_boundary_receipts,
)

T0 = datetime(2026, 9, 30, 20, 45, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64
KIND = "FINAL_EXAM_PREREQUISITE"


def _artifact(
    *,
    receipt_id: str = "P1",
    evidence_kind: str = KIND,
    status: str = "PASS",
    head: str = HEAD,
    policy: str = POLICY,
) -> str:
    payload = {
        "schema": "qore.cibo.test-producer.v1",
        "evidence_binding_id": receipt_id,
        "evidence_kind": evidence_kind,
        "producer_gate_id": "QORE_CIBO_SAMPLE_GATE",
        "integrated_git_sha": head,
        "policy_identity_sha256": policy,
        "observed_at": T0.isoformat(),
        "status": status,
        "failures": [] if status == "PASS" else ["FAILED"],
        "holdout_outcomes_inspected": False,
        "productive_authority": False,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _receipt(receipt_id: str = "P1"):
    return bind_cross_boundary_pass_artifact(
        receipt_id=receipt_id,
        evidence_kind=KIND,
        source_artifact_json=_artifact(receipt_id=receipt_id),
    )


def test_binder_derives_pass_from_existing_canonical_artifact() -> None:
    receipt = _receipt()

    assert receipt.integrated_git_sha == HEAD
    assert receipt.policy_identity_sha256 == POLICY
    assert receipt.source_artifact_sha256 == (
        "sha256:"
        + hashlib.sha256(_artifact().encode("utf-8")).hexdigest()
    )
    assert receipt.productive_authority is False


def test_non_pass_source_artifact_cannot_be_bound() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="source artifact is not PASS",
    ):
        bind_cross_boundary_pass_artifact(
            receipt_id="P1",
            evidence_kind=KIND,
            source_artifact_json=_artifact(status="FAIL"),
        )


def test_source_artifact_cannot_be_relabelled_to_another_receipt_id() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="binding identity drift",
    ):
        bind_cross_boundary_pass_artifact(
            receipt_id="P2",
            evidence_kind=KIND,
            source_artifact_json=_artifact(receipt_id="P1"),
        )


def test_source_artifact_cannot_be_relabelled_to_another_kind() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="evidence kind drift",
    ):
        bind_cross_boundary_pass_artifact(
            receipt_id="P1",
            evidence_kind="USD60_PRE_EXAM_PREREQUISITE",
            source_artifact_json=_artifact(
                receipt_id="P1",
                evidence_kind=KIND,
            ),
        )


def test_fake_digest_cannot_replace_bound_source_artifact() -> None:
    receipt = _receipt()

    with pytest.raises(
        CiboCapitalManagementError,
        match="source artifact digest mismatch",
    ):
        replace(receipt, source_artifact_sha256="sha256:" + "c" * 64)


def test_tampered_source_artifact_cannot_keep_original_digest() -> None:
    receipt = _receipt()
    payload = json.loads(receipt.source_artifact_json)
    payload["status"] = "FAIL"
    payload["failures"] = ["FAILED"]
    tampered = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    with pytest.raises(
        CiboCapitalManagementError,
        match="source artifact digest mismatch",
    ):
        replace(receipt, source_artifact_json=tampered)


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
