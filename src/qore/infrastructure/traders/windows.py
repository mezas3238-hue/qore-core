"""DST-aware New York session/window membership and the VT-17 90-minute cycle.

Session/window membership is evaluated against local wall-clock time in
``America/New_York`` (handled by ``zoneinfo``, so DST spring/fall transitions are
exact). Windows are half-open ``[open, close)`` on the local wall clock. The
VT-17 90-minute cycle is an epoch-aligned UTC grid: cycle ``i`` covers
``[i * 5400s, (i + 1) * 5400s)`` since the Unix epoch, so cycle identity is
deterministic and timezone-independent while its *admissibility* is constrained
by the NY session window at the evaluation site.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from qore.infrastructure.market_clock_schedule import WallClockBoundary
from qore.kernel.errors import InfrastructureError

NY_TIMEZONE = "America/New_York"
_NINETY_MINUTE_SECONDS = 5400
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class DemoTradingWindowError(InfrastructureError):
    """Base error for deterministic session/window/cycle semantics."""

    __slots__ = ()


class DemoTradingWindowValidationError(DemoTradingWindowError):
    """Violation of a session/window/cycle invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise DemoTradingWindowValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise DemoTradingWindowValidationError(f"{field_name} must be timezone-aware")


def _utc(value: datetime, *, field_name: str) -> datetime:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC)


def _epoch_micros(value: datetime) -> int:
    """Exact integer microseconds since the Unix epoch (no float arithmetic)."""

    delta = value.astimezone(UTC) - _EPOCH
    return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds


def _zone(timezone_name: str) -> ZoneInfo:
    if type(timezone_name) is not str or not timezone_name.strip():
        raise DemoTradingWindowValidationError("timezone_name must be non-empty")
    if timezone_name != timezone_name.strip():
        raise DemoTradingWindowValidationError("timezone_name must be trimmed")
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise DemoTradingWindowValidationError(
            f"invalid IANA timezone: {timezone_name!r}"
        ) from exc


@dataclass(frozen=True, slots=True)
class SessionWindow:
    """One named, DST-aware New York session/window with half-open boundaries."""

    name: str
    timezone_name: str
    open: WallClockBoundary
    close: WallClockBoundary

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name.strip():
            raise DemoTradingWindowValidationError("window name must be non-empty")
        _zone(self.timezone_name)
        if type(self.open) is not WallClockBoundary:
            raise DemoTradingWindowValidationError("window open must be WallClockBoundary")
        if type(self.close) is not WallClockBoundary:
            raise DemoTradingWindowValidationError("window close must be WallClockBoundary")
        if (self.close.hour, self.close.minute, self.close.second) <= (
            self.open.hour,
            self.open.minute,
            self.open.second,
        ):
            raise DemoTradingWindowValidationError(
                "window close wall-clock must be after open wall-clock"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.name,
            self.timezone_name,
            self.open.logical_values(),
            self.close.logical_values(),
        )


def is_in_window(instant: datetime, window: SessionWindow) -> bool:
    """Return whether an instant is inside a half-open session window.

    Membership is decided on the local wall clock in the window's timezone, so
    DST transitions are handled exactly. A non-existent (spring-forward gap) or
    ambiguous (fall-back fold) local instant is evaluated on its resolved local
    wall-clock time.
    """

    _validate_timestamp(instant, field_name="instant")
    if type(window) is not SessionWindow:
        raise DemoTradingWindowValidationError("window must be SessionWindow")
    zone = _zone(window.timezone_name)
    local = instant.astimezone(zone)
    wall = (local.hour, local.minute, local.second)
    open_wall = (window.open.hour, window.open.minute, window.open.second)
    close_wall = (window.close.hour, window.close.minute, window.close.second)
    return open_wall <= wall < close_wall


@dataclass(frozen=True, slots=True)
class NinetyMinuteCycle:
    """One epoch-aligned deterministic 90-minute cycle (VT-17)."""

    index: int
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        if type(self.index) is not int or self.index < 0:
            raise DemoTradingWindowValidationError("cycle index must be a non-negative int")
        opened_at = _utc(self.opened_at, field_name="cycle opened_at")
        closed_at = _utc(self.closed_at, field_name="cycle closed_at")
        if (closed_at - opened_at).total_seconds() != _NINETY_MINUTE_SECONDS:
            raise DemoTradingWindowValidationError(
                "90-minute cycle must span exactly 5400 seconds"
            )
        if opened_at.tzinfo is not UTC:
            raise DemoTradingWindowValidationError("cycle opened_at must be canonical UTC")
        total_us = _epoch_micros(opened_at)
        if total_us % (_NINETY_MINUTE_SECONDS * 1_000_000) != 0:
            raise DemoTradingWindowValidationError(
                "90-minute cycle must be epoch-aligned"
            )
        if total_us // (_NINETY_MINUTE_SECONDS * 1_000_000) != self.index:
            raise DemoTradingWindowValidationError(
                "90-minute cycle index must match its epoch alignment"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.index,
            self.opened_at.isoformat(timespec="microseconds"),
            self.closed_at.isoformat(timespec="microseconds"),
        )


def ninety_minute_cycle(instant: datetime) -> NinetyMinuteCycle:
    """Return the epoch-aligned 90-minute cycle containing an instant."""

    utc_instant = _utc(instant, field_name="instant")
    total_us = _epoch_micros(utc_instant)
    index = total_us // (_NINETY_MINUTE_SECONDS * 1_000_000)
    opened_at = _EPOCH + timedelta(seconds=index * _NINETY_MINUTE_SECONDS)
    closed_at = opened_at + timedelta(seconds=_NINETY_MINUTE_SECONDS)
    return NinetyMinuteCycle(index=index, opened_at=opened_at, closed_at=closed_at)


def cycle_is_closed(cycle: NinetyMinuteCycle, *, as_of: datetime) -> bool:
    """Return whether a 90-minute cycle is fully closed at an instant."""

    if type(cycle) is not NinetyMinuteCycle:
        raise DemoTradingWindowValidationError("cycle must be NinetyMinuteCycle")
    _validate_timestamp(as_of, field_name="as_of")
    return as_of >= cycle.closed_at


# Canonical fixed NY windows for the DEMO cohort.
NY_AM_SESSION = SessionWindow(
    name="ny-am-session",
    timezone_name=NY_TIMEZONE,
    open=WallClockBoundary(hour=7, minute=0),
    close=WallClockBoundary(hour=11, minute=0),
)
NY_SILVER_BULLET_AM = SessionWindow(
    name="ny-silver-bullet-am",
    timezone_name=NY_TIMEZONE,
    open=WallClockBoundary(hour=10, minute=0),
    close=WallClockBoundary(hour=11, minute=0),
)
NY_SILVER_BULLET_PM = SessionWindow(
    name="ny-silver-bullet-pm",
    timezone_name=NY_TIMEZONE,
    open=WallClockBoundary(hour=14, minute=0),
    close=WallClockBoundary(hour=15, minute=0),
)

SILVER_BULLET_WINDOWS: tuple[SessionWindow, ...] = (
    NY_SILVER_BULLET_AM,
    NY_SILVER_BULLET_PM,
)


def active_silver_bullet_window(instant: datetime) -> SessionWindow | None:
    """Return the active Silver Bullet window at an instant, or None."""

    _validate_timestamp(instant, field_name="instant")
    for window in SILVER_BULLET_WINDOWS:
        if is_in_window(instant, window):
            return window
    return None
