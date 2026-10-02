from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_robust_growth_ruin_capacity import (
    Genc9CandidateDefinition,
    Genc9CandidateRole,
    Genc9GrowthFamily,
    Genc9ModelRiskDimension,
    Genc9ModelRiskEvidence,
    Genc9ModelRiskStatus,
    Genc9Numeraire,
    Genc9PathEvidence,
    Genc9ScenarioDefinition,
    evaluate_genc9_robust_growth,
)

T0 = datetime(2026, 9, 30, 5, 0, tzinfo=UTC)


def _risks() -> tuple[Genc9ModelRiskEvidence, ...]:
    return tuple(
        Genc9ModelRiskEvidence(
            dimension=dimension,
            status=Genc9ModelRiskStatus.EVIDENCED,
            evidence_sha256=(
                "sha256:"
                + format(index + 1, "x") * 64
            )[:71],
        )
        for index, dimension in enumerate(Genc9ModelRiskDimension)
    )


def _scenario(name: str, digit: str) -> Genc9ScenarioDefinition:
    return Genc9ScenarioDefinition(
        scenario_id=name,
        scenario_evidence_sha256="sha256:" + digit * 64,
        model_risks=_risks(),
    )


def _candidate(
    candidate_id: str,
    *,
    control: bool,
    digit: str,
) -> Genc9CandidateDefinition:
    return Genc9CandidateDefinition(
        candidate_id=candidate_id,
        role=(
            Genc9CandidateRole.CONTROL
            if control
            else Genc9CandidateRole.TREATMENT
        ),
        family=(
            Genc9GrowthFamily.CURRENT_CONTROL
            if control
            else Genc9GrowthFamily.DRAWDOWN_CONSTRAINED_GROWTH
        ),
        parameterization_sha256="sha256:" + digit * 64,
        preregistered_at=T0,
    )


def _path(
    candidate_id: str,
    scenario: Genc9ScenarioDefinition,
    *,
    ending: str,
    minimum: str,
    drawdown: str,
    underwater: str,
    recovery: str,
    peak_loss: str,
    capacity_breach: bool = False,
) -> Genc9PathEvidence:
    minimum_value = Decimal(minimum)
    return Genc9PathEvidence(
        candidate_id=candidate_id,
        scenario_id=scenario.scenario_id,
        evaluated_at=T0 + timedelta(minutes=1),
        numeraire=Genc9Numeraire.NORMALIZED_CAPITAL_UNITS,
        initial_capital=Decimal("100"),
        ending_capital=Decimal(ending),
        minimum_capital=minimum_value,
        max_drawdown=Decimal(drawdown),
        max_time_underwater_minutes=Decimal(underwater),
        max_recovery_minutes=Decimal(recovery),
        peak_plausible_loss=Decimal(peak_loss),
        ruin_boundary=Decimal("20"),
        ruin_occurred=minimum_value <= Decimal("20"),
        capacity_breach=capacity_breach,
        horizon_minutes=Decimal("10000"),
        scenario_evidence_sha256=scenario.scenario_evidence_sha256,
        causal_replay_sha256="sha256:" + "c" * 64,
    )


def _fixture():
    scenarios = (
        _scenario("continuation", "1"),
        _scenario("losses-first", "2"),
        _scenario("fat-tail", "3"),
        _scenario("regime-shift", "4"),
    )
    candidates = (
        _candidate("control", control=True, digit="5"),
        _candidate("treatment", control=False, digit="6"),
    )
    control_rows = (
        _path(
            "control",
            scenarios[0],
            ending="120",
            minimum="80",
            drawdown="20",
            underwater="200",
            recovery="180",
            peak_loss="12",
        ),
        _path(
            "control",
            scenarios[1],
            ending="105",
            minimum="60",
            drawdown="40",
            underwater="500",
            recovery="450",
            peak_loss="20",
        ),
        _path(
            "control",
            scenarios[2],
            ending="80",
            minimum="15",
            drawdown="85",
            underwater="800",
            recovery="700",
            peak_loss="30",
            capacity_breach=True,
        ),
        _path(
            "control",
            scenarios[3],
            ending="110",
            minimum="55",
            drawdown="45",
            underwater="600",
            recovery="550",
            peak_loss="22",
        ),
    )
    treatment_rows = (
        _path(
            "treatment",
            scenarios[0],
            ending="125",
            minimum="85",
            drawdown="15",
            underwater="150",
            recovery="120",
            peak_loss="10",
        ),
        _path(
            "treatment",
            scenarios[1],
            ending="108",
            minimum="70",
            drawdown="30",
            underwater="400",
            recovery="350",
            peak_loss="18",
        ),
        _path(
            "treatment",
            scenarios[2],
            ending="90",
            minimum="25",
            drawdown="75",
            underwater="700",
            recovery="650",
            peak_loss="27",
        ),
        _path(
            "treatment",
            scenarios[3],
            ending="112",
            minimum="65",
            drawdown="35",
            underwater="450",
            recovery="400",
            peak_loss="20",
        ),
    )
    return candidates, scenarios, control_rows + treatment_rows


def test_genc9_reports_robust_growth_without_selecting_winner() -> None:
    candidates, scenarios, paths = _fixture()
    report = evaluate_genc9_robust_growth(
        research_id="GENC9_TEST",
        candidates=candidates,
        scenarios=scenarios,
        paths=paths,
    )

    assert report.control_candidate_id == "control"
    assert report.winner_candidate_id is None
    assert report.weighted_score_used is False
    assert report.production_policy_selected is False
    assert report.value_demonstrated is False
    assert report.certification_ready is False

    by_id = {item.candidate_id: item for item in report.summaries}
    control = by_id["control"]
    treatment = by_id["treatment"]
    assert control.path_count == 4
    assert control.ruin_path_count == 1
    assert control.empirical_scenario_ruin_frequency == Decimal("0.25")
    assert control.capacity_breach_path_count == 1
    assert control.p99_max_drawdown == Decimal("85")
    assert treatment.ruin_path_count == 0
    assert treatment.minimum_ending_multiple == Decimal("0.9")
    assert treatment.empirical_frequency_is_market_probability is False


