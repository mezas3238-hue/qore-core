from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    EVAL_CLOSE,
    EVAL_OPEN,
    H4_SOURCE_ANCHORS,
    Side,
    SourceCandle,
    _h4_open_for,
    _source_day_open,
    causal_cisd,
)


def _candle(
    hour: int,
    open_price: str,
    high_price: str,
    low_price: str,
    close_price: str,
) -> SourceCandle:
    opened = datetime(2019, 1, 2, hour, tzinfo=UTC)
    return SourceCandle(
        opened_at=opened,
        closed_at=opened + timedelta(hours=1),
        open=Decimal(open_price),
        high=Decimal(high_price),
        low=Decimal(low_price),
        close=Decimal(close_price),
        m5=(),
    )


def test_fresh_window_is_exactly_730_days() -> None:
    assert EVAL_CLOSE - EVAL_OPEN == timedelta(days=730)


def test_forex_source_h4_anchors_are_frozen() -> None:
    assert H4_SOURCE_ANCHORS == (17, 21, 1, 5, 9, 13)
    assert _source_day_open(datetime(2019, 1, 2).date()) == datetime(
        2019, 1, 2, 22, tzinfo=UTC
    )
    assert _h4_open_for(datetime(2019, 1, 3, 2, 35, tzinfo=UTC)) == datetime(
        2019, 1, 3, 2, tzinfo=UTC
    )


def test_bullish_cisd_uses_first_open_of_exact_opposing_series() -> None:
    candles = (
        _candle(0, "1.1000", "1.1010", "1.0980", "1.0990"),
        _candle(1, "1.0990", "1.1000", "1.0970", "1.0980"),
        _candle(2, "1.0980", "1.0990", "1.0960", "1.0970"),
        _candle(3, "1.0970", "1.1010", "1.0965", "1.1005"),
    )
    cisd = causal_cisd(
        candles, side=Side.LONG, extreme=Decimal("1.0960")
    )
    assert cisd is not None
    assert cisd.threshold == Decimal("1.1000")
    assert cisd.confirmed_at == candles[3].closed_at
    assert cisd.protected_swing == Decimal("1.0960")


def test_doji_breaks_opposing_series() -> None:
    candles = (
        _candle(0, "1.1000", "1.1010", "1.0980", "1.0990"),
        _candle(1, "1.0990", "1.1000", "1.0980", "1.0990"),
        _candle(2, "1.0990", "1.1000", "1.0960", "1.0970"),
        _candle(3, "1.0970", "1.1010", "1.0965", "1.1000"),
    )
    cisd = causal_cisd(
        candles, side=Side.LONG, extreme=Decimal("1.0960")
    )
    assert cisd is not None
    assert cisd.threshold == Decimal("1.0990")


def test_cisd_fails_closed_when_extreme_is_ambiguous() -> None:
    candles = (
        _candle(0, "1.1000", "1.1010", "1.0960", "1.0990"),
        _candle(1, "1.0990", "1.1000", "1.0960", "1.0980"),
        _candle(2, "1.0980", "1.1020", "1.0970", "1.1010"),
    )
    assert (
        causal_cisd(candles, side=Side.LONG, extreme=Decimal("1.0960"))
        is None
    )
