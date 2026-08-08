from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from types import MappingProxyType
from typing import Protocol

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.ports import ExternalPortError, ExternalRequestMetadata
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderDescriptor,
    ProviderEnablement,
)
from qore.kernel.result import Failure, Result, Success


class ProviderConnectivityError(ExternalPortError):
    """Base error for controlled external-provider connectivity."""

    __slots__ = ()


class ProviderConnectivityValidationError(ProviderConnectivityError):
    """Violation of a connectivity contract invariant."""

    __slots__ = ()


class ProviderConnectivityUnavailableError(ProviderConnectivityError):
    """Typed fail-closed result when connectivity cannot be exposed."""

    __slots__ = ()


class ProviderConnectivityMode(StrEnum):
    """Closed connectivity modes permitted by PHASE-09."""

    DISABLED = "disabled"
    DETERMINISTIC = "deterministic"
    NETWORK_READ_ONLY = "network_read_only"


class ProviderConnectionState(StrEnum):
    """Closed provider connection state exposed to supervision."""

    DISCONNECTED = "disconnected"
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ProviderEndpoint:
    """Canonical HTTPS endpoint identity without credentials or query values."""

    host: str
    port: int = 443
    base_path: str = "/"

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or fullmatch(
            r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", self.host
        ) is None:
            raise ProviderConnectivityValidationError(
                "provider endpoint host must be canonical lowercase DNS syntax"
            )
        if self.host.startswith(".") or self.host.endswith(".") or ".." in self.host:
            raise ProviderConnectivityValidationError(
                "provider endpoint host must not contain empty DNS labels"
            )
        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise ProviderConnectivityValidationError(
                "provider endpoint port must be an integer"
            )
        if self.port < 1 or self.port > 65535:
            raise ProviderConnectivityValidationError(
                "provider endpoint port must be between 1 and 65535"
            )
        if not isinstance(self.base_path, str) or not self.base_path.startswith("/"):
            raise ProviderConnectivityValidationError(
                "provider endpoint base_path must start with '/'"
            )
        if any(marker in self.base_path for marker in ("?", "#", "@")):
            raise ProviderConnectivityValidationError(
                "provider endpoint base_path must not contain query, fragment, or credentials"
            )
        if "//" in self.base_path:
            raise ProviderConnectivityValidationError(
                "provider endpoint base_path must not contain empty path segments"
            )

    @property
    def origin(self) -> str:
        """Return a credential-free HTTPS origin."""
        if self.port == 443:
            return f"https://{self.host}"
        return f"https://{self.host}:{self.port}"

    def logical_values(self) -> tuple[object, ...]:
        return (self.host, self.port, self.base_path)


_READ_ONLY_CAPABILITIES = frozenset(
    {
        ProviderCapability.HEALTH,
        ProviderCapability.MARKET_DATA_READ,
        ProviderCapability.PERSISTENCE_READ,
    }
)


@dataclass(frozen=True, slots=True)
class ReadOnlyProviderConnectivityIntent:
    """Explicit opt-in intent for one provider-neutral read-only capability."""

    provider: ProviderDescriptor
    endpoint: ProviderEndpoint
    mode: ProviderConnectivityMode
    capability: ProviderCapability

    def __post_init__(self) -> None:
        if not isinstance(self.provider, ProviderDescriptor):
            raise ProviderConnectivityValidationError(
                "connectivity intent provider must be ProviderDescriptor"
            )
        if not isinstance(self.endpoint, ProviderEndpoint):
            raise ProviderConnectivityValidationError(
                "connectivity intent endpoint must be ProviderEndpoint"
            )
        if not isinstance(self.mode, ProviderConnectivityMode):
            raise ProviderConnectivityValidationError(
                "connectivity intent mode must be ProviderConnectivityMode"
            )
        if not isinstance(self.capability, ProviderCapability):
            raise ProviderConnectivityValidationError(
                "connectivity intent capability must be ProviderCapability"
            )
        if self.capability not in _READ_ONLY_CAPABILITIES:
            raise ProviderConnectivityValidationError(
                "PHASE-09 connectivity intent must be read-only"
            )
        if not self.provider.capabilities.supports(self.capability):
            raise ProviderConnectivityValidationError(
                "provider does not declare the requested connectivity capability"
            )
        if self.mode is ProviderConnectivityMode.NETWORK_READ_ONLY and (
            self.provider.enablement is not ProviderEnablement.READ_ONLY
        ):
            raise ProviderConnectivityValidationError(
                "network read-only connectivity requires READ_ONLY provider enablement"
            )
        if self.mode is ProviderConnectivityMode.DETERMINISTIC and (
            self.provider.enablement is ProviderEnablement.DISABLED
        ):
            raise ProviderConnectivityValidationError(
                "deterministic connectivity requires an enabled provider"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.endpoint.logical_values(),
            self.mode.value,
            self.capability.value,
        )


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ProviderConnectivityValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProviderConnectivityValidationError(
            f"{field_name} must be timezone-aware"
        )


