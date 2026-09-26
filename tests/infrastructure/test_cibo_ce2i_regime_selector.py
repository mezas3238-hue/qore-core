# ruff: noqa: I001
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
    fundednext_stellar_instant_identity,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimePosture,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


def _demo():
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="demo-free",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _funded():
    return derive_cibo_capital_mission(
        fundednext_stellar_instant_identity(
            account_ref="stellar-instant-2k"
        )
    )


def _state(
    *,
    liquidity: LiquidityState = LiquidityState.NORMAL,
    volatility: VolatilityState = VolatilityState.NORMAL,
    correlation: CorrelationState = CorrelationState.NORMAL,
    provider: ProviderCondition = ProviderCondition.HEALTHY,
    risk: str = "0.20",
    margin: str = "0.20",
    dd: str = "0.20",
    opportunities: int = 3,
    adverse: bool = False,
    stale: bool = False,
) -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=liquidity,
        volatility=volatility,
        correlation=correlation,
        provider_condition=provider,
        risk_utilization=Decimal(risk),
        margin_utilization=Decimal(margin),
        drawdown_utilization=Decimal(dd),
        opportunity_count=opportunities,
        position_path_adverse=adverse,
        evidence_stale=stale,
    )


def test_demo_stable_regime_exposes_implemented_capability_surface() -> None:
    decision = select_ce2i_tools_for_regime(
        mission=_demo(),
        state=_state(),
    )

    assert decision.posture is CiboRegimePosture.WATCH
    for code in ("T01", "T06", "T07", "T09", "T11", "T18", "T19", "T20"):
        assert code in decision.enabled_tools


def test_funded_regime_never_promotes_unvalidated_advanced_tools() -> None:
    decision = select_ce2i_tools_for_regime(
        mission=_funded(),
        state=_state(opportunities=1),
    )

    assert decision.posture is CiboRegimePosture.STABLE
    assert decision.enabled_tools == ("T01", "T19", "T20")


def test_provider_degradation_blocks_new_capital_even_in_demo() -> None:
    decision = select_ce2i_tools_for_regime(
        mission=_demo(),
        state=_state(
            provider=ProviderCondition.DEGRADED,
            opportunities=3,
        ),
    )

    assert decision.posture is CiboRegimePosture.DEFENSIVE
    assert "T01" not in decision.enabled_tools
    assert "T06" not in decision.enabled_tools
    assert "T07" not in decision.enabled_tools
    assert "T20" in decision.enabled_tools


def test_recovery_posture_blocks_expansion_and_competition() -> None:
    decision = select_ce2i_tools_for_regime(
        mission=_demo(),
        state=_state(dd="0.80"),
    )

    assert decision.posture is CiboRegimePosture.RECOVERY
    assert "T06" not in decision.enabled_tools
    assert "T07" not in decision.enabled_tools
    assert "T09" not in decision.enabled_tools
    assert "T18" not in decision.enabled_tools
    assert "T11" in decision.enabled_tools
    assert "T20" in decision.enabled_tools


def test_single_opportunity_removes_competition_tools() -> None:
    decision = select_ce2i_tools_for_regime(
        mission=_demo(),
        state=_state(opportunities=1),
    )

    assert "T09" not in decision.enabled_tools
    assert "T18" not in decision.enabled_tools


def test_stale_evidence_fails_closed_to_release_only() -> None:
    decision = select_ce2i_tools_for_regime(
        mission=_demo(),
        state=_state(stale=True),
    )

    assert decision.posture is CiboRegimePosture.HALT_NEW_CAPITAL
    assert decision.enabled_tools == ("T20",)
