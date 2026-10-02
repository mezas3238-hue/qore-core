"""Receipt-bound P3 CI-clear control for the Final Integrated CIBO Exam."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

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

_SCOPE_ID = "CIBO_FINAL_CERTIFICATION_CI_SCOPE_V1"
_SCHEMA = "qore.cibo.final-ci-control.v1"
_EVIDENCE_KIND = "FINAL_INTEGRATED_EXAM_CONTROL"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class FinalCiWorkflowRequirement:
    workflow_name: str
    workflow_path: str
    workflow_file_sha256: str

    def __post_init__(self) -> None:
        if not self.workflow_name or not self.workflow_path:
            raise CiboCapitalManagementError(
                "P3 CI workflow requirement identity is required"
            )
        if _SHA256_RE.fullmatch(self.workflow_file_sha256) is None:
            raise CiboCapitalManagementError(
                "P3 CI workflow file digest invalid"
            )


@dataclass(frozen=True, slots=True)
class FinalCiScope:
    scope_id: str
    integrated_git_sha: str
    source_truth_control_sha256: str
    requirements: tuple[FinalCiWorkflowRequirement, ...]
    frozen_at: datetime
    frozen: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.scope_id != _SCOPE_ID:
            raise CiboCapitalManagementError("P3 CI scope identity drift")
        if _SHA1_RE.fullmatch(self.integrated_git_sha) is None:
            raise CiboCapitalManagementError("P3 CI scope HEAD invalid")
        if _SHA256_RE.fullmatch(self.source_truth_control_sha256) is None:
            raise CiboCapitalManagementError(
                "P3 CI source-truth digest invalid"
            )
        if not self.requirements:
            raise CiboCapitalManagementError(
                "P3 CI scope requires at least one workflow"
            )
        names = tuple(item.workflow_name for item in self.requirements)
        paths = tuple(item.workflow_path for item in self.requirements)
        if len(names) != len(set(names)) or len(paths) != len(set(paths)):
            raise CiboCapitalManagementError(
                "P3 CI scope duplicate workflow identity"
            )
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "P3 CI scope frozen_at must be timezone-aware"
            )
        if type(self.frozen) is not bool or not self.frozen:
            raise CiboCapitalManagementError(
                "P3 CI scope must be explicitly frozen"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "P3 CI scope grants no productive authority"
            )

    def fingerprint(self) -> str:
        payload = {
            "scope_id": self.scope_id,
            "integrated_git_sha": self.integrated_git_sha,
            "source_truth_control_sha256": self.source_truth_control_sha256,
            "requirements": [asdict(item) for item in self.requirements],
            "frozen_at": self.frozen_at.isoformat(),
            "frozen": self.frozen,
            "productive_authority": self.productive_authority,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class FinalCiCheckResult:
    workflow_name: str
    workflow_path: str
    head_sha: str
    run_id: int
    status: str
    conclusion: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.workflow_name or not self.workflow_path:
            raise CiboCapitalManagementError(
                "P3 CI check identity is required"
            )
        if _SHA1_RE.fullmatch(self.head_sha) is None:
            raise CiboCapitalManagementError("P3 CI check HEAD invalid")
        if type(self.run_id) is not int or self.run_id <= 0:
            raise CiboCapitalManagementError("P3 CI run id invalid")
        if self.status != "completed" or self.conclusion != "success":
            raise CiboCapitalManagementError(
                "P3 CI check must be completed/success"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "P3 CI observed_at must be timezone-aware"
            )


def build_p3_ci_clear_control(
    *,
    scope: FinalCiScope,
    results: tuple[FinalCiCheckResult, ...],
    source_truth_control: CiboFinalExamControlReceipt,
    phase22_receipt: Phase22QualificationReceipt,
    observed_at: datetime,
) -> CiboFinalExamControlReceipt:
    """Build P3 only when every frozen required workflow is green on one HEAD."""

    if not isinstance(scope, FinalCiScope):
        raise CiboCapitalManagementError("P3 requires canonical CI scope")
    if not isinstance(source_truth_control, CiboFinalExamControlReceipt):
        raise CiboCapitalManagementError(
            "P3 requires canonical P1 source-truth control"
        )
    if source_truth_control.receipt_id != "P1_SOURCE_OF_TRUTH_RECONCILED":
        raise CiboCapitalManagementError("P3 requires P1 source-truth control")
    if (
        source_truth_control.producer_gate_id
        != "CIBO_FINAL_SOURCE_OF_TRUTH_CONTROL_V2"
    ):
        raise CiboCapitalManagementError(
            "P3 source-truth producer identity drift"
        )
    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "P3 requires canonical Phase22 receipt"
        )
    if source_truth_control.integrated_git_sha != scope.integrated_git_sha:
        raise CiboCapitalManagementError("P3 source-truth HEAD drift")
    if scope.source_truth_control_sha256 != source_truth_control.fingerprint():
        raise CiboCapitalManagementError(
            "P3 source-truth fingerprint drift"
        )
    if (
        source_truth_control.policy_identity_sha256
        != phase22_receipt.candidate_parameter_sha256
        or source_truth_control.phase22_qualification_artifact_sha256
        != phase22_receipt.qualification_artifact_sha256
    ):
        raise CiboCapitalManagementError(
            "P3 source-truth/Phase22 lineage drift"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "P3 observed_at must be timezone-aware"
        )
    if observed_at <= phase22_receipt.qualified_at or observed_at <= scope.frozen_at:
        raise CiboCapitalManagementError(
            "P3 must be observed after Phase22 and CI-scope freeze"
        )

    required = {
        (item.workflow_name, item.workflow_path): item
        for item in scope.requirements
    }
    if (
        not isinstance(results, tuple)
        or any(not isinstance(item, FinalCiCheckResult) for item in results)
    ):
        raise CiboCapitalManagementError(
            "P3 results must be canonical CI checks"
        )
    seen: dict[tuple[str, str], FinalCiCheckResult] = {}
    for result in results:
        key = (result.workflow_name, result.workflow_path)
        if key in seen:
            raise CiboCapitalManagementError("P3 duplicate CI result")
        if key not in required:
            raise CiboCapitalManagementError(
                "P3 unexpected workflow result"
            )
        if result.head_sha != scope.integrated_git_sha:
            raise CiboCapitalManagementError("P3 workflow HEAD drift")
        if result.observed_at < scope.frozen_at:
            raise CiboCapitalManagementError(
                "P3 workflow result predates CI-scope freeze"
            )
        seen[key] = result

    missing = tuple(key for key in required if key not in seen)
    if missing:
        raise CiboCapitalManagementError(
            "P3 required workflow results missing"
        )

    payload = {
        "schema": _SCHEMA,
        "evidence_binding_id": "P3_CERTIFICATION_CI_CLEAR",
        "evidence_kind": _EVIDENCE_KIND,
        "producer_gate_id": "CIBO_FINAL_CERTIFICATION_CI_CLEAR_V1",
        "integrated_git_sha": scope.integrated_git_sha,
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
        "ci_scope_sha256": scope.fingerprint(),
        "source_truth_control_sha256": source_truth_control.fingerprint(),
        "required_check_count": len(scope.requirements),
        "successful_check_count": len(results),
        "checks": [
            {
                "workflow_name": item.workflow_name,
                "workflow_path": item.workflow_path,
                "run_id": item.run_id,
                "head_sha": item.head_sha,
                "status": item.status,
                "conclusion": item.conclusion,
                "observed_at": item.observed_at.isoformat(),
            }
            for item in results
        ],
    }
    artifact_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return bind_final_exam_control_artifact(
        receipt_id="P3_CERTIFICATION_CI_CLEAR",
        evidence_kind=_EVIDENCE_KIND,
        source_artifact_json=artifact_json,
    )
