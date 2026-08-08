from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure as infrastructure
from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.activation_policy import (
    ProviderActivationDecision,
    ProviderActivationDecisionReason,
    ProviderActivationMode,
    ProviderActivationPolicy,
)
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationMode,
    AdapterSecretName,
    AdapterSecretRequirement,
    AdapterSecretRequirements,
    ExternalAdapterConfiguration,
)
from qore.infrastructure.adapter_lifecycle import (
    AdapterLifecycleActor,
    AdapterLifecycleSnapshot,
    AdapterLifecycleState,
    AdapterLifecycleTransitionReason,
    AdapterLifecycleTransitionRequest,
    apply_adapter_lifecycle_transition,
    declare_adapter_lifecycle,
)
from qore.infrastructure.adapter_observability import (
    AdapterObservabilitySnapshot,
    AdapterReadiness,
)
from qore.infrastructure.adapter_resilience import (
    AdapterResiliencePolicy,
    AdapterResilienceUnavailableError,
    AdapterRetryDelay,
    AdapterTimeoutPolicy,
)
from qore.infrastructure.external_health import ExternalProviderReadiness
from qore.infrastructure.ingestion import ExternalOhlcPayload, ExternalQuotePayload
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcRequest,
    QuoteRequest,
    Timeframe,
)
from qore.infrastructure.market_data_provider_harness import (
    MarketDataProviderHarnessState,
    MarketDataProviderOhlcIngestion,
    MarketDataProviderQuoteIngestion,
    ReadOnlyMarketDataProviderHarnessConfiguration,
)
from qore.infrastructure.persistence import LoadPersistenceRequest, PersistenceKey
from qore.infrastructure.persistence_backend_harness import (
    PersistenceBackendHarnessConfiguration,
)
from qore.infrastructure.ports import (
    AdapterId,
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
    build_external_provider_runtime_plan,
)
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.infrastructure.supervised_provider_harness import (
    SupervisedProviderHarnessBoundary,
    SupervisedProviderHarnessConfiguration,
    SupervisedProviderHarnessError,
    SupervisedProviderHarnessPorts,
    SupervisedProviderHarnessValidationError,
    SupervisedProviderSecretReferences,
    compose_supervised_provider_harness,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 2, 30, tzinfo=UTC)
_DECLARED_AT = _NOW - timedelta(minutes=5)
_CONFIGURED_AT = _NOW - timedelta(minutes=4)
_INITIALIZED_AT = _NOW - timedelta(minutes=3)
_STARTED_AT = _NOW - timedelta(minutes=2)
_STOPPED_AT = _NOW - timedelta(minutes=1)
_OPENED_AT = datetime(2026, 8, 8, 2, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=1)

_PROVIDER_ID = ProviderId(UUID("c9000000-0000-0000-0000-000000000001"))
_MARKET_ADAPTER_ID = AdapterId(UUID("c9000000-0000-0000-0000-000000000002"))
_MARKET_SOURCE_ID = SourceId(UUID("c9000000-0000-0000-0000-000000000003"))
_PERSISTENCE_ADAPTER_ID = AdapterId(UUID("c9000000-0000-0000-0000-000000000004"))
_PERSISTENCE_SOURCE_ID = SourceId(UUID("c9000000-0000-0000-0000-000000000005"))
_CORRELATION_ID = CorrelationId(UUID("c9000000-0000-0000-0000-000000000006"))
_CAUSATION_ID = CausationId(UUID("c9000000-0000-0000-0000-000000000007"))
_QUOTE_ID = MarketDataSnapshotId(UUID("c9000000-0000-0000-0000-000000000008"))
_OHLC_ID = MarketDataSnapshotId(UUID("c9000000-0000-0000-0000-000000000009"))
_ACTOR = AdapterLifecycleActor("supervisor")
_API_KEY = AdapterSecretName("api_key")


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"request": "supervised-provider-harness"},
    )


