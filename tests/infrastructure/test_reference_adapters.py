from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataPort,
    MarketDataSnapshotId,
    OhlcRequest,
    OhlcSnapshot,
    QuoteRequest,
    QuoteSnapshot,
    Timeframe,
)
from qore.infrastructure.persistence import (
    LoadPersistenceRequest,
    PersistenceConflictError,
    PersistenceKey,
    PersistencePort,
    PersistenceVersion,
    SavePersistenceRequest,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
from qore.infrastructure.reference_adapters import (
    ReferenceAdapterCopyError,
    ReferenceAdapterValidationError,
    ReferenceDataNotFoundError,
    ReferenceMarketDataAdapter,
    ReferencePersistenceAdapter,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 7, 23, 0, tzinfo=UTC)
_OPENED_AT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=15)
_INSTRUMENT = Instrument("EURUSD")
_TIMEFRAME = Timeframe(900)
_MARKET_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("d1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("d1000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.reference"),
)
_PERSISTENCE_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("d1000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("d1000000-0000-0000-0000-000000000004")),
    port_name=PortName("persistence.reference"),
)
_CORRELATION = CorrelationId(UUID("d1000000-0000-0000-0000-000000000005"))
_CAUSATION = CausationId(UUID("d1000000-0000-0000-0000-000000000006"))
_KEY = PersistenceKey("specialized.statistics", "snapshot/reference")
_VERSION_ZERO = PersistenceVersion(0)


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _quote() -> QuoteSnapshot:
    return QuoteSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID("d1000000-0000-0000-0000-000000000010")
        ),
        instrument=_INSTRUMENT,
        source=_MARKET_DESCRIPTOR,
        observed_at=_NOW,
        bid=1.16,
        ask=1.1602,
    )


def _ohlc() -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID("d1000000-0000-0000-0000-000000000011")
        ),
        instrument=_INSTRUMENT,
        source=_MARKET_DESCRIPTOR,
        timeframe=_TIMEFRAME,
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
        open=1.155,
        high=1.165,
        low=1.15,
        close=1.16,
    )


def _save_request(
    value: dict[str, list[int]],
    *,
    version: PersistenceVersion = _VERSION_ZERO,
    expected_version: PersistenceVersion | None = None,
) -> SavePersistenceRequest[dict[str, list[int]]]:
    return SavePersistenceRequest(
        key=_KEY,
        version=version,
        value=value,
        stored_at=_NOW,
        expected_version=expected_version,
    )


class _Uncopyable:
    def __deepcopy__(self, memo: object) -> object:
        del memo
        raise RuntimeError("copy disabled")


def test_reference_market_data_adapter_is_structural_and_deterministic() -> None:
    quote = _quote()
    ohlc = _ohlc()
    adapter = ReferenceMarketDataAdapter(
        _MARKET_DESCRIPTOR,
        quotes=(quote,),
        ohlc=(ohlc,),
    )
    port: MarketDataPort = adapter

    quote_result = port.read_quote(QuoteRequest(_INSTRUMENT), metadata=_metadata())
    ohlc_result = port.read_ohlc(
        OhlcRequest(
            instrument=_INSTRUMENT,
            timeframe=_TIMEFRAME,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
        ),
        metadata=_metadata(),
    )
    health_result = port.health(checked_at=_NOW, metadata=_metadata())

    assert isinstance(quote_result, Success)
    assert quote_result.value is quote
    assert isinstance(ohlc_result, Success)
    assert ohlc_result.value is ohlc
    assert isinstance(health_result, Success)
    assert health_result.value.descriptor is _MARKET_DESCRIPTOR
    assert health_result.value.checked_at is _NOW
    assert health_result.value.availability is PortAvailability.AVAILABLE


def test_reference_market_data_adapter_returns_typed_missing_data_failure() -> None:
    adapter = ReferenceMarketDataAdapter(_MARKET_DESCRIPTOR)

    result = adapter.read_quote(QuoteRequest(_INSTRUMENT), metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReferenceDataNotFoundError)


def test_reference_market_data_adapter_rejects_invalid_configuration() -> None:
    wrong_descriptor = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("d1000000-0000-0000-0000-000000000020")),
        source_id=SourceId(UUID("d1000000-0000-0000-0000-000000000021")),
        port_name=PortName("persistence.reference"),
    )
    with pytest.raises(ReferenceAdapterValidationError, match="market-data namespace"):
        ReferenceMarketDataAdapter(wrong_descriptor)

    with pytest.raises(ReferenceAdapterValidationError, match="at most one"):
        ReferenceMarketDataAdapter(
            _MARKET_DESCRIPTOR,
            quotes=(_quote(), _quote()),
        )

    with pytest.raises(ReferenceAdapterValidationError, match="source must match"):
        other_source = ExternalSourceDescriptor(
            adapter_id=AdapterId(UUID("d1000000-0000-0000-0000-000000000022")),
            source_id=SourceId(UUID("d1000000-0000-0000-0000-000000000023")),
            port_name=PortName("market-data.other"),
        )
        ReferenceMarketDataAdapter(
            _MARKET_DESCRIPTOR,
            quotes=(
                QuoteSnapshot(
                    snapshot_id=MarketDataSnapshotId(
                        UUID("d1000000-0000-0000-0000-000000000024")
                    ),
                    instrument=_INSTRUMENT,
                    source=other_source,
                    observed_at=_NOW,
                    bid=1.0,
                    ask=1.1,
                ),
            ),
        )


