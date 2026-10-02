from __future__ import annotations

import importlib.util
import json
from datetime import timedelta
from pathlib import Path

import pytest

from qore.infrastructure.cibo_arch_a_final_pre_exam_control import (
    build_pre_exam_zero_open_control,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_FIXTURE_PATH = Path(__file__).with_name("test_cibo_ce2i_final_certification.py")
_SPEC = importlib.util.spec_from_file_location("_final_cert_fixture_p2", _FIXTURE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)
HEAD = "a" * 40


def _pre_exam(*, passed: bool = True) -> str:
    payload = {
        "schema": "QORE_CIBO_ZERO_OPEN_WORK_GATE_V1",
        "scope": "PRE_EXAM",
        "pass": passed,
        "mandatory_workstream_count": 62,
        "terminal_workstream_count": 62,
        "open_workstream_ids": [],
        "certification_blocking_external_dependency_ids": [],
        "missing_required_artifacts": [],
        "high_signal_marker_hits": [],
        "inventory_paths": ["a.py"],
        "inventory_assignments": [
            {"path": "a.py", "workstream_id": "T01"}
        ],
        "orphan_candidate_paths": [],
        "reasons": [] if passed else ["UNCLOSED_REQUIRED_WORKSTREAM"],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def test_p2_binds_exact_pre_exam_pass_to_same_head() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    receipt = build_pre_exam_zero_open_control(
        pre_exam_artifact_json=_pre_exam(),
        pre_exam_evidence_git_sha=HEAD,
        integrated_git_sha=HEAD,
        phase22_receipt=phase22,
        observed_at=phase22.qualified_at + timedelta(minutes=1),
    )
    assert receipt.receipt_id == "P2_PRE_EXAM_ZERO_OPEN_PASS"
    assert receipt.integrated_git_sha == HEAD


def test_p2_rejects_failed_pre_exam() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    with pytest.raises(
        CiboCapitalManagementError,
        match="field mismatch: pass",
    ):
        build_pre_exam_zero_open_control(
            pre_exam_artifact_json=_pre_exam(passed=False),
            pre_exam_evidence_git_sha=HEAD,
            integrated_git_sha=HEAD,
            phase22_receipt=phase22,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_p2_rejects_cross_head_reuse() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    with pytest.raises(CiboCapitalManagementError, match="evidence HEAD drift"):
        build_pre_exam_zero_open_control(
            pre_exam_artifact_json=_pre_exam(),
            pre_exam_evidence_git_sha="b" * 40,
            integrated_git_sha=HEAD,
            phase22_receipt=phase22,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )
