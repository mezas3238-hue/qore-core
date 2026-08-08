from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Protocol

import qore.infrastructure.activation_policy as activation_policy
import qore.infrastructure.adapter_configuration as adapter_configuration
import qore.infrastructure.adapter_lifecycle as adapter_lifecycle
import qore.infrastructure.adapter_observability as adapter_observability
import qore.infrastructure.adapter_resilience as adapter_resilience
import qore.infrastructure.external_health as external_health
import qore.infrastructure.market_data_provider_harness as market_data_provider_harness
import qore.infrastructure.persistence_backend_harness as persistence_backend_harness
import qore.infrastructure.ports as ports
import qore.infrastructure.provider_runtime as provider_runtime
import qore.infrastructure.reference_adapters as reference_adapters
import qore.kernel.result as result_contract


class SupervisedProviderHarnessError(ports.ExternalPortError):
    """Base error for supervised external provider harness contracts."""

    __slots__ = ()


class SupervisedProviderHarnessValidationError(SupervisedProviderHarnessError):
    """Violation of a supervised external provider harness invariant."""

    __slots__ = ()


@dataclasses.dataclass(frozen=True, slots=True)
class SupervisedProviderSecretReferences:
    """Secret references supplied for one supervised provider/source boundary."""

    source: ports.ExternalSourceDescriptor
    references: activation_policy.ProviderActivationSecretReferences = dataclasses.field(
        default_factory=activation_policy.ProviderActivationSecretReferences
    )

    def __post_init__(self) -> None:
        if not isinstance(self.source, ports.ExternalSourceDescriptor):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider secret source must be ExternalSourceDescriptor"
            )
        if not isinstance(
            self.references,
            activation_policy.ProviderActivationSecretReferences,
        ):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider secret references must be "
                "ProviderActivationSecretReferences"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.source.logical_values(),
            self.references.logical_values(),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class SupervisedProviderHarnessConfiguration[PersistenceValueT]:
    """Explicit deterministic configuration for supervised provider harnesses."""

    runtime_plan: provider_runtime.ExternalProviderRuntimePlan
    observed_at: datetime
    metadata: ports.ExternalRequestMetadata
    lifecycles: tuple[adapter_lifecycle.AdapterLifecycleSnapshot, ...]
    market_data_configuration: (
        market_data_provider_harness.ReadOnlyMarketDataProviderHarnessConfiguration
        | None
    ) = None
    persistence_configuration: (
        persistence_backend_harness.PersistenceBackendHarnessConfiguration[
            PersistenceValueT
        ]
        | None
    ) = None
    observability: tuple[adapter_observability.AdapterObservabilitySnapshot, ...] = ()
    secret_references: tuple[SupervisedProviderSecretReferences, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_plan, provider_runtime.ExternalProviderRuntimePlan):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider runtime_plan must be ExternalProviderRuntimePlan"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if not isinstance(self.metadata, ports.ExternalRequestMetadata):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider metadata must be ExternalRequestMetadata"
            )
        if self.market_data_configuration is not None and not isinstance(
            self.market_data_configuration,
            market_data_provider_harness.ReadOnlyMarketDataProviderHarnessConfiguration,
        ):
            raise SupervisedProviderHarnessValidationError(
                "market_data_configuration must be "
                "ReadOnlyMarketDataProviderHarnessConfiguration or None"
            )
        if self.persistence_configuration is not None and not isinstance(
            self.persistence_configuration,
            persistence_backend_harness.PersistenceBackendHarnessConfiguration,
        ):
            raise SupervisedProviderHarnessValidationError(
                "persistence_configuration must be "
                "PersistenceBackendHarnessConfiguration or None"
            )
        sources = _configured_sources(self)
        if not sources:
            raise SupervisedProviderHarnessValidationError(
                "supervised provider harness requires at least one configured harness"
            )
        if len({_source_key(source) for source in sources}) != len(sources):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider harness configured sources must be unique"
            )
        _validate_runtime_plan_bindings(self)
        _validate_lifecycles(self.lifecycles, configured_sources=sources)
        _validate_observability(self.observability, configured_sources=sources)
        _validate_secret_references(self.secret_references, configured_sources=sources)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.runtime_plan.logical_values(),
            self.observed_at.isoformat(),
            self.metadata.logical_values(),
            tuple(lifecycle.logical_values() for lifecycle in self.lifecycles),
            self.market_data_configuration.logical_values()
            if self.market_data_configuration is not None
            else None,
            self.persistence_configuration.logical_values()
            if self.persistence_configuration is not None
            else None,
            tuple(snapshot.logical_values() for snapshot in self.observability),
            tuple(reference.logical_values() for reference in self.secret_references),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class SupervisedProviderHarnessPorts[PersistenceValueT]:
    """Canonical ports exposed only after supervised activation allows them."""

    market_data: reference_adapters.ReferenceMarketDataAdapter | None = None
    persistence: reference_adapters.ReferencePersistenceAdapter[PersistenceValueT] | None = (
        None
    )

    def __post_init__(self) -> None:
        if self.market_data is not None and not isinstance(
            self.market_data,
            reference_adapters.ReferenceMarketDataAdapter,
        ):
            raise SupervisedProviderHarnessValidationError(
                "supervised market_data port must be ReferenceMarketDataAdapter or None"
            )
        if self.persistence is not None and not isinstance(
            self.persistence,
            reference_adapters.ReferencePersistenceAdapter,
        ):
            raise SupervisedProviderHarnessValidationError(
                "supervised persistence port must be ReferencePersistenceAdapter or None"
            )

    @property
    def exposes_any(self) -> bool:
        """Return whether at least one canonical port is exposed."""
        return self.market_data is not None or self.persistence is not None

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.market_data.descriptor.logical_values()
            if self.market_data is not None
            else None,
            self.persistence.descriptor.logical_values()
            if self.persistence is not None
            else None,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class SupervisedProviderHarness[PersistenceValueT]:
    """Deterministic supervised composition over provider readiness harnesses."""

    configuration: SupervisedProviderHarnessConfiguration[PersistenceValueT]
    activation_decisions: tuple[
        activation_policy.ProviderActivationDecisionSnapshot,
        ...,
    ]
    health_inputs: tuple[external_health.ExternalProviderHealthInput, ...]
    health: external_health.ExternalProviderHealthAggregateSnapshot
    market_data_harness: (
        market_data_provider_harness.ReadOnlyMarketDataProviderHarness | None
    ) = None
    persistence_harness: (
        persistence_backend_harness.PersistenceBackendHarness[PersistenceValueT] | None
    ) = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.configuration,
            SupervisedProviderHarnessConfiguration,
        ):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider configuration must be "
                "SupervisedProviderHarnessConfiguration"
            )
        if not isinstance(self.activation_decisions, tuple):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider activation_decisions must be a tuple"
            )
        for decision in self.activation_decisions:
            if not isinstance(
                decision,
                activation_policy.ProviderActivationDecisionSnapshot,
            ):
                raise SupervisedProviderHarnessValidationError(
                    "supervised provider activation decisions must contain "
                    "ProviderActivationDecisionSnapshot"
                )
        if not isinstance(self.health_inputs, tuple):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider health_inputs must be a tuple"
            )
        for health_input in self.health_inputs:
            if not isinstance(health_input, external_health.ExternalProviderHealthInput):
                raise SupervisedProviderHarnessValidationError(
                    "supervised provider health_inputs entries must be "
                    "ExternalProviderHealthInput"
                )
        if not isinstance(
            self.health,
            external_health.ExternalProviderHealthAggregateSnapshot,
        ):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider health must be "
                "ExternalProviderHealthAggregateSnapshot"
            )
        if self.market_data_harness is not None and not isinstance(
            self.market_data_harness,
            market_data_provider_harness.ReadOnlyMarketDataProviderHarness,
        ):
            raise SupervisedProviderHarnessValidationError(
                "market_data_harness must be ReadOnlyMarketDataProviderHarness or None"
            )
        if self.persistence_harness is not None and not isinstance(
            self.persistence_harness,
            persistence_backend_harness.PersistenceBackendHarness,
        ):
            raise SupervisedProviderHarnessValidationError(
                "persistence_harness must be PersistenceBackendHarness or None"
            )

    @property
    def external_runtime_plan(self) -> provider_runtime.ExternalProviderRuntimePlan:
        """Expose the immutable external runtime plan without Core registration."""
        return self.configuration.runtime_plan

    def activation_decision_for(
        self,
        source: ports.ExternalSourceDescriptor,
    ) -> activation_policy.ProviderActivationDecisionSnapshot | None:
        """Return the activation decision for a source, if supervised."""
        if not isinstance(source, ports.ExternalSourceDescriptor):
            raise SupervisedProviderHarnessValidationError(
                "activation decision lookup source must be ExternalSourceDescriptor"
            )
        for decision in self.activation_decisions:
            if decision.policy.source == source:
                return decision
        return None

    def external_health_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[
        external_health.ExternalProviderHealthAggregateSnapshot,
        external_health.ExternalHealthAggregationError,
    ]:
        """Return aggregated external health without monitoring backend side effects."""
        return external_health.aggregate_external_provider_health(
            inputs=self.health_inputs,
            observed_at=observed_at,
            metadata=metadata,
        )

    @property
    def ports(self) -> SupervisedProviderHarnessPorts[PersistenceValueT]:
        """Expose canonical ports only when activation policy allowed them."""
        return SupervisedProviderHarnessPorts(
            market_data=self.market_data_harness.ports
            if self.market_data_harness is not None
            else None,
            persistence=self.persistence_harness.ports
            if self.persistence_harness is not None
            else None,
        )


