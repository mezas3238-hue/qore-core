from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_crt_pure_ctrader_market_calendar import (
    CTraderMarketCalendar,
    CTraderWeeklyInterval,
)


def _broker_calendar() -> CTraderMarketCalendar:
    return CTraderMarketCalendar(
        "America/New_York",
        (
            CTraderWeeklyInterval(0, 61140),
            CTraderWeeklyInterval(61500, 147540),
            CTraderWeeklyInterval(147900, 233940),
            CTraderWeeklyInterval(234300, 320340),
            CTraderWeeklyInterval(320700, 406740),
            CTraderWeeklyInterval(407100, 492900),
            CTraderWeeklyInterval(495900, 579540),
            CTraderWeeklyInterval(579900, 604799),
        ),
    )


def test_daily_1700_new_york_rollover_is_closed() -> None:
    calendar = _broker_calendar()
    assert calendar.is_open_at(datetime(2026, 9, 21, 20, 55, tzinfo=UTC)) is True
    assert calendar.is_open_at(datetime(2026, 9, 21, 21, 0, tzinfo=UTC)) is False
    assert calendar.is_open_at(datetime(2026, 9, 21, 21, 5, tzinfo=UTC)) is True


def test_friday_reopen_is_1745_new_york() -> None:
    calendar = _broker_calendar()
    assert calendar.is_open_at(datetime(2026, 9, 18, 21, 5, tzinfo=UTC)) is False
    assert calendar.is_open_at(datetime(2026, 9, 18, 21, 40, tzinfo=UTC)) is False
    assert calendar.is_open_at(datetime(2026, 9, 18, 21, 45, tzinfo=UTC)) is True
