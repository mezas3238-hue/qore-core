from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_market_data import (
    CTraderDemoMarketDataPayloadAdapter,
    CTraderDemoMarketDataUnsupportedError,
    CTraderDemoMarketDataValidationError,
    CTraderTrendbar,
    CTraderTrendbarPeriod,
    CTraderTrendbarReadResult,
)
from qore.infrastructure.ctrader_open_api_client import CTraderOpenApiClientError
from qore.infrastructure.ctrader_open_api_market_data_client import (
    CTraderOpenApiMarketDataClient,
)
from qore.infrastructure.ingestion import ExternalQuotePayload
from qore.infrastructure.market_data import Instrument, OhlcRequest, QuoteRequest, Timeframe
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import ExecutionInstrument
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
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.result import Failure, Result, Success

_ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="424242",
    environment=MarketRuntimeEnvironment.DEMO,
)
_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("53000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("53000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo"),
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("53000000-0000-0000-0000-000000000003"))
)
_OPENED = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
_PERIODS: tuple[tuple[int, CTraderTrendbarPeriod, int], ...] = (
    (60, CTraderTrendbarPeriod.M1, 1),
    (300, CTraderTrendbarPeriod.M5, 5),
    (900, CTraderTrendbarPeriod.M15, 7),
    (1_800, CTraderTrendbarPeriod.M30, 8),
    (3_600, CTraderTrendbarPeriod.H1, 9),
    (14_400, CTraderTrendbarPeriod.H4, 10),
    (86_400, CTraderTrendbarPeriod.D1, 12),
)


def _configuration() -> CTraderDemoRuntimeConfiguration:
    return CTraderDemoRuntimeConfiguration(
        provider_key="ctrader-demo",
        environment=MarketRuntimeEnvironment.DEMO,
        endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=_ACCOUNT,
        symbol_mappings=(
            CTraderSymbolMapping(
                instrument=ExecutionInstrument("EURUSD"),
                symbol_id=1234,
                symbol_name="EURUSD",
                digits=5,
                volume_step=Decimal("1"),
                min_volume_units=1,
                max_volume_units=1_000_000,
                step_volume_units=1,
            ),
        ),
        capabilities=(
            CTraderDemoCapability.ACCOUNT,
            CTraderDemoCapability.CANDLES,
            CTraderDemoCapability.ORDERS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )


def _request(seconds: int, *, opened_at: datetime = _OPENED) -> OhlcRequest:
    return OhlcRequest(
        instrument=Instrument("EURUSD"),
        timeframe=Timeframe(seconds),
        opened_at=opened_at,
        closed_at=opened_at + timedelta(seconds=seconds),
    )


def _trendbar(opened_at: datetime = _OPENED) -> CTraderTrendbar:
    return CTraderTrendbar(
        low_relative=110_000,
        delta_open=10,
        delta_high=50,
        delta_close=25,
        utc_timestamp_in_minutes=int(opened_at.timestamp() // 60),
    )


class _AdapterStub:
    def __init__(self) -> None:
        self.period: CTraderTrendbarPeriod | None = None
        self.calls: list[OhlcRequest] = []

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return _DESCRIPTOR

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        return Success(
            ExternalHealth(
                descriptor=_DESCRIPTOR,
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
        self.calls.append(request)
        period = next(
            item
            for seconds, item, _ in _PERIODS
            if seconds == request.timeframe.seconds
        )
        self.period = period
        return Success(
            CTraderTrendbarReadResult(
                instrument=request.instrument.symbol,
                symbol_id=1234,
                digits=5,
                period=period,
                trendbars=(_trendbar(request.opened_at),),
            )
        )

    def read_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        del metadata
        return Success(
            ExternalQuotePayload(
                source=_DESCRIPTOR,
                instrument=request.instrument.symbol,
                observed_at=_OPENED,
                bid="1.10000",
                ask="1.10010",
            )
        )


@pytest.mark.parametrize(("seconds", "period", "wire_value"), _PERIODS)
def test_payload_adapter_accepts_each_native_first_cohort_period(
    seconds: int,
    period: CTraderTrendbarPeriod,
    wire_value: int,
) -> None:
    del wire_value
    client = _AdapterStub()
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(seconds), metadata=_METADATA)

    assert isinstance(result, Success)
    assert result.value.timeframe_seconds == seconds
    assert client.period is period
    assert client.calls == [_request(seconds)]


def test_payload_adapter_rejects_non_native_m2_before_provider_call() -> None:
    client = _AdapterStub()
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(120), metadata=_METADATA)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataUnsupportedError)
    assert client.calls == []


def test_daily_requires_exact_utc_midnight() -> None:
    client = _AdapterStub()
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)
    opened = _OPENED + timedelta(hours=1)

    result = adapter.read_external_ohlc(
        _request(86_400, opened_at=opened),
        metadata=_METADATA,
    )

    assert isinstance(result, Failure)
    assert client.calls == []


