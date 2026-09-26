# ruff: noqa: I001
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
    fundednext_stellar_instant_identity,
)
from qore.infrastructure.cibo_ce2i_optionality import (
    KnownCapitalOption,
    plan_capital_optionality,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


def _mission_demo():
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="demo-free",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _mission_funded():
    return derive_cibo_capital_mission(
        fundednext_stellar_instant_identity(
            account_ref="stellar-instant-2k"
        )
    )


def _regime(mission, *, dd: str = "0.20", adverse: bool = False):
    return select_ce2i_tools_for_regime(
        mission=mission,
        state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.20"),
            margin_utilization=Decimal("0.20"),
            drawdown_utilization=Decimal(dd),
            opportunity_count=2,
            position_path_adverse=adverse,
        ),
    )


OPTIONS = (
    KnownCapitalOption(
        opportunity_id="next-small",
        minimum_stop_risk_usd=Decimal("4"),
        minimum_margin_usd=Decimal("20"),
    ),
    KnownCapitalOption(
        opportunity_id="next-large",
        minimum_stop_risk_usd=Decimal("10"),
        minimum_margin_usd=Decimal("40"),
    ),
)


def test_funded_mission_reserves_capacity_for_any_one_known_option() -> None:
    mission = _mission_funded()
    decision = plan_capital_optionality(
        mission=mission,
        regime=_regime(mission),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=OPTIONS,
    )

    assert decision.reserve_stop_risk_usd == Decimal("10")
    assert decision.reserve_margin_usd == Decimal("40")
    assert decision.deployable_stop_risk_usd == Decimal("50")
    assert decision.preserve_new_capital is True


def test_demo_stable_uses_full_capacity_for_capability_discovery() -> None:
    mission = _mission_demo()
    decision = plan_capital_optionality(
        mission=mission,
        regime=_regime(mission),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=OPTIONS,
    )

    assert decision.reserve_stop_risk_usd == 0
    assert decision.deployable_stop_risk_usd == Decimal("60")
    assert decision.preserve_new_capital is False


def test_demo_defensive_preserves_cheapest_known_option() -> None:
    mission = _mission_demo()
    decision = plan_capital_optionality(
        mission=mission,
        regime=_regime(mission, adverse=True),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=OPTIONS,
    )

    assert decision.reserve_stop_risk_usd == Decimal("4")
    assert decision.reserve_margin_usd == Decimal("20")
    assert decision.reserved_for_opportunity_ids == ("next-small",)


def test_recovery_preserves_all_remaining_capacity() -> None:
    mission = _mission_demo()
    decision = plan_capital_optionality(
        mission=mission,
        regime=_regime(mission, dd="0.80"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=OPTIONS,
    )

    assert decision.reserve_stop_risk_usd == Decimal("60")
    assert decision.reserve_margin_usd == Decimal("500")
    assert decision.deployable_stop_risk_usd == 0
    assert decision.deployable_margin_usd == 0
    assert decision.preserve_new_capital is True
