"""Build P2 PRE_EXAM Zero-Open control for Final Integrated CIBO Exam."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    Phase22QualificationReceipt,
)
from qore.infrastructure.cibo_final_exam_control_receipt import (
    CiboFinalExamControlReceipt,
    bind_final_exam_control_artifact,
)

_ZERO_OPEN_SCHEMA = "QORE_CIBO_ZERO_OPEN_WORK_GATE_V1"
_ARTIFACT_SCHEMA = "qore.cibo.pre-exam-zero-open-control.v1"
_EVIDENCE_KIND = "FINAL_INTEGRATED_EXAM_CONTROL"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def _parse_canonical(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "P2 PRE_EXAM artifact is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "P2 PRE_EXAM artifact must be object"
        )
    canonical = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if canonical != value:
        raise CiboCapitalManagementError(
            "P2 PRE_EXAM artifact must use canonical JSON"
        )
    return payload


def build_pre_exam_zero_open_control(
    *,
    pre_exam_artifact_json: str,
    pre_exam_evidence_git_sha: str,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    observed_at: datetime,
) -> CiboFinalExamControlReceipt:
    if _SHA1_RE.fullmatch(pre_exam_evidence_git_sha) is None:
        raise CiboCapitalManagementError(
            "P2 PRE_EXAM evidence Git SHA invalid"
        )
    if pre_exam_evidence_git_sha != integrated_git_sha:
        raise CiboCapitalManagementError(
            "P2 PRE_EXAM evidence HEAD drift"
        )
    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "P2 PRE_EXAM requires canonical Phase22 receipt"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "P2 PRE_EXAM observed_at must be timezone-aware"
        )
    if observed_at <= phase22_receipt.qualified_at:
        raise CiboCapitalManagementError(
            "P2 PRE_EXAM must be post-Phase22 qualification"
        )

    pre = _parse_canonical(pre_exam_artifact_json)
    expected = {
        "schema": _ZERO_OPEN_SCHEMA,
        "scope": "PRE_EXAM",
        "pass": True,
        "mandatory_workstream_count": 62,
        "terminal_workstream_count": 62,
        "open_workstream_ids": [],
        "certification_blocking_external_dependency_ids": [],
        "missing_required_artifacts": [],
        "high_signal_marker_hits": [],
        "orphan_candidate_paths": [],
        "reasons": [],
    }
    for key, value in expected.items():
        if pre.get(key) != value:
            raise CiboCapitalManagementError(
                f"P2 PRE_EXAM artifact field mismatch: {key}"
            )
    source_sha = "sha256:" + hashlib.sha256(
        pre_exam_artifact_json.encode("utf-8")
    ).hexdigest()
    payload = {
        "schema": _ARTIFACT_SCHEMA,
        "evidence_binding_id": "P2_PRE_EXAM_ZERO_OPEN_PASS",
        "evidence_kind": _EVIDENCE_KIND,
        "producer_gate_id": "CIBO_PRE_EXAM_ZERO_OPEN_CONTROL_V1",
        "integrated_git_sha": integrated_git_sha,
        "policy_identity_sha256": phase22_receipt.candidate_parameter_sha256,
        "phase22_qualification_artifact_sha256": (
            phase22_receipt.qualification_artifact_sha256
        ),
        "certification_stage": "POST_PHASE22",
        "observed_at": observed_at.isoformat(),
        "status": "PASS",
        "failures": [],
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
        "pre_exam_evidence_git_sha": pre_exam_evidence_git_sha,
        "pre_exam_artifact_sha256": source_sha,
        "pre_exam_scope": "PRE_EXAM",
        "pre_exam_mandatory_count": 62,
        "pre_exam_terminal_count": 62,
    }
    artifact_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return bind_final_exam_control_artifact(
        receipt_id="P2_PRE_EXAM_ZERO_OPEN_PASS",
        evidence_kind=_EVIDENCE_KIND,
        source_artifact_json=artifact_json,
    )