class SupervisedProviderHarnessBoundary[PersistenceValueT](Protocol):
    """Structural boundary exposing supervised provider readiness state."""

    @property
    def external_runtime_plan(self) -> provider_runtime.ExternalProviderRuntimePlan:
        """Expose the external runtime plan without mutating the Core RuntimePlan."""
        ...

    @property
    def ports(self) -> SupervisedProviderHarnessPorts[PersistenceValueT]:
        """Expose canonical ports permitted by supervised activation policy."""
        ...

    def external_health_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[
        external_health.ExternalProviderHealthAggregateSnapshot,
        external_health.ExternalHealthAggregationError,
    ]:
        """Return aggregated external health without monitoring backend side effects."""
        ...


@dataclasses.dataclass(frozen=True, slots=True)
class _SupervisedProviderTarget:
    source: ports.ExternalSourceDescriptor
    adapter_configuration: adapter_configuration.ExternalAdapterConfiguration
    resilience_policy: adapter_resilience.AdapterResiliencePolicy
    circuit_breaker: adapter_resilience.AdapterCircuitBreakerSnapshot | None
    state: str


def compose_supervised_provider_harness[PersistenceValueT](
    configuration: SupervisedProviderHarnessConfiguration[PersistenceValueT],
) -> result_contract.Result[
    SupervisedProviderHarness[PersistenceValueT],
    ports.ExternalPortError,
]:
    """Compose supervised provider harnesses without live IO or Core registration."""
    if not isinstance(configuration, SupervisedProviderHarnessConfiguration):
        return result_contract.Failure(
            SupervisedProviderHarnessValidationError(
                "configuration must be SupervisedProviderHarnessConfiguration"
            )
        )
    try:
        activation_decisions: list[
            activation_policy.ProviderActivationDecisionSnapshot
        ] = []
        health_inputs: list[external_health.ExternalProviderHealthInput] = []
        market_data_harness = None
        persistence_harness: (
            persistence_backend_harness.PersistenceBackendHarness[PersistenceValueT]
            | None
        ) = None

        if configuration.market_data_configuration is not None:
            market_target = _market_data_target(configuration.market_data_configuration)
            market_decision = _evaluate_target(configuration, market_target)
            if isinstance(market_decision, result_contract.Failure):
                return market_decision
            activation_decisions.append(market_decision.value)
            health_inputs.append(
                external_health.ExternalProviderHealthInput(
                    activation=market_decision.value,
                    metadata={"component": "market-data"},
                )
            )
            if market_decision.value.can_activate:
                market_result = (
                    market_data_provider_harness
                    .compose_read_only_market_data_provider_harness(
                        configuration.market_data_configuration
                    )
                )
                if isinstance(market_result, result_contract.Failure):
                    return market_result
                market_data_harness = market_result.value

        if configuration.persistence_configuration is not None:
            persistence_target = _persistence_target(
                configuration.persistence_configuration
            )
            persistence_decision = _evaluate_target(configuration, persistence_target)
            if isinstance(persistence_decision, result_contract.Failure):
                return persistence_decision
            activation_decisions.append(persistence_decision.value)
            health_inputs.append(
                external_health.ExternalProviderHealthInput(
                    activation=persistence_decision.value,
                    metadata={"component": "persistence"},
                )
            )
            if persistence_decision.value.can_activate:
                persistence_result = (
                    persistence_backend_harness.compose_persistence_backend_harness(
                        configuration.persistence_configuration
                    )
                )
                if isinstance(persistence_result, result_contract.Failure):
                    return persistence_result
                persistence_harness = persistence_result.value

        health_result = external_health.aggregate_external_provider_health(
            inputs=tuple(health_inputs),
            observed_at=configuration.observed_at,
            metadata=configuration.metadata,
        )
        if isinstance(health_result, result_contract.Failure):
            return result_contract.Failure(health_result.error)

        harness = SupervisedProviderHarness(
            configuration=configuration,
            activation_decisions=tuple(activation_decisions),
            health_inputs=tuple(health_inputs),
            health=health_result.value,
            market_data_harness=market_data_harness,
            persistence_harness=persistence_harness,
        )
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)
    return result_contract.Success(harness)


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise SupervisedProviderHarnessValidationError(
            f"supervised provider {field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise SupervisedProviderHarnessValidationError(
            f"supervised provider {field_name} must be timezone-aware"
        )


