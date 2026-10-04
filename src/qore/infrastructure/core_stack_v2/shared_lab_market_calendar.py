"""Instrument-aware engineering market calendar for Shared Lab.

The calendar is fixture/config driven and authority-free. It exists to test
whether provider observations agree with the declared market-hours contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from qore.infrastructure.core_stack_v2.shared_lab_market_hours import SessionState


@dataclass(frozen=True, slots=True)
class SessionBreak:
    start: time
    end: time


@dataclass(frozen=True, slots=True)
class MarketCalendarContract:
    instrument_id: str
    timezone: str
    open_weekdays: tuple[int, ...]
    session_open: time
    session_close: time
    holidays: tuple[date, ...] = ()
    early_closes: tuple[tuple[date, time], ...] = ()
    session_breaks: tuple[SessionBreak, ...] = ()

    def __post_init__(self) -> None:
        if not self.instrument_id:
            raise ValueError("instrument_id is required")
        if len(set(self.open_weekdays)) != len(self.open_weekdays):
            raise ValueError("open_weekdays must be unique")
        if any(day < 0 or day > 6 for day in self.open_weekdays):
            raise ValueError("weekday must be in [0,6]")
        ZoneInfo(self.timezone)


def _in_window(current: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def expected_session_state(
    contract: MarketCalendarContract,
    observed_at: datetime,
) -> SessionState:
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    local = observed_at.astimezone(ZoneInfo(contract.timezone))
    local_date = local.date()
    local_time = local.timetz().replace(tzinfo=None)

    if local_date in contract.holidays:
        return SessionState.HOLIDAY
    if local.weekday() not in contract.open_weekdays:
        return SessionState.WEEKEND

    for break_window in contract.session_breaks:
        if _in_window(local_time, break_window.start, break_window.end):
            return SessionState.SESSION_BREAK

    early_close = dict(contract.early_closes).get(local_date)
    if early_close is not None and local_time >= early_close:
        return SessionState.EARLY_CLOSE

    if _in_window(local_time, contract.session_open, contract.session_close):
        if contract.session_open > contract.session_close:
            return SessionState.OVERNIGHT
        return SessionState.OPEN

    return SessionState.CLOSED
