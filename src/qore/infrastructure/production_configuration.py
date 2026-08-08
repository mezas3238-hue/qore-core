from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite
from re import fullmatch
from types import MappingProxyType
from typing import Protocol

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_KEY_PARTS = (
    "api-key",
    "api_key",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)
_SENSITIVE_TEXT_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret=",
    "password=",
    "secret=",
    "token=",
)


class ProductionConfigurationError(ExternalPortError):
    """Base error for production configuration contracts."""

    __slots__ = ()


class ProductionConfigurationValidationError(ProductionConfigurationError):
    """Violation of a production configuration invariant."""

    __slots__ = ()


class ProductionEnvironment(StrEnum):
    """Closed deployment environment identity."""

    STAGING = "staging"
    PRODUCTION = "production"


class ProductionRuntimeMode(StrEnum):
    """Closed operational runtime mode; neither mode authorizes trading."""

    OBSERVE = "observe"
    SERVICE = "service"


@dataclass(frozen=True, slots=True)
class ProductionRegion:
    """Canonical provider-neutral deployment region identifier."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9-]{1,31}", self.value
        ) is None:
            raise ProductionConfigurationValidationError(
                "production region must use lowercase letters, digits, or hyphens"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _validate_value(value: DomainMetadataValue) -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ProductionConfigurationValidationError(
                "production configuration floats must be finite"
            )
        return
    if isinstance(value, str):
        normalized = value.lower()
        if any(part in normalized for part in _SENSITIVE_TEXT_PARTS):
            raise ProductionConfigurationValidationError(
                "production configuration values must not contain sensitive material"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_value(item)
        return
    raise ProductionConfigurationValidationError(
        "production configuration values must be immutable metadata values"
    )


def _validate_values(
    values: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(values, Mapping):
        raise ProductionConfigurationValidationError(
            "production configuration values must be a mapping"
        )
    ordered: dict[str, DomainMetadataValue] = {}
    for key in sorted(values):
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise ProductionConfigurationValidationError(
                "production configuration keys must use canonical lowercase syntax"
            )
        if any(part in key for part in _SENSITIVE_KEY_PARTS):
            raise ProductionConfigurationValidationError(
                "production configuration must not contain secret-like keys"
            )
        value = values[key]
        _validate_value(value)
        ordered[key] = value
    return MappingProxyType(ordered)


@dataclass(frozen=True, slots=True)
class ProductionConfigurationSnapshot:
    """Immutable non-sensitive operational configuration snapshot."""

    environment: ProductionEnvironment
    region: ProductionRegion
    runtime_mode: ProductionRuntimeMode
    loaded_at: datetime
    values: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.environment, ProductionEnvironment):
            raise ProductionConfigurationValidationError(
                "production environment must be ProductionEnvironment"
            )
        if not isinstance(self.region, ProductionRegion):
            raise ProductionConfigurationValidationError(
                "production region must be ProductionRegion"
            )
        if not isinstance(self.runtime_mode, ProductionRuntimeMode):
            raise ProductionConfigurationValidationError(
                "production runtime_mode must be ProductionRuntimeMode"
            )
        if not isinstance(self.loaded_at, datetime):
            raise ProductionConfigurationValidationError(
                "production loaded_at must be a datetime"
            )
        if self.loaded_at.tzinfo is None or self.loaded_at.utcoffset() is None:
            raise ProductionConfigurationValidationError(
                "production loaded_at must be timezone-aware"
            )
        object.__setattr__(self, "values", _validate_values(self.values))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.environment.value,
            self.region.logical_values(),
            self.runtime_mode.value,
            self.loaded_at.isoformat(),
            tuple(self.values.items()),
        )


class ProductionConfigurationSource(Protocol):
    """Structural source boundary; concrete deployment loading remains injected."""

    def load(
        self,
        *,
        loaded_at: datetime,
    ) -> Result[ProductionConfigurationSnapshot, ProductionConfigurationError]: ...


@dataclass(frozen=True, slots=True)
class MappingProductionConfigurationSource:
    """Deterministic reference source over caller-supplied non-sensitive values."""

    environment: ProductionEnvironment
    region: ProductionRegion
    runtime_mode: ProductionRuntimeMode
    values: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.environment, ProductionEnvironment):
            raise ProductionConfigurationValidationError(
                "configuration source environment must be ProductionEnvironment"
            )
        if not isinstance(self.region, ProductionRegion):
            raise ProductionConfigurationValidationError(
                "configuration source region must be ProductionRegion"
            )
        if not isinstance(self.runtime_mode, ProductionRuntimeMode):
            raise ProductionConfigurationValidationError(
                "configuration source runtime_mode must be ProductionRuntimeMode"
            )
        object.__setattr__(self, "values", _validate_values(self.values))

    def load(
        self,
        *,
        loaded_at: datetime,
    ) -> Result[ProductionConfigurationSnapshot, ProductionConfigurationError]:
        try:
            snapshot = ProductionConfigurationSnapshot(
                environment=self.environment,
                region=self.region,
                runtime_mode=self.runtime_mode,
                loaded_at=loaded_at,
                values=self.values,
            )
        except ProductionConfigurationError as error:
            return Failure(error)
        return Success(snapshot)


def load_production_configuration(
    source: ProductionConfigurationSource,
    *,
    loaded_at: datetime,
) -> Result[ProductionConfigurationSnapshot, ProductionConfigurationError]:
    """Load through an injected source without global environment access."""
    return source.load(loaded_at=loaded_at)
