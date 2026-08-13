from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from qore.infrastructure.market_event_replay import (
    RetainedMarketEventObservation,
    order_market_event_observations,
)
from qore.kernel.errors import InfrastructureError


class MarketClockScheduleError(InfrastructureError):
    """Base error for deterministic generic market-clock scheduling."""

    __slots__ = ()


class MarketClockScheduleValidationError(MarketClockScheduleError):
    """Violation of a deterministic Schedule B time invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise MarketClockScheduleValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketClockScheduleValidationError(
            f"{field_name} must be timezone-aware"
        )


def _utc(value: datetime, *, field_name: str) -> datetime:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC)


def _zone(timezone_name: str) -> ZoneInfo:
    if not isinstance(timezone_name, str) or not timezone_name:
        raise MarketClockScheduleValidationError(
            "timezone_name must be non-empty str"
        )
    if timezone_name != timezone_name.strip():
        raise MarketClockScheduleValidationError(
            "timezone_name must be trimmed"
        )
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise MarketClockScheduleValidationError(
            f"unknown IANA timezone: {timezone_name!r}"
        ) from exc


@dataclass(frozen=True, slots=True, order=True)
class WallClockBoundary:
    """One methodology-neutral local wall-clock boundary."""

    hour: int
    minute: int = 0
    second: int = 0

    def __post_init__(self) -> None:
        for field_name, value, maximum in (
            ("hour", self.hour, 23),
            ("minute", self.minute, 59),
            ("second", self.second, 59),
        ):
            if isinstance(value, bool) or type(value) is not int:
                raise MarketClockScheduleValidationError(
                    f"wall-clock {field_name} must be strict int"
                )
            if value < 0 or value > maximum:
                raise MarketClockScheduleValidationError(
                    f"wall-clock {field_name} outside supported range"
                )

    def logical_values(self) -> tuple[int, int, int]:
        return (self.hour, self.minute, self.second)


@dataclass(frozen=True, slots=True)
class WallClockTransition:
    """One exact UTC instant produced by a local wall-clock boundary."""

    simulated_now: datetime
    timezone_name: str
    local_date: date
    boundary: WallClockBoundary

    def __post_init__(self) -> None:
        canonical_now = _utc(
            self.simulated_now,
            field_name="wall-clock transition simulated_now",
        )
        if self.simulated_now != canonical_now or self.simulated_now.tzinfo is not UTC:
            raise MarketClockScheduleValidationError(
                "wall-clock transition simulated_now must be canonical UTC"
            )
        zone = _zone(self.timezone_name)
        if type(self.local_date) is not date:
            raise MarketClockScheduleValidationError(
                "wall-clock transition local_date must be date"
            )
        if not isinstance(self.boundary, WallClockBoundary):
            raise MarketClockScheduleValidationError(
                "wall-clock transition boundary must be WallClockBoundary"
            )
        local = self.simulated_now.astimezone(zone)
        expected = (
            local.date(),
            local.hour,
            local.minute,
            local.second,
        )
        actual = (
            self.local_date,
            self.boundary.hour,
            self.boundary.minute,
            self.boundary.second,
        )
        if expected != actual:
            raise MarketClockScheduleValidationError(
                "wall-clock transition does not round-trip to retained local boundary"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.simulated_now.isoformat(timespec="microseconds"),
            self.timezone_name,
            self.local_date.isoformat(),
            self.boundary.logical_values(),
        )


class ScheduleBTrigger(StrEnum):
    MARKET_DATA = "market_data"
    WALL_CLOCK = "wall_clock"


@dataclass(frozen=True, slots=True)
class ScheduleBInstant:
    """One unique evaluation instant with every reason for evaluating at that time."""

    simulated_now: datetime
    newly_available_market_events: tuple[RetainedMarketEventObservation, ...]
    wall_clock_transitions: tuple[WallClockTransition, ...]

    def __post_init__(self) -> None:
        canonical_now = _utc(self.simulated_now, field_name="Schedule B simulated_now")
        if self.simulated_now != canonical_now or self.simulated_now.tzinfo is not UTC:
            raise MarketClockScheduleValidationError(
                "Schedule B simulated_now must be canonical UTC"
            )
        if not isinstance(self.newly_available_market_events, tuple) or any(
            not isinstance(item, RetainedMarketEventObservation)
            for item in self.newly_available_market_events
        ):
            raise MarketClockScheduleValidationError(
                "Schedule B market events must be immutable retained-event tuple"
            )
        if not isinstance(self.wall_clock_transitions, tuple) or any(
            not isinstance(item, WallClockTransition)
            for item in self.wall_clock_transitions
        ):
            raise MarketClockScheduleValidationError(
                "Schedule B wall transitions must be immutable transition tuple"
            )
        if not self.newly_available_market_events and not self.wall_clock_transitions:
            raise MarketClockScheduleValidationError(
                "Schedule B instant requires at least one evaluation trigger"
            )
        if self.newly_available_market_events:
            ordered = order_market_event_observations(
                self.newly_available_market_events
            )
            if ordered != self.newly_available_market_events:
                raise MarketClockScheduleValidationError(
                    "Schedule B market events must retain canonical arrival order"
                )
            for item in self.newly_available_market_events:
                if item.available_at.astimezone(UTC) != self.simulated_now:
                    raise MarketClockScheduleValidationError(
                        "Schedule B market event available_at must equal simulated_now"
                    )
        if self.wall_clock_transitions != tuple(
            sorted(
                self.wall_clock_transitions,
                key=lambda item: (
                    item.boundary.hour,
                    item.boundary.minute,
                    item.boundary.second,
                    item.timezone_name,
                ),
            )
        ):
            raise MarketClockScheduleValidationError(
                "Schedule B wall transitions must use canonical boundary order"
            )
        if len(set(self.wall_clock_transitions)) != len(self.wall_clock_transitions):
            raise MarketClockScheduleValidationError(
                "Schedule B wall transitions must be unique"
            )
        for item in self.wall_clock_transitions:
            if item.simulated_now != self.simulated_now:
                raise MarketClockScheduleValidationError(
                    "Schedule B wall transition must equal simulated_now"
                )

    @property
    def triggers(self) -> tuple[ScheduleBTrigger, ...]:
        result: list[ScheduleBTrigger] = []
        if self.newly_available_market_events:
            result.append(ScheduleBTrigger.MARKET_DATA)
        if self.wall_clock_transitions:
            result.append(ScheduleBTrigger.WALL_CLOCK)
        return tuple(result)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.simulated_now.isoformat(timespec="microseconds"),
            tuple(item.logical_values() for item in self.newly_available_market_events),
            tuple(item.logical_values() for item in self.wall_clock_transitions),
            tuple(item.value for item in self.triggers),
        )


def _resolve_local_boundary(
    *,
    local_date: date,
    boundary: WallClockBoundary,
    zone: ZoneInfo,
) -> datetime | None:
    naive = datetime(
        local_date.year,
        local_date.month,
        local_date.day,
        boundary.hour,
        boundary.minute,
        boundary.second,
    )
    candidates: list[datetime] = []
    for fold in (0, 1):
        local = naive.replace(tzinfo=zone, fold=fold)
        utc_candidate = local.astimezone(UTC)
        round_trip = utc_candidate.astimezone(zone)
        if round_trip.replace(tzinfo=None) == naive:
            candidates.append(utc_candidate)
    unique = tuple(sorted(set(candidates)))
    if not unique:
        return None
    if len(unique) > 1:
        raise MarketClockScheduleValidationError(
            "ambiguous local wall-clock boundary requires explicit methodology policy"
        )
    return unique[0]


def derive_wall_clock_transitions(
    *,
    simulated_start: datetime,
    simulated_end: datetime,
    timezone_name: str,
    boundaries: tuple[WallClockBoundary, ...],
) -> tuple[WallClockTransition, ...]:
    """Derive exact UTC wall-clock transitions in a half-open simulation window."""

    start = _utc(simulated_start, field_name="schedule simulated_start")
    end = _utc(simulated_end, field_name="schedule simulated_end")
    if end <= start:
        raise MarketClockScheduleValidationError(
            "schedule simulated_end must be after simulated_start"
        )
    zone = _zone(timezone_name)
    if not isinstance(boundaries, tuple) or any(
        not isinstance(item, WallClockBoundary) for item in boundaries
    ):
        raise MarketClockScheduleValidationError(
            "wall-clock boundaries must be immutable WallClockBoundary tuple"
        )
    canonical_boundaries = tuple(sorted(set(boundaries)))
    if not canonical_boundaries:
        return ()

    first_date = start.astimezone(zone).date()
    last_date = (end - timedelta(microseconds=1)).astimezone(zone).date()
    transitions: list[WallClockTransition] = []
    current_date = first_date
    while current_date <= last_date:
        for boundary in canonical_boundaries:
            instant = _resolve_local_boundary(
                local_date=current_date,
                boundary=boundary,
                zone=zone,
            )
            if instant is None or instant < start or instant >= end:
                continue
            transitions.append(
                WallClockTransition(
                    simulated_now=instant,
                    timezone_name=timezone_name,
                    local_date=current_date,
                    boundary=boundary,
                )
            )
        current_date += timedelta(days=1)
    return tuple(sorted(transitions, key=lambda item: item.simulated_now))


def derive_schedule_b_instants(
    observations: tuple[RetainedMarketEventObservation, ...],
    *,
    simulated_start: datetime,
    simulated_end: datetime,
    timezone_name: str,
    boundaries: tuple[WallClockBoundary, ...],
) -> tuple[ScheduleBInstant, ...]:
    """Compose market availability and wall-clock transitions into unique instants."""

    start = _utc(simulated_start, field_name="Schedule B simulated_start")
    end = _utc(simulated_end, field_name="Schedule B simulated_end")
    if end <= start:
        raise MarketClockScheduleValidationError(
            "Schedule B simulated_end must be after simulated_start"
        )
    if not isinstance(observations, tuple) or any(
        not isinstance(item, RetainedMarketEventObservation) for item in observations
    ):
        raise MarketClockScheduleValidationError(
            "Schedule B observations must be immutable retained-event tuple"
        )
    ordered = order_market_event_observations(observations)
    market_by_time: dict[datetime, list[RetainedMarketEventObservation]] = {}
    for item in ordered:
        instant = item.available_at.astimezone(UTC)
        if start <= instant < end:
            market_by_time.setdefault(instant, []).append(item)

    wall_transitions = derive_wall_clock_transitions(
        simulated_start=start,
        simulated_end=end,
        timezone_name=timezone_name,
        boundaries=boundaries,
    )
    wall_by_time: dict[datetime, list[WallClockTransition]] = {}
    for transition in wall_transitions:
        wall_by_time.setdefault(transition.simulated_now, []).append(transition)

    instants = tuple(sorted(set(market_by_time) | set(wall_by_time)))
    return tuple(
        ScheduleBInstant(
            simulated_now=instant,
            newly_available_market_events=tuple(market_by_time.get(instant, [])),
            wall_clock_transitions=tuple(wall_by_time.get(instant, [])),
        )
        for instant in instants
    )
