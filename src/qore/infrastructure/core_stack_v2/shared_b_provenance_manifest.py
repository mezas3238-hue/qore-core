"""Architect-B evidence provenance manifest.

The manifest binds B capability evidence to exact GitHub workflow runs,
artifacts, producer branches, producer SHAs and immutable artifact digests. It
never rewrites upstream B4/B5 evidence and does not itself prove scientific
correctness or convert partial work into complete work.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum


class SharedBEvidenceKind(StrEnum):
    RAW_PROVIDER_EVIDENCE = "RAW_PROVIDER_EVIDENCE"
    REPLAY_EVIDENCE = "REPLAY_EVIDENCE"
    GOVERNANCE_EVIDENCE = "GOVERNANCE_EVIDENCE"
    IDENTITY_EVIDENCE = "IDENTITY_EVIDENCE"
    ARCHITECTURE_EVIDENCE = "ARCHITECTURE_EVIDENCE"
    REAL_REPLICATION_EVIDENCE = "REAL_REPLICATION_EVIDENCE"


@dataclass(frozen=True, slots=True)
class SharedBEvidencePointer:
    evidence_id: str
    capability_scope: str
    evidence_kind: SharedBEvidenceKind
    workflow_run_id: int
    artifact_id: int
    head_sha: str
    head_branch: str
    artifact_digest_sha256: str
    artifact_name: str
    source_hash_verified_inside_artifact: bool
    provider_free_replay_supported: bool
    fresh_holdout_opened: bool = False
    broker_mutation: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "evidence_id",
            "capability_scope",
            "head_branch",
            "artifact_name",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in ("workflow_run_id", "artifact_id"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be positive int")
        if len(self.head_sha) != 40:
            raise ValueError("head_sha must be 40-char git SHA")
        int(self.head_sha, 16)
        if len(self.artifact_digest_sha256) != 64:
            raise ValueError("artifact digest must be SHA256")
        int(self.artifact_digest_sha256, 16)
        if (
            self.fresh_holdout_opened
            or self.broker_mutation
            or self.productive_authority
        ):
            raise ValueError(
                "B evidence pointer cannot carry forbidden authority/state"
            )


def build_shared_b_provenance_manifest(
    pointers: tuple[SharedBEvidencePointer, ...],
    *,
    expected_branch: str,
    coverage_complete: bool,
    open_coverage_reasons: tuple[str, ...],
    allowed_source_branches: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Build a deterministic total-provenance view without rewriting producers.

    expected_branch is the branch producing this B6 manifest. Evidence may
    originate from explicitly allowed B producer branches (for example B4/B5)
    because B-21 is required to consume their sealed evidence exactly as
    produced. Any unlisted producer branch fails closed.
    """

    if not expected_branch.strip():
        raise ValueError("expected_branch must be non-empty")
    if not pointers:
        raise ValueError("provenance manifest requires evidence pointers")

    allowed = (
        (expected_branch,)
        if allowed_source_branches is None
        else allowed_source_branches
    )
    if (
        not allowed
        or len(allowed) != len(set(allowed))
        or any(not isinstance(item, str) or not item.strip() for item in allowed)
    ):
        raise ValueError(
            "allowed_source_branches must be non-empty, unique and canonical"
        )

    evidence_ids = tuple(item.evidence_id for item in pointers)
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("duplicate evidence_id")
    artifact_ids = tuple(item.artifact_id for item in pointers)
    if len(artifact_ids) != len(set(artifact_ids)):
        raise ValueError("duplicate artifact_id")

    escaped = tuple(
        sorted(set(item.head_branch for item in pointers) - set(allowed))
    )
    if escaped:
        raise ValueError(
            "evidence escaped allowed B producer branches: "
            + ",".join(escaped)
        )

    if coverage_complete and open_coverage_reasons:
        raise ValueError("complete provenance coverage cannot retain blockers")
    if not coverage_complete and not open_coverage_reasons:
        raise ValueError("incomplete provenance coverage requires blockers")
    if (
        len(open_coverage_reasons) != len(set(open_coverage_reasons))
        or any(not item.strip() for item in open_coverage_reasons)
    ):
        raise ValueError(
            "open_coverage_reasons must be non-empty/unique when present"
        )

    ordered = tuple(
        sorted(
            pointers,
            key=lambda item: (
                item.capability_scope,
                item.evidence_id,
                item.head_branch,
            ),
        )
    )
    source_branches = tuple(
        sorted(set(item.head_branch for item in ordered))
    )
    source_branch_pointer_counts = {
        branch: sum(item.head_branch == branch for item in ordered)
        for branch in source_branches
    }

    payload: dict[str, object] = {
        "identity": "SHARED_B_GLOBAL_WORLD_PERCEPTION_PROVENANCE_MANIFEST_001",
        "head_branch": expected_branch,
        "allowed_source_branches": tuple(sorted(allowed)),
        "source_branches": source_branches,
        "source_branch_pointer_counts": source_branch_pointer_counts,
        "evidence_pointer_count": len(ordered),
        "capability_scopes": tuple(
            sorted(set(item.capability_scope for item in ordered))
        ),
        "source_hash_verified_pointer_count": sum(
            item.source_hash_verified_inside_artifact for item in ordered
        ),
        "provider_free_replay_pointer_count": sum(
            item.provider_free_replay_supported for item in ordered
        ),
        "coverage_complete": coverage_complete,
        "open_coverage_reasons": tuple(sorted(open_coverage_reasons)),
        "upstream_evidence_rewritten": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "pointers": [
            {
                "evidence_id": item.evidence_id,
                "capability_scope": item.capability_scope,
                "evidence_kind": item.evidence_kind.value,
                "workflow_run_id": item.workflow_run_id,
                "artifact_id": item.artifact_id,
                "head_sha": item.head_sha,
                "head_branch": item.head_branch,
                "artifact_digest_sha256": item.artifact_digest_sha256,
                "artifact_name": item.artifact_name,
                "source_hash_verified_inside_artifact": (
                    item.source_hash_verified_inside_artifact
                ),
                "provider_free_replay_supported": (
                    item.provider_free_replay_supported
                ),
            }
            for item in ordered
        ],
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    payload["manifest_fingerprint_sha256"] = hashlib.sha256(raw).hexdigest()
    return payload
