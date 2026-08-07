from __future__ import annotations

from typing import cast
from uuid import UUID

from qore.infrastructure.market_data import Instrument, QuoteRequest
from qore.infrastructure.persistence import LoadPersistenceRequest, PersistenceKey
from qore.infrastructure.ports import (
    AdapterId,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.reference_adapters import (
    ReferenceAdapterValidationError,
    ReferenceMarketDataAdapter,
    ReferencePersistenceAdapter,
)
from qore.kernel.result import Failure

_MARKET_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("d2000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("d2000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.reference"),
)
_PERSISTENCE_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("d2000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("d2000000-0000-0000-0000-000000000004")),
    port_name=PortName("persistence.reference"),
)


def test_reference_market_data_adapter_rejects_runtime_metadata_bypass() -> None:
    adapter = ReferenceMarketDataAdapter(_MARKET_DESCRIPTOR)

    result = adapter.read_quote(
        QuoteRequest(Instrument("EURUSD")),
        metadata=cast(ExternalRequestMetadata, object()),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReferenceAdapterValidationError)


def test_reference_persistence_adapter_rejects_runtime_metadata_bypass() -> None:
    adapter: ReferencePersistenceAdapter[str] = ReferencePersistenceAdapter(
        _PERSISTENCE_DESCRIPTOR
    )

    result = adapter.load(
        LoadPersistenceRequest(PersistenceKey("tests", "metadata")),
        metadata=cast(ExternalRequestMetadata, object()),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReferenceAdapterValidationError)
