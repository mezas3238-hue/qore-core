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

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.ports import (
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
)
from qore.infrastructure.providers import ProviderDescriptor
from qore.kernel.result import Result

_RESERVED_OBSERVABILITY_METADATA_KEYS = frozenset(
    {"adapter_id", "provider_id", "secret", "secret_value", "source_id", "token", "value"}
)
_SENSITIVE_OBSERVABILITY_KEY_PARTS = frozenset(
    {"api-key", "api_key", "credential", "password", "secret", "token"}
)
_SENSITIVE_OBSERVABILITY_TEXT_PARTS = frozenset(
    {
        "-----begin",
        "api_key=",
        "authorization:",
        "bearer ",
        "client_secret=",
        "ghp_",
        "github_pat_",
        "password=",
        "secret=",
        "sk-",
        "token=",
        "xox",
    }
)


class AdapterObservabilityError(ExternalPortError):
    """Base error for adapter observability boundary contracts."""

    __slots__ = ()


class AdapterObservabilityValidationError(AdapterObservabilityError):
    """Violation of an adapter observability contract invariant."""

    __slots__ = ()


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise AdapterObservabilityValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise AdapterObservabilityValidationError(f"{field_name} must be timezone-aware")


def _validate_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int, UUID)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise AdapterObservabilityValidationError(
                "adapter observability metadata floats must be finite"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise AdapterObservabilityValidationError(
        "adapter observability metadata values must be immutable scalars or tuples"
    )


def _validate_metadata(
    values: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(values, Mapping):
        raise AdapterObservabilityValidationError(
            "adapter observability metadata must be a mapping"
        )
    for key, value in values.items():
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise AdapterObservabilityValidationError(
                "adapter observability metadata keys must use lowercase letters, "
                "digits, dots, underscores, or hyphens"
            )
        if key in _RESERVED_OBSERVABILITY_METADATA_KEYS:
            raise AdapterObservabilityValidationError(
                f"reserved adapter observability metadata key: {key}"
            )
        if any(part in key for part in _SENSITIVE_OBSERVABILITY_KEY_PARTS):
            raise AdapterObservabilityValidationError(
                "adapter observability metadata must not contain secret-like keys"
            )
        _validate_metadata_value(value)
    ordered = {key: values[key] for key in sorted(values)}
    return MappingProxyType(ordered)


def _validate_public_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AdapterObservabilityValidationError(f"{field_name} must be non-empty")
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_OBSERVABILITY_TEXT_PARTS):
        raise AdapterObservabilityValidationError(
            f"{field_name} must not contain sensitive payloads"
        )


def _availability_for_readiness(readiness: AdapterReadiness) -> PortAvailability:
    if readiness is AdapterReadiness.READY:
        return PortAvailability.AVAILABLE
    if readiness is AdapterReadiness.DEGRADED:
        return PortAvailability.DEGRADED
    return PortAvailability.UNAVAILABLE


class AdapterReadiness(StrEnum):
    """Closed observable readiness state for external adapters."""

    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class AdapterObservedErrorSeverity(StrEnum):
    """Closed severity for last-observed adapter errors."""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AdapterLatencyMeasurement:
    """Explicit latency measurement supplied by caller or injected instrumentation."""

    milliseconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.milliseconds, int) or isinstance(self.milliseconds, bool):
            raise AdapterObservabilityValidationError(
                "adapter latency milliseconds must be an integer"
            )
        if self.milliseconds < 0:
            raise AdapterObservabilityValidationError(
                "adapter latency milliseconds must be non-negative"
            )

    def logical_values(self) -> tuple[int]:
        return (self.milliseconds,)


