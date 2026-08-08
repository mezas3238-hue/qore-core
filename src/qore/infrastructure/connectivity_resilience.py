from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.adapter_resilience import (
    AdapterCircuitBreakerState,
    AdapterResiliencePolicy,
    AdapterResilienceSnapshot,
    AdapterRetryDelay,
    AdapterRetryableFailure,
)
from qore.infrastructure.connectivity_observability import ConnectivityFailureCategory
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success


class ConnectivityResilienceError(ExternalPortError):
    """Base error for pure connectivity retry/reconnect decisions."""

    __slots__ = ()


class ConnectivityResilienceValidationError(ConnectivityResilienceError):
    """Violation of a connectivity resilience invariant."""

    __slots__ = ()


class ConnectivityRecoveryDecision(StrEnum):
    """Closed side-effect-free recovery decision."""

    RETRY = "retry"
    RECONNECT = "reconnect"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class ConnectivityRecoveryRequest:
    """Explicit failure and attempt state for one pure recovery decision."""

    failure: ConnectivityFailureCategory
    attempt: int

    def __post_init__(self) -> None:
        if not isinstance(self.failure, ConnectivityFailureCategory):
            raise ConnectivityResilienceValidationError(
                "connectivity recovery failure must be ConnectivityFailureCategory"
            )
        if type(self.attempt) is not int or self.attempt < 1:
            raise ConnectivityResilienceValidationError(
                "connectivity recovery attempt must be a positive int"
            )


@dataclass(frozen=True, slots=True)
class ConnectivityRecoveryPlan:
    """Deterministic recovery plan; delay is descriptive and never sleeps."""

    decision: ConnectivityRecoveryDecision
    attempt: int
    delay: AdapterRetryDelay | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ConnectivityRecoveryDecision):
            raise ConnectivityResilienceValidationError(
                "connectivity recovery decision must be ConnectivityRecoveryDecision"
            )
        if type(self.attempt) is not int or self.attempt < 1:
            raise ConnectivityResilienceValidationError(
                "connectivity recovery plan attempt must be a positive int"
            )
        if self.delay is not None and not isinstance(self.delay, AdapterRetryDelay):
            raise ConnectivityResilienceValidationError(
                "connectivity recovery delay must be AdapterRetryDelay or None"
            )
        if self.decision is ConnectivityRecoveryDecision.STOP and self.delay is not None:
            raise ConnectivityResilienceValidationError(
                "stopped connectivity recovery must not carry a delay"
            )
        if not isinstance(self.reason, str) or not self.reason:
            raise ConnectivityResilienceValidationError(
                "connectivity recovery plan requires a reason"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.decision.value,
            self.attempt,
            self.delay.logical_values() if self.delay is not None else None,
            self.reason,
        )


def _retryable_category(
    failure: ConnectivityFailureCategory,
) -> AdapterRetryableFailure | None:
    if failure is ConnectivityFailureCategory.TIMEOUT:
        return AdapterRetryableFailure.TIMEOUT
    if failure is ConnectivityFailureCategory.RATE_LIMITED:
        return AdapterRetryableFailure.THROTTLED
    if failure is ConnectivityFailureCategory.UNAVAILABLE:
        return AdapterRetryableFailure.UNAVAILABLE
    return None


def plan_connectivity_recovery(
    policy: AdapterResiliencePolicy,
    snapshot: AdapterResilienceSnapshot,
    request: ConnectivityRecoveryRequest,
) -> Result[ConnectivityRecoveryPlan, ExternalPortError]:
    """Plan retry/reconnect from existing resilience contracts without side effects."""
    if not isinstance(policy, AdapterResiliencePolicy):
        return Failure(
            ConnectivityResilienceValidationError(
                "connectivity recovery policy must be AdapterResiliencePolicy"
            )
        )
    if not isinstance(snapshot, AdapterResilienceSnapshot):
        return Failure(
            ConnectivityResilienceValidationError(
                "connectivity recovery snapshot must be AdapterResilienceSnapshot"
            )
        )
    if not isinstance(request, ConnectivityRecoveryRequest):
        return Failure(
            ConnectivityResilienceValidationError(
                "connectivity recovery request must be ConnectivityRecoveryRequest"
            )
        )
    if snapshot.policy != policy:
        return Failure(
            ConnectivityResilienceValidationError(
                "connectivity recovery snapshot policy must match policy"
            )
        )

    breaker = snapshot.circuit_breaker
    if breaker is not None and breaker.state is AdapterCircuitBreakerState.OPEN:
        return Success(
            ConnectivityRecoveryPlan(
                decision=ConnectivityRecoveryDecision.STOP,
                attempt=request.attempt,
                reason="circuit_breaker_open",
            )
        )

    retryable = _retryable_category(request.failure)
    if retryable is None or retryable not in policy.retry.retryable_failures:
        return Success(
            ConnectivityRecoveryPlan(
                decision=ConnectivityRecoveryDecision.STOP,
                attempt=request.attempt,
                reason="failure_not_retryable",
            )
        )
    if request.attempt >= policy.retry.max_attempts:
        return Success(
            ConnectivityRecoveryPlan(
                decision=ConnectivityRecoveryDecision.STOP,
                attempt=request.attempt,
                reason="retry_budget_exhausted",
            )
        )

    delay = policy.retry.delay_schedule[request.attempt - 1]
    decision = (
        ConnectivityRecoveryDecision.RECONNECT
        if request.failure is ConnectivityFailureCategory.UNAVAILABLE
        else ConnectivityRecoveryDecision.RETRY
    )
    return Success(
        ConnectivityRecoveryPlan(
            decision=decision,
            attempt=request.attempt,
            delay=delay,
            reason="policy_allows_recovery",
        )
    )
