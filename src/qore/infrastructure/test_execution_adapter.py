from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from re import fullmatch
from typing import Protocol

from qore.infrastructure.execution_boundary import (
    ExecutionBoundary,
    ExecutionBoundaryConflictError,
    ExecutionBoundaryError,
    ExecutionBoundaryNotFoundError,
    ExecutionBoundaryValidationError,
    ExecutionCancellation,
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionStatus,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
    MarketTestEnvironmentAuthorization,
)
from qore.infrastructure.order_intent import ExecutionIdempotencyKey
from qore.kernel.result import Failure, Result, Success


class TestExecutionAdapterError(ExecutionBoundaryError):
    """Base error for the authorized TEST/DEMO execution adapter."""

    __slots__ = ()


class TestExecutionAdapterValidationError(TestExecutionAdapterError):
    """Violation of a TEST/DEMO adapter invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class TestExecutionGatewayReceipt:
    """Sanitized provider receipt for a non-production execution gateway."""

    provider_execution_ref: str
    status: ExecutionStatus
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.provider_execution_ref, str) or fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*", self.provider_execution_ref
        ) is None:
            raise TestExecutionAdapterValidationError(
                "provider_execution_ref must be a stable non-secret identifier"
            )
        if not isinstance(self.status, ExecutionStatus):
            raise TestExecutionAdapterValidationError(
                "gateway receipt status must be ExecutionStatus"
            )
        if not isinstance(self.recorded_at, datetime):
            raise TestExecutionAdapterValidationError(
                "gateway receipt recorded_at must be a datetime"
            )
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise TestExecutionAdapterValidationError(
                "gateway receipt recorded_at must be timezone-aware"
            )

    def logical_values(self) -> tuple[str, str, str]:
        return (
            self.provider_execution_ref,
            self.status.value,
            self.recorded_at.isoformat(),
        )


class TestExecutionGatewayBoundary(Protocol):
    """Provider-specific gateway surface allowed only behind TEST/DEMO authorization."""

    def submit(
        self,
        *,
        account: MarketTestAccountIdentity,
        submission: ExecutionSubmission,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]: ...

    def cancel(
        self,
        *,
        account: MarketTestAccountIdentity,
        provider_execution_ref: str,
        cancelled_at: datetime,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]: ...


class AuthorizedTestExecutionAdapter(ExecutionBoundary):
    """Idempotent execution adapter that can target only authorized TEST/DEMO accounts."""

    __slots__ = (
        "_authorization",
        "_gateway",
        "_idempotency",
        "_provider_refs",
        "_receipts",
    )

    def __init__(
        self,
        *,
        environment_authorization: MarketTestEnvironmentAuthorization,
        gateway: TestExecutionGatewayBoundary,
    ) -> None:
        if not isinstance(environment_authorization, MarketTestEnvironmentAuthorization):
            raise TestExecutionAdapterValidationError(
                "test execution adapter requires environment authorization"
            )
        if environment_authorization.account.environment not in {
            MarketRuntimeEnvironment.DEMO,
            MarketRuntimeEnvironment.TEST,
        }:
            raise TestExecutionAdapterValidationError(
                "test execution adapter requires TEST or DEMO account"
            )
        self._authorization = environment_authorization
        self._gateway = gateway
        self._receipts: dict[ExecutionReceiptId, ExecutionReceipt] = {}
        self._provider_refs: dict[ExecutionReceiptId, str] = {}
        self._idempotency: dict[
            ExecutionIdempotencyKey,
            tuple[tuple[object, ...], ExecutionReceipt],
        ] = {}

    @property
    def environment_authorization(self) -> MarketTestEnvironmentAuthorization:
        return self._authorization

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
                    "test execution submit requires ExecutionSubmission"
                )
            )
        if self._authorization.authorized_at > submission.submitted_at:
            return Failure(
                TestExecutionAdapterValidationError(
                    "environment authorization must not postdate submission"
                )
            )
        prior = self._idempotency.get(submission.idempotency_key)
        if prior is not None:
            logical_submission, receipt = prior
            if logical_submission != submission.logical_values():
                return Failure(
                    ExecutionBoundaryConflictError(
                        "test execution idempotency key reused with different submission"
                    )
                )
            return Success(receipt)
        if submission.receipt_id in self._receipts:
            return Failure(
                ExecutionBoundaryConflictError(
                    "test execution receipt id already exists"
                )
            )

        gateway_result = self._gateway.submit(
            account=self._authorization.account,
            submission=submission,
        )
        if isinstance(gateway_result, Failure):
            return Failure(gateway_result.error)
        gateway_receipt = gateway_result.value
        if not isinstance(gateway_receipt, TestExecutionGatewayReceipt):
            return Failure(
                TestExecutionAdapterValidationError(
                    "test execution gateway must return TestExecutionGatewayReceipt"
                )
            )
        if gateway_receipt.status is not ExecutionStatus.ACCEPTED:
            return Failure(
                TestExecutionAdapterValidationError(
                    "new test execution gateway receipt must be ACCEPTED"
                )
            )
        if gateway_receipt.recorded_at < submission.submitted_at:
            return Failure(
                TestExecutionAdapterValidationError(
                    "gateway receipt must not predate submission"
                )
            )
        if gateway_receipt.provider_execution_ref in self._provider_refs.values():
            return Failure(
                ExecutionBoundaryConflictError(
                    "provider execution reference already exists"
                )
            )

        receipt = ExecutionReceipt(
            receipt_id=submission.receipt_id,
            request_id=submission.request_id,
            idempotency_key=submission.idempotency_key,
            status=ExecutionStatus.ACCEPTED,
            recorded_at=gateway_receipt.recorded_at,
        )
        self._receipts[receipt.receipt_id] = receipt
        self._provider_refs[receipt.receipt_id] = gateway_receipt.provider_execution_ref
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
                    "test execution status requires ExecutionReceiptId"
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
                    "test execution cancel requires ExecutionCancellation"
                )
            )
        prior = self._receipts.get(cancellation.receipt_id)
        if prior is None:
            return Failure(
                ExecutionBoundaryNotFoundError("test execution receipt not found")
            )
        if cancellation.cancelled_at < prior.recorded_at:
            return Failure(
                ExecutionBoundaryConflictError(
                    "test execution cancellation must not predate receipt"
                )
            )
        if prior.status is ExecutionStatus.CANCELLED:
            return Success(prior)

        provider_execution_ref = self._provider_refs[prior.receipt_id]
        gateway_result = self._gateway.cancel(
            account=self._authorization.account,
            provider_execution_ref=provider_execution_ref,
            cancelled_at=cancellation.cancelled_at,
        )
        if isinstance(gateway_result, Failure):
            return Failure(gateway_result.error)
        gateway_receipt = gateway_result.value
        if not isinstance(gateway_receipt, TestExecutionGatewayReceipt):
            return Failure(
                TestExecutionAdapterValidationError(
                    "test execution gateway must return TestExecutionGatewayReceipt"
                )
            )
        if gateway_receipt.provider_execution_ref != provider_execution_ref:
            return Failure(
                ExecutionBoundaryConflictError(
                    "gateway cancellation reference must match submitted execution"
                )
            )
        if gateway_receipt.status is not ExecutionStatus.CANCELLED:
            return Failure(
                TestExecutionAdapterValidationError(
                    "gateway cancellation must return CANCELLED"
                )
            )
        if gateway_receipt.recorded_at < cancellation.cancelled_at:
            return Failure(
                TestExecutionAdapterValidationError(
                    "gateway cancellation receipt must not predate cancellation"
                )
            )

        cancelled = replace(
            prior,
            status=ExecutionStatus.CANCELLED,
            recorded_at=gateway_receipt.recorded_at,
        )
        self._receipts[cancelled.receipt_id] = cancelled
        logical_submission, _ = self._idempotency[cancelled.idempotency_key]
        self._idempotency[cancelled.idempotency_key] = (
            logical_submission,
            cancelled,
        )
        return Success(cancelled)
