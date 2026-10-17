"""Broker-declared cTrader market calendar for CRT PURE research evidence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab.vt08_crt_pure_m5_consumer import _credentials
from qore.kernel.result import Failure

SECONDS_PER_DAY = 86400
EPOCH_DATE = date(1970, 1, 1)


@dataclass(frozen=True, slots=True)
class CTraderWeeklyInterval:
    start_second: int
    end_second: int

    def __post_init__(self) -> None:
        if not (0 <= self.start_second < self.end_second <= 7 * SECONDS_PER_DAY):
            raise ValueError("invalid cTrader weekly trading interval")


@dataclass(frozen=True, slots=True)
class CTraderHolidayInterval:
    holiday_date: int
    schedule_time_zone: str
    is_recurring: bool
    start_second: int | None
    end_second: int | None

    def __post_init__(self) -> None:
        if self.holiday_date < 0 or not self.schedule_time_zone:
            raise ValueError("invalid cTrader holiday identity")
        if (self.start_second is None) != (self.end_second is None):
            raise ValueError("holiday start/end must both be present or absent")
        if self.start_second is not None and self.end_second is not None:
            if not (0 <= self.start_second < self.end_second <= SECONDS_PER_DAY):
                raise ValueError("invalid cTrader holiday interval")


@dataclass(frozen=True, slots=True)
class CTraderMarketCalendar:
    schedule_time_zone: str
    intervals: tuple[CTraderWeeklyInterval, ...]
    holidays: tuple[CTraderHolidayInterval, ...] = ()

    def __post_init__(self) -> None:
        ZoneInfo(self.schedule_time_zone)
        if not self.intervals:
            raise ValueError("cTrader market calendar requires intervals")

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.schedule_time_zone)

    def _holiday_closed(self, moment: datetime) -> bool:
        for holiday in self.holidays:
            local = moment.astimezone(ZoneInfo(holiday.schedule_time_zone))
            holiday_base = EPOCH_DATE + timedelta(days=holiday.holiday_date)
            applies = (
                (local.month, local.day) == (holiday_base.month, holiday_base.day)
                if holiday.is_recurring
                else local.date() == holiday_base
            )
            if not applies:
                continue
            if holiday.start_second is None or holiday.end_second is None:
                return True
            second = local.hour * 3600 + local.minute * 60 + local.second
            if holiday.start_second <= second < holiday.end_second:
                return True
        return False

    def is_open_at(self, moment: datetime) -> bool:
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("market-calendar moment must be timezone-aware")
        local = moment.astimezone(self.timezone)
        days_since_sunday = (local.weekday() + 1) % 7
        second = (
            days_since_sunday * SECONDS_PER_DAY
            + local.hour * 3600
            + local.minute * 60
            + local.second
        )
        weekly_open = any(
            interval.start_second <= second < interval.end_second
            for interval in self.intervals
        )
        return weekly_open and not self._holiday_closed(moment)


def _native_int(value: object, name: str) -> int:
    raw = getattr(value, name)
    if type(raw) is not int:
        raise TypeError(f"{name} must be int")
    return raw


def _optional_int(value: object, name: str) -> int | None:
    has_field = getattr(value, "HasField", None)
    if callable(has_field):
        try:
            if has_field(name) is not True:
                return None
        except (TypeError, ValueError):
            return None
    raw = getattr(value, name, None)
    if raw is None:
        return None
    if type(raw) is not int:
        raise TypeError(f"{name} must be int when present")
    return raw


def load_btcusd_ctrader_calendar() -> CTraderMarketCalendar:
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader authentication failed: {ready.error}")
        account_id = client.account_id
        listed = client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
            client_msg_id="crt-btcusd-calendar-list",
            timeout_seconds=30.0,
        )
        if isinstance(listed, Failure):
            raise RuntimeError(f"cTrader symbol discovery failed: {listed.error}")
        light = next(
            (
                item
                for item in cast(Iterable[object], getattr(listed.value, "symbol", ()))
                if getattr(item, "symbolName", None) == "BTCUSD"
                and getattr(item, "enabled", None) is True
            ),
            None,
        )
        if light is None:
            raise RuntimeError("BTCUSD unavailable on configured cTrader DEMO account")
        symbol_id = _native_int(light, "symbolId")
        details = client.request(
            "ProtoOASymbolByIdReq",
            {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
            client_msg_id="crt-btcusd-calendar-detail",
            timeout_seconds=30.0,
        )
        if isinstance(details, Failure):
            raise RuntimeError(f"cTrader symbol details failed: {details.error}")
        detail = next(
            (
                item
                for item in cast(Iterable[object], getattr(details.value, "symbol", ()))
                if getattr(item, "symbolId", None) == symbol_id
            ),
            None,
        )
        if detail is None:
            raise RuntimeError("BTCUSD symbol detail missing")
        timezone_name = getattr(detail, "scheduleTimeZone", None)
        if not isinstance(timezone_name, str) or not timezone_name:
            raise RuntimeError("BTCUSD schedule timezone missing")
        intervals = tuple(
            CTraderWeeklyInterval(
                start_second=_native_int(item, "startSecond"),
                end_second=_native_int(item, "endSecond"),
            )
            for item in cast(Iterable[object], getattr(detail, "schedule", ()))
        )
        holidays = tuple(
            CTraderHolidayInterval(
                holiday_date=_native_int(item, "holidayDate"),
                schedule_time_zone=str(getattr(item, "scheduleTimeZone", "")),
                is_recurring=getattr(item, "isRecurring", None) is True,
                start_second=_optional_int(item, "startSecond"),
                end_second=_optional_int(item, "endSecond"),
            )
            for item in cast(Iterable[object], getattr(detail, "holiday", ()))
        )
        return CTraderMarketCalendar(timezone_name, intervals, holidays)
    finally:
        client.close()
