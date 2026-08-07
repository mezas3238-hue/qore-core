from __future__ import annotations

import dataclasses
import datetime
import math
import typing

import qore.infrastructure.market_data as market_data
import qore.infrastructure.ports as ports
import qore.kernel.result as result_contract
type ExternalDecimalValue = str | float
type ExternalWholeNumberValue = str | int


class IngestionError(ports.ExternalPortError):
    """Base error for deterministic external-data normalization."""

    __slots__ = ()


class IngestionValidationError(IngestionError):
    """An external payload cannot be normalized into a canonical contract."""

    __slots__ = ()


@dataclasses.dataclass(frozen=True, slots=True)
class ExternalQuotePayload:
    """Provider-neutral quote payload before canonical normalization."""

    source: ports.ExternalSourceDescriptor
    instrument: str
    observed_at: datetime.datetime
    bid: ExternalDecimalValue
    ask: ExternalDecimalValue


@dataclasses.dataclass(frozen=True, slots=True)
class ExternalOhlcPayload:
    """Provider-neutral OHLC payload before canonical normalization."""

    source: ports.ExternalSourceDescriptor
    instrument: str
    timeframe_seconds: ExternalWholeNumberValue
    opened_at: datetime.datetime
    closed_at: datetime.datetime
    open: ExternalDecimalValue
    high: ExternalDecimalValue
    low: ExternalDecimalValue
    close: ExternalDecimalValue


