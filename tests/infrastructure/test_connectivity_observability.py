from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.infrastructure.adapter_observability import AdapterReadiness
from qore.infrastructure.connectivity import (
    ProviderConnectionState,
    ProviderConnectivityMode,
    ProviderConnectivitySnapshot,
    ProviderEndpoint,
    ReadOnlyProviderConnectivityIntent,
)
from qore.infrastructure.connectivity_observability import (
    ConnectivityFailureCategory,
    ConnectivityObservabilityValidationError,
    ConnectivityObservation,
    observe_live_connectivity,
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

_NOW = datetime(2026, 8, 8, 5, 0, tzinfo=UTC)
_PROVIDER = ProviderDescriptor(
    provider_id=ProviderId(UUID("e9000000-0000-0000-0000-000000000001")),
    provider_name=ProviderName("reference.observable"),
    enablement=ProviderEnablement.READ_ONLY,
    capabilities=ProviderCapabilitySet((ProviderCapability.MARKET_DATA_READ,)),
)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("e9000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("e9000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.live"),
)
_INTENT = ReadOnlyProviderConnectivityIntent(
    provider=_PROVIDER,
    endpoint=ProviderEndpoint("data.example.test"),
    mode=ProviderConnectivityMode.NETWORK_READ_ONLY,
    capability=ProviderCapability.MARKET_DATA_READ,
)


def _connectivity(
    state: ProviderConnectionState,
    message: str | None = None,
) -> ProviderConnectivitySnapshot:
    return ProviderConnectivitySnapshot(
        intent=_INTENT,
        state=state,
        observed_at=_NOW,
        message=message,
    )


def test_ready_connectivity_projects_to_ready_observability() -> None:
    result = observe_live_connectivity(
        _PROVIDER,
        ConnectivityObservation(
            connectivity=_connectivity(ProviderConnectionState.READY),
            source=_SOURCE,
            latency_milliseconds=17,
        ),
        observed_at=_NOW,
    )

    assert isinstance(result, Success)
    assert result.value.readiness is AdapterReadiness.READY
    assert result.value.latency is not None
    assert result.value.latency.milliseconds == 17
    assert result.value.last_errors == ()


def test_degraded_failure_is_sanitized_and_categorized() -> None:
    result = observe_live_connectivity(
        _PROVIDER,
        ConnectivityObservation(
            connectivity=_connectivity(
                ProviderConnectionState.DEGRADED,
                "provider connectivity degraded",
            ),
            source=_SOURCE,
            latency_milliseconds=250,
            failure=ConnectivityFailureCategory.RATE_LIMITED,
        ),
        observed_at=_NOW,
    )

    assert isinstance(result, Success)
    assert result.value.readiness is AdapterReadiness.DEGRADED
    assert result.value.last_errors[0].error_type == "connectivity.rate_limited"
    assert "secret" not in result.value.last_errors[0].message


def test_unavailable_connectivity_projects_to_unavailable() -> None:
    result = observe_live_connectivity(
        _PROVIDER,
        ConnectivityObservation(
            connectivity=_connectivity(
                ProviderConnectionState.UNAVAILABLE,
                "provider unavailable",
            ),
            source=_SOURCE,
            failure=ConnectivityFailureCategory.UNAVAILABLE,
        ),
        observed_at=_NOW,
    )

    assert isinstance(result, Success)
    assert result.value.readiness is AdapterReadiness.UNAVAILABLE


def test_ready_connectivity_rejects_failure_category() -> None:
    with pytest.raises(ConnectivityObservabilityValidationError):
        ConnectivityObservation(
            connectivity=_connectivity(ProviderConnectionState.READY),
            source=_SOURCE,
            failure=ConnectivityFailureCategory.PROTOCOL,
        )


def test_latency_rejects_bool() -> None:
    with pytest.raises(ConnectivityObservabilityValidationError):
        ConnectivityObservation(
            connectivity=_connectivity(ProviderConnectionState.READY),
            source=_SOURCE,
            latency_milliseconds=True,
        )


def test_provider_identity_mismatch_returns_typed_failure() -> None:
    other = ProviderDescriptor(
        provider_id=ProviderId(UUID("e9000000-0000-0000-0000-000000000009")),
        provider_name=ProviderName("reference.other"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet((ProviderCapability.MARKET_DATA_READ,)),
    )
    result = observe_live_connectivity(
        other,
        ConnectivityObservation(
            connectivity=_connectivity(ProviderConnectionState.READY),
            source=_SOURCE,
        ),
        observed_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ConnectivityObservabilityValidationError)
