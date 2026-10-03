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
    AdvancedToolDisposition,
)
from qore.infrastructure.cibo_ce2i_full_surface import AdvancedPortfolioEvidence
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_universal_capability_runtime import (
    CAPABILITY_LAB,
    evaluate_universal_capability_lab,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


def _mission():
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="capability-lab",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _regime() -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.10"),
        margin_utilization=Decimal("0.10"),
        drawdown_utilization=Decimal("0.10"),
        opportunity_count=1,
    )


def _opportunity(symbol: str) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint=f"capability-{symbol}",
        qore_symbol=symbol,
        provider_symbol=symbol,
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("1"),
        margin_per_volume=Decimal("1"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )


def test_capability_lab_exposes_all_advanced_engines_without_certification_filter() -> None:
    result = evaluate_universal_capability_lab(
        mission=_mission(),
        regime_state=_regime(),
        opportunities=(_opportunity("BTCUSD"),),
        advanced_evidence=AdvancedPortfolioEvidence(),
    )

    assert result.capability_lab_id == CAPABILITY_LAB
    assert tuple(
        decision.tool_code
        for decision in result.surface.advanced_decisions
    ) == ("T02", "T03", "T04", "T17", "T08", "T10", "T16")
    assert all(
        decision.disposition is AdvancedToolDisposition.FAIL_CLOSED
        for decision in result.surface.advanced_decisions
    )
    assert result.advanced_actions == ()
    assert result.portfolio_budget_adjustment.risk_capacity_credit_usd == 0
    assert result.portfolio_budget_adjustment.margin_capacity_credit_usd == 0
    assert result.scientific_certification_claimed is False
    assert result.productive_authority is False
    assert result.broker_mutation_authorized is False


def test_capability_lab_is_asset_agnostic_for_noncanonical_symbols() -> None:
    for symbol in ("BTCUSD", "USDCAD", "EURAUD"):
        result = evaluate_universal_capability_lab(
            mission=_mission(),
            regime_state=_regime(),
            opportunities=(_opportunity(symbol),),
            advanced_evidence=AdvancedPortfolioEvidence(),
        )
        assert result.surface.opportunity_assessments[0].signal_fingerprint == (
            f"capability-{symbol}"
        )