def _source_key(source: ports.ExternalSourceDescriptor) -> tuple[str, str]:
    return (str(source.adapter_id.value), str(source.source_id.value))


def _configured_sources[PersistenceValueT](
    configuration: SupervisedProviderHarnessConfiguration[PersistenceValueT],
) -> tuple[ports.ExternalSourceDescriptor, ...]:
    sources: list[ports.ExternalSourceDescriptor] = []
    if configuration.market_data_configuration is not None:
        sources.append(configuration.market_data_configuration.source)
    if configuration.persistence_configuration is not None:
        sources.append(configuration.persistence_configuration.source)
    return tuple(sources)


def _validate_runtime_plan_bindings[PersistenceValueT](
    configuration: SupervisedProviderHarnessConfiguration[PersistenceValueT],
) -> None:
    if configuration.market_data_configuration is not None:
        _validate_component_binding(
            runtime_plan=configuration.runtime_plan,
            source=configuration.market_data_configuration.source,
            expected_kind=provider_runtime.ExternalRuntimeComponentKind.MARKET_DATA_HARNESS,
        )
    if configuration.persistence_configuration is not None:
        _validate_component_binding(
            runtime_plan=configuration.runtime_plan,
            source=configuration.persistence_configuration.source,
            expected_kind=provider_runtime.ExternalRuntimeComponentKind.PERSISTENCE_HARNESS,
        )
    configured_keys = {
        _source_key(source) for source in _configured_sources(configuration)
    }
    for component in configuration.runtime_plan.components:
        if component.component_kind in {
            provider_runtime.ExternalRuntimeComponentKind.MARKET_DATA_HARNESS,
            provider_runtime.ExternalRuntimeComponentKind.PERSISTENCE_HARNESS,
        } and _source_key(component.source) not in configured_keys:
            raise SupervisedProviderHarnessValidationError(
                "supervised runtime plan harness components must be configured"
            )


