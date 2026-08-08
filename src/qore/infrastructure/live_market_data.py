from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from qore.infrastructure.ingestion import (
    ExternalOhlcPayload,
    ExternalQuotePayload,
    MarketDataIngestionFlow,
)
from qore.infrastructure.market_data import (
    MarketDataSnapshotId,
    OhlcRequest,
    OhlcSnapshot,
    QuoteRequest,
    QuoteSnapshot,
)
from qore.infrastructure.ports import (
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
)
from qore.infrastructure.read_only_provider_adapter import ReadOnlyExternalProviderAdapter
from qore.infrastructure.transport import (
    ExternalTransportRequest,
    ExternalTransportResponse,
)
from qore.kernel.result import Failure, Result, Success


class LiveMarketDataError(ExternalPortError):
    """Base error for controlled live market-data flow."""

    __slots__ = ()


class LiveMarketDataValidationError(LiveMarketDataError):
    """Violation of a live market-data composition invariant."""

    __slots__ = ()


class LiveMarketDataDecoderBoundary(Protocol):
    """Decode transport responses into existing provider-neutral ingestion payloads."""

    def decode_quote(
        self,
        response: ExternalTransportResponse,
        *,
        source: ExternalSourceDescriptor,
        request: QuoteRequest,
    ) -> Result[ExternalQuotePayload, ExternalPortError]: ...

    def decode_ohlc(
        self,
        response: ExternalTransportResponse,
        *,
        source: ExternalSourceDescriptor,
        request: OhlcRequest,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]: ...


class LiveMarketDataRequestFactoryBoundary(Protocol):
    """Build provider transport reads from canonical market-data requests."""

    def quote_request(self, request: QuoteRequest) -> ExternalTransportRequest: ...

    def ohlc_request(self, request: OhlcRequest) -> ExternalTransportRequest: ...


@dataclass(frozen=True, slots=True)
class LiveMarketDataPayloadAdapter:
    """Bridge supervised provider reads into the existing ingestion flow."""

    provider: ReadOnlyExternalProviderAdapter
    request_factory: LiveMarketDataRequestFactoryBoundary
    decoder: LiveMarketDataDecoderBoundary
    resolved_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.provider, ReadOnlyExternalProviderAdapter):
            raise LiveMarketDataValidationError(
                "live market-data provider must be ReadOnlyExternalProviderAdapter"
            )
        if not isinstance(self.resolved_at, datetime):
            raise LiveMarketDataValidationError("resolved_at must be a datetime")
        if self.resolved_at.tzinfo is None or self.resolved_at.utcoffset() is None:
            raise LiveMarketDataValidationError("resolved_at must be timezone-aware")
        if not self.provider.source.port_name.value.startswith("market-data"):
            raise LiveMarketDataValidationError(
                "live market-data source must use market-data namespace"
            )

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self.provider.source

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        if not isinstance(metadata, ExternalRequestMetadata):
            return Failure(LiveMarketDataValidationError("metadata must be explicit"))
        try:
            return Success(
                ExternalHealth(
                    descriptor=self.descriptor,
                    availability=(
                        PortAvailability.AVAILABLE
                        if self.provider.configuration.activation.can_activate
                        else PortAvailability.UNAVAILABLE
                    ),
                    checked_at=checked_at,
                    message=(
                        None
                        if self.provider.configuration.activation.can_activate
                        else "provider activation blocked"
                    ),
                )
            )
        except ExternalPortError as error:
            return Failure(error)

    def read_external_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        if not isinstance(request, QuoteRequest):
            return Failure(LiveMarketDataValidationError("request must be QuoteRequest"))
        transport_request = self.request_factory.quote_request(request)
        response = self.provider.read(
            transport_request,
            metadata=metadata,
            resolved_at=self.resolved_at,
        )
        if isinstance(response, Failure):
            return Failure(response.error)
        if not response.value.is_success:
            return Failure(
                LiveMarketDataError(
                    f"market-data quote transport status={response.value.status_code}"
                )
            )
        return self.decoder.decode_quote(
            response.value,
            source=self.descriptor,
            request=request,
        )

    def read_external_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        if not isinstance(request, OhlcRequest):
            return Failure(LiveMarketDataValidationError("request must be OhlcRequest"))
        transport_request = self.request_factory.ohlc_request(request)
        response = self.provider.read(
            transport_request,
            metadata=metadata,
            resolved_at=self.resolved_at,
        )
        if isinstance(response, Failure):
            return Failure(response.error)
        if not response.value.is_success:
            return Failure(
                LiveMarketDataError(
                    f"market-data OHLC transport status={response.value.status_code}"
                )
            )
        return self.decoder.decode_ohlc(
            response.value,
            source=self.descriptor,
            request=request,
        )


@dataclass(frozen=True, slots=True)
class ControlledLiveMarketDataFlow:
    """Canonical market-data facade over supervised read-only provider connectivity."""

    payload_adapter: LiveMarketDataPayloadAdapter

    def __post_init__(self) -> None:
        if not isinstance(self.payload_adapter, LiveMarketDataPayloadAdapter):
            raise LiveMarketDataValidationError(
                "live market-data flow requires LiveMarketDataPayloadAdapter"
            )

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self.payload_adapter.descriptor

    def read_quote(
        self,
        request: QuoteRequest,
        *,
        snapshot_id: MarketDataSnapshotId,
        metadata: ExternalRequestMetadata,
    ) -> Result[QuoteSnapshot, ExternalPortError]:
        return MarketDataIngestionFlow(self.payload_adapter).ingest_quote(
            request,
            snapshot_id=snapshot_id,
            metadata=metadata,
        )

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
