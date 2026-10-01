from __future__ import annotations

from dataclasses import replace

import pytest

from qore.infrastructure.cibo_ce2i_temporal_utility_replication import (
    CausalParetoTemporalFoldEvidence,
    Ce2iTemporalReplicationVerdict,
    ExpansionTemporalFoldEvidence,
    evaluate_expansion_temporal_replication,
    evaluate_t14_t15_temporal_replication,
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

FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _expansion_report(
    fold_index: int,
    *,
    treatment_status: ExpansionUtilityStatus = (
        ExpansionUtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    ),
) -> ExpansionUtilityGateReport:
    return ExpansionUtilityGateReport(
        gate_id=EXPANSION_UTILITY_GATE_ID,
        kind=ExpansionUtilityKind.T06_PROFIT_FUNDED,
        control_candidate_id="control",
        population_sha256=_sha(str(fold_index + 1)),
        provider_economics_sha256=_sha("a"),
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
                status=treatment_status,
                safety_no_worse=(
                    treatment_status
                    is not ExpansionUtilityStatus.REJECTED_SAFETY_DETERIORATION
                ),
                strict_economic_improvement=(
                    treatment_status
                    is ExpansionUtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
                ),
                failed_dimensions=(
                    ("TEST_FAILURE",)
                    if treatment_status
                    is ExpansionUtilityStatus.REJECTED_SAFETY_DETERIORATION
                    else ()
                ),
            ),
        ),
    )


def _pareto_report(
    fold_index: int,
    *,
    treatment_status: T14T15UtilityStatus = (
        T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    ),
) -> T14T15UtilityGateReport:
    return T14T15UtilityGateReport(
        gate_id=T14_T15_UTILITY_GATE_ID,
        kind=T14T15UtilityKind.T14_DYNAMIC_DERISKING,
        control_candidate_id="control",
        population_sha256=_sha(str(fold_index + 1)),
        provider_economics_sha256=_sha("b"),
        causal_horizon_sha256=_sha("c"),
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
                status=treatment_status,
                causal_identification_pass=True,
                governance_pass=True,
                pareto_no_worse=(
                    treatment_status
                    is not T14T15UtilityStatus.REJECTED_PARETO_DETERIORATION
                ),
                strict_utility_improvement=(
                    treatment_status
                    is T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
                ),
                failed_dimensions=(
                    ()
                    if treatment_status
                    is T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
                    else ("TEST_FAILURE",)
                ),
            ),
        ),
    )


def _expansion_folds() -> tuple[ExpansionTemporalFoldEvidence, ...]:
    return tuple(
        ExpansionTemporalFoldEvidence(
            fold_id=fold_id,
            gate_report=_expansion_report(index),
            protocol_binding_sha256=_sha("f"),
        )
        for index, fold_id in enumerate(FOLDS)
    )


def _pareto_folds() -> tuple[CausalParetoTemporalFoldEvidence, ...]:
    return tuple(
        CausalParetoTemporalFoldEvidence(
            fold_id=fold_id,
            gate_report=_pareto_report(index),
            protocol_binding_sha256=_sha("e"),
        )
        for index, fold_id in enumerate(FOLDS)
    )


def test_expansion_requires_strict_four_of_four() -> None:
    report = evaluate_expansion_temporal_replication(
        treatment_candidate_id="treatment",
        folds=_expansion_folds(),
    )

    assert report.verdict is Ce2iTemporalReplicationVerdict.REPLICATED
    assert tuple(item.fold_id for item in report.fold_results) == FOLDS
    assert all(item.passed for item in report.fold_results)
    assert report.certification_ready is False


def test_one_failed_expansion_fold_falsifies_replication() -> None:
    folds = list(_expansion_folds())
    folds[2] = replace(
        folds[2],
        gate_report=_expansion_report(
            2,
            treatment_status=(
                ExpansionUtilityStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
            ),
        ),
    )

    report = evaluate_expansion_temporal_replication(
        treatment_candidate_id="treatment",
        folds=tuple(folds),
    )

    assert report.verdict is Ce2iTemporalReplicationVerdict.FALSIFIED
    assert report.fold_results[2].passed is False


def test_expansion_rejects_reused_fold_population() -> None:
    folds = list(_expansion_folds())
    folds[3] = replace(
        folds[3],
        gate_report=replace(
            folds[3].gate_report,
            population_sha256=folds[0].gate_report.population_sha256,
        ),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="four distinct fold populations",
    ):
        evaluate_expansion_temporal_replication(
            treatment_candidate_id="treatment",
            folds=tuple(folds),
        )


def test_expansion_rejects_protocol_retune_between_folds() -> None:
    folds = list(_expansion_folds())
    folds[1] = replace(folds[1], protocol_binding_sha256=_sha("d"))

    with pytest.raises(
        CiboCompoundCapitalError,
        match="protocol binding drift",
    ):
        evaluate_expansion_temporal_replication(
            treatment_candidate_id="treatment",
            folds=tuple(folds),
        )


def test_t14_t15_requires_strict_four_of_four() -> None:
    report = evaluate_t14_t15_temporal_replication(
        treatment_candidate_id="treatment",
        folds=_pareto_folds(),
    )

    assert report.verdict is Ce2iTemporalReplicationVerdict.REPLICATED
    assert all(item.passed for item in report.fold_results)
    assert report.productive_authority is False


def test_t14_t15_rejects_missing_fold() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires exactly WF1..WF4",
    ):
        evaluate_t14_t15_temporal_replication(
            treatment_candidate_id="treatment",
            folds=_pareto_folds()[:3],
        )


def test_t14_t15_one_failed_fold_falsifies_replication() -> None:
    folds = list(_pareto_folds())
    folds[3] = replace(
        folds[3],
        gate_report=_pareto_report(
            3,
            treatment_status=T14T15UtilityStatus.REJECTED_PARETO_DETERIORATION,
        ),
    )

    report = evaluate_t14_t15_temporal_replication(
        treatment_candidate_id="treatment",
        folds=tuple(folds),
    )

    assert report.verdict is Ce2iTemporalReplicationVerdict.FALSIFIED
    assert report.fold_results[3].passed is False
