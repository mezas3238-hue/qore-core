from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.ingestion import (
    ExternalMarketDataPayloadPort,
    ExternalOhlcPayload,
    ExternalQuotePayload,
    IngestionValidationError,
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
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure, Result, Success

_OBSERVED_AT = datetime(2026, 8, 7, 23, 20, tzinfo=UTC)
_OPENED_AT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=15)
_INSTRUMENT = Instrument("EURUSD")
_TIMEFRAME = Timeframe(900)
_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("e1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("e1000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.external-reference"),
)
_OTHER_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("e1000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("e1000000-0000-0000-0000-000000000004")),
    port_name=PortName("market-data.other"),
)
_CORRELATION = CorrelationId(UUID("e1000000-0000-0000-0000-000000000005"))
_CAUSATION = CausationId(UUID("e1000000-0000-0000-0000-000000000006"))
_QUOTE_ID = MarketDataSnapshotId(UUID("e1000000-0000-0000-0000-000000000010"))
_OHLC_ID = MarketDataSnapshotId(UUID("e1000000-0000-0000-0000-000000000011"))


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _quote_payload(
    *,
    source: ExternalSourceDescriptor = _DESCRIPTOR,
    instrument: str = " eurusd ",
    bid: str | float = "1.1600",
    ask: str | float = "1.1602",
) -> ExternalQuotePayload:
    return ExternalQuotePayload(
        source=source,
        instrument=instrument,
        observed_at=_OBSERVED_AT,
        bid=bid,
        ask=ask,
    )


def _ohlc_payload(
    *,
    source: ExternalSourceDescriptor = _DESCRIPTOR,
    instrument: str = "eurusd",
    timeframe_seconds: str | int = "900",
    opened_at: datetime = _OPENED_AT,
    closed_at: datetime = _CLOSED_AT,
    open_price: str | float = "1.1550",
    high: str | float = "1.1650",
    low: str | float = "1.1500",
    close: str | float = "1.1600",
) -> ExternalOhlcPayload:
    return ExternalOhlcPayload(
        source=source,
        instrument=instrument,
        timeframe_seconds=timeframe_seconds,
        opened_at=opened_at,
        closed_at=closed_at,
        open=open_price,
        high=high,
        low=low,
        close=close,
    )


class _PayloadPortFailure(ExternalPortError):
    __slots__ = ()


class _FakePayloadPort:
    def __init__(
        self,
        *,
        descriptor: ExternalSourceDescriptor = _DESCRIPTOR,
        quote: ExternalQuotePayload | None = None,
        ohlc: ExternalOhlcPayload | None = None,
        failure: ExternalPortError | None = None,
    ) -> None:
        self._descriptor = descriptor
        self.quote = quote if quote is not None else _quote_payload()
        self.ohlc = ohlc if ohlc is not None else _ohlc_payload()
        self.failure = failure

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
        return Success(
            ExternalHealth(
                descriptor=self.descriptor,
                availability=PortAvailability.AVAILABLE,
                checked_at=checked_at,
            )
        )

    def read_external_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        del request, metadata
        if self.failure is not None:
            return Failure(self.failure)
        return Success(self.quote)

    def read_external_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        del request, metadata
        if self.failure is not None:
            return Failure(self.failure)
        return Success(self.ohlc)


def _quote_request() -> QuoteRequest:
    return QuoteRequest(_INSTRUMENT)


def _ohlc_request() -> OhlcRequest:
    return OhlcRequest(
        instrument=_INSTRUMENT,
        timeframe=_TIMEFRAME,
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
    )


def test_ingestion_port_is_structural_and_quote_normalization_is_deterministic() -> None:
    fake = _FakePayloadPort()
    port: ExternalMarketDataPayloadPort = fake
    flow = MarketDataIngestionFlow(port)

    first = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )
    second = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value == second.value
    assert first.value.snapshot_id is _QUOTE_ID
    assert first.value.instrument == _INSTRUMENT
    assert first.value.source is _DESCRIPTOR
    assert first.value.observed_at is _OBSERVED_AT
    assert first.value.bid == 1.16
    assert first.value.ask == 1.1602


def test_ingestion_normalizes_external_ohlc_into_the_canonical_contract() -> None:
    flow = MarketDataIngestionFlow(_FakePayloadPort())

    result = flow.ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.snapshot_id is _OHLC_ID
    assert result.value.instrument == _INSTRUMENT
    assert result.value.source is _DESCRIPTOR
    assert result.value.timeframe == _TIMEFRAME
    assert result.value.opened_at is _OPENED_AT
    assert result.value.closed_at is _CLOSED_AT
    assert result.value.open == 1.155
    assert result.value.high == 1.165
    assert result.value.low == 1.15
    assert result.value.close == 1.16


