from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from qore.infrastructure.order_intent import ExecutionIdempotencyKey
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.pretrade_safety import AuthorizedOrderIntent
from qore.kernel.result import Failure, Result, Success


class ExecutionBoundaryError(ExternalPortError):
    """Base error for the controlled execution boundary."""

    __slots__ = ()


class ExecutionBoundaryValidationError(ExecutionBoundaryError):
    """Violation of an execution boundary invariant."""

    __slots__ = ()


class ExecutionBoundaryConflictError(ExecutionBoundaryError):
    """Typed idempotency or execution-state conflict."""

    __slots__ = ()


class ExecutionBoundaryNotFoundError(ExecutionBoundaryError):
    """Typed result for an unknown execution receipt."""

    __slots__ = ()


class ExecutionStatus(StrEnum):
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ExecutionRequestId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutionBoundaryValidationError("execution request id must be UUID")

    def logical_values(self) -> tuple[UUID, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutionReceiptId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutionBoundaryValidationError("execution receipt id must be UUID")

    def logical_values(self) -> tuple[UUID, ...]:
        return (self.value,)


def _validate_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutionBoundaryValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutionBoundaryValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ExecutionSubmission:
    """Explicit sandbox submission of an already-authorized order intent."""

    request_id: ExecutionRequestId
    receipt_id: ExecutionReceiptId
    authorized_intent: AuthorizedOrderIntent
    submitted_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, ExecutionRequestId):
            raise ExecutionBoundaryValidationError(
                "execution submission request_id must be ExecutionRequestId"
            )
        if not isinstance(self.receipt_id, ExecutionReceiptId):
            raise ExecutionBoundaryValidationError(
                "execution submission receipt_id must be ExecutionReceiptId"
            )
        if not isinstance(self.authorized_intent, AuthorizedOrderIntent):
            raise ExecutionBoundaryValidationError(
                "execution submission requires AuthorizedOrderIntent"
            )
        _validate_datetime(self.submitted_at, field_name="submitted_at")
        if self.submitted_at < self.authorized_intent.authorized_at:
            raise ExecutionBoundaryValidationError(
                "execution submission must not predate authorization"
            )
        if self.submitted_at > self.authorized_intent.authorization.expires_at:
            raise ExecutionBoundaryValidationError(
                "execution submission authorization is expired"
            )
        if not self.authorized_intent.switch.allows_execution:
            raise ExecutionBoundaryValidationError(
                "execution submission requires enabled execution switch"
            )

    @property
    def idempotency_key(self) -> ExecutionIdempotencyKey:
        return self.authorized_intent.intent.idempotency_key

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_id.logical_values(),
            self.receipt_id.logical_values(),
            self.authorized_intent.logical_values(),
            self.submitted_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    """Provider-neutral sandbox receipt; no broker/account identifiers."""

    receipt_id: ExecutionReceiptId
    request_id: ExecutionRequestId
    idempotency_key: ExecutionIdempotencyKey
    status: ExecutionStatus
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_id, ExecutionReceiptId):
            raise ExecutionBoundaryValidationError(
                "execution receipt receipt_id must be ExecutionReceiptId"
            )
        if not isinstance(self.request_id, ExecutionRequestId):
            raise ExecutionBoundaryValidationError(
                "execution receipt request_id must be ExecutionRequestId"
            )
        if not isinstance(self.idempotency_key, ExecutionIdempotencyKey):
            raise ExecutionBoundaryValidationError(
                "execution receipt idempotency_key must be ExecutionIdempotencyKey"
            )
        if not isinstance(self.status, ExecutionStatus):
            raise ExecutionBoundaryValidationError(
                "execution receipt status must be ExecutionStatus"
            )
        _validate_datetime(self.recorded_at, field_name="recorded_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.receipt_id.logical_values(),
            self.request_id.logical_values(),
            self.idempotency_key.logical_values(),
            self.status.value,
            self.recorded_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutionCancellation:
    receipt_id: ExecutionReceiptId
    cancelled_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_id, ExecutionReceiptId):
            raise ExecutionBoundaryValidationError(
                "execution cancellation receipt_id must be ExecutionReceiptId"
            )
        _validate_datetime(self.cancelled_at, field_name="cancelled_at")


