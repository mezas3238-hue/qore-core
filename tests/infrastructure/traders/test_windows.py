"""DST-aware session/window/cycle tests (spring/fall transitions and boundaries)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.market_clock_schedule import WallClockBoundary
from qore.infrastructure.traders.windows import (
    NY_AM_SESSION,
    NY_SILVER_BULLET_AM,
    NY_SILVER_BULLET_PM,
    NY_TIMEZONE,
    DemoTradingWindowValidationError,
    NinetyMinuteCycle,
    SessionWindow,
    active_silver_bullet_window,
    cycle_is_closed,
    is_in_window,
    ninety_minute_cycle,
)

_ET = ZoneInfo(NY_TIMEZONE)


def _utc_instant(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=_ET).astimezone(UTC)


def test_ny_am_session_membership_half_open() -> None:
    inside = _utc_instant(2026, 1, 6, 8, 30)
    assert is_in_window(inside, NY_AM_SESSION) is True
    before_open = _utc_instant(2026, 1, 6, 6, 59)
    assert is_in_window(before_open, NY_AM_SESSION) is False
    at_open = _utc_instant(2026, 1, 6, 7, 0)
    assert is_in_window(at_open, NY_AM_SESSION) is True
    at_close = _utc_instant(2026, 1, 6, 11, 0)
    assert is_in_window(at_close, NY_AM_SESSION) is False


def test_silver_bullet_windows() -> None:
    assert active_silver_bullet_window(_utc_instant(2026, 1, 6, 10, 15)) == NY_SILVER_BULLET_AM
    assert active_silver_bullet_window(_utc_instant(2026, 1, 6, 14, 15)) == NY_SILVER_BULLET_PM
    assert active_silver_bullet_window(_utc_instant(2026, 1, 6, 11, 30)) is None


def test_spring_forward_dst_transition() -> None:
    # 2026 US DST began 2026-03-08 02:00 ET; 03:00 ET on that day is valid.
    inside = _utc_instant(2026, 3, 9, 8, 30)
    assert is_in_window(inside, NY_AM_SESSION) is True


def test_fall_back_dst_transition() -> None:
    # 2026 US DST ended 2026-11-01 02:00 ET.
    inside = _utc_instant(2026, 11, 2, 8, 30)
    assert is_in_window(inside, NY_AM_SESSION) is True


def test_window_rejects_close_before_open() -> None:
    with pytest.raises(DemoTradingWindowValidationError):
        SessionWindow(
            name="bad",
            timezone_name=NY_TIMEZONE,
            open=WallClockBoundary(hour=10),
            close=WallClockBoundary(hour=9),
        )


def test_ninety_minute_cycle_epoch_aligned() -> None:
    instant = _utc_instant(2026, 1, 6, 8, 30)
    cycle = ninety_minute_cycle(instant)
    assert (cycle.closed_at - cycle.opened_at).total_seconds() == 5400
    assert cycle.opened_at.timestamp() % 5400 == 0
    assert cycle.opened_at <= instant < cycle.closed_at


def test_ninety_minute_cycle_index_monotonic() -> None:
    a = ninety_minute_cycle(_utc_instant(2026, 1, 6, 8, 0))
    b = ninety_minute_cycle(_utc_instant(2026, 1, 6, 9, 30))
    assert b.index == a.index + 1


def test_cycle_closed_boundary() -> None:
    cycle = ninety_minute_cycle(_utc_instant(2026, 1, 6, 8, 30))
    assert cycle_is_closed(cycle, as_of=cycle.closed_at) is True
    assert cycle_is_closed(cycle, as_of=cycle.closed_at - timedelta(seconds=1)) is False


def test_ninety_minute_cycle_rejects_unaligned() -> None:
    with pytest.raises(DemoTradingWindowValidationError):
        NinetyMinuteCycle(
            index=0,
            opened_at=_utc_instant(2026, 1, 6, 0, 1),
            closed_at=_utc_instant(2026, 1, 6, 0, 1) + timedelta(minutes=90),
        )