class _OpenApiStub:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, object]]] = []

    @property
    def is_ready(self) -> bool:
        return True

    @property
    def account_id(self) -> int:
        return 424242

    def connect_and_authenticate(self) -> Result[None, CTraderOpenApiClientError]:
        return Success(None)

    def request(
        self,
        message_name: str,
        fields: Mapping[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Result[object, CTraderOpenApiClientError]:
        del client_msg_id, timeout_seconds
        captured = dict(fields)
        self.requests.append((message_name, captured))
        if message_name == "ProtoOAGetTrendbarsReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=424242,
                    symbolId=1234,
                    trendbar=(
                        SimpleNamespace(
                            low=110_000,
                            deltaOpen=10,
                            deltaHigh=50,
                            deltaClose=25,
                            utcTimestampInMinutes=int(_OPENED.timestamp() // 60),
                        ),
                    ),
                )
            )
        raise AssertionError(f"unexpected request: {message_name}")

    def wait_for_event(
        self,
        message_name: str,
        *,
        timeout_seconds: float,
        predicate: Callable[[object], bool] | None = None,
    ) -> Result[object, CTraderOpenApiClientError]:
        del message_name, timeout_seconds, predicate
        raise AssertionError("no event wait expected")

    def close(self) -> None:
        return None


@pytest.mark.parametrize(("seconds", "period", "wire_value"), _PERIODS)
def test_open_api_client_sends_exact_native_period_code(
    seconds: int,
    period: CTraderTrendbarPeriod,
    wire_value: int,
) -> None:
    client = _OpenApiStub()
    boundary = CTraderOpenApiMarketDataClient(
        descriptor=_DESCRIPTOR,
        configuration=_configuration(),
        client=client,
        clock=lambda: _OPENED + timedelta(days=7),
    )

    result = boundary.read_trendbars(_request(seconds), metadata=_METADATA)

    assert isinstance(result, Success)
    assert result.value.period is period
    assert client.requests[-1][0] == "ProtoOAGetTrendbarsReq"
    assert client.requests[-1][1]["period"] == wire_value


def test_open_api_client_rejects_still_open_bar_before_provider_call() -> None:
    client = _OpenApiStub()
    boundary = CTraderOpenApiMarketDataClient(
        descriptor=_DESCRIPTOR,
        configuration=_configuration(),
        client=client,
        clock=lambda: _OPENED + timedelta(minutes=4, seconds=59),
    )

    result = boundary.read_trendbars(_request(300), metadata=_METADATA)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)
    assert "fully closed" in str(result.error)
    assert client.requests == []


def test_open_api_client_accepts_bar_closed_exactly_at_observation_clock() -> None:
    client = _OpenApiStub()
    boundary = CTraderOpenApiMarketDataClient(
        descriptor=_DESCRIPTOR,
        configuration=_configuration(),
        client=client,
        clock=lambda: _OPENED + timedelta(minutes=5),
    )

    result = boundary.read_trendbars(_request(300), metadata=_METADATA)

    assert isinstance(result, Success)
    assert len(client.requests) == 1


def test_vt08_required_h4_is_native_not_resampled() -> None:
    client = _OpenApiStub()
    boundary = CTraderOpenApiMarketDataClient(
        descriptor=_DESCRIPTOR,
        configuration=_configuration(),
        client=client,
        clock=lambda: _OPENED + timedelta(days=7),
    )

    result = boundary.read_trendbars(_request(14_400), metadata=_METADATA)

    assert isinstance(result, Success)
    assert result.value.period is CTraderTrendbarPeriod.H4
    assert client.requests[-1][1]["period"] == 10
