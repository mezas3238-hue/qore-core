from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_expansion_utility_gate import (
    EXPANSION_UTILITY_GATE_ID,
    ExpansionCandidateRole,
    ExpansionUtilityKind,
    ExpansionUtilityStatus,
    ExpansionUtilitySummary,
    evaluate_expansion_utility_gate,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _summary(
    *,
    candidate_id: str,
    role: ExpansionCandidateRole,
    kind: ExpansionUtilityKind = ExpansionUtilityKind.T06_PROFIT_FUNDED,
    **changes,
) -> ExpansionUtilitySummary:
    values = dict(
        candidate_id=candidate_id,
        kind=kind,
        role=role,
        population_sha256=_sha("a"),
        provider_economics_sha256=_sha("b"),
        realized_net_delta_usd=Decimal("10"),
        capital_productivity_usd_per_risk_minute=Decimal("0.10"),
        peak_plausible_loss_usd=Decimal("5"),
        max_settlement_drawdown_usd=Decimal("4"),
        peak_margin_occupancy_usd=Decimal("20"),
        capital_lockup_minutes=Decimal("100"),
        max_recovery_minutes=Decimal("200"),
        minimum_realized_capital_usd=Decimal("90"),
        optionality_preserved_rate=Decimal("0.80"),
        provider_failure_incidence=Decimal("0.01"),
        protected_capacity_accounting_only=(
            kind is ExpansionUtilityKind.T07_PROTECTED_CAPACITY
        ),
    )
    values.update(changes)
    return ExpansionUtilitySummary(**values)


def test_expansion_gate_allows_strict_improvement_only_after_safety() -> None:
    control = _summary(
        candidate_id="control",
        role=ExpansionCandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=ExpansionCandidateRole.TREATMENT,
        realized_net_delta_usd=Decimal("12"),
    )

    report = evaluate_expansion_utility_gate((control, treatment))

    assert report.gate_id == EXPANSION_UTILITY_GATE_ID
    assert report.control_candidate_id == "control"
    row = report.rows[1]
    assert row.status is ExpansionUtilityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    assert row.safety_no_worse is True
    assert row.strict_economic_improvement is True
    assert row.failed_dimensions == ()
    assert report.weighted_score_used is False
    assert report.production_policy_selected is False
    assert report.certification_ready is False


def test_expansion_gate_rejects_more_return_when_drawdown_is_worse() -> None:
    control = _summary(
        candidate_id="control",
        role=ExpansionCandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=ExpansionCandidateRole.TREATMENT,
        realized_net_delta_usd=Decimal("100"),
        max_settlement_drawdown_usd=Decimal("4.01"),
    )

    row = evaluate_expansion_utility_gate((control, treatment)).rows[1]

    assert row.status is ExpansionUtilityStatus.REJECTED_SAFETY_DETERIORATION
    assert row.strict_economic_improvement is True
    assert row.safety_no_worse is False
    assert row.failed_dimensions == ("MAX_SETTLEMENT_DRAWDOWN_USD",)


def test_expansion_gate_rejects_safe_but_nonimproving_treatment() -> None:
    control = _summary(
        candidate_id="control",
        role=ExpansionCandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=ExpansionCandidateRole.TREATMENT,
    )

    row = evaluate_expansion_utility_gate((control, treatment)).rows[1]

    assert row.status is (
        ExpansionUtilityStatus.REJECTED_NO_STRICT_ECONOMIC_IMPROVEMENT
    )
    assert row.safety_no_worse is True
    assert row.strict_economic_improvement is False


def test_expansion_gate_rejects_population_or_provider_drift() -> None:
    control = _summary(
        candidate_id="control",
        role=ExpansionCandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=ExpansionCandidateRole.TREATMENT,
        population_sha256=_sha("c"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical population/provider economics",
    ):
        evaluate_expansion_utility_gate((control, treatment))

    treatment = replace(
        treatment,
        population_sha256=control.population_sha256,
        provider_economics_sha256=_sha("d"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical population/provider economics",
    ):
        evaluate_expansion_utility_gate((control, treatment))


def test_t07_requires_accounting_protection_and_separate_broker_evidence() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="accounting protection",
    ):
        _summary(
            candidate_id="bad-t07",
            role=ExpansionCandidateRole.TREATMENT,
            kind=ExpansionUtilityKind.T07_PROTECTED_CAPACITY,
            protected_capacity_accounting_only=False,
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="broker guarantee claim requires canonical evidence",
    ):
        _summary(
            candidate_id="bad-guarantee",
            role=ExpansionCandidateRole.TREATMENT,
            kind=ExpansionUtilityKind.T07_PROTECTED_CAPACITY,
            broker_guarantee_claimed=True,
        )

    valid = _summary(
        candidate_id="evidenced-guarantee",
        role=ExpansionCandidateRole.TREATMENT,
        kind=ExpansionUtilityKind.T07_PROTECTED_CAPACITY,
        broker_guarantee_claimed=True,
        broker_guarantee_evidence_sha256=_sha("e"),
    )
    assert valid.broker_guarantee_claimed is True


def test_t06_cannot_claim_protected_or_broker_capacity() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot claim protected/broker capacity",
    ):
        _summary(
            candidate_id="bad-t06",
            role=ExpansionCandidateRole.TREATMENT,
            protected_capacity_accounting_only=True,
        )


def test_expansion_gate_requires_exactly_one_control_and_one_kind() -> None:
    control = _summary(
        candidate_id="control",
        role=ExpansionCandidateRole.CONTROL,
    )
    second_control = _summary(
        candidate_id="control-2",
        role=ExpansionCandidateRole.CONTROL,
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="exactly one control",
    ):
        evaluate_expansion_utility_gate((control, second_control))

    t07 = _summary(
        candidate_id="t07",
        role=ExpansionCandidateRole.TREATMENT,
        kind=ExpansionUtilityKind.T07_PROTECTED_CAPACITY,
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot mix T06 and T07",
    ):
        evaluate_expansion_utility_gate((control, t07))

def test_expansion_row_rejects_manual_status_metric_drift() -> None:
    control = _summary(
        candidate_id="control",
        role=ExpansionCandidateRole.CONTROL,
    )
    treatment = _summary(
        candidate_id="treatment",
        role=ExpansionCandidateRole.TREATMENT,
        realized_net_delta_usd=Decimal("12"),
    )
    row = evaluate_expansion_utility_gate((control, treatment)).rows[1]

    with pytest.raises(
        CiboCompoundCapitalError,
        match="status/metric drift",
    ):
        replace(row, safety_no_worse=False)

