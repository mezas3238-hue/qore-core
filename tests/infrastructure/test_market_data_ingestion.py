from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.ingestion import (
    ExternalDecimalValue,
    ExternalMarketDataPayloadPort,
    ExternalOhlcPayload,
    ExternalQuotePayload,
    ExternalWholeNumberValue,
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
    PortUnavailableError,
    SourceId,
)
from qore.kernel.result import Failure, Result, Success

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("d1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("d1000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.raw-reference"),
)
_OTHER_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("d1000000-0000-0000-0000-000000000011")),
    source_id=SourceId(UUID("d1000000-0000-0000-0000-000000000012")),
    port_name=PortName("market-data.other-reference"),
)
_PERSISTENCE_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("d1000000-0000-0000-0000-000000000021")),
    source_id=SourceId(UUID("d1000000-0000-0000-0000-000000000022")),
    port_name=PortName("persistence.reference"),
)
_CORRELATION = CorrelationId(UUID("d1000000-0000-0000-0000-000000000003"))
_CAUSATION = CausationId(UUID("d1000000-0000-0000-0000-000000000004"))
_QUOTE_ID = MarketDataSnapshotId(UUID("d1000000-0000-0000-0000-000000000005"))
_OHLC_ID = MarketDataSnapshotId(UUID("d1000000-0000-0000-0000-000000000006"))
_INSTRUMENT = Instrument("EURUSD")
_TIMEFRAME = Timeframe(900)
_OBSERVED_AT = datetime(2026, 8, 7, 13, 30, tzinfo=UTC)
_OPENED_AT = datetime(2026, 8, 7, 13, 15, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(seconds=_TIMEFRAME.seconds)


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _quote_request() -> QuoteRequest:
    return QuoteRequest(instrument=_INSTRUMENT)


def _ohlc_request() -> OhlcRequest:
    return OhlcRequest(
        instrument=_INSTRUMENT,
        timeframe=_TIMEFRAME,
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
    )


def _quote_payload(
    *,
    source: ExternalSourceDescriptor = _SOURCE,
    instrument: str = " eurusd ",
    observed_at: datetime = _OBSERVED_AT,
    bid: ExternalDecimalValue = "1.1000",
    ask: ExternalDecimalValue = 1.1002,
) -> ExternalQuotePayload:
    return ExternalQuotePayload(
        source=source,
        instrument=instrument,
        observed_at=observed_at,
        bid=bid,
        ask=ask,
    )


def _ohlc_payload(
    *,
    source: ExternalSourceDescriptor = _SOURCE,
    instrument: str = "EURUSD",
    timeframe_seconds: ExternalWholeNumberValue = "900",
    opened_at: datetime = _OPENED_AT,
    closed_at: datetime = _CLOSED_AT,
    open_: ExternalDecimalValue = "1.1000",
    high: ExternalDecimalValue = "1.1010",
    low: ExternalDecimalValue = "1.0990",
    close: ExternalDecimalValue = 1.1005,
) -> ExternalOhlcPayload:
    return ExternalOhlcPayload(
        source=source,
        instrument=instrument,
        timeframe_seconds=timeframe_seconds,
        opened_at=opened_at,
        closed_at=closed_at,
        open=open_,
        high=high,
        low=low,
        close=close,
    )


class ScriptedPayloadPort:
    def __init__(
        self,
        *,
        descriptor: ExternalSourceDescriptor = _SOURCE,
        quote_result: Result[ExternalQuotePayload, ExternalPortError] | None = None,
        ohlc_result: Result[ExternalOhlcPayload, ExternalPortError] | None = None,
    ) -> None:
        self._descriptor = descriptor
        self._quote_result = quote_result if quote_result is not None else Success(_quote_payload())
        self._ohlc_result = ohlc_result if ohlc_result is not None else Success(_ohlc_payload())

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
        return self._quote_result

    def read_external_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        del request, metadata
        return self._ohlc_result


class BadResultPayloadPort(ScriptedPayloadPort):
    def __init__(
        self,
        *,
        quote_result: object = Success(object()),
        ohlc_result: object = Success(object()),
    ) -> None:
        super().__init__()
        self._bad_quote_result = quote_result
        self._bad_ohlc_result = ohlc_result

    def read_external_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        del request, metadata
        return cast(Result[ExternalQuotePayload, ExternalPortError], self._bad_quote_result)

    def read_external_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        del request, metadata
        return cast(Result[ExternalOhlcPayload, ExternalPortError], self._bad_ohlc_result)


def test_ingestion_flow_accepts_structural_payload_port() -> None:
    port: ExternalMarketDataPayloadPort = ScriptedPayloadPort()
    flow = MarketDataIngestionFlow(port)

    assert flow.port is port
    assert flow.descriptor is _SOURCE


def test_ingest_quote_normalizes_provider_payload_into_canonical_snapshot() -> None:
    flow = MarketDataIngestionFlow(ScriptedPayloadPort())

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.snapshot_id is _QUOTE_ID
    assert snapshot.instrument == _INSTRUMENT
    assert snapshot.source is _SOURCE
    assert snapshot.observed_at is _OBSERVED_AT
    assert snapshot.bid == 1.1
    assert snapshot.ask == 1.1002


def test_ingest_ohlc_normalizes_provider_payload_into_canonical_snapshot() -> None:
    flow = MarketDataIngestionFlow(ScriptedPayloadPort())

    result = flow.ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.snapshot_id is _OHLC_ID
    assert snapshot.instrument == _INSTRUMENT
    assert snapshot.source is _SOURCE
    assert snapshot.timeframe == _TIMEFRAME
    assert snapshot.opened_at is _OPENED_AT
    assert snapshot.closed_at is _CLOSED_AT
    assert snapshot.open == 1.1
    assert snapshot.high == 1.101
    assert snapshot.low == 1.099
    assert snapshot.close == 1.1005


def test_ingestion_propagates_payload_port_failure() -> None:
    error = PortUnavailableError("payload source unavailable")
    flow = MarketDataIngestionFlow(
        ScriptedPayloadPort(quote_result=Failure(error))
    )

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert result.error is error


def test_ingestion_rejects_invalid_result_object_from_runtime_bypass() -> None:
    flow = MarketDataIngestionFlow(BadResultPayloadPort(quote_result=object()))

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "must return Result" in str(result.error)


def test_ingestion_rejects_invalid_payload_type_from_runtime_bypass() -> None:
    flow = MarketDataIngestionFlow(BadResultPayloadPort(quote_result=Success(object())))

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "ExternalQuotePayload" in str(result.error)


def test_ingestion_rejects_payload_source_that_does_not_match_port() -> None:
    flow = MarketDataIngestionFlow(
        ScriptedPayloadPort(quote_result=Success(_quote_payload(source=_OTHER_SOURCE)))
    )

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "source" in str(result.error)


def test_ingestion_rejects_non_market_data_payload_port_descriptor() -> None:
    with pytest.raises(IngestionValidationError, match="market-data namespace"):
        MarketDataIngestionFlow(ScriptedPayloadPort(descriptor=_PERSISTENCE_SOURCE))


def test_ingestion_rejects_quote_payload_for_another_instrument() -> None:
    flow = MarketDataIngestionFlow(
        ScriptedPayloadPort(quote_result=Success(_quote_payload(instrument="GBPUSD")))
    )

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "instrument" in str(result.error)


def test_ingestion_rejects_decimal_bool_runtime_bypass() -> None:
    flow = MarketDataIngestionFlow(
        ScriptedPayloadPort(
            quote_result=Success(_quote_payload(bid=cast(ExternalDecimalValue, True)))
        )
    )

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "decimal string or float" in str(result.error)


def test_ingestion_rejects_non_finite_decimal_string() -> None:
    flow = MarketDataIngestionFlow(
        ScriptedPayloadPort(quote_result=Success(_quote_payload(ask="nan")))
    )

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "positive finite" in str(result.error)


def test_ingestion_rejects_ohlc_timeframe_mismatch() -> None:
    flow = MarketDataIngestionFlow(
        ScriptedPayloadPort(
            ohlc_result=Success(_ohlc_payload(timeframe_seconds="300"))
        )
    )

    result = flow.ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "timeframe" in str(result.error)


def test_ingestion_rejects_ohlc_interval_mismatch() -> None:
    flow = MarketDataIngestionFlow(
        ScriptedPayloadPort(
            ohlc_result=Success(
                _ohlc_payload(closed_at=_CLOSED_AT + timedelta(seconds=1))
            )
        )
    )

    result = flow.ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "interval" in str(result.error)


def test_ingestion_propagates_canonical_snapshot_construction_failure() -> None:
    flow = MarketDataIngestionFlow(
        ScriptedPayloadPort(
            ohlc_result=Success(_ohlc_payload(open_="1.2000"))
        )
    )

    result = flow.ingest_ohlc(
        _ohlc_request(),
        snapshot_id=_OHLC_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "canonical snapshot" in str(result.error)


def test_ingestion_rejects_runtime_metadata_bypass() -> None:
    flow = MarketDataIngestionFlow(ScriptedPayloadPort())

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=_QUOTE_ID,
        metadata=cast(ExternalRequestMetadata, object()),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "metadata" in str(result.error)


def test_ingestion_rejects_runtime_snapshot_id_bypass() -> None:
    flow = MarketDataIngestionFlow(ScriptedPayloadPort())

    result = flow.ingest_quote(
        _quote_request(),
        snapshot_id=cast(MarketDataSnapshotId, UUID("d1000000-0000-0000-0000-000000000099")),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "snapshot_id" in str(result.error)
