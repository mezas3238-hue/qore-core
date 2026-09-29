from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
    T12_SHADOW_POLICY_FROZEN_AT,
    T12_SHADOW_POLICY_ID,
    Phase20T12ToolEligibilityShadowDecision,
    t12_shadow_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_store import (
    DurableT12ShadowDecisionError,
    DurableT12ShadowDecisionStore,
)


def _fixture() -> tuple[
    Phase20T12ToolEligibilityShadowDecision,
    VersionedPhase20ForwardEvidenceBook,
    VersionedPhase20ForwardPolicyBook,
    datetime,
]:
    decision_at = T12_SHADOW_POLICY_FROZEN_AT + timedelta(minutes=1)
    evidence_sha = "sha256:" + "1" * 64
    decision = Phase20ForwardDecisionSeal(
        evidence_id="evidence-1",
        decision_epoch_id="epoch-1",
        evidence_sha256=evidence_sha,
        decision_at=decision_at,
        candidate_id="candidate-v3",
        code_sha="a" * 40,
        parameter_sha256="sha256:" + "b" * 64,
        signal_fingerprints=("signal-1",),
        canonical_payload_json="{}",
        sealed_at=decision_at + timedelta(milliseconds=100),
        seal_deadline_at=decision_at + timedelta(seconds=2),
    )
    evidence_book = VersionedPhase20ForwardEvidenceBook(
        generation=1,
        decisions=(decision,),
    )

    canonical_record_json = json.dumps(
        {
            "evidence_sha256": evidence_sha,
            "allocator_decision": {
                "disposition": "ALLOCATE",
                "applied_tools": ["T03"],
                "allocation": {
                    "selected_signal_fingerprints": ["signal-1"],
                },
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    policy_sha = "sha256:" + hashlib.sha256(
        canonical_record_json.encode()
    ).hexdigest()
    policy = Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=evidence_sha,
        policy_record_sha256=policy_sha,
        allocator_disposition="ALLOCATE",
        selected_signal_fingerprints=("signal-1",),
        canonical_record_json=canonical_record_json,
    )
    policy_book = VersionedPhase20ForwardPolicyBook(
        generation=1,
        decisions=(policy,),
    )

    shadow = Phase20T12ToolEligibilityShadowDecision(
        policy_id=T12_SHADOW_POLICY_ID,
        policy_sha256=t12_shadow_policy_sha256(),
        policy_frozen_at=T12_SHADOW_POLICY_FROZEN_AT,
        decision_epoch_id="epoch-1",
        decision_evidence_sha256=evidence_sha,
        baseline_policy_record_sha256=policy_sha,
        treatment_enabled_tools=("T03",),
        treatment_blocked_tools=("T09",),
        control_enabled_tools=("T03", "T09"),
        control_blocked_tools=(),
        treatment_allocator_disposition="ALLOCATE",
        control_allocator_disposition="ALLOCATE",
        treatment_allocator_applied_tools=("T03",),
        control_allocator_applied_tools=("T03", "T09"),
        treatment_selected_signal_fingerprints=("signal-1",),
        control_selected_signal_fingerprints=("signal-1",),
        selection_changed=False,
        allocator_changed=True,
    )
    return shadow, evidence_book, policy_book, decision_at


def test_t12_shadow_store_is_append_only_hash_chained_and_idempotent(
    tmp_path,
) -> None:
    shadow, evidence_book, policy_book, decision_at = _fixture()
    path = tmp_path / "t12-shadow.json"
    store = DurableT12ShadowDecisionStore(
        path,
        clock=lambda: decision_at + timedelta(seconds=1),
    )

    book = store.seal_shadow_decision(
        shadow,
        evidence_book=evidence_book,
        policy_book=policy_book,
        expected_generation=0,
    )

    assert book.generation == 1
    assert len(book.records) == 1
    assert book.decision_for_evidence(
        shadow.decision_evidence_sha256
    ) is not None
    assert store.load() == book

    again = store.seal_shadow_decision(
        shadow,
        evidence_book=evidence_book,
        policy_book=policy_book,
        expected_generation=1,
    )
    assert again == book


def test_t12_shadow_store_fails_closed_on_generation_conflict(
    tmp_path,
) -> None:
    shadow, evidence_book, policy_book, decision_at = _fixture()
    store = DurableT12ShadowDecisionStore(
        tmp_path / "t12-shadow.json",
        clock=lambda: decision_at + timedelta(seconds=1),
    )

    with pytest.raises(
        DurableT12ShadowDecisionError,
        match="generation conflict",
    ):
        store.seal_shadow_decision(
            shadow,
            evidence_book=evidence_book,
            policy_book=policy_book,
            expected_generation=1,
        )


def test_t12_shadow_store_fails_closed_after_two_second_window(
    tmp_path,
) -> None:
    shadow, evidence_book, policy_book, decision_at = _fixture()
    store = DurableT12ShadowDecisionStore(
        tmp_path / "t12-shadow.json",
        clock=lambda: decision_at + timedelta(seconds=3),
    )

    with pytest.raises(
        DurableT12ShadowDecisionError,
        match="two-second window",
    ):
        store.seal_shadow_decision(
            shadow,
            evidence_book=evidence_book,
            policy_book=policy_book,
            expected_generation=0,
        )
