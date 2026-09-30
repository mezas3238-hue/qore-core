from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_governed_capital_science import (
    GENC14_POLICY_SHA256,
    Genc14CapitalHypothesis,
    Genc14EvidenceKind,
    Genc14ScienceEvidence,
    Genc14ScienceStage,
    advance_genc14_science,
    reject_genc14_science,
    start_genc14_science,
)

T0 = datetime(2026, 9, 30, 8, 30, tzinfo=UTC)


def _hypothesis() -> Genc14CapitalHypothesis:
    return Genc14CapitalHypothesis(
        hypothesis_id="hypothesis-1",
        research_question="Can reserve-aware compounding improve robust value?",
        candidate_policy_id="CIBO_CANDIDATE_X",
        candidate_policy_sha256="sha256:" + "1" * 64,
        current_control_policy_id="CIBO_CURRENT_CONTROL",
        current_control_policy_sha256="sha256:" + "2" * 64,
        created_at=T0,
        protected_holdout_ref="CIBO_USD60_6M_HOLDOUT_2017H1_V1",
    )


def _evidence(
    *,
    kind: Genc14EvidenceKind,
    minute: int,
    passed: bool = True,
    digit: str = "3",
) -> Genc14ScienceEvidence:
    return Genc14ScienceEvidence(
        evidence_id=f"{kind.value.lower()}-{minute}",
        kind=kind,
        candidate_policy_sha256="sha256:" + "1" * 64,
        evaluated_at=T0 + timedelta(minutes=minute),
        evidence_sha256="sha256:" + digit * 64,
        passed=passed,
    )


def test_genc14_policy_digest_is_frozen() -> None:
    assert GENC14_POLICY_SHA256 == (
        "sha256:1a3d3673511f11114907825ab74d26f72f08bea6c115bf27dc8808fb72e9227a"
    )


def test_genc14_cannot_reuse_current_control_as_candidate() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="distinct semantic identity",
    ):
        Genc14CapitalHypothesis(
            hypothesis_id="same",
            research_question="same",
            candidate_policy_id="same",
            candidate_policy_sha256="sha256:" + "1" * 64,
            current_control_policy_id="same",
            current_control_policy_sha256="sha256:" + "1" * 64,
            created_at=T0,
        )


def test_genc14_full_pass_stops_at_owner_review_without_promotion() -> None:
    record = start_genc14_science(
        science_id="science-1",
        hypothesis=_hypothesis(),
    )
    gates = (
        Genc14EvidenceKind.PREREGISTRATION,
        Genc14EvidenceKind.SIMULATION,
        Genc14EvidenceKind.OOS,
        Genc14EvidenceKind.STRESS,
        Genc14EvidenceKind.TEMPORAL_REPLICATION,
    )
    for index, kind in enumerate(gates, start=1):
        record = advance_genc14_science(
            record,
            evidence=_evidence(
                kind=kind,
                minute=index,
                digit=str(index + 2),
            ),
            advanced_at=T0 + timedelta(minutes=index),
        )
    record = advance_genc14_science(
        record,
        evidence=None,
        advanced_at=T0 + timedelta(minutes=6),
    )

    assert record.stage is Genc14ScienceStage.OWNER_REVIEW_REQUIRED
    assert record.terminal is True
    assert record.current_control_policy_sha256 == "sha256:" + "2" * 64
    assert record.automatic_promotion is False
    assert record.certification_claimed is False
    assert record.owner_decision_recorded is False


def test_genc14_failed_gate_falsifies_and_closes_candidate() -> None:
    record = start_genc14_science(
        science_id="science-fail",
        hypothesis=_hypothesis(),
    )
    record = advance_genc14_science(
        record,
        evidence=_evidence(
            kind=Genc14EvidenceKind.PREREGISTRATION,
            minute=1,
        ),
        advanced_at=T0 + timedelta(minutes=1),
    )
    record = advance_genc14_science(
        record,
        evidence=_evidence(
            kind=Genc14EvidenceKind.SIMULATION,
            minute=2,
            passed=False,
            digit="4",
        ),
        advanced_at=T0 + timedelta(minutes=2),
    )

    assert record.stage is Genc14ScienceStage.FALSIFIED_AND_CLOSED
    assert record.terminal is True
    assert "SIMULATION gate failed" in (record.closure_reason or "")

    with pytest.raises(
        CiboCapitalManagementError,
        match="terminal science record cannot advance",
    ):
        advance_genc14_science(
            record,
            evidence=_evidence(
                kind=Genc14EvidenceKind.OOS,
                minute=3,
                digit="5",
            ),
            advanced_at=T0 + timedelta(minutes=3),
        )


def test_genc14_cannot_skip_scientific_gate() -> None:
    record = start_genc14_science(
        science_id="science-skip",
        hypothesis=_hypothesis(),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot skip or reorder",
    ):
        advance_genc14_science(
            record,
            evidence=_evidence(
                kind=Genc14EvidenceKind.SIMULATION,
                minute=1,
            ),
            advanced_at=T0 + timedelta(minutes=1),
        )


def test_genc14_oos_cannot_reuse_burned_data() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="OOS evidence cannot reuse burned data",
    ):
        Genc14ScienceEvidence(
            evidence_id="bad-oos",
            kind=Genc14EvidenceKind.OOS,
            candidate_policy_sha256="sha256:" + "1" * 64,
            evaluated_at=T0 + timedelta(minutes=3),
            evidence_sha256="sha256:" + "6" * 64,
            passed=True,
            burned_data_used=True,
        )


def test_genc14_protected_holdout_cannot_leak_into_simulation() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="protected holdout cannot be consumed outside OOS gate",
    ):
        Genc14ScienceEvidence(
            evidence_id="holdout-leak",
            kind=Genc14EvidenceKind.SIMULATION,
            candidate_policy_sha256="sha256:" + "1" * 64,
            evaluated_at=T0 + timedelta(minutes=2),
            evidence_sha256="sha256:" + "7" * 64,
            passed=True,
            protected_holdout_used=True,
        )


def test_genc14_explicit_rejection_is_terminal_without_control_mutation() -> None:
    record = start_genc14_science(
        science_id="science-reject",
        hypothesis=_hypothesis(),
    )
    rejected = reject_genc14_science(
        record,
        rejected_at=T0 + timedelta(minutes=1),
        reason="provider economics unavailable for this hypothesis",
    )

    assert rejected.stage is Genc14ScienceStage.REJECTED_AND_CLOSED
    assert rejected.current_control_policy_sha256 == "sha256:" + "2" * 64
    assert rejected.productive_control_mutated is False
    assert rejected.automatic_promotion is False