def _validate_component_binding(
    *,
    runtime_plan: provider_runtime.ExternalProviderRuntimePlan,
    source: ports.ExternalSourceDescriptor,
    expected_kind: provider_runtime.ExternalRuntimeComponentKind,
) -> None:
    component = _runtime_component_for_source(runtime_plan, source)
    if component.component_kind is not expected_kind:
        raise SupervisedProviderHarnessValidationError(
            "supervised runtime plan component kind does not match harness"
        )


def _runtime_component_for_source(
    runtime_plan: provider_runtime.ExternalProviderRuntimePlan,
    source: ports.ExternalSourceDescriptor,
) -> provider_runtime.ExternalProviderRuntimeComponent:
    for component in runtime_plan.components:
        if component.source == source:
            return component
    raise SupervisedProviderHarnessValidationError(
        "supervised runtime plan must contain a component for each harness source"
    )


def _validate_lifecycles(
    lifecycles: tuple[adapter_lifecycle.AdapterLifecycleSnapshot, ...],
    *,
    configured_sources: tuple[ports.ExternalSourceDescriptor, ...],
) -> None:
    if not isinstance(lifecycles, tuple):
        raise SupervisedProviderHarnessValidationError(
            "supervised provider lifecycles must be a tuple"
        )
    configured_keys = {_source_key(source) for source in configured_sources}
    seen: set[tuple[str, str]] = set()
    for lifecycle in lifecycles:
        if not isinstance(lifecycle, adapter_lifecycle.AdapterLifecycleSnapshot):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider lifecycles entries must be "
                "AdapterLifecycleSnapshot"
            )
        key = _source_key(lifecycle.descriptor)
        if key not in configured_keys:
            raise SupervisedProviderHarnessValidationError(
                "supervised provider lifecycle source must be configured"
            )
        if key in seen:
            raise SupervisedProviderHarnessValidationError(
                "supervised provider lifecycles must not duplicate sources"
            )
        seen.add(key)
    if configured_keys.difference(seen):
        raise SupervisedProviderHarnessValidationError(
            "supervised provider lifecycle is required for every configured source"
        )