def test_genc9_requires_identical_scenario_coverage() -> None:
    candidates, scenarios, paths = _fixture()
    with pytest.raises(
        CiboCompoundCapitalError,
        match="scenario coverage drift",
    ):
        evaluate_genc9_robust_growth(
            research_id="GENC9_TEST",
            candidates=candidates,
            scenarios=scenarios,
            paths=paths[:-1],
        )


def test_genc9_rejects_mixed_numeraire() -> None:
    candidates, scenarios, paths = _fixture()
    replacement = replace(
        paths[0],
        numeraire=Genc9Numeraire.PROVIDER_VALID_USD,
        provider_economics_sha256="sha256:" + "d" * 64,
    )
    mixed = (replacement,) + paths[1:]
    with pytest.raises(
        CiboCompoundCapitalError,
        match="mixed numeraires",
    ):
        evaluate_genc9_robust_growth(
            research_id="GENC9_TEST",
            candidates=candidates,
            scenarios=scenarios,
            paths=mixed,
        )


def test_genc9_rejects_path_before_preregistration() -> None:
    candidates, scenarios, paths = _fixture()
    late = Genc9CandidateDefinition(
        candidate_id="control",
        role=Genc9CandidateRole.CONTROL,
        family=Genc9GrowthFamily.CURRENT_CONTROL,
        parameterization_sha256="sha256:" + "5" * 64,
        preregistered_at=T0 + timedelta(days=1),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="predates candidate preregistration",
    ):
        evaluate_genc9_robust_growth(
            research_id="GENC9_TEST",
            candidates=(late, candidates[1]),
            scenarios=scenarios,
            paths=paths,
        )


def test_genc9_requires_complete_model_risk_declaration() -> None:
    risks = _risks()[:-1]
    with pytest.raises(
        CiboCompoundCapitalError,
        match="every mandatory model risk",
    ):
        Genc9ScenarioDefinition(
            scenario_id="incomplete",
            scenario_evidence_sha256="sha256:" + "e" * 64,
            model_risks=risks,
        )


def test_genc9_ruin_flag_is_boundary_derived() -> None:
    scenario = _scenario("ruin-check", "f")
    with pytest.raises(
        CiboCompoundCapitalError,
        match="ruin flag does not match",
    ):
        Genc9PathEvidence(
            candidate_id="control",
            scenario_id=scenario.scenario_id,
            evaluated_at=T0 + timedelta(minutes=1),
            numeraire=Genc9Numeraire.NORMALIZED_CAPITAL_UNITS,
            initial_capital=Decimal("100"),
            ending_capital=Decimal("80"),
            minimum_capital=Decimal("10"),
            max_drawdown=Decimal("90"),
            max_time_underwater_minutes=Decimal("500"),
            max_recovery_minutes=Decimal("400"),
            peak_plausible_loss=Decimal("30"),
            ruin_boundary=Decimal("20"),
            ruin_occurred=False,
            capacity_breach=False,
            horizon_minutes=Decimal("1000"),
            scenario_evidence_sha256=scenario.scenario_evidence_sha256,
            causal_replay_sha256="sha256:" + "a" * 64,
        )


def test_genc9_rejects_drawdown_smaller_than_forced_initial_to_minimum_loss() -> None:
    scenario = _scenario("drawdown-check", "1")
    with pytest.raises(
        CiboCompoundCapitalError,
        match="max drawdown is inconsistent with minimum capital",
    ):
        Genc9PathEvidence(
            candidate_id="control",
            scenario_id=scenario.scenario_id,
            evaluated_at=T0 + timedelta(minutes=1),
            numeraire=Genc9Numeraire.NORMALIZED_CAPITAL_UNITS,
            initial_capital=Decimal("100"),
            ending_capital=Decimal("120"),
            minimum_capital=Decimal("80"),
            max_drawdown=Decimal("19"),
            max_time_underwater_minutes=Decimal("100"),
            max_recovery_minutes=Decimal("90"),
            peak_plausible_loss=Decimal("10"),
            ruin_boundary=Decimal("20"),
            ruin_occurred=False,
            capacity_breach=False,
            horizon_minutes=Decimal("1000"),
            scenario_evidence_sha256=scenario.scenario_evidence_sha256,
            causal_replay_sha256="sha256:" + "b" * 64,
        )


def test_genc9_summary_rejects_impossible_quantiles_or_frequency_drift() -> None:
    candidates, scenarios, paths = _fixture()
    report = evaluate_genc9_robust_growth(
        research_id="GENC9_SUMMARY_INTEGRITY",
        candidates=candidates,
        scenarios=scenarios,
        paths=paths,
    )
    summary = report.summaries[0]

    with pytest.raises(
        CiboCompoundCapitalError,
        match="drawdown quantile order drift",
    ):
        replace(
            summary,
            p99_max_drawdown=summary.maximum_drawdown + Decimal("1"),
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="empirical frequency/count drift",
    ):
        replace(
            summary,
            empirical_scenario_ruin_frequency=Decimal("0.5"),
        )


def test_genc9_summary_rejects_ambiguous_path_count_type() -> None:
    candidates, scenarios, paths = _fixture()
    report = evaluate_genc9_robust_growth(
        research_id="GENC9_SUMMARY_TYPES",
        candidates=candidates,
        scenarios=scenarios,
        paths=paths,
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="path/scenario count drift",
    ):
        replace(report.summaries[0], path_count=True)
