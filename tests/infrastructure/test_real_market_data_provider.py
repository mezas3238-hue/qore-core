from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ingestion import (
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
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
from qore.infrastructure.real_market_data_provider import (
    ConcreteJsonMarketDataDecoder,
    ConcreteJsonMarketDataRequestFactory,
    RealMarketDataProviderValidationError,
)
from qore.infrastructure.transport import (
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 10, 30, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("22000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("22000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.real-test"),
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("22000000-0000-0000-0000-000000000003"))
)


class _PayloadPort:
    def __init__(
        self,
        quote: ExternalQuotePayload,
        ohlc: ExternalOhlcPayload,
    ) -> None:
        self._quote = quote
        self._ohlc = ohlc

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return _SOURCE

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        return Success(
            ExternalHealth(
                descriptor=_SOURCE,
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
        return Success(self._quote)

    def read_external_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        del request, metadata
        return Success(self._ohlc)


def _quote_request() -> QuoteRequest:
    return QuoteRequest(Instrument("EURUSD"))


def _ohlc_request() -> OhlcRequest:
    return OhlcRequest(
        instrument=Instrument("EURUSD"),
        timeframe=Timeframe(900),
        opened_at=_NOW - timedelta(minutes=15),
        closed_at=_NOW,
    )


def test_request_factory_builds_stable_read_only_queries() -> None:
    factory = ConcreteJsonMarketDataRequestFactory(
        endpoint=ProviderEndpoint("data.example.test", base_path="/v1"),
        timeout=ExternalTransportTimeout(1500),
    )

    quote = factory.quote_request(_quote_request())
    ohlc = factory.ohlc_request(_ohlc_request())

    assert quote.path == "/quote"
    assert quote.query == (("instrument", "EURUSD"),)
    assert tuple(key for key, _ in ohlc.query) == (
        "closed_at",
        "instrument",
        "opened_at",
        "timeframe_seconds",
    )
    assert ohlc.query[-1] == ("timeframe_seconds", "900")


def test_json_quote_decoder_feeds_existing_canonical_ingestion() -> None:
    decoder = ConcreteJsonMarketDataDecoder()
    quote_result = decoder.decode_quote(
        ExternalTransportResponse(
            status_code=200,
            received_at=_NOW,
            payload=(
                b'{"instrument":"EURUSD","observed_at":"2026-08-08T10:30:00+00:00",'
                b'"bid":"1.1000","ask":"1.1002"}'
            ),
        ),
        source=_SOURCE,
        request=_quote_request(),
    )
    assert isinstance(quote_result, Success)

    ohlc = ExternalOhlcPayload(
        source=_SOURCE,
        instrument="EURUSD",
        timeframe_seconds=900,
        opened_at=_NOW - timedelta(minutes=15),
        closed_at=_NOW,
        open="1.1000",
        high="1.1010",
        low="1.0990",
        close="1.1005",
    )
    flow = MarketDataIngestionFlow(_PayloadPort(quote_result.value, ohlc))
    snapshot = flow.ingest_quote(
        _quote_request(),
        snapshot_id=MarketDataSnapshotId(
            UUID("22000000-0000-0000-0000-000000000004")
        ),
        metadata=_METADATA,
    )

    assert isinstance(snapshot, Success)
    assert snapshot.value.instrument.symbol == "EURUSD"
    assert snapshot.value.bid == 1.1
    assert snapshot.value.ask == 1.1002


def test_json_ohlc_decoder_feeds_existing_canonical_ingestion() -> None:
    request = _ohlc_request()
    decoder = ConcreteJsonMarketDataDecoder()
    ohlc_result = decoder.decode_ohlc(
        ExternalTransportResponse(
            status_code=200,
            received_at=_NOW,
            payload=(
                b'{"instrument":"EURUSD","timeframe_seconds":900,'
                b'"opened_at":"2026-08-08T10:15:00+00:00",'
                b'"closed_at":"2026-08-08T10:30:00+00:00",'
                b'"open":1.1000,"high":1.1010,"low":1.0990,"close":1.1005}'
            ),
        ),
        source=_SOURCE,
        request=request,
    )
    assert isinstance(ohlc_result, Success)

    quote = ExternalQuotePayload(
        source=_SOURCE,
        instrument="EURUSD",
        observed_at=_NOW,
        bid="1.1000",
        ask="1.1002",
    )
    flow = MarketDataIngestionFlow(_PayloadPort(quote, ohlc_result.value))
    snapshot = flow.ingest_ohlc(
        request,
        snapshot_id=MarketDataSnapshotId(
            UUID("22000000-0000-0000-0000-000000000005")
        ),
        metadata=_METADATA,
    )

    assert isinstance(snapshot, Success)
    assert snapshot.value.timeframe.seconds == 900
    assert snapshot.value.close == 1.1005


def test_decoder_rejects_naive_provider_timestamp() -> None:
    result = ConcreteJsonMarketDataDecoder().decode_quote(
        ExternalTransportResponse(
            status_code=200,
            received_at=_NOW,
            payload=(
                b'{"instrument":"EURUSD","observed_at":"2026-08-08T10:30:00",'
                b'"bid":"1.1000","ask":"1.1002"}'
            ),
        ),
        source=_SOURCE,
        request=_quote_request(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, RealMarketDataProviderValidationError)


def test_decoder_rejects_non_json_payload() -> None:
    result = ConcreteJsonMarketDataDecoder().decode_quote(
        ExternalTransportResponse(
            status_code=200,
            received_at=_NOW,
            payload=b"not-json",
        ),
        source=_SOURCE,
        request=_quote_request(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, RealMarketDataProviderValidationError)
