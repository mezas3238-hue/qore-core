from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_t09_t18_scarcity_safety_gate import (
    GATE_SHA256,
    T09T18ScarcityFoldObservation,
    T09T18ScarcityRole,
    T09T18ScarcityStatus,
    T09T18ScarcityTool,
    evaluate_t09_t18_scarcity_gate,
)

FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _observation(
    *,
    tool: T09T18ScarcityTool,
    candidate_id: str,
    role: T09T18ScarcityRole,
    fold_id: str,
    net_delta: str = "10",
    productivity: str = "1.0",
    concentration: str = "0.40",
    starvation: str = "0.10",
) -> T09T18ScarcityFoldObservation:
    return T09T18ScarcityFoldObservation(
        candidate_id=candidate_id,
        tool=tool,
        role=role,
        fold_id=fold_id,
        population_sha256=_sha("1"),
        opportunity_set_sha256=_sha("2"),
        strategy_surface_sha256=_sha("3"),
        provider_surface_sha256=_sha("4"),
        risk_boundary_sha256=_sha("5"),
        capital_truth_sha256=_sha("6"),
        causal_horizon_sha256=_sha("7"),
        protocol_binding_sha256=_sha("8"),
        realized_net_delta_usd=Decimal(net_delta),
        maximum_drawdown_usd=Decimal("5"),
        p99_drawdown_usd=Decimal("4.5"),
        peak_plausible_loss_usd=Decimal("6"),
        peak_margin_occupancy_usd=Decimal("20"),
        minimum_liquid_reserve_usd=Decimal("15"),
        minimum_optionality_usd=Decimal("12"),
        p95_recovery_minutes=Decimal("50"),
        capital_productivity=Decimal(productivity),
        concentration_rate=Decimal(concentration),
        starvation_rate=Decimal(starvation),
        provider_failure_count=0,
        true_scarcity_observed=True,
        simultaneous_opportunity_set_verified=True,
        trader_sovereignty_preserved=True,
        causal_effect_identified=True,
        treatment_preregistered_before_outcomes=True,
        provider_economics_complete=True,
        outcome_coverage_complete=True,
    )


def _batch(
    tool: T09T18ScarcityTool,
) -> tuple[T09T18ScarcityFoldObservation, ...]:
    rows = []
    for fold_id in FOLDS:
        rows.append(
            _observation(
                tool=tool,
                candidate_id="control",
                role=T09T18ScarcityRole.CONTROL,
                fold_id=fold_id,
            )
        )
        rows.append(
            _observation(
                tool=tool,
                candidate_id="treatment",
                role=T09T18ScarcityRole.TREATMENT,
                fold_id=fold_id,
                net_delta="11",
                productivity="1.1",
                concentration="0.35",
                starvation="0.08",
            )
        )
    return tuple(rows)


def test_gate_digest_is_frozen() -> None:
    assert GATE_SHA256 == (
        "sha256:6db2f83fb17a8b9f3f90864cbb18fcd02a36709b"
        "068693436014d3d5e2056abe"
    )


@pytest.mark.parametrize("tool", tuple(T09T18ScarcityTool))
def test_each_tool_can_pass_strict_four_of_four(
    tool: T09T18ScarcityTool,
) -> None:
    report = evaluate_t09_t18_scarcity_gate(_batch(tool))
    verdict = next(
        item for item in report.verdicts if item.candidate_id == "treatment"
    )

    assert verdict.tool is tool
    assert (
        verdict.status
        is T09T18ScarcityStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
    )
    assert verdict.passed_fold_ids == FOLDS


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("concentration_rate", Decimal("0.41")),
        ("starvation_rate", Decimal("0.11")),
    ),
)
def test_mandatory_scarcity_safety_cannot_deteriorate(
    field: str,
    value: Decimal,
) -> None:
    rows = list(_batch(T09T18ScarcityTool.T18))
    target = next(
        index for index, item in enumerate(rows)
        if item.candidate_id == "treatment" and item.fold_id == "WF2"
    )
    rows[target] = replace(rows[target], **{field: value})

    report = evaluate_t09_t18_scarcity_gate(tuple(rows))
    verdict = next(
        item for item in report.verdicts if item.candidate_id == "treatment"
    )

    assert (
        verdict.status
        is T09T18ScarcityStatus.REJECTED_SAFETY_DETERIORATION
    )
    assert verdict.failed_fold_ids == ("WF2",)
    assert f"WF2:{field}" in verdict.failed_dimensions


def test_one_fold_without_strict_improvement_rejects_four_of_four() -> None:
    rows = list(_batch(T09T18ScarcityTool.T09))
    target = next(
        index for index, item in enumerate(rows)
        if item.candidate_id == "treatment" and item.fold_id == "WF4"
    )
    rows[target] = replace(
        rows[target],
        realized_net_delta_usd=Decimal("10"),
        capital_productivity=Decimal("1.0"),
    )

    report = evaluate_t09_t18_scarcity_gate(tuple(rows))
    verdict = next(
        item for item in report.verdicts if item.candidate_id == "treatment"
    )

    assert verdict.status is T09T18ScarcityStatus.REJECTED_NOT_STRICT_4_OF_4
    assert verdict.failed_fold_ids == ("WF4",)
    assert "WF4:NO_STRICT_IMPROVEMENT" in verdict.failed_dimensions


def test_mismatched_opportunity_set_is_illegal() -> None:
    rows = list(_batch(T09T18ScarcityTool.T09))
    target = next(
        index for index, item in enumerate(rows)
        if item.candidate_id == "treatment" and item.fold_id == "WF3"
    )
    rows[target] = replace(rows[target], opportunity_set_sha256=_sha("9"))

    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical causal comparison surface",
    ):
        evaluate_t09_t18_scarcity_gate(tuple(rows))


def test_t18_requires_trader_sovereignty() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="preserve Trader sovereignty",
    ):
        replace(
            _observation(
                tool=T09T18ScarcityTool.T18,
                candidate_id="treatment",
                role=T09T18ScarcityRole.TREATMENT,
                fold_id="WF1",
            ),
            trader_sovereignty_preserved=False,
        )

def test_scarcity_verdict_rejects_manual_status_fold_drift() -> None:
    report = evaluate_t09_t18_scarcity_gate(_batch(T09T18ScarcityTool.T09))
    verdict = next(
        item for item in report.verdicts if item.candidate_id == "treatment"
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="status/fold drift",
    ):
        replace(
            verdict,
            status=T09T18ScarcityStatus.REJECTED_NOT_STRICT_4_OF_4,
        )

