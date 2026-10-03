from decimal import Decimal

from qore.infrastructure.cibo_ce2i_advanced_actions import (
    AdvancedCapitalActionType,
    advanced_portfolio_budget_adjustment,
    build_advanced_capital_actions,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedToolDecision,
    AdvancedToolDisposition,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    AdvancedOpportunityAssessment,
    FullCe2iSurfaceAssessment,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboRegimePosture,
    CiboRegimeToolSelection,
)


def _surface() -> FullCe2iSurfaceAssessment:
    t02 = AdvancedToolDecision(
        tool_code="T02",
        disposition=AdvancedToolDisposition.APPLIED,
        reason="test structural leverage",
        selected_id="structural-oos-1",
        approved_volume=Decimal("0.02"),
        target_stop_risk_usd=Decimal("2"),
    )
    t08 = AdvancedToolDecision(
        tool_code="T08",
        disposition=AdvancedToolDisposition.APPLIED,
        reason="test verified portfolio netting",
        selected_id="netting-1",
        released_capacity_usd=Decimal("3"),
    )
    return FullCe2iSurfaceAssessment(
        mission_tools=tuple(f"T{i:02d}" for i in range(1, 21)),
        regime=CiboRegimeToolSelection(
            posture=CiboRegimePosture.STABLE,
            enabled_tools=("T02", "T08"),
            blocked_tools=(),
            reason="test",
        ),
        opportunity_assessments=(
            AdvancedOpportunityAssessment(
                signal_fingerprint="signal-1",
                decisions=(t02,),
            ),
        ),
        portfolio_decisions=(t08,),
        registry_codes=tuple(f"T{i:02d}" for i in range(1, 21)),
        complete_registry=True,
    )


def test_advanced_actions_translate_applied_tool_decisions() -> None:
    actions = build_advanced_capital_actions(_surface())

    assert len(actions) == 2
    by_tool = {item.tool_code: item for item in actions}
    assert by_tool["T02"].action_type is AdvancedCapitalActionType.SCALE_OPPORTUNITY
    assert by_tool["T02"].signal_fingerprint == "signal-1"
    assert by_tool["T02"].approved_volume == Decimal("0.02")
    assert by_tool["T08"].action_type is AdvancedCapitalActionType.APPLY_PORTFOLIO_NETTING
    assert by_tool["T08"].risk_capacity_credit_usd == Decimal("3")
    assert all(item.broker_mutation_authorized is False for item in actions)


def test_only_safe_portfolio_credits_change_global_budget() -> None:
    actions = build_advanced_capital_actions(_surface())
    adjustment = advanced_portfolio_budget_adjustment(actions)

    assert adjustment.risk_capacity_credit_usd == Decimal("3")
    assert adjustment.margin_capacity_credit_usd == Decimal("0")
