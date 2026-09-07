from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from qore.infrastructure.ingestion import (
    ExternalOhlcPayload,
    ExternalQuotePayload,
    MarketDataIngestionFlow,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcRequest,
    OhlcSnapshot,
    QuoteRequest,
    Timeframe,
)
from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.infrastructure.ports import (
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.kernel.result import Failure, Result, Success

_CTRADER_RELATIVE_PRICE_SCALE = Decimal(100_000)
_DAILY_SECONDS = 86_400


class CTraderDemoMarketDataError(ExternalPortError):
    """Base error for the cTrader DEMO market-data boundary."""

    __slots__ = ()


class CTraderDemoMarketDataValidationError(CTraderDemoMarketDataError):
    """Provider data violates the cTrader DEMO candle contract."""

    __slots__ = ()


class CTraderDemoMarketDataUnsupportedError(CTraderDemoMarketDataError):
    """Requested functionality is outside the limited candle-only delivery."""

    __slots__ = ()


class CTraderTrendbarPeriod(StrEnum):
    """Provider-native cTrader trendbar periods admitted by this delivery.

    The exact native identifiers and wire codes come from the cTrader Open API
    ``ProtoOATrendbarPeriod`` enum (spotware/openapi-proto-messages,
    ``OpenApiModelMessages.proto``): M1=1, M5=5, M15=7, M30=8, H1=9, D1=12.

    The cTrader native Daily identifier is ``D1`` (not ``"D"``). It is mapped
    explicitly and immutably to canonical QORE daily via
    ``canonical_timeframe_code`` (``MarketTimeframeCode.D1``) and to the legacy
    fixed-duration contract as ``Timeframe(86400)``.
    """

    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    D1 = "D1"

    @property
    def seconds(self) -> int:
        """Exact interval duration in seconds for the fixed-duration contract."""
        return _SECONDS_BY_PERIOD[self]

    @property
    def is_daily(self) -> bool:
        """True when the period is the UTC calendar-day period (D1)."""
        return self is CTraderTrendbarPeriod.D1

    @property
    def canonical_timeframe_code(self) -> MarketTimeframeCode:
        """Canonical Core-facing timeframe code this native period maps to."""
        return _CANONICAL_TIMEFRAME_CODE_BY_PERIOD[self]


_SECONDS_BY_PERIOD: MappingProxyType[CTraderTrendbarPeriod, int] = MappingProxyType(
    {
        CTraderTrendbarPeriod.M1: 60,
        CTraderTrendbarPeriod.M5: 300,
        CTraderTrendbarPeriod.M15: 900,
        CTraderTrendbarPeriod.M30: 1800,
        CTraderTrendbarPeriod.H1: 3600,
        CTraderTrendbarPeriod.D1: _DAILY_SECONDS,
    }
)

_CANONICAL_TIMEFRAME_CODE_BY_PERIOD: MappingProxyType[
    CTraderTrendbarPeriod, MarketTimeframeCode
] = MappingProxyType(
    {
        CTraderTrendbarPeriod.M1: MarketTimeframeCode.M1,
        CTraderTrendbarPeriod.M5: MarketTimeframeCode.M5,
        CTraderTrendbarPeriod.M15: MarketTimeframeCode.M15,
        CTraderTrendbarPeriod.M30: MarketTimeframeCode.M30,
        CTraderTrendbarPeriod.H1: MarketTimeframeCode.H1,
        CTraderTrendbarPeriod.D1: MarketTimeframeCode.D1,
    }
)

_PERIOD_BY_SECONDS: MappingProxyType[int, CTraderTrendbarPeriod] = MappingProxyType(
    {seconds: period for period, seconds in _SECONDS_BY_PERIOD.items()}
)

if len(_PERIOD_BY_SECONDS) != len(_SECONDS_BY_PERIOD):
    raise CTraderDemoMarketDataValidationError(
        "cTrader period-to-seconds mapping must be a bijection"
    )


def _period_for_timeframe(timeframe: Timeframe) -> CTraderTrendbarPeriod | None:
    return _PERIOD_BY_SECONDS.get(timeframe.seconds)


def _is_utc_midnight(value: datetime) -> bool:
    utc_value = value.astimezone(UTC)
    return (
        utc_value.hour == 0
        and utc_value.minute == 0
        and utc_value.second == 0
        and utc_value.microsecond == 0
    )


@dataclass(frozen=True, slots=True)
class CTraderTrendbar:
    """Provider-relative cTrader trendbar values before QORE normalization."""

    low_relative: int
    delta_open: int
    delta_high: int
    delta_close: int
    utc_timestamp_in_minutes: int

    def __post_init__(self) -> None:
        if type(self.low_relative) is not int or self.low_relative <= 0:
            raise CTraderDemoMarketDataValidationError(
                "cTrader trendbar low_relative must be a positive int"
            )
        for field_name, value in (
            ("delta_open", self.delta_open),
            ("delta_high", self.delta_high),
            ("delta_close", self.delta_close),
            ("utc_timestamp_in_minutes", self.utc_timestamp_in_minutes),
        ):
            if type(value) is not int or value < 0:
                raise CTraderDemoMarketDataValidationError(
                    f"cTrader trendbar {field_name} must be a non-negative int"
                )
        if self.delta_open > self.delta_high:
            raise CTraderDemoMarketDataValidationError(
                "cTrader trendbar delta_open must not exceed delta_high"
            )
        if self.delta_close > self.delta_high:
            raise CTraderDemoMarketDataValidationError(
                "cTrader trendbar delta_close must not exceed delta_high"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (
            self.low_relative,
            self.delta_open,
            self.delta_high,
            self.delta_close,
            self.utc_timestamp_in_minutes,
        )


@dataclass(frozen=True, slots=True)
class CTraderTrendbarReadResult:
    """Sanitized provider result returned by an injected cTrader runtime client."""

    instrument: str
    symbol_id: int
    digits: int
    period: CTraderTrendbarPeriod
    trendbars: tuple[CTraderTrendbar, ...]
    has_more: bool = False

    def __post_init__(self) -> None:
        try:
            Instrument(self.instrument)
        except ExternalPortError as error:
            raise CTraderDemoMarketDataValidationError(
                "cTrader result instrument must be a canonical QORE instrument"
            ) from error
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderDemoMarketDataValidationError(
                "cTrader result symbol_id must be a positive int"
            )
        if type(self.digits) is not int or self.digits < 0:
            raise CTraderDemoMarketDataValidationError(
                "cTrader result digits must be a non-negative int"
            )
        if not isinstance(self.period, CTraderTrendbarPeriod):
            raise CTraderDemoMarketDataValidationError(
                "cTrader result period must be CTraderTrendbarPeriod"
            )
        if type(self.trendbars) is not tuple or any(
            type(item) is not CTraderTrendbar for item in self.trendbars
        ):
            raise CTraderDemoMarketDataValidationError(
                "cTrader result trendbars must be an immutable CTraderTrendbar tuple"
            )
        if type(self.has_more) is not bool:
            raise CTraderDemoMarketDataValidationError(
                "cTrader result has_more must be a strict bool"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument,
            self.symbol_id,
            self.digits,
            self.period.value,
            tuple(item.logical_values() for item in self.trendbars),
            self.has_more,
        )


class CTraderDemoTrendbarClientBoundary(Protocol):
    """Injected provider runtime that owns cTrader connection/auth lifecycle."""

    @property
    def descriptor(self) -> ExternalSourceDescriptor: ...

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]: ...

    def read_trendbars(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderTrendbarReadResult, ExternalPortError]: ...


def _price_from_relative(value: int, *, digits: int) -> Result[str, ExternalPortError]:
    if type(value) is not int or value <= 0:
        return Failure(
            CTraderDemoMarketDataValidationError(
                "cTrader reconstructed relative price must be a positive int"
            )
        )
    if type(digits) is not int or digits < 0:
        return Failure(
            CTraderDemoMarketDataValidationError(
                "cTrader symbol digits must be a non-negative int"
            )
        )
    try:
        scaled = Decimal(value) / _CTRADER_RELATIVE_PRICE_SCALE
        quantum = Decimal(1).scaleb(-digits)
        rounded = scaled.quantize(quantum, rounding=ROUND_HALF_EVEN)
    except (InvalidOperation, ValueError):
        return Failure(
            CTraderDemoMarketDataValidationError(
                "cTrader relative price cannot be normalized with symbol digits"
            )
        )
    if not rounded.is_finite() or rounded <= 0:
        return Failure(
            CTraderDemoMarketDataValidationError(
                "cTrader normalized price must be positive and finite"
            )
        )
    return Success(format(rounded, f".{digits}f"))


def _opened_at_from_minutes(value: int) -> Result[datetime, ExternalPortError]:
    if type(value) is not int or value < 0:
        return Failure(
            CTraderDemoMarketDataValidationError(
                "cTrader trendbar timestamp minutes must be a non-negative int"
            )
        )
    try:
        opened_at = datetime.fromtimestamp(value * 60, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return Failure(
            CTraderDemoMarketDataValidationError(
                "cTrader trendbar timestamp minutes are outside supported datetime range"
            )
        )
    return Success(opened_at)


@dataclass(frozen=True, slots=True)
class CTraderDemoMarketDataPayloadAdapter:
    """Translate cTrader DEMO closed trendbars into QORE ingestion payloads."""

    client: CTraderDemoTrendbarClientBoundary

    def __post_init__(self) -> None:
        descriptor = getattr(self.client, "descriptor", None)
        if not isinstance(descriptor, ExternalSourceDescriptor):
            raise CTraderDemoMarketDataValidationError(
                "cTrader client descriptor must be ExternalSourceDescriptor"
            )
        if not descriptor.port_name.value.startswith("market-data.ctrader"):
            raise CTraderDemoMarketDataValidationError(
                "cTrader client source must use market-data.ctrader namespace"
            )
        if not callable(getattr(self.client, "health", None)):
            raise CTraderDemoMarketDataValidationError(
                "cTrader client must expose health"
            )
        if not callable(getattr(self.client, "read_trendbars", None)):
            raise CTraderDemoMarketDataValidationError(
                "cTrader client must expose read_trendbars"
            )

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self.client.descriptor

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        return self.client.health(checked_at=checked_at, metadata=metadata)

    def read_external_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        del request, metadata
        return Failure(
            CTraderDemoMarketDataUnsupportedError(
                "cTrader delivery supports closed OHLC reads only"
            )
        )

    def read_external_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        if not isinstance(request, OhlcRequest):
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader OHLC read requires OhlcRequest"
                )
            )
        period = _period_for_timeframe(request.timeframe)
        if period is None:
            return Failure(
                CTraderDemoMarketDataUnsupportedError(
                    "cTrader delivery supports native M1/M5/M15/M30/H1/D1 only"
                )
            )
        if period.is_daily and not _is_utc_midnight(request.opened_at):
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader daily interval must open at UTC midnight"
                )
            )
        try:
            result = self.client.read_trendbars(request, metadata=metadata)
        except ExternalPortError as error:
            return Failure(error)
        if isinstance(result, Failure):
            return Failure(result.error)
        if not isinstance(result, Success) or not isinstance(
            result.value, CTraderTrendbarReadResult
        ):
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader client must return Result[CTraderTrendbarReadResult]"
                )
            )
        response = result.value
        if response.instrument != request.instrument.symbol:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader result instrument must match requested instrument"
                )
            )
        if response.period is not period:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader trendbar period must match requested timeframe"
                )
            )
        if response.has_more:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader exact-interval result must not be truncated"
                )
            )
        if len(response.trendbars) != 1:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader exact-interval result must contain exactly one trendbar"
                )
            )

        trendbar = response.trendbars[0]
        if trendbar.utc_timestamp_in_minutes % (period.seconds // 60) != 0:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader trendbar open must align to the requested period grid"
                )
            )
        opened_at_result = _opened_at_from_minutes(trendbar.utc_timestamp_in_minutes)
        if isinstance(opened_at_result, Failure):
            return opened_at_result
        opened_at = opened_at_result.value
        try:
            closed_at = opened_at + timedelta(seconds=period.seconds)
        except OverflowError:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader trendbar interval is outside supported datetime range"
                )
            )
        if opened_at != request.opened_at or closed_at != request.closed_at:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "cTrader trendbar interval must match requested interval"
                )
            )

        low_relative = trendbar.low_relative
        relative_prices = {
            "open": low_relative + trendbar.delta_open,
            "high": low_relative + trendbar.delta_high,
            "low": low_relative,
            "close": low_relative + trendbar.delta_close,
        }
        normalized: dict[str, str] = {}
        for field_name, relative_price in relative_prices.items():
            price_result = _price_from_relative(relative_price, digits=response.digits)
            if isinstance(price_result, Failure):
                return price_result
            normalized[field_name] = price_result.value

        return Success(
            ExternalOhlcPayload(
                source=self.descriptor,
                instrument=response.instrument,
                timeframe_seconds=period.seconds,
                opened_at=opened_at,
                closed_at=closed_at,
                open=normalized["open"],
                high=normalized["high"],
                low=normalized["low"],
                close=normalized["close"],
            )
        )


@dataclass(frozen=True, slots=True)
class CTraderDemoMarketDataFlow:
    """Canonical QORE facade for one injected cTrader DEMO candle client."""

    payload_adapter: CTraderDemoMarketDataPayloadAdapter

    def __post_init__(self) -> None:
        if not isinstance(self.payload_adapter, CTraderDemoMarketDataPayloadAdapter):
            raise CTraderDemoMarketDataValidationError(
                "cTrader flow requires CTraderDemoMarketDataPayloadAdapter"
            )

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self.payload_adapter.descriptor

    def read_ohlc(
        self,
        request: OhlcRequest,
        *,
        snapshot_id: MarketDataSnapshotId,
        metadata: ExternalRequestMetadata,
    ) -> Result[OhlcSnapshot, ExternalPortError]:
        return MarketDataIngestionFlow(self.payload_adapter).ingest_ohlc(
            request,
            snapshot_id=snapshot_id,
            metadata=metadata,
        )
