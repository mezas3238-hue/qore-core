from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    PortfolioFlowTrade,
    _select,
)


def _trade(symbol: str, index: int, realized: str) -> PortfolioFlowTrade:
    entry = datetime(2026, 1, 5, 1, 0, tzinfo=UTC) + timedelta(minutes=10 * index)
    return PortfolioFlowTrade(
        symbol=symbol,
        entry_at=entry,
        exit_at=entry + timedelta(minutes=5),
        realized_r=Decimal(realized),
    )


def test_portfolio_ceiling_is_shared_across_symbols() -> None:
    trades = (
        _trade("AUDJPY", 0, "1"),
        _trade("AUDUSD", 1, "1"),
        _trade("GBPJPY", 2, "1"),
        _trade("USDJPY", 3, "1"),
    )
    selected = _select(trades, mode="MAX3_ANY_VALID", tie_policy="SYMBOL_ASC")
    assert len(selected) == 3
    assert {item.symbol for item in selected} == {"AUDJPY", "AUDUSD", "GBPJPY"}


def test_positive_third_requires_realized_profit_before_candidate() -> None:
    trades = (
        _trade("AUDJPY", 0, "-1"),
        _trade("AUDUSD", 1, "0.5"),
        _trade("GBPJPY", 2, "1"),
    )
    selected = _select(
        trades,
        mode="MAX3_POSITIVE_REALIZED_CONTINUATION",
        tie_policy="SYMBOL_ASC",
    )
    assert len(selected) == 2
