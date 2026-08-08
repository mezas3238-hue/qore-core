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

import qore.infrastructure.activation_policy as activation_policy
import qore.infrastructure.adapter_lifecycle as adapter_lifecycle
import qore.infrastructure.adapter_observability as adapter_observability
import qore.infrastructure.adapter_resilience as adapter_resilience
import qore.infrastructure.ports as ports
import qore.infrastructure.providers as providers
import qore.kernel.result as result_contract
from qore.domain.events import DomainMetadataValue

_RESERVED_EXTERNAL_HEALTH_METADATA_KEYS = frozenset(
    {
        "adapter_id",
        "causation_id",
        "correlation_id",
        "decision",
        "health",
        "issue",
        "issues",
        "provider_id",
        "readiness",
        "secret",
        "secret_value",
        "source_id",
        "token",
        "value",
    }
)
_SENSITIVE_EXTERNAL_HEALTH_KEY_PARTS = frozenset(
    {"api-key", "api_key", "credential", "password", "secret", "token"}
)
_SENSITIVE_EXTERNAL_HEALTH_TEXT_PARTS = frozenset(
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


class ExternalHealthAggregationError(ports.ExternalPortError):
    """Base error for external provider health aggregation contracts."""

    __slots__ = ()


class ExternalHealthAggregationValidationError(ExternalHealthAggregationError):
    """Violation of an external health aggregation invariant."""

    __slots__ = ()


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExternalHealthAggregationValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExternalHealthAggregationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_public_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ExternalHealthAggregationValidationError(f"{field_name} must be non-empty")
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_EXTERNAL_HEALTH_TEXT_PARTS):
        raise ExternalHealthAggregationValidationError(
            f"{field_name} must not contain sensitive payloads"
        )


def _validate_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (bool, int, UUID)):
        return
    if isinstance(value, str):
        _validate_public_text(value, field_name="external health metadata value")
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ExternalHealthAggregationValidationError(
                "external health metadata floats must be finite"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise ExternalHealthAggregationValidationError(
        "external health metadata values must be immutable scalars or tuples"
    )


def _validate_metadata(
    values: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(values, Mapping):
        raise ExternalHealthAggregationValidationError(
            "external health metadata must be a mapping"
        )
    for key, value in values.items():
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise ExternalHealthAggregationValidationError(
                "external health metadata keys must use lowercase letters, digits, "
                "dots, underscores, or hyphens"
            )
        if key in _RESERVED_EXTERNAL_HEALTH_METADATA_KEYS:
            raise ExternalHealthAggregationValidationError(
                f"reserved external health metadata key: {key}"
            )
        if any(part in key for part in _SENSITIVE_EXTERNAL_HEALTH_KEY_PARTS):
            raise ExternalHealthAggregationValidationError(
                "external health metadata must not contain secret-like keys"
            )
        _validate_metadata_value(value)
    return MappingProxyType({key: values[key] for key in sorted(values)})


def _validate_canonical_code(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9._-]*",
        value,
    ) is None:
        raise ExternalHealthAggregationValidationError(
            f"{field_name} must be lowercase canonical text"
        )
    if any(part in value for part in _SENSITIVE_EXTERNAL_HEALTH_KEY_PARTS):
        raise ExternalHealthAggregationValidationError(
            f"{field_name} must not be secret-like"
        )


class ExternalProviderReadiness(StrEnum):
    """Closed readiness state for aggregated external provider health."""

    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    BLOCKED = "blocked"


class ExternalHealthIssueSource(StrEnum):
    """Closed provider-neutral source for aggregated health issues."""

    ACTIVATION_POLICY = "activation_policy"
    LIFECYCLE = "lifecycle"
    OBSERVABILITY = "observability"
    RESILIENCE = "resilience"


class ExternalHealthIssueSeverity(StrEnum):
    """Closed severity for sanitized external health issues."""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


_READINESS_RANK = MappingProxyType(
    {
        ExternalProviderReadiness.READY: 0,
        ExternalProviderReadiness.DEGRADED: 1,
        ExternalProviderReadiness.UNAVAILABLE: 2,
        ExternalProviderReadiness.BLOCKED: 3,
    }
)


@dataclass(frozen=True, slots=True)
class ExternalHealthIssue:
    """Sanitized external health issue without provider payload or secrets."""

    source: ExternalHealthIssueSource
    severity: ExternalHealthIssueSeverity
    code: str
    message: str
    observed_at: datetime
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.source, ExternalHealthIssueSource):
            raise ExternalHealthAggregationValidationError(
                "external health issue source must be ExternalHealthIssueSource"
            )
        if not isinstance(self.severity, ExternalHealthIssueSeverity):
            raise ExternalHealthAggregationValidationError(
                "external health issue severity must be ExternalHealthIssueSeverity"
            )
        _validate_canonical_code(self.code, field_name="external health issue code")
        _validate_public_text(self.message, field_name="external health issue message")
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.source.value,
            self.severity.value,
            self.code,
            self.message,
            self.observed_at.isoformat(),
            tuple(self.metadata.items()),
        )


