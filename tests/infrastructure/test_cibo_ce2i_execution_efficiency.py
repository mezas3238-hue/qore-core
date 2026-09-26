# ruff: noqa: I001
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalStage,
    CiboCapitalActionPlan,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_execution_efficiency import (
    ExecutionCostCurveInput,
    cap_expansion_plan_by_execution,
    execution_efficient_volume_cap,
)


def _curve(**overrides: object) -> ExecutionCostCurveInput:
    values: dict[str, object] = {
        "evidence_id": "curve-1",
        "volume_step": Decimal("1"),
        "maximum_volume": Decimal("10"),
        "gross_edge_per_volume_usd": Decimal("10"),
        "spread_cost_per_volume_usd": Decimal("1"),
        "commission_cost_per_volume_usd": Decimal("1"),
        "slippage_cost_per_volume_usd": Decimal("0"),
        "impact_cost_per_volume_squared_usd": Decimal("1"),
    }
    values.update(overrides)
    return ExecutionCostCurveInput(**values)  # type: ignore[arg-type]


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="signal-1",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        stop_loss_per_volume=Decimal("2"),
        margin_per_volume=Decimal("3"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
    )


def _plan(volume: str = "10") -> CiboCapitalActionPlan:
    value = Decimal(volume)
    return CiboCapitalActionPlan(
        trader_id=TraderLineage.R38_EURUSD,
        qore_symbol="EURUSD",
        stage=CapitalStage.CAPITALIZE,
        action=CapitalAction.EXPAND,
        volume=value,
        stop_risk_usd=value * Decimal("2"),
        margin_usd=value * Decimal("3"),
        capital_source=CapitalSource.REALIZED_PROFIT,
        capital_source_amount_usd=value * Decimal("2"),
        reason="test expansion",
    )


def test_positive_linear_edge_without_impact_keeps_maximum_volume() -> None:
    cap = execution_efficient_volume_cap(
        _curve(impact_cost_per_volume_squared_usd=Decimal("0"))
    )

    assert cap.volume_cap == Decimal("10")
    assert cap.net_expectancy_usd == Decimal("80")
    assert cap.marginal_next_step_net_usd is None


def test_linear_cost_above_edge_rejects_all_expansion() -> None:
    cap = execution_efficient_volume_cap(
        _curve(
            gross_edge_per_volume_usd=Decimal("2"),
            spread_cost_per_volume_usd=Decimal("2"),
            commission_cost_per_volume_usd=Decimal("1"),
        )
    )

    assert cap.volume_cap == 0
    assert cap.net_expectancy_usd == 0
    assert cap.marginal_next_step_net_usd is not None
    assert cap.marginal_next_step_net_usd < 0


def test_nonlinear_impact_stops_before_negative_marginal_step() -> None:
    cap = execution_efficient_volume_cap(_curve())

    assert cap.volume_cap == Decimal("4")
    assert cap.net_expectancy_usd == Decimal("16")
    assert cap.marginal_next_step_net_usd == Decimal("-1")


def test_execution_cap_reduces_existing_expansion_plan() -> None:
    cap = execution_efficient_volume_cap(_curve())
    plan = cap_expansion_plan_by_execution(
        plan=_plan("10"),
        opportunity=_opportunity(),
        cap=cap,
    )

    assert plan.action is CapitalAction.EXPAND
    assert plan.volume == Decimal("4")
    assert plan.stop_risk_usd == Decimal("8")
    assert plan.margin_usd == Decimal("12")
    assert plan.capital_source_amount_usd == Decimal("8")


def test_execution_cap_below_provider_minimum_returns_hold() -> None:
    cap = execution_efficient_volume_cap(
        _curve(
            volume_step=Decimal("0.25"),
            maximum_volume=Decimal("0.75"),
            gross_edge_per_volume_usd=Decimal("2"),
            spread_cost_per_volume_usd=Decimal("2"),
            commission_cost_per_volume_usd=Decimal("1"),
        )
    )
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="signal-1",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        stop_loss_per_volume=Decimal("2"),
        margin_per_volume=Decimal("3"),
        volume_step=Decimal("0.25"),
        minimum_volume=Decimal("0.50"),
        maximum_volume=Decimal("10"),
    )

    plan = cap_expansion_plan_by_execution(
        plan=_plan("1"),
        opportunity=opportunity,
        cap=cap,
    )

    assert plan.action is CapitalAction.HOLD
    assert plan.volume == 0
