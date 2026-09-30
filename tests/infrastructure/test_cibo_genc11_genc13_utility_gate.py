from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_genc11_genc13_utility_gate import (
    GATE_SHA256,
    Genc11Genc13UtilityInput,
    Genc11Genc13Workstream,
    evaluate_genc11_genc13_utility,
)
from qore.infrastructure.cibo_genc9_economic_gate import Genc9EconomicGateStatus
from qore.infrastructure.cibo_robust_growth_ruin_capacity import (
    Genc9CandidateRole,
    Genc9CandidateSummary,
    Genc9GrowthFamily,
    Genc9Numeraire,
    Genc9ResearchReport,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _summary(
    *,
    candidate_id: str,
    role: Genc9CandidateRole,
    median: str,
    p99_dd: str = "5",
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
        p95_max_drawdown=Decimal(p99_dd),
        p99_max_drawdown=Decimal(p99_dd),
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


def _report(*, worse_tail: bool = False) -> Genc9ResearchReport:
    control = _summary(
        candidate_id="control",
        role=Genc9CandidateRole.CONTROL,
        median="110",
    )
    treatment = _summary(
        candidate_id="treatment",
        role=Genc9CandidateRole.TREATMENT,
        median="115",
        p99_dd="5.1" if worse_tail else "5",
    )
    return Genc9ResearchReport(
        research_id="genc11-13-wrapper-test",
        control_candidate_id="control",
        numeraire=Genc9Numeraire.PROVIDER_VALID_USD,
        scenario_ids=("a", "b"),
        summaries=(control, treatment),
    )


def _input(
    workstream: Genc11Genc13Workstream,
    *,
    worse_tail: bool = False,
) -> Genc11Genc13UtilityInput:
    common = dict(
        evaluation_id=f"{workstream.value}-evaluation",
        workstream=workstream,
        control_candidate_id="control",
        treatment_candidate_id="treatment",
        population_sha256=_sha("1"),
        provider_surface_sha256=_sha("2"),
        protocol_binding_sha256=_sha("3"),
        research_report=_report(worse_tail=worse_tail),
        causal_effect_identified=True,
        treatment_preregistered_before_outcomes=True,
        temporal_separation_proven=True,
    )
    if workstream is Genc11Genc13Workstream.GENC11:
        return Genc11Genc13UtilityInput(
            **common,
            transition_uncertainty_calibrated=True,
            transition_calibration_sha256=_sha("4"),
        )
    return Genc11Genc13UtilityInput(
        **common,
        prospective_memory_use_ablation=True,
        memory_hypothesis_sha256=_sha("5"),
    )


def test_wrapper_digest_is_frozen() -> None:
    assert GATE_SHA256 == (
        "sha256:97f9b42b8843d5aa1483a387c8df87dff7f3c5e9"
        "7206c98970673769bcc7e9d7"
    )


@pytest.mark.parametrize("workstream", tuple(Genc11Genc13Workstream))
def test_wrapper_reuses_genc9_noncompensatory_law(
    workstream: Genc11Genc13Workstream,
) -> None:
    report = evaluate_genc11_genc13_utility(_input(workstream))

    assert (
        report.status
        is Genc9EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    )
    assert report.research_eligible is True
    assert report.temporal_replication_claimed is False
    assert report.stress_pass_claimed is False
    assert report.productive_authority is False
    assert report.certification_ready is False


def test_wrapper_preserves_noncompensatory_tail_rejection() -> None:
    report = evaluate_genc11_genc13_utility(
        _input(Genc11Genc13Workstream.GENC11, worse_tail=True)
    )

    assert (
        report.status
        is Genc9EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    )
    assert report.research_eligible is False
    assert "p99_max_drawdown" in report.failed_dimensions


def test_genc11_requires_transition_calibration() -> None:
    evidence = _input(Genc11Genc13Workstream.GENC11)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires calibrated GEN-C10 transition evidence",
    ):
        replace(
            evidence,
            transition_uncertainty_calibrated=False,
            transition_calibration_sha256=None,
        )


def test_genc13_requires_prospective_memory_ablation() -> None:
    evidence = _input(Genc11Genc13Workstream.GENC13)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires prospective memory-use ablation",
    ):
        replace(
            evidence,
            prospective_memory_use_ablation=False,
            memory_hypothesis_sha256=None,
        )


def test_genc13_cannot_upgrade_retrospective_counterfactual() -> None:
    evidence = _input(Genc11Genc13Workstream.GENC13)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="governance/causal drift",
    ):
        replace(
            evidence,
            retrospective_counterfactual_used_as_causal=True,
        )


def test_wrapper_rejects_report_candidate_identity_drift() -> None:
    evidence = _input(Genc11Genc13Workstream.GENC11)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="candidate identity drift",
    ):
        replace(evidence, treatment_candidate_id="other")