@dataclass(frozen=True, slots=True)
class ExternalProviderHealthInput:
    """Explicit health aggregation input for one provider/source boundary."""

    activation: activation_policy.ProviderActivationDecisionSnapshot
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.activation,
            activation_policy.ProviderActivationDecisionSnapshot,
        ):
            raise ExternalHealthAggregationValidationError(
                "external health input activation must be "
                "ProviderActivationDecisionSnapshot"
            )
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    @property
    def provider(self) -> providers.ProviderDescriptor:
        """Return the explicit provider identity for this health input."""
        return self.activation.policy.provider

    @property
    def source(self) -> ports.ExternalSourceDescriptor:
        """Return the explicit source identity for this health input."""
        return self.activation.policy.source

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.activation.logical_values(),
            tuple(self.metadata.items()),
        )


@dataclass(frozen=True, slots=True)
class ExternalProviderHealthSnapshot:
    """Aggregated external health snapshot for one provider/source boundary."""

    provider: providers.ProviderDescriptor
    source: ports.ExternalSourceDescriptor
    readiness: ExternalProviderReadiness
    observed_at: datetime
    activation: activation_policy.ProviderActivationDecisionSnapshot
    lifecycle: adapter_lifecycle.AdapterLifecycleSnapshot
    observability: adapter_observability.AdapterObservabilitySnapshot | None = None
    resilience: adapter_resilience.AdapterResilienceSnapshot | None = None
    issues: tuple[ExternalHealthIssue, ...] = ()
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.provider, providers.ProviderDescriptor):
            raise ExternalHealthAggregationValidationError(
                "external provider health provider must be ProviderDescriptor"
            )
        if not isinstance(self.source, ports.ExternalSourceDescriptor):
            raise ExternalHealthAggregationValidationError(
                "external provider health source must be ExternalSourceDescriptor"
            )
        if not isinstance(self.readiness, ExternalProviderReadiness):
            raise ExternalHealthAggregationValidationError(
                "external provider health readiness must be ExternalProviderReadiness"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if not isinstance(
            self.activation,
            activation_policy.ProviderActivationDecisionSnapshot,
        ):
            raise ExternalHealthAggregationValidationError(
                "external provider health activation must be "
                "ProviderActivationDecisionSnapshot"
            )
        if not isinstance(self.lifecycle, adapter_lifecycle.AdapterLifecycleSnapshot):
            raise ExternalHealthAggregationValidationError(
                "external provider health lifecycle must be AdapterLifecycleSnapshot"
            )
        if self.observability is not None and not isinstance(
            self.observability,
            adapter_observability.AdapterObservabilitySnapshot,
        ):
            raise ExternalHealthAggregationValidationError(
                "external provider health observability must be "
                "AdapterObservabilitySnapshot or None"
            )
        if self.resilience is not None and not isinstance(
            self.resilience,
            adapter_resilience.AdapterResilienceSnapshot,
        ):
            raise ExternalHealthAggregationValidationError(
                "external provider health resilience must be "
                "AdapterResilienceSnapshot or None"
            )
        _validate_identity(self)
        _validate_snapshot_time(self)
        if not isinstance(self.issues, tuple):
            raise ExternalHealthAggregationValidationError(
                "external provider health issues must be a tuple"
            )
        for issue in self.issues:
            if not isinstance(issue, ExternalHealthIssue):
                raise ExternalHealthAggregationValidationError(
                    "external provider health issues entries must be ExternalHealthIssue"
                )
            if issue.observed_at > self.observed_at:
                raise ExternalHealthAggregationValidationError(
                    "external provider health issue observed_at must not be after snapshot"
                )
        if self.readiness is ExternalProviderReadiness.READY and self.issues:
            raise ExternalHealthAggregationValidationError(
                "ready external provider health snapshots must not carry issues"
            )
        if self.readiness is not ExternalProviderReadiness.READY and not self.issues:
            raise ExternalHealthAggregationValidationError(
                "non-ready external provider health snapshots require issues"
            )
        object.__setattr__(
            self,
            "issues",
            tuple(
                sorted(
                    self.issues,
                    key=lambda item: (item.severity.value, item.source.value, item.code),
                )
            ),
        )
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.source.logical_values(),
            self.readiness.value,
            self.observed_at.isoformat(),
            self.activation.logical_values(),
            self.lifecycle.logical_values(),
            self.observability.logical_values()
            if self.observability is not None
            else None,
            self.resilience.logical_values() if self.resilience is not None else None,
            tuple(issue.logical_values() for issue in self.issues),
            tuple(self.metadata.items()),
        )


