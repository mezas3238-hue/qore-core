from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.activation_policy import (
    ProviderActivationEvaluation,
    ProviderActivationMode,
    ProviderActivationPolicy,
    evaluate_provider_activation_policy,
)
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationMode,
    ExternalAdapterConfiguration,
)
from qore.infrastructure.adapter_lifecycle import (
    AdapterLifecycleActor,
    AdapterLifecycleState,
    AdapterLifecycleTransitionReason,
    AdapterLifecycleTransitionRequest,
    apply_adapter_lifecycle_transition,
    declare_adapter_lifecycle,
)
from qore.infrastructure.connectivity import (
    ProviderConnectivityMode,
    ProviderEndpoint,
    ReadOnlyProviderConnectivityIntent,
)
from qore.infrastructure.ingestion import ExternalOhlcPayload, ExternalQuotePayload
from qore.infrastructure.live_market_data import (
    ControlledLiveMarketDataFlow,
    LiveMarketDataPayloadAdapter,
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
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.infrastructure.read_only_provider_adapter import (
    ReadOnlyExternalProviderAdapter,
    ReadOnlyProviderAdapterConfiguration,
)
from qore.infrastructure.transport import (
    ExternalTransportError,
    ExternalTransportMethod,
    ExternalTransportRequest,
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Result, Success

_NOW = datetime(2026, 8, 8, 4, 50, tzinfo=UTC)
_ENDPOINT = ProviderEndpoint("data.example.test", base_path="/v1")
_PROVIDER = ProviderDescriptor(
    provider_id=ProviderId(UUID("d9000000-0000-0000-0000-000000000001")),
    provider_name=ProviderName("reference.live-data"),
    enablement=ProviderEnablement.READ_ONLY,
    capabilities=ProviderCapabilitySet(
        (ProviderCapability.HEALTH, ProviderCapability.MARKET_DATA_READ)
    ),
)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("d9000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("d9000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.live"),
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("d9000000-0000-0000-0000-000000000004")),
    causation_id=CausationId(UUID("d9000000-0000-0000-0000-000000000005")),
)


def _activation():
    declared = declare_adapter_lifecycle(
        descriptor=_SOURCE,
        provider=_PROVIDER,
        declared_at=_NOW,
        actor=AdapterLifecycleActor("phase09.live"),
        metadata=_METADATA,
    )
    assert isinstance(declared, Success)
    snapshot = declared.value
    for offset, state, reason in (
        (1, AdapterLifecycleState.CONFIGURED, AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED),
        (2, AdapterLifecycleState.INITIALIZED, AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED),
    ):
        transitioned = apply_adapter_lifecycle_transition(
            snapshot,
            AdapterLifecycleTransitionRequest(
                to_state=state,
                reason=reason,
                transitioned_at=_NOW + timedelta(seconds=offset),
                actor=AdapterLifecycleActor("phase09.live"),
                metadata=_METADATA,
            ),
        )
        assert isinstance(transitioned, Success)
        snapshot = transitioned.value
    decision = evaluate_provider_activation_policy(
        ProviderActivationEvaluation(
            policy=ProviderActivationPolicy(
                provider=_PROVIDER,
                source=_SOURCE,
                mode=ProviderActivationMode.READ_ONLY,
                required_capabilities=(ProviderCapability.MARKET_DATA_READ,),
            ),
            configuration=ExternalAdapterConfiguration(
                provider=_PROVIDER,
                source=_SOURCE,
                mode=AdapterConfigurationMode.READ_ONLY,
            ),
            lifecycle=snapshot,
            evaluated_at=_NOW + timedelta(seconds=3),
            metadata=_METADATA,
        )
    )
    assert isinstance(decision, Success)
    return decision.value


class _Transport:
    def execute(
        self,
        request: ExternalTransportRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExternalTransportError]:
        assert metadata == _METADATA
        payload = b"quote" if request.path == "/quote" else b"ohlc"
        return Success(
            ExternalTransportResponse(
                status_code=200,
                received_at=_NOW + timedelta(seconds=4),
                payload=payload,
            )
        )


class _Factory:
    def quote_request(self, request: QuoteRequest) -> ExternalTransportRequest:
        return ExternalTransportRequest(
            endpoint=_ENDPOINT,
            method=ExternalTransportMethod.GET,
            path="/quote",
            timeout=ExternalTransportTimeout(1000),
            query=(("instrument", request.instrument.symbol),),
        )

    def ohlc_request(self, request: OhlcRequest) -> ExternalTransportRequest:
        return ExternalTransportRequest(
            endpoint=_ENDPOINT,
            method=ExternalTransportMethod.GET,
            path="/ohlc",
            timeout=ExternalTransportTimeout(1000),
            query=(("instrument", request.instrument.symbol),),
        )


class _Decoder:
    def decode_quote(
        self,
        response: ExternalTransportResponse,
        *,
        source: ExternalSourceDescriptor,
        request: QuoteRequest,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        assert response.payload == b"quote"
        return Success(
            ExternalQuotePayload(
                source=source,
                instrument=request.instrument.symbol.lower(),
                observed_at=response.received_at,
                bid="1.1000",
                ask="1.1002",
            )
        )

    def decode_ohlc(
        self,
        response: ExternalTransportResponse,
        *,
        source: ExternalSourceDescriptor,
        request: OhlcRequest,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        assert response.payload == b"ohlc"
        return Success(
            ExternalOhlcPayload(
                source=source,
                instrument=request.instrument.symbol,
                timeframe_seconds=str(request.timeframe.seconds),
                opened_at=request.opened_at,
                closed_at=request.closed_at,
                open="1.1000",
                high="1.1010",
                low="1.0990",
                close="1.1005",
            )
        )


def _flow() -> ControlledLiveMarketDataFlow:
    provider = ReadOnlyExternalProviderAdapter(
        configuration=ReadOnlyProviderAdapterConfiguration(
            connectivity=ReadOnlyProviderConnectivityIntent(
                provider=_PROVIDER,
                endpoint=_ENDPOINT,
                mode=ProviderConnectivityMode.NETWORK_READ_ONLY,
                capability=ProviderCapability.MARKET_DATA_READ,
            ),
            activation=_activation(),
        ),
        transport=_Transport(),
    )
    return ControlledLiveMarketDataFlow(
        LiveMarketDataPayloadAdapter(
            provider=provider,
            request_factory=_Factory(),
            decoder=_Decoder(),
            resolved_at=_NOW,
        )
    )


def test_live_quote_flows_through_existing_canonical_ingestion() -> None:
    result = _flow().read_quote(
        QuoteRequest(Instrument("EURUSD")),
        snapshot_id=MarketDataSnapshotId(
            UUID("d9000000-0000-0000-0000-000000000006")
        ),
        metadata=_METADATA,
    )

    assert isinstance(result, Success)
    assert result.value.instrument == Instrument("EURUSD")
    assert result.value.bid == 1.1
    assert result.value.ask == 1.1002
    assert result.value.source == _SOURCE


def test_live_ohlc_flows_through_existing_canonical_ingestion() -> None:
    opened = _NOW - timedelta(minutes=15)
    request = OhlcRequest(
        instrument=Instrument("GBPUSD"),
        timeframe=Timeframe(900),
        opened_at=opened,
        closed_at=_NOW,
    )
    result = _flow().read_ohlc(
        request,
        snapshot_id=MarketDataSnapshotId(
            UUID("d9000000-0000-0000-0000-000000000007")
        ),
        metadata=_METADATA,
    )

    assert isinstance(result, Success)
    assert result.value.timeframe == Timeframe(900)
    assert result.value.open == 1.1
    assert result.value.high == 1.101
    assert result.value.low == 1.099
    assert result.value.close == 1.1005


def test_live_payload_adapter_health_is_available_only_for_allowed_activation() -> None:
    result = _flow().payload_adapter.health(checked_at=_NOW, metadata=_METADATA)

    assert isinstance(result, Success)
    assert result.value.availability.value == "available"
