from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationMode,
    ExternalAdapterConfiguration,
)
from qore.infrastructure.adapter_resilience import (
    AdapterCircuitBreakerSnapshot,
    AdapterCircuitBreakerState,
    AdapterRateLimitPolicy,
    AdapterResiliencePolicy,
    AdapterResilienceUnavailableError,
    AdapterRetryableFailure,
    AdapterRetryDelay,
    AdapterRetryPolicy,
    AdapterThrottledError,
    AdapterTimeoutPolicy,
)
from qore.infrastructure.persistence import (
    LoadPersistenceRequest,
    PersistenceConflictError,
    PersistenceKey,
    PersistenceVersion,
    SavePersistenceRequest,
    StoredRecord,
)
from qore.infrastructure.persistence_backend_harness import (
    PersistenceBackendHarness,
    PersistenceBackendHarnessConfiguration,
    PersistenceBackendHarnessError,
    PersistenceBackendHarnessState,
    PersistenceBackendHarnessValidationError,
    compose_persistence_backend_harness,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
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
from qore.kernel.result import Failure, Success

type Payload = dict[str, list[str]]

_RAW_SECRET = "sk-persistence-secret-value"
_PROVIDER_ID = ProviderId(UUID("f7000000-0000-0000-0000-000000000001"))
_ADAPTER_ID = AdapterId(UUID("f7000000-0000-0000-0000-000000000002"))
_SOURCE_ID = SourceId(UUID("f7000000-0000-0000-0000-000000000003"))
_OTHER_SOURCE_ID = SourceId(UUID("f7000000-0000-0000-0000-000000000004"))
_CORRELATION_ID = CorrelationId(UUID("f7000000-0000-0000-0000-000000000005"))
_STORED_AT = datetime(2026, 8, 7, 13, 0, tzinfo=UTC)
_OBSERVED_AT = datetime(2026, 8, 7, 13, 1, tzinfo=UTC)


def _provider() -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("reference-persistence-backend"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (
                ProviderCapability.HEALTH,
                ProviderCapability.PERSISTENCE_READ,
                ProviderCapability.PERSISTENCE_WRITE,
            )
        ),
    )


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=_SOURCE_ID,
        port_name=PortName("persistence.backend-harness"),
    )


def _other_source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=_OTHER_SOURCE_ID,
        port_name=PortName("persistence.backend-harness"),
    )


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(correlation_id=_CORRELATION_ID)


def _adapter_configuration() -> ExternalAdapterConfiguration:
    return ExternalAdapterConfiguration(
        provider=_provider(),
        source=_source(),
        mode=AdapterConfigurationMode.SIMULATION,
    )


def _resilience_policy(
    *,
    rate_limit: AdapterRateLimitPolicy | None = None,
) -> AdapterResiliencePolicy:
    return AdapterResiliencePolicy(
        provider=_provider(),
        source=_source(),
        timeout=AdapterTimeoutPolicy(AdapterRetryDelay(250)),
        retry=AdapterRetryPolicy(
            max_attempts=2,
            delay_schedule=(AdapterRetryDelay(10),),
            retryable_failures=(
                AdapterRetryableFailure.THROTTLED,
                AdapterRetryableFailure.UNAVAILABLE,
            ),
        ),
        rate_limit=rate_limit,
    )


def _key(value: str = "state/main") -> PersistenceKey:
    return PersistenceKey(namespace="provider-readiness", value=value)


def _payload(label: str = "seed") -> Payload:
    return {"items": [label]}


def _record(
    *,
    key: PersistenceKey | None = None,
    value: Payload | None = None,
    version: PersistenceVersion | None = None,
    source: ExternalSourceDescriptor | None = None,
) -> StoredRecord[Payload]:
    return StoredRecord(
        key=key or _key(),
        version=version or PersistenceVersion(0),
        value=value or _payload(),
        source=source or _source(),
        stored_at=_STORED_AT,
    )


def _configuration(
    *,
    initial_records: tuple[StoredRecord[Payload], ...] | None = None,
    state: PersistenceBackendHarnessState = PersistenceBackendHarnessState.AVAILABLE,
    rate_limit: AdapterRateLimitPolicy | None = None,
    retry_after: AdapterRetryDelay | None = None,
    circuit_breaker: AdapterCircuitBreakerSnapshot | None = None,
) -> PersistenceBackendHarnessConfiguration[Payload]:
    return PersistenceBackendHarnessConfiguration(
        adapter_configuration=_adapter_configuration(),
        metadata=_metadata(),
        resilience_policy=_resilience_policy(rate_limit=rate_limit),
        initial_records=initial_records if initial_records is not None else (_record(),),
        state=state,
        retry_after=retry_after,
        circuit_breaker=circuit_breaker,
    )


def test_persistence_backend_harness_loads_seed_and_preserves_absence() -> None:
    result = compose_persistence_backend_harness(_configuration())

    assert isinstance(result, Success)
    harness = result.value
    assert isinstance(harness, PersistenceBackendHarness)
    assert harness.provider == _provider()
    assert harness.adapter_configuration == _adapter_configuration()

    load_result = harness.ports.load(
        LoadPersistenceRequest(_key()),
        metadata=_metadata(),
    )
    absent_result = harness.ports.load(
        LoadPersistenceRequest(_key("state/missing")),
        metadata=_metadata(),
    )

    assert isinstance(load_result, Success)
    assert load_result.value is not None
    assert load_result.value.version == PersistenceVersion(0)
    assert load_result.value.value == _payload()
    assert isinstance(absent_result, Success)
    assert absent_result.value is None


def test_persistence_backend_harness_health_and_resilience_are_explicit() -> None:
    result = compose_persistence_backend_harness(_configuration())

    assert isinstance(result, Success)
    harness = result.value
    health_result = harness.health(checked_at=_OBSERVED_AT, metadata=_metadata())
    resilience_result = harness.resilience_snapshot(
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )

    assert isinstance(health_result, Success)
    assert health_result.value.availability is PortAvailability.AVAILABLE
    assert health_result.value.message is None
    assert health_result.value.details["provider_name"] == "reference-persistence-backend"
    assert isinstance(resilience_result, Success)
    assert resilience_result.value.policy == _resilience_policy()
    assert resilience_result.value.metadata["backend_state"] == "available"


def test_persistence_backend_harness_preserves_version_conflicts() -> None:
    result = compose_persistence_backend_harness(_configuration())

    assert isinstance(result, Success)
    duplicate_create = result.value.ports.save(
        SavePersistenceRequest(
            key=_key(),
            version=PersistenceVersion(0),
            value=_payload("duplicate"),
            stored_at=_OBSERVED_AT,
            expected_version=None,
        ),
        metadata=_metadata(),
    )
    update = result.value.ports.save(
        SavePersistenceRequest(
            key=_key(),
            version=PersistenceVersion(1),
            value=_payload("updated"),
            stored_at=_OBSERVED_AT,
            expected_version=PersistenceVersion(0),
        ),
        metadata=_metadata(),
    )
    stale_update = result.value.ports.save(
        SavePersistenceRequest(
            key=_key(),
            version=PersistenceVersion(1),
            value=_payload("stale"),
            stored_at=_OBSERVED_AT,
            expected_version=PersistenceVersion(0),
        ),
        metadata=_metadata(),
    )

    assert isinstance(duplicate_create, Failure)
    assert isinstance(duplicate_create.error, PersistenceConflictError)
    assert isinstance(update, Success)
    assert update.value.version == PersistenceVersion(1)
    assert update.value.value == _payload("updated")
    assert isinstance(stale_update, Failure)
    assert isinstance(stale_update.error, PersistenceConflictError)


def test_persistence_backend_harness_defensively_copies_and_isolates_instances() -> None:
    configuration = _configuration(initial_records=(_record(value=_payload("seed")),))
    first_result = compose_persistence_backend_harness(configuration)
    second_result = compose_persistence_backend_harness(configuration)

    assert isinstance(first_result, Success)
    assert isinstance(second_result, Success)
    first_load = first_result.value.ports.load(
        LoadPersistenceRequest(_key()),
        metadata=_metadata(),
    )
    assert isinstance(first_load, Success)
    assert first_load.value is not None
    mutable_payload = cast(Payload, first_load.value.value)
    mutable_payload["items"].append("mutated")

    first_load_again = first_result.value.ports.load(
        LoadPersistenceRequest(_key()),
        metadata=_metadata(),
    )
    second_load = second_result.value.ports.load(
        LoadPersistenceRequest(_key()),
        metadata=_metadata(),
    )

    assert isinstance(first_load_again, Success)
    assert first_load_again.value is not None
    assert first_load_again.value.value == _payload("seed")
    assert isinstance(second_load, Success)
    assert second_load.value is not None
    assert second_load.value.value == _payload("seed")

    first_update = first_result.value.ports.save(
        SavePersistenceRequest(
            key=_key(),
            version=PersistenceVersion(1),
            value=_payload("first-only"),
            stored_at=_OBSERVED_AT,
            expected_version=PersistenceVersion(0),
        ),
        metadata=_metadata(),
    )
    second_load_again = second_result.value.ports.load(
        LoadPersistenceRequest(_key()),
        metadata=_metadata(),
    )

    assert isinstance(first_update, Success)
    assert isinstance(second_load_again, Success)
    assert second_load_again.value is not None
    assert second_load_again.value.value == _payload("seed")


