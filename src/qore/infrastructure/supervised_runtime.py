from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Protocol

import qore.core.application as core_application
import qore.infrastructure.adapter_lifecycle as adapter_lifecycle
import qore.infrastructure.adapter_observability as adapter_observability
import qore.infrastructure.external_health as external_health
import qore.infrastructure.market_data_provider_harness as market_data_provider_harness
import qore.infrastructure.persistence_backend_harness as persistence_backend_harness
import qore.infrastructure.ports as ports_contract
import qore.infrastructure.provider_runtime as provider_runtime
import qore.infrastructure.supervised_provider_harness as supervised_provider_harness
import qore.kernel.result as result_contract


class SupervisedRuntimeEndToEndError(ports_contract.ExternalPortError):
    """Base error for supervised external runtime end-to-end composition."""

    __slots__ = ()


class SupervisedRuntimeEndToEndValidationError(SupervisedRuntimeEndToEndError):
    """Violation of a supervised external runtime composition invariant."""

    __slots__ = ()


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise SupervisedRuntimeEndToEndValidationError(
            f"supervised runtime {field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise SupervisedRuntimeEndToEndValidationError(
            f"supervised runtime {field_name} must be timezone-aware"
        )


@dataclasses.dataclass(frozen=True, slots=True)
class SupervisedRuntimeEndToEndConfiguration[PersistenceValueT]:
    """Explicit inputs for supervised provider runtime composition above the Core."""

    runtime_plan: provider_runtime.ExternalProviderRuntimePlan
    observed_at: datetime
    metadata: ports_contract.ExternalRequestMetadata
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
    secret_references: tuple[
        supervised_provider_harness.SupervisedProviderSecretReferences,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_plan, provider_runtime.ExternalProviderRuntimePlan):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime runtime_plan must be ExternalProviderRuntimePlan"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if not isinstance(self.metadata, ports_contract.ExternalRequestMetadata):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime metadata must be ExternalRequestMetadata"
            )
        if not isinstance(self.lifecycles, tuple):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime lifecycles must be a tuple"
            )
        for lifecycle in self.lifecycles:
            if not isinstance(lifecycle, adapter_lifecycle.AdapterLifecycleSnapshot):
                raise SupervisedRuntimeEndToEndValidationError(
                    "supervised runtime lifecycles entries must be "
                    "AdapterLifecycleSnapshot"
                )
        if self.market_data_configuration is not None and not isinstance(
            self.market_data_configuration,
            market_data_provider_harness.ReadOnlyMarketDataProviderHarnessConfiguration,
        ):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime market_data_configuration must be "
                "ReadOnlyMarketDataProviderHarnessConfiguration or None"
            )
        if self.persistence_configuration is not None and not isinstance(
            self.persistence_configuration,
            persistence_backend_harness.PersistenceBackendHarnessConfiguration,
        ):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime persistence_configuration must be "
                "PersistenceBackendHarnessConfiguration or None"
            )
        if (
            self.market_data_configuration is None
            and self.persistence_configuration is None
        ):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime requires at least one provider harness configuration"
            )
        if not isinstance(self.observability, tuple):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime observability must be a tuple"
            )
        for snapshot in self.observability:
            if not isinstance(snapshot, adapter_observability.AdapterObservabilitySnapshot):
                raise SupervisedRuntimeEndToEndValidationError(
                    "supervised runtime observability entries must be "
                    "AdapterObservabilitySnapshot"
                )
        if not isinstance(self.secret_references, tuple):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime secret_references must be a tuple"
            )
        for reference in self.secret_references:
            if not isinstance(
                reference,
                supervised_provider_harness.SupervisedProviderSecretReferences,
            ):
                raise SupervisedRuntimeEndToEndValidationError(
                    "supervised runtime secret_references entries must be "
                    "SupervisedProviderSecretReferences"
                )

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
class SupervisedRuntimeEndToEndComposition[PersistenceValueT]:
    """Supervised provider runtime composed explicitly above one Core instance."""

    core: core_application.CoreApplication
    configuration: SupervisedRuntimeEndToEndConfiguration[PersistenceValueT]
    provider_harness: supervised_provider_harness.SupervisedProviderHarness[
        PersistenceValueT
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.core, core_application.CoreApplication):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime core must be CoreApplication"
            )
        if not isinstance(self.configuration, SupervisedRuntimeEndToEndConfiguration):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime configuration must be "
                "SupervisedRuntimeEndToEndConfiguration"
            )
        if not isinstance(
            self.provider_harness,
            supervised_provider_harness.SupervisedProviderHarness,
        ):
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime provider_harness must be SupervisedProviderHarness"
            )
        if self.provider_harness.external_runtime_plan is not self.configuration.runtime_plan:
            raise SupervisedRuntimeEndToEndValidationError(
                "supervised runtime must preserve the exact external runtime plan"
            )

    @property
    def external_runtime_plan(self) -> provider_runtime.ExternalProviderRuntimePlan:
        """Expose the external plan while keeping it outside the Core RuntimePlan."""
        return self.provider_harness.external_runtime_plan

    @property
    def market_data_harness(
        self,
    ) -> market_data_provider_harness.ReadOnlyMarketDataProviderHarness | None:
        """Expose the supervised market-data harness, if activation allowed it."""
        return self.provider_harness.market_data_harness

    @property
    def persistence_harness(
        self,
    ) -> persistence_backend_harness.PersistenceBackendHarness[PersistenceValueT] | None:
        """Expose the supervised persistence harness, if activation allowed it."""
        return self.provider_harness.persistence_harness

    @property
    def ports(
        self,
    ) -> supervised_provider_harness.SupervisedProviderHarnessPorts[PersistenceValueT]:
        """Expose only canonical ports permitted by supervised activation policy."""
        return self.provider_harness.ports

    @property
    def health(self) -> external_health.ExternalProviderHealthAggregateSnapshot:
        """Expose deterministic aggregate external health without a monitoring backend."""
        return self.provider_harness.health

    def external_health_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ports_contract.ExternalRequestMetadata,
    ) -> result_contract.Result[
        external_health.ExternalProviderHealthAggregateSnapshot,
        external_health.ExternalHealthAggregationError,
    ]:
        """Recompute external health from retained supervised inputs without side effects."""
        return self.provider_harness.external_health_snapshot(
            observed_at=observed_at,
            metadata=metadata,
        )


