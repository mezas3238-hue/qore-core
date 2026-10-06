from decimal import Decimal, localcontext

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    CiboCapitalMissionPolicy,
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
    CapitalSourceLot,
    CapitalStage,
    CiboCapitalActionPlan,
    CiboCapitalState,
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


def _mission(
    environment: MarketRuntimeEnvironment,
) -> CiboCapitalMissionPolicy:
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
        CapitalSource.REALIZED_PROFIT
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


def test_demo_capability_sizing_uses_profit_provenance_after_growth() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("80"),
        margin_headroom_usd=Decimal("160"),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("40"),
    )

    decision = plan_account_sizing(
        opportunity=_opportunity(),
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.DEMO),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("40"),
    )

    assert decision.plan.stop_risk_usd == Decimal("80.00")
    assert decision.plan.capital_source is None
    assert tuple(
        (lot.source, lot.amount_usd)
        for lot in decision.plan.capital_source_lots
    ) == (
        (CapitalSource.ORIGINAL_BASE_CAPITAL, Decimal("60")),
        (CapitalSource.REALIZED_PROFIT, Decimal("20.00")),
    )


def test_demo_capability_sizing_does_not_label_profit_as_original_base() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("120"),
        hard_risk_headroom_usd=Decimal("70"),
        margin_headroom_usd=Decimal("140"),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("60"),
    )

    decision = plan_account_sizing(
        opportunity=_opportunity(),
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.DEMO),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("60"),
    )

    assert decision.plan.stop_risk_usd == Decimal("70.00")
    lots = {lot.source: lot.amount_usd for lot in decision.plan.capital_source_lots}
    assert lots[CapitalSource.ORIGINAL_BASE_CAPITAL] == Decimal("60")
    assert lots[CapitalSource.REALIZED_PROFIT] == Decimal("10.00")


def test_demo_maximum_sizing_reserves_provider_cost_inside_capital() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("60"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("1000"),
        survival_capital_usd=Decimal("0"),
        protected_capital_usd=Decimal("0"),
    )

    decision = plan_account_sizing(
        opportunity=_opportunity(),
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.DEMO),
        survival_capital_usd=Decimal("0"),
        protected_capital_usd=Decimal("0"),
        provider_cost_per_volume_usd=Decimal("2"),
    )

    assert decision.mode is CiboAccountSizingMode.CAPABILITY_MAXIMUM
    assert decision.plan.volume == Decimal("5.00")
    assert decision.plan.stop_risk_usd == Decimal("50.00")
    assert (
        decision.plan.volume
        * (
            _opportunity().stop_loss_per_volume
            + Decimal("2")
        )
        == Decimal("60.00")
    )

def test_demo_capability_sizing_respects_current_source_availability() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("50"),
        margin_headroom_usd=Decimal("1000"),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("40"),
    )

    decision = plan_account_sizing(
        opportunity=_opportunity(),
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.DEMO),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("40"),
        original_base_available_usd=Decimal("20"),
        realized_profit_available_usd=Decimal("40"),
    )

    assert decision.plan.stop_risk_usd == Decimal("50.00")
    assert decision.plan.capital_source is None
    assert tuple(
        (lot.source, lot.amount_usd)
        for lot in decision.plan.capital_source_lots
    ) == (
        (CapitalSource.ORIGINAL_BASE_CAPITAL, Decimal("20")),
        (CapitalSource.REALIZED_PROFIT, Decimal("30.00")),
    )