class ExecutionBoundary(Protocol):
    """Provider-neutral controlled execution boundary."""

    def submit(
        self,
        submission: ExecutionSubmission,
    ) -> Result[ExecutionReceipt, ExecutionBoundaryError]: ...

    def status(
        self,
        receipt_id: ExecutionReceiptId,
    ) -> Result[ExecutionReceipt | None, ExecutionBoundaryError]: ...

    def cancel(
        self,
        cancellation: ExecutionCancellation,
    ) -> Result[ExecutionReceipt, ExecutionBoundaryError]: ...


class SandboxExecutionBoundary:
    """Instance-local deterministic execution sandbox with no external IO."""

    __slots__ = ("_idempotency", "_receipts")

    def __init__(self) -> None:
        self._receipts: dict[ExecutionReceiptId, ExecutionReceipt] = {}
        self._idempotency: dict[
            ExecutionIdempotencyKey,
            tuple[tuple[object, ...], ExecutionReceipt],
        ] = {}

    @property
    def receipts(self) -> tuple[ExecutionReceipt, ...]:
        return tuple(
            self._receipts[key]
            for key in sorted(self._receipts, key=lambda item: str(item.value))
        )

    def submit(
        self,
        submission: ExecutionSubmission,
    ) -> Result[ExecutionReceipt, ExecutionBoundaryError]:
        if not isinstance(submission, ExecutionSubmission):
            return Failure(
                ExecutionBoundaryValidationError(
                    "execution submit requires ExecutionSubmission"
                )
            )
        prior = self._idempotency.get(submission.idempotency_key)
        if prior is not None:
            logical_submission, receipt = prior
            if logical_submission != submission.logical_values():
                return Failure(
                    ExecutionBoundaryConflictError(
                        "execution idempotency key reused with different submission"
                    )
                )
            return Success(receipt)
        if submission.receipt_id in self._receipts:
            return Failure(
                ExecutionBoundaryConflictError(
                    "execution receipt id already exists"
                )
            )
        receipt = ExecutionReceipt(
            receipt_id=submission.receipt_id,
            request_id=submission.request_id,
            idempotency_key=submission.idempotency_key,
            status=ExecutionStatus.ACCEPTED,
            recorded_at=submission.submitted_at,
        )
        self._receipts[receipt.receipt_id] = receipt
        self._idempotency[receipt.idempotency_key] = (
            submission.logical_values(),
            receipt,
        )
        return Success(receipt)

    def status(
        self,
        receipt_id: ExecutionReceiptId,
    ) -> Result[ExecutionReceipt | None, ExecutionBoundaryError]:
        if not isinstance(receipt_id, ExecutionReceiptId):
            return Failure(
                ExecutionBoundaryValidationError(
                    "execution status requires ExecutionReceiptId"
                )
            )
        return Success(self._receipts.get(receipt_id))

    def cancel(
        self,
        cancellation: ExecutionCancellation,
    ) -> Result[ExecutionReceipt, ExecutionBoundaryError]:
        if not isinstance(cancellation, ExecutionCancellation):
            return Failure(
                ExecutionBoundaryValidationError(
                    "execution cancel requires ExecutionCancellation"
                )
            )
        prior = self._receipts.get(cancellation.receipt_id)
        if prior is None:
            return Failure(
                ExecutionBoundaryNotFoundError("execution receipt not found")
            )
        if cancellation.cancelled_at < prior.recorded_at:
            return Failure(
                ExecutionBoundaryConflictError(
                    "execution cancellation must not predate receipt"
                )
            )
        if prior.status is ExecutionStatus.CANCELLED:
            return Success(prior)
        cancelled = replace(
            prior,
            status=ExecutionStatus.CANCELLED,
            recorded_at=cancellation.cancelled_at,
        )
        self._receipts[cancelled.receipt_id] = cancelled
        idempotency = self._idempotency[prior.idempotency_key]
        self._idempotency[prior.idempotency_key] = (idempotency[0], cancelled)
        return Success(cancelled)
