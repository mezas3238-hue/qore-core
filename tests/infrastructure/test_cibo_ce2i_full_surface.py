from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    CiboCapitalMissionPolicy,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedToolDisposition,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    AdvancedPortfolioEvidence,
    build_causal_baseline_advanced_evidence,
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


def _mission() -> CiboCapitalMissionPolicy:
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
        opportunity_count=1,
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


def test_full_surface_binds_all_twenty_tools_and_all_advanced_scopes() -> None:
    result = evaluate_full_ce2i_surface(
        mission=_mission(),
        regime_state=_state(),
        opportunities=(_opportunity(),),
        advanced_evidence=AdvancedPortfolioEvidence(),
    )

    assert result.complete_registry is True
    assert result.registry_codes == tuple(
        f"T{index:02d}" for index in range(1, 21)
    )
    assert result.mission_tools == result.registry_codes
    assert len(result.opportunity_assessments) == 1
    assert tuple(
        item.tool_code
        for item in result.opportunity_assessments[0].decisions
    ) == ("T02", "T03", "T04", "T17")
    assert tuple(item.tool_code for item in result.portfolio_decisions) == (
        "T08",
        "T10",
        "T16",
    )
    assert all(
        item.disposition is AdvancedToolDisposition.FAIL_CLOSED
        for item in result.advanced_decisions
    )
    assert len(result.runtime_receipts) == 1
    receipt = result.runtime_receipts[0]
    assert receipt.tool_code == "T12"
    assert receipt.engine_name == "select_ce2i_tools_for_regime"
    assert receipt.downstream_consumer == "cibo-full-ce2i-surface"
    assert receipt.consumer_action == "regime-tool-selection-consumed"
    assert receipt.native_engine_called is True
    assert receipt.outcome_used is False
    assert receipt.risk_authority is False
    assert receipt.execution_authority is False



def test_causal_baseline_feeds_advanced_engines_without_inventing_oos() -> None:
    observed_at = datetime(2020, 1, 2, 12, tzinfo=UTC)
    opportunity = _opportunity()
    evidence = build_causal_baseline_advanced_evidence(
        opportunities=(opportunity,),
        decision_at=observed_at,
    )

    assert len(evidence.opportunities) == 1
    row = evidence.opportunities[0]
    assert row.margin_efficiency is not None
    assert row.margin_efficiency.fresh_oos_utility_demonstrated is False
    assert len(row.margin_efficiency.expressions) == 1
    assert row.risk_efficiency is not None
    assert len(row.risk_efficiency.candidates) == 1
    assert row.risk_efficiency.candidates[0].evidence_oos is False
    assert row.convex_exposure is not None
    assert row.convex_exposure.instruments == ()
    assert evidence.portfolio_netting is not None
    assert evidence.portfolio_netting.factor_map_verified is False
    assert evidence.capital_velocity is not None
    assert len(evidence.capital_velocity.policies) == 1
    assert evidence.hedged_exposure is not None
    assert evidence.hedged_exposure.instruments == ()

    result = evaluate_full_ce2i_surface(
        mission=_mission(),
        regime_state=_state(),
        opportunities=(opportunity,),
        advanced_evidence=evidence,
        decision_at=observed_at,
    )
    by_code = {item.tool_code: item for item in result.advanced_decisions}
    assert by_code["T03"].disposition is AdvancedToolDisposition.ABSTAIN
    assert by_code["T04"].disposition is AdvancedToolDisposition.ABSTAIN
    assert by_code["T08"].disposition is AdvancedToolDisposition.ABSTAIN
    assert by_code["T10"].disposition is AdvancedToolDisposition.ABSTAIN
    assert by_code["T16"].disposition is AdvancedToolDisposition.ABSTAIN
    assert by_code["T17"].disposition is AdvancedToolDisposition.ABSTAIN
    assert by_code["T02"].disposition is AdvancedToolDisposition.FAIL_CLOSED
