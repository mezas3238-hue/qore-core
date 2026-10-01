from __future__ import annotations

import importlib.util
import json
from datetime import timedelta
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_exam_control_receipt import (
    bind_final_exam_control_artifact,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_final_integrated_exam_assembly import (
    assemble_final_integrated_control_package,
    assess_assembled_final_integrated_exam,
)
from qore.infrastructure.cibo_receipt_bound_final_integrated_exam_v2 import (
    required_final_exam_control_ids,
)

_FIXTURE_PATH = Path(__file__).with_name("test_cibo_ce2i_final_certification.py")
_SPEC = importlib.util.spec_from_file_location("_assembly_fixture", _FIXTURE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)

HEAD = "a" * 40


def _chain():
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    observed = phase22.qualified_at + timedelta(minutes=1)
    receipts = []
    for receipt_id in reversed(required_final_exam_control_ids()):
        payload = {
            "schema": "qore.cibo.final-assembly.test.v1",
            "evidence_binding_id": receipt_id,
            "evidence_kind": "FINAL_INTEGRATED_EXAM_CONTROL",
            "producer_gate_id": f"gate:{receipt_id}",
            "integrated_git_sha": HEAD,
            "policy_identity_sha256": phase22.candidate_parameter_sha256,
            "phase22_qualification_artifact_sha256": (
                phase22.qualification_artifact_sha256
            ),
            "certification_stage": "POST_PHASE22",
            "observed_at": observed.isoformat(),
            "status": "PASS",
            "failures": [],
            "productive_authority": False,
            "synthetic_evidence_used": False,
            "holdout_mining_used": False,
            "outcome_aware_refit": False,
            "operational_authority_claimed": False,
        }
        receipts.append(
            bind_final_exam_control_artifact(
                receipt_id=receipt_id,
                evidence_kind="FINAL_INTEGRATED_EXAM_CONTROL",
                source_artifact_json=(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n"
                ),
            )
        )
    return phase21, phase22, tuple(receipts)


def test_assembly_orders_exact_18_receipts_and_runs_final_exam() -> None:
    phase21, phase22, receipts = _chain()
    package = assemble_final_integrated_control_package(
        integrated_git_sha=HEAD,
        receipts=receipts,
    )
    assert tuple(item.receipt_id for item in package.receipts) == (
        required_final_exam_control_ids()
    )
    assert len(package.receipts) == 18
    assert package.fingerprint().startswith("sha256:")

    report = assess_assembled_final_integrated_exam(
        package=package,
        phase21_manifest=phase21,
        phase22_receipt=phase22,
    )
    assert report.status is FinalIntegratedExamStatus.PASS
    assert report.blockers == ()


def test_assembly_rejects_missing_receipt() -> None:
    _phase21, _phase22, receipts = _chain()
    with pytest.raises(
        CiboCapitalManagementError,
        match="missing receipts",
    ):
        assemble_final_integrated_control_package(
            integrated_git_sha=HEAD,
            receipts=receipts[:-1],
        )


def test_assembly_rejects_cross_head_receipt() -> None:
    _phase21, _phase22, receipts = _chain()
    altered = list(receipts)
    item = altered[0]
    payload = json.loads(item.source_artifact_json)
    payload["integrated_git_sha"] = "b" * 40
    altered[0] = bind_final_exam_control_artifact(
        receipt_id=item.receipt_id,
        evidence_kind=item.evidence_kind,
        source_artifact_json=json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="cross-HEAD receipt",
    ):
        assemble_final_integrated_control_package(
            integrated_git_sha=HEAD,
            receipts=tuple(altered),
        )
