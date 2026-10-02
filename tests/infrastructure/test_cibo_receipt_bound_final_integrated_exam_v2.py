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
_PRODUCERS = {
    "P1_SOURCE_OF_TRUTH_RECONCILED": "CIBO_FINAL_SOURCE_OF_TRUTH_CONTROL_V2",
    "P2_PRE_EXAM_ZERO_OPEN_PASS": "CIBO_PRE_EXAM_ZERO_OPEN_CONTROL_V1",
    "P3_CERTIFICATION_CI_CLEAR": "CIBO_FINAL_CERTIFICATION_CI_CLEAR_V1",
    "P4_PROVIDER_RISK_CMA_FORWARD_TRUTH": "CIBO_P4_PROVIDER_RISK_CMA_FORWARD_TRUTH_V1",
    "P5_PHASE20D_PASS": "CIBO_P5_PHASE20D_PASS_V1",
    "P6_POLICY_CALIBRATION_FREEZE": "CIBO_P6_POLICY_CALIBRATION_FREEZE_V1",
    "P7_SCIENTIFIC_CLOSURE": "CIBO_SCIENTIFIC_CLOSURE_41_V1",
    "P8_COMPOUND_CLOSURE": "CIBO_CAPITAL_COMPOUND_CLOSURE_13_V1",
    "E1_AUTHORITY": "CIBO_ARCH_A_E1_AUTHORITY_V1",
    "E2_CAPITAL_CONSERVATION": "CIBO_ARCH_A_E2_CAPITAL_CONSERVATION_V1",
    "E3_REALIZED_CAPITAL_LAW": "CIBO_ARCH_A_E3_REALIZED_CAPITAL_LAW_V1",
    "E4_PROVIDER_TRUTH": "CIBO_ARCH_A_E4_PROVIDER_TRUTH_V2",
    "E5_RISK_PRECEDENCE": "CIBO_ARCH_A_E5_RISK_PRECEDENCE_V1",
    "E6_CHRONOLOGY_NO_LEAKAGE": "CIBO_ARCH_A_E6_CHRONOLOGY_NO_LEAKAGE_V1",
    "E7_ECONOMIC_NONCOMPENSATION": "CIBO_ARCH_A_E7_ECONOMIC_NONCOMPENSATION_V1",
    "E8_STRESS_INTEGRITY": "CIBO_ARCH_A_E8_STRESS_INTEGRITY_V1",
    "E9_TEMPORAL_REPLICATION": "CIBO_ARCH_A_E9_TEMPORAL_REPLICATION_V1",
    "E10_DETERMINISTIC_REPLAY": "CIBO_ARCH_A_E10_DETERMINISTIC_REPLAY_V1",
}
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
        "producer_gate_id": _PRODUCERS[receipt_id],
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


def test_final_exam_v2_rejects_wrong_producer_gate() -> None:
    phase21, phase22 = _chain()
    receipts = list(_receipts(phase22.qualification_artifact_sha256))
    index = required_final_exam_control_ids().index("E4_PROVIDER_TRUTH")
    payload = json.loads(receipts[index].source_artifact_json)
    payload["producer_gate_id"] = "CIBO_ARCH_A_E4_PROVIDER_TRUTH_V1"
    receipts[index] = bind_final_exam_control_artifact(
        receipt_id="E4_PROVIDER_TRUTH",
        evidence_kind="FINAL_INTEGRATED_EXAM_CONTROL",
        source_artifact_json=json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="producer-gate drift: E4_PROVIDER_TRUTH",
    ):
        assess_receipt_bound_final_integrated_exam_v2(
            integrated_head_sha=HEAD,
            phase21_manifest=phase21,
            phase22_receipt=phase22,
            receipts=tuple(receipts),
        )
