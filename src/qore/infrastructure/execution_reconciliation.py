from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.execution_boundary import (
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
)
from qore.infrastructure.order_intent import ExecutionIdempotencyKey
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success


class ExecutionReconciliationError(ExternalPortError):
    """Base error for execution reconciliation contracts."""

    __slots__ = ()


class ExecutionReconciliationValidationError(ExecutionReconciliationError):
    """Violation of an execution reconciliation invariant."""

    __slots__ = ()


class ExecutionReconciliationStatus(StrEnum):
    MATCHED = "matched"
    DIVERGED = "diverged"
    MISSING = "missing"
    UNEXPECTED = "unexpected"


@dataclass(frozen=True, slots=True)
class ExecutionObservation:
    """Provider-neutral observation without account or secret data."""

    receipt_id: ExecutionReceiptId
    request_id: ExecutionRequestId
    idempotency_key: ExecutionIdempotencyKey
    status: ExecutionStatus
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_id, ExecutionReceiptId):
            raise ExecutionReconciliationValidationError(
                "execution observation receipt_id must be ExecutionReceiptId"
            )
        if not isinstance(self.request_id, ExecutionRequestId):
            raise ExecutionReconciliationValidationError(
                "execution observation request_id must be ExecutionRequestId"
            )
        if not isinstance(self.idempotency_key, ExecutionIdempotencyKey):
            raise ExecutionReconciliationValidationError(
                "execution observation idempotency_key must be ExecutionIdempotencyKey"
            )
        if not isinstance(self.status, ExecutionStatus):
            raise ExecutionReconciliationValidationError(
                "execution observation status must be ExecutionStatus"
            )
        if not isinstance(self.observed_at, datetime):
            raise ExecutionReconciliationValidationError(
                "execution observation observed_at must be a datetime"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ExecutionReconciliationValidationError(
                "execution observation observed_at must be timezone-aware"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.receipt_id.logical_values(),
            self.request_id.logical_values(),
            self.idempotency_key.logical_values(),
            self.status.value,
            self.observed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutionReconciliationSnapshot:
    """Pure comparison result. It never performs corrective execution."""

    status: ExecutionReconciliationStatus
    reconciled_at: datetime
    expected: ExecutionReceipt | None = None
    observed: ExecutionObservation | None = None
    issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, ExecutionReconciliationStatus):
            raise ExecutionReconciliationValidationError(
                "reconciliation status must be ExecutionReconciliationStatus"
            )
        if not isinstance(self.reconciled_at, datetime):
            raise ExecutionReconciliationValidationError(
                "reconciled_at must be a datetime"
            )
        if self.reconciled_at.tzinfo is None or self.reconciled_at.utcoffset() is None:
            raise ExecutionReconciliationValidationError(
                "reconciled_at must be timezone-aware"
            )
        if self.expected is not None and not isinstance(self.expected, ExecutionReceipt):
            raise ExecutionReconciliationValidationError(
                "expected must be ExecutionReceipt or None"
            )
        if self.observed is not None and not isinstance(
            self.observed, ExecutionObservation
        ):
            raise ExecutionReconciliationValidationError(
                "observed must be ExecutionObservation or None"
            )
        if not isinstance(self.issues, tuple) or any(
            not isinstance(issue, str) or not issue for issue in self.issues
        ):
            raise ExecutionReconciliationValidationError(
                "reconciliation issues must be non-empty strings in a tuple"
            )
        if self.status is ExecutionReconciliationStatus.MATCHED and self.issues:
            raise ExecutionReconciliationValidationError(
                "matched reconciliation must not carry issues"
            )
        if self.status is not ExecutionReconciliationStatus.MATCHED and not self.issues:
            raise ExecutionReconciliationValidationError(
                "non-matched reconciliation requires at least one issue"
            )

    @property
    def requires_manual_action(self) -> bool:
        return self.status is not ExecutionReconciliationStatus.MATCHED

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.status.value,
            self.reconciled_at.isoformat(),
            self.expected.logical_values() if self.expected is not None else None,
            self.observed.logical_values() if self.observed is not None else None,
            self.issues,
        )


def observe_execution_receipt(
    receipt: ExecutionReceipt,
    *,
    observed_at: datetime,
) -> Result[ExecutionObservation, ExecutionReconciliationError]:
    """Project a sandbox/provider-neutral receipt into observation form."""
    if not isinstance(receipt, ExecutionReceipt):
        return Failure(
            ExecutionReconciliationValidationError(
                "execution receipt observation requires ExecutionReceipt"
            )
        )
    try:
        return Success(
            ExecutionObservation(
                receipt_id=receipt.receipt_id,
                request_id=receipt.request_id,
                idempotency_key=receipt.idempotency_key,
                status=receipt.status,
                observed_at=observed_at,
            )
        )
    except ExecutionReconciliationError as error:
        return Failure(error)


def reconcile_execution(
    expected: ExecutionReceipt | None,
    observed: ExecutionObservation | None,
    *,
    reconciled_at: datetime,
) -> Result[ExecutionReconciliationSnapshot, ExecutionReconciliationError]:
    """Compare expected and observed execution state without side effects."""
    if expected is None and observed is None:
        return Failure(
            ExecutionReconciliationValidationError(
                "reconciliation requires expected or observed execution state"
            )
        )
    if expected is not None and not isinstance(expected, ExecutionReceipt):
        return Failure(
            ExecutionReconciliationValidationError(
                "expected execution must be ExecutionReceipt or None"
            )
        )
    if observed is not None and not isinstance(observed, ExecutionObservation):
        return Failure(
            ExecutionReconciliationValidationError(
                "observed execution must be ExecutionObservation or None"
            )
        )

    if expected is not None and observed is None:
        status = ExecutionReconciliationStatus.MISSING
        issues = ("expected_execution_missing_observation",)
    elif expected is None and observed is not None:
        status = ExecutionReconciliationStatus.UNEXPECTED
        issues = ("unexpected_execution_observation",)
    else:
        assert expected is not None
        assert observed is not None
        issue_list: list[str] = []
        if expected.receipt_id != observed.receipt_id:
            issue_list.append("receipt_id_mismatch")
        if expected.request_id != observed.request_id:
            issue_list.append("request_id_mismatch")
        if expected.idempotency_key != observed.idempotency_key:
            issue_list.append("idempotency_key_mismatch")
        if expected.status is not observed.status:
            issue_list.append("status_mismatch")
        if issue_list:
            status = ExecutionReconciliationStatus.DIVERGED
            issues = tuple(issue_list)
        else:
            status = ExecutionReconciliationStatus.MATCHED
            issues = ()
    try:
        snapshot = ExecutionReconciliationSnapshot(
            status=status,
            reconciled_at=reconciled_at,
            expected=expected,
            observed=observed,
            issues=issues,
        )
    except ExecutionReconciliationError as error:
        return Failure(error)
    return Success(snapshot)
