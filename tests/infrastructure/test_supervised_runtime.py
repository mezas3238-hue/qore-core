from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import qore.infrastructure as infrastructure
from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CorrelationId
from qore.governance.composition import compose_functional_governance
from qore.infrastructure.activation_policy import (
    ProviderActivationDecision,
    ProviderActivationMode,
    ProviderActivationPolicy,
    ProviderActivationPolicyValidationError,
)
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationMode,
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
from qore.infrastructure.external_health import (
    ExternalProviderHealthAggregateSnapshot,
    ExternalProviderReadiness,
)
from qore.infrastructure.ingestion import ExternalQuotePayload
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    QuoteRequest,
)
from qore.infrastructure.market_data_provider_harness import (
    MarketDataProviderHarnessState,
    MarketDataProviderQuoteIngestion,
    ReadOnlyMarketDataProviderHarnessConfiguration,
)
from qore.infrastructure.persistence import LoadPersistenceRequest, PersistenceKey
from qore.infrastructure.persistence_backend_harness import (
    PersistenceBackendHarnessConfiguration,
)
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
    SupervisedProviderHarnessValidationError,
)
from qore.infrastructure.supervised_runtime import (
    SupervisedRuntimeEndToEndBoundary,
    SupervisedRuntimeEndToEndComposition,
    SupervisedRuntimeEndToEndConfiguration,
    SupervisedRuntimeEndToEndError,
    SupervisedRuntimeEndToEndValidationError,
    compose_supervised_runtime_end_to_end,
)
from qore.kernel.result import Failure, Result, Success
from qore.specialized_governance.composition import compose_specialized_governance

_NOW = datetime(2026, 8, 8, 3, 30, tzinfo=UTC)
_DECLARED_AT = _NOW - timedelta(minutes=4)
_CONFIGURED_AT = _NOW - timedelta(minutes=3)
_INITIALIZED_AT = _NOW - timedelta(minutes=2)
_STARTED_AT = _NOW - timedelta(minutes=1)
_PROVIDER_ID = ProviderId(UUID("d1000000-0000-0000-0000-000000000001"))
_OTHER_PROVIDER_ID = ProviderId(UUID("d1000000-0000-0000-0000-000000000002"))
_MARKET_ADAPTER_ID = AdapterId(UUID("d1000000-0000-0000-0000-000000000003"))
_MARKET_SOURCE_ID = SourceId(UUID("d1000000-0000-0000-0000-000000000004"))
_PERSISTENCE_ADAPTER_ID = AdapterId(UUID("d1000000-0000-0000-0000-000000000005"))
_PERSISTENCE_SOURCE_ID = SourceId(UUID("d1000000-0000-0000-0000-000000000006"))
_CORRELATION_ID = CorrelationId(UUID("d1000000-0000-0000-0000-000000000007"))
_QUOTE_ID = MarketDataSnapshotId(UUID("d1000000-0000-0000-0000-000000000008"))
_ACTOR = AdapterLifecycleActor("runtime-supervisor")


def _core(name: str = "qore-supervised-runtime-e2e") -> CoreApplication:
    result = bootstrap(Configuration(application_name=name))
    assert isinstance(result, Success)
    return result.value


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(correlation_id=_CORRELATION_ID)


def _provider(*, alternate: bool = False) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_OTHER_PROVIDER_ID if alternate else _PROVIDER_ID,
        provider_name=ProviderName(
            "supervised-runtime-other" if alternate else "supervised-runtime"
        ),
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
        port_name=PortName("market-data.supervised-runtime"),
    )


def _persistence_source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_PERSISTENCE_ADAPTER_ID,
        source_id=_PERSISTENCE_SOURCE_ID,
        port_name=PortName("persistence.supervised-runtime"),
    )


def _adapter_configuration(source: ExternalSourceDescriptor) -> ExternalAdapterConfiguration:
    return ExternalAdapterConfiguration(
        provider=_provider(),
        source=source,
        mode=AdapterConfigurationMode.READ_ONLY,
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
    provider: ProviderDescriptor | None = None,
    mode: ProviderActivationMode = ProviderActivationMode.READ_ONLY,
    capability: ProviderCapability,
) -> ProviderActivationPolicy:
    resolved_provider = provider or _provider()
    return ProviderActivationPolicy(
        provider=resolved_provider,
        source=source,
        mode=mode,
        required_capabilities=(capability,),
    )


