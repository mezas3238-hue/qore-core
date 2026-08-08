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
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.infrastructure.providers import ProviderDescriptor
from qore.kernel.result import Result

_RESERVED_RESILIENCE_METADATA_KEYS = frozenset(
    {"adapter_id", "provider_id", "secret", "secret_value", "source_id", "token", "value"}
)
_SENSITIVE_RESILIENCE_KEY_PARTS = frozenset(
    {"api-key", "api_key", "credential", "password", "secret", "token"}
)
_SENSITIVE_RESILIENCE_TEXT_PARTS = frozenset(
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


class AdapterResilienceError(ExternalPortError):
    """Base error for adapter resilience boundary contracts."""

    __slots__ = ()


class AdapterResilienceValidationError(AdapterResilienceError):
    """Violation of an adapter resilience contract invariant."""

    __slots__ = ()


class AdapterTimeoutError(AdapterResilienceError):
    """Typed error for an operation exceeding an explicit timeout policy."""

    __slots__ = ()

    def __init__(
        self,
        *,
        source: ExternalSourceDescriptor,
        timeout: AdapterTimeoutPolicy,
        elapsed: AdapterRetryDelay,
    ) -> None:
        if not isinstance(source, ExternalSourceDescriptor):
            raise AdapterResilienceValidationError(
                "adapter timeout source must be ExternalSourceDescriptor"
            )
        if not isinstance(timeout, AdapterTimeoutPolicy):
            raise AdapterResilienceValidationError(
                "adapter timeout policy must be AdapterTimeoutPolicy"
            )
        if not isinstance(elapsed, AdapterRetryDelay):
            raise AdapterResilienceValidationError(
                "adapter timeout elapsed must be AdapterRetryDelay"
            )
        super().__init__(
            "adapter operation timed out: "
            f"source={source.logical_values()} "
            f"timeout_ms={timeout.operation_timeout.milliseconds} "
            f"elapsed_ms={elapsed.milliseconds}"
        )


class AdapterThrottledError(AdapterResilienceError):
    """Typed error for a provider-neutral rate-limit decision."""

    __slots__ = ()

    def __init__(
        self,
        *,
        source: ExternalSourceDescriptor,
        policy: AdapterRateLimitPolicy,
        retry_after: AdapterRetryDelay | None = None,
    ) -> None:
        if not isinstance(source, ExternalSourceDescriptor):
            raise AdapterResilienceValidationError(
                "adapter throttled source must be ExternalSourceDescriptor"
            )
        if not isinstance(policy, AdapterRateLimitPolicy):
            raise AdapterResilienceValidationError(
                "adapter throttled policy must be AdapterRateLimitPolicy"
            )
        if retry_after is not None and not isinstance(retry_after, AdapterRetryDelay):
            raise AdapterResilienceValidationError(
                "adapter throttled retry_after must be AdapterRetryDelay or None"
            )
        retry_after_text = (
            f" retry_after_ms={retry_after.milliseconds}"
            if retry_after is not None
            else ""
        )
        super().__init__(
            "adapter rate limit exceeded: "
            f"source={source.logical_values()} "
            f"limit={policy.request_limit} "
            f"window_ms={policy.window.milliseconds}"
            f"{retry_after_text}"
        )


class AdapterResilienceUnavailableError(AdapterResilienceError):
    """Typed error for an unavailable adapter resilience state."""

    __slots__ = ()

    def __init__(
        self,
        *,
        source: ExternalSourceDescriptor,
        circuit_breaker: AdapterCircuitBreakerSnapshot | None = None,
    ) -> None:
        if not isinstance(source, ExternalSourceDescriptor):
            raise AdapterResilienceValidationError(
                "adapter unavailable source must be ExternalSourceDescriptor"
            )
        if circuit_breaker is not None and not isinstance(
            circuit_breaker,
            AdapterCircuitBreakerSnapshot,
        ):
            raise AdapterResilienceValidationError(
                "adapter unavailable circuit_breaker must be "
                "AdapterCircuitBreakerSnapshot or None"
            )
        breaker_text = (
            f" circuit_breaker={circuit_breaker.state.value}"
            if circuit_breaker is not None
            else ""
        )
        super().__init__(
            "adapter unavailable: "
            f"source={source.logical_values()}"
            f"{breaker_text}"
        )


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise AdapterResilienceValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise AdapterResilienceValidationError(f"{field_name} must be timezone-aware")


def _validate_public_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AdapterResilienceValidationError(f"{field_name} must be non-empty")
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_RESILIENCE_TEXT_PARTS):
        raise AdapterResilienceValidationError(
            f"{field_name} must not contain sensitive payloads"
        )


def _validate_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (bool, int, UUID)):
        return
    if isinstance(value, str):
        _validate_public_text(value, field_name="adapter resilience metadata value")
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise AdapterResilienceValidationError(
                "adapter resilience metadata floats must be finite"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise AdapterResilienceValidationError(
        "adapter resilience metadata values must be immutable scalars or tuples"
    )


def _validate_metadata(
    values: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(values, Mapping):
        raise AdapterResilienceValidationError(
            "adapter resilience metadata must be a mapping"
        )
    for key, value in values.items():
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise AdapterResilienceValidationError(
                "adapter resilience metadata keys must use lowercase letters, "
                "digits, dots, underscores, or hyphens"
            )
        if key in _RESERVED_RESILIENCE_METADATA_KEYS:
            raise AdapterResilienceValidationError(
                f"reserved adapter resilience metadata key: {key}"
            )
        if any(part in key for part in _SENSITIVE_RESILIENCE_KEY_PARTS):
            raise AdapterResilienceValidationError(
                "adapter resilience metadata must not contain secret-like keys"
            )
        _validate_metadata_value(value)
    ordered = {key: values[key] for key in sorted(values)}
    return MappingProxyType(ordered)


class AdapterRetryableFailure(StrEnum):
    """Closed provider-neutral failure categories eligible for retry policy."""

    TIMEOUT = "timeout"
    THROTTLED = "throttled"
    UNAVAILABLE = "unavailable"


class AdapterCircuitBreakerState(StrEnum):
    """Closed observable circuit-breaker state."""

    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


@dataclass(frozen=True, slots=True)
class AdapterRetryDelay:
    """Explicit delay duration in milliseconds; never sleeps by itself."""

    milliseconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.milliseconds, int) or isinstance(self.milliseconds, bool):
            raise AdapterResilienceValidationError(
                "adapter retry delay milliseconds must be an integer"
            )
        if self.milliseconds < 0:
            raise AdapterResilienceValidationError(
                "adapter retry delay milliseconds must be non-negative"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.milliseconds,)


@dataclass(frozen=True, slots=True)
class AdapterTimeoutPolicy:
    """Explicit per-operation timeout policy without clock access."""

    operation_timeout: AdapterRetryDelay

    def __post_init__(self) -> None:
        if not isinstance(self.operation_timeout, AdapterRetryDelay):
            raise AdapterResilienceValidationError(
                "adapter timeout operation_timeout must be AdapterRetryDelay"
            )
        if self.operation_timeout.milliseconds <= 0:
            raise AdapterResilienceValidationError(
                "adapter timeout operation_timeout must be positive"
            )

    def logical_values(self) -> tuple[object, ...]:
        return self.operation_timeout.logical_values()


@dataclass(frozen=True, slots=True)
class AdapterRetryPolicy:
    """Immutable retry policy with an explicit deterministic delay schedule."""

    max_attempts: int = 1
    delay_schedule: tuple[AdapterRetryDelay, ...] = ()
    retryable_failures: tuple[AdapterRetryableFailure, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.max_attempts, int) or isinstance(self.max_attempts, bool):
            raise AdapterResilienceValidationError(
                "adapter retry max_attempts must be an integer"
            )
        if self.max_attempts < 1:
            raise AdapterResilienceValidationError(
                "adapter retry max_attempts must be at least one"
            )
        if not isinstance(self.delay_schedule, tuple):
            raise AdapterResilienceValidationError(
                "adapter retry delay_schedule must be a tuple"
            )
        if len(self.delay_schedule) != self.max_attempts - 1:
            raise AdapterResilienceValidationError(
                "adapter retry delay_schedule must contain one delay per retry"
            )
        for delay in self.delay_schedule:
            if not isinstance(delay, AdapterRetryDelay):
                raise AdapterResilienceValidationError(
                    "adapter retry delay_schedule entries must be AdapterRetryDelay"
                )
        if not isinstance(self.retryable_failures, tuple):
            raise AdapterResilienceValidationError(
                "adapter retry retryable_failures must be a tuple"
            )
        for failure in self.retryable_failures:
            if not isinstance(failure, AdapterRetryableFailure):
                raise AdapterResilienceValidationError(
                    "adapter retry retryable_failures entries must be "
                    "AdapterRetryableFailure"
                )
        ordered_failures = tuple(sorted(set(self.retryable_failures), key=lambda item: item.value))
        object.__setattr__(self, "retryable_failures", ordered_failures)

    @property
    def retries_enabled(self) -> bool:
        """Return whether this policy allows at least one retry attempt."""
        return self.max_attempts > 1

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.max_attempts,
            tuple(delay.logical_values() for delay in self.delay_schedule),
            tuple(failure.value for failure in self.retryable_failures),
        )


@dataclass(frozen=True, slots=True)
class AdapterRateLimitPolicy:
    """Provider-neutral rate-limit declaration without counters or sleeps."""

    request_limit: int
    window: AdapterRetryDelay
    burst_capacity: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_limit, int) or isinstance(self.request_limit, bool):
            raise AdapterResilienceValidationError(
                "adapter rate limit request_limit must be an integer"
            )
        if self.request_limit < 1:
            raise AdapterResilienceValidationError(
                "adapter rate limit request_limit must be positive"
            )
        if not isinstance(self.window, AdapterRetryDelay):
            raise AdapterResilienceValidationError(
                "adapter rate limit window must be AdapterRetryDelay"
            )
        if self.window.milliseconds <= 0:
            raise AdapterResilienceValidationError(
                "adapter rate limit window must be positive"
            )
        if self.burst_capacity is not None:
            if not isinstance(self.burst_capacity, int) or isinstance(self.burst_capacity, bool):
                raise AdapterResilienceValidationError(
                    "adapter rate limit burst_capacity must be an integer or None"
                )
            if self.burst_capacity < 1 or self.burst_capacity > self.request_limit:
                raise AdapterResilienceValidationError(
                    "adapter rate limit burst_capacity must be between one and "
                    "request_limit"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_limit,
            self.window.logical_values(),
            self.burst_capacity,
        )