def test_persistence_backend_harness_unavailable_returns_resilience_error() -> None:
    circuit_breaker = AdapterCircuitBreakerSnapshot(
        state=AdapterCircuitBreakerState.OPEN,
        observed_at=_OBSERVED_AT,
        failure_count=2,
        recovery_delay=AdapterRetryDelay(500),
        message="backend temporarily unavailable",
    )

    result = compose_persistence_backend_harness(
        _configuration(
            state=PersistenceBackendHarnessState.UNAVAILABLE,
            circuit_breaker=circuit_breaker,
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterResilienceUnavailableError)
    assert _RAW_SECRET not in str(result.error)
    assert "circuit_breaker=open" in str(result.error)


def test_persistence_backend_harness_throttled_returns_typed_error() -> None:
    rate_limit = AdapterRateLimitPolicy(
        request_limit=1,
        window=AdapterRetryDelay(1000),
    )

    result = compose_persistence_backend_harness(
        _configuration(
            state=PersistenceBackendHarnessState.THROTTLED,
            rate_limit=rate_limit,
            retry_after=AdapterRetryDelay(750),
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterThrottledError)
    assert "retry_after_ms=750" in str(result.error)
    assert _RAW_SECRET not in str(result.error)


def test_persistence_backend_harness_rejects_runtime_type_bypasses() -> None:
    with pytest.raises(PersistenceBackendHarnessValidationError, match="metadata"):
        PersistenceBackendHarnessConfiguration(
            adapter_configuration=_adapter_configuration(),
            metadata=cast(ExternalRequestMetadata, object()),
            resilience_policy=_resilience_policy(),
        )
    with pytest.raises(PersistenceBackendHarnessValidationError, match="source"):
        _configuration(initial_records=(_record(source=_other_source()),))
    with pytest.raises(PersistenceBackendHarnessValidationError, match="version 0"):
        _configuration(
            initial_records=(
                _record(version=PersistenceVersion(1)),
            )
        )
    with pytest.raises(PersistenceBackendHarnessValidationError, match="duplicate"):
        _configuration(initial_records=(_record(), _record()))
    with pytest.raises(PersistenceBackendHarnessValidationError, match="rate-limit"):
        _configuration(state=PersistenceBackendHarnessState.THROTTLED)
    with pytest.raises(PersistenceBackendHarnessValidationError, match="enabled"):
        PersistenceBackendHarnessConfiguration(
            adapter_configuration=ExternalAdapterConfiguration(
                provider=ProviderDescriptor(
                    provider_id=_PROVIDER_ID,
                    provider_name=ProviderName("reference-persistence-backend"),
                    enablement=ProviderEnablement.DISABLED,
                    capabilities=ProviderCapabilitySet(
                        (ProviderCapability.PERSISTENCE_READ,)
                    ),
                ),
                source=_source(),
                mode=AdapterConfigurationMode.DISABLED,
            ),
            metadata=_metadata(),
            resilience_policy=_resilience_policy(),
        )


def test_persistence_backend_harness_public_exports() -> None:
    import qore.infrastructure as infrastructure

    assert infrastructure.PersistenceBackendHarness is PersistenceBackendHarness
    assert (
        infrastructure.PersistenceBackendHarnessConfiguration
        is PersistenceBackendHarnessConfiguration
    )
    assert infrastructure.PersistenceBackendHarnessError is PersistenceBackendHarnessError
    assert issubclass(PersistenceBackendHarnessError, ExternalPortError)
    assert infrastructure.PersistenceBackendHarnessState is PersistenceBackendHarnessState
    assert (
        infrastructure.PersistenceBackendHarnessValidationError
        is PersistenceBackendHarnessValidationError
    )
    assert (
        infrastructure.compose_persistence_backend_harness
        is compose_persistence_backend_harness
    )
