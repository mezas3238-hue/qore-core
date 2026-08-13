from __future__ import annotations

import inspect
from datetime import UTC, datetime
from uuid import UUID

import pytest

import qore.infrastructure.ctrader_native_market_data as native_module
from qore.domain.events import CorrelationId
from qore.infrastructure.ctrader_demo_market_data import CTraderTrendbar
from qore.infrastructure.ctrader_native_market_data import (
    CTraderNativeMarketDataFlow,
    CTraderNativeMarketDataUnsupportedError,
    CTraderNativeMarketDataValidationError,
    CTraderNativeTrendbarDelivery,
    CTraderNativeTrendbarPeriod,
    CTraderNativeTrendbarProviderRequest,
    CTraderNativeTrendbarReadRequest,
    CTraderNativeTrendbarReadResult,
    ctrader_period_for_timeframe,
    market_timeframe_for_ctrader_period,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import MarketTimeframe, MarketTimeframeCode
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.provider_instrument_catalog import (
    ProviderCatalogScope,
    ProviderInstrumentCatalog,
    ProviderInstrumentCatalogEntry,
    ProviderInstrumentEvidenceReference,
    ProviderInstrumentTradingStatus,
)
from qore.kernel.result import Failure, Result, Success


_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f3000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("f3000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader.native-test"),
)
_SCOPE = ProviderCatalogScope(
    provider_name="cTrader",
    server_environment="demo-eu",
    account_reference="12345",
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("f3000000-0000-0000-0000-000000000003")),
)
_OBSERVED_AT = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
_FROM = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
_TO = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
_BAR_OPEN = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
_BAR_OPEN_MINUTES = int(_BAR_OPEN.timestamp() // 60)


def _catalog(
    timeframes: tuple[MarketTimeframe, ...],
    *,
    source: ExternalSourceDescriptor = _DESCRIPTOR,
    scope: ProviderCatalogScope = _SCOPE,
) -> ProviderInstrumentCatalog:
    entry = ProviderInstrumentCatalogEntry(
        instrument=Instrument("EURUSD"),
        provider_symbol="EUR/USD",
        provider_symbol_id="1001",
        asset_class="FX",
        price_precision=5,
        minimum_price_increment=None,
        volume_terms=None,
        trading_status=ProviderInstrumentTradingStatus.TRADABLE,
        trading_sessions=(),
        native_timeframes=timeframes,
        margin_terms=None,
        effective_at=_OBSERVED_AT,
        evidence_ref=ProviderInstrumentEvidenceReference("ctrader-native-catalog-evidence"),
    )
    return ProviderInstrumentCatalog(
        scope=scope,
        source=source,
        observed_at=_OBSERVED_AT,
        entries=(entry,),
    )


def _trendbar(*, opened_at_minutes: int = _BAR_OPEN_MINUTES) -> CTraderTrendbar:
    return CTraderTrendbar(
        low_relative=110_000,
        delta_open=10,
        delta_high=50,
        delta_close=25,
        utc_timestamp_in_minutes=opened_at_minutes,
    )


def _result(
    *,
    symbol_id: int = 1001,
    period: CTraderNativeTrendbarPeriod = CTraderNativeTrendbarPeriod.MN1,
    has_more: bool = False,
    trendbars: tuple[CTraderTrendbar, ...] | None = None,
) -> CTraderNativeTrendbarReadResult:
    return CTraderNativeTrendbarReadResult(
        symbol_id=symbol_id,
        period=period,
        trendbars=(_trendbar(),) if trendbars is None else trendbars,
        has_more=has_more,
        observed_at=_OBSERVED_AT,
        evidence_ref=ProviderInstrumentEvidenceReference("ctrader-native-read-evidence"),
    )


class _NativeClient:
    def __init__(
        self,
        result: Result[CTraderNativeTrendbarReadResult, ExternalPortError],
        *,
        descriptor: ExternalSourceDescriptor = _DESCRIPTOR,
        scope: ProviderCatalogScope = _SCOPE,
    ) -> None:
        self._result = result
        self._descriptor = descriptor
        self._scope = scope
        self.calls: list[CTraderNativeTrendbarProviderRequest] = []

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self._descriptor

    @property
    def scope(self) -> ProviderCatalogScope:
        return self._scope

    def read_native_trendbars(
        self,
        request: CTraderNativeTrendbarProviderRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderNativeTrendbarReadResult, ExternalPortError]:
        assert metadata is _METADATA
        self.calls.append(request)
        return self._result


def _request(code: MarketTimeframeCode) -> CTraderNativeTrendbarReadRequest:
    return CTraderNativeTrendbarReadRequest(
        instrument=Instrument("EURUSD"),
        timeframe=MarketTimeframe(code),
        from_timestamp=_FROM,
        to_timestamp=_TO,
    )


def test_all_official_period_identities_map_bidirectionally() -> None:
    assert tuple(item.value for item in CTraderNativeTrendbarPeriod) == tuple(
        item.value for item in MarketTimeframeCode
    )
    for period in CTraderNativeTrendbarPeriod:
        timeframe = market_timeframe_for_ctrader_period(period)
        assert timeframe.code.value == period.value
        assert ctrader_period_for_timeframe(timeframe) is period


def test_calendar_timeframes_remain_identity_without_fake_fixed_seconds() -> None:
    for code in (
        MarketTimeframeCode.D1,
        MarketTimeframeCode.W1,
        MarketTimeframeCode.MN1,
    ):
        timeframe = MarketTimeframe(code)
        assert timeframe.fixed_seconds is None
        assert ctrader_period_for_timeframe(timeframe).value == code.value


def test_native_result_canonicalizes_order_and_rejects_duplicate_open_times() -> None:
    first = _trendbar(opened_at_minutes=_BAR_OPEN_MINUTES)
    second = _trendbar(opened_at_minutes=_BAR_OPEN_MINUTES + 5)

    left = _result(trendbars=(second, first))
    right = _result(trendbars=(first, second))

    assert left.trendbars == (first, second)
    assert left.logical_values() == right.logical_values()

    with pytest.raises(CTraderNativeMarketDataValidationError):
        _result(trendbars=(first, first))


def test_unverified_timeframe_fails_before_provider_read() -> None:
    client = _NativeClient(Success(_result(period=CTraderNativeTrendbarPeriod.M15)))
    flow = CTraderNativeMarketDataFlow(
        catalog=_catalog((MarketTimeframe(MarketTimeframeCode.M5),)),
        client=client,
    )

    result = flow.read_native_trendbars(
        _request(MarketTimeframeCode.M15),
        metadata=_METADATA,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderNativeMarketDataUnsupportedError)
    assert client.calls == []


def test_verified_mn1_read_resolves_catalog_symbol_and_preserves_calendar_identity() -> None:
    client = _NativeClient(Success(_result()))
    flow = CTraderNativeMarketDataFlow(
        catalog=_catalog((MarketTimeframe(MarketTimeframeCode.MN1),)),
        client=client,
    )
    request = _request(MarketTimeframeCode.MN1)

    result = flow.read_native_trendbars(request, metadata=_METADATA)

    assert isinstance(result, Success)
    delivery = result.value
    assert isinstance(delivery, CTraderNativeTrendbarDelivery)
    assert delivery.instrument == Instrument("EURUSD")
    assert delivery.provider_symbol == "EUR/USD"
    assert delivery.provider_symbol_id == 1001
    assert delivery.timeframe.code is MarketTimeframeCode.MN1
    assert delivery.timeframe.fixed_seconds is None
    assert delivery.trendbars == (_trendbar(),)
    assert len(client.calls) == 1
    provider_request = client.calls[0]
    assert provider_request.symbol_id == 1001
    assert provider_request.period is CTraderNativeTrendbarPeriod.MN1
    assert provider_request.from_timestamp == _FROM
    assert provider_request.to_timestamp == _TO


def test_result_symbol_and_period_mismatch_fail_closed() -> None:
    symbol_client = _NativeClient(Success(_result(symbol_id=999)))
    symbol_flow = CTraderNativeMarketDataFlow(
        catalog=_catalog((MarketTimeframe(MarketTimeframeCode.MN1),)),
        client=symbol_client,
    )
    symbol_result = symbol_flow.read_native_trendbars(
        _request(MarketTimeframeCode.MN1),
        metadata=_METADATA,
    )
    assert isinstance(symbol_result, Failure)
    assert isinstance(symbol_result.error, CTraderNativeMarketDataValidationError)

    period_client = _NativeClient(
        Success(_result(period=CTraderNativeTrendbarPeriod.W1))
    )
    period_flow = CTraderNativeMarketDataFlow(
        catalog=_catalog((MarketTimeframe(MarketTimeframeCode.MN1),)),
        client=period_client,
    )
    period_result = period_flow.read_native_trendbars(
        _request(MarketTimeframeCode.MN1),
        metadata=_METADATA,
    )
    assert isinstance(period_result, Failure)
    assert isinstance(period_result.error, CTraderNativeMarketDataValidationError)


def test_truncated_or_out_of_window_provider_evidence_fails_closed() -> None:
    truncated_client = _NativeClient(Success(_result(has_more=True)))
    truncated_flow = CTraderNativeMarketDataFlow(
        catalog=_catalog((MarketTimeframe(MarketTimeframeCode.MN1),)),
        client=truncated_client,
    )
    truncated = truncated_flow.read_native_trendbars(
        _request(MarketTimeframeCode.MN1),
        metadata=_METADATA,
    )
    assert isinstance(truncated, Failure)
    assert isinstance(truncated.error, CTraderNativeMarketDataValidationError)

    before_window = int(datetime(2026, 7, 31, 23, 59, tzinfo=UTC).timestamp() // 60)
    window_client = _NativeClient(
        Success(_result(trendbars=(_trendbar(opened_at_minutes=before_window),)))
    )
    window_flow = CTraderNativeMarketDataFlow(
        catalog=_catalog((MarketTimeframe(MarketTimeframeCode.MN1),)),
        client=window_client,
    )
    outside = window_flow.read_native_trendbars(
        _request(MarketTimeframeCode.MN1),
        metadata=_METADATA,
    )
    assert isinstance(outside, Failure)
    assert isinstance(outside.error, CTraderNativeMarketDataValidationError)


def test_client_descriptor_and_scope_must_match_catalog() -> None:
    other_descriptor = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f3000000-0000-0000-0000-000000000011")),
        source_id=SourceId(UUID("f3000000-0000-0000-0000-000000000012")),
        port_name=PortName("market-data.ctrader.other"),
    )
    with pytest.raises(CTraderNativeMarketDataValidationError):
        CTraderNativeMarketDataFlow(
            catalog=_catalog((MarketTimeframe(MarketTimeframeCode.M5),)),
            client=_NativeClient(Success(_result()), descriptor=other_descriptor),
        )

    other_scope = ProviderCatalogScope(
        provider_name="cTrader",
        server_environment="demo-eu",
        account_reference="54321",
    )
    with pytest.raises(CTraderNativeMarketDataValidationError):
        CTraderNativeMarketDataFlow(
            catalog=_catalog((MarketTimeframe(MarketTimeframeCode.M5),)),
            client=_NativeClient(Success(_result()), scope=other_scope),
        )


def test_native_market_data_module_has_no_hidden_runtime_or_fake_calendar_duration() -> None:
    source = inspect.getsource(native_module).lower()
    for forbidden in (
        "datetime.now(",
        "datetime.utcnow(",
        "uuid4(",
        "requests.",
        "httpx",
        "aiohttp",
        "socket",
        "30 * 24",
        "30*24",
        "mn1_seconds",
    ):
        assert forbidden not in source
