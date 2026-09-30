"""Canonical cross-boundary evidence receipt for CIBO certification gates.

This is a reusable trust primitive for Architect-A Final Integrated Exam and
Architect-B USD60 pre-exam readiness. It validates canonical artifact content,
recomputes its digest, binds evidence to one integrated Git HEAD and never
grants productive authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SCHEMA = "qore.cibo.crossboundary-evidence-receipt.v1"


@dataclass(frozen=True, slots=True)
class CiboCrossBoundaryEvidenceReceipt:
    receipt_id: str
    evidence_kind: str
    producer_gate_id: str
    integrated_git_sha: str
    policy_identity_sha256: str
    artifact_sha256: str
    artifact_json: str
    observed_at: datetime
    passed: bool
    holdout_outcomes_inspected: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("receipt_id", "evidence_kind", "producer_gate_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise CiboCapitalManagementError(
                    f"cross-boundary receipt {name} is required"
                )
        if _SHA1_RE.fullmatch(self.integrated_git_sha) is None:
            raise CiboCapitalManagementError(
                "cross-boundary receipt integrated Git SHA must be lowercase 40-hex"
            )
        if _SHA256_RE.fullmatch(self.policy_identity_sha256) is None:
            raise CiboCapitalManagementError(
                "cross-boundary receipt policy identity must be canonical sha256"
            )
        if _SHA256_RE.fullmatch(self.artifact_sha256) is None:
            raise CiboCapitalManagementError(
                "cross-boundary receipt artifact digest must be canonical sha256"
            )
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "cross-boundary receipt observed_at must be timezone-aware"
            )
        for name in (
            "passed",
            "holdout_outcomes_inspected",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"cross-boundary receipt {name} must be bool"
                )
        if self.holdout_outcomes_inspected:
            raise CiboCapitalManagementError(
                "cross-boundary pre-certification receipt cannot inspect holdout outcomes"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "cross-boundary evidence receipt grants no productive authority"
            )

        try:
            artifact = json.loads(self.artifact_json)
        except json.JSONDecodeError as error:
            raise CiboCapitalManagementError(
                "cross-boundary receipt artifact is invalid JSON"
            ) from error
        if not isinstance(artifact, dict):
            raise CiboCapitalManagementError(
                "cross-boundary receipt artifact must be object"
            )

        canonical = json.dumps(
            artifact,
            indent=2,
            sort_keys=True,
        ) + "\n"
        if canonical != self.artifact_json:
            raise CiboCapitalManagementError(
                "cross-boundary receipt artifact must use canonical JSON"
            )
        digest = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if digest != self.artifact_sha256:
            raise CiboCapitalManagementError(
                "cross-boundary receipt artifact digest mismatch"
            )

        expected = {
            "schema": _SCHEMA,
            "receipt_id": self.receipt_id,
            "evidence_kind": self.evidence_kind,
            "producer_gate_id": self.producer_gate_id,
            "integrated_git_sha": self.integrated_git_sha,
            "policy_identity_sha256": self.policy_identity_sha256,
            "observed_at": self.observed_at.isoformat(),
            "status": "PASS",
            "holdout_outcomes_inspected": False,
            "productive_authority": False,
        }
        for key, value in expected.items():
            if artifact.get(key) != value:
                raise CiboCapitalManagementError(
                    f"cross-boundary receipt artifact field mismatch: {key}"
                )
        if artifact.get("failures") != []:
            raise CiboCapitalManagementError(
                "cross-boundary receipt artifact contains failures"
            )
        if self.passed is not True:
            raise CiboCapitalManagementError(
                "cross-boundary receipt requires derived PASS"
            )

    def fingerprint(self) -> str:
        payload = {
            "receipt_id": self.receipt_id,
            "evidence_kind": self.evidence_kind,
            "producer_gate_id": self.producer_gate_id,
            "integrated_git_sha": self.integrated_git_sha,
            "policy_identity_sha256": self.policy_identity_sha256,
            "artifact_sha256": self.artifact_sha256,
            "observed_at": self.observed_at.isoformat(),
            "passed": self.passed,
            "holdout_outcomes_inspected": self.holdout_outcomes_inspected,
            "productive_authority": self.productive_authority,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_cross_boundary_evidence_receipt(
    *,
    receipt_id: str,
    evidence_kind: str,
    producer_gate_id: str,
    integrated_git_sha: str,
    policy_identity_sha256: str,
    observed_at: datetime,
) -> CiboCrossBoundaryEvidenceReceipt:
    artifact = {
        "schema": _SCHEMA,
        "receipt_id": receipt_id,
        "evidence_kind": evidence_kind,
        "producer_gate_id": producer_gate_id,
        "integrated_git_sha": integrated_git_sha,
        "policy_identity_sha256": policy_identity_sha256,
        "observed_at": observed_at.isoformat(),
        "status": "PASS",
        "failures": [],
        "holdout_outcomes_inspected": False,
        "productive_authority": False,
    }
    artifact_json = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    artifact_sha256 = (
        "sha256:" + hashlib.sha256(artifact_json.encode("utf-8")).hexdigest()
    )
    return CiboCrossBoundaryEvidenceReceipt(
        receipt_id=receipt_id,
        evidence_kind=evidence_kind,
        producer_gate_id=producer_gate_id,
        integrated_git_sha=integrated_git_sha,
        policy_identity_sha256=policy_identity_sha256,
        artifact_sha256=artifact_sha256,
        artifact_json=artifact_json,
        observed_at=observed_at,
        passed=True,
        holdout_outcomes_inspected=False,
        productive_authority=False,
    )


def require_cross_boundary_receipts(
    *,
    receipts: tuple[CiboCrossBoundaryEvidenceReceipt, ...],
    required_receipt_ids: tuple[str, ...],
    integrated_git_sha: str,
    policy_identity_sha256: str,
) -> dict[str, CiboCrossBoundaryEvidenceReceipt]:
    if _SHA1_RE.fullmatch(integrated_git_sha) is None:
        raise CiboCapitalManagementError(
            "cross-boundary required integrated Git SHA invalid"
        )
    if _SHA256_RE.fullmatch(policy_identity_sha256) is None:
        raise CiboCapitalManagementError(
            "cross-boundary required policy identity invalid"
        )
    if not isinstance(receipts, tuple) or any(
        not isinstance(item, CiboCrossBoundaryEvidenceReceipt)
        for item in receipts
    ):
        raise CiboCapitalManagementError(
            "cross-boundary receipts must be canonical tuple"
        )
    if (
        not isinstance(required_receipt_ids, tuple)
        or not required_receipt_ids
        or len(required_receipt_ids) != len(set(required_receipt_ids))
        or any(not isinstance(item, str) or not item for item in required_receipt_ids)
    ):
        raise CiboCapitalManagementError(
            "cross-boundary required receipt ids invalid"
        )

    by_id: dict[str, CiboCrossBoundaryEvidenceReceipt] = {}
    for receipt in receipts:
        if receipt.receipt_id in by_id:
            raise CiboCapitalManagementError(
                "cross-boundary duplicate receipt id"
            )
        if receipt.integrated_git_sha != integrated_git_sha:
            raise CiboCapitalManagementError(
                "cross-boundary receipt integrated-head drift"
            )
        if receipt.policy_identity_sha256 != policy_identity_sha256:
            raise CiboCapitalManagementError(
                "cross-boundary receipt policy-identity drift"
            )
        by_id[receipt.receipt_id] = receipt

    missing = tuple(item for item in required_receipt_ids if item not in by_id)
    if missing:
        raise CiboCapitalManagementError(
            "cross-boundary required receipts missing: " + ",".join(missing)
        )
    extras = tuple(sorted(set(by_id) - set(required_receipt_ids)))
    if extras:
        raise CiboCapitalManagementError(
            "cross-boundary unexpected receipt ids: " + ",".join(extras)
        )
    return by_id
