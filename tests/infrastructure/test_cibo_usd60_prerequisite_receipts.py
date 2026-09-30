from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    bind_cross_boundary_pass_artifact,
)
from qore.infrastructure.cibo_usd60_prerequisite_receipts import (
    require_usd60_pre_exam_receipts,
    required_usd60_pre_exam_receipt_ids,
)

T0 = datetime(2026, 9, 30, 21, 15, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64


def _artifact(receipt_id: str, *, contaminated: bool = False) -> str:
    payload = {
        "schema": "qore.cibo.usd60-prerequisite-test.v1",
        "evidence_binding_id": receipt_id,
        "evidence_kind": "USD60_PRE_EXAM_PREREQUISITE",
        "producer_gate_id": f"gate:{receipt_id}",
        "integrated_git_sha": HEAD,
        "policy_identity_sha256": POLICY,
        "observed_at": T0.isoformat(),
        "status": "PASS",
        "failures": [],
        "holdout_outcomes_inspected": False,
        "productive_authority": False,
        "synthetic_evidence_used": contaminated,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _receipts(*, contaminated_id: str | None = None):
    return tuple(
        bind_cross_boundary_pass_artifact(
            receipt_id=receipt_id,
            evidence_kind="USD60_PRE_EXAM_PREREQUISITE",
            source_artifact_json=_artifact(
                receipt_id,
                contaminated=receipt_id == contaminated_id,
            ),
        )
        for receipt_id in required_usd60_pre_exam_receipt_ids()
    )


def test_seven_bound_usd60_prerequisites_are_required() -> None:
    bound = require_usd60_pre_exam_receipts(
        receipts=_receipts(),
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
    )

    assert len(required_usd60_pre_exam_receipt_ids()) == 7
    assert set(bound) == set(required_usd60_pre_exam_receipt_ids())


def test_missing_usd60_prerequisite_fails_closed() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        require_usd60_pre_exam_receipts(
            receipts=_receipts()[:-1],
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )


def test_wrong_evidence_kind_is_rejected_by_source_binder() -> None:
    receipt_id = required_usd60_pre_exam_receipt_ids()[0]
    receipts = list(_receipts())
    receipts[0] = bind_cross_boundary_pass_artifact(
        receipt_id=receipt_id,
        evidence_kind="FINAL_INTEGRATED_EXAM_CONTROL",
        source_artifact_json=_artifact(receipt_id),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="evidence kind drift",
    ):
        require_usd60_pre_exam_receipts(
            receipts=tuple(receipts),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )


def test_contaminated_usd60_prerequisite_fails_closed() -> None:
    receipt_id = required_usd60_pre_exam_receipt_ids()[0]

    with pytest.raises(
        CiboCapitalManagementError,
        match="USD60 receipt governance contamination",
    ):
        require_usd60_pre_exam_receipts(
            receipts=_receipts(contaminated_id=receipt_id),
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )
