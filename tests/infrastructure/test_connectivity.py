from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.infrastructure.connectivity import (
    ProviderConnectionState,
    ProviderConnectivityMode,
    ProviderConnectivitySnapshot,
    ProviderConnectivityValidationError,
    ProviderEndpoint,
    ReadOnlyProviderConnectivityIntent,
    declare_connectivity_snapshot,
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

_NOW = datetime(2026, 8, 8, 4, 10, tzinfo=UTC)
_PROVIDER_ID = ProviderId(UUID("a9000000-0000-0000-0000-000000000001"))


def _provider(
    *,
    enablement: ProviderEnablement = ProviderEnablement.READ_ONLY,
    capabilities: tuple[ProviderCapability, ...] = (
        ProviderCapability.HEALTH,
        ProviderCapability.MARKET_DATA_READ,
    ),
) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("reference.connectivity"),
        enablement=enablement,
        capabilities=ProviderCapabilitySet(capabilities),
    )


def _intent(
    *,
    mode: ProviderConnectivityMode = ProviderConnectivityMode.NETWORK_READ_ONLY,
    provider: ProviderDescriptor | None = None,
    capability: ProviderCapability = ProviderCapability.MARKET_DATA_READ,
) -> ReadOnlyProviderConnectivityIntent:
    return ReadOnlyProviderConnectivityIntent(
        provider=_provider() if provider is None else provider,
        endpoint=ProviderEndpoint("data.example.test", base_path="/v1/market"),
        mode=mode,
        capability=capability,
    )


def test_provider_endpoint_exposes_credential_free_https_origin() -> None:
    endpoint = ProviderEndpoint("data.example.test", base_path="/v1")

    assert endpoint.origin == "https://data.example.test"
    assert endpoint.logical_values() == ("data.example.test", 443, "/v1")


def test_provider_endpoint_rejects_bool_port_and_sensitive_path_markers() -> None:
    with pytest.raises(ProviderConnectivityValidationError):
        ProviderEndpoint("data.example.test", port=True)
    with pytest.raises(ProviderConnectivityValidationError):
        ProviderEndpoint("data.example.test", base_path="/v1?token=value")


def test_network_connectivity_requires_read_only_provider_enablement() -> None:
    simulation_provider = _provider(enablement=ProviderEnablement.SIMULATION)

    with pytest.raises(ProviderConnectivityValidationError):
        _intent(provider=simulation_provider)


def test_connectivity_rejects_write_capability() -> None:
    provider = _provider(
        capabilities=(
            ProviderCapability.HEALTH,
            ProviderCapability.PERSISTENCE_WRITE,
        )
    )

    with pytest.raises(ProviderConnectivityValidationError):
        _intent(provider=provider, capability=ProviderCapability.PERSISTENCE_WRITE)


def test_connectivity_rejects_undeclared_capability() -> None:
    provider = _provider(capabilities=(ProviderCapability.HEALTH,))

    with pytest.raises(ProviderConnectivityValidationError):
        _intent(provider=provider)


def test_declare_ready_connectivity_is_deterministic() -> None:
    result = declare_connectivity_snapshot(_intent(), observed_at=_NOW)

    assert isinstance(result, Success)
    assert result.value.state is ProviderConnectionState.READY
    assert result.value.message is None
    assert result.value.observed_at == _NOW


def test_disabled_connectivity_is_fail_closed() -> None:
    disabled = _provider(enablement=ProviderEnablement.DISABLED)
    intent = _intent(mode=ProviderConnectivityMode.DISABLED, provider=disabled)

    result = declare_connectivity_snapshot(intent, observed_at=_NOW)

    assert isinstance(result, Success)
    assert result.value.state is ProviderConnectionState.BLOCKED
    assert result.value.message == "connectivity disabled"


def test_snapshot_rejects_naive_timestamp() -> None:
    result = declare_connectivity_snapshot(
        _intent(),
        observed_at=datetime(2026, 8, 8, 4, 10),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProviderConnectivityValidationError)


def test_snapshot_requires_message_for_non_ready_state() -> None:
    result = declare_connectivity_snapshot(
        _intent(),
        observed_at=_NOW,
        state=ProviderConnectionState.UNAVAILABLE,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProviderConnectivityValidationError)


def test_snapshot_rejects_sensitive_detail_keys() -> None:
    result = declare_connectivity_snapshot(
        _intent(),
        observed_at=_NOW,
        state=ProviderConnectionState.DEGRADED,
        message="provider latency degraded",
        details={"access_token": "must-not-be-stored"},
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProviderConnectivityValidationError)


def test_snapshot_sorts_safe_details_and_logical_values() -> None:
    snapshot = ProviderConnectivitySnapshot(
        intent=_intent(),
        state=ProviderConnectionState.DEGRADED,
        observed_at=_NOW,
        message="latency threshold exceeded",
        details={"z_state": "degraded", "a_attempt": 2},
    )

    assert tuple(snapshot.details) == ("a_attempt", "z_state")
    assert snapshot.logical_values()[1:4] == (
        "degraded",
        _NOW.isoformat(),
        "latency threshold exceeded",
    )