def _provider() -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("supervised-provider"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (
                ProviderCapability.HEALTH,
                ProviderCapability.MARKET_DATA_READ,
                ProviderCapability.PERSISTENCE_READ,
                ProviderCapability.PERSISTENCE_WRITE,
            )
        ),
    )


def _market_source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_MARKET_ADAPTER_ID,
        source_id=_MARKET_SOURCE_ID,
        port_name=PortName("market-data.supervised-harness"),
    )


def _persistence_source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_PERSISTENCE_ADAPTER_ID,
        source_id=_PERSISTENCE_SOURCE_ID,
        port_name=PortName("persistence.supervised-harness"),
    )


def _adapter_configuration(
    source: ExternalSourceDescriptor,
    *,
    secret_requirements: AdapterSecretRequirements | None = None,
) -> ExternalAdapterConfiguration:
    return ExternalAdapterConfiguration(
        provider=_provider(),
        source=source,
        mode=AdapterConfigurationMode.READ_ONLY,
        secret_requirements=secret_requirements or AdapterSecretRequirements(),
    )


def _resilience_policy(source: ExternalSourceDescriptor) -> AdapterResiliencePolicy:
    return AdapterResiliencePolicy(
        provider=_provider(),
        source=source,
        timeout=AdapterTimeoutPolicy(AdapterRetryDelay(250)),
    )


def _activation_policy(
    source: ExternalSourceDescriptor,
    *,
    required_capabilities: tuple[ProviderCapability, ...],
) -> ProviderActivationPolicy:
    return ProviderActivationPolicy(
        provider=_provider(),
        source=source,
        mode=ProviderActivationMode.READ_ONLY,
        required_capabilities=required_capabilities,
    )


def _runtime_component(
    source: ExternalSourceDescriptor,
    *,
    component_id: str,
    kind: ExternalRuntimeComponentKind,
    required_capabilities: tuple[ProviderCapability, ...],
) -> ExternalProviderRuntimeComponent:
    return ExternalProviderRuntimeComponent(
        component_id=ExternalRuntimeComponentId(component_id),
        component_kind=kind,
        provider=_provider(),
        source=source,
        activation_policy=_activation_policy(
            source,
            required_capabilities=required_capabilities,
        ),
    )


def _runtime_plan(
    *,
    include_market: bool = True,
    include_persistence: bool = True,
    market_kind: ExternalRuntimeComponentKind = (
        ExternalRuntimeComponentKind.MARKET_DATA_HARNESS
    ),
) -> ExternalProviderRuntimePlan:
    components: list[ExternalProviderRuntimeComponent] = []
    if include_market:
        components.append(
            _runtime_component(
                _market_source(),
                component_id="market-data",
                kind=market_kind,
                required_capabilities=(ProviderCapability.MARKET_DATA_READ,),
            )
        )
    if include_persistence:
        components.append(
            _runtime_component(
                _persistence_source(),
                component_id="persistence",
                kind=ExternalRuntimeComponentKind.PERSISTENCE_HARNESS,
                required_capabilities=(ProviderCapability.PERSISTENCE_READ,),
            )
        )
    result = build_external_provider_runtime_plan(components=tuple(components))
    assert isinstance(result, Success)
    return result.value


def _policy_disabled_runtime_plan() -> ExternalProviderRuntimePlan:
    component = ExternalProviderRuntimeComponent(
        component_id=ExternalRuntimeComponentId("market-data"),
        component_kind=ExternalRuntimeComponentKind.MARKET_DATA_HARNESS,
        provider=_provider(),
        source=_market_source(),
        activation_policy=ProviderActivationPolicy(
            provider=_provider(),
            source=_market_source(),
            mode=ProviderActivationMode.DISABLED,
            required_capabilities=(ProviderCapability.MARKET_DATA_READ,),
        ),
    )
    result = build_external_provider_runtime_plan(components=(component,))
    assert isinstance(result, Success)
    return result.value


def _quote_request() -> QuoteRequest:
    return QuoteRequest(Instrument("EURUSD"))


