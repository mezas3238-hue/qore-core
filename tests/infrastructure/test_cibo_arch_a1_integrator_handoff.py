from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from qore.infrastructure.cibo_a1_scientific_disposition import (
    A1_WORKSTREAMS,
    A1ScientificDispositionPackage,
    A1ScientificStatus,
    build_a1_scientific_disposition,
)
from qore.infrastructure.cibo_arch_a1_integrator_handoff import (
    A1_BRANCH,
    build_architect_a1_integrator_handoff,
)
from qore.infrastructure.cibo_arch_a1_internal_readiness import (
    evaluate_architect_a1_internal_readiness,
)
from qore.infrastructure.cibo_arch_a1_scientific_closure import (
    reconcile_architect_a1_scientific_dispositions,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _disposition(
    workstream_id: str,
    *,
    falsified: bool = False,
):
    status = (
        A1ScientificStatus.FALSIFIED_AND_CLOSED
        if falsified
        else A1ScientificStatus.COMPLETED_AND_PROVEN
    )
    kwargs = {
        "workstream_id": workstream_id,
        "scientific_status": status,
        "hypothesis": f"{workstream_id} frozen hypothesis",
        "mechanism_identity": f"{workstream_id}_MECHANISM_V1",
        "candidate_id": "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        "code_sha": "a" * 40,
        "parameter_sha256": _sha("parameters"),
        "source_evidence": (_sha(f"evidence-{workstream_id}"),),
        "population_identity": "PHASE22_V2:WF1-WF4",
        "decision_time_boundary": "decision_at < outcome_observed_at",
        "control_baseline": f"{workstream_id}:CONTROL",
        "metrics": {"folds": "4/4", "causal": "true"},
        "result": "terminal scientific result",
    }
    if falsified:
        kwargs["failure_reason"] = "frozen hypothesis failed without retune"
    else:
        kwargs["proof_reason"] = "frozen hypothesis proven on canonical evidence"
    return build_a1_scientific_disposition(**kwargs)


def _canonical_receipt(
    workstream_id: str,
    *,
    falsified: bool = False,
) -> ArchitectAPhase22V2ScientificDispositionReceipt:
    return ArchitectAPhase22V2ScientificDispositionReceipt(
        schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
        workstream_id=workstream_id,
        phase22_manifest_sha256=_sha("canonical-phase22"),
        source_gate_id=f"{workstream_id}_GATE_V1",
        source_gate_evidence_sha256=_sha(f"canonical-{workstream_id}"),
        source_gate_status="FAIL" if falsified else "PASS",
        passed=not falsified,
        recommended_disposition=(
            "FALSIFIED_AND_CLOSED"
            if falsified
            else "COMPLETED_AND_PROVEN"
        ),
        blockers=("FROZEN_HYPOTHESIS_FAILED",) if falsified else (),
        failed_dimensions=(),
        owner_review_approved=False,
    )


def _canonical_closure(*, falsified_ids: tuple[str, ...] = ("T15",)):
    receipts = tuple(
        _canonical_receipt(
            item,
            falsified=item in set(falsified_ids),
        )
        for item in A1_WORKSTREAMS
    )
    return reconcile_architect_a1_scientific_dispositions(
        phase22_manifest_sha256=_sha("canonical-phase22"),
        receipts=receipts,
    )


def _package(
    *,
    head: str = "b" * 40,
    complete: bool = True,
) -> A1ScientificDispositionPackage:
    workstreams = A1_WORKSTREAMS if complete else A1_WORKSTREAMS[:3]
    dispositions = tuple(
        _disposition(item, falsified=(item == "T15"))
        for item in workstreams
    )
    return A1ScientificDispositionPackage(
        source_branch=A1_BRANCH,
        source_head=head,
        canonical_phase22_manifest_sha256=_sha("canonical-phase22"),
        a1_consumption_manifest_sha256=_sha("a1-consumption"),
        canonical_manifest_bridge_sha256=_sha("bridge"),
        dispositions=dispositions,
        complete_handoff=complete,
    )


def test_a1_integrator_handoff_accepts_exact_terminal_18_surface() -> None:
    readiness = evaluate_architect_a1_internal_readiness(Path("."))
    package = _package()

    receipt = build_architect_a1_integrator_handoff(
        a1_head_sha="b" * 40,
        readiness=readiness,
        package=package,
        canonical_closure=_canonical_closure(),
    )

    assert receipt.terminal_count == 18
    assert "T15" in receipt.falsified_ids
    assert len(receipt.completed_ids) == 17
    assert receipt.blockers == ()
    assert receipt.ready_for_integrator is True
    assert receipt.ledger_update_authority is False
    assert receipt.certification_claimed is False
    assert receipt.fingerprint().startswith("sha256:")


def test_a1_integrator_handoff_keeps_partial_science_blocked() -> None:
    readiness = evaluate_architect_a1_internal_readiness(Path("."))
    package = _package(complete=False)

    receipt = build_architect_a1_integrator_handoff(
        a1_head_sha="b" * 40,
        readiness=readiness,
        package=package,
        canonical_closure=_canonical_closure(),
    )

    assert receipt.ready_for_integrator is False
    assert "A1_TERMINAL_SCIENTIFIC_PACKAGE_INCOMPLETE" in receipt.blockers
    assert "A1_EXACT_18_TERMINAL_DISPOSITIONS_REQUIRED" in receipt.blockers


def test_a1_integrator_handoff_rejects_stale_package_head_by_blocker() -> None:
    readiness = evaluate_architect_a1_internal_readiness(Path("."))
    package = _package(head="c" * 40)

    receipt = build_architect_a1_integrator_handoff(
        a1_head_sha="b" * 40,
        readiness=readiness,
        package=package,
        canonical_closure=_canonical_closure(),
    )

    assert receipt.ready_for_integrator is False
    assert receipt.blockers == ("A1_DISPOSITION_PACKAGE_HEAD_DRIFT",)


def test_a1_integrator_handoff_preserves_terminal_falsification() -> None:
    readiness = evaluate_architect_a1_internal_readiness(Path("."))
    package = _package()
    dispositions = tuple(
        _disposition("T08", falsified=True)
        if item.workstream_id == "T08"
        else item
        for item in package.dispositions
    )
    package = replace(package, dispositions=dispositions)

    receipt = build_architect_a1_integrator_handoff(
        a1_head_sha="b" * 40,
        readiness=readiness,
        package=package,
        canonical_closure=_canonical_closure(),
    )

    assert "T08" in receipt.falsified_ids
    assert receipt.ready_for_integrator is True


def test_a1_integrator_handoff_blocks_canonical_partition_drift() -> None:
    readiness = evaluate_architect_a1_internal_readiness(Path("."))
    package = _package()

    receipt = build_architect_a1_integrator_handoff(
        a1_head_sha="b" * 40,
        readiness=readiness,
        package=package,
        canonical_closure=_canonical_closure(falsified_ids=()),
    )

    assert receipt.ready_for_integrator is False
    assert "A1_CANONICAL_CLOSURE_COMPLETED_PARTITION_DRIFT" in receipt.blockers
    assert "A1_CANONICAL_CLOSURE_FALSIFIED_PARTITION_DRIFT" in receipt.blockers
