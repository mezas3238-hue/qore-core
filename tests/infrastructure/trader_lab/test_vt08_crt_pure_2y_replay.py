from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    AggregatedCandle,
    ReplayBar,
    _trade_from_window,
    summarize,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def _bar(
    minute: int,
    *,
    open_price: int,
    high: int,
    low: int,
    close: int,
) -> ReplayBar:
    opened = datetime(2026, 1, 15, 14, minute, tzinfo=UTC)
    return ReplayBar(
        opened_at=opened,
        open_price=open_price,
        high_price=high,
        low_price=low,
        close_price=close,
    )


def _candle(
    *,
    opened: datetime,
    high: int,
    low: int,
    close: int,
) -> AggregatedCandle:
    return AggregatedCandle(
        opened_at=opened,
        closed_at=opened + timedelta(hours=4),
        open_price=(high + low) // 2,
        high_price=high,
        low_price=low,
        close_price=close,
        m5_count=48,
    )


def test_bearish_turtle_soup_hits_midpoint_target() -> None:
    c1_open = datetime(2026, 1, 15, 6, tzinfo=UTC)
    c2_open = datetime(2026, 1, 15, 10, tzinfo=UTC)
    c1 = _candle(opened=c1_open, high=1100, low=900, close=1050)
    c2 = _candle(opened=c2_open, high=1120, low=930, close=1080)
    c3 = (
        _bar(0, open_price=1080, high=1090, low=1040, close=1050),
        _bar(5, open_price=1050, high=1060, low=995, close=1000),
    )
    trade = _trade_from_window(
        market=CrtPureMarket.AUDUSD,
        timing_index=0,
        c1=c1,
        c2=c2,
        c3_m5=c3,
    )
    assert trade is not None
    assert trade.direction == "BEARISH"
    assert trade.exit_reason == "TARGET_50"
    assert trade.stop_price_relative == 1120
    assert trade.target_price_relative == "1000"
    assert trade.r_multiple > 0


def test_same_m5_stop_and_target_is_stop_first() -> None:
    c1_open = datetime(2026, 1, 15, 6, tzinfo=UTC)
    c2_open = datetime(2026, 1, 15, 10, tzinfo=UTC)
    c1 = _candle(opened=c1_open, high=1100, low=900, close=1050)
    c2 = _candle(opened=c2_open, high=1120, low=930, close=1080)
    c3 = (
        _bar(0, open_price=1080, high=1130, low=990, close=1050),
    )
    trade = _trade_from_window(
        market=CrtPureMarket.USDJPY,
        timing_index=0,
        c1=c1,
        c2=c2,
        c3_m5=c3,
    )
    assert trade is not None
    assert trade.exit_reason == "STOP"
    assert trade.r_multiple == -1.0


def test_invalid_midpoint_geometry_is_not_forced() -> None:
    c1_open = datetime(2026, 1, 15, 6, tzinfo=UTC)
    c2_open = datetime(2026, 1, 15, 10, tzinfo=UTC)
    c1 = _candle(opened=c1_open, high=1100, low=900, close=950)
    c2 = _candle(opened=c2_open, high=1070, low=880, close=920)
    c3 = (
        _bar(0, open_price=1050, high=1070, low=1030, close=1060),
    )
    trade = _trade_from_window(
        market=CrtPureMarket.BTCUSD,
        timing_index=0,
        c1=c1,
        c2=c2,
        c3_m5=c3,
    )
    assert trade is None


def test_summary_reports_drawdown_and_losing_streak() -> None:
    c1_open = datetime(2026, 1, 15, 6, tzinfo=UTC)
    c2_open = datetime(2026, 1, 15, 10, tzinfo=UTC)
    c1 = _candle(opened=c1_open, high=1100, low=900, close=1050)
    c2 = _candle(opened=c2_open, high=1120, low=930, close=1080)
    loser = _trade_from_window(
        market=CrtPureMarket.AUDUSD,
        timing_index=0,
        c1=c1,
        c2=c2,
        c3_m5=(_bar(0, open_price=1080, high=1130, low=1070, close=1120),),
    )
    winner = _trade_from_window(
        market=CrtPureMarket.AUDUSD,
        timing_index=0,
        c1=c1,
        c2=c2,
        c3_m5=(
            _bar(0, open_price=1080, high=1090, low=1040, close=1050),
            _bar(5, open_price=1050, high=1060, low=995, close=1000),
        ),
    )
    assert loser is not None
    assert winner is not None
    stats = summarize((loser, loser, winner))
    assert stats["trades"] == 3
    assert stats["longest_losing_streak"] == 2
    assert stats["max_drawdown_r"] == 2.0
