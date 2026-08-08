from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from qore.infrastructure.market_data import Instrument, OhlcRequest, Timeframe
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success


class HistoricalMarketDataPlanningError(ExternalPortError):
    """Base error for deterministic historical market-data planning."""

    __slots__ = ()


class HistoricalMarketDataPlanningValidationError(HistoricalMarketDataPlanningError):
    """Violation of a deterministic historical OHLC planning invariant."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HistoricalMarketDataPlanningValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise HistoricalMarketDataPlanningValidationError(
            f"{field_name} must be timezone-aware"
        )


def _duration_seconds(opened_at: datetime, closed_at: datetime) -> int:
    duration = closed_at - opened_at
    seconds = duration.total_seconds()
    if not seconds.is_integer():
        raise HistoricalMarketDataPlanningValidationError(
            "historical OHLC window duration must use whole seconds"
        )
    return int(seconds)


@dataclass(frozen=True, slots=True)
class HistoricalOhlcWindow:
    """Canonical multi-interval historical OHLC planning window."""

    instrument: Instrument
    timeframe: Timeframe
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise HistoricalMarketDataPlanningValidationError(
                "historical OHLC instrument must be Instrument"
            )
        if not isinstance(self.timeframe, Timeframe):
            raise HistoricalMarketDataPlanningValidationError(
                "historical OHLC timeframe must be Timeframe"
            )
        _validate_aware_datetime(self.opened_at, field_name="historical OHLC opened_at")
        _validate_aware_datetime(self.closed_at, field_name="historical OHLC closed_at")
        if self.closed_at <= self.opened_at:
            raise HistoricalMarketDataPlanningValidationError(
                "historical OHLC closed_at must be after opened_at"
            )
        duration_seconds = _duration_seconds(self.opened_at, self.closed_at)
        if duration_seconds % self.timeframe.seconds != 0:
            raise HistoricalMarketDataPlanningValidationError(
                "historical OHLC window must contain a whole number of timeframes"
            )

    @property
    def interval_count(self) -> int:
        """Return the exact number of canonical intervals in the window."""

        return _duration_seconds(self.opened_at, self.closed_at) // self.timeframe.seconds

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument.symbol,
            self.timeframe.seconds,
            self.opened_at.isoformat(),
            self.closed_at.isoformat(),
            self.interval_count,
        )


@dataclass(frozen=True, slots=True)
class HistoricalOhlcPlanningPolicy:
    """Explicit resource bound for one deterministic historical request plan."""

    maximum_intervals: int

    def __post_init__(self) -> None:
        if type(self.maximum_intervals) is not int or self.maximum_intervals <= 0:
            raise HistoricalMarketDataPlanningValidationError(
                "maximum_intervals must be a positive int"
            )

    def logical_values(self) -> tuple[int]:
        return (self.maximum_intervals,)


@dataclass(frozen=True, slots=True)
class HistoricalOhlcRequestPlan:
    """Stable contiguous canonical requests covering one historical window."""

    window: HistoricalOhlcWindow
    policy: HistoricalOhlcPlanningPolicy
    requests: tuple[OhlcRequest, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.window, HistoricalOhlcWindow):
            raise HistoricalMarketDataPlanningValidationError(
                "historical request plan window must be HistoricalOhlcWindow"
            )
        if not isinstance(self.policy, HistoricalOhlcPlanningPolicy):
            raise HistoricalMarketDataPlanningValidationError(
                "historical request plan policy must be HistoricalOhlcPlanningPolicy"
            )
        if not isinstance(self.requests, tuple) or any(
            not isinstance(item, OhlcRequest) for item in self.requests
        ):
            raise HistoricalMarketDataPlanningValidationError(
                "historical request plan requests must be a tuple of OhlcRequest"
            )
        if self.window.interval_count > self.policy.maximum_intervals:
            raise HistoricalMarketDataPlanningValidationError(
                "historical request plan exceeds maximum_intervals policy"
            )
        if len(self.requests) != self.window.interval_count:
            raise HistoricalMarketDataPlanningValidationError(
                "historical request plan must cover every interval exactly once"
            )

        expected_opened_at = self.window.opened_at
        for request in self.requests:
            expected_closed_at = expected_opened_at + timedelta(
                seconds=self.window.timeframe.seconds
            )
            if request.instrument != self.window.instrument:
                raise HistoricalMarketDataPlanningValidationError(
                    "historical request instrument must match window instrument"
                )
            if request.timeframe != self.window.timeframe:
                raise HistoricalMarketDataPlanningValidationError(
                    "historical request timeframe must match window timeframe"
                )
            if (
                request.opened_at != expected_opened_at
                or request.closed_at != expected_closed_at
            ):
                raise HistoricalMarketDataPlanningValidationError(
                    "historical requests must be contiguous and stably ordered"
                )
            expected_opened_at = expected_closed_at
        if expected_opened_at != self.window.closed_at:
            raise HistoricalMarketDataPlanningValidationError(
                "historical request plan must end exactly at window closed_at"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.window.logical_values(),
            self.policy.logical_values(),
            tuple(
                (
                    request.instrument.symbol,
                    request.timeframe.seconds,
                    request.opened_at.isoformat(),
                    request.closed_at.isoformat(),
                )
                for request in self.requests
            ),
        )


def plan_historical_ohlc_requests(
    window: HistoricalOhlcWindow,
    *,
    policy: HistoricalOhlcPlanningPolicy,
) -> Result[HistoricalOhlcRequestPlan, HistoricalMarketDataPlanningError]:
    """Plan canonical per-interval OHLC reads without executing network IO."""

    if not isinstance(window, HistoricalOhlcWindow):
        return Failure(
            HistoricalMarketDataPlanningValidationError(
                "historical OHLC planning requires HistoricalOhlcWindow"
            )
        )
    if not isinstance(policy, HistoricalOhlcPlanningPolicy):
        return Failure(
            HistoricalMarketDataPlanningValidationError(
                "historical OHLC planning requires HistoricalOhlcPlanningPolicy"
            )
        )
    if window.interval_count > policy.maximum_intervals:
        return Failure(
            HistoricalMarketDataPlanningValidationError(
                "historical OHLC window exceeds maximum_intervals policy"
            )
        )

    try:
        requests = tuple(
            OhlcRequest(
                instrument=window.instrument,
                timeframe=window.timeframe,
                opened_at=window.opened_at
                + timedelta(seconds=index * window.timeframe.seconds),
                closed_at=window.opened_at
                + timedelta(seconds=(index + 1) * window.timeframe.seconds),
            )
            for index in range(window.interval_count)
        )
        plan = HistoricalOhlcRequestPlan(
            window=window,
            policy=policy,
            requests=requests,
        )
    except ExternalPortError as error:
        if isinstance(error, HistoricalMarketDataPlanningError):
            return Failure(error)
        return Failure(HistoricalMarketDataPlanningValidationError(str(error)))
    return Success(plan)
