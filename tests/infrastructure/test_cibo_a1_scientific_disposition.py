from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from qore.infrastructure.cibo_a1_scientific_disposition import (
    A1_WORKSTREAMS,
    A1ScientificDispositionPackage,
    A1ScientificStatus,
    build_a1_scientific_disposition,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _disposition(
    workstream_id: str = "T08",
    *,
    status: A1ScientificStatus = A1ScientificStatus.COMPLETED_AND_PROVEN,
):
    kwargs = {
        "workstream_id": workstream_id,
        "scientific_status": status,
        "hypothesis": f"{workstream_id} frozen hypothesis",
        "mechanism_identity": f"{workstream_id}_MECHANISM_V1",
        "candidate_id": "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        "code_sha": "a" * 40,
        "parameter_sha256": _sha("parameters"),
        "source_evidence": (_sha(f"evidence-{workstream_id}"),),
        "population_identity": f"{workstream_id}:WF1-WF4",
        "decision_time_boundary": "decision_at < outcome_observed_at",
        "control_baseline": f"{workstream_id}:CONTROL",
        "metrics": {"folds": "4/4", "causal": "true"},
        "result": "terminal scientific result",
    }
    if status is A1ScientificStatus.COMPLETED_AND_PROVEN:
        kwargs["proof_reason"] = "preregistered claim proven on canonical evidence"
    else:
        kwargs["failure_reason"] = "preregistered claim failed without retune"
    return build_a1_scientific_disposition(**kwargs)


def test_a1_proven_disposition_receipt_binds_canonical_payload() -> None:
    disposition = _disposition()

    assert disposition.receipt_matches_payload() is True
    assert disposition.productive_authority is False
    assert disposition.global_ledger_reconciled is False
    assert disposition.cibo_certified is False


def test_a1_falsified_disposition_is_terminal_without_proof_claim() -> None:
    disposition = _disposition(
        "T15",
        status=A1ScientificStatus.FALSIFIED_AND_CLOSED,
    )

    assert disposition.receipt_matches_payload() is True
    assert disposition.proof_reason is None
    assert disposition.failure_reason is not None


def test_a1_disposition_rejects_a2_workstream() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="outside A1 ownership",
    ):
        _disposition("GEN-C8")


def test_a1_package_partial_handoff_reports_remaining_work() -> None:
    disposition = _disposition("T08")
    package = A1ScientificDispositionPackage(
        source_branch="agent/cibo-architect-a1-causal-science-001",
        source_head="b" * 40,
        canonical_phase22_manifest_sha256=_sha("canonical-phase22"),
        a1_consumption_manifest_sha256=_sha("a1-consumption"),
        canonical_manifest_bridge_sha256=_sha("bridge"),
        dispositions=(disposition,),
        complete_handoff=False,
    )

    assert package.terminal_count == 1
    assert "T08" not in package.remaining_workstreams
    assert len(package.remaining_workstreams) == 17


def test_a1_complete_handoff_requires_exactly_eighteen_terminal_rows() -> None:
    dispositions = tuple(_disposition(item) for item in A1_WORKSTREAMS)
    package = A1ScientificDispositionPackage(
        source_branch="agent/cibo-architect-a1-causal-science-001",
        source_head="c" * 40,
        canonical_phase22_manifest_sha256=_sha("canonical-phase22"),
        a1_consumption_manifest_sha256=_sha("a1-consumption"),
        canonical_manifest_bridge_sha256=_sha("bridge"),
        dispositions=dispositions,
        complete_handoff=True,
    )

    assert package.terminal_count == 18
    assert package.remaining_workstreams == ()


def test_a1_package_rejects_tampered_receipt() -> None:
    disposition = replace(
        _disposition("T08"),
        receipt_sha256=_sha("tampered"),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="receipt/payload mismatch",
    ):
        A1ScientificDispositionPackage(
            source_branch="agent/cibo-architect-a1-causal-science-001",
            source_head="d" * 40,
            canonical_phase22_manifest_sha256=_sha("canonical-phase22"),
            a1_consumption_manifest_sha256=_sha("a1-consumption"),
            canonical_manifest_bridge_sha256=_sha("bridge"),
            dispositions=(disposition,),
            complete_handoff=False,
        )


def test_a1_package_requires_canonical_phase22_manifest_digests() -> None:
    disposition = _disposition("T08")

    with pytest.raises(
        CiboCapitalManagementError,
        match="canonical_phase22_manifest_sha256",
    ):
        A1ScientificDispositionPackage(
            source_branch="agent/cibo-architect-a1-causal-science-001",
            source_head="e" * 40,
            canonical_phase22_manifest_sha256="not-a-sha",
            a1_consumption_manifest_sha256=_sha("a1-consumption"),
            canonical_manifest_bridge_sha256=_sha("bridge"),
            dispositions=(disposition,),
            complete_handoff=False,
        )
