from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedCe2iEvidenceBundle,
    AdvancedToolDisposition,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    evaluate_full_ce2i_surface,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)


def _mission():
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="demo-free",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _state() -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.20"),
        margin_utilization=Decimal("0.20"),
        drawdown_utilization=Decimal("0.20"),
        opportunity_count=3,
    )


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="signal-001",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("3800"),
        stop_loss=Decimal("3790"),
        take_profit=Decimal("3820"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("25"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("1"),
    )


def test_full_surface_binds_all_twenty_tools_and_all_advanced_engines() -> None:
    result = evaluate_full_ce2i_surface(
        mission=_mission(),
        regime_state=_state(),
        opportunity=_opportunity(),
        advanced_evidence=AdvancedCe2iEvidenceBundle(),
    )

    assert result.complete_registry is True
    assert result.registry_codes == tuple(
        f"T{index:02d}" for index in range(1, 21)
    )
    assert result.mission_tools == result.registry_codes
    assert tuple(item.tool_code for item in result.advanced_decisions) == (
        "T02",
        "T03",
        "T04",
        "T08",
        "T10",
        "T16",
        "T17",
    )
    assert all(
        item.disposition is AdvancedToolDisposition.FAIL_CLOSED
        for item in result.advanced_decisions
    )
