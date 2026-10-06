from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    MarginEfficiencyEvidence,
    MarginExpression,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    AdvancedOpportunityEvidence,
    AdvancedPortfolioEvidence,
    evaluate_full_ce2i_surface,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

DECISION_AT = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="causal-time-signal",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("25"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("1"),
    )


def _regime() -> CiboCapitalRegimeState:
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


def _mission():
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="causal-time-demo",
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _t03(observed_at: datetime) -> MarginEfficiencyEvidence:
    return MarginEfficiencyEvidence(
        evidence_id="t03-causal-time",
        observed_at=observed_at,
        baseline_expression_id="baseline",
        fresh_oos_utility_demonstrated=True,
        policy_authorized=True,
        expressions=(
            MarginExpression(
                expression_id="baseline",
                normalized_exposure=Decimal("1"),
                stop_risk_usd=Decimal("1"),
                margin_usd=Decimal("10"),
                all_in_cost_usd=Decimal("1"),
                executable=True,
                economics_verified=True,
            ),
            MarginExpression(
                expression_id="candidate",
                normalized_exposure=Decimal("1"),
                stop_risk_usd=Decimal("1"),
                margin_usd=Decimal("8"),
                all_in_cost_usd=Decimal("1"),
                executable=True,
                economics_verified=True,
            ),
        ),
    )


def _surface(observed_at: datetime, *, decision_at=DECISION_AT):
    opportunity = _opportunity()
    return evaluate_full_ce2i_surface(
        mission=_mission(),
        regime_state=_regime(),
        opportunities=(opportunity,),
        advanced_evidence=AdvancedPortfolioEvidence(
            opportunities=(
                AdvancedOpportunityEvidence(
                    signal_fingerprint=opportunity.signal_fingerprint,
                    margin_efficiency=_t03(observed_at),
                ),
            )
        ),
        decision_at=decision_at,
    )


def test_advanced_evidence_at_decision_time_is_temporally_eligible() -> None:
    result = _surface(DECISION_AT)

    t03 = next(
        item
        for item in result.opportunity_assessments[0].decisions
        if item.tool_code == "T03"
    )
    assert t03.selected_id == "candidate"


def test_future_advanced_evidence_fails_closed() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="T03 advanced evidence is future-known",
    ):
        _surface(DECISION_AT + timedelta(microseconds=1))


def test_nonempty_advanced_evidence_requires_explicit_decision_time() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="requires explicit decision_at",
    ):
        _surface(DECISION_AT, decision_at=None)
