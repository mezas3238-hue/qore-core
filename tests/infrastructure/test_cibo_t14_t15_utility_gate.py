from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_t14_t15_utility_gate import (
    T14_T15_UTILITY_GATE_ID,
    T14T15CandidateRole,
    T14T15UtilityKind,
    T14T15UtilityStatus,
    T14T15UtilitySummary,
    evaluate_t14_t15_utility_gate,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _summary(
    *,
    candidate_id: str,
    role: T14T15CandidateRole,
    kind: T14T15UtilityKind = T14T15UtilityKind.T14_DYNAMIC_DERISKING,
    **changes,
) -> T14T15UtilitySummary:
    values = dict(
        candidate_id=candidate_id,
        kind=kind,
        role=role,
        population_sha256=_sha("a"),
        provider_economics_sha256=_sha("b"),
        causal_horizon_sha256=_sha("c"),
        realized_net_delta_usd=Decimal("10"),
        capital_productivity_usd_per_risk_minute=Decimal("0.10"),
        peak_plausible_loss_usd=Decimal("5"),
        max_settlement_drawdown_usd=Decimal("4"),
        peak_margin_occupancy_usd=Decimal("20"),
        minimum_realized_capital_usd=Decimal("90"),
        max_recovery_minutes=Decimal("200"),
        optionality_preserved_rate=Decimal("0.80"),
        released_stop_risk_minutes_usd=Decimal("0"),
        materialized_known_options_executable=0,
        known_option_set_sha256=(
            _sha("d")
            if kind is T14T15UtilityKind.T15_OPTIONALITY
            else None
        ),
        causal_effect_identified=(
            kind is T14T15UtilityKind.T15_OPTIONALITY
        ),
    )
    values.update(changes)
    return T14T15UtilitySummary(**values)


def test_t14_gate_accepts_pareto_improving_derisking() -> None:
    control = _summary(
        candidate_id="control",
        role=T14T15CandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=T14T15CandidateRole.TREATMENT,
        max_settlement_drawdown_usd=Decimal("3"),
        released_stop_risk_minutes_usd=Decimal("50"),
    )

    report = evaluate_t14_t15_utility_gate((control, treatment))

    assert report.gate_id == T14_T15_UTILITY_GATE_ID
    row = report.rows[1]
    assert row.status is T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert row.causal_identification_pass is True
    assert row.governance_pass is True
    assert row.pareto_no_worse is True
    assert row.strict_utility_improvement is True
    assert report.weighted_score_used is False
    assert report.production_policy_selected is False
    assert report.certification_ready is False


def test_t14_gate_rejects_lower_return_despite_lower_drawdown() -> None:
    control = _summary(
        candidate_id="control",
        role=T14T15CandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=T14T15CandidateRole.TREATMENT,
        realized_net_delta_usd=Decimal("9.99"),
        max_settlement_drawdown_usd=Decimal("1"),
    )

    row = evaluate_t14_t15_utility_gate((control, treatment)).rows[1]

    assert row.status is T14T15UtilityStatus.REJECTED_PARETO_DETERIORATION
    assert row.strict_utility_improvement is True
    assert "REALIZED_NET_DELTA_USD" in row.failed_dimensions


def test_t14_gate_rejects_methodology_or_stop_override() -> None:
    control = _summary(
        candidate_id="control",
        role=T14T15CandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=T14T15CandidateRole.TREATMENT,
        structural_stop_changed_by_cibo=True,
        max_settlement_drawdown_usd=Decimal("3"),
    )

    row = evaluate_t14_t15_utility_gate((control, treatment)).rows[1]

    assert row.status is T14T15UtilityStatus.REJECTED_GOVERNANCE
    assert row.governance_pass is False
    assert "STRUCTURAL_STOP_CHANGED_BY_CIBO" in row.failed_dimensions


def test_t15_realization_alone_cannot_claim_utility() -> None:
    control = _summary(
        candidate_id="control",
        role=T14T15CandidateRole.CONTROL,
        kind=T14T15UtilityKind.T15_OPTIONALITY,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=T14T15CandidateRole.TREATMENT,
        kind=T14T15UtilityKind.T15_OPTIONALITY,
        causal_effect_identified=False,
        materialized_known_options_executable=4,
        optionality_preserved_rate=Decimal("0.90"),
    )

    row = evaluate_t14_t15_utility_gate((control, treatment)).rows[1]

    assert row.status is T14T15UtilityStatus.REJECTED_CAUSAL_IDENTIFICATION
    assert row.causal_identification_pass is False
    assert row.strict_utility_improvement is True


def test_t15_requires_same_predecision_known_option_set() -> None:
    control = _summary(
        candidate_id="control",
        role=T14T15CandidateRole.CONTROL,
        kind=T14T15UtilityKind.T15_OPTIONALITY,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=T14T15CandidateRole.TREATMENT,
        kind=T14T15UtilityKind.T15_OPTIONALITY,
        known_option_set_sha256=_sha("e"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical frozen known-option set",
    ):
        evaluate_t14_t15_utility_gate((control, treatment))


def test_t15_causal_pareto_improvement_is_research_eligible_only() -> None:
    control = _summary(
        candidate_id="control",
        role=T14T15CandidateRole.CONTROL,
        kind=T14T15UtilityKind.T15_OPTIONALITY,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=T14T15CandidateRole.TREATMENT,
        kind=T14T15UtilityKind.T15_OPTIONALITY,
        materialized_known_options_executable=2,
        optionality_preserved_rate=Decimal("0.90"),
    )

    report = evaluate_t14_t15_utility_gate((control, treatment))
    row = report.rows[1]

    assert row.status is T14T15UtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert report.production_policy_selected is False
    assert report.certification_ready is False


def test_t14_t15_gate_rejects_population_provider_or_horizon_drift() -> None:
    control = _summary(
        candidate_id="control",
        role=T14T15CandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=T14T15CandidateRole.TREATMENT,
        population_sha256=_sha("f"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical causal comparison surface",
    ):
        evaluate_t14_t15_utility_gate((control, treatment))

    treatment = replace(
        treatment,
        population_sha256=control.population_sha256,
        provider_economics_sha256=_sha("e"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical causal comparison surface",
    ):
        evaluate_t14_t15_utility_gate((control, treatment))


def test_t14_t15_gate_rejects_mixed_workstreams() -> None:
    control = _summary(
        candidate_id="control",
        role=T14T15CandidateRole.CONTROL,
    )
    t15 = _summary(
        candidate_id="t15",
        role=T14T15CandidateRole.TREATMENT,
        kind=T14T15UtilityKind.T15_OPTIONALITY,
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot mix workstreams",
    ):
        evaluate_t14_t15_utility_gate((control, t15))

def test_t14_t15_row_rejects_manual_status_metric_drift() -> None:
    control = _summary(
        candidate_id="control",
        role=T14T15CandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=T14T15CandidateRole.TREATMENT,
        max_settlement_drawdown_usd=Decimal("3"),
    )
    row = evaluate_t14_t15_utility_gate((control, treatment)).rows[1]

    with pytest.raises(
        CiboCompoundCapitalError,
        match="status/metric drift",
    ):
        replace(row, governance_pass=False)

