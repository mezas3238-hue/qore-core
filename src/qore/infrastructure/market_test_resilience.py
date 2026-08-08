from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.adapter_resilience import (
    AdapterRetryableFailure,
    AdapterRetryDelay,
    AdapterRetryPolicy,
)
from qore.infrastructure.execution_reconciliation import ExecutionReconciliationStatus
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success


class MarketTestResilienceError(ExternalPortError):
    """Base error for MISSION-02 deterministic recovery decisions."""

    __slots__ = ()


class MarketTestResilienceValidationError(MarketTestResilienceError):
    """Violation of market-test resilience invariants."""

    __slots__ = ()


class MarketTestFailureKind(StrEnum):
    TIMEOUT = "timeout"
    THROTTLED = "throttled"
    UNAVAILABLE = "unavailable"
    STALE_MARKET_DATA = "stale_market_data"
    PROVIDER_REJECTION = "provider_rejection"
    EXECUTION_AMBIGUOUS = "execution_ambiguous"
    RECONCILIATION_DIVERGED = "reconciliation_diverged"


class MarketTestRecoveryAction(StrEnum):
    RETRY_READ = "retry_read"
    RECONNECT = "reconnect"
    CONTAIN = "contain"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class MarketTestRecoveryDecision:
    failure: MarketTestFailureKind
    action: MarketTestRecoveryAction
    retry_delay: AdapterRetryDelay | None
    remaining_attempts: int
    corrective_execution_allowed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.failure, MarketTestFailureKind):
            raise MarketTestResilienceValidationError(
                "recovery failure must be MarketTestFailureKind"
            )
        if not isinstance(self.action, MarketTestRecoveryAction):
            raise MarketTestResilienceValidationError(
                "recovery action must be MarketTestRecoveryAction"
            )
        if self.retry_delay is not None and not isinstance(
            self.retry_delay, AdapterRetryDelay
        ):
            raise MarketTestResilienceValidationError(
                "recovery retry_delay must be AdapterRetryDelay or None"
            )
        if (
            not isinstance(self.remaining_attempts, int)
            or isinstance(self.remaining_attempts, bool)
            or self.remaining_attempts < 0
        ):
            raise MarketTestResilienceValidationError(
                "remaining_attempts must be a non-negative integer"
            )
        if not isinstance(self.corrective_execution_allowed, bool):
            raise MarketTestResilienceValidationError(
                "corrective_execution_allowed must be bool"
            )
        if self.corrective_execution_allowed:
            raise MarketTestResilienceValidationError(
                "MISSION-02 never permits corrective execution"
            )
        if self.action in {
            MarketTestRecoveryAction.CONTAIN,
            MarketTestRecoveryAction.STOP,
        } and self.retry_delay is not None:
            raise MarketTestResilienceValidationError(
                "contain/stop decisions must not declare retry delay"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.failure.value,
            self.action.value,
            self.retry_delay.logical_values() if self.retry_delay is not None else None,
            self.remaining_attempts,
            self.corrective_execution_allowed,
        )


def decide_market_test_recovery(
    failure: MarketTestFailureKind,
    *,
    retry_policy: AdapterRetryPolicy,
    attempts_used: int,
) -> Result[MarketTestRecoveryDecision, MarketTestResilienceError]:
    """Return one declarative recovery decision; never loop, sleep or resubmit orders."""
    if not isinstance(failure, MarketTestFailureKind):
        return Failure(
            MarketTestResilienceValidationError(
                "market-test recovery requires MarketTestFailureKind"
            )
        )
    if not isinstance(retry_policy, AdapterRetryPolicy):
        return Failure(
            MarketTestResilienceValidationError(
                "market-test recovery requires AdapterRetryPolicy"
            )
        )
    if (
        not isinstance(attempts_used, int)
        or isinstance(attempts_used, bool)
        or attempts_used < 1
    ):
        return Failure(
            MarketTestResilienceValidationError(
                "attempts_used must be a positive integer"
            )
        )

    remaining = max(retry_policy.max_attempts - attempts_used, 0)
    if failure in {
        MarketTestFailureKind.EXECUTION_AMBIGUOUS,
        MarketTestFailureKind.PROVIDER_REJECTION,
        MarketTestFailureKind.RECONCILIATION_DIVERGED,
    }:
        return Success(
            MarketTestRecoveryDecision(
                failure=failure,
                action=MarketTestRecoveryAction.CONTAIN,
                retry_delay=None,
                remaining_attempts=0,
            )
        )
    if failure is MarketTestFailureKind.STALE_MARKET_DATA:
        return Success(
            MarketTestRecoveryDecision(
                failure=failure,
                action=MarketTestRecoveryAction.STOP,
                retry_delay=None,
                remaining_attempts=0,
            )
        )

    retryable_map = {
        MarketTestFailureKind.TIMEOUT: AdapterRetryableFailure.TIMEOUT,
        MarketTestFailureKind.THROTTLED: AdapterRetryableFailure.THROTTLED,
        MarketTestFailureKind.UNAVAILABLE: AdapterRetryableFailure.UNAVAILABLE,
    }
    retryable_failure = retryable_map[failure]
    if remaining == 0 or retryable_failure not in retry_policy.retryable_failures:
        return Success(
            MarketTestRecoveryDecision(
                failure=failure,
                action=MarketTestRecoveryAction.CONTAIN,
                retry_delay=None,
                remaining_attempts=0,
            )
        )
    delay_index = attempts_used - 1
    delay = retry_policy.delay_schedule[delay_index]
    action = (
        MarketTestRecoveryAction.RECONNECT
        if failure is MarketTestFailureKind.UNAVAILABLE
        else MarketTestRecoveryAction.RETRY_READ
    )
    return Success(
        MarketTestRecoveryDecision(
            failure=failure,
            action=action,
            retry_delay=delay,
            remaining_attempts=remaining,
        )
    )


def reconciliation_recovery_decision(
    status: ExecutionReconciliationStatus,
    *,
    retry_policy: AdapterRetryPolicy,
) -> Result[MarketTestRecoveryDecision | None, MarketTestResilienceError]:
    """MATCHED needs no recovery; every non-match is contained without trading."""
    if not isinstance(status, ExecutionReconciliationStatus):
        return Failure(
            MarketTestResilienceValidationError(
                "reconciliation recovery requires ExecutionReconciliationStatus"
            )
        )
    if status is ExecutionReconciliationStatus.MATCHED:
        return Success(None)
    return decide_market_test_recovery(
        MarketTestFailureKind.RECONCILIATION_DIVERGED,
        retry_policy=retry_policy,
        attempts_used=retry_policy.max_attempts,
    )
