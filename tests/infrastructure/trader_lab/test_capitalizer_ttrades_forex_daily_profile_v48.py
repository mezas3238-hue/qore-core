from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_ttrades_forex_daily_profile_v48 import (
    FOREX_DAILY_OPEN_HOUR_NY,
    build_forex_daily_profiles,
    forex_daily_profile_bounds,
)

NEW_YORK = ZoneInfo("America/New_York")


def _bar(opened: datetime, minute: int) -> CapitalizerM1Bar:
    price = Decimal("1.10000") + Decimal(minute) / Decimal("1000000")
    return CapitalizerM1Bar(
        symbol="GBPUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=price,
        high=price + Decimal("0.00005"),
        low=price - Decimal("0.00005"),
        close=price + Decimal("0.00001"),
        volume=1,
        digits=5,
    )


def test_forex_daily_open_is_source_bound_to_17_new_york() -> None:
    assert FOREX_DAILY_OPEN_HOUR_NY == 17


def test_daily_profile_builds_from_provider_m1_without_interpolation() -> None:
    local_start = datetime(2026, 1, 5, 17, 0, tzinfo=NEW_YORK)
    start = local_start.astimezone(UTC)
    bars = tuple(_bar(start + timedelta(minutes=i), i) for i in range(1440))
    profiles = build_forex_daily_profiles(bars)
    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.profile_opened_at.astimezone(NEW_YORK).hour == 17
    assert profile.retained_m1 == 1440
    assert profile.completeness == Decimal("1")
    assert profile.synthetic_price_used is False
    assert profile.interpolated_price_used is False


def test_before_17_new_york_belongs_to_prior_daily_profile() -> None:
    moment = datetime(2026, 1, 6, 16, 30, tzinfo=NEW_YORK)
    start, end = forex_daily_profile_bounds(moment)
    assert start.astimezone(NEW_YORK).date().isoformat() == "2026-01-05"
    assert start.astimezone(NEW_YORK).hour == 17
    assert end.astimezone(NEW_YORK).date().isoformat() == "2026-01-06"


def test_daily_profile_bounds_are_dst_aware() -> None:
    spring = datetime(2026, 3, 8, 18, 0, tzinfo=NEW_YORK)
    spring_start, spring_end = forex_daily_profile_bounds(spring)
    assert int((spring_end - spring_start).total_seconds() // 60) == 1440

    pre_spring = datetime(2026, 3, 7, 18, 0, tzinfo=NEW_YORK)
    pre_start, pre_end = forex_daily_profile_bounds(pre_spring)
    assert int((pre_end - pre_start).total_seconds() // 60) == 1380

    pre_fall = datetime(2026, 10, 31, 18, 0, tzinfo=NEW_YORK)
    fall_start, fall_end = forex_daily_profile_bounds(pre_fall)
    assert int((fall_end - fall_start).total_seconds() // 60) == 1500
