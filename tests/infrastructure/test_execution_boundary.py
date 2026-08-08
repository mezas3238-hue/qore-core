from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryConflictError,
    ExecutionBoundaryNotFoundError,
    ExecutionBoundaryValidationError,
    ExecutionCancellation,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
    ExecutionSubmission,
    SandboxExecutionBoundary,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.pretrade_safety import (
    AuthorizedOrderIntent,
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
    PreTradeAuthorization,
    PreTradeAuthorizationId,
    PreTradeDecision,
    PreTradePolicyId,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 6, 50, tzinfo=UTC)
_IDEMPOTENCY = ExecutionIdempotencyKey(
    UUID("b0000000-0000-0000-0000-000000000001")
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("b0000000-0000-0000-0000-000000000002")),
    causation_id=CausationId(UUID("b0000000-0000-0000-0000-000000000003")),
)


def _authorized() -> AuthorizedOrderIntent:
    intent = OrderIntent(
        intent_id=OrderIntentId(UUID("b0000000-0000-0000-0000-000000000004")),
        idempotency_key=_IDEMPOTENCY,
        instrument=ExecutionInstrument("EURUSD"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_NOW,
        metadata=_METADATA,
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID("b0000000-0000-0000-0000-000000000005")
        ),
        policy_id=PreTradePolicyId("risk.pretrade.v1"),
        intent_id=intent.intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(seconds=10),
        reason="sandbox execution approved",
    )
    switch = ExecutionSafetySwitchSnapshot(
        state=ExecutionSwitchState.ENABLED,
        observed_at=_NOW + timedelta(seconds=2),
        reason="sandbox execution enabled",
    )
    return AuthorizedOrderIntent(
        intent=intent,
        authorization=authorization,
        switch=switch,
        authorized_at=_NOW + timedelta(seconds=3),
    )


def _submission(
    *,
    request_id: str = "b0000000-0000-0000-0000-000000000006",
    receipt_id: str = "b0000000-0000-0000-0000-000000000007",
    submitted_at: datetime = _NOW + timedelta(seconds=4),
) -> ExecutionSubmission:
    return ExecutionSubmission(
        request_id=ExecutionRequestId(UUID(request_id)),
        receipt_id=ExecutionReceiptId(UUID(receipt_id)),
        authorized_intent=_authorized(),
        submitted_at=submitted_at,
    )


def test_sandbox_submit_accepts_authorized_submission_and_status_reads_it() -> None:
    boundary = SandboxExecutionBoundary()
    submission = _submission()

    submitted = boundary.submit(submission)
    status = boundary.status(submission.receipt_id)

    assert isinstance(submitted, Success)
    assert submitted.value.status is ExecutionStatus.ACCEPTED
    assert isinstance(status, Success)
    assert status.value is submitted.value


def test_exact_submit_replay_returns_same_receipt() -> None:
    boundary = SandboxExecutionBoundary()
    submission = _submission()

    first = boundary.submit(submission)
    replay = boundary.submit(submission)

    assert isinstance(first, Success)
    assert isinstance(replay, Success)
    assert replay.value is first.value
    assert len(boundary.receipts) == 1


def test_idempotency_key_reuse_with_different_submission_conflicts() -> None:
    boundary = SandboxExecutionBoundary()
    first = boundary.submit(_submission())
    collision = boundary.submit(
        _submission(
            request_id="b0000000-0000-0000-0000-000000000008",
            receipt_id="b0000000-0000-0000-0000-000000000009",
        )
    )

    assert isinstance(first, Success)
    assert isinstance(collision, Failure)
    assert isinstance(collision.error, ExecutionBoundaryConflictError)


def test_submission_rejects_expired_authorization_at_submit_time() -> None:
    with pytest.raises(ExecutionBoundaryValidationError):
        _submission(submitted_at=_NOW + timedelta(seconds=11))


def test_cancel_changes_accepted_receipt_to_cancelled() -> None:
    boundary = SandboxExecutionBoundary()
    submission = _submission()
    submitted = boundary.submit(submission)
    assert isinstance(submitted, Success)

    cancelled = boundary.cancel(
        ExecutionCancellation(
            receipt_id=submission.receipt_id,
            cancelled_at=_NOW + timedelta(seconds=5),
        )
    )
    status = boundary.status(submission.receipt_id)

    assert isinstance(cancelled, Success)
    assert cancelled.value.status is ExecutionStatus.CANCELLED
    assert isinstance(status, Success)
    assert status.value == cancelled.value


def test_cancel_unknown_receipt_returns_typed_not_found() -> None:
    boundary = SandboxExecutionBoundary()
    result = boundary.cancel(
        ExecutionCancellation(
            receipt_id=ExecutionReceiptId(
                UUID("b0000000-0000-0000-0000-000000000099")
            ),
            cancelled_at=_NOW,
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutionBoundaryNotFoundError)


def test_cancel_cannot_predate_receipt() -> None:
    boundary = SandboxExecutionBoundary()
    submission = _submission()
    submitted = boundary.submit(submission)
    assert isinstance(submitted, Success)

    result = boundary.cancel(
        ExecutionCancellation(
            receipt_id=submission.receipt_id,
            cancelled_at=_NOW + timedelta(seconds=3),
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutionBoundaryConflictError)


def test_sandbox_has_no_real_broker_surface() -> None:
    boundary = SandboxExecutionBoundary()

    assert not hasattr(boundary, "connect_broker")
    assert not hasattr(boundary, "account")
    assert not hasattr(boundary, "withdraw")
