from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_h4_amd_v2_backtest import (
    Vt08CrtH4AmdV2Trade,
    _Bar,
    _terminal_trade,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    Vt08CrtH4AmdV2Scenario,
    Vt08CrtH4AmdV2Setup,
)


def _setup(start: datetime) -> Vt08CrtH4AmdV2Setup:
    return Vt08CrtH4AmdV2Setup(
        side=DemoTradingSetupSide.LONG,
        scenario=Vt08CrtH4AmdV2Scenario.CANDLE2_EXPANSION,
        entry_price=Decimal("100"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("110"),
        signal_at=start,
        expires_at=start + timedelta(minutes=30),
        cisd_level=Decimal("99"),
        manipulation_extreme=Decimal("95"),
        manipulation_fraction_of_reference=Decimal("0.4"),
    )


def _bar(start: datetime, low: str, high: str, close: str) -> _Bar:
    return _Bar(
        opened_at=start,
        closed_at=start + timedelta(minutes=15),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_positive_h4_close_without_target_is_censored_not_a_win() -> None:
    start = datetime(2026, 1, 1, 10, tzinfo=UTC)
    setup = _setup(start)
    path = (
        _bar(start, "99", "105", "104"),
        _bar(start + timedelta(minutes=15), "103", "108", "107"),
    )
    result: Vt08CrtH4AmdV2Trade = _terminal_trade(
        setup, path, expected_terminal=start + timedelta(minutes=30)
    )
    assert result.outcome == "h4_close_censored"
    assert result.r_multiple is None
    assert result.mark_to_market_r_at_h4_close > 0


def test_target_and_stop_are_the_only_terminal_outcomes_and_stop_is_conservative() -> None:
    start = datetime(2026, 1, 1, 10, tzinfo=UTC)
    setup = _setup(start)
    both = (_bar(start, "94", "111", "105"),)
    result = _terminal_trade(
        setup, both, expected_terminal=start + timedelta(minutes=15)
    )
    assert result.outcome == "stop"
    assert result.r_multiple == Decimal("-1")
