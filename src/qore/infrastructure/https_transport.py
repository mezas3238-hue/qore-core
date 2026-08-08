from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from http.client import HTTPException, HTTPSConnection
from typing import Protocol
from urllib.parse import urlencode

from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.transport import (
    ExternalTransportBoundary,
    ExternalTransportError,
    ExternalTransportProtocolError,
    ExternalTransportRequest,
    ExternalTransportResponse,
    ExternalTransportTimeoutError,
    ExternalTransportUnavailableError,
    ExternalTransportValidationError,
)
from qore.kernel.result import Failure, Result, Success

_ALLOWED_RESPONSE_HEADERS = frozenset(
    {
        "content-length",
        "content-type",
        "date",
        "etag",
        "last-modified",
        "retry-after",
        "x-ratelimit-limit",
        "x-ratelimit-remaining",
        "x-ratelimit-reset",
    }
)


class HttpsResponseBoundary(Protocol):
    """Minimal response surface required from an HTTPS client."""

    status: int

    def read(self) -> bytes: ...

    def getheaders(self) -> list[tuple[str, str]]: ...


class HttpsConnectionBoundary(Protocol):
    """Minimal connection surface used by the concrete HTTPS transport."""

    def request(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
    ) -> None: ...

    def getresponse(self) -> HttpsResponseBoundary: ...

    def close(self) -> None: ...


class HttpsConnectionFactoryBoundary(Protocol):
    """Injectable connection construction for deterministic tests."""

    def create(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
    ) -> HttpsConnectionBoundary: ...


class TransportClockBoundary(Protocol):
    """Explicit clock boundary; production composition decides the clock source."""

    def now(self) -> datetime: ...


class _StdlibHttpsConnection:
    __slots__ = ("_connection",)

    def __init__(self, *, host: str, port: int, timeout_seconds: float) -> None:
        self._connection = HTTPSConnection(
            host=host,
            port=port,
            timeout=timeout_seconds,
        )

    def request(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
    ) -> None:
        self._connection.request(method=method, url=path, headers=dict(headers))

    def getresponse(self) -> HttpsResponseBoundary:
        return self._connection.getresponse()

    def close(self) -> None:
        self._connection.close()


class StdlibHttpsConnectionFactory:
    """Concrete stdlib HTTPS connection factory with TLS enabled by HTTPSConnection."""

    __slots__ = ()

    def create(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
    ) -> HttpsConnectionBoundary:
        return _StdlibHttpsConnection(
            host=host,
            port=port,
            timeout_seconds=timeout_seconds,
        )


def _request_path(request: ExternalTransportRequest) -> str:
    base_path = request.endpoint.base_path.rstrip("/")
    path = f"{base_path}{request.path}" if base_path else request.path
    if request.query:
        return f"{path}?{urlencode(request.query)}"
    return path


def _safe_response_headers(
    headers: list[tuple[str, str]],
) -> Mapping[str, str]:
    selected: dict[str, str] = {}
    for raw_name, raw_value in headers:
        name = raw_name.lower()
        if name not in _ALLOWED_RESPONSE_HEADERS or name in selected:
            continue
        value = raw_value.strip()
        if "\r" in value or "\n" in value:
            continue
        selected[name] = value
    return {name: selected[name] for name in sorted(selected)}


@dataclass(frozen=True, slots=True)
class ConcreteHttpsExternalTransport(ExternalTransportBoundary):
    """Concrete HTTPS implementation of the existing read-only transport boundary."""

    connection_factory: HttpsConnectionFactoryBoundary
    clock: TransportClockBoundary

    def execute(
        self,
        request: ExternalTransportRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExternalTransportError]:
        if not isinstance(request, ExternalTransportRequest):
            return Failure(
                ExternalTransportValidationError(
                    "concrete HTTPS transport requires ExternalTransportRequest"
                )
            )
        if not isinstance(metadata, ExternalRequestMetadata):
            return Failure(
                ExternalTransportValidationError(
                    "concrete HTTPS transport requires explicit metadata"
                )
            )

        connection = self.connection_factory.create(
            host=request.endpoint.host,
            port=request.endpoint.port,
            timeout_seconds=request.timeout.milliseconds / 1000,
        )
        try:
            connection.request(
                method=request.method.value,
                path=_request_path(request),
                headers=request.headers,
            )
            response = connection.getresponse()
            payload = response.read()
            received_at = self.clock.now()
            transport_response = ExternalTransportResponse(
                status_code=response.status,
                received_at=received_at,
                payload=payload,
                headers=_safe_response_headers(response.getheaders()),
            )
        except TimeoutError:
            return Failure(
                ExternalTransportTimeoutError("HTTPS transport timed out")
            )
        except HTTPException:
            return Failure(
                ExternalTransportProtocolError("HTTPS protocol failure")
            )
        except OSError:
            return Failure(
                ExternalTransportUnavailableError("HTTPS transport unavailable")
            )
        except ExternalTransportError as error:
            return Failure(error)
        finally:
            connection.close()
        return Success(transport_response)


def build_stdlib_https_transport(
    *,
    clock: TransportClockBoundary,
) -> ConcreteHttpsExternalTransport:
    """Build the network-capable transport while keeping the clock explicit."""
    return ConcreteHttpsExternalTransport(
        connection_factory=StdlibHttpsConnectionFactory(),
        clock=clock,
    )