def _safe_details(
    details: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(details, Mapping):
        raise ProviderConnectivityValidationError(
            "connectivity snapshot details must be a mapping"
        )
    blocked_parts = ("authorization", "credential", "password", "secret", "token")
    ordered: dict[str, DomainMetadataValue] = {}
    for key in sorted(details):
        if not isinstance(key, str) or not key.strip():
            raise ProviderConnectivityValidationError(
                "connectivity snapshot detail keys must be non-empty strings"
            )
        if any(part in key.lower() for part in blocked_parts):
            raise ProviderConnectivityValidationError(
                "connectivity snapshot details must not contain sensitive keys"
            )
        value = details[key]
        if value is not None and not isinstance(value, (str, bool, int, float, tuple)):
            raise ProviderConnectivityValidationError(
                "connectivity snapshot details must use immutable metadata values"
            )
        ordered[key] = value
    return MappingProxyType(ordered)


@dataclass(frozen=True, slots=True)
class ProviderConnectivitySnapshot:
    """Immutable sanitized connection state for supervision."""

    intent: ReadOnlyProviderConnectivityIntent
    state: ProviderConnectionState
    observed_at: datetime
    message: str | None = None
    details: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.intent, ReadOnlyProviderConnectivityIntent):
            raise ProviderConnectivityValidationError(
                "connectivity snapshot intent must be explicit"
            )
        if not isinstance(self.state, ProviderConnectionState):
            raise ProviderConnectivityValidationError(
                "connectivity snapshot state must be ProviderConnectionState"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if self.state is ProviderConnectionState.READY and self.message is not None:
            raise ProviderConnectivityValidationError(
                "ready connectivity snapshot must not carry an error message"
            )
        if self.state in {
            ProviderConnectionState.DEGRADED,
            ProviderConnectionState.UNAVAILABLE,
            ProviderConnectionState.BLOCKED,
        } and (not isinstance(self.message, str) or not self.message.strip()):
            raise ProviderConnectivityValidationError(
                "non-ready connectivity snapshot must include a message"
            )
        if self.message is not None and not isinstance(self.message, str):
            raise ProviderConnectivityValidationError(
                "connectivity snapshot message must be a string or None"
            )
        object.__setattr__(self, "details", _safe_details(self.details))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.intent.logical_values(),
            self.state.value,
            self.observed_at.isoformat(),
            self.message,
            tuple(self.details.items()),
        )


class ProviderConnectivityBoundary(Protocol):
    """Structural boundary for an explicitly supervised provider connection."""

    @property
    def connectivity_intent(self) -> ReadOnlyProviderConnectivityIntent:
        """Expose the immutable connectivity intent."""
        ...

    def connectivity_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ProviderConnectivitySnapshot, ProviderConnectivityError]:
        """Return a typed sanitized connection snapshot."""
        ...


def declare_connectivity_snapshot(
    intent: ReadOnlyProviderConnectivityIntent,
    *,
    observed_at: datetime,
    state: ProviderConnectionState | None = None,
    message: str | None = None,
    details: Mapping[str, DomainMetadataValue] | None = None,
) -> Result[ProviderConnectivitySnapshot, ProviderConnectivityError]:
    """Declare deterministic connectivity state without performing network IO."""
    if not isinstance(intent, ReadOnlyProviderConnectivityIntent):
        return Failure(
            ProviderConnectivityValidationError(
                "connectivity declaration requires ReadOnlyProviderConnectivityIntent"
            )
        )
    try:
        resolved_state = state
        if resolved_state is None:
            resolved_state = (
                ProviderConnectionState.BLOCKED
                if intent.mode is ProviderConnectivityMode.DISABLED
                else ProviderConnectionState.READY
            )
            if resolved_state is ProviderConnectionState.BLOCKED and message is None:
                message = "connectivity disabled"
        snapshot = ProviderConnectivitySnapshot(
            intent=intent,
            state=resolved_state,
            observed_at=observed_at,
            message=message,
            details=MappingProxyType({}) if details is None else details,
        )
    except ProviderConnectivityError as error:
        return Failure(error)
    return Success(snapshot)
