"""Price-only V2 lifecycle cannot reinterpret outcome as trade or sizing."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_three_source_v2_price_lifecycle import (
    observe_price_only_path,
)

START = datetime(2025, 3, 3, 8, tzinfo=UTC)
DECISION = START + timedelta(minutes=30)


def candle(
    minute: int, opened: int, high: int, low: int, closed: int
) -> ReplayBar:
    return ReplayBar(
        opened_at=START + timedelta(minutes=minute),
        open_price=opened,
        high_price=high,
        low_price=low,
        close_price=closed,
    )


def _path(*candles: ReplayBar) -> dict[datetime, ReplayBar]:
    return {bar.opened_at: bar for bar in candles}


def _result(
    bars: dict[datetime, ReplayBar], direction: str = "BULLISH"
) -> tuple[str, str | None, int]:
    return observe_price_only_path(
        direction=direction,
        decision_at=DECISION,
        c3_open=START,
        invalidation_relative=90 if direction == "BULLISH" else 110,
        target_double_relative=200,
        m5=bars,
    )


def test_target_first_price_touch_not_trading_profit() -> None:
    outcome, when, count = _result(
        _path(candle(30, 95, 101, 94, 99))
    )
    assert outcome == "DESTINATION_FIRST"
    assert when == DECISION.isoformat()
    assert count == 1


def test_invalidation_first_price_touch_is_recorded() -> None:
    outcome, _, count = _result(
        _path(candle(30, 95, 99, 89, 93))
    )
    assert outcome == "INVALIDATION_FIRST"
    assert count == 1


def test_simultaneous_touch_is_conservative_not_target_first() -> None:
    outcome, _, _ = _result(_path(candle(30, 95, 102, 89, 95)))
    assert outcome == "INVALIDATION_FIRST_AMBIGUOUS_SAME_M5"


def test_missing_m5_before_terminal_never_interpolates_future() -> None:
    outcome, when, count = _result(
        _path(candle(30, 95, 98, 92, 96))
    )
    assert outcome == "UNKNOWN_MISSING_M5_BEFORE_TERMINAL"
    assert when is None and count == 1


def test_missing_or_invalid_entry_is_uncertainty_not_win() -> None:
    assert _result({})[0] == "UNKNOWN_MISSING_ENTRY_OPEN_PRICE"
    assert _result(_path(candle(30, 101, 102, 100, 101)))[0] == (
        "UNKNOWN_ENTRY_ALREADY_BEYOND_BARRIER"
    )


def test_bearish_target_then_stop_separated_by_direction() -> None:
    outcome, _, count = _result(
        _path(candle(30, 105, 107, 99, 102)), "BEARISH"
    )
    assert outcome == "DESTINATION_FIRST" and count == 1


def test_empty_last_bar_horizon_is_expired_without_hit() -> None:
    bars = {
        START + timedelta(minutes=m): candle(m, 95, 99, 91, 95)
        for m in range(30, 240, 5)
    }
    assert _result(bars)[0] == "EXPIRED_WITHOUT_TOUCH"


def test_noncausal_decision_time_rejected() -> None:
    with pytest.raises(ValueError, match="cannot precede or exceed"):
        observe_price_only_path(
            direction="BULLISH",
            decision_at=START,
            c3_open=START,
            invalidation_relative=90,
            target_double_relative=200,
            m5={},
        )


def test_invalid_bar_geometry_rejected() -> None:
    bad = candle(30, 95, 94, 92, 95)
    with pytest.raises(ValueError, match="OHLC geometry"):
        _result(_path(bad))


def test_confirmation_at_last_c3_m15_close_has_no_future_price_path() -> None:
    result = observe_price_only_path(
        direction="BULLISH",
        decision_at=START + timedelta(hours=4),
        c3_open=START,
        invalidation_relative=90,
        target_double_relative=200,
        m5={},
    )
    assert result == ("EXPIRED_AT_C3_CLOSE_NO_POST_DECISION_WINDOW", None, 0)