def _validate_observability(
    snapshots: tuple[adapter_observability.AdapterObservabilitySnapshot, ...],
    *,
    configured_sources: tuple[ports.ExternalSourceDescriptor, ...],
) -> None:
    if not isinstance(snapshots, tuple):
        raise SupervisedProviderHarnessValidationError(
            "supervised provider observability must be a tuple"
        )
    configured_keys = {_source_key(source) for source in configured_sources}
    seen: set[tuple[str, str]] = set()
    for snapshot in snapshots:
        if not isinstance(snapshot, adapter_observability.AdapterObservabilitySnapshot):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider observability entries must be "
                "AdapterObservabilitySnapshot"
            )
        key = _source_key(snapshot.source)
        if key not in configured_keys:
            raise SupervisedProviderHarnessValidationError(
                "supervised provider observability source must be configured"
            )
        if key in seen:
            raise SupervisedProviderHarnessValidationError(
                "supervised provider observability must not duplicate sources"
            )
        seen.add(key)


def _validate_secret_references(
    references: tuple[SupervisedProviderSecretReferences, ...],
    *,
    configured_sources: tuple[ports.ExternalSourceDescriptor, ...],
) -> None:
    if not isinstance(references, tuple):
        raise SupervisedProviderHarnessValidationError(
            "supervised provider secret_references must be a tuple"
        )
    configured_keys = {_source_key(source) for source in configured_sources}
    seen: set[tuple[str, str]] = set()
    for reference in references:
        if not isinstance(reference, SupervisedProviderSecretReferences):
            raise SupervisedProviderHarnessValidationError(
                "supervised provider secret_references entries must be "
                "SupervisedProviderSecretReferences"
            )
        key = _source_key(reference.source)
        if key not in configured_keys:
            raise SupervisedProviderHarnessValidationError(
                "supervised provider secret reference source must be configured"
            )
        if key in seen:
            raise SupervisedProviderHarnessValidationError(
                "supervised provider secret references must not duplicate sources"
            )
        seen.add(key)


