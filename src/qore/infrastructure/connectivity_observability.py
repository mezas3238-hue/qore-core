from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.adapter_observability import (
    AdapterLatencyMeasurement,
    AdapterObservabilitySnapshot,
    AdapterObservedError,
    AdapterObservedErrorSeverity,
    AdapterReadiness,
)
from qore.infrastructure.connectivity import (
    ProviderConnectionState,
    ProviderConnectivitySnapshot,
)
from qore.infrastructure.ports import ExternalPortError, ExternalSourceDescriptor
from qore.infrastructure.providers import ProviderDescriptor
from qore.kernel.result import Failure, Result, Success


class ConnectivityObservabilityError(ExternalPortError):
    """Base error for sanitized live-connectivity observations."""

    __slots__ = ()


class ConnectivityObservabilityValidationError(ConnectivityObservabilityError):
    """Violation of a connectivity observation invariant."""

    __slots__ = ()


class ConnectivityFailureCategory(StrEnum):
    """Closed provider-neutral failure category safe for observation."""

    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    PROTOCOL = "protocol"
    UNAVAILABLE = "unavailable"
    AUTHENTICATION = "authentication"


@dataclass(frozen=True, slots=True)
class ConnectivityObservation:
    """Sanitized inputs supplied explicitly by transport instrumentation."""

    connectivity: ProviderConnectivitySnapshot
    source: ExternalSourceDescriptor
    latency_milliseconds: int | None = None
    failure: ConnectivityFailureCategory | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.connectivity, ProviderConnectivitySnapshot):
            raise ConnectivityObservabilityValidationError(
                "connectivity observation requires ProviderConnectivitySnapshot"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise ConnectivityObservabilityValidationError(
                "connectivity observation source must be ExternalSourceDescriptor"
            )
        if self.latency_milliseconds is not None and (
            type(self.latency_milliseconds) is not int
            or self.latency_milliseconds < 0
        ):
            raise ConnectivityObservabilityValidationError(
                "connectivity latency must be a non-negative int or None"
            )
        if self.failure is not None and not isinstance(
            self.failure, ConnectivityFailureCategory
        ):
            raise ConnectivityObservabilityValidationError(
                "connectivity failure must be ConnectivityFailureCategory or None"
            )
        if self.connectivity.state is ProviderConnectionState.READY and (
            self.failure is not None
        ):
            raise ConnectivityObservabilityValidationError(
                "ready connectivity must not carry a failure category"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.connectivity.logical_values(),
            self.source.logical_values(),
            self.latency_milliseconds,
            self.failure.value if self.failure is not None else None,
        )


def _readiness(state: ProviderConnectionState) -> AdapterReadiness:
    if state is ProviderConnectionState.READY:
        return AdapterReadiness.READY
    if state is ProviderConnectionState.DEGRADED:
        return AdapterReadiness.DEGRADED
    return AdapterReadiness.UNAVAILABLE


def observe_live_connectivity(
    provider: ProviderDescriptor,
    observation: ConnectivityObservation,
    *,
    observed_at: datetime,
) -> Result[AdapterObservabilitySnapshot, ExternalPortError]:
    """Project connectivity state into existing sanitized adapter observability."""
    if not isinstance(provider, ProviderDescriptor):
        return Failure(
            ConnectivityObservabilityValidationError(
                "connectivity observability provider must be ProviderDescriptor"
            )
        )
    if not isinstance(observation, ConnectivityObservation):
        return Failure(
            ConnectivityObservabilityValidationError(
                "connectivity observability observation must be ConnectivityObservation"
            )
        )
    if provider != observation.connectivity.intent.provider:
        return Failure(
            ConnectivityObservabilityValidationError(
                "connectivity observability provider identity must match intent"
            )
        )
    readiness = _readiness(observation.connectivity.state)
    last_errors: tuple[AdapterObservedError, ...] = ()
    message: str | None = None
    if readiness is not AdapterReadiness.READY:
        message = observation.connectivity.message or "connectivity not ready"
    if observation.failure is not None:
        last_errors = (
            AdapterObservedError(
                error_type=f"connectivity.{observation.failure.value}",
                message=f"connectivity failure category: {observation.failure.value}",
                severity=(
                    AdapterObservedErrorSeverity.WARNING
                    if readiness is AdapterReadiness.DEGRADED
                    else AdapterObservedErrorSeverity.ERROR
                ),
                observed_at=observed_at,
            ),
        )
    try:
        snapshot = AdapterObservabilitySnapshot(
            provider=provider,
            source=observation.source,
            readiness=readiness,
            observed_at=observed_at,
            latency=(
                AdapterLatencyMeasurement(observation.latency_milliseconds)
                if observation.latency_milliseconds is not None
                else None
            ),
            last_errors=last_errors,
            message=message,
            metadata={"connectivity_state": observation.connectivity.state.value},
        )
    except ExternalPortError as error:
        return Failure(error)
    return Success(snapshot)