def _ohlc_request() -> OhlcRequest:
    return OhlcRequest(
        instrument=Instrument("EURUSD"),
        timeframe=Timeframe(60),
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
    )


def _quote_payload() -> ExternalQuotePayload:
    return ExternalQuotePayload(
        source=_market_source(),
        instrument="eurusd",
        observed_at=_NOW,
        bid="1.1000",
        ask="1.1002",
    )


def _ohlc_payload() -> ExternalOhlcPayload:
    return ExternalOhlcPayload(
        source=_market_source(),
        instrument="eurusd",
        timeframe_seconds="60",
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
        open="1.1000",
        high="1.1010",
        low="1.0990",
        close="1.1005",
    )


def _market_configuration(
    *,
    state: MarketDataProviderHarnessState = MarketDataProviderHarnessState.AVAILABLE,
    secret_requirements: AdapterSecretRequirements | None = None,
) -> ReadOnlyMarketDataProviderHarnessConfiguration:
    return ReadOnlyMarketDataProviderHarnessConfiguration(
        adapter_configuration=_adapter_configuration(
            _market_source(),
            secret_requirements=secret_requirements,
        ),
        metadata=_metadata(),
        resilience_policy=_resilience_policy(_market_source()),
        quote_payloads=(_quote_payload(),),
        ohlc_payloads=(_ohlc_payload(),),
        quote_ingestions=(
            MarketDataProviderQuoteIngestion(
                request=_quote_request(),
                snapshot_id=_QUOTE_ID,
            ),
        ),
        ohlc_ingestions=(
            MarketDataProviderOhlcIngestion(
                request=_ohlc_request(),
                snapshot_id=_OHLC_ID,
            ),
        ),
        state=state,
    )


def _persistence_configuration() -> PersistenceBackendHarnessConfiguration[str]:
    return PersistenceBackendHarnessConfiguration(
        adapter_configuration=_adapter_configuration(_persistence_source()),
        metadata=_metadata(),
        resilience_policy=_resilience_policy(_persistence_source()),
    )


def _lifecycle(
    source: ExternalSourceDescriptor,
    *,
    state: AdapterLifecycleState = AdapterLifecycleState.STARTED,
) -> AdapterLifecycleSnapshot:
    declared = declare_adapter_lifecycle(
        descriptor=source,
        provider=_provider(),
        declared_at=_DECLARED_AT,
        actor=_ACTOR,
        metadata=_metadata(),
    )
    assert isinstance(declared, Success)

    configured = apply_adapter_lifecycle_transition(
        declared.value,
        AdapterLifecycleTransitionRequest(
            to_state=AdapterLifecycleState.CONFIGURED,
            reason=AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
            transitioned_at=_CONFIGURED_AT,
            actor=_ACTOR,
            metadata=_metadata(),
        ),
    )
    assert isinstance(configured, Success)

    initialized = apply_adapter_lifecycle_transition(
        configured.value,
        AdapterLifecycleTransitionRequest(
            to_state=AdapterLifecycleState.INITIALIZED,
            reason=AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED,
            transitioned_at=_INITIALIZED_AT,
            actor=_ACTOR,
            metadata=_metadata(),
        ),
    )
    assert isinstance(initialized, Success)
    if state is AdapterLifecycleState.INITIALIZED:
        return initialized.value

    started = apply_adapter_lifecycle_transition(
        initialized.value,
        AdapterLifecycleTransitionRequest(
            to_state=AdapterLifecycleState.STARTED,
            reason=AdapterLifecycleTransitionReason.START_REQUESTED,
            transitioned_at=_STARTED_AT,
            actor=_ACTOR,
            metadata=_metadata(),
        ),
    )
    assert isinstance(started, Success)
    if state is AdapterLifecycleState.STARTED:
        return started.value

    reason = AdapterLifecycleTransitionReason.STOP_REQUESTED
    message = None
    if state is AdapterLifecycleState.DEGRADED:
        reason = AdapterLifecycleTransitionReason.DEGRADED_HEALTH
        message = "supervised provider degraded"
    if state is AdapterLifecycleState.FAILED:
        reason = AdapterLifecycleTransitionReason.FAILURE_DETECTED
        message = "supervised provider unavailable"

    transitioned = apply_adapter_lifecycle_transition(
        started.value,
        AdapterLifecycleTransitionRequest(
            to_state=state,
            reason=reason,
            transitioned_at=_STOPPED_AT,
            actor=_ACTOR,
            metadata=_metadata(),
            message=message,
        ),
    )
    assert isinstance(transitioned, Success)
    return transitioned.value


