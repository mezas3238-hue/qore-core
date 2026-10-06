from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_maximum_capability_reasoning_policy import (
    select_cibo_maximum_capability_reasoning_route,
)
from qore.infrastructure.cibo_reasoning_policy import CiboReasoningRouteTier
from qore.infrastructure.cibo_sovereign_function_consultation import (
    consult_cibo_economic_faculties,
)
from qore.modules.cibo.cognitive_contracts import CiboReasoningMode


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="maxcap-route-001",
        qore_symbol="NAS100",
        provider_symbol="NAS100",
        side="long",
        entry_type="market",
        intended_entry=Decimal("20000"),
        stop_loss=Decimal("19980"),
        take_profit=Decimal("20060"),
        stop_loss_per_volume=Decimal("20"),
        margin_per_volume=Decimal("25"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("10"),
        decision_context=(("ctx_session", "NEW_YORK"),),
    )


def _regime() -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.05"),
        margin_utilization=Decimal("0.05"),
        drawdown_utilization=Decimal("0"),
        opportunity_count=1,
    )


def test_maximum_capability_exam_uses_existing_sol_max_route() -> None:
    regime = _regime()
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(_opportunity(),),
        regime_state=regime,
    )

    route = select_cibo_maximum_capability_reasoning_route(
        consultation=consultation,
        regime_state=regime,
    )

    assert route.tier is CiboReasoningRouteTier.SOL_MAX
    assert route.semantic_mode is CiboReasoningMode.MAX
    assert route.model == "gpt-5.6-sol"
    assert route.provider_reasoning_effort == "max"
