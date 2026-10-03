from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalState,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capability_exam_cognitive_coverage import (
    build_cibo_capability_cognitive_coverage,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedToolDisposition,
)
from qore.infrastructure.cibo_ce2i_dynamic_derisking import CiboDeRiskingInput
from qore.infrastructure.cibo_ce2i_full_surface import AdvancedPortfolioEvidence
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicEnvelope,
)
from qore.infrastructure.cibo_universal_capability_runtime import (
    CAPABILITY_LAB,
    CapabilityLabRuntimeInputs,
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


def _cognitive():
    return build_cibo_capability_cognitive_coverage(
        source_batch_sha256="sha256:" + "a" * 64,
        observed_at=datetime(2026, 10, 3, 2, tzinfo=UTC),
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


def _runtime_inputs(
    *,
    symbol: str,
    signal: str,
) -> CapabilityLabRuntimeInputs:
    realized = CiboCapitalState(
        assigned_capital_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("20"),
        base_capital_at_risk_usd=Decimal("0"),
        realized_net_profit_usd=Decimal("10"),
        protected_open_economic_floor_usd=Decimal("0"),
        proven_self_financing_capacity_usd=Decimal("10"),
        reserved_expansion_risk_usd=Decimal("0"),
        cost_reserve_usd=Decimal("0"),
    )
    protected = CiboCapitalState(
        assigned_capital_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("20"),
        base_capital_at_risk_usd=Decimal("0"),
        realized_net_profit_usd=Decimal("0"),
        protected_open_economic_floor_usd=Decimal("10"),
        proven_self_financing_capacity_usd=Decimal("10"),
        reserved_expansion_risk_usd=Decimal("0"),
        cost_reserve_usd=Decimal("0"),
    )
    envelope = ProviderEconomicEnvelope(
        provider_key="capability-lab",
        qore_symbol=symbol,
        provider_symbol=symbol,
        side="long",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        contract_size=Decimal("1"),
        notional_per_volume_usd=Decimal("100"),
        provider_units_per_volume=Decimal("1"),
        raw_stop_loss_per_volume_usd=Decimal("1"),
        cibo_stop_loss_per_volume_usd=Decimal("1"),
        spread_cost_per_volume_usd=Decimal("0"),
        commission_per_volume_usd=Decimal("0"),
        slippage_reserve_per_volume_usd=Decimal("0"),
        execution_cost_per_volume_usd=Decimal("0"),
        margin_per_volume_usd=Decimal("1"),
        minimum_execution_steps=1,
        minimum_executable_volume=Decimal("0.01"),
        minimum_provider_units=Decimal("0.01"),
        minimum_stop_risk_usd=Decimal("0.01"),
        minimum_margin_usd=Decimal("0.01"),
        minimum_execution_cost_usd=Decimal("0"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        observed_at=datetime(2026, 10, 3, 2, tzinfo=UTC),
    )
    derisk = CiboDeRiskingInput(
        current_volume=Decimal("1"),
        minimum_retained_volume=Decimal("0.01"),
        volume_step=Decimal("0.01"),
        stop_risk_per_volume_usd=Decimal("1"),
        margin_per_volume_usd=Decimal("1"),
        maximum_retained_stop_risk_usd=Decimal("0.50"),
        maximum_retained_margin_usd=Decimal("0.50"),
        methodology_position_valid=True,
    )
    return CapabilityLabRuntimeInputs(
        realized_profit_state=realized,
        protected_capacity_state=protected,
        provider_envelopes=((symbol, envelope),),
        derisk_inputs=((signal, derisk),),
    )


def test_capability_lab_exposes_all_advanced_engines_without_certification_filter() -> None:
    result = evaluate_universal_capability_lab(
        mission=_mission(),
        regime_state=_regime(),
        opportunities=(_opportunity("BTCUSD"),),
        advanced_evidence=AdvancedPortfolioEvidence(),
        cognitive_coverage=_cognitive(),
        runtime_inputs=_runtime_inputs(
            symbol="BTCUSD",
            signal="capability-BTCUSD",
        ),
    )

    assert result.capability_lab_id == CAPABILITY_LAB
    assert result.cognitive_coverage.complete is True
    assert result.cognitive_coverage.cognitive_used is True
    assert tuple(
        decision.tool_code for decision in result.surface.advanced_decisions
    ) == ("T02", "T03", "T04", "T17", "T08", "T10", "T16")
    assert all(
        decision.disposition is AdvancedToolDisposition.FAIL_CLOSED
        for decision in result.surface.advanced_decisions
    )
    assert result.advanced_actions == ()
    assert tuple(
        receipt.tool_code for receipt in result.runtime_tool_receipts
    ) == ("T06", "T07", "T11", "T14")
    assert all(
        receipt.functional_pass for receipt in result.runtime_tool_receipts
    )
    assert result.portfolio_budget_adjustment.risk_capacity_credit_usd == 0
    assert result.portfolio_budget_adjustment.margin_capacity_credit_usd == 0
    assert result.scientific_certification_claimed is False
    assert result.productive_authority is False
    assert result.broker_mutation_authorized is False


def test_capability_lab_is_asset_agnostic_for_noncanonical_symbols() -> None:
    for symbol in ("BTCUSD", "USDCAD", "EURAUD"):
        signal = f"capability-{symbol}"
        result = evaluate_universal_capability_lab(
            mission=_mission(),
            regime_state=_regime(),
            opportunities=(_opportunity(symbol),),
            advanced_evidence=AdvancedPortfolioEvidence(),
            cognitive_coverage=_cognitive(),
            runtime_inputs=_runtime_inputs(
                symbol=symbol,
                signal=signal,
            ),
        )
        assert result.surface.opportunity_assessments[0].signal_fingerprint == signal
        assert all(
            receipt.functional_pass for receipt in result.runtime_tool_receipts
        )
