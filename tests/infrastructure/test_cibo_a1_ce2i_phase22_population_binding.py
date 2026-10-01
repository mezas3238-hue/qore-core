from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_a1_ce2i_phase22_population_binding import (
    bind_t04_t10_to_phase22,
    bind_t06_t07_temporal_to_phase22,
    bind_t14_t15_temporal_to_phase22,
)
from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    MANIFEST_ID,
    A1Phase22PopulationFold,
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_ce2i_t04_t10_economic_gate import (
    Ce2iT04T10FoldObservation,
    Ce2iT04T10Role,
    Ce2iT04T10Tool,
)
from qore.infrastructure.cibo_ce2i_temporal_utility_replication import (
    CausalParetoTemporalFoldEvidence,
    ExpansionTemporalFoldEvidence,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_expansion_utility_gate import (
    EXPANSION_UTILITY_GATE_ID,
    ExpansionUtilityGateReport,
    ExpansionUtilityGateRow,
    ExpansionUtilityKind,
    ExpansionUtilityStatus,
)
from qore.infrastructure.cibo_t14_t15_utility_gate import (
    T14_T15_UTILITY_GATE_ID,
    T14T15UtilityGateReport,
    T14T15UtilityGateRow,
    T14T15UtilityKind,
    T14T15UtilityStatus,
)

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
        parameter_sha256=_sha("parameters"),
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


def _t04_observations() -> tuple[Ce2iT04T10FoldObservation, ...]:
    result: list[Ce2iT04T10FoldObservation] = []
    for fold in _manifest().folds:
        common = {
            "tool": Ce2iT04T10Tool.T04,
            "fold_id": fold.fold_id,
            "population_sha256": fold.population_sha256,
            "strategy_surface_sha256": _sha("strategy"),
            "provider_surface_sha256": _sha("provider"),
            "risk_boundary_sha256": _sha("risk"),
            "capital_truth_sha256": _sha("capital"),
            "causal_horizon_sha256": _sha(f"horizon-{fold.fold_id}"),
            "protocol_binding_sha256": _sha("protocol"),
            "maximum_drawdown_usd": Decimal("5"),
            "p99_drawdown_usd": Decimal("5"),
            "peak_plausible_loss_usd": Decimal("5"),
            "peak_margin_occupancy_usd": Decimal("5"),
            "provider_cost_usd": Decimal("1"),
            "provider_failure_count": 0,
            "capital_conservation_breach_count": 0,
            "minimum_realized_capital_usd": Decimal("60"),
            "minimum_liquid_reserve_usd": Decimal("10"),
            "minimum_optionality_usd": Decimal("10"),
            "p95_recovery_minutes": Decimal("5"),
            "true_stop_risk_usd": Decimal("5"),
            "capital_minutes": Decimal("10"),
            "causal_effect_identified": True,
            "treatment_preregistered_before_outcomes": True,
            "provider_economics_complete": True,
            "outcome_coverage_complete": True,
        }
        result.append(
            Ce2iT04T10FoldObservation(
                candidate_id="control",
                role=Ce2iT04T10Role.CONTROL,
                realized_net_delta_usd=Decimal("10"),
                capital_risk_time_productivity=Decimal("1"),
                realized_output_per_true_stop_risk=Decimal("2"),
                realized_output_per_capital_minute=Decimal("1"),
                **common,
            )
        )
        result.append(
            Ce2iT04T10FoldObservation(
                candidate_id="treatment",
                role=Ce2iT04T10Role.TREATMENT,
                realized_net_delta_usd=Decimal("11"),
                capital_risk_time_productivity=Decimal("2"),
                realized_output_per_true_stop_risk=Decimal("2.2"),
                realized_output_per_capital_minute=Decimal("1.1"),
                **common,
            )
        )
    return tuple(result)


def _expansion_folds() -> tuple[ExpansionTemporalFoldEvidence, ...]:
    result: list[ExpansionTemporalFoldEvidence] = []
    for fold in _manifest().folds:
        report = ExpansionUtilityGateReport(
            gate_id=EXPANSION_UTILITY_GATE_ID,
            kind=ExpansionUtilityKind.T06_PROFIT_FUNDED,
            control_candidate_id="control",
            population_sha256=fold.population_sha256,
            provider_economics_sha256=_sha("provider"),
            rows=(
                ExpansionUtilityGateRow(
                    candidate_id="control",
                    status=ExpansionUtilityStatus.CONTROL,
                    safety_no_worse=True,
                    strict_economic_improvement=False,
                    failed_dimensions=(),
                ),
                ExpansionUtilityGateRow(
                    candidate_id="treatment",
                    status=ExpansionUtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
                    safety_no_worse=True,
                    strict_economic_improvement=True,
                    failed_dimensions=(),
                ),
            ),
        )
        result.append(
            ExpansionTemporalFoldEvidence(
                fold_id=fold.fold_id,
                gate_report=report,
                protocol_binding_sha256=_sha("protocol"),
            )
        )
    return tuple(result)


def _pareto_folds() -> tuple[CausalParetoTemporalFoldEvidence, ...]:
    result: list[CausalParetoTemporalFoldEvidence] = []
    for fold in _manifest().folds:
        report = T14T15UtilityGateReport(
            gate_id=T14_T15_UTILITY_GATE_ID,
            kind=T14T15UtilityKind.T14_DYNAMIC_DERISKING,
            control_candidate_id="control",
            population_sha256=fold.population_sha256,
            provider_economics_sha256=_sha("provider"),
            causal_horizon_sha256=_sha(f"horizon-{fold.fold_id}"),
            rows=(
                T14T15UtilityGateRow(
                    candidate_id="control",
                    status=T14T15UtilityStatus.CONTROL,
                    causal_identification_pass=True,
                    governance_pass=True,
                    pareto_no_worse=True,
                    strict_utility_improvement=False,
                    failed_dimensions=(),
                ),
                T14T15UtilityGateRow(
                    candidate_id="treatment",
                    status=T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH,
                    causal_identification_pass=True,
                    governance_pass=True,
                    pareto_no_worse=True,
                    strict_utility_improvement=True,
                    failed_dimensions=(),
                ),
            ),
        )
        result.append(
            CausalParetoTemporalFoldEvidence(
                fold_id=fold.fold_id,
                gate_report=report,
                protocol_binding_sha256=_sha("protocol"),
            )
        )
    return tuple(result)


def test_t04_t10_gate_binds_exact_phase22_populations() -> None:
    report = bind_t04_t10_to_phase22(
        manifest=_manifest(),
        observations=_t04_observations(),
    )

    assert report.exact_fold_population_binding is True
    assert report.certification_ready is False


def test_t04_t10_binding_rejects_fold_population_drift() -> None:
    observations = list(_t04_observations())
    observations[0] = replace(
        observations[0],
        population_sha256=_sha("wrong"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="differs from Phase22 fold",
    ):
        bind_t04_t10_to_phase22(
            manifest=_manifest(),
            observations=tuple(observations),
        )


def test_t06_t07_replication_binds_phase22_wf1_wf4() -> None:
    report = bind_t06_t07_temporal_to_phase22(
        manifest=_manifest(),
        treatment_candidate_id="treatment",
        folds=_expansion_folds(),
    )

    assert report.family == "T06_T07"
    assert report.exact_fold_population_binding is True


def test_t14_t15_replication_binds_phase22_wf1_wf4() -> None:
    report = bind_t14_t15_temporal_to_phase22(
        manifest=_manifest(),
        treatment_candidate_id="treatment",
        folds=_pareto_folds(),
    )

    assert report.family == "T14_T15"
    assert report.exact_fold_population_binding is True


def test_t14_t15_binding_rejects_noncanonical_fold_population() -> None:
    folds = list(_pareto_folds())
    bad_report = replace(
        folds[2].gate_report,
        population_sha256=_sha("wrong"),
    )
    folds[2] = replace(folds[2], gate_report=bad_report)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="differs from canonical Phase22 fold",
    ):
        bind_t14_t15_temporal_to_phase22(
            manifest=_manifest(),
            treatment_candidate_id="treatment",
            folds=tuple(folds),
        )
