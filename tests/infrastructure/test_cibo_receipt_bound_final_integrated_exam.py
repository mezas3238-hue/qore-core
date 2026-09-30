from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    CiboEconomicCertificationDecision,
    CiboEconomicCertificationStatus,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    bind_cross_boundary_pass_artifact,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_receipt_bound_final_integrated_exam import (
    assess_receipt_bound_final_integrated_exam,
    required_final_exam_receipt_ids,
)

T0 = datetime(2026, 9, 30, 21, 0, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64


def _artifact(receipt_id: str, *, head: str = HEAD, contaminated: bool = False) -> str:
    payload = {
        "schema": "qore.cibo.bound-final-exam-test.v1",
        "producer_gate_id": f"gate:{receipt_id}",
        "integrated_git_sha": head,
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


def _receipts(*, contaminated_id: str | None = None, head: str = HEAD):
    return tuple(
        bind_cross_boundary_pass_artifact(
            receipt_id=receipt_id,
            evidence_kind="FINAL_INTEGRATED_EXAM_CONTROL",
            source_artifact_json=_artifact(
                receipt_id,
                head=head,
                contaminated=receipt_id == contaminated_id,
            ),
        )
        for receipt_id in required_final_exam_receipt_ids()
    )


def _economic() -> CiboEconomicCertificationDecision:
    return CiboEconomicCertificationDecision(
        status=CiboEconomicCertificationStatus.CERTIFIED,
        candidate_id="phase20-v3",
        candidate_parameter_sha256=POLICY,
        phase21_manifest_sha256="sha256:" + "c" * 64,
        phase22_plan_sha256="sha256:" + "d" * 64,
        blockers=(),
    )


def test_eighteen_bound_receipts_drive_final_exam_pass() -> None:
    report = assess_receipt_bound_final_integrated_exam(
        integrated_head_sha=HEAD,
        economic_certification=_economic(),
        receipts=_receipts(),
    )

    assert len(required_final_exam_receipt_ids()) == 18
    assert report.status is FinalIntegratedExamStatus.PASS
    assert report.blockers == ()
    assert report.live_authorized is False
    assert report.real_capital_authorized is False
    assert report.merge_authorized is False


def test_missing_receipt_fails_closed_before_exam() -> None:
    receipts = _receipts()[:-1]

    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        assess_receipt_bound_final_integrated_exam(
            integrated_head_sha=HEAD,
            economic_certification=_economic(),
            receipts=receipts,
        )


def test_cross_head_receipt_fails_closed_before_exam() -> None:
    receipts = _receipts(head="e" * 40)

    with pytest.raises(
        CiboCapitalManagementError,
        match="integrated-head drift",
    ):
        assess_receipt_bound_final_integrated_exam(
            integrated_head_sha=HEAD,
            economic_certification=_economic(),
            receipts=receipts,
        )


def test_governance_contamination_fails_closed_before_exam() -> None:
    receipt_id = required_final_exam_receipt_ids()[0]

    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        assess_receipt_bound_final_integrated_exam(
            integrated_head_sha=HEAD,
            economic_certification=_economic(),
            receipts=_receipts(contaminated_id=receipt_id),
        )
