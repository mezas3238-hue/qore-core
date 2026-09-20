from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    SOURCE_STRATEGY_GRAMMAR_ID,
    CapitalizerSourceEntryRoute,
    CapitalizerSourceStrategyAssessment,
    CapitalizerSourceStrategyDecision,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
    CapitalizerSourceTradePlanFacts,
    build_source_trade_plan,
)


def _assessment(
    decision: CapitalizerSourceStrategyDecision,
) -> CapitalizerSourceStrategyAssessment:
    del CapitalizerCognitiveGateDecision
    return CapitalizerSourceStrategyAssessment(
        grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
        symbol="EURUSD",
        route=CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION,
        decision=decision,
        reasons=("TEST_REASON",),
    )


def test_eligible_long_plan_uses_protected_swing_and_structural_target() -> None:
    plan = build_source_trade_plan(
        CapitalizerSourceTradePlanFacts(
            symbol="EURUSD",
            side=CapitalizerSide.LONG,
            route=CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION,
            entry_price=Decimal("1.1000"),
            protected_swing_price=Decimal("1.0980"),
            structural_target_price=Decimal("1.1040"),
            target_kind=CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE,
            strategy_assessment=_assessment(
                CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK
            ),
        )
    )

    assert plan.initial_stop_price == Decimal("1.0980")
    assert plan.target_price == Decimal("1.1040")
    assert plan.stop_anchor == "LOGICAL_PROTECTED_SWING"
    assert plan.target_anchor == "STRUCTURAL_OR_HIGHER_TIMEFRAME_OBJECTIVE"
    assert plan.fixed_r_target_invented is False
    assert plan.executes_trade is False
    assert plan.grants_capital_authority is False


def test_trade_plan_rejects_noneligible_strategy_assessment() -> None:
    with pytest.raises(ValueError, match="ELIGIBLE_FOR_QORE_RISK"):
        build_source_trade_plan(
            CapitalizerSourceTradePlanFacts(
                symbol="EURUSD",
                side=CapitalizerSide.LONG,
                route=CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION,
                entry_price=Decimal("1.1000"),
                protected_swing_price=Decimal("1.0980"),
                structural_target_price=Decimal("1.1040"),
                target_kind=CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW,
                strategy_assessment=_assessment(
                    CapitalizerSourceStrategyDecision.WAIT
                ),
            )
        )


def test_long_plan_requires_correct_structural_geometry() -> None:
    with pytest.raises(ValueError, match="stop < entry < target"):
        build_source_trade_plan(
            CapitalizerSourceTradePlanFacts(
                symbol="EURUSD",
                side=CapitalizerSide.LONG,
                route=CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION,
                entry_price=Decimal("1.1000"),
                protected_swing_price=Decimal("1.1010"),
                structural_target_price=Decimal("1.1040"),
                target_kind=CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW,
                strategy_assessment=_assessment(
                    CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK
                ),
            )
        )
