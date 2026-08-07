from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from qore.infrastructure.market_data import (
    OhlcRequest,
    OhlcSnapshot,
    QuoteRequest,
    QuoteSnapshot,
)
from qore.infrastructure.persistence import (
    LoadPersistenceRequest,
    PersistenceConflictError,
    PersistenceKey,
    SavePersistenceRequest,
    StoredRecord,
)
from qore.infrastructure.ports import (
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
)
from qore.kernel.result import Failure, Result, Success


class ReferenceAdapterError(ExternalPortError):
    """Base error for deterministic reference adapters."""

    __slots__ = ()


class ReferenceAdapterValidationError(ReferenceAdapterError):
    """Invalid deterministic reference-adapter configuration."""

    __slots__ = ()


class ReferenceDataNotFoundError(ReferenceAdapterError):
    """Requested reference data is not configured on this adapter instance."""

    __slots__ = ()


class ReferenceAdapterCopyError(ReferenceAdapterError):
    """A persistence value could not be defensively copied."""

    __slots__ = ()


def _require_descriptor_namespace(
    descriptor: ExternalSourceDescriptor,
    *,
    namespace: str,
) -> None:
    if not isinstance(descriptor, ExternalSourceDescriptor):
        raise ReferenceAdapterValidationError(
            "reference adapter descriptor must be ExternalSourceDescriptor"
        )
    name = descriptor.port_name.value
    if name != namespace and not name.startswith(f"{namespace}."):
        raise ReferenceAdapterValidationError(
            f"reference adapter descriptor must use the {namespace} namespace"
        )


def _health(
    descriptor: ExternalSourceDescriptor,
    *,
    checked_at: datetime,
) -> Result[ExternalHealth, ExternalPortError]:
    try:
        health = ExternalHealth(
            descriptor=descriptor,
            availability=PortAvailability.AVAILABLE,
            checked_at=checked_at,
        )
    except ExternalPortError as error:
        return Failure(error)
    return Success(health)


class ReferenceMarketDataAdapter:
    """Deterministic in-memory implementation of the canonical MarketDataPort."""

    __slots__ = ("_descriptor", "_ohlc", "_quotes")

    def __init__(
        self,
        descriptor: ExternalSourceDescriptor,
        *,
        quotes: tuple[QuoteSnapshot, ...] = (),
        ohlc: tuple[OhlcSnapshot, ...] = (),
    ) -> None:
        _require_descriptor_namespace(descriptor, namespace="market-data")
        if not isinstance(quotes, tuple):
            raise ReferenceAdapterValidationError("reference quotes must be a tuple")
        if not isinstance(ohlc, tuple):
            raise ReferenceAdapterValidationError("reference OHLC data must be a tuple")

        quote_map: dict[str, QuoteSnapshot] = {}
        for snapshot in quotes:
            if not isinstance(snapshot, QuoteSnapshot):
                raise ReferenceAdapterValidationError(
                    "reference quote entries must be QuoteSnapshot"
                )
            if snapshot.source != descriptor:
                raise ReferenceAdapterValidationError(
                    "reference quote source must match adapter descriptor"
                )
            key = snapshot.instrument.symbol
            if key in quote_map:
                raise ReferenceAdapterValidationError(
                    "reference quotes must contain at most one snapshot per instrument"
                )
            quote_map[key] = snapshot

        ohlc_map: dict[tuple[str, int, datetime, datetime], OhlcSnapshot] = {}
        for snapshot in ohlc:
            if not isinstance(snapshot, OhlcSnapshot):
                raise ReferenceAdapterValidationError(
                    "reference OHLC entries must be OhlcSnapshot"
                )
            if snapshot.source != descriptor:
                raise ReferenceAdapterValidationError(
                    "reference OHLC source must match adapter descriptor"
                )
            key = (
                snapshot.instrument.symbol,
                snapshot.timeframe.seconds,
                snapshot.opened_at,
                snapshot.closed_at,
            )
            if key in ohlc_map:
                raise ReferenceAdapterValidationError(
                    "reference OHLC data must not contain duplicate intervals"
                )
            ohlc_map[key] = snapshot

        self._descriptor = descriptor
        self._quotes = quote_map
        self._ohlc = ohlc_map

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self._descriptor

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        return _health(self.descriptor, checked_at=checked_at)

    def read_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[QuoteSnapshot, ExternalPortError]:
        del metadata
        if not isinstance(request, QuoteRequest):
            return Failure(ReferenceAdapterValidationError("request must be QuoteRequest"))
        snapshot = self._quotes.get(request.instrument.symbol)
        if snapshot is None:
            return Failure(
                ReferenceDataNotFoundError(
                    f"reference quote not found for {request.instrument.symbol}"
                )
            )
        return Success(snapshot)

    def read_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OhlcSnapshot, ExternalPortError]:
        del metadata
        if not isinstance(request, OhlcRequest):
            return Failure(ReferenceAdapterValidationError("request must be OhlcRequest"))
        key = (
            request.instrument.symbol,
            request.timeframe.seconds,
            request.opened_at,
            request.closed_at,
        )
        snapshot = self._ohlc.get(key)
        if snapshot is None:
            return Failure(
                ReferenceDataNotFoundError(
                    "reference OHLC interval is not configured"
                )
            )
        return Success(snapshot)


