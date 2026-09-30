from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
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
POLICY = FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()

_FINAL_CERT_TEST = Path(__file__).with_name(
    "test_cibo_ce2i_final_certification.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "_cibo_final_certification_fixture",
    _FINAL_CERT_TEST,
)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)


def _artifact(
    receipt_id: str,
    *,
    head: str = HEAD,
    contaminated: bool = False,
) -> str:
    payload = {
        "schema": "qore.cibo.bound-final-exam-test.v1",
        "evidence_binding_id": receipt_id,
        "evidence_kind": "FINAL_INTEGRATED_EXAM_CONTROL",
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


def _receipts(
    *,
    contaminated_id: str | None = None,
    head: str = HEAD,
):
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


def _canonical_chain():
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(
        phase21_sha=phase21.manifest_sha256(),
    )
    return phase21, phase22


def test_eighteen_bound_receipts_drive_final_exam_pass() -> None:
    phase21, phase22 = _canonical_chain()

    report = assess_receipt_bound_final_integrated_exam(
        integrated_head_sha=HEAD,
        phase21_manifest=phase21,
        phase22_receipt=phase22,
        receipts=_receipts(),
    )

    assert len(required_final_exam_receipt_ids()) == 18
    assert report.status is FinalIntegratedExamStatus.PASS
    assert report.blockers == ()
    assert report.live_authorized is False
    assert report.real_capital_authorized is False
    assert report.merge_authorized is False


def test_missing_receipt_fails_closed_before_exam() -> None:
    phase21, phase22 = _canonical_chain()

    with pytest.raises(
        CiboCapitalManagementError,
        match="required receipts missing",
    ):
        assess_receipt_bound_final_integrated_exam(
            integrated_head_sha=HEAD,
            phase21_manifest=phase21,
            phase22_receipt=phase22,
            receipts=_receipts()[:-1],
        )


def test_cross_head_receipt_fails_closed_before_exam() -> None:
    phase21, phase22 = _canonical_chain()

    with pytest.raises(
        CiboCapitalManagementError,
        match="integrated-head drift",
    ):
        assess_receipt_bound_final_integrated_exam(
            integrated_head_sha=HEAD,
            phase21_manifest=phase21,
            phase22_receipt=phase22,
            receipts=_receipts(head="e" * 40),
        )


def test_governance_contamination_fails_closed_before_exam() -> None:
    phase21, phase22 = _canonical_chain()
    receipt_id = required_final_exam_receipt_ids()[0]

    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        assess_receipt_bound_final_integrated_exam(
            integrated_head_sha=HEAD,
            phase21_manifest=phase21,
            phase22_receipt=phase22,
            receipts=_receipts(contaminated_id=receipt_id),
        )


def test_phase22_receipt_must_match_exact_phase21_chain() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    detached = _FIXTURE._receipt(
        phase21_sha="sha256:" + "f" * 64,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="exact Phase21/Phase22 economic certification",
    ):
        assess_receipt_bound_final_integrated_exam(
            integrated_head_sha=HEAD,
            phase21_manifest=phase21,
            phase22_receipt=detached,
            receipts=_receipts(),
        )
