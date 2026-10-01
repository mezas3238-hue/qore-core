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
from qore.infrastructure.cibo_final_exam_control_receipt import (
    bind_final_exam_control_artifact,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_receipt_bound_final_integrated_exam_v2 import (
    assess_receipt_bound_final_integrated_exam_v2,
    required_final_exam_control_ids,
)

T0 = datetime(2026, 10, 1, 18, 15, tzinfo=UTC)
HEAD = "a" * 40
POLICY = FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
_FIXTURE_PATH = Path(__file__).with_name("test_cibo_ce2i_final_certification.py")
_SPEC = importlib.util.spec_from_file_location("_final_cert_fixture_v2", _FIXTURE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)


def _artifact(receipt_id: str, phase22_sha: str, *, head: str = HEAD) -> str:
    payload = {
        "schema": "qore.cibo.final-exam-control.test.v2",
        "evidence_binding_id": receipt_id,
        "evidence_kind": "FINAL_INTEGRATED_EXAM_CONTROL",
        "producer_gate_id": f"gate:{receipt_id}",
        "integrated_git_sha": head,
        "policy_identity_sha256": POLICY,
        "phase22_qualification_artifact_sha256": phase22_sha,
        "certification_stage": "POST_PHASE22",
        "observed_at": T0.isoformat(),
        "status": "PASS",
        "failures": [],
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _chain():
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    return phase21, phase22


def _receipts(phase22_sha: str, *, head: str = HEAD):
    return tuple(
        bind_final_exam_control_artifact(
            receipt_id=receipt_id,
            evidence_kind="FINAL_INTEGRATED_EXAM_CONTROL",
            source_artifact_json=_artifact(receipt_id, phase22_sha, head=head),
        )
        for receipt_id in required_final_exam_control_ids()
    )


def test_eighteen_v2_receipts_drive_final_exam_pass() -> None:
    phase21, phase22 = _chain()
    report = assess_receipt_bound_final_integrated_exam_v2(
        integrated_head_sha=HEAD,
        phase21_manifest=phase21,
        phase22_receipt=phase22,
        receipts=_receipts(phase22.qualification_artifact_sha256),
    )
    assert len(required_final_exam_control_ids()) == 18
    assert report.status is FinalIntegratedExamStatus.PASS
    assert report.blockers == ()
    assert report.live_authorized is False
    assert report.real_capital_authorized is False


def test_final_exam_v2_rejects_cross_head_or_phase22_drift() -> None:
    phase21, phase22 = _chain()
    with pytest.raises(CiboCapitalManagementError, match="integrated-head drift"):
        assess_receipt_bound_final_integrated_exam_v2(
            integrated_head_sha=HEAD,
            phase21_manifest=phase21,
            phase22_receipt=phase22,
            receipts=_receipts(
                phase22.qualification_artifact_sha256,
                head="e" * 40,
            ),
        )
    bad_receipts = _receipts("sha256:" + "f" * 64)
    with pytest.raises(CiboCapitalManagementError, match="Phase22-artifact drift"):
        assess_receipt_bound_final_integrated_exam_v2(
            integrated_head_sha=HEAD,
            phase21_manifest=phase21,
            phase22_receipt=phase22,
            receipts=bad_receipts,
        )
