from __future__ import annotations

from datetime import datetime

from qore.infrastructure.ingestion import (
    ExternalOhlcPayload,
    ExternalQuotePayload,
)
from qore.infrastructure.market_data import OhlcRequest, QuoteRequest
from qore.infrastructure.ports import (
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
)
from qore.infrastructure.reference_adapters import (
    ReferenceAdapterValidationError,
    ReferenceDataNotFoundError,
)
from qore.kernel.result import Failure, Result, Success


def _validate_metadata(
    metadata: ExternalRequestMetadata,
) -> Result[None, ExternalPortError]:
    if not isinstance(metadata, ExternalRequestMetadata):
        return Failure(
            ReferenceAdapterValidationError(
                "metadata must be ExternalRequestMetadata"
            )
        )
    return Success(None)


def _validate_descriptor(descriptor: ExternalSourceDescriptor) -> None:
    if not isinstance(descriptor, ExternalSourceDescriptor):
        raise ReferenceAdapterValidationError(
            "reference payload adapter descriptor must be ExternalSourceDescriptor"
        )
    name = descriptor.port_name.value
    if name != "market-data" and not name.startswith("market-data."):
        raise ReferenceAdapterValidationError(
            "reference payload adapter descriptor must use the market-data namespace"
        )


class ReferenceExternalMarketDataPayloadAdapter:
    """Deterministic in-memory source of external payloads before normalization."""

    __slots__ = ("_descriptor", "_ohlc", "_quotes")

    def __init__(
        self,
        descriptor: ExternalSourceDescriptor,
        *,
        quotes: tuple[ExternalQuotePayload, ...] = (),
        ohlc: tuple[ExternalOhlcPayload, ...] = (),
    ) -> None:
        _validate_descriptor(descriptor)
        if not isinstance(quotes, tuple):
            raise ReferenceAdapterValidationError(
                "reference external quotes must be a tuple"
            )
        if not isinstance(ohlc, tuple):
            raise ReferenceAdapterValidationError(
                "reference external OHLC payloads must be a tuple"
            )

        quote_map: dict[str, ExternalQuotePayload] = {}
        for payload in quotes:
            if not isinstance(payload, ExternalQuotePayload):
                raise ReferenceAdapterValidationError(
                    "reference external quote entries must be ExternalQuotePayload"
                )
            if payload.source != descriptor:
                raise ReferenceAdapterValidationError(
                    "reference external quote source must match adapter descriptor"
                )
            key = payload.instrument.strip().upper()
            if not key:
                raise ReferenceAdapterValidationError(
                    "reference external quote instrument must not normalize to empty"
                )
            if key in quote_map:
                raise ReferenceAdapterValidationError(
                    "reference external quotes must contain at most one payload per instrument"
                )
            quote_map[key] = payload

        ohlc_map: dict[tuple[str, int, datetime, datetime], ExternalOhlcPayload] = {}
        for payload in ohlc:
            if not isinstance(payload, ExternalOhlcPayload):
                raise ReferenceAdapterValidationError(
                    "reference external OHLC entries must be ExternalOhlcPayload"
                )
            if payload.source != descriptor:
                raise ReferenceAdapterValidationError(
                    "reference external OHLC source must match adapter descriptor"
                )
            instrument = payload.instrument.strip().upper()
            if not instrument:
                raise ReferenceAdapterValidationError(
                    "reference external OHLC instrument must not normalize to empty"
                )
            timeframe = self._normalize_timeframe_key(payload.timeframe_seconds)
            key = (instrument, timeframe, payload.opened_at, payload.closed_at)
            if key in ohlc_map:
                raise ReferenceAdapterValidationError(
                    "reference external OHLC payloads must not contain duplicate intervals"
                )
            ohlc_map[key] = payload

        self._descriptor = descriptor
        self._quotes = quote_map
        self._ohlc = ohlc_map

    @staticmethod
    def _normalize_timeframe_key(value: str | int) -> int:
        if type(value) is int and value > 0:
            return value
        if isinstance(value, str):
            candidate = value.strip()
            if candidate.isascii() and candidate.isdecimal():
                normalized = int(candidate)
                if normalized > 0:
                    return normalized
        raise ReferenceAdapterValidationError(
            "reference external OHLC timeframe must normalize to a positive int"
        )

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self._descriptor

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, Failure):
            return metadata_result
        try:
            health = ExternalHealth(
                descriptor=self.descriptor,
                availability=PortAvailability.AVAILABLE,
                checked_at=checked_at,
            )
        except ExternalPortError as error:
            return Failure(error)
        return Success(health)

    def read_external_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, Failure):
            return metadata_result
        if not isinstance(request, QuoteRequest):
            return Failure(
                ReferenceAdapterValidationError("request must be QuoteRequest")
            )
        payload = self._quotes.get(request.instrument.symbol)
        if payload is None:
            return Failure(
                ReferenceDataNotFoundError(
                    f"reference external quote not found for {request.instrument.symbol}"
                )
            )
        return Success(payload)

    def read_external_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, Failure):
            return metadata_result
        if not isinstance(request, OhlcRequest):
            return Failure(
                ReferenceAdapterValidationError("request must be OhlcRequest")
            )
        key = (
            request.instrument.symbol,
            request.timeframe.seconds,
            request.opened_at,
            request.closed_at,
        )
        payload = self._ohlc.get(key)
        if payload is None:
            return Failure(
                ReferenceDataNotFoundError(
                    "reference external OHLC interval is not configured"
                )
            )
        return Success(payload)