def _market_data_target(
    configuration: (
        market_data_provider_harness.ReadOnlyMarketDataProviderHarnessConfiguration
    ),
) -> _SupervisedProviderTarget:
    return _SupervisedProviderTarget(
        source=configuration.source,
        adapter_configuration=configuration.adapter_configuration,
        resilience_policy=configuration.resilience_policy,
        circuit_breaker=configuration.circuit_breaker,
        state=configuration.state.value,
    )


def _persistence_target[PersistenceValueT](
    configuration: persistence_backend_harness.PersistenceBackendHarnessConfiguration[
        PersistenceValueT
    ],
) -> _SupervisedProviderTarget:
    return _SupervisedProviderTarget(
        source=configuration.source,
        adapter_configuration=configuration.adapter_configuration,
        resilience_policy=configuration.resilience_policy,
        circuit_breaker=configuration.circuit_breaker,
        state=configuration.state.value,
    )


def _evaluate_target[PersistenceValueT](
    configuration: SupervisedProviderHarnessConfiguration[PersistenceValueT],
    target: _SupervisedProviderTarget,
) -> result_contract.Result[
    activation_policy.ProviderActivationDecisionSnapshot,
    ports.ExternalPortError,
]:
    component = _runtime_component_for_source(configuration.runtime_plan, target.source)
    lifecycle = _lifecycle_for_source(configuration.lifecycles, target.source)
    observability = _observability_for_source(configuration.observability, target.source)
    secrets = _secrets_for_source(configuration.secret_references, target.source)
    try:
        resilience = adapter_resilience.AdapterResilienceSnapshot(
            policy=target.resilience_policy,
            observed_at=configuration.observed_at,
            circuit_breaker=target.circuit_breaker,
            metadata={"harness_state": target.state},
        )
        evaluation = activation_policy.ProviderActivationEvaluation(
            policy=component.activation_policy,
            configuration=target.adapter_configuration,
            lifecycle=lifecycle,
            observability=observability,
            resilience=resilience,
            secrets=secrets,
            evaluated_at=configuration.observed_at,
            metadata=configuration.metadata,
        )
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)

    decision = activation_policy.evaluate_provider_activation_policy(evaluation)
    if isinstance(decision, result_contract.Failure):
        return result_contract.Failure(decision.error)
    return result_contract.Success(decision.value)


def _lifecycle_for_source(
    lifecycles: tuple[adapter_lifecycle.AdapterLifecycleSnapshot, ...],
    source: ports.ExternalSourceDescriptor,
) -> adapter_lifecycle.AdapterLifecycleSnapshot:
    for lifecycle in lifecycles:
        if lifecycle.descriptor == source:
            return lifecycle
    raise SupervisedProviderHarnessValidationError(
        "supervised provider lifecycle is missing for source"
    )


def _observability_for_source(
    snapshots: tuple[adapter_observability.AdapterObservabilitySnapshot, ...],
    source: ports.ExternalSourceDescriptor,
) -> adapter_observability.AdapterObservabilitySnapshot | None:
    for snapshot in snapshots:
        if snapshot.source == source:
            return snapshot
    return None


def _secrets_for_source(
    references: tuple[SupervisedProviderSecretReferences, ...],
    source: ports.ExternalSourceDescriptor,
) -> activation_policy.ProviderActivationSecretReferences:
    for reference in references:
        if reference.source == source:
            return reference.references
    return activation_policy.ProviderActivationSecretReferences()