@dataclass(frozen=True, slots=True)
class AdapterMetricName:
    """Stable provider-neutral adapter metric name."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]*",
            self.value,
        ) is None:
            raise AdapterObservabilityValidationError(
                "adapter metric name must use lowercase letters, digits, dots, "
                "underscores, or hyphens"
            )
        if any(part in self.value for part in _SENSITIVE_OBSERVABILITY_KEY_PARTS):
            raise AdapterObservabilityValidationError(
                "adapter metric name must not be secret-like"
            )


@dataclass(frozen=True, slots=True)
class AdapterMetric:
    """Provider-neutral observable adapter metric."""

    name: AdapterMetricName
    value: int | float
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, AdapterMetricName):
            raise AdapterObservabilityValidationError(
                "adapter metric name must be AdapterMetricName"
            )
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise AdapterObservabilityValidationError(
                "adapter metric value must be a finite number"
            )
        if isinstance(self.value, float) and not isfinite(self.value):
            raise AdapterObservabilityValidationError(
                "adapter metric value must be finite"
            )
        if not isinstance(self.unit, str) or fullmatch(r"[a-z][a-z0-9._/-]*", self.unit) is None:
            raise AdapterObservabilityValidationError(
                "adapter metric unit must be lowercase provider-neutral text"
            )
        if any(part in self.unit for part in _SENSITIVE_OBSERVABILITY_KEY_PARTS):
            raise AdapterObservabilityValidationError(
                "adapter metric unit must not be secret-like"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.name.value, self.value, self.unit)


@dataclass(frozen=True, slots=True)
class AdapterObservedError:
    """Sanitized last-observed adapter error without sensitive payloads."""

    error_type: str
    message: str
    severity: AdapterObservedErrorSeverity
    observed_at: datetime
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.error_type, str) or fullmatch(
            r"[a-z][a-z0-9._-]*",
            self.error_type,
        ) is None:
            raise AdapterObservabilityValidationError(
                "observed adapter error type must be lowercase canonical text"
            )
        if any(part in self.error_type for part in _SENSITIVE_OBSERVABILITY_KEY_PARTS):
            raise AdapterObservabilityValidationError(
                "observed adapter error type must not be secret-like"
            )
        _validate_public_text(self.message, field_name="observed adapter error message")
        if not isinstance(self.severity, AdapterObservedErrorSeverity):
            raise AdapterObservabilityValidationError(
                "observed adapter error severity must be AdapterObservedErrorSeverity"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.error_type,
            self.message,
            self.severity.value,
            self.observed_at.isoformat(),
            tuple(self.metadata.items()),
        )


@dataclass(frozen=True, slots=True)
class AdapterObservabilitySnapshot:
    """Immutable provider-neutral observable snapshot for one adapter boundary."""

    provider: ProviderDescriptor
    source: ExternalSourceDescriptor
    readiness: AdapterReadiness
    observed_at: datetime
    latency: AdapterLatencyMeasurement | None = None
    health: ExternalHealth | None = None
    metrics: tuple[AdapterMetric, ...] = ()
    last_errors: tuple[AdapterObservedError, ...] = ()
    message: str | None = None
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.provider, ProviderDescriptor):
            raise AdapterObservabilityValidationError(
                "adapter observability provider must be ProviderDescriptor"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise AdapterObservabilityValidationError(
                "adapter observability source must be ExternalSourceDescriptor"
            )
        if not isinstance(self.readiness, AdapterReadiness):
            raise AdapterObservabilityValidationError(
                "adapter observability readiness must be AdapterReadiness"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if self.latency is not None and not isinstance(
            self.latency,
            AdapterLatencyMeasurement,
        ):
            raise AdapterObservabilityValidationError(
                "adapter observability latency must be AdapterLatencyMeasurement or None"
            )
        if self.health is not None:
            if not isinstance(self.health, ExternalHealth):
                raise AdapterObservabilityValidationError(
                    "adapter observability health must be ExternalHealth or None"
                )
            if self.health.descriptor != self.source:
                raise AdapterObservabilityValidationError(
                    "adapter observability health descriptor must match source"
                )
            expected_availability = _availability_for_readiness(self.readiness)
            if self.health.availability is not expected_availability:
                raise AdapterObservabilityValidationError(
                    "adapter observability health availability must match readiness"
                )
        if not isinstance(self.metrics, tuple):
            raise AdapterObservabilityValidationError(
                "adapter observability metrics must be a tuple"
            )
        metric_names: set[str] = set()
        for metric in self.metrics:
            if not isinstance(metric, AdapterMetric):
                raise AdapterObservabilityValidationError(
                    "adapter observability metrics must contain AdapterMetric"
                )
            if metric.name.value in metric_names:
                raise AdapterObservabilityValidationError(
                    "adapter observability metrics must not contain duplicates"
                )
            metric_names.add(metric.name.value)
        if not isinstance(self.last_errors, tuple):
            raise AdapterObservabilityValidationError(
                "adapter observability last_errors must be a tuple"
            )
        for error in self.last_errors:
            if not isinstance(error, AdapterObservedError):
                raise AdapterObservabilityValidationError(
                    "adapter observability last_errors must contain AdapterObservedError"
                )
        if self.readiness is AdapterReadiness.READY and self.last_errors:
            raise AdapterObservabilityValidationError(
                "ready adapter observability snapshots must not carry last errors"
            )
        if self.readiness is not AdapterReadiness.READY and not self.message:
            raise AdapterObservabilityValidationError(
                "degraded or unavailable adapter observability snapshots need a message"
            )
        if self.message is not None:
            _validate_public_text(self.message, field_name="adapter observability message")
        object.__setattr__(
            self,
            "metrics",
            tuple(sorted(self.metrics, key=lambda item: item.name.value)),
        )
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.source.logical_values(),
            self.readiness.value,
            self.observed_at.isoformat(),
            self.latency.logical_values() if self.latency is not None else None,
            self.health.logical_values() if self.health is not None else None,
            tuple(metric.logical_values() for metric in self.metrics),
            tuple(error.logical_values() for error in self.last_errors),
            self.message,
            tuple(self.metadata.items()),
        )


class AdapterObservabilityBoundary(Protocol):
    """Structural future boundary for observing adapters without a backend."""

    def observe(
        self,
        *,
        observed_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[AdapterObservabilitySnapshot, AdapterObservabilityError]:
        """Return a deterministic observable snapshot using explicit metadata."""
        ...
