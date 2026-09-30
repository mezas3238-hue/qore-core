from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_efficiency_sizing_lab import (
    BROKER_MINIMUM_VOLUME,
    MARGIN_BUDGET,
    RISK_BUDGET,
    CapitalEfficiencyFeasibility,
    CapitalEfficiencySizingError,
    CapitalEfficiencySizingInput,
    capital_efficiency_pareto_frontier,
    evaluate_capital_efficiency_sizing,
)


def _spec(
    *,
    experiment_id: str = "baseline",
    risk_budget: str = "20",
    margin_budget: str = "100",
    stop_loss_per_volume: str = "100",
    margin_per_volume: str = "200",
    exposure_per_volume: str = "10000",
    baseline_volume: str | None = "0.10",
    verified: bool = True,
) -> CapitalEfficiencySizingInput:
    return CapitalEfficiencySizingInput(
        experiment_id=experiment_id,
        qore_symbol="EURUSD",
        geometry_provenance="frozen-trader-ledger:case-001",
        structural_stop_verified=verified,
        assigned_capital=Decimal("2000"),
        risk_budget_usd=Decimal(risk_budget),
        margin_budget_usd=Decimal(margin_budget),
        stop_loss_per_volume=Decimal(stop_loss_per_volume),
        margin_per_volume=Decimal(margin_per_volume),
        exposure_per_volume=Decimal(exposure_per_volume),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("50"),
        volume_step=Decimal("0.01"),
        baseline_volume=(
            Decimal(baseline_volume)
            if baseline_volume is not None
            else None
        ),
    )


def test_risk_budget_can_bind_maximum_exposure() -> None:
    result = evaluate_capital_efficiency_sizing(_spec())

    assert result.status is CapitalEfficiencyFeasibility.FEASIBLE
    assert result.authorized_volume == Decimal("0.20")
    assert result.stop_risk_usd == Decimal("20.00")
    assert result.margin_committed_usd == Decimal("40.00")
    assert result.exposure == Decimal("2000.00")
    assert result.exposure_gain_multiple == Decimal("2")
    assert result.binding_constraints == (RISK_BUDGET,)
    assert result.risk_budget_utilization == Decimal("1.00")


def test_margin_budget_can_bind_before_stop_risk_budget() -> None:
    result = evaluate_capital_efficiency_sizing(
        _spec(
            risk_budget="100",
            margin_budget="30",
            stop_loss_per_volume="100",
            margin_per_volume="200",
        )
    )

    assert result.authorized_volume == Decimal("0.15")
    assert result.stop_risk_usd == Decimal("15.00")
    assert result.margin_committed_usd == Decimal("30.00")
    assert result.binding_constraints == (MARGIN_BUDGET,)


def test_more_precise_verified_invalidation_increases_exposure_at_same_risk() -> None:
    wide = evaluate_capital_efficiency_sizing(
        _spec(
            experiment_id="wide",
            stop_loss_per_volume="200",
            baseline_volume=None,
        )
    )
    precise = evaluate_capital_efficiency_sizing(
        _spec(
            experiment_id="precise",
            stop_loss_per_volume="100",
            baseline_volume=None,
        )
    )

    assert wide.stop_risk_usd == precise.stop_risk_usd == Decimal("20.00")
    assert precise.authorized_volume == wide.authorized_volume * Decimal("2")
    assert precise.exposure == wide.exposure * Decimal("2")


def test_unverified_tighter_stop_is_refused_instead_of_manufacturing_leverage() -> None:
    with pytest.raises(CapitalEfficiencySizingError, match="structural stop"):
        evaluate_capital_efficiency_sizing(
            _spec(stop_loss_per_volume="25", verified=False)
        )


def test_broker_minimum_can_make_budget_infeasible() -> None:
    spec = CapitalEfficiencySizingInput(
        experiment_id="minimum-fails",
        qore_symbol="XAUUSD",
        geometry_provenance="frozen-trader-ledger:xau-case",
        structural_stop_verified=True,
        assigned_capital=Decimal("2000"),
        risk_budget_usd=Decimal("4"),
        margin_budget_usd=Decimal("100"),
        stop_loss_per_volume=Decimal("810.8476128"),
        margin_per_volume=Decimal("1000"),
        exposure_per_volume=Decimal("100"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("50"),
        volume_step=Decimal("0.01"),
    )

    result = evaluate_capital_efficiency_sizing(spec)

    assert result.status is CapitalEfficiencyFeasibility.INFEASIBLE
    assert result.authorized_volume == 0
    assert BROKER_MINIMUM_VOLUME in result.binding_constraints


def test_volume_is_floored_to_broker_step_without_exceeding_budgets() -> None:
    result = evaluate_capital_efficiency_sizing(
        _spec(
            risk_budget="19",
            margin_budget="100",
            stop_loss_per_volume="100",
            baseline_volume=None,
        )
    )

    assert result.raw_volume_by_risk == Decimal("0.19")
    assert result.authorized_volume == Decimal("0.19")
    assert result.stop_risk_usd <= Decimal("19")
    assert result.margin_committed_usd <= Decimal("100")


def test_pareto_frontier_rejects_more_margin_for_same_exposure_and_risk() -> None:
    efficient = evaluate_capital_efficiency_sizing(
        _spec(
            experiment_id="efficient",
            risk_budget="20",
            margin_budget="100",
            margin_per_volume="100",
            baseline_volume=None,
        )
    )
    inefficient = evaluate_capital_efficiency_sizing(
        _spec(
            experiment_id="inefficient",
            risk_budget="20",
            margin_budget="100",
            margin_per_volume="200",
            baseline_volume=None,
        )
    )

    frontier = capital_efficiency_pareto_frontier(
        (inefficient, efficient)
    )

    assert frontier == (efficient,)


def test_risk_budget_cannot_exceed_assigned_capital() -> None:
    with pytest.raises(CapitalEfficiencySizingError, match="assigned_capital"):
        CapitalEfficiencySizingInput(
            experiment_id="bad-risk",
            qore_symbol="EURUSD",
            geometry_provenance="fixture",
            structural_stop_verified=True,
            assigned_capital=Decimal("100"),
            risk_budget_usd=Decimal("101"),
            margin_budget_usd=Decimal("100"),
            stop_loss_per_volume=Decimal("100"),
            margin_per_volume=Decimal("100"),
            exposure_per_volume=Decimal("10000"),
            minimum_volume=Decimal("0.01"),
            maximum_volume=Decimal("50"),
            volume_step=Decimal("0.01"),
        )
