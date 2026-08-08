from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.https_transport import (
    ConcreteHttpsExternalTransport,
    HttpsConnectionBoundary,
    HttpsConnectionFactoryBoundary,
    HttpsResponseBoundary,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.transport import (
    ExternalTransportMethod,
    ExternalTransportRequest,
    ExternalTransportTimeout,
    ExternalTransportTimeoutError,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 10, 25, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return _NOW


class FakeResponse:
    status = 200

    def read(self) -> bytes:
        return b'{"bid":"1.1000","ask":"1.1002"}'

    def getheaders(self) -> list[tuple[str, str]]:
        return [
            ("Content-Type", "application/json"),
            ("Set-Cookie", "session=secret"),
            ("ETag", "stable-tag"),
        ]


class FakeConnection:
    def __init__(self, *, fail_timeout: bool = False) -> None:
        self.fail_timeout = fail_timeout
        self.calls: list[tuple[str, str, tuple[tuple[str, str], ...]]] = []
        self.closed = False

    def request(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
    ) -> None:
        if self.fail_timeout:
            raise TimeoutError
        self.calls.append((method, path, tuple(headers.items())))

    def getresponse(self) -> HttpsResponseBoundary:
        return FakeResponse()

    def close(self) -> None:
        self.closed = True


class FakeFactory:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.created: list[tuple[str, int, float]] = []

    def create(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
    ) -> HttpsConnectionBoundary:
        self.created.append((host, port, timeout_seconds))
        return self.connection


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=CorrelationId(
            UUID("21000000-0000-0000-0000-000000000001")
        )
    )


def _request() -> ExternalTransportRequest:
    return ExternalTransportRequest(
        endpoint=ProviderEndpoint("data.example.test", base_path="/v1"),
        method=ExternalTransportMethod.GET,
        path="/quotes/latest",
        timeout=ExternalTransportTimeout(1500),
        query=(("instrument", "EURUSD"),),
        headers={"accept": "application/json"},
    )


def test_concrete_https_transport_executes_existing_read_only_contract() -> None:
    connection = FakeConnection()
    factory: HttpsConnectionFactoryBoundary = FakeFactory(connection)
    transport = ConcreteHttpsExternalTransport(
        connection_factory=factory,
        clock=FakeClock(),
    )

    result = transport.execute(_request(), metadata=_metadata())

    assert isinstance(result, Success)
    assert result.value.status_code == 200
    assert result.value.received_at == _NOW
    assert result.value.payload.startswith(b"{")
    assert tuple(result.value.headers.items()) == (
        ("content-type", "application/json"),
        ("etag", "stable-tag"),
    )
    assert connection.calls == [
        (
            "GET",
            "/v1/quotes/latest?instrument=EURUSD",
            (("accept", "application/json"),),
        )
    ]
    assert connection.closed is True


def test_concrete_transport_passes_explicit_host_port_and_timeout() -> None:
    connection = FakeConnection()
    factory = FakeFactory(connection)
    transport = ConcreteHttpsExternalTransport(
        connection_factory=factory,
        clock=FakeClock(),
    )

    result = transport.execute(_request(), metadata=_metadata())

    assert isinstance(result, Success)
    assert factory.created == [("data.example.test", 443, 1.5)]


def test_timeout_is_typed_and_connection_is_closed() -> None:
    connection = FakeConnection(fail_timeout=True)
    transport = ConcreteHttpsExternalTransport(
        connection_factory=FakeFactory(connection),
        clock=FakeClock(),
    )

    result = transport.execute(_request(), metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExternalTransportTimeoutError)
    assert connection.closed is True


def test_transport_does_not_send_trace_metadata_as_credentials() -> None:
    connection = FakeConnection()
    transport = ConcreteHttpsExternalTransport(
        connection_factory=FakeFactory(connection),
        clock=FakeClock(),
    )

    result = transport.execute(_request(), metadata=_metadata())

    assert isinstance(result, Success)
    sent_headers = dict(connection.calls[0][2])
    assert sent_headers == {"accept": "application/json"}
    assert "authorization" not in sent_headers
