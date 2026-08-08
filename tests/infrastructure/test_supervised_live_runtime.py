from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.activation_policy import (
    ProviderActivationDecisionSnapshot,
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
from qore.infrastructure.adapter_resilience import (
    AdapterResiliencePolicy,
    AdapterResilienceSnapshot,
    AdapterRetryDelay,
    AdapterTimeoutPolicy,
)
from qore.infrastructure.connectivity import (
    ProviderConnectionState,
    ProviderConnectivityMode,
    ProviderConnectivitySnapshot,
    ProviderEndpoint,
    ReadOnlyProviderConnectivityIntent,
)
from qore.infrastructure.ingestion import ExternalOhlcPayload, ExternalQuotePayload
from qore.infrastructure.live_market_data import (
    ControlledLiveMarketDataFlow,
    LiveMarketDataPayloadAdapter,
)
from qore.infrastructure.market_data import OhlcRequest, QuoteRequest
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.provider_runtime import (
    ExternalProviderRuntimeComponent,
    ExternalProviderRuntimePlan,
    ExternalRuntimeComponentId,
    ExternalRuntimeComponentKind,
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
from qore.infrastructure.supervised_live_runtime import (
    SupervisedLiveRuntimeConfiguration,
    compose_supervised_live_runtime,
)
from qore.infrastructure.transport import (
    ExternalTransportError,
    ExternalTransportMethod,
    ExternalTransportRequest,
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Result, Success

_NOW = datetime(2026, 8, 8, 5, 20, tzinfo=UTC)
_PROVIDER = ProviderDescriptor(
    provider_id=ProviderId(UUID("aa000000-0000-0000-0000-000000000001")),
    provider_name=ProviderName("reference.supervised-live"),
    enablement=ProviderEnablement.READ_ONLY,
    capabilities=ProviderCapabilitySet((ProviderCapability.MARKET_DATA_READ,)),
)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("aa000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("aa000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.live"),
)
_ENDPOINT = ProviderEndpoint("data.example.test")
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("aa000000-0000-0000-0000-000000000004")),
    causation_id=CausationId(UUID("aa000000-0000-0000-0000-000000000005")),
)


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-supervised-live"))
    assert isinstance(result, Success)
    return result.value


def _policy() -> ProviderActivationPolicy:
    return ProviderActivationPolicy(
        provider=_PROVIDER,
        source=_SOURCE,
        mode=ProviderActivationMode.READ_ONLY,
        required_capabilities=(ProviderCapability.MARKET_DATA_READ,),
    )


def _activation() -> ProviderActivationDecisionSnapshot:
    declared = declare_adapter_lifecycle(
        descriptor=_SOURCE,
        provider=_PROVIDER,
        declared_at=_NOW,
        actor=AdapterLifecycleActor("phase09.e2e"),
        metadata=_METADATA,
    )
    assert isinstance(declared, Success)
    lifecycle = declared.value
    for offset, state, reason in (
        (
            1,
            AdapterLifecycleState.CONFIGURED,
            AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
        ),
        (
            2,
            AdapterLifecycleState.INITIALIZED,
            AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED,
        ),
    ):
        result = apply_adapter_lifecycle_transition(
            lifecycle,
            AdapterLifecycleTransitionRequest(
                to_state=state,
                reason=reason,
                transitioned_at=_NOW + timedelta(seconds=offset),
                actor=AdapterLifecycleActor("phase09.e2e"),
                metadata=_METADATA,
            ),
        )
        assert isinstance(result, Success)
        lifecycle = result.value
    decision = evaluate_provider_activation_policy(
        ProviderActivationEvaluation(
            policy=_policy(),
            configuration=ExternalAdapterConfiguration(
                provider=_PROVIDER,
                source=_SOURCE,
                mode=AdapterConfigurationMode.READ_ONLY,
            ),
            lifecycle=lifecycle,
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
        return Success(
            ExternalTransportResponse(
                status_code=200,
                received_at=_NOW,
                payload=b"{}",
            )
        )


class _Factory:
    def quote_request(self, request: QuoteRequest) -> ExternalTransportRequest:
        return ExternalTransportRequest(
            endpoint=_ENDPOINT,
            method=ExternalTransportMethod.GET,
            path="/quote",
            timeout=ExternalTransportTimeout(1000),
        )

    def ohlc_request(self, request: OhlcRequest) -> ExternalTransportRequest:
        return ExternalTransportRequest(
            endpoint=_ENDPOINT,
            method=ExternalTransportMethod.GET,
            path="/ohlc",
            timeout=ExternalTransportTimeout(1000),
        )


class _Decoder:
    def decode_quote(
        self,
        response: ExternalTransportResponse,
        *,
        source: ExternalSourceDescriptor,
        request: QuoteRequest,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        return Success(
            ExternalQuotePayload(
                source=source,
                instrument=request.instrument.symbol,
                observed_at=response.received_at,
                bid="1.1",
                ask="1.2",
            )
        )

    def decode_ohlc(
        self,
        response: ExternalTransportResponse,
        *,
        source: ExternalSourceDescriptor,
        request: OhlcRequest,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        return Success(
            ExternalOhlcPayload(
                source=source,
                instrument=request.instrument.symbol,
                timeframe_seconds=str(request.timeframe.seconds),
                opened_at=request.opened_at,
                closed_at=request.closed_at,
                open="1.1",
                high="1.2",
                low="1.0",
                close="1.15",
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


def _external_plan() -> ExternalProviderRuntimePlan:
    return ExternalProviderRuntimePlan(
        components=(
            ExternalProviderRuntimeComponent(
                component_id=ExternalRuntimeComponentId("market-data.live"),
                component_kind=ExternalRuntimeComponentKind.PROVIDER_ADAPTER,
                provider=_PROVIDER,
                source=_SOURCE,
                activation_policy=_policy(),
            ),
        )
    )


def _configuration(
    state: ProviderConnectionState = ProviderConnectionState.READY,
) -> SupervisedLiveRuntimeConfiguration:
    connectivity = ProviderConnectivitySnapshot(
        intent=ReadOnlyProviderConnectivityIntent(
            provider=_PROVIDER,
            endpoint=_ENDPOINT,
            mode=ProviderConnectivityMode.NETWORK_READ_ONLY,
            capability=ProviderCapability.MARKET_DATA_READ,
        ),
        state=state,
        observed_at=_NOW,
        message=None if state is ProviderConnectionState.READY else "connectivity blocked",
    )
    resilience_policy = AdapterResiliencePolicy(
        provider=_PROVIDER,
        source=_SOURCE,
        timeout=AdapterTimeoutPolicy(AdapterRetryDelay(1000)),
    )
    return SupervisedLiveRuntimeConfiguration(
        external_runtime_plan=_external_plan(),
        market_data=_flow(),
        connectivity=connectivity,
        resilience=AdapterResilienceSnapshot(
            policy=resilience_policy,
            observed_at=_NOW,
        ),
        latency_milliseconds=12,
    )


def test_supervised_live_runtime_preserves_core_and_exposes_ready_market_data() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    result = compose_supervised_live_runtime(core, _configuration())

    assert isinstance(result, Success)
    assert result.value.core is core
    assert result.value.market_data is not None
    assert result.value.external_runtime_plan is result.value.configuration.external_runtime_plan
    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health


def test_non_ready_connectivity_exposes_no_live_market_data() -> None:
    result = compose_supervised_live_runtime(
        _core(),
        _configuration(ProviderConnectionState.BLOCKED),
    )

    assert isinstance(result, Success)
    assert result.value.market_data is None


def test_supervised_live_runtime_observability_is_sanitized() -> None:
    result = compose_supervised_live_runtime(_core(), _configuration())

    assert isinstance(result, Success)
    observed = result.value.observability()
    assert isinstance(observed, Success)
    assert observed.value.readiness.value == "ready"
    assert observed.value.latency is not None
    assert observed.value.latency.milliseconds == 12


def test_live_runtime_has_no_trading_write_surface() -> None:
    result = compose_supervised_live_runtime(_core(), _configuration())

    assert isinstance(result, Success)
    assert not hasattr(result.value, "write")
    assert not hasattr(result.value, "execute_order")