@dataclass(frozen=True, slots=True)
class AdapterCircuitBreakerSnapshot:
    """Observable circuit-breaker state supplied explicitly by instrumentation."""

    state: AdapterCircuitBreakerState
    observed_at: datetime
    failure_count: int = 0
    recovery_delay: AdapterRetryDelay | None = None
    message: str | None = None
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.state, AdapterCircuitBreakerState):
            raise AdapterResilienceValidationError(
                "adapter circuit breaker state must be AdapterCircuitBreakerState"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if not isinstance(self.failure_count, int) or isinstance(self.failure_count, bool):
            raise AdapterResilienceValidationError(
                "adapter circuit breaker failure_count must be an integer"
            )
        if self.failure_count < 0:
            raise AdapterResilienceValidationError(
                "adapter circuit breaker failure_count must be non-negative"
            )
        if self.recovery_delay is not None and not isinstance(
            self.recovery_delay,
            AdapterRetryDelay,
        ):
            raise AdapterResilienceValidationError(
                "adapter circuit breaker recovery_delay must be AdapterRetryDelay or None"
            )
        if self.state is AdapterCircuitBreakerState.OPEN and self.recovery_delay is None:
            raise AdapterResilienceValidationError(
                "open adapter circuit breaker must declare recovery_delay"
            )
        if self.state is not AdapterCircuitBreakerState.OPEN and self.recovery_delay is not None:
            raise AdapterResilienceValidationError(
                "non-open adapter circuit breaker must not declare recovery_delay"
            )
        if self.message is not None:
            _validate_public_text(self.message, field_name="adapter circuit breaker message")
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.state.value,
            self.observed_at.isoformat(),
            self.failure_count,
            self.recovery_delay.logical_values() if self.recovery_delay is not None else None,
            self.message,
            tuple(self.metadata.items()),
        )


@dataclass(frozen=True, slots=True)
class AdapterResiliencePolicy:
    """Immutable declarative resilience policy for one provider/source boundary."""

    provider: ProviderDescriptor
    source: ExternalSourceDescriptor
    timeout: AdapterTimeoutPolicy
    retry: AdapterRetryPolicy = field(default_factory=AdapterRetryPolicy)
    rate_limit: AdapterRateLimitPolicy | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider, ProviderDescriptor):
            raise AdapterResilienceValidationError(
                "adapter resilience provider must be ProviderDescriptor"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise AdapterResilienceValidationError(
                "adapter resilience source must be ExternalSourceDescriptor"
            )
        if not isinstance(self.timeout, AdapterTimeoutPolicy):
            raise AdapterResilienceValidationError(
                "adapter resilience timeout must be AdapterTimeoutPolicy"
            )
        if not isinstance(self.retry, AdapterRetryPolicy):
            raise AdapterResilienceValidationError(
                "adapter resilience retry must be AdapterRetryPolicy"
            )
        if self.rate_limit is not None and not isinstance(
            self.rate_limit,
            AdapterRateLimitPolicy,
        ):
            raise AdapterResilienceValidationError(
                "adapter resilience rate_limit must be AdapterRateLimitPolicy or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.source.logical_values(),
            self.timeout.logical_values(),
            self.retry.logical_values(),
            self.rate_limit.logical_values() if self.rate_limit is not None else None,
        )


@dataclass(frozen=True, slots=True)
class AdapterResilienceSnapshot:
    """Observable resilience snapshot without executing sleeps, IO, or network."""

    policy: AdapterResiliencePolicy
    observed_at: datetime
    circuit_breaker: AdapterCircuitBreakerSnapshot | None = None
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.policy, AdapterResiliencePolicy):
            raise AdapterResilienceValidationError(
                "adapter resilience snapshot policy must be AdapterResiliencePolicy"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if self.circuit_breaker is not None and not isinstance(
            self.circuit_breaker,
            AdapterCircuitBreakerSnapshot,
        ):
            raise AdapterResilienceValidationError(
                "adapter resilience snapshot circuit_breaker must be "
                "AdapterCircuitBreakerSnapshot or None"
            )
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy.logical_values(),
            self.observed_at.isoformat(),
            self.circuit_breaker.logical_values()
            if self.circuit_breaker is not None
            else None,
            tuple(self.metadata.items()),
        )


class AdapterResilienceBoundary(Protocol):
    """Structural boundary exposing resilience policy and observable state."""

    @property
    def policy(self) -> AdapterResiliencePolicy:
        """Return the immutable resilience policy for this adapter boundary."""
        ...

    def resilience_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[AdapterResilienceSnapshot, AdapterResilienceError]:
        """Return a typed resilience snapshot without executing side effects."""
        ...
