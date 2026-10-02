from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_a1_a2_scientific_dependency import (
    CONTRACT_ID as A1_A2_DEPENDENCY_CONTRACT_ID,
)
from qore.infrastructure.cibo_a1_a2_scientific_dependency import (
    A1A2ScientificDependencyAdmission,
)
from qore.infrastructure.cibo_a1_genc2_phase22_profit_graduation import (
    Genc2EconomicRole,
    Genc2EconomicStatus,
    Genc2ProfitGraduationFoldObservation,
    evaluate_genc2_phase22_profit_graduation,
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
FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _manifest() -> A1Phase22ScientificConsumptionManifest:
    folds = tuple(
        A1Phase22PopulationFold(
            fold_id=fold_id,
            decision_count=20,
            first_decision_at=BASE + timedelta(days=index * 20),
            last_decision_at=BASE + timedelta(days=(index + 1) * 20 - 1),
            population_sha256=_sha(f"population-{fold_id}"),
        )
        for index, fold_id in enumerate(FOLDS)
    )
    return A1Phase22ScientificConsumptionManifest(
        manifest_id=MANIFEST_ID,
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        code_sha="a" * 40,
        parameter_sha256=_sha("params"),
        amendment_sha256=_sha("amendment"),
        source_population_sha256=_sha("source-population"),
        policy_population_sha256=_sha("policy-population"),
        decision_count=80,
        policy_count=80,
        outcome_count=160,
        trader_ids=("R38_EURUSD", "VT31_NAS100"),
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
        canonical_execution_manifest_sha256=_sha("execution-manifest"),
        a1_consumption_manifest_sha256=manifest.fingerprint(),
        candidate_id=manifest.candidate_id,
        decision_epochs=manifest.decision_count,
        trader_ids=manifest.trader_ids,
        fold_ids=FOLDS,
        qualification_status="PASS",
        ready_for_scientific_reentry=True,
        exact_candidate_binding=True,
        exact_execution_identity_binding=True,
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


def _dependency():
    manifest = _manifest()
    receipt = A1HistoricalCompoundLineageReceipt(
        contract_id=CONTRACT_ID,
        source_workstream="COMPOUND_ENGINE",
        source_head="b" * 40,
        artifact_sha256=_sha("compound"),
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
    return admit_historical_compound_lineage_for_a1(
        manifest=manifest,
        canonical_bridge=_bridge(),
        a2_dependency=_a2_dependency(),
        receipt=receipt,
    )


def _observations(
    *,
    treatment_floor: Decimal = Decimal("6"),
    treatment_drawdown: Decimal = Decimal("5"),
) -> tuple[Genc2ProfitGraduationFoldObservation, ...]:
    manifest = _manifest()
    dependency = _dependency()
    result: list[Genc2ProfitGraduationFoldObservation] = []
    for fold in manifest.folds:
        common = {
            "fold_id": fold.fold_id,
            "population_sha256": fold.population_sha256,
            "compound_dependency_receipt_sha256": dependency.receipt_sha256,
            "provider_surface_sha256": _sha("provider"),
            "protocol_binding_sha256": _sha("protocol"),
            "realized_net_delta_usd": Decimal("10"),
            "ending_realized_capital_usd": Decimal("70"),
            "minimum_base_capital_usd": Decimal("60"),
            "p99_drawdown_usd": Decimal("5"),
            "peak_plausible_loss_usd": Decimal("5"),
            "provider_cost_usd": Decimal("1"),
            "provider_failure_count": 0,
            "minimum_liquid_reserve_usd": Decimal("10"),
            "minimum_optionality_usd": Decimal("10"),
            "capital_risk_time_productivity": Decimal("1"),
            "source_realized_profit_usd": Decimal("10"),
            "capital_conservation_breach_count": 0,
            "causal_effect_identified": True,
            "treatment_preregistered_before_outcomes": True,
        }
        result.append(
            Genc2ProfitGraduationFoldObservation(
                candidate_id="control",
                role=Genc2EconomicRole.CONTROL,
                ending_protected_floor_usd=Decimal("5"),
                maximum_drawdown_usd=Decimal("5"),
                graduated_realized_profit_usd=Decimal("0"),
                **common,
            )
        )
        result.append(
            Genc2ProfitGraduationFoldObservation(
                candidate_id="treatment",
                role=Genc2EconomicRole.TREATMENT,
                ending_protected_floor_usd=treatment_floor,
                maximum_drawdown_usd=treatment_drawdown,
                graduated_realized_profit_usd=Decimal("2"),
                **common,
            )
        )
    return tuple(result)


def test_genc2_phase22_profit_graduation_passes_strict_four_of_four() -> None:
    report = evaluate_genc2_phase22_profit_graduation(
        manifest=_manifest(),
        compound_dependency=_dependency(),
        observations=_observations(),
    )

    treatment = next(
        item for item in report.verdicts if item.candidate_id == "treatment"
    )
    assert treatment.status is Genc2EconomicStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert treatment.passed_fold_ids == FOLDS
    assert report.certification_ready is False


def test_genc2_rejects_safety_deterioration_noncompensatorily() -> None:
    report = evaluate_genc2_phase22_profit_graduation(
        manifest=_manifest(),
        compound_dependency=_dependency(),
        observations=_observations(treatment_drawdown=Decimal("6")),
    )

    treatment = next(
        item for item in report.verdicts if item.candidate_id == "treatment"
    )
    assert treatment.status is Genc2EconomicStatus.REJECTED_SAFETY_DETERIORATION
    assert treatment.failed_fold_ids == FOLDS


def test_genc2_rejects_population_drift() -> None:
    observations = list(_observations())
    observations[0] = replace(
        observations[0],
        population_sha256=_sha("wrong"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="differs from Phase22 fold",
    ):
        evaluate_genc2_phase22_profit_graduation(
            manifest=_manifest(),
            compound_dependency=_dependency(),
            observations=tuple(observations),
        )


def test_genc2_rejects_floating_pnl_as_capital() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="governance/causal drift",
    ):
        replace(
            _observations()[1],
            floating_pnl_used_as_capital=True,
        )


def test_genc2_rejects_graduating_more_than_realized_profit() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="more than realized source profit",
    ):
        replace(
            _observations()[1],
            graduated_realized_profit_usd=Decimal("11"),
        )
