from __future__ import annotations

from hashlib import sha256

import pytest

from qore.infrastructure.cibo_arch_a2_scientific_closure import (
    A1_RESERVED_WORKSTREAM_IDS,
    A2_WORKSTREAM_IDS,
    reconcile_architect_a2_scientific_dispositions,
    view_architect_a2_evidence_matrix,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificDispositionReceipt,
    ArchitectAPhase22V2WorkstreamEvidenceMatrix,
    ArchitectAPhase22V2WorkstreamEvidenceState,
    ArchitectAReadinessError,
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _receipt(
    workstream_id: str,
    *,
    passed: bool = True,
    owner_review_approved: bool = True,
) -> ArchitectAPhase22V2ScientificDispositionReceipt:
    if passed:
        disposition = (
            "COMPLETED_AND_PROVEN"
            if workstream_id != "GEN-C14" or owner_review_approved
            else "EXTERNAL_DEPENDENCY_BLOCKED"
        )
    else:
        disposition = "FALSIFIED_AND_CLOSED"
    return ArchitectAPhase22V2ScientificDispositionReceipt(
        schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
        workstream_id=workstream_id,
        phase22_manifest_sha256=_sha("manifest"),
        source_gate_id=f"gate:{workstream_id}",
        source_gate_evidence_sha256=_sha(workstream_id),
        source_gate_status="PASS" if passed else "FAIL",
        passed=passed,
        recommended_disposition=disposition,
        blockers=() if passed else ("FALSIFIED_DIMENSION",),
        failed_dimensions=() if passed else ("economic_value",),
        owner_review_approved=owner_review_approved,
    )


def test_a1_a2_partition_is_exact_and_disjoint() -> None:
    assert len(A1_RESERVED_WORKSTREAM_IDS) == 18
    assert len(A2_WORKSTREAM_IDS) == 17
    assert not set(A1_RESERVED_WORKSTREAM_IDS) & set(A2_WORKSTREAM_IDS)


def test_a2_packet_terminal_17_of_17_is_ready_for_integrator() -> None:
    receipts = tuple(_receipt(item) for item in A2_WORKSTREAM_IDS)

    packet = reconcile_architect_a2_scientific_dispositions(
        phase22_manifest_sha256=_sha("manifest"),
        receipts=receipts,
    )

    assert packet.receipt_count == 17
    assert packet.terminal_count == 17
    assert packet.completed_ids == A2_WORKSTREAM_IDS
    assert packet.falsified_ids == ()
    assert packet.external_ids == ()
    assert packet.missing_ids == ()
    assert packet.ready_for_integrator is True
    assert packet.ledger_update_authority is False
    assert packet.certification_claimed is False
    assert packet.productive_authority is False
    assert packet.merge_authority is False
    assert packet.fingerprint().startswith("sha256:")


def test_a2_packet_accepts_scientific_falsification_as_terminal() -> None:
    receipts = tuple(
        _receipt(item, passed=item != "GEN-C12")
        for item in A2_WORKSTREAM_IDS
    )

    packet = reconcile_architect_a2_scientific_dispositions(
        phase22_manifest_sha256=_sha("manifest"),
        receipts=receipts,
    )

    assert packet.terminal_count == 17
    assert packet.falsified_ids == ("GEN-C12",)
    assert packet.ready_for_integrator is True


def test_a2_packet_keeps_genc14_external_without_owner_review() -> None:
    receipts = tuple(
        _receipt(
            item,
            owner_review_approved=item != "GEN-C14",
        )
        for item in A2_WORKSTREAM_IDS
    )

    packet = reconcile_architect_a2_scientific_dispositions(
        phase22_manifest_sha256=_sha("manifest"),
        receipts=receipts,
    )

    assert packet.terminal_count == 16
    assert packet.external_ids == ("GEN-C14",)
    assert packet.ready_for_integrator is False


def test_a2_packet_rejects_a1_owned_receipt() -> None:
    with pytest.raises(
        ArchitectAReadinessError,
        match="cannot consume A1-owned",
    ):
        reconcile_architect_a2_scientific_dispositions(
            phase22_manifest_sha256=_sha("manifest"),
            receipts=(_receipt("T04"),),
        )


def test_a2_packet_reports_missing_receipts_without_promoting_them() -> None:
    receipts = tuple(_receipt(item) for item in A2_WORKSTREAM_IDS[:-1])

    packet = reconcile_architect_a2_scientific_dispositions(
        phase22_manifest_sha256=_sha("manifest"),
        receipts=receipts,
    )

    assert packet.terminal_count == 16
    assert packet.missing_ids == ("AS_IS_ECONOMIC_BASELINE",)
    assert packet.ready_for_integrator is False


def test_a2_evidence_view_can_be_ready_while_a1_remains_blocked() -> None:
    states = []
    ready_ids = []
    blocked_ids = []
    for workstream_id, required in (
        _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM.items()
    ):
        if workstream_id in A2_WORKSTREAM_IDS:
            present = required
            missing = ()
            ready = True
            ready_ids.append(workstream_id)
        else:
            present = ()
            missing = required
            ready = False
            blocked_ids.append(workstream_id)
        states.append(
            ArchitectAPhase22V2WorkstreamEvidenceState(
                workstream_id=workstream_id,
                required_kinds=required,
                present_kinds=present,
                missing_kinds=missing,
                ready_for_frozen_evaluation=ready,
            )
        )
    matrix = ArchitectAPhase22V2WorkstreamEvidenceMatrix(
        phase22_manifest_sha256=_sha("manifest"),
        states=tuple(states),
        ready_ids=tuple(ready_ids),
        blocked_ids=tuple(blocked_ids),
        all_external_workstreams_ready=False,
    )

    view = view_architect_a2_evidence_matrix(matrix)

    assert view.ready_ids == A2_WORKSTREAM_IDS
    assert view.blocked_ids == ()
    assert view.all_a2_workstreams_ready is True
    assert view.a1_state_consumed is False
    assert view.integration_authority is False
    assert view.productive_authority is False