@dataclass(frozen=True, slots=True)
class ExternalProviderHealthAggregateSnapshot:
    """Global aggregate health snapshot for supervised external providers."""

    readiness: ExternalProviderReadiness
    observed_at: datetime
    providers: tuple[ExternalProviderHealthSnapshot, ...]
    metadata: ports.ExternalRequestMetadata
    issues: tuple[ExternalHealthIssue, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.readiness, ExternalProviderReadiness):
            raise ExternalHealthAggregationValidationError(
                "external aggregate health readiness must be ExternalProviderReadiness"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if not isinstance(self.providers, tuple):
            raise ExternalHealthAggregationValidationError(
                "external aggregate health providers must be a tuple"
            )
        if not self.providers:
            raise ExternalHealthAggregationValidationError(
                "external aggregate health requires at least one provider snapshot"
            )
        seen: set[tuple[object, object]] = set()
        for snapshot in self.providers:
            if not isinstance(snapshot, ExternalProviderHealthSnapshot):
                raise ExternalHealthAggregationValidationError(
                    "external aggregate health providers entries must be "
                    "ExternalProviderHealthSnapshot"
                )
            key = (snapshot.provider.provider_id.value, snapshot.source.source_id.value)
            if key in seen:
                raise ExternalHealthAggregationValidationError(
                    "external aggregate health provider/source snapshots must be unique"
                )
            seen.add(key)
            if snapshot.observed_at > self.observed_at:
                raise ExternalHealthAggregationValidationError(
                    "external aggregate health observed_at must be at or after providers"
                )
        if not isinstance(self.metadata, ports.ExternalRequestMetadata):
            raise ExternalHealthAggregationValidationError(
                "external aggregate health metadata must be ExternalRequestMetadata"
            )
        if not isinstance(self.issues, tuple):
            raise ExternalHealthAggregationValidationError(
                "external aggregate health issues must be a tuple"
            )
        for issue in self.issues:
            if not isinstance(issue, ExternalHealthIssue):
                raise ExternalHealthAggregationValidationError(
                    "external aggregate health issues entries must be ExternalHealthIssue"
                )
            if issue.observed_at > self.observed_at:
                raise ExternalHealthAggregationValidationError(
                    "external aggregate health issue observed_at must not be after snapshot"
                )
        if self.readiness is ExternalProviderReadiness.READY and self.issues:
            raise ExternalHealthAggregationValidationError(
                "ready external aggregate health snapshots must not carry issues"
            )
        if self.readiness is not ExternalProviderReadiness.READY and not self.issues:
            raise ExternalHealthAggregationValidationError(
                "non-ready external aggregate health snapshots require issues"
            )
        object.__setattr__(
            self,
            "providers",
            tuple(
                sorted(
                    self.providers,
                    key=lambda item: (
                        item.provider.provider_name.value,
                        item.source.port_name.value,
                        str(item.source.source_id.value),
                    ),
                )
            ),
        )
        object.__setattr__(
            self,
            "issues",
            tuple(
                sorted(
                    self.issues,
                    key=lambda item: (item.severity.value, item.source.value, item.code),
                )
            ),
        )

    def snapshot_for(
        self,
        source: ports.ExternalSourceDescriptor,
    ) -> ExternalProviderHealthSnapshot | None:
        """Return the provider health snapshot for a source, if present."""
        if not isinstance(source, ports.ExternalSourceDescriptor):
            raise ExternalHealthAggregationValidationError(
                "external aggregate snapshot source lookup must be ExternalSourceDescriptor"
            )
        for snapshot in self.providers:
            if snapshot.source == source:
                return snapshot
        return None

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.readiness.value,
            self.observed_at.isoformat(),
            tuple(snapshot.logical_values() for snapshot in self.providers),
            self.metadata.logical_values(),
            tuple(issue.logical_values() for issue in self.issues),
        )


