from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.shared_b_provenance_manifest import (
    SharedBEvidenceKind,
    SharedBEvidencePointer,
    build_shared_b_provenance_manifest,
)

BRANCH="agent/shared-b-global-world-perception-001"


def _pointer(
    evidence_id: str,
    artifact_id: int,
    **overrides: object,
) -> SharedBEvidencePointer:
    values:dict[str,object]={
        "evidence_id":evidence_id,
        "capability_scope":"B-03",
        "evidence_kind":SharedBEvidenceKind.REPLAY_EVIDENCE,
        "workflow_run_id":36746337433,
        "artifact_id":artifact_id,
        "head_sha":"80c83baf2538195e2c8ece17e286e80603aae571",
        "head_branch":BRANCH,
        "artifact_digest_sha256":"a"*64,
        "artifact_name":f"artifact-{artifact_id}",
        "source_hash_verified_inside_artifact":True,
        "provider_free_replay_supported":True,
    }
    values.update(overrides)
    return SharedBEvidencePointer(**values)  # type: ignore[arg-type]


def test_provenance_manifest_is_deterministic_and_explicitly_partial() -> None:
    payload=build_shared_b_provenance_manifest(
        (
            _pointer("E2",2,capability_scope="B-05"),
            _pointer("E1",1),
        ),
        expected_branch=BRANCH,
        coverage_complete=False,
        open_coverage_reasons=("B-04 still running","B-07/B-08 unresolved"),
    )
    assert payload["evidence_pointer_count"] == 2
    assert payload["coverage_complete"] is False
    assert payload["fresh_holdout_opened"] is False
    assert payload["broker_mutation"] is False
    assert payload["productive_authority"] is False
    assert len(payload["manifest_fingerprint_sha256"]) == 64
    assert [item["evidence_id"] for item in payload["pointers"]] == ["E1","E2"]


def test_provenance_manifest_rejects_duplicate_artifact_and_evidence_ids() -> None:
    with pytest.raises(ValueError,match="duplicate artifact_id"):
        build_shared_b_provenance_manifest(
            (_pointer("E1",1),_pointer("E2",1)),
            expected_branch=BRANCH,
            coverage_complete=False,
            open_coverage_reasons=("open",),
        )
    with pytest.raises(ValueError,match="duplicate evidence_id"):
        build_shared_b_provenance_manifest(
            (_pointer("E1",1),_pointer("E1",2)),
            expected_branch=BRANCH,
            coverage_complete=False,
            open_coverage_reasons=("open",),
        )


def test_provenance_manifest_rejects_branch_escape() -> None:
    with pytest.raises(ValueError,match="escaped B branch"):
        build_shared_b_provenance_manifest(
            (_pointer("E1",1,head_branch="other"),),
            expected_branch=BRANCH,
            coverage_complete=False,
            open_coverage_reasons=("open",),
        )


def test_incomplete_coverage_requires_explicit_reasons() -> None:
    with pytest.raises(ValueError,match="requires blockers"):
        build_shared_b_provenance_manifest(
            (_pointer("E1",1),),
            expected_branch=BRANCH,
            coverage_complete=False,
            open_coverage_reasons=(),
        )


def test_complete_coverage_cannot_hide_blockers() -> None:
    with pytest.raises(ValueError,match="cannot retain blockers"):
        build_shared_b_provenance_manifest(
            (_pointer("E1",1),),
            expected_branch=BRANCH,
            coverage_complete=True,
            open_coverage_reasons=("still open",),
        )


def test_evidence_pointer_forbids_holdout_mutation_and_productive_authority() -> None:
    for field in (
        "fresh_holdout_opened",
        "broker_mutation",
        "productive_authority",
    ):
        with pytest.raises(ValueError,match="forbidden authority"):
            _pointer("E1",1,**{field:True})