def _observability(
    *,
    readiness: AdapterReadiness = AdapterReadiness.READY,
) -> AdapterObservabilitySnapshot:
    message = None
    if readiness is AdapterReadiness.DEGRADED:
        message = "supervised observability degraded"
    if readiness is AdapterReadiness.UNAVAILABLE:
        message = "supervised observability unavailable"
    return AdapterObservabilitySnapshot(
        provider=_provider(),
        source=_market_source(),
        readiness=readiness,
        observed_at=_NOW,
        message=message,
    )


def _configuration(
    *,
    include_market: bool = True,
    include_persistence: bool = True,
    market: ReadOnlyMarketDataProviderHarnessConfiguration | None = None,
    persistence: PersistenceBackendHarnessConfiguration[str] | None = None,
    lifecycles: tuple[AdapterLifecycleSnapshot, ...] | None = None,
    observability: tuple[AdapterObservabilitySnapshot, ...] = (),
    runtime_plan: ExternalProviderRuntimePlan | None = None,
) -> SupervisedProviderHarnessConfiguration[str]:
    market_configuration = None
    if include_market:
        market_configuration = market if market is not None else _market_configuration()
    persistence_configuration = None
    if include_persistence:
        persistence_configuration = (
            persistence if persistence is not None else _persistence_configuration()
        )
    if lifecycles is None:
        lifecycle_list: list[AdapterLifecycleSnapshot] = []
        if market_configuration is not None:
            lifecycle_list.append(_lifecycle(_market_source()))
        if persistence_configuration is not None:
            lifecycle_list.append(_lifecycle(_persistence_source()))
        resolved_lifecycles = tuple(lifecycle_list)
    else:
        resolved_lifecycles = lifecycles
    return SupervisedProviderHarnessConfiguration(
        runtime_plan=runtime_plan or _runtime_plan(
            include_market=market_configuration is not None,
            include_persistence=persistence_configuration is not None,
        ),
        observed_at=_NOW,
        metadata=_metadata(),
        lifecycles=resolved_lifecycles,
        market_data_configuration=market_configuration,
        persistence_configuration=persistence_configuration,
        observability=observability,
    )


def test_supervised_provider_harness_starts_and_exposes_allowed_ports() -> None:
    result = compose_supervised_provider_harness(_configuration())

    assert isinstance(result, Success)
    harness = result.value
    assert harness.health.readiness is ExternalProviderReadiness.READY
    assert harness.ports.exposes_any
    assert harness.ports.market_data is not None
    assert harness.ports.persistence is not None

    quote = harness.ports.market_data.read_quote(_quote_request(), metadata=_metadata())
    missing = harness.ports.persistence.load(
        LoadPersistenceRequest(PersistenceKey("supervised", "missing")),
        metadata=_metadata(),
    )
    health = harness.external_health_snapshot(observed_at=_NOW, metadata=_metadata())

    assert isinstance(quote, Success)
    assert quote.value.snapshot_id == _QUOTE_ID
    assert isinstance(missing, Success)
    assert missing.value is None
    assert isinstance(health, Success)
    assert health.value.logical_values() == harness.health.logical_values()