class ExternalHealthAggregationBoundary(Protocol):
    """Structural boundary exposing external health aggregation."""

    def external_health_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[
        ExternalProviderHealthAggregateSnapshot,
        ExternalHealthAggregationError,
    ]:
        """Return aggregated external health without backend side effects."""
        ...


def _validate_identity(snapshot: ExternalProviderHealthSnapshot) -> None:
    if snapshot.activation.policy.provider != snapshot.provider:
        raise ExternalHealthAggregationValidationError(
            "external provider health activation provider must match snapshot"
        )
    if snapshot.activation.policy.source != snapshot.source:
        raise ExternalHealthAggregationValidationError(
            "external provider health activation source must match snapshot"
        )
    if snapshot.activation.configuration.provider != snapshot.provider:
        raise ExternalHealthAggregationValidationError(
            "external provider health configuration provider must match snapshot"
        )
    if snapshot.activation.configuration.source != snapshot.source:
        raise ExternalHealthAggregationValidationError(
            "external provider health configuration source must match snapshot"
        )
    if snapshot.lifecycle.provider != snapshot.provider:
        raise ExternalHealthAggregationValidationError(
            "external provider health lifecycle provider must match snapshot"
        )
    if snapshot.lifecycle.descriptor != snapshot.source:
        raise ExternalHealthAggregationValidationError(
            "external provider health lifecycle source must match snapshot"
        )
    if snapshot.observability is not None:
        if snapshot.observability.provider != snapshot.provider:
            raise ExternalHealthAggregationValidationError(
                "external provider health observability provider must match snapshot"
            )
        if snapshot.observability.source != snapshot.source:
            raise ExternalHealthAggregationValidationError(
                "external provider health observability source must match snapshot"
            )
    if snapshot.resilience is not None:
        if snapshot.resilience.policy.provider != snapshot.provider:
            raise ExternalHealthAggregationValidationError(
                "external provider health resilience provider must match snapshot"
            )
        if snapshot.resilience.policy.source != snapshot.source:
            raise ExternalHealthAggregationValidationError(
                "external provider health resilience source must match snapshot"
            )


def _validate_snapshot_time(snapshot: ExternalProviderHealthSnapshot) -> None:
    if snapshot.activation.evaluated_at > snapshot.observed_at:
        raise ExternalHealthAggregationValidationError(
            "external provider health observed_at must be at or after activation"
        )
    if snapshot.lifecycle.observed_at > snapshot.observed_at:
        raise ExternalHealthAggregationValidationError(
            "external provider health observed_at must be at or after lifecycle"
        )
    if snapshot.observability is not None and snapshot.observability.observed_at > snapshot.observed_at:
        raise ExternalHealthAggregationValidationError(
            "external provider health observed_at must be at or after observability"
        )
    if snapshot.resilience is not None and snapshot.resilience.observed_at > snapshot.observed_at:
        raise ExternalHealthAggregationValidationError(
            "external provider health observed_at must be at or after resilience"
        )


def _activation_issues(
    activation: activation_policy.ProviderActivationDecisionSnapshot,
) -> tuple[ExternalHealthIssue, ...]:
    if activation.decision is activation_policy.ProviderActivationDecision.ALLOWED:
        return ()
    severity = (
        ExternalHealthIssueSeverity.CRITICAL
        if activation.decision is activation_policy.ProviderActivationDecision.BLOCKED
        else ExternalHealthIssueSeverity.WARNING
    )
    return tuple(
        ExternalHealthIssue(
            source=ExternalHealthIssueSource.ACTIVATION_POLICY,
            severity=severity,
            code=f"activation.{reason.value}",
            message=f"activation {activation.decision.value}: {reason.value}",
            observed_at=activation.evaluated_at,
        )
        for reason in activation.reasons
    )


def _lifecycle_issues(
    lifecycle: adapter_lifecycle.AdapterLifecycleSnapshot,
) -> tuple[ExternalHealthIssue, ...]:
    if lifecycle.state is adapter_lifecycle.AdapterLifecycleState.FAILED:
        return (
            ExternalHealthIssue(
                source=ExternalHealthIssueSource.LIFECYCLE,
                severity=ExternalHealthIssueSeverity.ERROR,
                code="lifecycle.failed",
                message="external adapter lifecycle failed",
                observed_at=lifecycle.observed_at,
            ),
        )
    if lifecycle.state is adapter_lifecycle.AdapterLifecycleState.DEGRADED:
        return (
            ExternalHealthIssue(
                source=ExternalHealthIssueSource.LIFECYCLE,
                severity=ExternalHealthIssueSeverity.WARNING,
                code="lifecycle.degraded",
                message="external adapter lifecycle degraded",
                observed_at=lifecycle.observed_at,
            ),
        )
    return ()


def _observability_issues(
    observability: adapter_observability.AdapterObservabilitySnapshot | None,
) -> tuple[ExternalHealthIssue, ...]:
    if observability is None:
        return ()
    issues: list[ExternalHealthIssue] = []
    if observability.readiness is adapter_observability.AdapterReadiness.UNAVAILABLE:
        issues.append(
            ExternalHealthIssue(
                source=ExternalHealthIssueSource.OBSERVABILITY,
                severity=ExternalHealthIssueSeverity.ERROR,
                code="observability.unavailable",
                message=observability.message or "external adapter observability unavailable",
                observed_at=observability.observed_at,
            )
        )
    elif observability.readiness is adapter_observability.AdapterReadiness.DEGRADED:
        issues.append(
            ExternalHealthIssue(
                source=ExternalHealthIssueSource.OBSERVABILITY,
                severity=ExternalHealthIssueSeverity.WARNING,
                code="observability.degraded",
                message=observability.message or "external adapter observability degraded",
                observed_at=observability.observed_at,
            )
        )
    for observed_error in observability.last_errors:
        severity = {
            adapter_observability.AdapterObservedErrorSeverity.WARNING: (
                ExternalHealthIssueSeverity.WARNING
            ),
            adapter_observability.AdapterObservedErrorSeverity.ERROR: (
                ExternalHealthIssueSeverity.ERROR
            ),
            adapter_observability.AdapterObservedErrorSeverity.CRITICAL: (
                ExternalHealthIssueSeverity.CRITICAL
            ),
        }[observed_error.severity]
        issues.append(
            ExternalHealthIssue(
                source=ExternalHealthIssueSource.OBSERVABILITY,
                severity=severity,
                code=f"observability.{observed_error.error_type}",
                message=observed_error.message,
                observed_at=observed_error.observed_at,
                metadata=observed_error.metadata,
            )
        )
    return tuple(issues)


def _resilience_issues(
    resilience: adapter_resilience.AdapterResilienceSnapshot | None,
) -> tuple[ExternalHealthIssue, ...]:
    if resilience is None or resilience.circuit_breaker is None:
        return ()
    breaker = resilience.circuit_breaker
    if breaker.state is adapter_resilience.AdapterCircuitBreakerState.OPEN:
        return (
            ExternalHealthIssue(
                source=ExternalHealthIssueSource.RESILIENCE,
                severity=ExternalHealthIssueSeverity.ERROR,
                code="resilience.circuit_open",
                message=breaker.message or "external adapter circuit breaker is open",
                observed_at=breaker.observed_at,
                metadata=breaker.metadata,
            ),
        )
    if breaker.state is adapter_resilience.AdapterCircuitBreakerState.HALF_OPEN:
        return (
            ExternalHealthIssue(
                source=ExternalHealthIssueSource.RESILIENCE,
                severity=ExternalHealthIssueSeverity.WARNING,
                code="resilience.circuit_half_open",
                message=breaker.message or "external adapter circuit breaker is half open",
                observed_at=breaker.observed_at,
                metadata=breaker.metadata,
            ),
        )
    return ()


