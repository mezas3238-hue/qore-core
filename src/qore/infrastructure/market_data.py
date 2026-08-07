from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from re import fullmatch
from typing import Protocol
from uuid import UUID

from qore.infrastructure.ports import (
    ExternalPort,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.kernel.result import Result


class MarketDataError(ExternalPortError):
    """Base error for canonical market-data boundaries."""

    __slots__ = ()


class MarketDataValidationError(MarketDataError):
    """Violation of a canonical market-data invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class MarketDataSnapshotId:
    """Explicit identity of one canonical market-data snapshot."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise MarketDataValidationError("market-data snapshot id must be a UUID")


@dataclass(frozen=True, slots=True)
class Instrument:
    """Canonical provider-neutral instrument symbol."""

    symbol: str

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or fullmatch(
            r"[A-Z0-9][A-Z0-9._/-]*", self.symbol
        ) is None:
            raise MarketDataValidationError(
                "instrument symbol must be canonical uppercase ASCII"
            )


@dataclass(frozen=True, slots=True)
class Timeframe:
    """Canonical OHLC timeframe expressed as a positive whole number of seconds."""

    seconds: int

    def __post_init__(self) -> None:
        if type(self.seconds) is not int or self.seconds <= 0:
            raise MarketDataValidationError("timeframe seconds must be a positive int")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise MarketDataValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketDataValidationError(f"{field_name} must be timezone-aware")


def _validate_price(value: float, *, field_name: str) -> None:
    if type(value) is not float or not isfinite(value) or value <= 0.0:
        raise MarketDataValidationError(
            f"{field_name} must be a positive finite float"
        )


def _validate_market_data_source(
    source: ExternalSourceDescriptor,
    *,
    field_name: str,
) -> None:
    if not isinstance(source, ExternalSourceDescriptor):
        raise MarketDataValidationError(
            f"{field_name} source must be ExternalSourceDescriptor"
        )
    name = source.port_name.value
    if name != "market-data" and not name.startswith("market-data."):
        raise MarketDataValidationError(
            f"{field_name} source port must use the market-data namespace"
        )


@dataclass(frozen=True, slots=True)
class QuoteSnapshot:
    """Immutable canonical bid/ask snapshot from one explicit source."""

    snapshot_id: MarketDataSnapshotId
    instrument: Instrument
    source: ExternalSourceDescriptor
    observed_at: datetime
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, MarketDataSnapshotId):
            raise MarketDataValidationError(
                "quote snapshot_id must be MarketDataSnapshotId"
            )
        if not isinstance(self.instrument, Instrument):
            raise MarketDataValidationError("quote instrument must be Instrument")
        _validate_market_data_source(self.source, field_name="quote")
        _validate_timestamp(self.observed_at, field_name="quote observed_at")
        _validate_price(self.bid, field_name="bid")
        _validate_price(self.ask, field_name="ask")
        if self.bid > self.ask:
            raise MarketDataValidationError("quote bid must not exceed ask")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.snapshot_id.value),
            self.instrument.symbol,
            self.source.logical_values(),
            self.observed_at.isoformat(),
            self.bid,
            self.ask,
        )


@dataclass(frozen=True, slots=True)
class OhlcSnapshot:
    """Immutable canonical OHLC bar over an explicit closed interval."""

    snapshot_id: MarketDataSnapshotId
    instrument: Instrument
    source: ExternalSourceDescriptor
    timeframe: Timeframe
    opened_at: datetime
    closed_at: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, MarketDataSnapshotId):
            raise MarketDataValidationError(
                "OHLC snapshot_id must be MarketDataSnapshotId"
            )
        if not isinstance(self.instrument, Instrument):
            raise MarketDataValidationError("OHLC instrument must be Instrument")
        _validate_market_data_source(self.source, field_name="OHLC")
        if not isinstance(self.timeframe, Timeframe):
            raise MarketDataValidationError("OHLC timeframe must be Timeframe")
        _validate_timestamp(self.opened_at, field_name="OHLC opened_at")
        _validate_timestamp(self.closed_at, field_name="OHLC closed_at")
        if self.closed_at <= self.opened_at:
            raise MarketDataValidationError("OHLC closed_at must be after opened_at")
        if (self.closed_at - self.opened_at).total_seconds() != self.timeframe.seconds:
            raise MarketDataValidationError(
                "OHLC interval must exactly match timeframe seconds"
            )
        _validate_price(self.open, field_name="open")
        _validate_price(self.high, field_name="high")
        _validate_price(self.low, field_name="low")
        _validate_price(self.close, field_name="close")
        if self.low > self.high:
            raise MarketDataValidationError("OHLC low must not exceed high")
        if not self.low <= self.open <= self.high:
            raise MarketDataValidationError("OHLC open must be within low/high")
        if not self.low <= self.close <= self.high:
            raise MarketDataValidationError("OHLC close must be within low/high")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.snapshot_id.value),
            self.instrument.symbol,
            self.source.logical_values(),
            self.timeframe.seconds,
            self.opened_at.isoformat(),
            self.closed_at.isoformat(),
            self.open,
            self.high,
            self.low,
            self.close,
        )


@dataclass(frozen=True, slots=True)
class QuoteRequest:
    """Provider-neutral request for the canonical quote of one instrument."""

    instrument: Instrument

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise MarketDataValidationError("quote request instrument must be Instrument")


@dataclass(frozen=True, slots=True)
class OhlcRequest:
    """Provider-neutral request for a canonical OHLC interval."""

    instrument: Instrument
    timeframe: Timeframe
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise MarketDataValidationError("OHLC request instrument must be Instrument")
        if not isinstance(self.timeframe, Timeframe):
            raise MarketDataValidationError("OHLC request timeframe must be Timeframe")
        _validate_timestamp(self.opened_at, field_name="OHLC request opened_at")
        _validate_timestamp(self.closed_at, field_name="OHLC request closed_at")
        if self.closed_at <= self.opened_at:
            raise MarketDataValidationError(
                "OHLC request closed_at must be after opened_at"
            )
        if (self.closed_at - self.opened_at).total_seconds() != self.timeframe.seconds:
            raise MarketDataValidationError(
                "OHLC request interval must exactly match timeframe seconds"
            )


class MarketDataPort(ExternalPort, Protocol):
    """Provider-neutral typed read port for canonical market data."""

    def read_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[QuoteSnapshot, ExternalPortError]:
        """Read one canonical quote through an external boundary."""
        ...

    def read_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OhlcSnapshot, ExternalPortError]:
        """Read one canonical OHLC bar through an external boundary."""
        ...
