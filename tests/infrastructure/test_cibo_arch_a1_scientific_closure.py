from __future__ import annotations

import hashlib

import pytest

from qore.infrastructure.cibo_a1_scientific_disposition import A1_WORKSTREAMS
from qore.infrastructure.cibo_arch_a1_scientific_closure import (
    A1_SCIENTIFIC_WAVE_1,
    A1_SCIENTIFIC_WAVE_2,
    A1_SCIENTIFIC_WAVE_3,
    build_architect_a1_scientific_execution_plan,
    evaluate_architect_a1_scientific_outcomes,
    reconcile_architect_a1_scientific_dispositions,
    view_architect_a1_evidence_matrix,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    A_WORKSTREAM_IDS,
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificDispositionReceipt,
    ArchitectAPhase22V2WorkstreamEvidenceMatrix,
    ArchitectAPhase22V2WorkstreamEvidenceState,
    ArchitectAReadinessError,
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _matrix() -> ArchitectAPhase22V2WorkstreamEvidenceMatrix:
    states = tuple(
        ArchitectAPhase22V2WorkstreamEvidenceState(
            workstream_id=workstream_id,
            required_kinds=_PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM[
                workstream_id
            ],
            present_kinds=_PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM[
                workstream_id
            ],
            missing_kinds=(),
            ready_for_frozen_evaluation=True,
        )
        for workstream_id in A_WORKSTREAM_IDS
    )
    return ArchitectAPhase22V2WorkstreamEvidenceMatrix(
        phase22_manifest_sha256=_sha("phase22"),
        states=states,
        ready_ids=A_WORKSTREAM_IDS,
        blocked_ids=(),
        all_external_workstreams_ready=True,
    )


def _receipt(
    workstream_id: str,
    *,
    passed: bool = True,
) -> ArchitectAPhase22V2ScientificDispositionReceipt:
    return ArchitectAPhase22V2ScientificDispositionReceipt(
        schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
        workstream_id=workstream_id,
        phase22_manifest_sha256=_sha("phase22"),
        source_gate_id=f"{workstream_id}_GATE_V1",
        source_gate_evidence_sha256=_sha(f"{workstream_id}-evidence"),
        source_gate_status="PASS" if passed else "FAIL",
        passed=passed,
        recommended_disposition=(
            "COMPLETED_AND_PROVEN" if passed else "FALSIFIED_AND_CLOSED"
        ),
        blockers=() if passed else ("FROZEN_HYPOTHESIS_FAILED",),
        failed_dimensions=(),
        owner_review_approved=False,
    )


def test_a1_evidence_view_filters_exact_eighteen_from_full_a_matrix() -> None:
    view = view_architect_a1_evidence_matrix(_matrix())

    assert tuple(item.workstream_id for item in view.states) == A1_WORKSTREAMS
    assert view.ready_ids == A1_WORKSTREAMS
    assert view.blocked_ids == ()
    assert view.a2_state_consumed is False


def test_a1_execution_plan_has_exact_three_wave_surface() -> None:
    plan = build_architect_a1_scientific_execution_plan(
        view_architect_a1_evidence_matrix(_matrix())
    )

    assert plan.wave_1_ids == A1_SCIENTIFIC_WAVE_1
    assert plan.wave_2_ids == A1_SCIENTIFIC_WAVE_2
    assert plan.wave_3_ids == A1_SCIENTIFIC_WAVE_3
    assert plan.exact_a1_surface is True
    assert plan.a2_execution_required is False


def test_a1_outcome_evaluation_uses_canonical_phase22_disposition_law() -> None:
    receipts = evaluate_architect_a1_scientific_outcomes(
        matrix=_matrix(),
        payloads=(
            {
                "workstream_id": "T04",
                "phase22_manifest_sha256": _sha("phase22"),
                "source_gate_id": "T04_GATE_V1",
                "source_gate_evidence_sha256": _sha("t04-evidence"),
                "source_gate_status": "PASS",
                "passed": True,
                "blockers": [],
                "failed_dimensions": [],
                "evaluation_complete": True,
            },
        ),
    )

    assert len(receipts) == 1
    assert receipts[0].workstream_id == "T04"
    assert receipts[0].recommended_disposition == "COMPLETED_AND_PROVEN"


def test_a1_outcome_evaluation_rejects_a2_owned_work() -> None:
    with pytest.raises(
        ArchitectAReadinessError,
        match="cannot evaluate A2-owned workstream",
    ):
        evaluate_architect_a1_scientific_outcomes(
            matrix=_matrix(),
            payloads=(
                {
                    "workstream_id": "COMPOUND_ENGINE",
                },
            ),
        )


def test_a1_closure_packet_is_ready_with_exact_eighteen_terminal_receipts() -> None:
    receipts = tuple(
        _receipt(workstream_id, passed=(workstream_id != "T15"))
        for workstream_id in A1_WORKSTREAMS
    )
    packet = reconcile_architect_a1_scientific_dispositions(
        phase22_manifest_sha256=_sha("phase22"),
        receipts=receipts,
    )

    assert packet.terminal_count == 18
    assert packet.missing_ids == ()
    assert packet.ready_for_integrator is True
    assert "T15" in packet.falsified_ids
    assert len(packet.completed_ids) == 17
    assert packet.fingerprint().startswith("sha256:")


def test_a1_closure_packet_keeps_missing_work_blocked() -> None:
    receipts = tuple(_receipt(item) for item in A1_WORKSTREAMS[:-1])
    packet = reconcile_architect_a1_scientific_dispositions(
        phase22_manifest_sha256=_sha("phase22"),
        receipts=receipts,
    )

    assert packet.ready_for_integrator is False
    assert packet.missing_ids == (A1_WORKSTREAMS[-1],)


def test_a1_closure_rejects_a2_receipt() -> None:
    with pytest.raises(
        ArchitectAReadinessError,
        match="cannot consume A2-owned workstream receipt",
    ):
        reconcile_architect_a1_scientific_dispositions(
            phase22_manifest_sha256=_sha("phase22"),
            receipts=(_receipt("COMPOUND_ENGINE"),),
        )
