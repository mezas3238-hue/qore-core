from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.infrastructure.adapter_resilience import (
    AdapterCircuitBreakerSnapshot,
    AdapterCircuitBreakerState,
    AdapterResiliencePolicy,
    AdapterResilienceSnapshot,
    AdapterRetryableFailure,
    AdapterRetryDelay,
    AdapterRetryPolicy,
    AdapterTimeoutPolicy,
)
from qore.infrastructure.connectivity_observability import ConnectivityFailureCategory
from qore.infrastructure.connectivity_resilience import (
    ConnectivityRecoveryDecision,
    ConnectivityRecoveryRequest,
    ConnectivityResilienceValidationError,
    plan_connectivity_recovery,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 5, 10, tzinfo=UTC)
_PROVIDER = ProviderDescriptor(
    provider_id=ProviderId(UUID("f9000000-0000-0000-0000-000000000001")),
    provider_name=ProviderName("reference.resilient"),
    enablement=ProviderEnablement.READ_ONLY,
    capabilities=ProviderCapabilitySet((ProviderCapability.MARKET_DATA_READ,)),
)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f9000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("f9000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.live"),
)
_POLICY = AdapterResiliencePolicy(
    provider=_PROVIDER,
    source=_SOURCE,
    timeout=AdapterTimeoutPolicy(AdapterRetryDelay(1500)),
    retry=AdapterRetryPolicy(
        max_attempts=3,
        delay_schedule=(AdapterRetryDelay(100), AdapterRetryDelay(250)),
        retryable_failures=(
            AdapterRetryableFailure.TIMEOUT,
            AdapterRetryableFailure.THROTTLED,
            AdapterRetryableFailure.UNAVAILABLE,
        ),
    ),
)


def _snapshot(
    breaker: AdapterCircuitBreakerSnapshot | None = None,
) -> AdapterResilienceSnapshot:
    return AdapterResilienceSnapshot(
        policy=_POLICY,
        observed_at=_NOW,
        circuit_breaker=breaker,
    )


def test_timeout_retry_uses_explicit_schedule() -> None:
    result = plan_connectivity_recovery(
        _POLICY,
        _snapshot(),
        ConnectivityRecoveryRequest(
            failure=ConnectivityFailureCategory.TIMEOUT,
            attempt=1,
        ),
    )

    assert isinstance(result, Success)
    assert result.value.decision is ConnectivityRecoveryDecision.RETRY
    assert result.value.delay == AdapterRetryDelay(100)


def test_unavailable_uses_reconnect_decision() -> None:
    result = plan_connectivity_recovery(
        _POLICY,
        _snapshot(),
        ConnectivityRecoveryRequest(
            failure=ConnectivityFailureCategory.UNAVAILABLE,
            attempt=2,
        ),
    )

    assert isinstance(result, Success)
    assert result.value.decision is ConnectivityRecoveryDecision.RECONNECT
    assert result.value.delay == AdapterRetryDelay(250)


def test_retry_budget_exhaustion_stops_without_delay() -> None:
    result = plan_connectivity_recovery(
        _POLICY,
        _snapshot(),
        ConnectivityRecoveryRequest(
            failure=ConnectivityFailureCategory.TIMEOUT,
            attempt=3,
        ),
    )

    assert isinstance(result, Success)
    assert result.value.decision is ConnectivityRecoveryDecision.STOP
    assert result.value.delay is None
    assert result.value.reason == "retry_budget_exhausted"


def test_protocol_failure_is_not_retryable() -> None:
    result = plan_connectivity_recovery(
        _POLICY,
        _snapshot(),
        ConnectivityRecoveryRequest(
            failure=ConnectivityFailureCategory.PROTOCOL,
            attempt=1,
        ),
    )

    assert isinstance(result, Success)
    assert result.value.decision is ConnectivityRecoveryDecision.STOP
    assert result.value.reason == "failure_not_retryable"


def test_open_circuit_stops_before_retry_policy() -> None:
    breaker = AdapterCircuitBreakerSnapshot(
        state=AdapterCircuitBreakerState.OPEN,
        observed_at=_NOW,
        failure_count=3,
        recovery_delay=AdapterRetryDelay(5000),
        message="provider circuit open",
    )
    result = plan_connectivity_recovery(
        _POLICY,
        _snapshot(breaker),
        ConnectivityRecoveryRequest(
            failure=ConnectivityFailureCategory.UNAVAILABLE,
            attempt=1,
        ),
    )

    assert isinstance(result, Success)
    assert result.value.decision is ConnectivityRecoveryDecision.STOP
    assert result.value.reason == "circuit_breaker_open"


def test_attempt_rejects_bool() -> None:
    with pytest.raises(ConnectivityResilienceValidationError):
        ConnectivityRecoveryRequest(
            failure=ConnectivityFailureCategory.TIMEOUT,
            attempt=True,
        )


def test_snapshot_policy_identity_mismatch_returns_failure() -> None:
    other = AdapterResiliencePolicy(
        provider=_PROVIDER,
        source=_SOURCE,
        timeout=AdapterTimeoutPolicy(AdapterRetryDelay(999)),
    )
    result = plan_connectivity_recovery(
        other,
        _snapshot(),
        ConnectivityRecoveryRequest(
            failure=ConnectivityFailureCategory.TIMEOUT,
            attempt=1,
        ),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ConnectivityResilienceValidationError)
