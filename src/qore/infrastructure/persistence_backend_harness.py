from __future__ import annotations

import dataclasses
from datetime import datetime
from enum import StrEnum

import qore.infrastructure.adapter_configuration as adapter_configuration
import qore.infrastructure.adapter_resilience as adapter_resilience
import qore.infrastructure.persistence as persistence
import qore.infrastructure.ports as ports
import qore.infrastructure.providers as providers
import qore.infrastructure.reference_adapters as reference_adapters
import qore.kernel.result as result_contract


class PersistenceBackendHarnessError(ports.ExternalPortError):
    """Base error for persistence backend readiness harness contracts."""

    __slots__ = ()


class PersistenceBackendHarnessValidationError(PersistenceBackendHarnessError):
    """Violation of a persistence backend harness invariant."""

    __slots__ = ()


class PersistenceBackendHarnessState(StrEnum):
    """Closed deterministic persistence backend harness state."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    THROTTLED = "throttled"


@dataclasses.dataclass(frozen=True, slots=True)
class PersistenceBackendHarnessConfiguration[ValueT]:
    """Explicit deterministic inputs for a persistence backend harness."""

    adapter_configuration: adapter_configuration.ExternalAdapterConfiguration
    metadata: ports.ExternalRequestMetadata
    resilience_policy: adapter_resilience.AdapterResiliencePolicy
    initial_records: tuple[persistence.StoredRecord[ValueT], ...] = ()
    state: PersistenceBackendHarnessState = PersistenceBackendHarnessState.AVAILABLE
    retry_after: adapter_resilience.AdapterRetryDelay | None = None
    circuit_breaker: adapter_resilience.AdapterCircuitBreakerSnapshot | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.adapter_configuration,
            adapter_configuration.ExternalAdapterConfiguration,
        ):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend adapter_configuration must be "
                "ExternalAdapterConfiguration"
            )
        if not isinstance(self.metadata, ports.ExternalRequestMetadata):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend metadata must be ExternalRequestMetadata"
            )
        if not isinstance(
            self.resilience_policy,
            adapter_resilience.AdapterResiliencePolicy,
        ):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend resilience_policy must be AdapterResiliencePolicy"
            )
        if not isinstance(self.state, PersistenceBackendHarnessState):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend state must be PersistenceBackendHarnessState"
            )
        if self.retry_after is not None and not isinstance(
            self.retry_after,
            adapter_resilience.AdapterRetryDelay,
        ):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend retry_after must be AdapterRetryDelay or None"
            )
        if self.circuit_breaker is not None and not isinstance(
            self.circuit_breaker,
            adapter_resilience.AdapterCircuitBreakerSnapshot,
        ):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend circuit_breaker must be "
                "AdapterCircuitBreakerSnapshot or None"
            )
        if not self.adapter_configuration.is_enabled:
            raise PersistenceBackendHarnessValidationError(
                "persistence backend adapter configuration must be enabled"
            )
        if self.adapter_configuration.provider != self.resilience_policy.provider:
            raise PersistenceBackendHarnessValidationError(
                "persistence backend resilience provider must match adapter configuration"
            )
        if self.adapter_configuration.source != self.resilience_policy.source:
            raise PersistenceBackendHarnessValidationError(
                "persistence backend resilience source must match adapter configuration"
            )
        source_name = self.adapter_configuration.source.port_name.value
        if source_name != "persistence" and not source_name.startswith("persistence."):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend source must use the persistence namespace"
            )
        capabilities = self.adapter_configuration.provider.capabilities
        if not (
            capabilities.supports(providers.ProviderCapability.PERSISTENCE_READ)
            or capabilities.supports(providers.ProviderCapability.PERSISTENCE_WRITE)
        ):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend requires persistence read or write capability"
            )
        if (
            self.adapter_configuration.mode
            is adapter_configuration.AdapterConfigurationMode.DISABLED
        ):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend adapter mode must not be disabled"
            )
        if (
            self.state is PersistenceBackendHarnessState.THROTTLED
            and self.resilience_policy.rate_limit is None
        ):
            raise PersistenceBackendHarnessValidationError(
                "throttled persistence backend requires a rate-limit policy"
            )
        _validate_initial_records(self.initial_records, source=self.source)

    @property
    def provider(self) -> providers.ProviderDescriptor:
        """Expose provider governance from the explicit adapter configuration."""
        return self.adapter_configuration.provider

    @property
    def source(self) -> ports.ExternalSourceDescriptor:
        """Expose the persistence source from the explicit adapter configuration."""
        return self.adapter_configuration.source

    def logical_values(self) -> tuple[object, ...]:
        """Return deterministic harness inputs without exposing stored values."""
        return (
            self.adapter_configuration.logical_values(),
            self.metadata.logical_values(),
            self.resilience_policy.logical_values(),
            tuple(
                (
                    record.key.logical_values(),
                    record.version.value,
                    record.source.logical_values(),
                    record.stored_at.isoformat(),
                )
                for record in self.initial_records
            ),
            self.state.value,
            self.retry_after.logical_values()
            if self.retry_after is not None
            else None,
            self.circuit_breaker.logical_values()
            if self.circuit_breaker is not None
            else None,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class PersistenceBackendHarness[ValueT]:
    """Composed readiness harness exposing a canonical PersistencePort."""

    configuration: PersistenceBackendHarnessConfiguration[ValueT]
    persistence: reference_adapters.ReferencePersistenceAdapter[ValueT]

    def __post_init__(self) -> None:
        if not isinstance(
            self.configuration,
            PersistenceBackendHarnessConfiguration,
        ):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend configuration must be "
                "PersistenceBackendHarnessConfiguration"
            )
        if not isinstance(
            self.persistence,
            reference_adapters.ReferencePersistenceAdapter,
        ):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend port must be ReferencePersistenceAdapter"
            )
        if self.persistence.descriptor != self.configuration.source:
            raise PersistenceBackendHarnessValidationError(
                "persistence backend descriptor must match configuration source"
            )

    @property
    def provider(self) -> providers.ProviderDescriptor:
        """Expose provider governance from configuration."""
        return self.configuration.provider

    @property
    def adapter_configuration(
        self,
    ) -> adapter_configuration.ExternalAdapterConfiguration:
        """Expose immutable adapter configuration."""
        return self.configuration.adapter_configuration

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[ports.ExternalHealth, ports.ExternalPortError]:
        """Return explicit backend health without backend IO."""
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, result_contract.Failure):
            return metadata_result
        try:
            health = ports.ExternalHealth(
                descriptor=self.configuration.source,
                availability=_availability_for_state(self.configuration.state),
                checked_at=checked_at,
                message=_message_for_state(self.configuration.state),
                details={
                    "backend_state": self.configuration.state.value,
                    "provider_name": self.provider.provider_name.value,
                },
            )
        except ports.ExternalPortError as error:
            return result_contract.Failure(error)
        return result_contract.Success(health)

    def resilience_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[
        adapter_resilience.AdapterResilienceSnapshot,
        adapter_resilience.AdapterResilienceError,
    ]:
        """Return a typed resilience snapshot without executing backend behavior."""
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, result_contract.Failure):
            return result_contract.Failure(
                adapter_resilience.AdapterResilienceValidationError(
                    str(metadata_result.error)
                )
            )
        try:
            snapshot = adapter_resilience.AdapterResilienceSnapshot(
                policy=self.configuration.resilience_policy,
                observed_at=observed_at,
                circuit_breaker=self.configuration.circuit_breaker,
                metadata={"backend_state": self.configuration.state.value},
            )
        except adapter_resilience.AdapterResilienceError as error:
            return result_contract.Failure(error)
        return result_contract.Success(snapshot)

    @property
    def ports(self) -> reference_adapters.ReferencePersistenceAdapter[ValueT]:
        """Expose canonical persistence through the approved port contract."""
        return self.persistence


def compose_persistence_backend_harness[ValueT](
    configuration: PersistenceBackendHarnessConfiguration[ValueT],
) -> result_contract.Result[
    PersistenceBackendHarness[ValueT],
    ports.ExternalPortError,
]:
    """Compose explicit backend config into a canonical PersistencePort harness."""
    if not isinstance(configuration, PersistenceBackendHarnessConfiguration):
        return result_contract.Failure(
            PersistenceBackendHarnessValidationError(
                "configuration must be PersistenceBackendHarnessConfiguration"
            )
        )
    state_error = _error_for_state(configuration)
    if state_error is not None:
        return result_contract.Failure(state_error)

    try:
        backend: reference_adapters.ReferencePersistenceAdapter[ValueT] = (
            reference_adapters.ReferencePersistenceAdapter(configuration.source)
        )
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)

    seed_result = _seed_records(backend, configuration)
    if isinstance(seed_result, result_contract.Failure):
        return seed_result

    try:
        harness = PersistenceBackendHarness(
            configuration=configuration,
            persistence=backend,
        )
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)
    return result_contract.Success(harness)


def _validate_metadata(
    metadata: ports.ExternalRequestMetadata,
) -> result_contract.Result[None, ports.ExternalPortError]:
    if not isinstance(metadata, ports.ExternalRequestMetadata):
        return result_contract.Failure(
            PersistenceBackendHarnessValidationError(
                "metadata must be ExternalRequestMetadata"
            )
        )
    return result_contract.Success(None)


def _validate_initial_records[ValueT](
    records: tuple[persistence.StoredRecord[ValueT], ...],
    *,
    source: ports.ExternalSourceDescriptor,
) -> None:
    if not isinstance(records, tuple):
        raise PersistenceBackendHarnessValidationError(
            "persistence backend initial_records must be a tuple"
        )
    seen: set[persistence.PersistenceKey] = set()
    for record in records:
        if not isinstance(record, persistence.StoredRecord):
            raise PersistenceBackendHarnessValidationError(
                "persistence backend initial_records entries must be StoredRecord"
            )
        if record.source != source:
            raise PersistenceBackendHarnessValidationError(
                "persistence backend initial record source must match configuration"
            )
        if record.version.value != 0:
            raise PersistenceBackendHarnessValidationError(
                "persistence backend initial records must use version 0"
            )
        if record.key in seen:
            raise PersistenceBackendHarnessValidationError(
                "persistence backend initial records must not duplicate keys"
            )
        seen.add(record.key)


def _seed_records[ValueT](
    backend: reference_adapters.ReferencePersistenceAdapter[ValueT],
    configuration: PersistenceBackendHarnessConfiguration[ValueT],
) -> result_contract.Result[None, ports.ExternalPortError]:
    for record in configuration.initial_records:
        request = persistence.SavePersistenceRequest(
            key=record.key,
            version=record.version,
            value=record.value,
            stored_at=record.stored_at,
            expected_version=None,
        )
        save_result = backend.save(request, metadata=configuration.metadata)
        if isinstance(save_result, result_contract.Failure):
            return save_result
    return result_contract.Success(None)


def _error_for_state[ValueT](
    configuration: PersistenceBackendHarnessConfiguration[ValueT],
) -> ports.ExternalPortError | None:
    if configuration.state is PersistenceBackendHarnessState.AVAILABLE:
        return None
    if configuration.state is PersistenceBackendHarnessState.UNAVAILABLE:
        return adapter_resilience.AdapterResilienceUnavailableError(
            source=configuration.source,
            circuit_breaker=configuration.circuit_breaker,
        )
    if configuration.state is PersistenceBackendHarnessState.THROTTLED:
        rate_limit = configuration.resilience_policy.rate_limit
        if rate_limit is None:
            return PersistenceBackendHarnessValidationError(
                "throttled persistence backend requires a rate-limit policy"
            )
        return adapter_resilience.AdapterThrottledError(
            source=configuration.source,
            policy=rate_limit,
            retry_after=configuration.retry_after,
        )
    return PersistenceBackendHarnessValidationError(
        "unknown persistence backend harness state"
    )


def _availability_for_state(
    state: PersistenceBackendHarnessState,
) -> ports.PortAvailability:
    if state is PersistenceBackendHarnessState.AVAILABLE:
        return ports.PortAvailability.AVAILABLE
    if state is PersistenceBackendHarnessState.THROTTLED:
        return ports.PortAvailability.DEGRADED
    return ports.PortAvailability.UNAVAILABLE


def _message_for_state(state: PersistenceBackendHarnessState) -> str | None:
    if state is PersistenceBackendHarnessState.AVAILABLE:
        return None
    if state is PersistenceBackendHarnessState.THROTTLED:
        return "persistence backend harness is throttled"
    return "persistence backend harness is unavailable"
