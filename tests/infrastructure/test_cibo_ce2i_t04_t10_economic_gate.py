from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_ce2i_t04_t10_economic_gate import (
    GATE_SHA256,
    Ce2iT04T10FoldObservation,
    Ce2iT04T10Role,
    Ce2iT04T10Status,
    Ce2iT04T10Tool,
    evaluate_t04_t10_economic_gate,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _observation(
    *,
    tool: Ce2iT04T10Tool,
    candidate_id: str,
    role: Ce2iT04T10Role,
    fold_id: str,
    net_delta: str = "10",
    max_dd: str = "5",
    productivity: str = "1.0",
    output_per_stop_risk: str = "1.0",
    output_per_capital_minute: str = "0.10",
    timestamps: bool | None = None,
) -> Ce2iT04T10FoldObservation:
    if timestamps is None:
        timestamps = tool is Ce2iT04T10Tool.T10
    return Ce2iT04T10FoldObservation(
        candidate_id=candidate_id,
        tool=tool,
        role=role,
        fold_id=fold_id,
        population_sha256=_sha("1"),
        strategy_surface_sha256=_sha("2"),
        provider_surface_sha256=_sha("3"),
        risk_boundary_sha256=_sha("4"),
        capital_truth_sha256=_sha("5"),
        causal_horizon_sha256=_sha("6"),
        protocol_binding_sha256=_sha("7"),
        realized_net_delta_usd=Decimal(net_delta),
        maximum_drawdown_usd=Decimal(max_dd),
        p99_drawdown_usd=Decimal("4.5"),
        peak_plausible_loss_usd=Decimal("6"),
        peak_margin_occupancy_usd=Decimal("20"),
        provider_cost_usd=Decimal("2"),
        provider_failure_count=0,
        capital_conservation_breach_count=0,
        minimum_realized_capital_usd=Decimal("90"),
        minimum_liquid_reserve_usd=Decimal("15"),
        minimum_optionality_usd=Decimal("12"),
        p95_recovery_minutes=Decimal("50"),
        true_stop_risk_usd=Decimal("10"),
        capital_minutes=Decimal("100"),
        capital_risk_time_productivity=Decimal(productivity),
        realized_output_per_true_stop_risk=Decimal(output_per_stop_risk),
        realized_output_per_capital_minute=Decimal(output_per_capital_minute),
        causal_effect_identified=True,
        treatment_preregistered_before_outcomes=True,
        provider_economics_complete=True,
        outcome_coverage_complete=True,
        authoritative_deployment_release_timestamps=timestamps,
    )


def _batch(
    tool: Ce2iT04T10Tool,
) -> tuple[Ce2iT04T10FoldObservation, ...]:
    rows = []
    for fold_id in FOLDS:
        rows.append(
            _observation(
                tool=tool,
                candidate_id="control",
                role=Ce2iT04T10Role.CONTROL,
                fold_id=fold_id,
            )
        )
        rows.append(
            _observation(
                tool=tool,
                candidate_id="treatment",
                role=Ce2iT04T10Role.TREATMENT,
                fold_id=fold_id,
                productivity="1.1",
                output_per_stop_risk="1.1",
                output_per_capital_minute="0.11",
            )
        )
    return tuple(rows)


def test_gate_digest_is_frozen() -> None:
    assert GATE_SHA256 == (
        "sha256:45928fe4db78cb771d88891f099dab484f37d5d4"
        "ce55e0fe1d76a7345b9fe35b"
    )


@pytest.mark.parametrize("tool", tuple(Ce2iT04T10Tool))
def test_each_tool_can_pass_strict_four_of_four(
    tool: Ce2iT04T10Tool,
) -> None:
    report = evaluate_t04_t10_economic_gate(_batch(tool))

    verdict = next(
        item for item in report.verdicts if item.candidate_id == "treatment"
    )
    assert verdict.tool is tool
    assert (
        verdict.status
        is Ce2iT04T10Status.ELIGIBLE_FOR_FURTHER_RESEARCH
    )
    assert verdict.passed_fold_ids == FOLDS
    assert verdict.failed_fold_ids == ()


def test_one_fold_safety_deterioration_rejects_whole_treatment() -> None:
    rows = list(_batch(Ce2iT04T10Tool.T04))
    target = next(
        index for index, item in enumerate(rows)
        if item.candidate_id == "treatment" and item.fold_id == "WF3"
    )
    rows[target] = replace(rows[target], maximum_drawdown_usd=Decimal("5.1"))

    report = evaluate_t04_t10_economic_gate(tuple(rows))
    verdict = next(
        item for item in report.verdicts if item.candidate_id == "treatment"
    )

    assert (
        verdict.status
        is Ce2iT04T10Status.REJECTED_SAFETY_DETERIORATION
    )
    assert verdict.failed_fold_ids == ("WF3",)
    assert "WF3:maximum_drawdown_usd" in verdict.failed_dimensions


def test_one_fold_without_strict_improvement_rejects_four_of_four() -> None:
    rows = list(_batch(Ce2iT04T10Tool.T10))
    target = next(
        index for index, item in enumerate(rows)
        if item.candidate_id == "treatment" and item.fold_id == "WF4"
    )
    rows[target] = replace(
        rows[target],
        capital_risk_time_productivity=Decimal("1.0"),
        realized_output_per_capital_minute=Decimal("0.10"),
    )

    report = evaluate_t04_t10_economic_gate(tuple(rows))
    verdict = next(
        item for item in report.verdicts if item.candidate_id == "treatment"
    )

    assert verdict.status is Ce2iT04T10Status.REJECTED_NOT_STRICT_4_OF_4
    assert verdict.failed_fold_ids == ("WF4",)
    assert "WF4:NO_STRICT_IMPROVEMENT" in verdict.failed_dimensions


def test_mismatched_population_is_illegal() -> None:
    rows = list(_batch(Ce2iT04T10Tool.T04))
    target = next(
        index for index, item in enumerate(rows)
        if item.candidate_id == "treatment" and item.fold_id == "WF2"
    )
    rows[target] = replace(rows[target], population_sha256=_sha("9"))

    with pytest.raises(
        CiboCompoundCapitalError,
        match="identical causal comparison surface",
    ):
        evaluate_t04_t10_economic_gate(tuple(rows))


def test_t10_requires_authoritative_release_timestamps() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="authoritative deployment/release timestamps",
    ):
        _observation(
            tool=Ce2iT04T10Tool.T10,
            candidate_id="treatment",
            role=Ce2iT04T10Role.TREATMENT,
            fold_id="WF1",
            timestamps=False,
        )


def test_future_outcome_use_is_illegal() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="governance/causal drift",
    ):
        replace(
            _observation(
                tool=Ce2iT04T10Tool.T04,
                candidate_id="treatment",
                role=Ce2iT04T10Role.TREATMENT,
                fold_id="WF1",
            ),
            future_outcome_used=True,
        )
