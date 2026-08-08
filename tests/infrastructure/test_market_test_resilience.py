from qore.infrastructure.adapter_resilience import (
    AdapterRetryableFailure,
    AdapterRetryDelay,
    AdapterRetryPolicy,
)
from qore.infrastructure.execution_reconciliation import ExecutionReconciliationStatus
from qore.infrastructure.market_test_resilience import (
    MarketTestFailureKind,
    MarketTestRecoveryAction,
    decide_market_test_recovery,
    reconciliation_recovery_decision,
)
from qore.kernel.result import Success


def _policy() -> AdapterRetryPolicy:
    return AdapterRetryPolicy(
        max_attempts=3,
        delay_schedule=(AdapterRetryDelay(100), AdapterRetryDelay(250)),
        retryable_failures=(
            AdapterRetryableFailure.THROTTLED,
            AdapterRetryableFailure.TIMEOUT,
            AdapterRetryableFailure.UNAVAILABLE,
        ),
    )


def test_timeout_returns_declarative_retry_read() -> None:
    result = decide_market_test_recovery(
        MarketTestFailureKind.TIMEOUT,
        retry_policy=_policy(),
        attempts_used=1,
    )

    assert isinstance(result, Success)
    assert result.value.action is MarketTestRecoveryAction.RETRY_READ
    assert result.value.retry_delay == AdapterRetryDelay(100)
    assert result.value.remaining_attempts == 2
    assert result.value.corrective_execution_allowed is False


def test_unavailable_returns_reconnect_without_executing_it() -> None:
    result = decide_market_test_recovery(
        MarketTestFailureKind.UNAVAILABLE,
        retry_policy=_policy(),
        attempts_used=2,
    )

    assert isinstance(result, Success)
    assert result.value.action is MarketTestRecoveryAction.RECONNECT
    assert result.value.retry_delay == AdapterRetryDelay(250)
    assert result.value.remaining_attempts == 1


def test_retry_budget_exhaustion_contains_failure() -> None:
    result = decide_market_test_recovery(
        MarketTestFailureKind.TIMEOUT,
        retry_policy=_policy(),
        attempts_used=3,
    )

    assert isinstance(result, Success)
    assert result.value.action is MarketTestRecoveryAction.CONTAIN
    assert result.value.retry_delay is None
    assert result.value.remaining_attempts == 0


def test_stale_market_data_stops_decision_flow() -> None:
    result = decide_market_test_recovery(
        MarketTestFailureKind.STALE_MARKET_DATA,
        retry_policy=_policy(),
        attempts_used=1,
    )

    assert isinstance(result, Success)
    assert result.value.action is MarketTestRecoveryAction.STOP
    assert result.value.corrective_execution_allowed is False


def test_ambiguous_execution_is_never_retried_or_resubmitted() -> None:
    result = decide_market_test_recovery(
        MarketTestFailureKind.EXECUTION_AMBIGUOUS,
        retry_policy=_policy(),
        attempts_used=1,
    )

    assert isinstance(result, Success)
    assert result.value.action is MarketTestRecoveryAction.CONTAIN
    assert result.value.retry_delay is None
    assert result.value.corrective_execution_allowed is False


def test_provider_rejection_is_contained_without_corrective_execution() -> None:
    result = decide_market_test_recovery(
        MarketTestFailureKind.PROVIDER_REJECTION,
        retry_policy=_policy(),
        attempts_used=1,
    )

    assert isinstance(result, Success)
    assert result.value.action is MarketTestRecoveryAction.CONTAIN
    assert result.value.corrective_execution_allowed is False


def test_matched_reconciliation_needs_no_recovery() -> None:
    result = reconciliation_recovery_decision(
        ExecutionReconciliationStatus.MATCHED,
        retry_policy=_policy(),
    )

    assert isinstance(result, Success)
    assert result.value is None


def test_diverged_reconciliation_is_always_contained() -> None:
    result = reconciliation_recovery_decision(
        ExecutionReconciliationStatus.DIVERGED,
        retry_policy=_policy(),
    )

    assert isinstance(result, Success)
    assert result.value is not None
    assert result.value.action is MarketTestRecoveryAction.CONTAIN
    assert result.value.corrective_execution_allowed is False
