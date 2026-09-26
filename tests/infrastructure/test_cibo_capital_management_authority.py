from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalStage,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    minimum_seed_volume,
    plan_minimal_seed,
    plan_self_financing_expansion,
)


def _opportunity(
    *,
    trader: TraderLineage = TraderLineage.R38_EURUSD,
    min_steps: int = 1,
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint="signal-1",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        intended_entry=Decimal("1.1000"),
        stop_loss=Decimal("1.0950"),
        take_profit=Decimal("1.1100"),
        stop_loss_per_volume=Decimal("100"),
        margin_per_volume=Decimal("200"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("10"),
        minimum_execution_steps=min_steps,
    )


def _capital(**overrides: Decimal) -> CiboCapitalState:
    values = {
        "assigned_capital_usd": Decimal("10000"),
        "hard_risk_headroom_usd": Decimal("50"),
        "margin_headroom_usd": Decimal("1000"),
        "base_capital_at_risk_usd": Decimal("0"),
        "realized_net_profit_usd": Decimal("0"),
        "protected_open_economic_floor_usd": Decimal("0"),
        "proven_self_financing_capacity_usd": Decimal("0"),
        "reserved_expansion_risk_usd": Decimal("0"),
        "cost_reserve_usd": Decimal("0"),
    }
    values.update(overrides)
    return CiboCapitalState(**values)


def test_minimum_seed_ignores_legacy_trader_risk_scale() -> None:
    opportunity = _opportunity()

    plan = plan_minimal_seed(opportunity, _capital())

    assert plan.action is CapitalAction.OPEN_MINIMAL_SEED
    assert plan.stage is CapitalStage.MINIMAL_SEED
    assert plan.volume == Decimal("0.01")
    assert plan.stop_risk_usd == Decimal("1.00")
    assert plan.capital_source is CapitalSource.ORIGINAL_BASE_CAPITAL


def test_methodology_execution_steps_can_raise_minimum_seed() -> None:
    opportunity = _opportunity(
        trader=TraderLineage.VT31_NAS100,
        min_steps=4,
    )

    assert minimum_seed_volume(opportunity) == Decimal("0.04")


def test_seed_holds_when_even_minimum_exceeds_hard_risk_headroom() -> None:
    plan = plan_minimal_seed(
        _opportunity(),
        _capital(hard_risk_headroom_usd=Decimal("0.50")),
    )

    assert plan.action is CapitalAction.HOLD
    assert plan.volume == 0
    assert "hard risk headroom" in plan.reason


def test_expansion_is_locked_while_base_capital_remains_at_risk() -> None:
    plan = plan_self_financing_expansion(
        _opportunity(),
        _capital(
            base_capital_at_risk_usd=Decimal("1"),
            realized_net_profit_usd=Decimal("20"),
            proven_self_financing_capacity_usd=Decimal("20"),
        ),
    )

    assert plan.action is CapitalAction.HOLD
    assert plan.stage is CapitalStage.PROTECT_BASE


def test_realized_profit_can_fund_expansion_after_base_recovery() -> None:
    plan = plan_self_financing_expansion(
        _opportunity(),
        _capital(
            realized_net_profit_usd=Decimal("10"),
            proven_self_financing_capacity_usd=Decimal("10"),
        ),
    )

    assert plan.action is CapitalAction.EXPAND
    assert plan.volume == Decimal("0.10")
    assert plan.stop_risk_usd == Decimal("10")
    assert plan.capital_source is CapitalSource.REALIZED_PROFIT


def test_protected_economic_floor_can_fund_bounded_expansion() -> None:
    plan = plan_self_financing_expansion(
        _opportunity(),
        _capital(
            protected_open_economic_floor_usd=Decimal("12"),
            proven_self_financing_capacity_usd=Decimal("10"),
            cost_reserve_usd=Decimal("2"),
        ),
    )

    assert plan.action is CapitalAction.EXPAND
    assert plan.stop_risk_usd == Decimal("10")
    assert plan.capital_source is CapitalSource.PROTECTED_ECONOMIC_FLOOR


def test_reserved_expansion_risk_is_subtracted_from_available_capacity() -> None:
    plan = plan_self_financing_expansion(
        _opportunity(),
        _capital(
            realized_net_profit_usd=Decimal("20"),
            proven_self_financing_capacity_usd=Decimal("20"),
            reserved_expansion_risk_usd=Decimal("15"),
        ),
    )

    assert plan.action is CapitalAction.EXPAND
    assert plan.stop_risk_usd == Decimal("5")


def test_expansion_cannot_claim_original_base_capital_source() -> None:
    with pytest.raises(CiboCapitalManagementError, match="original base capital"):
        CiboCapitalActionPlan(
            trader_id=TraderLineage.R38_EURUSD,
            qore_symbol="EURUSD",
            stage=CapitalStage.CAPITALIZE,
            action=CapitalAction.EXPAND,
            volume=Decimal("0.01"),
            stop_risk_usd=Decimal("1"),
            margin_usd=Decimal("2"),
            capital_source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            capital_source_amount_usd=Decimal("1"),
            reason="invalid",
        )


def test_zero_hard_headroom_is_representable_and_holds_seed() -> None:
    plan = plan_minimal_seed(
        _opportunity(),
        _capital(hard_risk_headroom_usd=Decimal("0")),
    )

    assert plan.action is CapitalAction.HOLD


def test_self_financing_capacity_cannot_exceed_proven_sources() -> None:
    with pytest.raises(CiboCapitalManagementError, match="cannot exceed"):
        _capital(
            realized_net_profit_usd=Decimal("5"),
            protected_open_economic_floor_usd=Decimal("5"),
            proven_self_financing_capacity_usd=Decimal("11"),
        )


def test_mixed_sources_hold_until_multi_source_ledger_reservation_exists() -> None:
    plan = plan_self_financing_expansion(
        _opportunity(),
        _capital(
            realized_net_profit_usd=Decimal("5"),
            protected_open_economic_floor_usd=Decimal("5"),
            proven_self_financing_capacity_usd=Decimal("10"),
        ),
    )

    assert plan.action is CapitalAction.HOLD
    assert "multi-source" in plan.reason
