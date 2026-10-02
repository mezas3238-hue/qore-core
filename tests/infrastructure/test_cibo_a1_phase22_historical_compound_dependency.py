from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_a1_a2_scientific_dependency import (
    CONTRACT_ID as A1_A2_DEPENDENCY_CONTRACT_ID,
)
from qore.infrastructure.cibo_a1_a2_scientific_dependency import (
    A1A2ScientificDependencyAdmission,
)
from qore.infrastructure.cibo_a1_phase22_canonical_manifest_bridge import (
    BRIDGE_ID,
    A1Phase22CanonicalScientificManifestBridge,
)
from qore.infrastructure.cibo_a1_phase22_historical_compound_dependency import (
    CONTRACT_ID,
    A1HistoricalCompoundLineageReceipt,
    admit_historical_compound_lineage_for_a1,
)
from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    MANIFEST_ID,
    A1Phase22PopulationFold,
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

BASE = datetime(2015, 10, 20, tzinfo=UTC)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _manifest() -> A1Phase22ScientificConsumptionManifest:
    folds = tuple(
        A1Phase22PopulationFold(
            fold_id=f"WF{index + 1}",
            decision_count=20,
            first_decision_at=BASE + timedelta(days=index * 20),
            last_decision_at=BASE + timedelta(days=(index + 1) * 20 - 1),
            population_sha256=_sha(f"fold-{index + 1}"),
        )
        for index in range(4)
    )
    return A1Phase22ScientificConsumptionManifest(
        manifest_id=MANIFEST_ID,
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        code_sha="a" * 40,
        parameter_sha256=_sha("params"),
        amendment_sha256=_sha("amendment"),
        source_population_sha256=_sha("population"),
        policy_population_sha256=_sha("policies"),
        decision_count=80,
        policy_count=80,
        outcome_count=100,
        trader_ids=("VT31_NAS100",),
        folds=folds,
        exact_policy_coverage=True,
        historical_replay_only=True,
        folds_defined_without_outcomes=True,
    )


def _bridge() -> A1Phase22CanonicalScientificManifestBridge:
    manifest = _manifest()
    return A1Phase22CanonicalScientificManifestBridge(
        bridge_id=BRIDGE_ID,
        canonical_phase22_manifest_sha256=_sha("canonical-phase22"),
        a1_consumption_manifest_sha256=manifest.fingerprint(),
        candidate_id=manifest.candidate_id,
        decision_epochs=manifest.decision_count,
        trader_ids=manifest.trader_ids,
        fold_ids=("WF1", "WF2", "WF3", "WF4"),
        qualification_status="PASS",
        ready_for_scientific_reentry=True,
        exact_candidate_binding=True,
        exact_decision_population_count=True,
        exact_trader_lineage=True,
        exact_fold_lineage=True,
        a2_compatible_manifest_identity=True,
    )


def _a2_dependency() -> A1A2ScientificDependencyAdmission:
    bridge = _bridge()
    return A1A2ScientificDependencyAdmission(
        contract_id=A1_A2_DEPENDENCY_CONTRACT_ID,
        a2_workstream_id="COMPOUND_ENGINE",
        canonical_phase22_manifest_sha256=bridge.canonical_phase22_manifest_sha256,
        a1_manifest_bridge_sha256=bridge.fingerprint(),
        a2_source_head="b" * 40,
        a2_source_gate_id="COMPOUND_ENGINE_PHASE22_GATE_V1",
        a2_source_gate_evidence_sha256=_sha("compound-engine-evidence"),
        a2_disposition_receipt_sha256=_sha("compound-engine-disposition"),
        recommended_disposition="COMPLETED_AND_PROVEN",
        admitted_for_a1_consumption=True,
    )


def _receipt() -> A1HistoricalCompoundLineageReceipt:
    manifest = _manifest()
    return A1HistoricalCompoundLineageReceipt(
        contract_id=CONTRACT_ID,
        source_workstream="COMPOUND_ENGINE",
        source_head="b" * 40,
        artifact_sha256=_sha("compound-adapter"),
        source_population_sha256=manifest.source_population_sha256,
        a1_manifest_sha256=manifest.fingerprint(),
        adapter_identity="CIBO_PHASE22_HISTORICAL_COMPOUND_LINEAGE_ADAPTER_V1",
        historical_replay_supported=True,
        historical_broker_ids_required=False,
        historical_broker_ids_emitted=False,
        current_demo_ids_relabelled_as_historical=False,
        fabricated_execution_ids_used=False,
        realized_profit_only=True,
        floating_pnl_used_as_capital=False,
        capital_conservation_proven=True,
        double_spend_detected=False,
        decision_before_outcome_preserved=True,
        deterministic_replay=True,
    )


def test_a1_admits_nonfabricated_historical_compound_receipt() -> None:
    admission = admit_historical_compound_lineage_for_a1(
        manifest=_manifest(),
        canonical_bridge=_bridge(),
        a2_dependency=_a2_dependency(),
        receipt=_receipt(),
    )

    assert admission.ready_for_a1_genc_consumption is True
    assert admission.a2_workstream_modified is False
    assert admission.productive_authority is False
    assert admission.certification_ready is False


def test_a1_rejects_fabricated_historical_broker_ids() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="violates replay/governance law",
    ):
        replace(_receipt(), fabricated_execution_ids_used=True)


def test_a1_rejects_current_demo_ids_relabelled_as_historical() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="violates replay/governance law",
    ):
        replace(
            _receipt(),
            current_demo_ids_relabelled_as_historical=True,
        )


def test_a1_rejects_compound_population_drift() -> None:
    receipt = replace(
        _receipt(),
        source_population_sha256=_sha("different-population"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="source population drift",
    ):
        admit_historical_compound_lineage_for_a1(
            manifest=_manifest(),
            canonical_bridge=_bridge(),
            a2_dependency=_a2_dependency(),
            receipt=receipt,
        )


def test_a1_never_closes_a2_compound_engine() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="violates replay/governance law",
    ):
        replace(_receipt(), a1_closes_source_workstream=True)


def test_a1_historical_compound_rejects_wrong_a2_dependency() -> None:
    dependency = replace(
        _a2_dependency(),
        a2_workstream_id="INTERNAL_CAPITAL_MARKET",
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires COMPOUND_ENGINE A2 dependency",
    ):
        admit_historical_compound_lineage_for_a1(
            manifest=_manifest(),
            canonical_bridge=_bridge(),
            a2_dependency=dependency,
            receipt=_receipt(),
        )
