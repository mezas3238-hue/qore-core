from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_adaptive_compound_speed_economic_gate import (
    Genc8EconomicObservation,
    Genc8EconomicRole,
)
from qore.infrastructure.cibo_adaptive_compound_speed_shadow import (
    genc8_policy_sha256,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_genc11_genc13_utility_gate import (
    Genc11Genc13UtilityInput,
    Genc11Genc13Workstream,
)
from qore.infrastructure.cibo_genc12_economic_gate import (
    Genc12CrisisEconomicObservation,
    Genc12EconomicRole,
)
from qore.infrastructure.cibo_genc_strict_temporal_replication import (
    Genc11Genc13TemporalFoldEvidence,
    Genc12TemporalFoldEvidence,
    Genc7TemporalFoldEvidence,
    Genc8TemporalFoldEvidence,
    GencTemporalReplicationVerdict,
    evaluate_genc11_genc13_temporal_replication,
    evaluate_genc12_temporal_replication,
    evaluate_genc7_temporal_replication,
    evaluate_genc8_temporal_replication,
)
from qore.infrastructure.cibo_profit_preservation_economic_gate import (
    Genc7CausalEconomicObservation,
    Genc7EconomicRole,
)
from qore.infrastructure.cibo_profit_preservation_shadow import (
    Genc7Action,
    genc7_policy_sha256,
)
from qore.infrastructure.cibo_robust_growth_ruin_capacity import (
    Genc9CandidateRole,
    Genc9CandidateSummary,
    Genc9GrowthFamily,
    Genc9Numeraire,
    Genc9ResearchReport,
)

FOLDS = ("WF1", "WF2", "WF3", "WF4")
START = datetime(2026, 9, 30, 12, tzinfo=UTC)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _genc7_observation(
    *,
    fold_id: str,
    population: str,
    candidate_id: str,
    role: Genc7EconomicRole,
    action: Genc7Action,
    floor: str = "20",
) -> Genc7CausalEconomicObservation:
    return Genc7CausalEconomicObservation(
        candidate_id=candidate_id,
        role=role,
        action=action,
        policy_sha256=genc7_policy_sha256(),
        population_sha256=_sha(population),
        provider_surface_sha256=_sha("a"),
        fold_ids=(fold_id,),
        horizon_start=START,
        horizon_end=START + timedelta(hours=1),
        realized_capital_delta_usd=Decimal("10"),
        realized_profit_delta_usd=Decimal("8"),
        ending_protected_floor_usd=Decimal(floor),
        minimum_base_capital_usd=Decimal("90"),
        minimum_compound_capital_usd=Decimal("15"),
        maximum_drawdown_usd=Decimal("5"),
        p99_drawdown_usd=Decimal("4.5"),
        peak_plausible_loss_usd=Decimal("6"),
        provider_cost_usd=Decimal("2"),
        minimum_optionality_usd=Decimal("12"),
        profit_retention_ratio=Decimal("0.8"),
        giveback_usd=Decimal("4"),
        capital_risk_time_productivity=Decimal("1.2"),
        causal_effect_identified=True,
    )


def _genc7_folds() -> tuple[Genc7TemporalFoldEvidence, ...]:
    rows = []
    for index, fold_id in enumerate(FOLDS, start=1):
        population = str(index)
        rows.append(
            Genc7TemporalFoldEvidence(
                fold_id=fold_id,
                observations=(
                    _genc7_observation(
                        fold_id=fold_id,
                        population=population,
                        candidate_id="control",
                        role=Genc7EconomicRole.CONTROL,
                        action=Genc7Action.HOLD_CURRENT_CAPITAL_STATE,
                    ),
                    _genc7_observation(
                        fold_id=fold_id,
                        population=population,
                        candidate_id="protect",
                        role=Genc7EconomicRole.TREATMENT,
                        action=Genc7Action.PROTECT,
                        floor="25",
                    ),
                ),
            )
        )
    return tuple(rows)


def _genc8_observation(
    *,
    fold_id: str,
    population: str,
    candidate_id: str,
    role: Genc8EconomicRole,
    ending: str,
) -> Genc8EconomicObservation:
    return Genc8EconomicObservation(
        candidate_id=candidate_id,
        role=role,
        policy_sha256=genc8_policy_sha256(),
        population_sha256=_sha(population),
        provider_surface_sha256=_sha("a"),
        fold_ids=(fold_id,),
        horizon_start=START,
        horizon_end=START + timedelta(hours=1),
        ending_realized_capital_usd=Decimal(ending),
        geometric_growth_factor=Decimal("1.12" if ending == "112" else "1.10"),
        maximum_drawdown_usd=Decimal("5"),
        p95_drawdown_usd=Decimal("4"),
        p99_drawdown_usd=Decimal("4.5"),
        maximum_time_underwater_minutes=Decimal("100"),
        p95_recovery_minutes=Decimal("50"),
        capital_risk_time_productivity=Decimal("1.3" if ending == "112" else "1.2"),
        profit_retention_usd=Decimal("20"),
        minimum_liquid_reserve_usd=Decimal("15"),
        minimum_optionality_usd=Decimal("10"),
        provider_cost_usd=Decimal("2"),
        positive_tail_capture_usd=Decimal("8"),
        unnecessary_acceleration_count=2,
        over_defensive_missed_opportunity_count=3 if ending == "112" else 4,
    )


def _genc8_folds() -> tuple[Genc8TemporalFoldEvidence, ...]:
    return tuple(
        Genc8TemporalFoldEvidence(
            fold_id=fold_id,
            observations=(
                _genc8_observation(
                    fold_id=fold_id,
                    population=str(index),
                    candidate_id="control",
                    role=Genc8EconomicRole.CONTROL,
                    ending="110",
                ),
                _genc8_observation(
                    fold_id=fold_id,
                    population=str(index),
                    candidate_id="treatment",
                    role=Genc8EconomicRole.TREATMENT,
                    ending="112",
                ),
            ),
        )
        for index, fold_id in enumerate(FOLDS, start=1)
    )


def _genc12_observation(
    *,
    population: str,
    candidate_id: str,
    role: Genc12EconomicRole,
    net_delta: str,
) -> Genc12CrisisEconomicObservation:
    return Genc12CrisisEconomicObservation(
        candidate_id=candidate_id,
        role=role,
        population_sha256=_sha(population),
        provider_surface_sha256=_sha("a"),
        crisis_factor_set_sha256=_sha("b"),
        horizon_start=START,
        horizon_end=START + timedelta(hours=1),
        net_delta_usd=Decimal(net_delta),
        maximum_drawdown_usd=Decimal("5"),
        peak_plausible_loss_usd=Decimal("6"),
        peak_margin_occupancy_usd=Decimal("20"),
        capital_lockup_minutes=Decimal("90" if net_delta == "12" else "100"),
        compound_giveback_usd=Decimal("3" if net_delta == "12" else "4"),
        simultaneous_loss_cluster_count=2,
        provider_failure_incidence=Decimal("0.01"),
        minimum_realized_capital_usd=Decimal("90"),
        minimum_liquid_reserve_usd=Decimal("15"),
    )


def _genc12_folds() -> tuple[Genc12TemporalFoldEvidence, ...]:
    return tuple(
        Genc12TemporalFoldEvidence(
            fold_id=fold_id,
            observations=(
                _genc12_observation(
                    population=str(index),
                    candidate_id="control",
                    role=Genc12EconomicRole.CONTROL,
                    net_delta="10",
                ),
                _genc12_observation(
                    population=str(index),
                    candidate_id="treatment",
                    role=Genc12EconomicRole.TREATMENT,
                    net_delta="12",
                ),
            ),
        )
        for index, fold_id in enumerate(FOLDS, start=1)
    )


def _summary(
    *,
    candidate_id: str,
    role: Genc9CandidateRole,
    median: str,
) -> Genc9CandidateSummary:
    return Genc9CandidateSummary(
        candidate_id=candidate_id,
        role=role,
        family=(
            Genc9GrowthFamily.CURRENT_CONTROL
            if role is Genc9CandidateRole.CONTROL
            else Genc9GrowthFamily.DISTRIBUTIONALLY_ROBUST_GROWTH
        ),
        numeraire=Genc9Numeraire.PROVIDER_VALID_USD,
        path_count=2,
        scenario_ids=("a", "b"),
        minimum_ending_capital=Decimal("105"),
        median_ending_capital=Decimal(median),
        minimum_ending_multiple=Decimal("1.05"),
        median_ending_multiple=Decimal("1.10" if median == "110" else "1.15"),
        p95_max_drawdown=Decimal("5"),
        p99_max_drawdown=Decimal("5"),
        maximum_drawdown=Decimal("6"),
        maximum_time_underwater_minutes=Decimal("100"),
        p95_recovery_minutes=Decimal("50"),
        ruin_path_count=0,
        empirical_scenario_ruin_frequency=Decimal("0"),
        capacity_breach_path_count=0,
        empirical_capacity_breach_frequency=Decimal("0"),
        positive_ending_delta_paths=2,
        minimum_realized_capital=Decimal("90"),
        maximum_peak_plausible_loss=Decimal("4"),
        minimum_return_per_peak_plausible_loss=Decimal(
            "1.2" if median == "110" else "1.3"
        ),
        empirical_frequency_is_market_probability=False,
        economic_value_demonstrated=False,
        certification_ready=False,
    )


def _genc11_13_folds(
    workstream: Genc11Genc13Workstream,
) -> tuple[Genc11Genc13TemporalFoldEvidence, ...]:
    rows = []
    for index, fold_id in enumerate(FOLDS, start=1):
        report = Genc9ResearchReport(
            research_id=f"{workstream.value}-{fold_id}",
            control_candidate_id="control",
            numeraire=Genc9Numeraire.PROVIDER_VALID_USD,
            scenario_ids=("a", "b"),
            summaries=(
                _summary(
                    candidate_id="control",
                    role=Genc9CandidateRole.CONTROL,
                    median="110",
                ),
                _summary(
                    candidate_id="treatment",
                    role=Genc9CandidateRole.TREATMENT,
                    median="115",
                ),
            ),
        )
        common = dict(
            evaluation_id=f"{workstream.value}-{fold_id}",
            workstream=workstream,
            control_candidate_id="control",
            treatment_candidate_id="treatment",
            population_sha256=_sha(str(index)),
            provider_surface_sha256=_sha("a"),
            protocol_binding_sha256=_sha("c"),
            research_report=report,
            causal_effect_identified=True,
            treatment_preregistered_before_outcomes=True,
            temporal_separation_proven=True,
        )
        if workstream is Genc11Genc13Workstream.GENC11:
            evidence = Genc11Genc13UtilityInput(
                **common,
                transition_uncertainty_calibrated=True,
                transition_calibration_sha256=_sha("d"),
            )
        else:
            evidence = Genc11Genc13UtilityInput(
                **common,
                prospective_memory_use_ablation=True,
                memory_hypothesis_sha256=_sha("e"),
            )
        rows.append(
            Genc11Genc13TemporalFoldEvidence(
                fold_id=fold_id,
                evidence=evidence,
            )
        )
    return tuple(rows)


def test_genc7_strict_four_fold_replication() -> None:
    report = evaluate_genc7_temporal_replication(
        treatment_candidate_id="protect",
        folds=_genc7_folds(),
    )
    assert report.verdict is GencTemporalReplicationVerdict.REPLICATED


def test_genc8_strict_four_fold_replication() -> None:
    report = evaluate_genc8_temporal_replication(
        treatment_candidate_id="treatment",
        folds=_genc8_folds(),
    )
    assert report.verdict is GencTemporalReplicationVerdict.REPLICATED


def test_genc12_strict_four_fold_replication() -> None:
    report = evaluate_genc12_temporal_replication(
        treatment_candidate_id="treatment",
        folds=_genc12_folds(),
    )
    assert report.verdict is GencTemporalReplicationVerdict.REPLICATED


def test_genc11_strict_four_fold_replication() -> None:
    report = evaluate_genc11_genc13_temporal_replication(
        _genc11_13_folds(Genc11Genc13Workstream.GENC11)
    )
    assert report.verdict is GencTemporalReplicationVerdict.REPLICATED
    assert report.workstream == "GEN-C11"


def test_genc13_strict_four_fold_replication() -> None:
    report = evaluate_genc11_genc13_temporal_replication(
        _genc11_13_folds(Genc11Genc13Workstream.GENC13)
    )
    assert report.verdict is GencTemporalReplicationVerdict.REPLICATED
    assert report.workstream == "GEN-C13"


def test_genc7_one_failed_fold_falsifies_replication() -> None:
    folds = list(_genc7_folds())
    failed = Genc7TemporalFoldEvidence(
        fold_id="WF3",
        observations=(
            _genc7_observation(
                fold_id="WF3",
                population="3",
                candidate_id="control",
                role=Genc7EconomicRole.CONTROL,
                action=Genc7Action.HOLD_CURRENT_CAPITAL_STATE,
            ),
            _genc7_observation(
                fold_id="WF3",
                population="3",
                candidate_id="protect",
                role=Genc7EconomicRole.TREATMENT,
                action=Genc7Action.PROTECT,
                floor="20",
            ),
        ),
    )
    folds[2] = failed

    report = evaluate_genc7_temporal_replication(
        treatment_candidate_id="protect",
        folds=tuple(folds),
    )

    assert report.verdict is GencTemporalReplicationVerdict.FALSIFIED
    assert report.fold_results[2].passed is False


def test_genc11_rejects_protocol_drift_between_folds() -> None:
    folds = list(_genc11_13_folds(Genc11Genc13Workstream.GENC11))
    folds[1] = replace(
        folds[1],
        evidence=replace(
            folds[1].evidence,
            protocol_binding_sha256=_sha("f"),
        ),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="treatment/control/protocol drift",
    ):
        evaluate_genc11_genc13_temporal_replication(tuple(folds))
