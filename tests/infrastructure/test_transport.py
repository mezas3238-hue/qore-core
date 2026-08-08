from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.transport import (
    ExternalTransportMethod,
    ExternalTransportRequest,
    ExternalTransportResponse,
    ExternalTransportTimeout,
    ExternalTransportValidationError,
)

_NOW = datetime(2026, 8, 8, 4, 20, tzinfo=UTC)


def _request() -> ExternalTransportRequest:
    return ExternalTransportRequest(
        endpoint=ProviderEndpoint("data.example.test", base_path="/v1"),
        method=ExternalTransportMethod.GET,
        path="/quotes/latest",
        timeout=ExternalTransportTimeout(1500),
        query=(("instrument", "EURUSD"),),
        headers={"accept": "application/json", "x-request-mode": "read-only"},
    )


def test_transport_request_is_read_only_and_deterministic() -> None:
    request = _request()

    assert request.method is ExternalTransportMethod.GET
    assert tuple(request.headers) == ("accept", "x-request-mode")
    assert request.logical_values()[1:4] == (
        "GET",
        "/quotes/latest",
        (1500,),
    )


def test_transport_timeout_rejects_bool_and_non_positive_values() -> None:
    with pytest.raises(ExternalTransportValidationError):
        ExternalTransportTimeout(True)
    with pytest.raises(ExternalTransportValidationError):
        ExternalTransportTimeout(0)


def test_transport_request_rejects_sensitive_headers() -> None:
    with pytest.raises(ExternalTransportValidationError):
        ExternalTransportRequest(
            endpoint=ProviderEndpoint("data.example.test"),
            method=ExternalTransportMethod.GET,
            path="/health",
            timeout=ExternalTransportTimeout(1000),
            headers={"Authorization": "Bearer secret"},
        )


def test_transport_request_rejects_sensitive_query_keys() -> None:
    with pytest.raises(ExternalTransportValidationError):
        ExternalTransportRequest(
            endpoint=ProviderEndpoint("data.example.test"),
            method=ExternalTransportMethod.GET,
            path="/quotes",
            timeout=ExternalTransportTimeout(1000),
            query=(("api_token", "secret"),),
        )


def test_transport_request_requires_stable_query_order() -> None:
    with pytest.raises(ExternalTransportValidationError):
        ExternalTransportRequest(
            endpoint=ProviderEndpoint("data.example.test"),
            method=ExternalTransportMethod.GET,
            path="/quotes",
            timeout=ExternalTransportTimeout(1000),
            query=(("z", "2"), ("a", "1")),
        )


def test_transport_request_rejects_fragment_and_credentials_in_path() -> None:
    with pytest.raises(ExternalTransportValidationError):
        ExternalTransportRequest(
            endpoint=ProviderEndpoint("data.example.test"),
            method=ExternalTransportMethod.GET,
            path="/quotes#fragment",
            timeout=ExternalTransportTimeout(1000),
        )
    with pytest.raises(ExternalTransportValidationError):
        ExternalTransportRequest(
            endpoint=ProviderEndpoint("data.example.test"),
            method=ExternalTransportMethod.GET,
            path="/user@example",
            timeout=ExternalTransportTimeout(1000),
        )


def test_transport_response_requires_explicit_timezone_aware_timestamp() -> None:
    with pytest.raises(ExternalTransportValidationError):
        ExternalTransportResponse(
            status_code=200,
            received_at=datetime(2026, 8, 8, 4, 20),
            payload=b"{}",
        )


def test_transport_response_rejects_sensitive_observable_headers() -> None:
    with pytest.raises(ExternalTransportValidationError):
        ExternalTransportResponse(
            status_code=200,
            received_at=_NOW,
            payload=b"{}",
            headers={"set-cookie": "session=secret"},
        )


def test_transport_response_logical_values_do_not_expose_payload() -> None:
    payload = b'{"bid":1.1,"ask":1.2}'
    response = ExternalTransportResponse(
        status_code=200,
        received_at=_NOW,
        payload=payload,
        headers={"content-type": "application/json"},
    )

    assert response.is_success is True
    assert response.logical_values() == (
        200,
        _NOW.isoformat(),
        len(payload),
        (("content-type", "application/json"),),
    )
    assert payload not in response.logical_values()
