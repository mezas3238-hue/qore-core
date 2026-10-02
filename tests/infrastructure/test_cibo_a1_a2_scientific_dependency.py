from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from qore.infrastructure.cibo_a1_a2_scientific_dependency import (
    A1_ALLOWED_A2_DEPENDENCIES,
    admit_proven_a2_dependency_for_a1,
)
from qore.infrastructure.cibo_a1_phase22_canonical_manifest_bridge import (
    BRIDGE_ID,
    A1Phase22CanonicalScientificManifestBridge,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _bridge() -> A1Phase22CanonicalScientificManifestBridge:
    return A1Phase22CanonicalScientificManifestBridge(
        bridge_id=BRIDGE_ID,
        canonical_phase22_manifest_sha256=_sha("canonical-phase22"),
        canonical_execution_manifest_sha256=_sha("execution-manifest"),
        a1_consumption_manifest_sha256=_sha("a1-consumption"),
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        decision_epochs=100,
        trader_ids=(
            "VT08_FOREX",
            "R34_XAUUSD",
            "R38_EURUSD",
            "R43_GBPUSD",
            "R38_GBPJPY",
            "R42_AUDJPY",
            "VT31_NAS100",
        ),
        fold_ids=("WF1", "WF2", "WF3", "WF4"),
        qualification_status="PASS",
        ready_for_scientific_reentry=True,
        exact_candidate_binding=True,
        exact_execution_identity_binding=True,
        exact_decision_population_count=True,
        exact_trader_lineage=True,
        exact_fold_lineage=True,
        a2_compatible_manifest_identity=True,
    )


def _receipt(
    workstream_id: str = "COMPOUND_ENGINE",
) -> ArchitectAPhase22V2ScientificDispositionReceipt:
    return ArchitectAPhase22V2ScientificDispositionReceipt(
        schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
        workstream_id=workstream_id,
        phase22_manifest_sha256=_bridge().canonical_phase22_manifest_sha256,
        source_gate_id=f"{workstream_id}_PHASE22_GATE_V1",
        source_gate_evidence_sha256=_sha(f"{workstream_id}-evidence"),
        source_gate_status="PASS",
        passed=True,
        recommended_disposition="COMPLETED_AND_PROVEN",
        blockers=(),
        failed_dimensions=(),
        owner_review_approved=False,
    )


@pytest.mark.parametrize("workstream_id", A1_ALLOWED_A2_DEPENDENCIES)
def test_a1_admits_only_proven_allowed_a2_dependencies(
    workstream_id: str,
) -> None:
    admission = admit_proven_a2_dependency_for_a1(
        bridge=_bridge(),
        a2_source_head="b" * 40,
        receipt=_receipt(workstream_id),
    )

    assert admission.a2_workstream_id == workstream_id
    assert admission.admitted_for_a1_consumption is True
    assert admission.a1_modifies_a2_workstream is False
    assert admission.a1_closes_a2_workstream is False
    assert admission.integration_authority is False


def test_a1_rejects_unproven_a2_dependency() -> None:
    receipt = replace(
        _receipt(),
        passed=False,
        recommended_disposition="FALSIFIED_AND_CLOSED",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="not scientifically proven",
    ):
        admit_proven_a2_dependency_for_a1(
            bridge=_bridge(),
            a2_source_head="b" * 40,
            receipt=receipt,
        )


def test_a1_rejects_a2_manifest_drift() -> None:
    receipt = replace(
        _receipt(),
        phase22_manifest_sha256=_sha("different-phase22"),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="canonical Phase22 manifest drift",
    ):
        admit_proven_a2_dependency_for_a1(
            bridge=_bridge(),
            a2_source_head="b" * 40,
            receipt=receipt,
        )


def test_a1_rejects_non_dependency_a2_workstream() -> None:
    receipt = _receipt("GEN-C8")

    with pytest.raises(
        CiboCapitalManagementError,
        match="not consumable by A1",
    ):
        admit_proven_a2_dependency_for_a1(
            bridge=_bridge(),
            a2_source_head="b" * 40,
            receipt=receipt,
        )
