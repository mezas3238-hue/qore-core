from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyError,
    DurablePhase20ForwardPolicyStore,
)


def _canonical_record(
    *,
    evidence_sha256: str,
    disposition: str = "NO_ELIGIBLE_ALLOCATION",
    selected: tuple[str, ...] = (),
) -> str:
    allocation = (
        None
        if not selected
        else {
            "selected_signal_fingerprints": list(selected),
        }
    )
    return json.dumps(
        {
            "evidence_sha256": evidence_sha256,
            "allocator_decision": {
                "disposition": disposition,
                "allocation": allocation,
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _write_book(
    path: Path,
    *,
    evidence_sha256: str,
    canonical_record_json: str,
    policy_record_sha256: str | None = None,
    disposition: str = "NO_ELIGIBLE_ALLOCATION",
    selected: tuple[str, ...] = (),
) -> None:
    digest = (
        policy_record_sha256
        if policy_record_sha256 is not None
        else "sha256:"
        + hashlib.sha256(canonical_record_json.encode("utf-8")).hexdigest()
    )
    payload = {
        "schema": "CIBO_PHASE20D_FORWARD_POLICY_BOOK_V1",
        "generation": 1,
        "decisions": [
            {
                "evidence_sha256": evidence_sha256,
                "policy_record_sha256": digest,
                "allocator_disposition": disposition,
                "selected_signal_fingerprints": list(selected),
                "canonical_record_json": canonical_record_json,
            }
        ],
    }
    path.write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )


def test_policy_store_load_verifies_canonical_record_binding(
    tmp_path: Path,
) -> None:
    evidence_sha = "sha256:" + ("1" * 64)
    record = _canonical_record(evidence_sha256=evidence_sha)
    path = tmp_path / "policy.json"
    _write_book(
        path,
        evidence_sha256=evidence_sha,
        canonical_record_json=record,
    )

    book = DurablePhase20ForwardPolicyStore(path).load()

    assert book.generation == 1
    assert book.decisions[0].evidence_sha256 == evidence_sha


def test_policy_store_rejects_tampered_canonical_record(
    tmp_path: Path,
) -> None:
    evidence_sha = "sha256:" + ("1" * 64)
    original = _canonical_record(evidence_sha256=evidence_sha)
    digest = "sha256:" + hashlib.sha256(
        original.encode("utf-8")
    ).hexdigest()
    tampered = _canonical_record(
        evidence_sha256=evidence_sha,
        disposition="ALLOCATE",
        selected=("signal-1",),
    )
    path = tmp_path / "policy.json"
    _write_book(
        path,
        evidence_sha256=evidence_sha,
        canonical_record_json=tampered,
        policy_record_sha256=digest,
        disposition="ALLOCATE",
        selected=("signal-1",),
    )

    with pytest.raises(
        DurablePhase20ForwardPolicyError,
        match="canonical record SHA mismatch",
    ):
        DurablePhase20ForwardPolicyStore(path).load()


def test_policy_store_rejects_evidence_binding_drift(
    tmp_path: Path,
) -> None:
    stored_sha = "sha256:" + ("1" * 64)
    record_sha = "sha256:" + ("2" * 64)
    record = _canonical_record(evidence_sha256=record_sha)
    path = tmp_path / "policy.json"
    _write_book(
        path,
        evidence_sha256=stored_sha,
        canonical_record_json=record,
    )

    with pytest.raises(
        DurablePhase20ForwardPolicyError,
        match="canonical evidence binding mismatch",
    ):
        DurablePhase20ForwardPolicyStore(path).load()


def test_policy_store_rejects_selection_binding_drift(
    tmp_path: Path,
) -> None:
    evidence_sha = "sha256:" + ("3" * 64)
    record = _canonical_record(
        evidence_sha256=evidence_sha,
        disposition="ALLOCATE",
        selected=("signal-1",),
    )
    path = tmp_path / "policy.json"
    _write_book(
        path,
        evidence_sha256=evidence_sha,
        canonical_record_json=record,
        disposition="ALLOCATE",
        selected=("signal-2",),
    )

    with pytest.raises(
        DurablePhase20ForwardPolicyError,
        match="selected-signal binding mismatch",
    ):
        DurablePhase20ForwardPolicyStore(path).load()