def test_self_financing_identity_preserves_long_decimal_sources() -> None:
    realized = Decimal("1.11111111111111111111111111111")
    protected = Decimal("2.22222222222222222222222222222")
    proven = Decimal("3.33333333333333333333333333333")
    reserved = Decimal("1.11111111111111111111111111111")

    capital = CiboCapitalState(
        assigned_capital_usd=Decimal("60"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("60"),
        base_capital_at_risk_usd=Decimal("0"),
        realized_net_profit_usd=realized,
        protected_open_economic_floor_usd=protected,
        proven_self_financing_capacity_usd=proven,
        reserved_expansion_risk_usd=reserved,
        cost_reserve_usd=Decimal("0"),
    )

    with localcontext() as context:
        context.prec = 100
        assert capital.proven_self_financing_capacity_usd <= realized + protected
    assert capital.available_self_financing_capacity_usd == Decimal(
        "2.22222222222222222222222222222"
    )



def test_capital_source_lots_conserve_long_decimal_source_amount_exactly() -> None:
    first = Decimal("1.1111111111111111111111111111111111111111")
    second = Decimal("2.2222222222222222222222222222222222222222")
    total = Decimal("3.3333333333333333333333333333333333333333")

    plan = CiboCapitalActionPlan(
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        stage=CapitalStage.CAPITALIZE,
        action=CapitalAction.OPEN_CAPABILITY_MAX,
        volume=Decimal("1"),
        stop_risk_usd=total,
        margin_usd=Decimal("1"),
        capital_source=None,
        capital_source_amount_usd=total,
        reason="exact provenance conservation",
        capital_source_lots=(
            CapitalSourceLot(
                source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                amount_usd=first,
                source_id="base",
            ),
            CapitalSourceLot(
                source=CapitalSource.REALIZED_PROFIT,
                amount_usd=second,
                source_id="profit",
            ),
        ),
    )

    assert plan.capital_source_amount_usd == total



def test_demo_maximum_sizing_preserves_long_decimal_geometry_exactly() -> None:
    volume = Decimal("2.2222222222222222222222222222222222222222")
    stop_per_volume = Decimal(
        "1.1111111111111111111111111111111111111111"
    )
    margin_per_volume = Decimal(
        "1.3333333333333333333333333333333333333333"
    )
    step = Decimal("0.0000000000000000000000000000000000000001")
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="account-sizing-long-decimal",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("2600"),
        stop_loss=Decimal("2590"),
        take_profit=Decimal("2620"),
        stop_loss_per_volume=stop_per_volume,
        margin_per_volume=margin_per_volume,
        volume_step=step,
        minimum_volume=step,
        maximum_volume=volume,
    )
    capital = account_capital_state(
        assigned_capital_usd=Decimal("60"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("60"),
        survival_capital_usd=Decimal("0"),
        protected_capital_usd=Decimal("0"),
    )

    decision = plan_account_sizing(
        opportunity=opportunity,
        capital=capital,
        mission_policy=_mission(MarketRuntimeEnvironment.DEMO),
        survival_capital_usd=Decimal("0"),
        protected_capital_usd=Decimal("0"),
    )

    with localcontext() as context:
        context.prec = 100
        expected_risk = volume * stop_per_volume
        expected_margin = volume * margin_per_volume
    assert decision.plan.volume == volume
    assert decision.plan.stop_risk_usd == expected_risk
    assert decision.plan.margin_usd == expected_margin

def test_demo_maximum_sizing_holds_when_minimum_seed_is_not_executable() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("1"),
        hard_risk_headroom_usd=Decimal("0.05"),
        margin_headroom_usd=Decimal("100"),
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
    assert decision.plan.action is CapitalAction.HOLD
    assert decision.plan.volume == Decimal("0")
    assert decision.plan.stop_risk_usd == Decimal("0")
    assert decision.plan.margin_usd == Decimal("0")
    assert (
        decision.plan.reason
        == "maximum account-constrained capacity cannot express minimum seed"
    )


def test_demo_maximum_sizing_holds_when_no_deployable_headroom_remains() -> None:
    capital = account_capital_state(
        assigned_capital_usd=Decimal("1"),
        hard_risk_headroom_usd=Decimal("0"),
        margin_headroom_usd=Decimal("100"),
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
    assert decision.plan.action is CapitalAction.HOLD
    assert decision.plan.volume == Decimal("0")
    assert decision.plan.reason == "CIBO account has no deployable risk/margin headroom"