def _runtime_plan(
    *,
    include_market: bool = True,
    include_persistence: bool = True,
    market_policy_mode: ProviderActivationMode = ProviderActivationMode.READ_ONLY,
    market_provider: ProviderDescriptor | None = None,
) -> ExternalProviderRuntimePlan:
    components: list[ExternalProviderRuntimeComponent] = []
    if include_market:
        provider = market_provider or _provider()
        components.append(
            ExternalProviderRuntimeComponent(
                component_id=ExternalRuntimeComponentId("market-data"),
                component_kind=ExternalRuntimeComponentKind.MARKET_DATA_HARNESS,
                provider=provider,
                source=_market_source(),
                activation_policy=_activation_policy(
                    _market_source(),
                    provider=provider,
                    mode=market_policy_mode,
                    capability=ProviderCapability.MARKET_DATA_READ,
                ),
            )
        )
    if include_persistence:
        dependencies = (
            (ExternalRuntimeComponentId("market-data"),) if include_market else ()
        )
        components.append(
            ExternalProviderRuntimeComponent(
                component_id=ExternalRuntimeComponentId("persistence"),
                component_kind=ExternalRuntimeComponentKind.PERSISTENCE_HARNESS,
                provider=_provider(),
                source=_persistence_source(),
                activation_policy=_activation_policy(
                    _persistence_source(),
                    capability=ProviderCapability.PERSISTENCE_READ,
                ),
                depends_on=dependencies,
            )
        )
    result = build_external_provider_runtime_plan(components=tuple(components))
    assert isinstance(result, Success)
    return result.value


