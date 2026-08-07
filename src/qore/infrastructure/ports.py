from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite
from re import fullmatch
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from qore.domain.events import CausationId, CorrelationId, DomainMetadataValue
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Result

_RESERVED_METADATA_KEYS = frozenset({"correlation_id", "causation_id"})


class ExternalPortError(InfrastructureError):
    """Base error for external integration boundaries."""

    __slots__ = ()


class PortValidationError(ExternalPortError):
    """Violation of an external-port contract invariant."""

    __slots__ = ()


class PortUnavailableError(ExternalPortError):
    """Typed error for an explicitly unavailable external port."""

    __slots__ = ()


def _validate_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int, UUID)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise PortValidationError("external metadata floats must be finite")
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise PortValidationError(
        "external metadata values must be immutable scalars or tuples"
    )


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise PortValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise PortValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class AdapterId:
    """Explicit identity of one concrete adapter instance/configuration."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise PortValidationError("adapter id must be a UUID")


@dataclass(frozen=True, slots=True)
class SourceId:
    """Explicit identity of one external data/service source."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise PortValidationError("source id must be a UUID")


@dataclass(frozen=True, slots=True)
class PortName:
    """Stable validated name for one external integration port."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9.-]*", self.value
        ) is None:
            raise PortValidationError(
                "port name must use lowercase letters, digits, dots, or hyphens"
            )


class PortAvailability(StrEnum):
    """Closed availability state exposed by external boundaries."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ExternalSourceDescriptor:
    """Immutable identity and naming of an adapter/source pair."""

    adapter_id: AdapterId
    source_id: SourceId
    port_name: PortName

    def __post_init__(self) -> None:
        if not isinstance(self.adapter_id, AdapterId):
            raise PortValidationError("descriptor adapter_id must be AdapterId")
        if not isinstance(self.source_id, SourceId):
            raise PortValidationError("descriptor source_id must be SourceId")
        if not isinstance(self.port_name, PortName):
            raise PortValidationError("descriptor port_name must be PortName")
        if self.adapter_id.value == self.source_id.value:
            raise PortValidationError(
                "adapter identity must differ from external source identity"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.adapter_id.value),
            str(self.source_id.value),
            self.port_name.value,
        )


@dataclass(frozen=True, slots=True)
class ExternalRequestMetadata:
    """Immutable trace metadata supplied explicitly at an external boundary."""

    correlation_id: CorrelationId
    causation_id: CausationId | None = None
    attributes: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.correlation_id, CorrelationId):
            raise PortValidationError(
                "external metadata correlation_id must be CorrelationId"
            )
        if self.causation_id is not None and not isinstance(
            self.causation_id, CausationId
        ):
            raise PortValidationError(
                "external metadata causation_id must be CausationId or None"
            )
        if not isinstance(self.attributes, Mapping):
            raise PortValidationError("external metadata attributes must be a mapping")
        if any(not isinstance(key, str) or not key.strip() for key in self.attributes):
            raise PortValidationError(
                "external metadata keys must be non-empty strings"
            )
        reserved = _RESERVED_METADATA_KEYS.intersection(self.attributes)
        if reserved:
            names = ", ".join(sorted(reserved))
            raise PortValidationError(f"reserved external metadata keys: {names}")
        for value in self.attributes.values():
            _validate_metadata_value(value)
        ordered = {key: self.attributes[key] for key in sorted(self.attributes)}
        object.__setattr__(self, "attributes", MappingProxyType(ordered))

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.correlation_id.value),
            str(self.causation_id.value) if self.causation_id is not None else None,
            tuple(self.attributes.items()),
        )


@dataclass(frozen=True, slots=True)
class ExternalHealth:
    """Immutable health snapshot reported by one external port boundary."""

    descriptor: ExternalSourceDescriptor
    availability: PortAvailability
    checked_at: datetime
    message: str | None = None
    details: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, ExternalSourceDescriptor):
            raise PortValidationError("external health descriptor must be explicit")
        if not isinstance(self.availability, PortAvailability):
            raise PortValidationError(
                "external health availability must be PortAvailability"
            )
        _validate_explicit_datetime(self.checked_at, field_name="checked_at")
        if self.message is not None and (
            not isinstance(self.message, str) or not self.message.strip()
        ):
            raise PortValidationError("external health message must be non-empty or None")
        if self.availability is PortAvailability.AVAILABLE and self.message is not None:
            raise PortValidationError(
                "available external health must not carry a degradation message"
            )
        if self.availability is not PortAvailability.AVAILABLE and self.message is None:
            raise PortValidationError(
                "degraded or unavailable external health must include a message"
            )
        if not isinstance(self.details, Mapping):
            raise PortValidationError("external health details must be a mapping")
        if any(not isinstance(key, str) or not key.strip() for key in self.details):
            raise PortValidationError(
                "external health detail keys must be non-empty strings"
            )
        for value in self.details.values():
            _validate_metadata_value(value)
        ordered = {key: self.details[key] for key in sorted(self.details)}
        object.__setattr__(self, "details", MappingProxyType(ordered))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.descriptor.logical_values(),
            self.availability.value,
            self.checked_at.isoformat(),
            self.message,
            tuple(self.details.items()),
        )


class ExternalPort(Protocol):
    """Common structural contract implemented by every external integration port."""

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        """Expose immutable adapter/source identity."""
        ...

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        """Return a typed health result without throwing lateral boundary errors."""
        ...


class ReadExternalPort[RequestT, ResponseT](ExternalPort, Protocol):
    """Generic typed read boundary for future provider-specific ports."""

    def read(
        self,
        request: RequestT,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ResponseT, ExternalPortError]:
        """Read through the boundary using explicit trace metadata."""
        ...


class WriteExternalPort[RequestT, ResponseT](ExternalPort, Protocol):
    """Generic typed write boundary for future provider-specific ports."""

    def write(
        self,
        request: RequestT,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ResponseT, ExternalPortError]:
        """Write through the boundary using explicit trace metadata."""
        ...
