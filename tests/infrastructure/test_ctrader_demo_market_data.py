from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.ctrader_demo_market_data import (
    CTraderDemoMarketDataFlow,
    CTraderDemoMarketDataPayloadAdapter,
    CTraderDemoMarketDataUnsupportedError,
    CTraderDemoMarketDataValidationError,
    CTraderTrendbar,
    CTraderTrendbarPeriod,
    CTraderTrendbarReadResult,
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

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("e1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("e1000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo"),
)
_CORRELATION = CorrelationId(UUID("e1000000-0000-0000-0000-000000000003"))
_CAUSATION = CausationId(UUID("e1000000-0000-0000-0000-000000000004"))
_SNAPSHOT_ID = MarketDataSnapshotId(UUID("e1000000-0000-0000-0000-000000000005"))
_INSTRUMENT = Instrument("EURUSD")
_OPENED_AT = datetime(2026, 8, 12, 13, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=5)
_OPENED_AT_MINUTES = 29_775_660


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _request(*, timeframe_seconds: int = 300) -> OhlcRequest:
    timeframe = Timeframe(timeframe_seconds)
    return OhlcRequest(
        instrument=_INSTRUMENT,
        timeframe=timeframe,
        opened_at=_OPENED_AT,
        closed_at=_OPENED_AT + timedelta(seconds=timeframe_seconds),
    )


def _trendbar(
    *,
    opened_at_minutes: int = _OPENED_AT_MINUTES,
) -> CTraderTrendbar:
    return CTraderTrendbar(
        low_relative=110_000,
        delta_open=10,
        delta_high=50,
        delta_close=25,
        utc_timestamp_in_minutes=opened_at_minutes,
    )


def _result(
    *,
    instrument: str = "EURUSD",
    digits: int = 5,
    trendbars: tuple[CTraderTrendbar, ...] | None = None,
    has_more: bool = False,
) -> CTraderTrendbarReadResult:
    return CTraderTrendbarReadResult(
        instrument=instrument,
        symbol_id=1_234,
        digits=digits,
        period=CTraderTrendbarPeriod.M5,
        trendbars=(_trendbar(),) if trendbars is None else trendbars,
        has_more=has_more,
    )


class StubCTraderClient:
    def __init__(
        self,
        result: Result[CTraderTrendbarReadResult, ExternalPortError],
    ) -> None:
        self._result = result
        self.requests: list[OhlcRequest] = []

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
                descriptor=self.descriptor,
                availability=PortAvailability.AVAILABLE,
                checked_at=checked_at,
            )
        )

    def read_trendbars(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderTrendbarReadResult, ExternalPortError]:
        del metadata
        self.requests.append(request)
        return self._result


def test_ctrader_closed_m5_normalizes_into_canonical_ohlc_snapshot() -> None:
    client = StubCTraderClient(Success(_result()))
    flow = CTraderDemoMarketDataFlow(
        CTraderDemoMarketDataPayloadAdapter(client=client)
    )

    result = flow.read_ohlc(
        _request(),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.snapshot_id is _SNAPSHOT_ID
    assert snapshot.instrument == _INSTRUMENT
    assert snapshot.source is _SOURCE
    assert snapshot.timeframe == Timeframe(300)
    assert snapshot.opened_at == _OPENED_AT
    assert snapshot.closed_at == _CLOSED_AT
    assert snapshot.open == 1.1001
    assert snapshot.high == 1.1005
    assert snapshot.low == 1.1
    assert snapshot.close == 1.10025
    assert client.requests == [_request()]


def test_ctrader_relative_prices_honor_symbol_digits() -> None:
    client = StubCTraderClient(Success(_result(digits=3)))
    flow = CTraderDemoMarketDataFlow(
        CTraderDemoMarketDataPayloadAdapter(client=client)
    )

    result = flow.read_ohlc(
        _request(),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.open == 1.1
    assert snapshot.high == 1.1
    assert snapshot.low == 1.1
    assert snapshot.close == 1.1


def test_ctrader_rejects_non_m5_request_before_client_call() -> None:
    client = StubCTraderClient(Success(_result()))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(timeframe_seconds=900), metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataUnsupportedError)
    assert client.requests == []


def test_ctrader_rejects_instrument_mismatch() -> None:
    client = StubCTraderClient(Success(_result(instrument="GBPUSD")))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(), metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_rejects_missing_or_multiple_exact_interval_trendbars() -> None:
    for trendbars in ((), (_trendbar(), _trendbar())):
        client = StubCTraderClient(Success(_result(trendbars=trendbars)))
        adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

        result = adapter.read_external_ohlc(_request(), metadata=_metadata())

        assert isinstance(result, Failure)
        assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_rejects_truncated_result() -> None:
    client = StubCTraderClient(Success(_result(has_more=True)))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(), metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_rejects_interval_mismatch() -> None:
    client = StubCTraderClient(
        Success(_result(trendbars=(_trendbar(opened_at_minutes=_OPENED_AT_MINUTES - 5),)))
    )
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(), metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_rejects_malformed_relative_structure() -> None:
    with pytest.raises(CTraderDemoMarketDataValidationError):
        CTraderTrendbar(
            low_relative=110_000,
            delta_open=60,
            delta_high=50,
            delta_close=25,
            utc_timestamp_in_minutes=_OPENED_AT_MINUTES,
        )


def test_ctrader_candle_only_adapter_fails_closed_for_quote_reads() -> None:
    client = StubCTraderClient(Success(_result()))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_quote(
        QuoteRequest(instrument=_INSTRUMENT),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataUnsupportedError)


def test_ctrader_client_failure_is_preserved() -> None:
    error = CTraderDemoMarketDataValidationError("sanitized provider failure")
    client = StubCTraderClient(Failure(error))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(), metadata=_metadata())

    assert isinstance(result, Failure)
    assert result.error is error


def test_ctrader_trendbar_logical_values_are_deterministic() -> None:
    first = _result()
    second = _result()

    assert first.logical_values() == second.logical_values()
    assert first.trendbars[0].logical_values() == second.trendbars[0].logical_values()
