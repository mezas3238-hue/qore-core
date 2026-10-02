"""Receipt binding for post-Phase22 CIBO Final Integrated Exam controls.

Every final-exam control is bound to one integrated Git HEAD, one frozen policy
identity and the exact Phase22 qualification artifact. This module never grants
runtime, merge, execution or real-capital authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STAGE = "POST_PHASE22"


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _parse_canonical(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "final-exam control artifact is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "final-exam control artifact must be object"
        )
    if _canonical_json(payload) != value:
        raise CiboCapitalManagementError(
            "final-exam control artifact must use canonical JSON"
        )
    return payload


@dataclass(frozen=True, slots=True)
class CiboFinalExamControlReceipt:
    receipt_id: str
    evidence_kind: str
    producer_gate_id: str
    integrated_git_sha: str
    policy_identity_sha256: str
    phase22_qualification_artifact_sha256: str
    source_artifact_schema: str
    source_artifact_sha256: str
    source_artifact_json: str
    observed_at: datetime
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "receipt_id",
            "evidence_kind",
            "producer_gate_id",
            "source_artifact_schema",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise CiboCapitalManagementError(
                    f"final-exam control receipt {name} is required"
                )
        if _SHA1_RE.fullmatch(self.integrated_git_sha) is None:
            raise CiboCapitalManagementError(
                "final-exam control integrated Git SHA invalid"
            )
        for name in (
            "policy_identity_sha256",
            "phase22_qualification_artifact_sha256",
            "source_artifact_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"final-exam control {name} must be canonical sha256"
                )
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "final-exam control observed_at must be timezone-aware"
            )
        if type(self.productive_authority) is not bool or self.productive_authority:
            raise CiboCapitalManagementError(
                "final-exam control grants no productive authority"
            )

        artifact = _parse_canonical(self.source_artifact_json)
        digest = (
            "sha256:"
            + hashlib.sha256(self.source_artifact_json.encode("utf-8")).hexdigest()
        )
        if digest != self.source_artifact_sha256:
            raise CiboCapitalManagementError(
                "final-exam control source artifact digest mismatch"
            )
        expected = {
            "schema": self.source_artifact_schema,
            "evidence_binding_id": self.receipt_id,
            "evidence_kind": self.evidence_kind,
            "producer_gate_id": self.producer_gate_id,
            "integrated_git_sha": self.integrated_git_sha,
            "policy_identity_sha256": self.policy_identity_sha256,
            "phase22_qualification_artifact_sha256": (
                self.phase22_qualification_artifact_sha256
            ),
            "certification_stage": _STAGE,
            "observed_at": self.observed_at.isoformat(),
            "status": "PASS",
            "productive_authority": False,
            "synthetic_evidence_used": False,
            "holdout_mining_used": False,
            "outcome_aware_refit": False,
            "operational_authority_claimed": False,
        }
        for key, value in expected.items():
            if artifact.get(key) != value:
                raise CiboCapitalManagementError(
                    f"final-exam control artifact field mismatch: {key}"
                )
        if artifact.get("failures") != []:
            raise CiboCapitalManagementError(
                "final-exam control artifact contains failures"
            )

    def fingerprint(self) -> str:
        payload = {
            "receipt_id": self.receipt_id,
            "evidence_kind": self.evidence_kind,
            "producer_gate_id": self.producer_gate_id,
            "integrated_git_sha": self.integrated_git_sha,
            "policy_identity_sha256": self.policy_identity_sha256,
            "phase22_qualification_artifact_sha256": (
                self.phase22_qualification_artifact_sha256
            ),
            "source_artifact_schema": self.source_artifact_schema,
            "source_artifact_sha256": self.source_artifact_sha256,
            "observed_at": self.observed_at.isoformat(),
            "productive_authority": self.productive_authority,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def bind_final_exam_control_artifact(
    *,
    receipt_id: str,
    evidence_kind: str,
    source_artifact_json: str,
) -> CiboFinalExamControlReceipt:
    artifact = _parse_canonical(source_artifact_json)
    required = (
        "schema",
        "evidence_binding_id",
        "evidence_kind",
        "producer_gate_id",
        "integrated_git_sha",
        "policy_identity_sha256",
        "phase22_qualification_artifact_sha256",
        "certification_stage",
        "observed_at",
        "status",
        "failures",
        "productive_authority",
        "synthetic_evidence_used",
        "holdout_mining_used",
        "outcome_aware_refit",
        "operational_authority_claimed",
    )
    missing = tuple(key for key in required if key not in artifact)
    if missing:
        raise CiboCapitalManagementError(
            "final-exam control artifact missing fields: " + ",".join(missing)
        )
    if artifact["evidence_binding_id"] != receipt_id:
        raise CiboCapitalManagementError(
            "final-exam control binding identity drift"
        )
    if artifact["evidence_kind"] != evidence_kind:
        raise CiboCapitalManagementError(
            "final-exam control evidence kind drift"
        )
    if artifact["certification_stage"] != _STAGE:
        raise CiboCapitalManagementError(
            "final-exam control must be POST_PHASE22"
        )
    if artifact["status"] != "PASS" or artifact["failures"] != []:
        raise CiboCapitalManagementError(
            "final-exam control source artifact is not PASS"
        )
    for key in (
        "productive_authority",
        "synthetic_evidence_used",
        "holdout_mining_used",
        "outcome_aware_refit",
        "operational_authority_claimed",
    ):
        if artifact[key] is not False:
            raise CiboCapitalManagementError(
                f"final-exam control governance contamination: {key}"
            )
    try:
        observed_at = datetime.fromisoformat(str(artifact["observed_at"]))
    except ValueError as error:
        raise CiboCapitalManagementError(
            "final-exam control observed_at invalid"
        ) from error

    digest = (
        "sha256:"
        + hashlib.sha256(source_artifact_json.encode("utf-8")).hexdigest()
    )
    return CiboFinalExamControlReceipt(
        receipt_id=receipt_id,
        evidence_kind=evidence_kind,
        producer_gate_id=str(artifact["producer_gate_id"]),
        integrated_git_sha=str(artifact["integrated_git_sha"]),
        policy_identity_sha256=str(artifact["policy_identity_sha256"]),
        phase22_qualification_artifact_sha256=str(
            artifact["phase22_qualification_artifact_sha256"]
        ),
        source_artifact_schema=str(artifact["schema"]),
        source_artifact_sha256=digest,
        source_artifact_json=source_artifact_json,
        observed_at=observed_at,
        productive_authority=False,
    )


def require_final_exam_control_receipts(
    *,
    receipts: tuple[CiboFinalExamControlReceipt, ...],
    required_receipt_ids: tuple[str, ...],
    integrated_git_sha: str,
    policy_identity_sha256: str,
    phase22_qualification_artifact_sha256: str,
) -> dict[str, CiboFinalExamControlReceipt]:
    if _SHA1_RE.fullmatch(integrated_git_sha) is None:
        raise CiboCapitalManagementError(
            "final-exam control required integrated Git SHA invalid"
        )
    for name, value in (
        ("policy_identity_sha256", policy_identity_sha256),
        (
            "phase22_qualification_artifact_sha256",
            phase22_qualification_artifact_sha256,
        ),
    ):
        if _SHA256_RE.fullmatch(value) is None:
            raise CiboCapitalManagementError(
                f"final-exam control required {name} invalid"
            )
    if not isinstance(receipts, tuple) or any(
        not isinstance(item, CiboFinalExamControlReceipt)
        for item in receipts
    ):
        raise CiboCapitalManagementError(
            "final-exam control receipts must be canonical tuple"
        )
    if (
        not isinstance(required_receipt_ids, tuple)
        or not required_receipt_ids
        or len(required_receipt_ids) != len(set(required_receipt_ids))
        or any(not isinstance(item, str) or not item for item in required_receipt_ids)
    ):
        raise CiboCapitalManagementError(
            "final-exam control required receipt ids invalid"
        )
    by_id: dict[str, CiboFinalExamControlReceipt] = {}
    for receipt in receipts:
        if receipt.receipt_id in by_id:
            raise CiboCapitalManagementError(
                "final-exam control duplicate receipt id"
            )
        if receipt.integrated_git_sha != integrated_git_sha:
            raise CiboCapitalManagementError(
                "final-exam control integrated-head drift"
            )
        if receipt.policy_identity_sha256 != policy_identity_sha256:
            raise CiboCapitalManagementError(
                "final-exam control policy-identity drift"
            )
        if (
            receipt.phase22_qualification_artifact_sha256
            != phase22_qualification_artifact_sha256
        ):
            raise CiboCapitalManagementError(
                "final-exam control Phase22-artifact drift"
            )
        by_id[receipt.receipt_id] = receipt
    missing = tuple(item for item in required_receipt_ids if item not in by_id)
    if missing:
        raise CiboCapitalManagementError(
            "final-exam control receipts missing: " + ",".join(missing)
        )
    extras = tuple(sorted(set(by_id) - set(required_receipt_ids)))
    if extras:
        raise CiboCapitalManagementError(
            "final-exam control unexpected receipt ids: " + ",".join(extras)
        )
    return by_id
