from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    SourceCandle,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r5_authentic_ideal import (
    ACQUISITION_OPEN,
    EVAL_CLOSE,
    EVAL_OPEN,
    Side,
    _daily_swing_targets,
    authentic_ideal_c2,
)


def _candle(
    day: int,
    open_price: str,
    high_price: str,
    low_price: str,
    close_price: str,
) -> SourceCandle:
    opened = datetime(2017, 1, day, 22, tzinfo=UTC)
    return SourceCandle(
        opened_at=opened,
        closed_at=opened + timedelta(days=1),
        open=Decimal(open_price),
        high=Decimal(high_price),
        low=Decimal(low_price),
        close=Decimal(close_price),
        m5=(),
    )


def _m5(
    opened_at: datetime,
    open_price: str,
    high_price: str,
    low_price: str,
    close_price: str,
) -> Bar:
    return Bar(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=5),
        open=Decimal(open_price),
        high=Decimal(high_price),
        low=Decimal(low_price),
        close=Decimal(close_price),
    )


def test_r5_fresh_window_is_exactly_730_days_and_precedes_r4() -> None:
    assert EVAL_CLOSE - EVAL_OPEN == timedelta(days=730)
    assert EVAL_CLOSE == datetime(2018, 5, 1, 21, tzinfo=UTC)
    assert ACQUISITION_OPEN == datetime(2016, 3, 1, 22, tzinfo=UTC)


def test_bullish_authentic_ideal_c2_closes_through_same_timeframe_series() -> None:
    candles = (
        _candle(1, "1.1100", "1.1120", "1.1000", "1.1050"),
        _candle(2, "1.1050", "1.1080", "1.0980", "1.1000"),
        _candle(3, "1.0990", "1.1130", "1.0960", "1.1110"),
    )
    ideal = authentic_ideal_c2(candles, 2)
    assert ideal is not None
    assert ideal.side is Side.LONG
    assert ideal.opposing_series_opened_at == candles[0].opened_at
    assert ideal.opposing_series_threshold == Decimal("1.1100")
    assert ideal.protected_swing == Decimal("1.0960")


def test_bearish_authentic_ideal_c2_is_exact_mirror() -> None:
    candles = (
        _candle(1, "1.0900", "1.1000", "1.0880", "1.0960"),
        _candle(2, "1.0960", "1.1020", "1.0940", "1.1000"),
        _candle(3, "1.1010", "1.1040", "1.0870", "1.0890"),
    )
    ideal = authentic_ideal_c2(candles, 2)
    assert ideal is not None
    assert ideal.side is Side.SHORT
    assert ideal.opposing_series_opened_at == candles[0].opened_at
    assert ideal.opposing_series_threshold == Decimal("1.0900")
    assert ideal.protected_swing == Decimal("1.1040")


def test_standard_c2_without_series_break_is_not_ideal() -> None:
    candles = (
        _candle(1, "1.1100", "1.1120", "1.1000", "1.1050"),
        _candle(2, "1.1050", "1.1080", "1.0980", "1.1000"),
        # Sweeps C1 low and closes back inside, but not through first series open.
        _candle(3, "1.0990", "1.1090", "1.0960", "1.1080"),
    )
    assert authentic_ideal_c2(candles, 2) is None


def test_body_misaligned_reversal_closure_is_not_ideal() -> None:
    candles = (
        _candle(1, "1.1000", "1.1050", "1.0950", "1.0980"),
        # Bullish sweep/reclaim but bearish body: not authentic Ideal C2.
        _candle(2, "1.1030", "1.1040", "1.0930", "1.0990"),
    )
    assert authentic_ideal_c2(candles, 1) is None


def test_doji_immediately_before_c2_breaks_opposing_series() -> None:
    candles = (
        _candle(1, "1.1100", "1.1120", "1.1000", "1.1050"),
        _candle(2, "1.1050", "1.1080", "1.0990", "1.1050"),
        _candle(3, "1.1040", "1.1150", "1.0970", "1.1110"),
    )
    assert authentic_ideal_c2(candles, 2) is None


def test_daily_dol_requires_completed_untouched_three_candle_swing() -> None:
    daily = (
        _candle(1, "1.0800", "1.1000", "1.0700", "1.0900"),
        _candle(2, "1.0900", "1.1200", "1.0800", "1.1000"),
        _candle(3, "1.1000", "1.1100", "1.0850", "1.0950"),
        _candle(4, "1.0950", "1.1050", "1.0800", "1.0900"),
    )
    entry_at = daily[3].closed_at + timedelta(hours=1)
    target = _daily_swing_targets(
        daily,
        (),
        side=Side.LONG,
        entry=Decimal("1.0950"),
        entry_at=entry_at,
    )
    assert target == (Decimal("1.1200"), daily[1].opened_at)

    consumed_bar = _m5(
        daily[2].closed_at + timedelta(hours=1),
        "1.1100",
        "1.1210",
        "1.1090",
        "1.1200",
    )
    assert (
        _daily_swing_targets(
            daily,
            (consumed_bar,),
            side=Side.LONG,
            entry=Decimal("1.0950"),
            entry_at=entry_at,
        )
        is None
    )
