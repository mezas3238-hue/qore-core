from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.cibo_genc9_economic_gate import (
    GENC9_ECONOMIC_GATE_SHA256,
    Genc9EconomicGateStatus,
    evaluate_genc9_economic_gate,
)
from qore.infrastructure.cibo_robust_growth_ruin_capacity import (
    Genc9CandidateRole,
    Genc9CandidateSummary,
    Genc9GrowthFamily,
    Genc9Numeraire,
    Genc9ResearchReport,
)


def _summary(
    *,
    candidate_id: str,
    role: Genc9CandidateRole,
    median: str,
    p99_dd: str = "5",
    max_dd: str = "6",
    peak_loss: str = "4",
    minimum_capital: str = "90",
    min_ending: str = "105",
    min_multiple: str = "1.05",
    median_multiple: str = "1.10",
    return_per_loss: str = "1.2",
    ruins: int = 0,
    breaches: int = 0,
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
        minimum_ending_capital=Decimal(min_ending),
        median_ending_capital=Decimal(median),
        minimum_ending_multiple=Decimal(min_multiple),
        median_ending_multiple=Decimal(median_multiple),
        p95_max_drawdown=Decimal(p99_dd),
        p99_max_drawdown=Decimal(p99_dd),
        maximum_drawdown=Decimal(max_dd),
        maximum_time_underwater_minutes=Decimal("100"),
        p95_recovery_minutes=Decimal("50"),
        ruin_path_count=ruins,
        empirical_scenario_ruin_frequency=Decimal(ruins) / Decimal(2),
        capacity_breach_path_count=breaches,
        empirical_capacity_breach_frequency=Decimal(breaches) / Decimal(2),
        positive_ending_delta_paths=2,
        minimum_realized_capital=Decimal(minimum_capital),
        maximum_peak_plausible_loss=Decimal(peak_loss),
        minimum_return_per_peak_plausible_loss=Decimal(return_per_loss),
        empirical_frequency_is_market_probability=False,
        economic_value_demonstrated=False,
        certification_ready=False,
    )


def _report(treatment: Genc9CandidateSummary) -> Genc9ResearchReport:
    control = _summary(
        candidate_id="control",
        role=Genc9CandidateRole.CONTROL,
        median="110",
    )
    return Genc9ResearchReport(
        research_id="genc9-gate-test",
        control_candidate_id="control",
        numeraire=Genc9Numeraire.PROVIDER_VALID_USD,
        scenario_ids=("a", "b"),
        summaries=(control, treatment),
    )


def test_genc9_economic_gate_digest_is_frozen() -> None:
    assert GENC9_ECONOMIC_GATE_SHA256 == (
        "sha256:ab3152b1b17ec4fbc740608c46884aa482589c1ec62af92735b81e06c2763889"
    )


def test_genc9_gate_accepts_noncompensatory_strict_improvement() -> None:
    treatment = _summary(
        candidate_id="treatment",
        role=Genc9CandidateRole.TREATMENT,
        median="115",
        min_ending="106",
        min_multiple="1.06",
        median_multiple="1.15",
        return_per_loss="1.3",
    )
    result = evaluate_genc9_economic_gate(_report(treatment))
    row = result.rows[1]

    assert row.status is (
        Genc9EconomicGateStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    )
    assert row.safety_no_worse is True
    assert row.strict_growth_or_efficiency_improvement is True
    assert result.winner_candidate_id is None
    assert result.weighted_score_used is False
    assert result.production_policy_selected is False


def test_genc9_gate_rejects_more_return_with_worse_tail_dd() -> None:
    treatment = _summary(
        candidate_id="treatment",
        role=Genc9CandidateRole.TREATMENT,
        median="200",
        p99_dd="5.1",
        max_dd="6",
        min_ending="106",
        min_multiple="1.06",
        median_multiple="2",
        return_per_loss="2",
    )
    result = evaluate_genc9_economic_gate(_report(treatment))
    row = result.rows[1]

    assert row.status is (
        Genc9EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    )
    assert "p99_max_drawdown" in row.failed_dimensions


def test_genc9_gate_rejects_no_strict_economic_improvement() -> None:
    treatment = _summary(
        candidate_id="treatment",
        role=Genc9CandidateRole.TREATMENT,
        median="110",
    )
    result = evaluate_genc9_economic_gate(_report(treatment))
    row = result.rows[1]

    assert row.status is (
        Genc9EconomicGateStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
    )
    assert row.safety_no_worse is True
    assert row.strict_growth_or_efficiency_improvement is False


def test_genc9_gate_is_noncompensatory_for_ruin_and_capacity() -> None:
    treatment = _summary(
        candidate_id="treatment",
        role=Genc9CandidateRole.TREATMENT,
        median="300",
        min_ending="120",
        min_multiple="1.2",
        median_multiple="3",
        return_per_loss="3",
        ruins=1,
        breaches=1,
    )
    result = evaluate_genc9_economic_gate(_report(treatment))
    row = result.rows[1]

    assert row.status is (
        Genc9EconomicGateStatus.REJECTED_SAFETY_DETERIORATION
    )
    assert "ruin_path_count" in row.failed_dimensions
    assert "capacity_breach_path_count" in row.failed_dimensions
