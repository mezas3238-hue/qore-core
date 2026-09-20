from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    PortfolioFlowTrade,
)
from qore.infrastructure.trader_lab.capitalizer_session_flow_economics import _build_report


def _trade(index: int, realized: str) -> PortfolioFlowTrade:
    entry = datetime(2026, 1, 5, 1, 0, tzinfo=UTC) + timedelta(minutes=10 * index)
    return PortfolioFlowTrade(
        symbol="USDJPY",
        entry_at=entry,
        exit_at=entry + timedelta(minutes=5),
        realized_r=Decimal(realized),
    )


def test_session_flow_economics_exposes_third_trade_giveback_after_profit() -> None:
    report = _build_report(
        (
            _trade(0, "1"),
            _trade(1, "0.5"),
            _trade(2, "-1"),
            _trade(3, "2"),
        )
    )
    row = next(
        item
        for item in report.policy_economics
        if item.policy == "MAX3_ANY_VALID" and item.tie_policy == "SYMBOL_ASC"
    )
    assert row.metrics.trades == 3
    assert row.sessions_reaching_three == 1
    assert row.sessions_positive_before_third == 1
    assert row.third_wins_after_positive == 0
    assert row.third_losses_after_positive == 1
    assert row.third_giveback_after_positive_rate == "1"

    third = next(
        item
        for item in report.ordinal_economics
        if item.policy == "MAX3_ANY_VALID"
        and item.tie_policy == "SYMBOL_ASC"
        and item.session == "ASIA"
        and item.ordinal == 3
    )
    assert third.trades == 1
    assert third.prior_realized_positive == 1
    assert third.metrics.total_r == "-1"


def test_positive_continuation_diagnostic_does_not_turn_positive_pnl_into_stop() -> None:
    report = _build_report((_trade(0, "1"), _trade(1, "0.5"), _trade(2, "1")))
    row = next(
        item
        for item in report.policy_economics
        if item.policy == "MAX3_POSITIVE_REALIZED_CONTINUATION"
        and item.tie_policy == "SYMBOL_ASC"
    )
    assert row.metrics.trades == 3
    assert report.positive_pnl_is_not_stop_condition is True
    assert report.governed_profit_objective_not_modeled is True
    assert report.max_executions_per_session == 3


def test_uncapped_research_exposes_opportunity_loss_from_session_ceiling() -> None:
    report = _build_report(tuple(_trade(i, "1") for i in range(4)))
    uncapped = next(
        item
        for item in report.policy_economics
        if item.policy == "UNCAPPED_RESEARCH" and item.tie_policy == "SYMBOL_ASC"
    )
    capped = next(
        item
        for item in report.policy_economics
        if item.policy == "MAX3_ANY_VALID" and item.tie_policy == "SYMBOL_ASC"
    )
    assert uncapped.metrics.trades == 4
    assert uncapped.max_trades_in_one_session == 4
    assert uncapped.opportunities_rejected_by_ceiling == 0
    assert capped.metrics.trades == 3
    assert capped.max_trades_in_one_session == 3
    assert capped.opportunities_rejected_by_ceiling == 1
