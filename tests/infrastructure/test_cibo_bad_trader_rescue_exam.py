from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_bad_trader_rescue_exam import (
    CiboBadTraderRescueExamResult,
    CiboManagedTraderContribution,
    DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _contribution(
    trader: TraderLineage,
    pnl: str = "1.00",
) -> CiboManagedTraderContribution:
    value = Decimal(pnl)
    if value >= 0:
        gross_profit = value
        gross_loss = Decimal("0")
    else:
        gross_profit = Decimal("0")
        gross_loss = -value
    return CiboManagedTraderContribution(
        trader_id=trader,
        opportunity_count=10,
        selected_count=5,
        abstained_count=5,
        reduced_count=1,
        rejected_count=1,
        settled_count=5,
        gross_profit_usd=gross_profit,
        gross_loss_usd=gross_loss,
        net_contribution_usd=value,
    )


def _positive_surface():
    return tuple(
        _contribution(trader, "1.00")
        for trader in DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM.trader_ids
    )


def test_rescue_exam_requires_every_trader_positive() -> None:
    surface = list(_positive_surface())
    surface[3] = _contribution(surface[3].trader_id, "-0.01")

    with pytest.raises(
        CiboCapitalManagementError,
        match="did not finish positive",
    ):
        CiboBadTraderRescueExamResult(
            contract=DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM,
            opportunity_decision_count=70,
            native_max_intelligence_decision_count=70,
            full_cf_semantic_decision_count=70,
            external_ai_call_count=0,
            account_reset_count=0,
            economic_era_reset_count=0,
            ending_capital_usd=Decimal("67"),
            peak_capital_usd=Decimal("70"),
            maximum_drawdown_usd=Decimal("3"),
            trader_contributions=tuple(surface),
        )


def test_rescue_exam_rejects_external_ai_even_when_all_traders_positive() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="forbids external AI",
    ):
        CiboBadTraderRescueExamResult(
            contract=DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM,
            opportunity_decision_count=70,
            native_max_intelligence_decision_count=70,
            full_cf_semantic_decision_count=70,
            external_ai_call_count=1,
            account_reset_count=0,
            economic_era_reset_count=0,
            ending_capital_usd=Decimal("67"),
            peak_capital_usd=Decimal("70"),
            maximum_drawdown_usd=Decimal("3"),
            trader_contributions=_positive_surface(),
        )


def test_rescue_exam_rejects_any_capital_reset() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="forbids capital/era resets",
    ):
        CiboBadTraderRescueExamResult(
            contract=DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM,
            opportunity_decision_count=70,
            native_max_intelligence_decision_count=70,
            full_cf_semantic_decision_count=70,
            external_ai_call_count=0,
            account_reset_count=0,
            economic_era_reset_count=1,
            ending_capital_usd=Decimal("67"),
            peak_capital_usd=Decimal("70"),
            maximum_drawdown_usd=Decimal("3"),
            trader_contributions=_positive_surface(),
        )


def test_rescue_exam_rejects_trader_logic_changes() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        CiboBadTraderRescueExamResult(
            contract=DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM,
            opportunity_decision_count=70,
            native_max_intelligence_decision_count=70,
            full_cf_semantic_decision_count=70,
            external_ai_call_count=0,
            account_reset_count=0,
            economic_era_reset_count=0,
            ending_capital_usd=Decimal("67"),
            peak_capital_usd=Decimal("70"),
            maximum_drawdown_usd=Decimal("3"),
            trader_contributions=_positive_surface(),
            trader_logic_modified_for_exam=True,
        )


def test_rescue_exam_passes_only_with_full_positive_seven_trader_surface() -> None:
    result = CiboBadTraderRescueExamResult(
        contract=DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM,
        opportunity_decision_count=70,
        native_max_intelligence_decision_count=70,
        full_cf_semantic_decision_count=70,
        external_ai_call_count=0,
        account_reset_count=0,
        economic_era_reset_count=0,
        ending_capital_usd=Decimal("67"),
        peak_capital_usd=Decimal("70"),
        maximum_drawdown_usd=Decimal("3"),
        trader_contributions=_positive_surface(),
    )

    assert result.passed is True
    assert result.account_net_profit_usd == Decimal("7")
    assert all(
        item.net_contribution_usd > 0
        for item in result.trader_contributions
    )
