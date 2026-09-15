from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.ict_turtle_soup_r2_all_session import M5Bar, Side
from qore.infrastructure.trader_lab.ict_turtle_soup_r2_forex_holdout import (
    _simulate_trade,
)


def _bar(
    minute: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> M5Bar:
    opened = datetime(2021, 1, 4, 12, minute, tzinfo=UTC)
    return M5Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=5),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_same_bar_stop_and_target_is_stop_first() -> None:
    bars = (
        _bar(0, open_="1.1000", high="1.1025", low="1.0985", close="1.1010"),
    )
    exited_at, exit_price, reason, gross = _simulate_trade(
        bars,
        0,
        1,
        side=Side.LONG,
        entry=Decimal("1.1000"),
        stop=Decimal("1.0990"),
        target=Decimal("1.1020"),
    )
    assert exited_at == bars[0].closed_at
    assert exit_price == Decimal("1.0990")
    assert reason == "stop-first"
    assert gross == Decimal("-1")


def test_adverse_gap_can_lose_more_than_one_r() -> None:
    bars = (
        _bar(0, open_="1.0980", high="1.0985", low="1.0975", close="1.0982"),
    )
    _at, price, reason, gross = _simulate_trade(
        bars,
        0,
        1,
        side=Side.LONG,
        entry=Decimal("1.1000"),
        stop=Decimal("1.0990"),
        target=Decimal("1.1020"),
    )
    assert price == Decimal("1.0980")
    assert reason == "gap-stop"
    assert gross == Decimal("-2")


def test_favorable_gap_does_not_receive_positive_slippage() -> None:
    bars = (
        _bar(0, open_="1.1030", high="1.1040", low="1.1025", close="1.1035"),
    )
    _at, price, reason, gross = _simulate_trade(
        bars,
        0,
        1,
        side=Side.LONG,
        entry=Decimal("1.1000"),
        stop=Decimal("1.0990"),
        target=Decimal("1.1020"),
    )
    assert price == Decimal("1.1020")
    assert reason == "target"
    assert gross == Decimal("2")


def test_intraday_time_exit_uses_final_bar_close() -> None:
    bars = (
        _bar(0, open_="1.1000", high="1.1005", low="1.0995", close="1.1002"),
        _bar(5, open_="1.1002", high="1.1008", low="1.1000", close="1.1005"),
    )
    at, price, reason, gross = _simulate_trade(
        bars,
        0,
        2,
        side=Side.LONG,
        entry=Decimal("1.1000"),
        stop=Decimal("1.0990"),
        target=Decimal("1.1020"),
    )
    assert at == bars[-1].closed_at
    assert price == Decimal("1.1005")
    assert reason == "time-exit"
    assert gross == Decimal("0.5")