def _readiness_from_issues(
    *,
    activation: activation_policy.ProviderActivationDecisionSnapshot,
    lifecycle: adapter_lifecycle.AdapterLifecycleSnapshot,
    observability: adapter_observability.AdapterObservabilitySnapshot | None,
    resilience: adapter_resilience.AdapterResilienceSnapshot | None,
    issues: tuple[ExternalHealthIssue, ...],
) -> ExternalProviderReadiness:
    if activation.decision is activation_policy.ProviderActivationDecision.BLOCKED:
        return ExternalProviderReadiness.BLOCKED
    if lifecycle.state is adapter_lifecycle.AdapterLifecycleState.FAILED:
        return ExternalProviderReadiness.UNAVAILABLE
    if observability is not None and observability.readiness is adapter_observability.AdapterReadiness.UNAVAILABLE:
        return ExternalProviderReadiness.UNAVAILABLE
    if resilience is not None and resilience.circuit_breaker is not None:
        if resilience.circuit_breaker.state is adapter_resilience.AdapterCircuitBreakerState.OPEN:
            return ExternalProviderReadiness.UNAVAILABLE
    if activation.decision is activation_policy.ProviderActivationDecision.DEGRADED:
        return ExternalProviderReadiness.DEGRADED
    if lifecycle.state is adapter_lifecycle.AdapterLifecycleState.DEGRADED:
        return ExternalProviderReadiness.DEGRADED
    if observability is not None and observability.readiness is adapter_observability.AdapterReadiness.DEGRADED:
        return ExternalProviderReadiness.DEGRADED
    if resilience is not None and resilience.circuit_breaker is not None:
        if resilience.circuit_breaker.state is adapter_resilience.AdapterCircuitBreakerState.HALF_OPEN:
            return ExternalProviderReadiness.DEGRADED
    if issues:
        return ExternalProviderReadiness.DEGRADED
    return ExternalProviderReadiness.READY


def _provider_snapshot(
    health_input: ExternalProviderHealthInput,
    *,
    observed_at: datetime,
) -> ExternalProviderHealthSnapshot:
    activation = health_input.activation
    lifecycle = activation.lifecycle
    observability = activation.observability
    resilience = activation.resilience
    issues = (
        _activation_issues(activation)
        + _lifecycle_issues(lifecycle)
        + _observability_issues(observability)
        + _resilience_issues(resilience)
    )
    readiness = _readiness_from_issues(
        activation=activation,
        lifecycle=lifecycle,
        observability=observability,
        resilience=resilience,
        issues=issues,
    )
    return ExternalProviderHealthSnapshot(
        provider=health_input.provider,
        source=health_input.source,
        readiness=readiness,
        observed_at=observed_at,
        activation=activation,
        lifecycle=lifecycle,
        observability=observability,
        resilience=resilience,
        issues=issues,
        metadata=health_input.metadata,
    )


def _aggregate_readiness(
    snapshots: tuple[ExternalProviderHealthSnapshot, ...],
) -> ExternalProviderReadiness:
    return max(snapshots, key=lambda item: _READINESS_RANK[item.readiness]).readiness


def aggregate_external_provider_health(
    *,
    inputs: tuple[ExternalProviderHealthInput, ...],
    observed_at: datetime,
    metadata: ports.ExternalRequestMetadata,
) -> result_contract.Result[
    ExternalProviderHealthAggregateSnapshot,
    ExternalHealthAggregationError,
]:
    """Aggregate external provider health without monitoring backend side effects."""
    try:
        if not isinstance(inputs, tuple):
            raise ExternalHealthAggregationValidationError(
                "external health aggregation inputs must be a tuple"
            )
        if not inputs:
            raise ExternalHealthAggregationValidationError(
                "external health aggregation requires at least one input"
            )
        for health_input in inputs:
            if not isinstance(health_input, ExternalProviderHealthInput):
                raise ExternalHealthAggregationValidationError(
                    "external health aggregation input entries must be "
                    "ExternalProviderHealthInput"
                )
        _validate_explicit_datetime(observed_at, field_name="observed_at")
        if not isinstance(metadata, ports.ExternalRequestMetadata):
            raise ExternalHealthAggregationValidationError(
                "external health aggregation metadata must be ExternalRequestMetadata"
            )
        provider_snapshots = tuple(
            _provider_snapshot(health_input, observed_at=observed_at)
            for health_input in inputs
        )
        readiness = _aggregate_readiness(provider_snapshots)
        aggregate_issues = tuple(
            issue for snapshot in provider_snapshots for issue in snapshot.issues
        )
        snapshot = ExternalProviderHealthAggregateSnapshot(
            readiness=readiness,
            observed_at=observed_at,
            providers=provider_snapshots,
            metadata=metadata,
            issues=aggregate_issues,
        )
    except ExternalHealthAggregationError as error:
        return result_contract.Failure(error)
    return result_contract.Success(snapshot)
