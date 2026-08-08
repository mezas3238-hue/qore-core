from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.infrastructure.execution_boundary import (
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionObservation,
    ExecutionReconciliationStatus,
    ExecutionReconciliationValidationError,
    observe_execution_receipt,
    reconcile_execution,
)
from qore.infrastructure.order_intent import ExecutionIdempotencyKey
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 7, 0, tzinfo=UTC)
_RECEIPT_ID = ExecutionReceiptId(UUID("b1000000-0000-0000-0000-000000000001"))
_REQUEST_ID = ExecutionRequestId(UUID("b1000000-0000-0000-0000-000000000002"))
_IDEMPOTENCY = ExecutionIdempotencyKey(
    UUID("b1000000-0000-0000-0000-000000000003")
)


def _receipt(status: ExecutionStatus = ExecutionStatus.ACCEPTED) -> ExecutionReceipt:
    return ExecutionReceipt(
        receipt_id=_RECEIPT_ID,
        request_id=_REQUEST_ID,
        idempotency_key=_IDEMPOTENCY,
        status=status,
        recorded_at=_NOW,
    )


def _observation(
    *,
    status: ExecutionStatus = ExecutionStatus.ACCEPTED,
    receipt_id: ExecutionReceiptId = _RECEIPT_ID,
) -> ExecutionObservation:
    return ExecutionObservation(
        receipt_id=receipt_id,
        request_id=_REQUEST_ID,
        idempotency_key=_IDEMPOTENCY,
        status=status,
        observed_at=_NOW + timedelta(seconds=1),
    )


def test_matching_receipt_and_observation_reconcile_as_matched() -> None:
    result = reconcile_execution(
        _receipt(),
        _observation(),
        reconciled_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.status is ExecutionReconciliationStatus.MATCHED
    assert result.value.issues == ()
    assert result.value.requires_manual_action is False


def test_status_difference_reconciles_as_diverged_without_correction() -> None:
    result = reconcile_execution(
        _receipt(),
        _observation(status=ExecutionStatus.CANCELLED),
        reconciled_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.status is ExecutionReconciliationStatus.DIVERGED
    assert result.value.issues == ("status_mismatch",)
    assert result.value.requires_manual_action is True
    assert not hasattr(result.value, "correct")
    assert not hasattr(result.value, "resubmit")


def test_identity_difference_is_reported_as_diverged() -> None:
    result = reconcile_execution(
        _receipt(),
        _observation(
            receipt_id=ExecutionReceiptId(
                UUID("b1000000-0000-0000-0000-000000000009")
            )
        ),
        reconciled_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.status is ExecutionReconciliationStatus.DIVERGED
    assert result.value.issues == ("receipt_id_mismatch",)


def test_expected_without_observation_is_missing() -> None:
    result = reconcile_execution(
        _receipt(),
        None,
        reconciled_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.status is ExecutionReconciliationStatus.MISSING
    assert result.value.requires_manual_action is True


def test_observation_without_expected_is_unexpected() -> None:
    result = reconcile_execution(
        None,
        _observation(),
        reconciled_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.status is ExecutionReconciliationStatus.UNEXPECTED
    assert result.value.requires_manual_action is True


def test_reconciliation_requires_expected_or_observed_state() -> None:
    result = reconcile_execution(
        None,
        None,
        reconciled_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutionReconciliationValidationError)


def test_observe_receipt_copies_only_provider_neutral_execution_identity() -> None:
    result = observe_execution_receipt(
        _receipt(),
        observed_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.receipt_id == _RECEIPT_ID
    assert result.value.request_id == _REQUEST_ID
    assert result.value.idempotency_key == _IDEMPOTENCY
    assert result.value.status is ExecutionStatus.ACCEPTED
