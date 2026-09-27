from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_account_sizing_authority import (
    CiboAccountSizingMode,
    account_capital_state,
    plan_account_sizing,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="account-sizing-signal",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("2600"),
        stop_loss=Decimal("2590"),
        take_profit=Decimal("2620"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )


def _mission(environment: MarketRuntimeEnvironment):
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key=(
                "ctrader-demo"
                if environment is MarketRuntimeEnvironment.DEMO
                else "fundednext"
            ),
            account_ref="account-1",
            environment=environment,
            provider_program=(
                None
                if environment is MarketRuntimeEnvironment.DEMO
                else "stellar-instant"
            ),
        )
    )


def test_demo_uses_maximum_account_constrained_capacity() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("1000"),
        hard_risk_headroom_usd=Decimal("50"),
        margin_headroom_usd=Decimal("80"),
        survival_capital_usd=Decimal("0"),
        protected_capital_usd=Decimal("0"),
    )

    decision = plan_account_sizing(
        opportunity=_opportunity(),
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.DEMO),
        survival_capital_usd=Decimal("0"),
        protected_capital_usd=Decimal("0"),
    )

    assert decision.mode is CiboAccountSizingMode.CAPABILITY_MAXIMUM
    assert decision.plan.action is CapitalAction.OPEN_CAPABILITY_MAX
    assert decision.plan.volume == Decimal("4.00")
    assert decision.plan.stop_risk_usd == Decimal("40.00")
    assert decision.plan.margin_usd == Decimal("80.00")
    assert decision.plan.capital_source is CapitalSource.ORIGINAL_BASE_CAPITAL


def test_funded_survival_uses_minimal_seed_before_capital_protection() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("2000"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("20"),
    )

    decision = plan_account_sizing(
        opportunity=_opportunity(),
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.PRODUCTION),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("20"),
    )

    assert decision.base_protected is False
    assert decision.mode is CiboAccountSizingMode.SURVIVAL_MINIMAL_SEED
    assert decision.plan.action is CapitalAction.OPEN_MINIMAL_SEED
    assert decision.plan.volume == Decimal("0.01")


def test_funded_uses_full_remaining_capacity_after_base_is_protected() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("2000"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("1000"),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("60"),
    )

    decision = plan_account_sizing(
        opportunity=_opportunity(),
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.PRODUCTION),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("60"),
    )

    assert decision.base_protected is True
    assert decision.mode is CiboAccountSizingMode.PROTECTED_FULL_CAPACITY
    assert decision.plan.action is CapitalAction.EXPAND
    assert decision.plan.volume == Decimal("6.00")
    assert decision.plan.stop_risk_usd == Decimal("60.00")
    assert decision.plan.capital_source is (
        CapitalSource.CERTIFIED_LIMITED_DOWNSIDE_CAPACITY
    )


def test_trader_identity_does_not_change_account_sizing_law() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("2000"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("1000"),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("60"),
    )
    first = plan_account_sizing(
        opportunity=_opportunity(),
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.PRODUCTION),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("60"),
    )
    second_opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="other-lineage",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )
    second = plan_account_sizing(
        opportunity=second_opportunity,
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.PRODUCTION),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("60"),
    )

    assert first.plan.volume == second.plan.volume
    assert first.mode is second.mode
