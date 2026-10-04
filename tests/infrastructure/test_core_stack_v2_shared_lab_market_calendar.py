from datetime import UTC, date, datetime, time

from qore.infrastructure.core_stack_v2.shared_lab_market_calendar import (
    MarketCalendarContract,
    SessionBreak,
    expected_session_state,
)
from qore.infrastructure.core_stack_v2.shared_lab_market_hours import SessionState


def _calendar() -> MarketCalendarContract:
    return MarketCalendarContract(
        instrument_id="FUT:ES",
        timezone="America/New_York",
        open_weekdays=(0, 1, 2, 3, 4),
        session_open=time(18, 0),
        session_close=time(17, 0),
        holidays=(date(2026, 12, 25),),
        early_closes=((date(2026, 11, 27), time(13, 0)),),
        session_breaks=(SessionBreak(time(17, 0), time(18, 0)),),
    )


def test_weekend_holiday_break_and_early_close_are_derived() -> None:
    cal = _calendar()
    assert expected_session_state(cal, datetime(2026, 12, 25, 15, 0, tzinfo=UTC)) is SessionState.HOLIDAY
    assert expected_session_state(cal, datetime(2026, 12, 26, 15, 0, tzinfo=UTC)) is SessionState.WEEKEND
    assert expected_session_state(cal, datetime(2026, 11, 27, 22, 30, tzinfo=UTC)) is SessionState.SESSION_BREAK
    assert expected_session_state(cal, datetime(2026, 11, 27, 19, 0, tzinfo=UTC)) is SessionState.EARLY_CLOSE


def test_overnight_session_is_not_treated_as_closed() -> None:
    cal = _calendar()
    assert expected_session_state(cal, datetime(2026, 11, 24, 0, 30, tzinfo=UTC)) is SessionState.OVERNIGHT