class SupervisedRuntimeEndToEndBoundary[PersistenceValueT](Protocol):
    """Structural application boundary for supervised external provider runtime."""

    @property
    def external_runtime_plan(self) -> provider_runtime.ExternalProviderRuntimePlan:
        """Expose the immutable external runtime plan outside the Core RuntimePlan."""
        ...

    @property
    def ports(
        self,
    ) -> supervised_provider_harness.SupervisedProviderHarnessPorts[PersistenceValueT]:
        """Expose canonical ports allowed by supervised provider policy."""
        ...

    @property
    def health(self) -> external_health.ExternalProviderHealthAggregateSnapshot:
        """Expose aggregate external provider health."""
        ...

    def external_health_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ports_contract.ExternalRequestMetadata,
    ) -> result_contract.Result[
        external_health.ExternalProviderHealthAggregateSnapshot,
        external_health.ExternalHealthAggregationError,
    ]:
        """Return aggregate external health without monitoring side effects."""
        ...


def _validation_failure(
    message: str,
) -> result_contract.Failure[ports_contract.ExternalPortError]:
    return result_contract.Failure(SupervisedRuntimeEndToEndValidationError(message))


def _provider_harness_configuration[PersistenceValueT](
    configuration: SupervisedRuntimeEndToEndConfiguration[PersistenceValueT],
) -> supervised_provider_harness.SupervisedProviderHarnessConfiguration[
    PersistenceValueT
]:
    return supervised_provider_harness.SupervisedProviderHarnessConfiguration(
        runtime_plan=configuration.runtime_plan,
        observed_at=configuration.observed_at,
        metadata=configuration.metadata,
        lifecycles=configuration.lifecycles,
        market_data_configuration=configuration.market_data_configuration,
        persistence_configuration=configuration.persistence_configuration,
        observability=configuration.observability,
        secret_references=configuration.secret_references,
    )


def compose_supervised_runtime_end_to_end[PersistenceValueT](
    core: core_application.CoreApplication,
    configuration: SupervisedRuntimeEndToEndConfiguration[PersistenceValueT],
) -> result_contract.Result[
    SupervisedRuntimeEndToEndComposition[PersistenceValueT],
    ports_contract.ExternalPortError,
]:
    """Compose supervised provider runtime above the Core with no live side effects."""
    if not isinstance(core, core_application.CoreApplication):
        return _validation_failure("core must be CoreApplication")
    if not isinstance(configuration, SupervisedRuntimeEndToEndConfiguration):
        return _validation_failure(
            "configuration must be SupervisedRuntimeEndToEndConfiguration"
        )

    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    try:
        harness_configuration = _provider_harness_configuration(configuration)
    except ports_contract.ExternalPortError as error:
        return result_contract.Failure(error)

    harness_result = supervised_provider_harness.compose_supervised_provider_harness(
        harness_configuration
    )
    if isinstance(harness_result, result_contract.Failure):
        return result_contract.Failure(harness_result.error)

    if core.event_bus is not event_bus:
        return _validation_failure("supervised runtime must preserve the Core EventBus")
    if core.runtime_plan != runtime_plan:
        return _validation_failure("supervised runtime must not mutate the Core RuntimePlan")
    if core.runtime_snapshot() != runtime_snapshot:
        return _validation_failure("supervised runtime must not mutate the Core RuntimeSnapshot")
    if core.runtime_health() != runtime_health:
        return _validation_failure("supervised runtime must not mutate the Core RuntimeHealth")

    try:
        composition = SupervisedRuntimeEndToEndComposition(
            core=core,
            configuration=configuration,
            provider_harness=harness_result.value,
        )
    except ports_contract.ExternalPortError as error:
        return result_contract.Failure(error)
    return result_contract.Success(composition)
