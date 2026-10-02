"""Build P1 Source-of-Truth control for the Final Integrated CIBO Exam."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
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

_SCHEMA = "qore.cibo.final-source-truth-manifest.v2"
_ARTIFACT_SCHEMA = "qore.cibo.final-source-truth-control.v2"
_EVIDENCE_KIND = "FINAL_INTEGRATED_EXAM_CONTROL"
_REQUIRED_OPEN_IDS = (
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
)
_REQUIRED_FILE_ROLES = (
    "master_ledger",
    "source_truth_reconciliation",
    "final_integrated_exam_protocol",
    "world_cup_exam_protocol",
    "certification_sequence",
    "architect_a_science",
    "architect_b_phase22",
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class FinalSourceTruthManifest:
    schema: str
    integrated_git_sha: str
    architect_a_head_sha: str
    architect_b_head_sha: str
    phase22_handoff_manifest_sha256: str
    mandatory_count: int
    terminal_count: int
    open_ids: tuple[str, ...]
    file_sha256s: tuple[tuple[str, str], ...]
    unaccounted_files: tuple[str, ...]
    certification_critical_external_blockers: tuple[str, ...]
    stale_current_state_claims: tuple[str, ...]
    productive_authority: bool = False
    certification_claimed: bool = False

    def __post_init__(self) -> None:
        if self.schema != _SCHEMA:
            raise CiboCapitalManagementError(
                "final source-truth manifest schema drift"
            )
        for name in (
            "integrated_git_sha",
            "architect_a_head_sha",
            "architect_b_head_sha",
        ):
            if _SHA1_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"final source-truth {name} invalid"
                )
        if _SHA256_RE.fullmatch(self.phase22_handoff_manifest_sha256) is None:
            raise CiboCapitalManagementError(
                "final source-truth Phase22 manifest digest invalid"
            )
        if self.mandatory_count != 64 or self.terminal_count != 62:
            raise CiboCapitalManagementError(
                "final source-truth requires exact 64/62 pre-exam topology"
            )
        if self.open_ids != _REQUIRED_OPEN_IDS:
            raise CiboCapitalManagementError(
                "final source-truth requires exact two open exam ids"
            )
        roles = tuple(role for role, _digest in self.file_sha256s)
        if roles != _REQUIRED_FILE_ROLES:
            raise CiboCapitalManagementError(
                "final source-truth file-role coverage drift"
            )
        for role, digest in self.file_sha256s:
            if _SHA256_RE.fullmatch(digest) is None:
                raise CiboCapitalManagementError(
                    f"final source-truth file digest invalid: {role}"
                )
        for name in (
            "unaccounted_files",
            "certification_critical_external_blockers",
            "stale_current_state_claims",
        ):
            values = getattr(self, name)
            if (
                not isinstance(values, tuple)
                or any(not isinstance(item, str) or not item for item in values)
                or len(values) != len(set(values))
            ):
                raise CiboCapitalManagementError(
                    f"final source-truth {name} invalid"
                )
        if self.productive_authority or self.certification_claimed:
            raise CiboCapitalManagementError(
                "final source-truth manifest cannot grant authority"
            )

    def fingerprint(self) -> str:
        payload = {
            "schema": self.schema,
            "integrated_git_sha": self.integrated_git_sha,
            "architect_a_head_sha": self.architect_a_head_sha,
            "architect_b_head_sha": self.architect_b_head_sha,
            "phase22_handoff_manifest_sha256": (
                self.phase22_handoff_manifest_sha256
            ),
            "mandatory_count": self.mandatory_count,
            "terminal_count": self.terminal_count,
            "open_ids": list(self.open_ids),
            "file_sha256s": [list(item) for item in self.file_sha256s],
            "unaccounted_files": list(self.unaccounted_files),
            "certification_critical_external_blockers": list(
                self.certification_critical_external_blockers
            ),
            "stale_current_state_claims": list(
                self.stale_current_state_claims
            ),
            "productive_authority": self.productive_authority,
            "certification_claimed": self.certification_claimed,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_final_source_truth_control(
    *,
    manifest: FinalSourceTruthManifest,
    phase22_receipt: Phase22QualificationReceipt,
    observed_at: datetime,
) -> CiboFinalExamControlReceipt:
    if not isinstance(manifest, FinalSourceTruthManifest):
        raise CiboCapitalManagementError(
            "P1 source-of-truth requires canonical manifest"
        )
    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "P1 source-of-truth requires canonical Phase22 receipt"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "P1 source-of-truth observed_at must be timezone-aware"
        )
    if observed_at <= phase22_receipt.qualified_at:
        raise CiboCapitalManagementError(
            "P1 source-of-truth must be post-Phase22 qualification"
        )
    if manifest.unaccounted_files:
        raise CiboCapitalManagementError(
            "P1 source-of-truth has unaccounted files"
        )
    if manifest.certification_critical_external_blockers:
        raise CiboCapitalManagementError(
            "P1 source-of-truth has certification-critical external blockers"
        )
    if manifest.stale_current_state_claims:
        raise CiboCapitalManagementError(
            "P1 source-of-truth has stale current-state claims"
        )

    payload = {
        "schema": _ARTIFACT_SCHEMA,
        "evidence_binding_id": "P1_SOURCE_OF_TRUTH_RECONCILED",
        "evidence_kind": _EVIDENCE_KIND,
        "producer_gate_id": "CIBO_FINAL_SOURCE_OF_TRUTH_CONTROL_V2",
        "integrated_git_sha": manifest.integrated_git_sha,
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
        "source_truth_manifest_sha256": manifest.fingerprint(),
        "architect_a_head_sha": manifest.architect_a_head_sha,
        "architect_b_head_sha": manifest.architect_b_head_sha,
        "phase22_handoff_manifest_sha256": (
            manifest.phase22_handoff_manifest_sha256
        ),
        "mandatory_count": manifest.mandatory_count,
        "terminal_count": manifest.terminal_count,
        "open_ids": list(manifest.open_ids),
        "file_sha256s": {role: digest for role, digest in manifest.file_sha256s},
        "unaccounted_files": [],
        "certification_critical_external_blockers": [],
        "stale_current_state_claims": [],
    }
    artifact_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return bind_final_exam_control_artifact(
        receipt_id="P1_SOURCE_OF_TRUTH_RECONCILED",
        evidence_kind=_EVIDENCE_KIND,
        source_artifact_json=artifact_json,
    )
