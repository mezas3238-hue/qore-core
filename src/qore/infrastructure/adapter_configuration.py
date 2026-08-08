from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from re import fullmatch
from types import MappingProxyType
from uuid import UUID

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.ports import ExternalPortError, ExternalSourceDescriptor
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderDescriptor,
    ProviderEnablement,
)

_RESERVED_PUBLIC_SETTING_KEYS = frozenset(
    {
        "adapter_id",
        "capabilities",
        "enablement",
        "mode",
        "provider_id",
        "provider_name",
        "secret",
        "secret_requirements",
        "secrets",
        "source_id",
    }
)
_SENSITIVE_PUBLIC_KEY_PARTS = frozenset(
    {"api-key", "api_key", "credential", "password", "secret", "token"}
)


class AdapterConfigurationError(ExternalPortError):
    """Base error for external adapter configuration contracts."""

    __slots__ = ()


class AdapterConfigurationValidationError(AdapterConfigurationError):
    """Violation of an external adapter configuration invariant."""

    __slots__ = ()


def _validate_setting_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int, UUID)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise AdapterConfigurationValidationError(
                "adapter public setting floats must be finite"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_setting_value(item)
        return
    raise AdapterConfigurationValidationError(
        "adapter public setting values must be immutable scalars or tuples"
    )


def _validate_configuration_key(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9._-]*",
        value,
    ) is None:
        raise AdapterConfigurationValidationError(
            f"{field_name} must use lowercase letters, digits, dots, underscores, "
            "or hyphens"
        )


def _contains_sensitive_public_key_part(key: str) -> bool:
    normalized = key.replace(".", "-").lower()
    return any(part in normalized for part in _SENSITIVE_PUBLIC_KEY_PARTS)


def _namespace_matches(port_name: str, namespace: str) -> bool:
    return port_name == namespace or port_name.startswith(f"{namespace}.")


class AdapterConfigurationMode(StrEnum):
    """Closed adapter configuration mode allowed before live execution."""

    DISABLED = "disabled"
    SIMULATION = "simulation"
    READ_ONLY = "read_only"

    @property
    def is_enabled(self) -> bool:
        """Return whether this mode enables a non-disabled adapter boundary."""
        return self is not AdapterConfigurationMode.DISABLED


_MODE_RANK = {
    AdapterConfigurationMode.DISABLED: 0,
    AdapterConfigurationMode.SIMULATION: 1,
    AdapterConfigurationMode.READ_ONLY: 2,
}
_PROVIDER_MODE_LIMIT = {
    ProviderEnablement.DISABLED: AdapterConfigurationMode.DISABLED,
    ProviderEnablement.SIMULATION: AdapterConfigurationMode.SIMULATION,
    ProviderEnablement.READ_ONLY: AdapterConfigurationMode.READ_ONLY,
}


@dataclass(frozen=True, slots=True)
class AdapterPublicSettings:
    """Immutable non-secret adapter settings safe for configuration snapshots."""

    values: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.values, Mapping):
            raise AdapterConfigurationValidationError(
                "adapter public settings must be a mapping"
            )
        for key, value in self.values.items():
            _validate_configuration_key(key, field_name="adapter public setting key")
            if key in _RESERVED_PUBLIC_SETTING_KEYS:
                raise AdapterConfigurationValidationError(
                    f"reserved adapter public setting key: {key}"
                )
            if _contains_sensitive_public_key_part(key):
                raise AdapterConfigurationValidationError(
                    "adapter public settings must not contain secret-like keys"
                )
            _validate_setting_value(value)
        ordered = {key: self.values[key] for key in sorted(self.values)}
        object.__setattr__(self, "values", MappingProxyType(ordered))

    def logical_values(self) -> tuple[tuple[str, DomainMetadataValue], ...]:
        """Return deterministic public settings without transport concerns."""
        return tuple(self.values.items())


@dataclass(frozen=True, slots=True)
class AdapterSecretName:
    """Opaque name of a required secret, never the secret value itself."""

    value: str

    def __post_init__(self) -> None:
        _validate_configuration_key(self.value, field_name="adapter secret name")


@dataclass(frozen=True, slots=True)
class AdapterSecretRequirement:
    """Declaration that an adapter needs a future secret reference."""

    name: AdapterSecretName
    required: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.name, AdapterSecretName):
            raise AdapterConfigurationValidationError(
                "adapter secret requirement name must be AdapterSecretName"
            )
        if not isinstance(self.required, bool):
            raise AdapterConfigurationValidationError(
                "adapter secret requirement required flag must be bool"
            )

    def logical_values(self) -> tuple[object, ...]:
        """Expose only the requirement name and required flag, not a value."""
        return (self.name.value, self.required)


