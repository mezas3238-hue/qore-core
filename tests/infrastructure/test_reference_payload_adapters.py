from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.ingestion import (
    ExternalMarketDataPayloadPort,
    ExternalOhlcPayload,
    ExternalQuotePayload,
    MarketDataIngestionFlow,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcRequest,
    QuoteRequest,
    Timeframe,
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
    ReferenceAdapterValidationError,
    ReferenceDataNotFoundError,
)
from qore.infrastructure.reference_payload_adapters import (
    ReferenceExternalMarketDataPayloadAdapter,
)
from qore.kernel.result import Failure, Success

_OBSERVED_AT = datetime(2026, 8, 7, 23, 45, tzinfo=UTC)
_OPENED_AT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=15)
_INSTRUMENT = Instrument("EURUSD")
_TIMEFRAME = Timeframe(900)
_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("e2000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("e2000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.external-reference"),
)
_OTHER_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("e2000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("e2000000-0000-0000-0000-000000000004")),
    port_name=PortName("market-data.other"),
)
_CORRELATION = CorrelationId(UUID("e2000000-0000-0000-0000-000000000005"))
_CAUSATION = CausationId(UUID("e2000000-0000-0000-0000-000000000006"))
_QUOTE_ID = MarketDataSnapshotId(UUID("e2000000-0000-0000-0000-000000000010"))
_OHLC_ID = MarketDataSnapshotId(UUID("e2000000-0000-0000-0000-000000000011"))


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _quote_payload() -> ExternalQuotePayload:
    return ExternalQuotePayload(
        source=_DESCRIPTOR,
        instrument=" eurusd ",
        observed_at=_OBSERVED_AT,
        bid="1.1600",
        ask="1.1602",
    )


def _ohlc_payload() -> ExternalOhlcPayload:
    return ExternalOhlcPayload(
        source=_DESCRIPTOR,
        instrument="eurusd",
        timeframe_seconds="900",
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
        open="1.1550",
        high="1.1650",
        low="1.1500",
        close="1.1600",
    )


def _ohlc_request() -> OhlcRequest:
    return OhlcRequest(
        instrument=_INSTRUMENT,
        timeframe=_TIMEFRAME,
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
    )


def test_reference_payload_adapter_is_structural_and_end_to_end_normalizes_quote() -> None:
    adapter = ReferenceExternalMarketDataPayloadAdapter(
        _DESCRIPTOR,
        quotes=(_quote_payload(),),
    )
    port: ExternalMarketDataPayloadPort = adapter
    flow = MarketDataIngestionFlow(port)

    result = flow.ingest_quote(
        QuoteRequest(_INSTRUMENT),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.snapshot_id is _QUOTE_ID
    assert result.value.source is _DESCRIPTOR
    assert result.value.instrument == _INSTRUMENT
    assert result.value.observed_at is _OBSERVED_AT
    assert result.value.bid == 1.16
    assert result.value.ask == 1.1602


def test_reference_payload_adapter_end_to_end_normalizes_ohlc() -> None:
    adapter = ReferenceExternalMarketDataPayloadAdapter(
        _DESCRIPTOR,
        ohlc=(_ohlc_payload(),),
    )
    flow = MarketDataIngestionFlow(adapter)

    result = flow.ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.snapshot_id is _OHLC_ID
    assert result.value.source is _DESCRIPTOR
    assert result.value.instrument == _INSTRUMENT
    assert result.value.timeframe == _TIMEFRAME
    assert result.value.opened_at is _OPENED_AT
    assert result.value.closed_at is _CLOSED_AT
    assert result.value.open == 1.155
    assert result.value.high == 1.165
    assert result.value.low == 1.15
    assert result.value.close == 1.16


def test_reference_payload_adapter_absence_is_typed_failure() -> None:
    adapter = ReferenceExternalMarketDataPayloadAdapter(_DESCRIPTOR)

    quote = adapter.read_external_quote(
        QuoteRequest(_INSTRUMENT),
        metadata=_metadata(),
    )
    ohlc = adapter.read_external_ohlc(_ohlc_request(), metadata=_metadata())

    assert isinstance(quote, Failure)
    assert isinstance(quote.error, ReferenceDataNotFoundError)
    assert isinstance(ohlc, Failure)
    assert isinstance(ohlc.error, ReferenceDataNotFoundError)


def test_reference_payload_adapters_are_isolated_by_instance() -> None:
    populated = ReferenceExternalMarketDataPayloadAdapter(
        _DESCRIPTOR,
        quotes=(_quote_payload(),),
    )
    empty = ReferenceExternalMarketDataPayloadAdapter(_DESCRIPTOR)

    populated_result = populated.read_external_quote(
        QuoteRequest(_INSTRUMENT),
        metadata=_metadata(),
    )
    empty_result = empty.read_external_quote(
        QuoteRequest(_INSTRUMENT),
        metadata=_metadata(),
    )

    assert isinstance(populated_result, Success)
    assert isinstance(empty_result, Failure)
    assert isinstance(empty_result.error, ReferenceDataNotFoundError)


def test_reference_payload_adapter_rejects_inconsistent_configuration() -> None:
    wrong_namespace = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("e2000000-0000-0000-0000-000000000020")),
        source_id=SourceId(UUID("e2000000-0000-0000-0000-000000000021")),
        port_name=PortName("persistence.reference"),
    )
    with pytest.raises(ReferenceAdapterValidationError, match="market-data namespace"):
        ReferenceExternalMarketDataPayloadAdapter(wrong_namespace)

    wrong_source_payload = ExternalQuotePayload(
        source=_OTHER_DESCRIPTOR,
        instrument="EURUSD",
        observed_at=_OBSERVED_AT,
        bid="1.0",
        ask="1.1",
    )
    with pytest.raises(ReferenceAdapterValidationError, match="source must match"):
        ReferenceExternalMarketDataPayloadAdapter(
            _DESCRIPTOR,
            quotes=(wrong_source_payload,),
        )

    with pytest.raises(ReferenceAdapterValidationError, match="at most one"):
        ReferenceExternalMarketDataPayloadAdapter(
            _DESCRIPTOR,
            quotes=(_quote_payload(), _quote_payload()),
        )


def test_reference_payload_adapter_validates_metadata_at_runtime() -> None:
    adapter = ReferenceExternalMarketDataPayloadAdapter(
        _DESCRIPTOR,
        quotes=(_quote_payload(),),
    )

    result = adapter.read_external_quote(
        QuoteRequest(_INSTRUMENT),
        metadata=cast(ExternalRequestMetadata, object()),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReferenceAdapterValidationError)


def test_reference_payload_adapter_health_uses_only_explicit_time() -> None:
    adapter = ReferenceExternalMarketDataPayloadAdapter(_DESCRIPTOR)

    result = adapter.health(checked_at=_OBSERVED_AT, metadata=_metadata())

    assert isinstance(result, Success)
    assert result.value.descriptor is _DESCRIPTOR
    assert result.value.checked_at is _OBSERVED_AT
    assert result.value.availability is PortAvailability.AVAILABLE
