from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from types import MappingProxyType
from typing import Protocol

from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ports import ExternalPortError, ExternalRequestMetadata
from qore.kernel.result import Result

_SENSITIVE_HEADER_PARTS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
)


class ExternalTransportError(ExternalPortError):
    """Base error for controlled external transport."""

    __slots__ = ()


class ExternalTransportValidationError(ExternalTransportError):
    """Violation of a transport contract invariant."""

    __slots__ = ()


class ExternalTransportTimeoutError(ExternalTransportError):
    """Typed transport timeout without embedding request secrets."""

    __slots__ = ()


class ExternalTransportUnavailableError(ExternalTransportError):
    """Typed unavailable transport result."""

    __slots__ = ()


class ExternalTransportProtocolError(ExternalTransportError):
    """Typed remote/protocol failure sanitized from provider payloads."""

    __slots__ = ()


class ExternalTransportRateLimitedError(ExternalTransportError):
    """Typed rate-limit result without implicit retry or sleep."""

    __slots__ = ()


class ExternalTransportMethod(StrEnum):
    """Read-only HTTP methods permitted by PHASE-09."""

    GET = "GET"
    HEAD = "HEAD"


@dataclass(frozen=True, slots=True)
class ExternalTransportTimeout:
    """Explicit transport timeout in milliseconds."""

    milliseconds: int

    def __post_init__(self) -> None:
        if type(self.milliseconds) is not int or self.milliseconds <= 0:
            raise ExternalTransportValidationError(
                "transport timeout milliseconds must be a positive int"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.milliseconds,)


def _sanitize_headers(values: Mapping[str, str]) -> MappingProxyType[str, str]:
    if not isinstance(values, Mapping):
        raise ExternalTransportValidationError("transport headers must be a mapping")
    ordered: dict[str, str] = {}
    for raw_key in sorted(values, key=lambda item: item.lower()):
        value = values[raw_key]
        if not isinstance(raw_key, str) or fullmatch(
            r"[A-Za-z][A-Za-z0-9-]*", raw_key
        ) is None:
            raise ExternalTransportValidationError(
                "transport header names must use canonical HTTP token syntax"
            )
        key = raw_key.lower()
        if any(part in key for part in _SENSITIVE_HEADER_PARTS):
            raise ExternalTransportValidationError(
                "observable transport headers must not contain sensitive fields"
            )
        if not isinstance(value, str) or "\r" in value or "\n" in value:
            raise ExternalTransportValidationError(
                "transport header values must be single-line strings"
            )
        ordered[key] = value
    return MappingProxyType(ordered)


def _validate_relative_path(value: str) -> None:
    if not isinstance(value, str) or not value.startswith("/"):
        raise ExternalTransportValidationError(
            "transport request path must start with '/'"
        )
    if "//" in value or any(marker in value for marker in ("#", "@")):
        raise ExternalTransportValidationError(
            "transport request path must not contain empty segments, fragments, or credentials"
        )


def _validate_query(values: tuple[tuple[str, str], ...]) -> None:
    if not isinstance(values, tuple):
        raise ExternalTransportValidationError("transport query must be a tuple")
    previous: tuple[str, str] | None = None
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ExternalTransportValidationError(
                "transport query entries must be key/value tuples"
            )
        key, value = item
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise ExternalTransportValidationError(
                "transport query keys must use canonical lowercase syntax"
            )
        if any(part in key for part in _SENSITIVE_HEADER_PARTS):
            raise ExternalTransportValidationError(
                "transport query must not contain secret-like keys"
            )
        if not isinstance(value, str) or not value:
            raise ExternalTransportValidationError(
                "transport query values must be non-empty strings"
            )
        if previous is not None and item < previous:
            raise ExternalTransportValidationError(
                "transport query entries must be supplied in stable sorted order"
            )
        previous = item


@dataclass(frozen=True, slots=True)
class ExternalTransportRequest:
    """Immutable read-only transport request with no observable credential field."""

    endpoint: ProviderEndpoint
    method: ExternalTransportMethod
    path: str
    timeout: ExternalTransportTimeout
    query: tuple[tuple[str, str], ...] = ()
    headers: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint, ProviderEndpoint):
            raise ExternalTransportValidationError(
                "transport request endpoint must be ProviderEndpoint"
            )
        if not isinstance(self.method, ExternalTransportMethod):
            raise ExternalTransportValidationError(
                "transport request method must be ExternalTransportMethod"
            )
        if not isinstance(self.timeout, ExternalTransportTimeout):
            raise ExternalTransportValidationError(
                "transport request timeout must be ExternalTransportTimeout"
            )
        _validate_relative_path(self.path)
        _validate_query(self.query)
        object.__setattr__(self, "headers", _sanitize_headers(self.headers))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.endpoint.logical_values(),
            self.method.value,
            self.path,
            self.timeout.logical_values(),
            self.query,
            tuple(self.headers.items()),
        )


@dataclass(frozen=True, slots=True)
class ExternalTransportResponse:
    """Immutable transport response carrying only status, safe headers and bytes."""

    status_code: int
    received_at: datetime
    payload: bytes
    headers: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.status_code) is not int or not 100 <= self.status_code <= 599:
            raise ExternalTransportValidationError(
                "transport response status_code must be an HTTP status int"
            )
        if not isinstance(self.received_at, datetime):
            raise ExternalTransportValidationError(
                "transport response received_at must be a datetime"
            )
        if self.received_at.tzinfo is None or self.received_at.utcoffset() is None:
            raise ExternalTransportValidationError(
                "transport response received_at must be timezone-aware"
            )
        if not isinstance(self.payload, bytes):
            raise ExternalTransportValidationError(
                "transport response payload must be bytes"
            )
        object.__setattr__(self, "headers", _sanitize_headers(self.headers))

    @property
    def is_success(self) -> bool:
        """Return whether the status is a 2xx success."""
        return 200 <= self.status_code <= 299

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.status_code,
            self.received_at.isoformat(),
            len(self.payload),
            tuple(self.headers.items()),
        )


class ExternalTransportBoundary(Protocol):
    """Structural network-capable boundary; implementations remain injected."""

    def execute(
        self,
        request: ExternalTransportRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExternalTransportError]:
        """Execute one explicit read-only request and return a typed result."""
        ...
