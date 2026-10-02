from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_genc3_genc6_economic_gate import (
    GATE_SHA256,
    Genc3To6EconomicRole,
    Genc3To6EconomicStatus,
    Genc3To6FoldEconomicObservation,
    Genc3To6Workstream,
    evaluate_genc3_genc6_economic_gate,
)

FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _observation(
    *,
    workstream: Genc3To6Workstream,
    candidate_id: str,
    role: Genc3To6EconomicRole,
    fold_id: str,
    net_delta: str = "10",
    ending: str = "110",
    max_dd: str = "5",
    p99_dd: str = "4.5",
    plausible_loss: str = "6",
    margin: str = "20",
    provider_cost: str = "2",
    capital_minutes: str = "100",
    reserve: str = "15",
    optionality: str = "12",
    recovery: str = "50",
    productivity: str = "1.2",
) -> Genc3To6FoldEconomicObservation:
    kwargs = {
        "portfolio_cycle_complete": workstream is Genc3To6Workstream.GENC3,
        "marginal_unit_identified": workstream is Genc3To6Workstream.GENC4,
        "chronological_sequence_preserved": (
            workstream is Genc3To6Workstream.GENC5
        ),
        "true_scarcity_observed": workstream is Genc3To6Workstream.GENC6,
    }
    return Genc3To6FoldEconomicObservation(
        candidate_id=candidate_id,
        workstream=workstream,
        role=role,
        fold_id=fold_id,
        population_sha256=_sha("1"),
        provider_surface_sha256=_sha("2"),
        causal_horizon_sha256=_sha("3"),
        protocol_binding_sha256=_sha("4"),
        realized_net_delta_usd=Decimal(net_delta),
        ending_realized_capital_usd=Decimal(ending),
        maximum_drawdown_usd=Decimal(max_dd),
        p99_drawdown_usd=Decimal(p99_dd),
        peak_plausible_loss_usd=Decimal(plausible_loss),
        peak_margin_occupancy_usd=Decimal(margin),
        provider_cost_usd=Decimal(provider_cost),
        capital_minutes=Decimal(capital_minutes),
        minimum_liquid_reserve_usd=Decimal(reserve),
        minimum_optionality_usd=Decimal(optionality),
        p95_recovery_minutes=Decimal(recovery),
        capital_risk_time_productivity=Decimal(productivity),
        causal_effect_identified=True,
        treatment_preregistered_before_outcomes=True,
        **kwargs,
    )


def _batch(
    workstream: Genc3To6Workstream,
    *,
    treatment_net: str = "11",
) -> tuple[Genc3To6FoldEconomicObservation, ...]:
    rows = []
    for fold_id in FOLDS:
        rows.append(
            _observation(
                workstream=workstream,
                candidate_id="control",
                role=Genc3To6EconomicRole.CONTROL,
                fold_id=fold_id,
            )
        )
        rows.append(
            _observation(
                workstream=workstream,
                candidate_id="treatment",
                role=Genc3To6EconomicRole.TREATMENT,
                fold_id=fold_id,
                net_delta=treatment_net,
            )
        )
    return tuple(rows)


def test_gate_digest_is_frozen() -> None:
    assert GATE_SHA256 == (
        "sha256:6d77b29b321d1dfc36f92adf7a81cdf62cf2221e"
        "ce3e4631d23daf999c8819af"
    )


@pytest.mark.parametrize("workstream", tuple(Genc3To6Workstream))
def test_each_workstream_can_pass_strict_four_of_four(
    workstream: Genc3To6Workstream,
) -> None:
    report = evaluate_genc3_genc6_economic_gate(_batch(workstream))

    verdict = next(
        item for item in report.verdicts
        if item.candidate_id == "treatment"
    )
    assert verdict.workstream is workstream
    assert (
        verdict.status
        is Genc3To6EconomicStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    )
    assert verdict.passed_fold_ids == FOLDS
    assert verdict.failed_fold_ids == ()


def test_one_fold_safety_deterioration_rejects_whole_treatment() -> None:
    rows = list(_batch(Genc3To6Workstream.GENC5))
    target = next(
        index for index, item in enumerate(rows)
        if item.candidate_id == "treatment" and item.fold_id == "WF3"
    )
    rows[target] = replace(rows[target], maximum_drawdown_usd=Decimal("5.1"))

    report = evaluate_genc3_genc6_economic_gate(tuple(rows))
    verdict = next(
        item for item in report.verdicts
        if item.candidate_id == "treatment"
    )

    assert (
        verdict.status
        is Genc3To6EconomicStatus.REJECTED_SAFETY_DETERIORATION
    )
    assert verdict.failed_fold_ids == ("WF3",)
    assert "WF3:maximum_drawdown_usd" in verdict.failed_dimensions


def test_one_fold_without_strict_improvement_rejects_four_of_four() -> None:
    rows = list(_batch(Genc3To6Workstream.GENC6))
    target = next(
        index for index, item in enumerate(rows)
        if item.candidate_id == "treatment" and item.fold_id == "WF4"
    )
    rows[target] = replace(rows[target], realized_net_delta_usd=Decimal("10"))

    report = evaluate_genc3_genc6_economic_gate(tuple(rows))
    verdict = next(
        item for item in report.verdicts
        if item.candidate_id == "treatment"
    )

    assert verdict.status is Genc3To6EconomicStatus.REJECTED_NOT_STRICT_4_OF_4
    assert verdict.failed_fold_ids == ("WF4",)
    assert "WF4:NO_STRICT_IMPROVEMENT" in verdict.failed_dimensions


def test_mismatched_population_is_illegal() -> None:
    rows = list(_batch(Genc3To6Workstream.GENC4))
    target = next(
        index for index, item in enumerate(rows)
        if item.candidate_id == "treatment" and item.fold_id == "WF2"
    )
    rows[target] = replace(rows[target], population_sha256=_sha("9"))

    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical causal comparison surface",
    ):
        evaluate_genc3_genc6_economic_gate(tuple(rows))


def test_missing_workstream_mechanism_condition_is_illegal() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="GEN-C5 economic mechanism condition missing",
    ):
        replace(
            _observation(
                workstream=Genc3To6Workstream.GENC5,
                candidate_id="treatment",
                role=Genc3To6EconomicRole.TREATMENT,
                fold_id="WF1",
            ),
            chronological_sequence_preserved=False,
        )


def test_productive_authority_is_illegal() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="governance/causal drift",
    ):
        replace(
            _observation(
                workstream=Genc3To6Workstream.GENC3,
                candidate_id="treatment",
                role=Genc3To6EconomicRole.TREATMENT,
                fold_id="WF1",
            ),
            productive_authority=True,
        )

def test_verdict_rejects_manual_status_fold_drift() -> None:
    report = evaluate_genc3_genc6_economic_gate(
        _batch(Genc3To6Workstream.GENC3)
    )
    verdict = next(
        item for item in report.verdicts
        if item.candidate_id == "treatment"
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="status/fold drift",
    ):
        replace(
            verdict,
            status=Genc3To6EconomicStatus.REJECTED_NOT_STRICT_4_OF_4,
        )

