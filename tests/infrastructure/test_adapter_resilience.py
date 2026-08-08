from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId, DomainMetadataValue
from qore.infrastructure.adapter_resilience import (
    AdapterCircuitBreakerSnapshot,
    AdapterCircuitBreakerState,
    AdapterRateLimitPolicy,
    AdapterResilienceBoundary,
    AdapterResilienceError,
    AdapterResiliencePolicy,
    AdapterResilienceSnapshot,
    AdapterResilienceUnavailableError,
    AdapterResilienceValidationError,
    AdapterRetryDelay,
    AdapterRetryPolicy,
    AdapterRetryableFailure,
    AdapterThrottledError,
    AdapterTimeoutError,
    AdapterTimeoutPolicy,
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
from qore.kernel.result import Success

_RAW_SECRET = "sk-super-secret-value"
_OBSERVED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_PROVIDER_ID = ProviderId(UUID("f6000000-0000-0000-0000-000000000001"))
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f6000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("f6000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.reference"),
)


class _ResilienceBoundary:
    def __init__(self, snapshot: AdapterResilienceSnapshot) -> None:
        self._snapshot = snapshot

    @property
    def policy(self) -> AdapterResiliencePolicy:
        return self._snapshot.policy

    def resilience_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Success[AdapterResilienceSnapshot]:
        assert observed_at == _OBSERVED_AT
        assert isinstance(metadata, ExternalRequestMetadata)
        return Success(self._snapshot)


def _provider() -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("reference-provider"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (
                ProviderCapability.MARKET_DATA_READ,
                ProviderCapability.HEALTH,
            )
        ),
    )


def _request_metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=CorrelationId(UUID("f6000000-0000-0000-0000-000000000004"))
    )


def _retry_policy() -> AdapterRetryPolicy:
    return AdapterRetryPolicy(
        max_attempts=3,
        delay_schedule=(
            AdapterRetryDelay(100),
            AdapterRetryDelay(250),
        ),
        retryable_failures=(
            AdapterRetryableFailure.TIMEOUT,
            AdapterRetryableFailure.THROTTLED,
            AdapterRetryableFailure.TIMEOUT,
        ),
    )


def _policy() -> AdapterResiliencePolicy:
    return AdapterResiliencePolicy(
        provider=_provider(),
        source=_SOURCE,
        timeout=AdapterTimeoutPolicy(AdapterRetryDelay(1_500)),
        retry=_retry_policy(),
        rate_limit=AdapterRateLimitPolicy(
            request_limit=10,
            window=AdapterRetryDelay(1_000),
            burst_capacity=5,
        ),
    )


def test_resilience_policy_is_canonical_and_declarative() -> None:
    policy = _policy()

    assert policy.retry.retries_enabled is True
    assert policy.retry.logical_values() == (
        3,
        ((100,), (250,)),
        ("throttled", "timeout"),
    )
    assert policy.timeout.logical_values() == (1_500,)
    assert policy.rate_limit is not None
    assert policy.rate_limit.logical_values() == (10, (1_000,), 5)
    assert policy.logical_values()[0] == _provider().logical_values()
    assert policy.logical_values()[1] == _SOURCE.logical_values()


def test_resilience_snapshot_is_deterministic_and_observable() -> None:
    circuit_breaker = AdapterCircuitBreakerSnapshot(
        state=AdapterCircuitBreakerState.OPEN,
        observed_at=_OBSERVED_AT,
        failure_count=2,
        recovery_delay=AdapterRetryDelay(5_000),
        message="provider temporarily unavailable",
        metadata={"reason": "upstream-maintenance"},
    )
    snapshot = AdapterResilienceSnapshot(
        policy=_policy(),
        observed_at=_OBSERVED_AT,
        circuit_breaker=circuit_breaker,
        metadata={"region": "ny"},
    )

    assert circuit_breaker.logical_values() == (
        "open",
        _OBSERVED_AT.isoformat(),
        2,
        (5_000,),
        "provider temporarily unavailable",
        (("reason", "upstream-maintenance"),),
    )
    assert snapshot.logical_values() == (
        _policy().logical_values(),
        _OBSERVED_AT.isoformat(),
        circuit_breaker.logical_values(),
        (("region", "ny"),),
    )
    assert _RAW_SECRET not in repr(snapshot.logical_values())


def test_timeout_retry_and_rate_limit_validation() -> None:
    with pytest.raises(AdapterResilienceValidationError, match="integer"):
        AdapterRetryDelay(cast(int, True))
    with pytest.raises(AdapterResilienceValidationError, match="non-negative"):
        AdapterRetryDelay(-1)
    with pytest.raises(AdapterResilienceValidationError, match="positive"):
        AdapterTimeoutPolicy(AdapterRetryDelay(0))
    with pytest.raises(AdapterResilienceValidationError, match="at least one"):
        AdapterRetryPolicy(max_attempts=0)
    with pytest.raises(AdapterResilienceValidationError, match="one delay per retry"):
        AdapterRetryPolicy(max_attempts=3, delay_schedule=(AdapterRetryDelay(1),))
    with pytest.raises(AdapterResilienceValidationError, match="delay_schedule"):
        AdapterRetryPolicy(
            max_attempts=2,
            delay_schedule=cast(tuple[AdapterRetryDelay, ...], [AdapterRetryDelay(1)]),
        )
    with pytest.raises(AdapterResilienceValidationError, match="entries"):
        AdapterRetryPolicy(
            max_attempts=2,
            delay_schedule=cast(tuple[AdapterRetryDelay, ...], (object(),)),
        )
    with pytest.raises(AdapterResilienceValidationError, match="retryable_failures"):
        AdapterRetryPolicy(
            retryable_failures=cast(
                tuple[AdapterRetryableFailure, ...],
                [AdapterRetryableFailure.TIMEOUT],
            )
        )
    with pytest.raises(AdapterResilienceValidationError, match="entries"):
        AdapterRetryPolicy(
            retryable_failures=cast(tuple[AdapterRetryableFailure, ...], (object(),))
        )
    with pytest.raises(AdapterResilienceValidationError, match="positive"):
        AdapterRateLimitPolicy(request_limit=0, window=AdapterRetryDelay(1_000))
    with pytest.raises(AdapterResilienceValidationError, match="positive"):
        AdapterRateLimitPolicy(request_limit=1, window=AdapterRetryDelay(0))
    with pytest.raises(AdapterResilienceValidationError, match="burst_capacity"):
        AdapterRateLimitPolicy(
            request_limit=10,
            window=AdapterRetryDelay(1_000),
            burst_capacity=11,
        )


def test_circuit_breaker_validation_is_explicit_and_clockless() -> None:
    closed = AdapterCircuitBreakerSnapshot(
        state=AdapterCircuitBreakerState.CLOSED,
        observed_at=_OBSERVED_AT,
    )

    assert closed.logical_values() == (
        "closed",
        _OBSERVED_AT.isoformat(),
        0,
        None,
        None,
        (),
    )
    with pytest.raises(AdapterResilienceValidationError, match="timezone-aware"):
        AdapterCircuitBreakerSnapshot(
            state=AdapterCircuitBreakerState.CLOSED,
            observed_at=datetime(2026, 1, 1, 12, 0),
        )
    with pytest.raises(AdapterResilienceValidationError, match="recovery_delay"):
        AdapterCircuitBreakerSnapshot(
            state=AdapterCircuitBreakerState.OPEN,
            observed_at=_OBSERVED_AT,
        )
    with pytest.raises(AdapterResilienceValidationError, match="must not declare"):
        AdapterCircuitBreakerSnapshot(
            state=AdapterCircuitBreakerState.CLOSED,
            observed_at=_OBSERVED_AT,
            recovery_delay=AdapterRetryDelay(100),
        )
    with pytest.raises(AdapterResilienceValidationError, match="non-negative"):
        AdapterCircuitBreakerSnapshot(
            state=AdapterCircuitBreakerState.HALF_OPEN,
            observed_at=_OBSERVED_AT,
            failure_count=-1,
        )
    with pytest.raises(AdapterResilienceValidationError, match="sensitive"):
        AdapterCircuitBreakerSnapshot(
            state=AdapterCircuitBreakerState.CLOSED,
            observed_at=_OBSERVED_AT,
            message="token=leaked",
        )


def test_resilience_errors_are_typed_and_do_not_leak_payloads() -> None:
    policy = _policy()
    assert policy.rate_limit is not None
    circuit_breaker = AdapterCircuitBreakerSnapshot(
        state=AdapterCircuitBreakerState.OPEN,
        observed_at=_OBSERVED_AT,
        recovery_delay=AdapterRetryDelay(1_000),
    )

    errors = (
        AdapterTimeoutError(
            source=_SOURCE,
            timeout=policy.timeout,
            elapsed=AdapterRetryDelay(1_600),
        ),
        AdapterThrottledError(
            source=_SOURCE,
            policy=policy.rate_limit,
            retry_after=AdapterRetryDelay(500),
        ),
        AdapterResilienceUnavailableError(
            source=_SOURCE,
            circuit_breaker=circuit_breaker,
        ),
    )

    for error in errors:
        assert isinstance(error, AdapterResilienceError)
        assert isinstance(error, ExternalPortError)
        assert _RAW_SECRET not in str(error)
        assert _SOURCE.port_name.value in str(error)

    with pytest.raises(AdapterResilienceValidationError, match="source"):
        AdapterTimeoutError(
            source=cast(ExternalSourceDescriptor, object()),
            timeout=policy.timeout,
            elapsed=AdapterRetryDelay(1_600),
        )
    with pytest.raises(AdapterResilienceValidationError, match="policy"):
        AdapterThrottledError(
            source=_SOURCE,
            policy=cast(AdapterRateLimitPolicy, object()),
        )
    with pytest.raises(AdapterResilienceValidationError, match="circuit_breaker"):
        AdapterResilienceUnavailableError(
            source=_SOURCE,
            circuit_breaker=cast(AdapterCircuitBreakerSnapshot, object()),
        )


def test_resilience_metadata_rejects_sensitive_or_mutable_payloads() -> None:
    with pytest.raises(AdapterResilienceValidationError, match="secret-like"):
        AdapterResilienceSnapshot(
            policy=_policy(),
            observed_at=_OBSERVED_AT,
            metadata={"api_key": "inline"},
        )
    with pytest.raises(AdapterResilienceValidationError, match="reserved"):
        AdapterResilienceSnapshot(
            policy=_policy(),
            observed_at=_OBSERVED_AT,
            metadata={"value": "inline"},
        )
    with pytest.raises(AdapterResilienceValidationError, match="sensitive"):
        AdapterResilienceSnapshot(
            policy=_policy(),
            observed_at=_OBSERVED_AT,
            metadata={"status": _RAW_SECRET},
        )
    with pytest.raises(AdapterResilienceValidationError, match="finite"):
        AdapterResilienceSnapshot(
            policy=_policy(),
            observed_at=_OBSERVED_AT,
            metadata={"ratio": float("nan")},
        )
    with pytest.raises(AdapterResilienceValidationError, match="immutable"):
        AdapterResilienceSnapshot(
            policy=_policy(),
            observed_at=_OBSERVED_AT,
            metadata={"payload": cast(DomainMetadataValue, object())},
        )


def test_resilience_contracts_reject_runtime_type_bypasses() -> None:
    with pytest.raises(AdapterResilienceValidationError, match="ProviderDescriptor"):
        AdapterResiliencePolicy(
            provider=cast(ProviderDescriptor, object()),
            source=_SOURCE,
            timeout=AdapterTimeoutPolicy(AdapterRetryDelay(1_500)),
        )
    with pytest.raises(AdapterResilienceValidationError, match="ExternalSourceDescriptor"):
        AdapterResiliencePolicy(
            provider=_provider(),
            source=cast(ExternalSourceDescriptor, object()),
            timeout=AdapterTimeoutPolicy(AdapterRetryDelay(1_500)),
        )
    with pytest.raises(AdapterResilienceValidationError, match="AdapterTimeoutPolicy"):
        AdapterResiliencePolicy(
            provider=_provider(),
            source=_SOURCE,
            timeout=cast(AdapterTimeoutPolicy, object()),
        )
    with pytest.raises(AdapterResilienceValidationError, match="AdapterRetryPolicy"):
        AdapterResiliencePolicy(
            provider=_provider(),
            source=_SOURCE,
            timeout=AdapterTimeoutPolicy(AdapterRetryDelay(1_500)),
            retry=cast(AdapterRetryPolicy, object()),
        )
    with pytest.raises(AdapterResilienceValidationError, match="policy"):
        AdapterResilienceSnapshot(
            policy=cast(AdapterResiliencePolicy, object()),
            observed_at=_OBSERVED_AT,
        )
    with pytest.raises(AdapterResilienceValidationError, match="circuit_breaker"):
        AdapterResilienceSnapshot(
            policy=_policy(),
            observed_at=_OBSERVED_AT,
            circuit_breaker=cast(AdapterCircuitBreakerSnapshot, object()),
        )


def test_resilience_boundary_is_structural_without_side_effects() -> None:
    snapshot = AdapterResilienceSnapshot(
        policy=_policy(),
        observed_at=_OBSERVED_AT,
        metadata={"status": "accepted"},
    )
    boundary: AdapterResilienceBoundary = _ResilienceBoundary(snapshot)

    result = boundary.resilience_snapshot(
        observed_at=_OBSERVED_AT,
        metadata=_request_metadata(),
    )

    assert boundary.policy is snapshot.policy
    assert isinstance(result, Success)
    assert result.value is snapshot
    assert _RAW_SECRET not in repr(result.value.logical_values())


def test_public_exports_include_adapter_resilience_contracts() -> None:
    import qore.infrastructure as infrastructure

    assert infrastructure.AdapterCircuitBreakerSnapshot is AdapterCircuitBreakerSnapshot
    assert infrastructure.AdapterCircuitBreakerState is AdapterCircuitBreakerState
    assert infrastructure.AdapterRateLimitPolicy is AdapterRateLimitPolicy
    assert infrastructure.AdapterResilienceBoundary is AdapterResilienceBoundary
    assert infrastructure.AdapterResilienceError is AdapterResilienceError
    assert issubclass(AdapterResilienceError, ExternalPortError)
    assert infrastructure.AdapterResiliencePolicy is AdapterResiliencePolicy
    assert infrastructure.AdapterResilienceSnapshot is AdapterResilienceSnapshot
    assert (
        infrastructure.AdapterResilienceUnavailableError
        is AdapterResilienceUnavailableError
    )
    assert (
        infrastructure.AdapterResilienceValidationError
        is AdapterResilienceValidationError
    )
    assert infrastructure.AdapterRetryDelay is AdapterRetryDelay
    assert infrastructure.AdapterRetryPolicy is AdapterRetryPolicy
    assert infrastructure.AdapterRetryableFailure is AdapterRetryableFailure
    assert infrastructure.AdapterThrottledError is AdapterThrottledError
    assert infrastructure.AdapterTimeoutError is AdapterTimeoutError
    assert infrastructure.AdapterTimeoutPolicy is AdapterTimeoutPolicy
