from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    build_arch_b_forward_economic_manifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    VersionedCmaSettlementBook,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    bind_cross_boundary_pass_artifact,
)
from qore.infrastructure.cibo_receipt_bound_usd60_exam_readiness import (
    assess_receipt_bound_usd60_pre_exam_readiness,
)
from qore.infrastructure.cibo_t20_capital_release_evidence import (
    VersionedT20CapitalReleaseBook,
)
from qore.infrastructure.cibo_usd60_prerequisite_receipts import (
    required_usd60_pre_exam_receipt_ids,
)

T0 = datetime(2026, 9, 30, 23, 30, tzinfo=UTC)
HEAD = "a" * 40
POLICY = FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()


def _empty_manifest():
    return build_arch_b_forward_economic_manifest(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        policy_book=VersionedPhase20ForwardPolicyBook(generation=0),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        settlement_book=VersionedCmaSettlementBook(generation=0),
        release_book=VersionedT20CapitalReleaseBook(generation=0),
    )


def _artifact(receipt_id: str) -> str:
    payload = {
        "schema": "qore.cibo.usd60-source-test.v1",
        "producer_gate_id": f"gate:{receipt_id}",
        "integrated_git_sha": HEAD,
        "policy_identity_sha256": POLICY,
        "observed_at": T0.isoformat(),
        "status": "PASS",
        "failures": [],
        "holdout_outcomes_inspected": False,
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _receipts():
    return tuple(
        bind_cross_boundary_pass_artifact(
            receipt_id=receipt_id,
            evidence_kind="USD60_PRE_EXAM_PREREQUISITE",
            source_artifact_json=_artifact(receipt_id),
        )
        for receipt_id in required_usd60_pre_exam_receipt_ids()
    )


def test_receipts_can_pass_prerequisites_but_not_replace_forward_thresholds() -> None:
    report = assess_receipt_bound_usd60_pre_exam_readiness(
        forward_manifest=_empty_manifest(),
        receipts=_receipts(),
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
    )

    assert report.prerequisite_count == 7
    assert report.passed_prerequisite_count == 7
    assert report.forward_manifest_ready is False
    assert report.ready_for_governed_exam is False
    assert "USD60_PHASE20D_FORWARD_MANIFEST_NOT_READY" in report.blockers
    assert report.holdout_access_authority is False
    assert report.certification_ready is False
    assert report.productive_authority is False


def test_missing_receipt_fails_before_readiness_evaluation() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        assess_receipt_bound_usd60_pre_exam_readiness(
            forward_manifest=_empty_manifest(),
            receipts=_receipts()[:-1],
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )


def test_policy_identity_drift_fails_before_receipt_use() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="frozen policy identity drift",
    ):
        assess_receipt_bound_usd60_pre_exam_readiness(
            forward_manifest=_empty_manifest(),
            receipts=_receipts(),
            integrated_git_sha=HEAD,
            policy_identity_sha256="sha256:" + "f" * 64,
        )