def test_supervised_provider_harness_stopped_lifecycle_blocks_ports() -> None:
    result = compose_supervised_provider_harness(
        _configuration(
            include_persistence=False,
            runtime_plan=_runtime_plan(include_persistence=False),
            lifecycles=(_lifecycle(_market_source(), state=AdapterLifecycleState.STOPPED),),
        )
    )

    assert isinstance(result, Success)
    harness = result.value
    decision = harness.activation_decision_for(_market_source())

    assert decision is not None
    assert decision.decision is ProviderActivationDecision.BLOCKED
    assert ProviderActivationDecisionReason.LIFECYCLE_NOT_READY in decision.reasons
    assert harness.health.readiness is ExternalProviderReadiness.BLOCKED
    assert not harness.ports.exposes_any


def test_supervised_provider_harness_degraded_health_does_not_expose_ports() -> None:
    result = compose_supervised_provider_harness(
        _configuration(
            include_persistence=False,
            runtime_plan=_runtime_plan(include_persistence=False),
            lifecycles=(_lifecycle(_market_source()),),
            observability=(_observability(readiness=AdapterReadiness.DEGRADED),),
        )
    )

    assert isinstance(result, Success)
    harness = result.value
    decision = harness.activation_decision_for(_market_source())

    assert decision is not None
    assert decision.decision is ProviderActivationDecision.DEGRADED
    assert harness.health.readiness is ExternalProviderReadiness.DEGRADED
    assert not harness.ports.exposes_any


def test_supervised_provider_harness_blocks_disabled_policy() -> None:
    result = compose_supervised_provider_harness(
        _configuration(
            include_persistence=False,
            runtime_plan=_policy_disabled_runtime_plan(),
            lifecycles=(_lifecycle(_market_source()),),
        )
    )

    assert isinstance(result, Success)
    harness = result.value
    decision = harness.activation_decision_for(_market_source())

    assert decision is not None
    assert decision.decision is ProviderActivationDecision.BLOCKED
    assert ProviderActivationDecisionReason.POLICY_DISABLED in decision.reasons
    assert harness.health.readiness is ExternalProviderReadiness.BLOCKED
    assert not harness.ports.exposes_any


def test_supervised_provider_harness_propagates_unavailable_failure() -> None:
    result = compose_supervised_provider_harness(
        _configuration(
            market=_market_configuration(state=MarketDataProviderHarnessState.UNAVAILABLE),
            include_persistence=False,
            runtime_plan=_runtime_plan(include_persistence=False),
            lifecycles=(_lifecycle(_market_source()),),
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterResilienceUnavailableError)


def test_supervised_provider_harness_rejects_plan_mismatch() -> None:
    with pytest.raises(SupervisedProviderHarnessValidationError):
        _configuration(
            include_persistence=False,
            runtime_plan=_runtime_plan(
                include_persistence=False,
                market_kind=ExternalRuntimeComponentKind.PERSISTENCE_HARNESS,
            ),
            lifecycles=(_lifecycle(_market_source()),),
        )


def test_supervised_provider_harness_boundary_is_structural() -> None:
    result = compose_supervised_provider_harness(_configuration())
    assert isinstance(result, Success)

    boundary: SupervisedProviderHarnessBoundary[str] = result.value

    assert boundary.external_runtime_plan == result.value.external_runtime_plan
    assert isinstance(boundary.ports, SupervisedProviderHarnessPorts)
    assert boundary.ports.exposes_any


def test_public_exports() -> None:
    assert infrastructure.SupervisedProviderHarnessConfiguration is (
        SupervisedProviderHarnessConfiguration
    )
    assert infrastructure.SupervisedProviderHarnessPorts is SupervisedProviderHarnessPorts
    assert infrastructure.SupervisedProviderSecretReferences is (
        SupervisedProviderSecretReferences
    )
    assert infrastructure.SupervisedProviderHarnessError is SupervisedProviderHarnessError
    assert infrastructure.SupervisedProviderHarnessValidationError is (
        SupervisedProviderHarnessValidationError
    )
    assert infrastructure.compose_supervised_provider_harness is (
        compose_supervised_provider_harness
    )
