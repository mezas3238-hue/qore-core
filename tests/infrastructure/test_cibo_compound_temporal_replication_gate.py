from __future__ import annotations

from dataclasses import replace

import pytest

from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_compound_temporal_replication_gate import (
    CompoundTemporalEconomicFoldEvidence,
    CompoundTemporalEconomicVerdict,
    evaluate_compound_temporal_economic_replication,
)
from qore.infrastructure.cibo_genc9_economic_gate import (
    GENC9_ECONOMIC_GATE_FROZEN_AT,
    GENC9_ECONOMIC_GATE_ID,
    GENC9_ECONOMIC_GATE_SHA256,
    Genc9EconomicGateReport,
    Genc9EconomicGateRow,
    Genc9EconomicGateStatus,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _report(
    fold_id: str,
    *,
    treatment_status: Genc9EconomicGateStatus = (
        Genc9EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    ),
    safety_no_worse: bool = True,
    strict_improvement: bool = True,
    failed_dimensions: tuple[str, ...] = (),
    control_id: str = "control-v1",
) -> Genc9EconomicGateReport:
    return Genc9EconomicGateReport(
        research_id=f"research-{fold_id}",
        gate_id=GENC9_ECONOMIC_GATE_ID,
        gate_sha256=GENC9_ECONOMIC_GATE_SHA256,
        gate_frozen_at=GENC9_ECONOMIC_GATE_FROZEN_AT,
        control_candidate_id=control_id,
        rows=(
            Genc9EconomicGateRow(
                candidate_id=control_id,
                status=Genc9EconomicGateStatus.CONTROL,
                safety_no_worse=True,
                strict_growth_or_efficiency_improvement=False,
                failed_dimensions=(),
            ),
            Genc9EconomicGateRow(
                candidate_id="treatment-v1",
                status=treatment_status,
                safety_no_worse=safety_no_worse,
                strict_growth_or_efficiency_improvement=strict_improvement,
                failed_dimensions=failed_dimensions,
            ),
        ),
    )


def _fold(
    index: int,
    *,
    report: Genc9EconomicGateReport | None = None,
) -> CompoundTemporalEconomicFoldEvidence:
    fold_id = f"WF{index}"
    return CompoundTemporalEconomicFoldEvidence(
        fold_id=fold_id,
        gate_report=report or _report(fold_id),
        source_population_sha256=_sha(str(index)),
        provider_economics_sha256=_sha(str(index + 4)),
        forward_observed=True,
    )


def test_temporal_replication_requires_noncompensatory_pass_in_all_folds() -> None:
    result = evaluate_compound_temporal_economic_replication(
        treatment_candidate_id="treatment-v1",
        folds=(_fold(1), _fold(2), _fold(3), _fold(4)),
    )

    assert result.verdict is CompoundTemporalEconomicVerdict.REPLICATED
    assert tuple(item.fold_id for item in result.fold_results) == (
        "WF1",
        "WF2",
        "WF3",
        "WF4",
    )
    assert all(item.passed for item in result.fold_results)
    assert result.weighted_score_used is False
    assert result.outcomes_pooled_across_folds is False
    assert result.production_policy_selected is False
    assert result.certification_ready is False


def test_temporal_replication_falsifies_when_one_fold_fails_safety() -> None:
    bad = _report(
        "WF3",
        treatment_status=Genc9EconomicGateStatus.REJECTED_SAFETY_DETERIORATION,
        safety_no_worse=False,
        strict_improvement=True,
        failed_dimensions=("p99_max_drawdown",),
    )

    result = evaluate_compound_temporal_economic_replication(
        treatment_candidate_id="treatment-v1",
        folds=(_fold(1), _fold(2), _fold(3, report=bad), _fold(4)),
    )

    assert result.verdict is CompoundTemporalEconomicVerdict.FALSIFIED
    assert result.fold_results[2].passed is False
    assert result.fold_results[2].failed_dimensions == ("p99_max_drawdown",)


def test_temporal_replication_rejects_missing_fold() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires exactly WF1..WF4",
    ):
        evaluate_compound_temporal_economic_replication(
            treatment_candidate_id="treatment-v1",
            folds=(_fold(1), _fold(2), _fold(3)),
        )


def test_temporal_replication_rejects_pooled_outcomes() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires unpooled forward evidence",
    ):
        replace(_fold(1), outcomes_pooled=True)


def test_temporal_replication_rejects_non_forward_evidence() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires unpooled forward evidence",
    ):
        replace(_fold(1), forward_observed=False)


def test_temporal_replication_rejects_control_drift() -> None:
    drifted = _fold(
        4,
        report=_report("WF4", control_id="different-control"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="control identity drift",
    ):
        evaluate_compound_temporal_economic_replication(
            treatment_candidate_id="treatment-v1",
            folds=(_fold(1), _fold(2), _fold(3), drifted),
        )
