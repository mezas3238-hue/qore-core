from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from re import fullmatch
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.ports import ExternalPortError

_RESERVED_PROVIDER_METADATA_KEYS = frozenset(
    {"capabilities", "enablement", "provider_id", "provider_name"}
)


class ProviderBoundaryError(ExternalPortError):
    """Base error for provider-governance boundary contracts."""

    __slots__ = ()


class ProviderBoundaryValidationError(ProviderBoundaryError):
    """Violation of a provider-governance contract invariant."""

    __slots__ = ()


def _validate_provider_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int, UUID)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ProviderBoundaryValidationError(
                "provider metadata floats must be finite"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_provider_metadata_value(item)
        return
    raise ProviderBoundaryValidationError(
        "provider metadata values must be immutable scalars or tuples"
    )


@dataclass(frozen=True, slots=True)
class ProviderId:
    """Explicit provider identity, independent from adapter/source identity."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ProviderBoundaryValidationError("provider id must be a UUID")


@dataclass(frozen=True, slots=True)
class ProviderName:
    """Stable lowercase provider name used for governance, not credentials."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9.-]*",
            self.value,
        ) is None:
            raise ProviderBoundaryValidationError(
                "provider name must use lowercase letters, digits, dots, or hyphens"
            )


class ProviderEnablement(StrEnum):
    """Closed provider enablement state before live execution is allowed."""

    DISABLED = "disabled"
    SIMULATION = "simulation"
    READ_ONLY = "read_only"


class ProviderCapability(StrEnum):
    """Closed provider-neutral capabilities allowed in PHASE-07."""

    HEALTH = "health"
    MARKET_DATA_READ = "market_data.read"
    PERSISTENCE_READ = "persistence.read"
    PERSISTENCE_WRITE = "persistence.write"


@dataclass(frozen=True, slots=True)
class ProviderCapabilitySet:
    """Immutable canonical set of provider-neutral capabilities."""

    capabilities: tuple[ProviderCapability, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.capabilities, tuple):
            raise ProviderBoundaryValidationError(
                "provider capabilities must be a tuple"
            )
        seen: set[ProviderCapability] = set()
        for capability in self.capabilities:
            if not isinstance(capability, ProviderCapability):
                raise ProviderBoundaryValidationError(
                    "provider capability entries must be ProviderCapability"
                )
            if capability in seen:
                raise ProviderBoundaryValidationError(
                    "provider capabilities must not contain duplicates"
                )
            seen.add(capability)
        ordered = tuple(sorted(self.capabilities, key=lambda item: item.value))
        object.__setattr__(self, "capabilities", ordered)

    def supports(self, capability: ProviderCapability) -> bool:
        """Return whether this capability set explicitly supports a capability."""
        if not isinstance(capability, ProviderCapability):
            raise ProviderBoundaryValidationError(
                "provider capability check must use ProviderCapability"
            )
        return capability in self.capabilities

    def logical_values(self) -> tuple[str, ...]:
        return tuple(capability.value for capability in self.capabilities)


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    """Provider governance descriptor independent from adapter/source identity."""

    provider_id: ProviderId
    provider_name: ProviderName
    enablement: ProviderEnablement
    capabilities: ProviderCapabilitySet = field(default_factory=ProviderCapabilitySet)
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.provider_id, ProviderId):
            raise ProviderBoundaryValidationError(
                "provider descriptor provider_id must be ProviderId"
            )
        if not isinstance(self.provider_name, ProviderName):
            raise ProviderBoundaryValidationError(
                "provider descriptor provider_name must be ProviderName"
            )
        if not isinstance(self.enablement, ProviderEnablement):
            raise ProviderBoundaryValidationError(
                "provider descriptor enablement must be ProviderEnablement"
            )
        if not isinstance(self.capabilities, ProviderCapabilitySet):
            raise ProviderBoundaryValidationError(
                "provider descriptor capabilities must be ProviderCapabilitySet"
            )
        if not isinstance(self.metadata, Mapping):
            raise ProviderBoundaryValidationError(
                "provider descriptor metadata must be a mapping"
            )
        if any(not isinstance(key, str) or not key.strip() for key in self.metadata):
            raise ProviderBoundaryValidationError(
                "provider metadata keys must be non-empty strings"
            )
        reserved = _RESERVED_PROVIDER_METADATA_KEYS.intersection(self.metadata)
        if reserved:
            names = ", ".join(sorted(reserved))
            raise ProviderBoundaryValidationError(
                f"reserved provider metadata keys: {names}"
            )
        for value in self.metadata.values():
            _validate_provider_metadata_value(value)
        ordered = {key: self.metadata[key] for key in sorted(self.metadata)}
        object.__setattr__(self, "metadata", MappingProxyType(ordered))

    @property
    def is_enabled(self) -> bool:
        """Return whether the provider is enabled for non-disabled readiness."""
        return self.enablement is not ProviderEnablement.DISABLED

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.provider_id.value),
            self.provider_name.value,
            self.enablement.value,
            self.capabilities.logical_values(),
            tuple(self.metadata.items()),
        )


class ProviderGovernanceBoundary(Protocol):
    """Structural boundary exposing provider governance without concrete adapters."""

    @property
    def provider_descriptor(self) -> ProviderDescriptor:
        """Expose immutable provider identity and governance state."""
        ...

    @property
    def provider_capabilities(self) -> ProviderCapabilitySet:
        """Expose provider-neutral capabilities without concrete adapter details."""
        ...