class ReferencePersistenceAdapter[ValueT]:
    """Deterministic in-memory PersistencePort with defensive value copying."""

    __slots__ = ("_descriptor", "_records")

    def __init__(self, descriptor: ExternalSourceDescriptor) -> None:
        _require_descriptor_namespace(descriptor, namespace="persistence")
        self._descriptor = descriptor
        self._records: dict[PersistenceKey, StoredRecord[ValueT]] = {}

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self._descriptor

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        return _health(self.descriptor, checked_at=checked_at)

    def _clone_value(self, value: ValueT) -> Result[ValueT, ExternalPortError]:
        try:
            cloned = deepcopy(value)
        except Exception as error:
            return Failure(
                ReferenceAdapterCopyError(
                    f"persistence value cannot be defensively copied: {error}"
                )
            )
        return Success(cloned)

    def _clone_record(
        self,
        record: StoredRecord[ValueT],
    ) -> Result[StoredRecord[ValueT], ExternalPortError]:
        value_result = self._clone_value(record.value)
        if isinstance(value_result, Failure):
            return value_result
        return Success(
            StoredRecord(
                key=record.key,
                version=record.version,
                value=value_result.value,
                source=record.source,
                stored_at=record.stored_at,
            )
        )

    def load(
        self,
        request: LoadPersistenceRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[StoredRecord[ValueT] | None, ExternalPortError]:
        del metadata
        if not isinstance(request, LoadPersistenceRequest):
            return Failure(
                ReferenceAdapterValidationError(
                    "request must be LoadPersistenceRequest"
                )
            )
        record = self._records.get(request.key)
        if record is None:
            return Success(None)
        return self._clone_record(record)

    def save(
        self,
        request: SavePersistenceRequest[ValueT],
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[StoredRecord[ValueT], ExternalPortError]:
        del metadata
        if not isinstance(request, SavePersistenceRequest):
            return Failure(
                ReferenceAdapterValidationError(
                    "request must be SavePersistenceRequest"
                )
            )

        current = self._records.get(request.key)
        if request.expected_version is None:
            if current is not None:
                return Failure(PersistenceConflictError("record already exists"))
        elif current is None or current.version != request.expected_version:
            return Failure(PersistenceConflictError("expected version does not match"))

        value_result = self._clone_value(request.value)
        if isinstance(value_result, Failure):
            return value_result
        stored = StoredRecord(
            key=request.key,
            version=request.version,
            value=value_result.value,
            source=self.descriptor,
            stored_at=request.stored_at,
        )
        self._records[request.key] = stored
        return self._clone_record(stored)
