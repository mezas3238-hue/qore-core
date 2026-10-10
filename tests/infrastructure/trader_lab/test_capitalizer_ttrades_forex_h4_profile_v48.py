from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_ttrades_forex_h4_profile_v48 import (
    FOREX_H4_ANCHOR_HOURS_NY,
    build_forex_h4_profiles,
    forex_h4_profile_bounds,
)

NEW_YORK = ZoneInfo("America/New_York")


def _bar(opened: datetime, minute: int) -> CapitalizerM1Bar:
    price = Decimal("1.10000") + Decimal(minute) / Decimal("100000")
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=price,
        high=price + Decimal("0.00005"),
        low=price - Decimal("0.00005"),
        close=price + Decimal("0.00001"),
        volume=1,
        digits=5,
    )


def test_forex_h4_anchor_cycle_is_source_bound_to_1_5_9_and_four_hour_steps() -> None:
    assert FOREX_H4_ANCHOR_HOURS_NY == (1, 5, 9, 13, 17, 21)


def test_normal_forex_h4_profile_builds_from_provider_m1_without_interpolation() -> None:
    local_start = datetime(2026, 1, 5, 1, 0, tzinfo=NEW_YORK)
    start = local_start.astimezone(UTC)
    bars = tuple(_bar(start + timedelta(minutes=i), i) for i in range(240))
    profiles = build_forex_h4_profiles(bars)
    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.ny_anchor_hour == 1
    assert profile.retained_m1 == 240
    assert profile.expected_wall_profile_minutes == 240
    assert profile.completeness == Decimal("1")
    assert profile.provider_native_m1 is True
    assert profile.synthetic_price_used is False
    assert profile.interpolated_price_used is False


def test_midnight_new_york_belongs_to_previous_21_hour_profile() -> None:
    moment = datetime(2026, 1, 6, 0, 30, tzinfo=NEW_YORK)
    start, end = forex_h4_profile_bounds(moment)
    assert start.astimezone(NEW_YORK).hour == 21
    assert start.astimezone(NEW_YORK).date().isoformat() == "2026-01-05"
    assert end.astimezone(NEW_YORK).hour == 1


def test_source_clock_bounds_are_dst_aware() -> None:
    spring = datetime(2026, 3, 8, 1, 30, tzinfo=NEW_YORK)
    spring_start, spring_end = forex_h4_profile_bounds(spring)
    assert int((spring_end - spring_start).total_seconds() // 60) == 180

    fall = datetime(2026, 11, 1, 1, 30, tzinfo=NEW_YORK)
    fall_start, fall_end = forex_h4_profile_bounds(fall)
    assert int((fall_end - fall_start).total_seconds() // 60) == 300