def test_ingestion_propagates_port_failure_without_rewrapping() -> None:
    error = _PayloadPortFailure("external read failed")
    flow = MarketDataIngestionFlow(_FakePayloadPort(failure=error))

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert result.error is error


def test_ingestion_rejects_payload_source_that_does_not_match_port_descriptor() -> None:
    flow = MarketDataIngestionFlow(
        _FakePayloadPort(quote=_quote_payload(source=_OTHER_DESCRIPTOR))
    )

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "source must match" in str(result.error)


def test_ingestion_rejects_payload_instrument_mismatch_after_normalization() -> None:
    flow = MarketDataIngestionFlow(
        _FakePayloadPort(quote=_quote_payload(instrument=" gbpusd "))
    )

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "requested instrument" in str(result.error)


def test_ingestion_rejects_invalid_external_price_and_canonical_quote_order() -> None:
    invalid_decimal = MarketDataIngestionFlow(
        _FakePayloadPort(quote=_quote_payload(bid="not-a-price"))
    ).ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )
    crossed_quote = MarketDataIngestionFlow(
        _FakePayloadPort(quote=_quote_payload(bid="1.20", ask="1.10"))
    ).ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(invalid_decimal, Failure)
    assert isinstance(invalid_decimal.error, IngestionValidationError)
    assert isinstance(crossed_quote, Failure)
    assert isinstance(crossed_quote.error, IngestionValidationError)
    assert "canonical snapshot" in str(crossed_quote.error)


def test_ingestion_rejects_non_finite_and_boolean_external_prices() -> None:
    non_finite = MarketDataIngestionFlow(
        _FakePayloadPort(quote=_quote_payload(bid="NaN"))
    ).ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )
    boolean_price = MarketDataIngestionFlow(
        _FakePayloadPort(
            quote=ExternalQuotePayload(
                source=_DESCRIPTOR,
                instrument="EURUSD",
                observed_at=_OBSERVED_AT,
                bid=cast(str | float, True),
                ask="1.1602",
            )
        )
    ).ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(non_finite, Failure)
    assert isinstance(non_finite.error, IngestionValidationError)
    assert isinstance(boolean_price, Failure)
    assert isinstance(boolean_price.error, IngestionValidationError)


def test_ingestion_rejects_ohlc_timeframe_and_interval_mismatch() -> None:
    timeframe_mismatch = MarketDataIngestionFlow(
        _FakePayloadPort(ohlc=_ohlc_payload(timeframe_seconds="300"))
    ).ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )
    interval_mismatch = MarketDataIngestionFlow(
        _FakePayloadPort(
            ohlc=_ohlc_payload(
                opened_at=_OPENED_AT + timedelta(minutes=15),
                closed_at=_CLOSED_AT + timedelta(minutes=15),
            )
        )
    ).ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )

    assert isinstance(timeframe_mismatch, Failure)
    assert isinstance(timeframe_mismatch.error, IngestionValidationError)
    assert isinstance(interval_mismatch, Failure)
    assert isinstance(interval_mismatch.error, IngestionValidationError)


def test_ingestion_rejects_ohlc_values_that_violate_canonical_invariants() -> None:
    flow = MarketDataIngestionFlow(
        _FakePayloadPort(ohlc=_ohlc_payload(high="1.10", low="1.20"))
    )

    result = flow.ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "canonical snapshot" in str(result.error)


def test_ingestion_rejects_runtime_metadata_and_identity_bypasses() -> None:
    flow = MarketDataIngestionFlow(_FakePayloadPort())

    bad_metadata = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=cast(ExternalRequestMetadata, object()),
    )
    bad_snapshot_id = flow.ingest_quote(
        _quote_request(),
        snapshot_id=cast(MarketDataSnapshotId, object()),
        metadata=_metadata(),
    )

    assert isinstance(bad_metadata, Failure)
    assert isinstance(bad_metadata.error, IngestionValidationError)
    assert isinstance(bad_snapshot_id, Failure)
    assert isinstance(bad_snapshot_id.error, IngestionValidationError)


def test_ingestion_uses_only_the_explicit_snapshot_identity_and_payload_time() -> None:
    flow = MarketDataIngestionFlow(_FakePayloadPort())

    quote = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )
    ohlc = flow.ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )

    assert isinstance(quote, Success)
    assert quote.value.snapshot_id is _QUOTE_ID
    assert quote.value.observed_at is _OBSERVED_AT
    assert isinstance(ohlc, Success)
    assert ohlc.value.snapshot_id is _OHLC_ID
    assert ohlc.value.opened_at is _OPENED_AT
    assert ohlc.value.closed_at is _CLOSED_AT
