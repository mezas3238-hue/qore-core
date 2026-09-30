"""Canonical cross-boundary evidence binding for CIBO certification gates.

The binder cannot create evidence from booleans. It accepts only an existing
canonical PASS artifact produced by an upstream gate, recomputes its digest and
binds that artifact to one integrated Git HEAD and policy identity.

Research/certification governance only. No productive authority is granted.
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


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _parse_canonical_artifact(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "cross-boundary source artifact is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "cross-boundary source artifact must be object"
        )
    if _canonical_json(payload) != value:
        raise CiboCapitalManagementError(
            "cross-boundary source artifact must use canonical JSON"
        )
    return payload


@dataclass(frozen=True, slots=True)
class CiboCrossBoundaryEvidenceReceipt:
    receipt_id: str
    evidence_kind: str
    producer_gate_id: str
    integrated_git_sha: str
    policy_identity_sha256: str
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
        if _SHA256_RE.fullmatch(self.source_artifact_sha256) is None:
            raise CiboCapitalManagementError(
                "cross-boundary source artifact digest must be canonical sha256"
            )
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "cross-boundary receipt observed_at must be timezone-aware"
            )
        if type(self.productive_authority) is not bool:
            raise CiboCapitalManagementError(
                "cross-boundary receipt productive_authority must be bool"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "cross-boundary evidence receipt grants no productive authority"
            )

        artifact = _parse_canonical_artifact(self.source_artifact_json)
        digest = (
            "sha256:"
            + hashlib.sha256(self.source_artifact_json.encode("utf-8")).hexdigest()
        )
        if digest != self.source_artifact_sha256:
            raise CiboCapitalManagementError(
                "cross-boundary source artifact digest mismatch"
            )

        expected = {
            "schema": self.source_artifact_schema,
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
                    f"cross-boundary source artifact field mismatch: {key}"
                )
        if artifact.get("failures") != []:
            raise CiboCapitalManagementError(
                "cross-boundary source artifact contains failures"
            )

    def fingerprint(self) -> str:
        payload = {
            "receipt_id": self.receipt_id,
            "evidence_kind": self.evidence_kind,
            "producer_gate_id": self.producer_gate_id,
            "integrated_git_sha": self.integrated_git_sha,
            "policy_identity_sha256": self.policy_identity_sha256,
            "source_artifact_schema": self.source_artifact_schema,
            "source_artifact_sha256": self.source_artifact_sha256,
            "observed_at": self.observed_at.isoformat(),
            "productive_authority": self.productive_authority,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def bind_cross_boundary_pass_artifact(
    *,
    receipt_id: str,
    evidence_kind: str,
    source_artifact_json: str,
) -> CiboCrossBoundaryEvidenceReceipt:
    """Bind one already-produced canonical PASS artifact.

    PASS, HEAD, policy identity and timestamps are derived from the artifact;
    callers do not provide a pass boolean.
    """

    artifact = _parse_canonical_artifact(source_artifact_json)
    required = (
        "schema",
        "producer_gate_id",
        "integrated_git_sha",
        "policy_identity_sha256",
        "observed_at",
        "status",
        "failures",
        "holdout_outcomes_inspected",
        "productive_authority",
    )
    missing = tuple(key for key in required if key not in artifact)
    if missing:
        raise CiboCapitalManagementError(
            "cross-boundary source artifact missing fields: " + ",".join(missing)
        )
    if artifact["status"] != "PASS" or artifact["failures"] != []:
        raise CiboCapitalManagementError(
            "cross-boundary source artifact is not PASS"
        )
    if artifact["holdout_outcomes_inspected"] is not False:
        raise CiboCapitalManagementError(
            "cross-boundary source artifact inspected holdout outcomes"
        )
    if artifact["productive_authority"] is not False:
        raise CiboCapitalManagementError(
            "cross-boundary source artifact claims productive authority"
        )
    try:
        observed_at = datetime.fromisoformat(str(artifact["observed_at"]))
    except ValueError as error:
        raise CiboCapitalManagementError(
            "cross-boundary source artifact observed_at invalid"
        ) from error

    digest = (
        "sha256:"
        + hashlib.sha256(source_artifact_json.encode("utf-8")).hexdigest()
    )
    return CiboCrossBoundaryEvidenceReceipt(
        receipt_id=receipt_id,
        evidence_kind=evidence_kind,
        producer_gate_id=str(artifact["producer_gate_id"]),
        integrated_git_sha=str(artifact["integrated_git_sha"]),
        policy_identity_sha256=str(artifact["policy_identity_sha256"]),
        source_artifact_schema=str(artifact["schema"]),
        source_artifact_sha256=digest,
        source_artifact_json=source_artifact_json,
        observed_at=observed_at,
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