@dataclass(frozen=True, slots=True)
class AdapterSecretRequirements:
    """Canonical immutable set of secret requirements without secret values."""

    requirements: tuple[AdapterSecretRequirement, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.requirements, tuple):
            raise AdapterConfigurationValidationError(
                "adapter secret requirements must be a tuple"
            )
        seen: set[str] = set()
        for requirement in self.requirements:
            if not isinstance(requirement, AdapterSecretRequirement):
                raise AdapterConfigurationValidationError(
                    "adapter secret requirement entries must be "
                    "AdapterSecretRequirement"
                )
            if requirement.name.value in seen:
                raise AdapterConfigurationValidationError(
                    "adapter secret requirements must not contain duplicates"
                )
            seen.add(requirement.name.value)
        ordered = tuple(
            sorted(self.requirements, key=lambda item: item.name.value)
        )
        object.__setattr__(self, "requirements", ordered)

    def logical_values(self) -> tuple[tuple[object, ...], ...]:
        return tuple(requirement.logical_values() for requirement in self.requirements)


def _validate_mode_with_provider(
    *,
    mode: AdapterConfigurationMode,
    provider: ProviderDescriptor,
) -> None:
    max_mode = _PROVIDER_MODE_LIMIT[provider.enablement]
    if _MODE_RANK[mode] > _MODE_RANK[max_mode]:
        raise AdapterConfigurationValidationError(
            "adapter mode must not exceed provider enablement"
        )


def _validate_source_namespace_with_provider(
    *,
    source: ExternalSourceDescriptor,
    provider: ProviderDescriptor,
) -> None:
    port_name = source.port_name.value
    capabilities = provider.capabilities
    if _namespace_matches(port_name, "market-data"):
        if not capabilities.supports(ProviderCapability.MARKET_DATA_READ):
            raise AdapterConfigurationValidationError(
                "market-data adapter configuration requires market-data capability"
            )
        return
    if _namespace_matches(port_name, "persistence"):
        if not (
            capabilities.supports(ProviderCapability.PERSISTENCE_READ)
            or capabilities.supports(ProviderCapability.PERSISTENCE_WRITE)
        ):
            raise AdapterConfigurationValidationError(
                "persistence adapter configuration requires persistence capability"
            )
        return
    if _namespace_matches(port_name, "provider"):
        if not capabilities.supports(ProviderCapability.HEALTH):
            raise AdapterConfigurationValidationError(
                "provider adapter configuration requires health capability"
            )
        return
    raise AdapterConfigurationValidationError(
        "adapter source port namespace must be market-data, persistence, or provider"
    )


@dataclass(frozen=True, slots=True)
class ExternalAdapterConfiguration:
    """Immutable provider-bound adapter configuration without secret values."""

    provider: ProviderDescriptor
    source: ExternalSourceDescriptor
    mode: AdapterConfigurationMode
    public_settings: AdapterPublicSettings = field(
        default_factory=AdapterPublicSettings
    )
    secret_requirements: AdapterSecretRequirements = field(
        default_factory=AdapterSecretRequirements
    )

    def __post_init__(self) -> None:
        if not isinstance(self.provider, ProviderDescriptor):
            raise AdapterConfigurationValidationError(
                "adapter configuration provider must be ProviderDescriptor"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise AdapterConfigurationValidationError(
                "adapter configuration source must be ExternalSourceDescriptor"
            )
        if not isinstance(self.mode, AdapterConfigurationMode):
            raise AdapterConfigurationValidationError(
                "adapter configuration mode must be AdapterConfigurationMode"
            )
        if not isinstance(self.public_settings, AdapterPublicSettings):
            raise AdapterConfigurationValidationError(
                "adapter configuration public_settings must be AdapterPublicSettings"
            )
        if not isinstance(self.secret_requirements, AdapterSecretRequirements):
            raise AdapterConfigurationValidationError(
                "adapter configuration secret_requirements must be "
                "AdapterSecretRequirements"
            )
        _validate_mode_with_provider(mode=self.mode, provider=self.provider)
        _validate_source_namespace_with_provider(
            source=self.source,
            provider=self.provider,
        )

    @property
    def is_enabled(self) -> bool:
        """Return whether both provider and adapter mode are non-disabled."""
        return self.provider.is_enabled and self.mode.is_enabled

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.source.logical_values(),
            self.mode.value,
            self.public_settings.logical_values(),
            self.secret_requirements.logical_values(),
        )