def _market_configuration(
    *,
    state: MarketDataProviderHarnessState = MarketDataProviderHarnessState.AVAILABLE,
) -> ReadOnlyMarketDataProviderHarnessConfiguration:
    request = QuoteRequest(Instrument("EURUSD"))
    return ReadOnlyMarketDataProviderHarnessConfiguration(
        adapter_configuration=_adapter_configuration(_market_source()),
        metadata=_metadata(),
        resilience_policy=_resilience_policy(_market_source()),
        quote_payloads=(
            ExternalQuotePayload(
                source=_market_source(),
                instrument="eurusd",
                observed_at=_NOW,
                bid="1.1000",
                ask="1.1002",
            ),
        ),
        quote_ingestions=(
            MarketDataProviderQuoteIngestion(
                request=request,
                snapshot_id=_QUOTE_ID,
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


def _lifecycle(source: ExternalSourceDescriptor) -> AdapterLifecycleSnapshot:
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
    return started.value


def _observability(readiness: AdapterReadiness) -> AdapterObservabilitySnapshot:
    message = None
    if readiness is AdapterReadiness.DEGRADED:
        message = "supervised runtime degraded"
    if readiness is AdapterReadiness.UNAVAILABLE:
        message = "supervised runtime unavailable"
    return AdapterObservabilitySnapshot(
        provider=_provider(),
        source=_market_source(),
        readiness=readiness,
        observed_at=_NOW,
        message=message,
    )


def _configuration(
    *,
    include_persistence: bool = True,
    runtime_plan: ExternalProviderRuntimePlan | None = None,
    lifecycles: tuple[AdapterLifecycleSnapshot, ...] | None = None,
    observability: tuple[AdapterObservabilitySnapshot, ...] = (),
    market: ReadOnlyMarketDataProviderHarnessConfiguration | None = None,
) -> SupervisedRuntimeEndToEndConfiguration[str]:
    market_configuration = market or _market_configuration()
    persistence_configuration = _persistence_configuration() if include_persistence else None
    resolved_lifecycles = lifecycles
    if resolved_lifecycles is None:
        lifecycle_values = [_lifecycle(_market_source())]
        if include_persistence:
            lifecycle_values.append(_lifecycle(_persistence_source()))
        resolved_lifecycles = tuple(lifecycle_values)
    return SupervisedRuntimeEndToEndConfiguration(
        runtime_plan=runtime_plan
        or _runtime_plan(include_persistence=include_persistence),
        observed_at=_NOW,
        metadata=_metadata(),
        lifecycles=resolved_lifecycles,
        market_data_configuration=market_configuration,
        persistence_configuration=persistence_configuration,
        observability=observability,
    )


def test_supervised_runtime_e2e_composes_allowed_market_data_and_persistence() -> None:
    core = _core()
    before_event_bus = core.event_bus
    before_snapshot = core.runtime_snapshot()
    before_health = core.runtime_health()
    before_plan = core.runtime_plan
    external_plan = _runtime_plan()
    result: Result[
        SupervisedRuntimeEndToEndComposition[str],
        ExternalPortError,
    ] = compose_supervised_runtime_end_to_end(
        core,
        _configuration(runtime_plan=external_plan),
    )

    assert isinstance(result, Success)
    composition = result.value
    assert composition.core is core
    assert composition.external_runtime_plan is external_plan
    assert composition.provider_harness.external_runtime_plan is external_plan
    assert composition.market_data_harness is not None
    assert composition.persistence_harness is not None
    assert composition.ports.market_data is not None
    assert composition.ports.persistence is not None
    assert composition.health.readiness is ExternalProviderReadiness.READY
    assert composition.external_runtime_plan.activation_order == (
        ExternalRuntimeComponentId("market-data"),
        ExternalRuntimeComponentId("persistence"),
    )

    quote = composition.ports.market_data.read_quote(
        QuoteRequest(Instrument("EURUSD")),
        metadata=_metadata(),
    )
    missing = composition.ports.persistence.load(
        LoadPersistenceRequest(PersistenceKey("supervised-runtime", "missing")),
        metadata=_metadata(),
    )
    health = composition.external_health_snapshot(
        observed_at=_NOW,
        metadata=_metadata(),
    )

    assert isinstance(quote, Success)
    assert quote.value.snapshot_id == _QUOTE_ID
    assert isinstance(missing, Success)
    assert missing.value is None
    assert isinstance(health, Success)
    assert health.value.logical_values() == composition.health.logical_values()
    assert core.event_bus is before_event_bus
    assert core.runtime_snapshot() == before_snapshot
    assert core.runtime_health() == before_health
    assert core.runtime_plan == before_plan
    assert len(core.runtime_plan.components) == 1
    assert core.runtime_plan.components[0].component is core.engine


def test_supervised_runtime_e2e_blocked_policy_does_not_expose_ports() -> None:
    runtime_plan = _runtime_plan(
        include_persistence=False,
        market_policy_mode=ProviderActivationMode.DISABLED,
    )
    result = compose_supervised_runtime_end_to_end(
        _core("qore-supervised-runtime-blocked"),
        _configuration(include_persistence=False, runtime_plan=runtime_plan),
    )

    assert isinstance(result, Success)
    decision = result.value.provider_harness.activation_decision_for(_market_source())
    assert decision is not None
    assert decision.decision is ProviderActivationDecision.BLOCKED
    assert result.value.health.readiness is ExternalProviderReadiness.BLOCKED
    assert not result.value.ports.exposes_any


def test_supervised_runtime_e2e_degraded_health_does_not_expose_ports() -> None:
    result = compose_supervised_runtime_end_to_end(
        _core("qore-supervised-runtime-degraded"),
        _configuration(
            include_persistence=False,
            runtime_plan=_runtime_plan(include_persistence=False),
            observability=(_observability(AdapterReadiness.DEGRADED),),
        ),
    )

    assert isinstance(result, Success)
    assert result.value.health.readiness is ExternalProviderReadiness.DEGRADED
    assert not result.value.ports.exposes_any


def test_supervised_runtime_e2e_unavailable_signal_is_reflected_in_health() -> None:
    result = compose_supervised_runtime_end_to_end(
        _core("qore-supervised-runtime-unavailable-health"),
        _configuration(
            include_persistence=False,
            runtime_plan=_runtime_plan(include_persistence=False),
            observability=(_observability(AdapterReadiness.UNAVAILABLE),),
        ),
    )

    assert isinstance(result, Success)
    assert isinstance(result.value.health, ExternalProviderHealthAggregateSnapshot)
    assert result.value.health.readiness is ExternalProviderReadiness.BLOCKED
    assert any(
        issue.code == "observability.unavailable"
        for issue in result.value.health.issues
    )
    assert not result.value.ports.exposes_any


def test_supervised_runtime_e2e_identity_mismatch_returns_typed_failure() -> None:
    result = compose_supervised_runtime_end_to_end(
        _core("qore-supervised-runtime-identity"),
        _configuration(
            include_persistence=False,
            runtime_plan=_runtime_plan(
                include_persistence=False,
                market_provider=_provider(alternate=True),
            ),
        ),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProviderActivationPolicyValidationError)
    assert "identities must match" in str(result.error)


def test_supervised_runtime_e2e_missing_lifecycle_returns_typed_failure() -> None:
    result = compose_supervised_runtime_end_to_end(
        _core("qore-supervised-runtime-missing-lifecycle"),
        _configuration(
            include_persistence=False,
            runtime_plan=_runtime_plan(include_persistence=False),
            lifecycles=(),
        ),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, SupervisedProviderHarnessValidationError)
    assert "lifecycle is required" in str(result.error)


def test_supervised_runtime_e2e_propagates_unavailable_harness_failure() -> None:
    result = compose_supervised_runtime_end_to_end(
        _core("qore-supervised-runtime-harness-failure"),
        _configuration(
            include_persistence=False,
            runtime_plan=_runtime_plan(include_persistence=False),
            market=_market_configuration(state=MarketDataProviderHarnessState.UNAVAILABLE),
        ),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterResilienceUnavailableError)


def test_supervised_runtime_e2e_rejects_runtime_bypasses() -> None:
    invalid_core: Result[
        SupervisedRuntimeEndToEndComposition[str],
        ExternalPortError,
    ] = compose_supervised_runtime_end_to_end(
        cast(CoreApplication, object()),
        _configuration(),
    )
    invalid_configuration: Result[
        SupervisedRuntimeEndToEndComposition[str],
        ExternalPortError,
    ] = compose_supervised_runtime_end_to_end(
        _core("qore-supervised-runtime-invalid-config"),
        cast(SupervisedRuntimeEndToEndConfiguration[str], object()),
    )

    assert isinstance(invalid_core, Failure)
    assert isinstance(invalid_core.error, SupervisedRuntimeEndToEndValidationError)
    assert isinstance(invalid_configuration, Failure)
    assert isinstance(
        invalid_configuration.error,
        SupervisedRuntimeEndToEndValidationError,
    )


def test_supervised_runtime_boundary_is_structural() -> None:
    result = compose_supervised_runtime_end_to_end(_core(), _configuration())
    assert isinstance(result, Success)

    boundary: SupervisedRuntimeEndToEndBoundary[str] = result.value

    assert boundary.external_runtime_plan is result.value.external_runtime_plan
    assert boundary.health is result.value.health
    assert boundary.ports.exposes_any


def test_functional_and_specialized_governance_still_compose_without_supervised_runtime() -> None:
    functional = compose_functional_governance(
        Configuration(application_name="qore-functional-after-supervised-runtime")
    )
    specialized = compose_specialized_governance(
        Configuration(application_name="qore-specialized-after-supervised-runtime")
    )

    assert isinstance(functional, Success)
    assert isinstance(specialized, Success)
    assert len(functional.value.core.runtime_plan.components) == 1
    assert len(specialized.value.core.runtime_plan.components) == 1


def test_supervised_runtime_public_exports() -> None:
    assert infrastructure.SupervisedRuntimeEndToEndConfiguration is (
        SupervisedRuntimeEndToEndConfiguration
    )
    assert infrastructure.SupervisedRuntimeEndToEndComposition is (
        SupervisedRuntimeEndToEndComposition
    )
    assert infrastructure.SupervisedRuntimeEndToEndBoundary is (
        SupervisedRuntimeEndToEndBoundary
    )
    assert infrastructure.SupervisedRuntimeEndToEndError is SupervisedRuntimeEndToEndError
    assert infrastructure.SupervisedRuntimeEndToEndValidationError is (
        SupervisedRuntimeEndToEndValidationError
    )
    assert infrastructure.compose_supervised_runtime_end_to_end is (
        compose_supervised_runtime_end_to_end
    )