class ExternalMarketDataPayloadPort(ports.ExternalPort, typing.Protocol):
    """Read boundary exposing provider-neutral payloads before normalization."""

    def read_external_quote(
        self,
        request: market_data.QuoteRequest,
        *,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[ExternalQuotePayload, ports.ExternalPortError]:
        """Read one external quote payload for deterministic normalization."""
        ...

    def read_external_ohlc(
        self,
        request: market_data.OhlcRequest,
        *,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[ExternalOhlcPayload, ports.ExternalPortError]:
        """Read one external OHLC payload for deterministic normalization."""
        ...


def _validation_failure(
    message: str,
) -> result_contract.Failure[ports.ExternalPortError]:
    return result_contract.Failure(IngestionValidationError(message))


def _validate_metadata(
    metadata: ports.ExternalRequestMetadata,
) -> result_contract.Result[None, ports.ExternalPortError]:
    if not isinstance(metadata, ports.ExternalRequestMetadata):
        return _validation_failure("ingestion metadata must be ExternalRequestMetadata")
    return result_contract.Success(None)


def _validate_market_data_source(
    source: object,
    *,
    expected: ports.ExternalSourceDescriptor | None = None,
    field_name: str,
) -> result_contract.Result[ports.ExternalSourceDescriptor, ports.ExternalPortError]:
    if not isinstance(source, ports.ExternalSourceDescriptor):
        return _validation_failure(f"{field_name} must be ExternalSourceDescriptor")
    name = source.port_name.value
    if name != "market-data" and not name.startswith("market-data."):
        return _validation_failure(f"{field_name} must use the market-data namespace")
    if expected is not None and source != expected:
        return _validation_failure(f"{field_name} must match port descriptor")
    return result_contract.Success(source)


def _normalize_instrument(
    value: object,
) -> result_contract.Result[market_data.Instrument, ports.ExternalPortError]:
    if not isinstance(value, str):
        return _validation_failure("external instrument must be a string")
    normalized = value.strip().upper()
    if not normalized:
        return _validation_failure("external instrument must not be empty")
    try:
        return result_contract.Success(market_data.Instrument(normalized))
    except ports.ExternalPortError as error:
        return _validation_failure(f"external instrument is invalid: {error}")


def _normalize_decimal(
    value: object,
    *,
    field_name: str,
) -> result_contract.Result[float, ports.ExternalPortError]:
    if type(value) is float:
        normalized = value
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return _validation_failure(f"external {field_name} must not be empty")
        try:
            normalized = float(candidate)
        except ValueError:
            return _validation_failure(
                f"external {field_name} must be a decimal string or float"
            )
    else:
        return _validation_failure(
            f"external {field_name} must be a decimal string or float"
        )
    if not math.isfinite(normalized) or normalized <= 0.0:
        return _validation_failure(
            f"external {field_name} must normalize to a positive finite float"
        )
    return result_contract.Success(normalized)


def _normalize_timeframe(
    value: object,
) -> result_contract.Result[market_data.Timeframe, ports.ExternalPortError]:
    if type(value) is int:
        normalized = value
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate or not candidate.isascii() or not candidate.isdecimal():
            return _validation_failure(
                "external timeframe_seconds must be a positive whole number"
            )
        normalized = int(candidate)
    else:
        return _validation_failure(
            "external timeframe_seconds must be an int or decimal string"
        )
    try:
        return result_contract.Success(market_data.Timeframe(normalized))
    except ports.ExternalPortError as error:
        return _validation_failure(f"external timeframe is invalid: {error}")


def _validate_timestamp(
    value: object,
    *,
    field_name: str,
) -> result_contract.Result[datetime.datetime, ports.ExternalPortError]:
    if not isinstance(value, datetime.datetime):
        return _validation_failure(f"external {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        return _validation_failure(f"external {field_name} must be timezone-aware")
    return result_contract.Success(value)


def _validate_payload_result_error(
    error: object,
    *,
    operation: str,
) -> result_contract.Result[ports.ExternalPortError, ports.ExternalPortError]:
    if not isinstance(error, ports.ExternalPortError):
        return _validation_failure(
            f"external {operation} failure error must be ExternalPortError"
        )
    return result_contract.Success(error)


def _read_quote_payload(
    port: ExternalMarketDataPayloadPort,
    request: market_data.QuoteRequest,
    *,
    metadata: ports.ExternalRequestMetadata,
) -> result_contract.Result[ExternalQuotePayload, ports.ExternalPortError]:
    try:
        result: object = port.read_external_quote(request, metadata=metadata)
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)
    if isinstance(result, result_contract.Failure):
        error_result = _validate_payload_result_error(result.error, operation="quote")
        if isinstance(error_result, result_contract.Failure):
            return error_result
        return result_contract.Failure(error_result.value)
    if not isinstance(result, result_contract.Success):
        return _validation_failure("external quote port must return Result")
    if not isinstance(result.value, ExternalQuotePayload):
        return _validation_failure(
            "external quote port must return ExternalQuotePayload"
        )
    return result_contract.Success(result.value)


def _read_ohlc_payload(
    port: ExternalMarketDataPayloadPort,
    request: market_data.OhlcRequest,
    *,
    metadata: ports.ExternalRequestMetadata,
) -> result_contract.Result[ExternalOhlcPayload, ports.ExternalPortError]:
    try:
        result: object = port.read_external_ohlc(request, metadata=metadata)
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)
    if isinstance(result, result_contract.Failure):
        error_result = _validate_payload_result_error(result.error, operation="OHLC")
        if isinstance(error_result, result_contract.Failure):
            return error_result
        return result_contract.Failure(error_result.value)
    if not isinstance(result, result_contract.Success):
        return _validation_failure("external OHLC port must return Result")
    if not isinstance(result.value, ExternalOhlcPayload):
        return _validation_failure("external OHLC port must return ExternalOhlcPayload")
    return result_contract.Success(result.value)


class MarketDataIngestionFlow:
    """Normalize external Market Data payloads into canonical immutable snapshots."""

    __slots__ = ("_descriptor", "_port")

    def __init__(self, port: ExternalMarketDataPayloadPort) -> None:
        descriptor_result = _validate_market_data_source(
            getattr(port, "descriptor", None),
            field_name="external market-data payload port descriptor",
        )
        if isinstance(descriptor_result, result_contract.Failure):
            raise descriptor_result.error
        if not callable(getattr(port, "health", None)):
            raise IngestionValidationError(
                "external market-data payload port must expose health"
            )
        if not callable(getattr(port, "read_external_quote", None)):
            raise IngestionValidationError(
                "external market-data payload port must expose read_external_quote"
            )
        if not callable(getattr(port, "read_external_ohlc", None)):
            raise IngestionValidationError(
                "external market-data payload port must expose read_external_ohlc"
            )
        self._port = port
        self._descriptor = descriptor_result.value

    @property
    def descriptor(self) -> ports.ExternalSourceDescriptor:
        return self._descriptor

    @property
    def port(self) -> ExternalMarketDataPayloadPort:
        return self._port

    def ingest_quote(
        self,
        request: market_data.QuoteRequest,
        *,
        snapshot_id: market_data.MarketDataSnapshotId,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[market_data.QuoteSnapshot, ports.ExternalPortError]:
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, result_contract.Failure):
            return metadata_result
        if not isinstance(request, market_data.QuoteRequest):
            return _validation_failure("quote ingestion request must be QuoteRequest")
        if not isinstance(snapshot_id, market_data.MarketDataSnapshotId):
            return _validation_failure(
                "quote ingestion snapshot_id must be MarketDataSnapshotId"
            )

        payload_result = _read_quote_payload(self.port, request, metadata=metadata)
        if isinstance(payload_result, result_contract.Failure):
            return payload_result
        payload = payload_result.value

        source_result = _validate_market_data_source(
            payload.source,
            expected=self.descriptor,
            field_name="external quote payload source",
        )
        if isinstance(source_result, result_contract.Failure):
            return source_result
        instrument_result = _normalize_instrument(payload.instrument)
        if isinstance(instrument_result, result_contract.Failure):
            return instrument_result
        if instrument_result.value != request.instrument:
            return _validation_failure(
                "external quote instrument must match the requested instrument"
            )
        observed_result = _validate_timestamp(
            payload.observed_at,
            field_name="quote observed_at",
        )
        if isinstance(observed_result, result_contract.Failure):
            return observed_result
        bid_result = _normalize_decimal(payload.bid, field_name="bid")
        if isinstance(bid_result, result_contract.Failure):
            return bid_result
        ask_result = _normalize_decimal(payload.ask, field_name="ask")
        if isinstance(ask_result, result_contract.Failure):
            return ask_result

        try:
            snapshot = market_data.QuoteSnapshot(
                snapshot_id=snapshot_id,
                instrument=instrument_result.value,
                source=source_result.value,
                observed_at=observed_result.value,
                bid=bid_result.value,
                ask=ask_result.value,
            )
        except ports.ExternalPortError as error:
            return _validation_failure(
                f"external quote cannot form a canonical snapshot: {error}"
            )
        return result_contract.Success(snapshot)

    def ingest_ohlc(
        self,
        request: market_data.OhlcRequest,
        *,
        snapshot_id: market_data.MarketDataSnapshotId,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[market_data.OhlcSnapshot, ports.ExternalPortError]:
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, result_contract.Failure):
            return metadata_result
        if not isinstance(request, market_data.OhlcRequest):
            return _validation_failure("OHLC ingestion request must be OhlcRequest")
        if not isinstance(snapshot_id, market_data.MarketDataSnapshotId):
            return _validation_failure(
                "OHLC ingestion snapshot_id must be MarketDataSnapshotId"
            )

        payload_result = _read_ohlc_payload(self.port, request, metadata=metadata)
        if isinstance(payload_result, result_contract.Failure):
            return payload_result
        payload = payload_result.value

        source_result = _validate_market_data_source(
            payload.source,
            expected=self.descriptor,
            field_name="external OHLC payload source",
        )
        if isinstance(source_result, result_contract.Failure):
            return source_result
        instrument_result = _normalize_instrument(payload.instrument)
        if isinstance(instrument_result, result_contract.Failure):
            return instrument_result
        if instrument_result.value != request.instrument:
            return _validation_failure(
                "external OHLC instrument must match the requested instrument"
            )
        timeframe_result = _normalize_timeframe(payload.timeframe_seconds)
        if isinstance(timeframe_result, result_contract.Failure):
            return timeframe_result
        if timeframe_result.value != request.timeframe:
            return _validation_failure(
                "external OHLC timeframe must match the requested timeframe"
            )
        opened_result = _validate_timestamp(
            payload.opened_at,
            field_name="OHLC opened_at",
        )
        if isinstance(opened_result, result_contract.Failure):
            return opened_result
        closed_result = _validate_timestamp(
            payload.closed_at,
            field_name="OHLC closed_at",
        )
        if isinstance(closed_result, result_contract.Failure):
            return closed_result
        if (
            opened_result.value != request.opened_at
            or closed_result.value != request.closed_at
        ):
            return _validation_failure(
                "external OHLC interval must match the requested interval"
            )

        open_result = _normalize_decimal(payload.open, field_name="open")
        if isinstance(open_result, result_contract.Failure):
            return open_result
        high_result = _normalize_decimal(payload.high, field_name="high")
        if isinstance(high_result, result_contract.Failure):
            return high_result
        low_result = _normalize_decimal(payload.low, field_name="low")
        if isinstance(low_result, result_contract.Failure):
            return low_result
        close_result = _normalize_decimal(payload.close, field_name="close")
        if isinstance(close_result, result_contract.Failure):
            return close_result

        try:
            snapshot = market_data.OhlcSnapshot(
                snapshot_id=snapshot_id,
                instrument=instrument_result.value,
                source=source_result.value,
                timeframe=timeframe_result.value,
                opened_at=opened_result.value,
                closed_at=closed_result.value,
                open=open_result.value,
                high=high_result.value,
                low=low_result.value,
                close=close_result.value,
            )
        except ports.ExternalPortError as error:
            return _validation_failure(
                f"external OHLC cannot form a canonical snapshot: {error}"
            )
        return result_contract.Success(snapshot)