def test_reference_market_data_adapters_are_isolated_by_instance() -> None:
    populated = ReferenceMarketDataAdapter(_MARKET_DESCRIPTOR, quotes=(_quote(),))
    empty = ReferenceMarketDataAdapter(_MARKET_DESCRIPTOR)

    populated_result = populated.read_quote(
        QuoteRequest(_INSTRUMENT),
        metadata=_metadata(),
    )
    empty_result = empty.read_quote(QuoteRequest(_INSTRUMENT), metadata=_metadata())

    assert isinstance(populated_result, Success)
    assert isinstance(empty_result, Failure)
    assert isinstance(empty_result.error, ReferenceDataNotFoundError)


def test_reference_market_data_adapter_rejects_runtime_request_bypass() -> None:
    adapter = ReferenceMarketDataAdapter(_MARKET_DESCRIPTOR, quotes=(_quote(),))

    result = adapter.read_quote(
        cast(QuoteRequest, object()),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReferenceAdapterValidationError)


def test_reference_persistence_adapter_is_structural_and_defensively_copies() -> None:
    adapter: ReferencePersistenceAdapter[dict[str, list[int]]] = (
        ReferencePersistenceAdapter(_PERSISTENCE_DESCRIPTOR)
    )
    port: PersistencePort[dict[str, list[int]]] = adapter
    original = {"values": [1]}

    saved = port.save(_save_request(original), metadata=_metadata())
    assert isinstance(saved, Success)
    assert saved.value.source is _PERSISTENCE_DESCRIPTOR
    assert saved.value.stored_at is _NOW

    original["values"].append(2)
    saved.value.value["values"].append(3)

    loaded = port.load(LoadPersistenceRequest(_KEY), metadata=_metadata())
    assert isinstance(loaded, Success)
    assert loaded.value is not None
    assert loaded.value.value == {"values": [1]}

    loaded.value.value["values"].append(4)
    loaded_again = port.load(LoadPersistenceRequest(_KEY), metadata=_metadata())
    assert isinstance(loaded_again, Success)
    assert loaded_again.value is not None
    assert loaded_again.value.value == {"values": [1]}


def test_reference_persistence_adapter_handles_absence_and_conflicts() -> None:
    adapter: ReferencePersistenceAdapter[dict[str, list[int]]] = (
        ReferencePersistenceAdapter(_PERSISTENCE_DESCRIPTOR)
    )

    absent = adapter.load(LoadPersistenceRequest(_KEY), metadata=_metadata())
    assert isinstance(absent, Success)
    assert absent.value is None

    created = adapter.save(_save_request({"values": [1]}), metadata=_metadata())
    duplicate = adapter.save(_save_request({"values": [2]}), metadata=_metadata())
    updated = adapter.save(
        _save_request(
            {"values": [3]},
            version=PersistenceVersion(1),
            expected_version=PersistenceVersion(0),
        ),
        metadata=_metadata(),
    )
    stale = adapter.save(
        _save_request(
            {"values": [4]},
            version=PersistenceVersion(1),
            expected_version=PersistenceVersion(0),
        ),
        metadata=_metadata(),
    )

    assert isinstance(created, Success)
    assert isinstance(duplicate, Failure)
    assert isinstance(duplicate.error, PersistenceConflictError)
    assert isinstance(updated, Success)
    assert updated.value.version == PersistenceVersion(1)
    assert isinstance(stale, Failure)
    assert isinstance(stale.error, PersistenceConflictError)


def test_reference_persistence_adapters_are_isolated_by_instance() -> None:
    first: ReferencePersistenceAdapter[dict[str, list[int]]] = (
        ReferencePersistenceAdapter(_PERSISTENCE_DESCRIPTOR)
    )
    second: ReferencePersistenceAdapter[dict[str, list[int]]] = (
        ReferencePersistenceAdapter(_PERSISTENCE_DESCRIPTOR)
    )

    assert isinstance(first.save(_save_request({"values": [1]}), metadata=_metadata()), Success)
    second_result = second.load(LoadPersistenceRequest(_KEY), metadata=_metadata())

    assert isinstance(second_result, Success)
    assert second_result.value is None


def test_reference_persistence_adapter_normalizes_copy_failures() -> None:
    adapter: ReferencePersistenceAdapter[_Uncopyable] = ReferencePersistenceAdapter(
        _PERSISTENCE_DESCRIPTOR
    )
    request = SavePersistenceRequest(
        key=_KEY,
        version=PersistenceVersion(0),
        value=_Uncopyable(),
        stored_at=_NOW,
    )

    result = adapter.save(request, metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReferenceAdapterCopyError)


def test_reference_persistence_health_uses_only_explicit_time_and_descriptor() -> None:
    adapter: ReferencePersistenceAdapter[str] = ReferencePersistenceAdapter(
        _PERSISTENCE_DESCRIPTOR
    )

    result = adapter.health(checked_at=_NOW, metadata=_metadata())

    assert isinstance(result, Success)
    assert result.value.descriptor is _PERSISTENCE_DESCRIPTOR
    assert result.value.checked_at is _NOW
    assert result.value.availability is PortAvailability.AVAILABLE
