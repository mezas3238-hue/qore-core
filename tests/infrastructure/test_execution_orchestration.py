from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.infrastructure.execution_boundary import ExecutionReceiptId
from qore.infrastructure.execution_orchestration import (
    ExecutionOrchestrationId,
    GovernedExecutionOrchestrationValidationError,
    GovernedExecutionReason,
    GovernedExecutionState,
    GovernedExecutionTransitionError,
    GovernedExecutionTransitionRequest,
    declare_governed_execution,
    transition_governed_execution,
)
from qore.infrastructure.execution_reconciliation import ExecutionReconciliationStatus
from qore.infrastructure.order_intent import OrderIntentId
from qore.infrastructure.pretrade_safety import PreTradeAuthorizationId
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 9, 30, tzinfo=UTC)
_ORCHESTRATION_ID = ExecutionOrchestrationId(
    UUID("b1000000-0000-0000-0000-000000000001")
)
_INTENT_ID = OrderIntentId(UUID("b1000000-0000-0000-0000-000000000002"))
_AUTHORIZATION_ID = PreTradeAuthorizationId(
    UUID("b1000000-0000-0000-0000-000000000003")
)
_OTHER_AUTHORIZATION_ID = PreTradeAuthorizationId(
    UUID("b1000000-0000-0000-0000-000000000004")
)
_RECEIPT_ID = ExecutionReceiptId(UUID("b1000000-0000-0000-0000-000000000005"))


def _declare():
    return declare_governed_execution(
        _ORCHESTRATION_ID,
        _INTENT_ID,
        requested_at=_NOW,
    )


def test_happy_path_is_strictly_sequenced() -> None:
    declared = _declare()
    assert isinstance(declared, Success)

    authorized = transition_governed_execution(
        declared.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.AUTHORIZED,
            transitioned_at=_NOW + timedelta(seconds=1),
            reason=GovernedExecutionReason.AUTHORIZATION_APPROVED,
            authorization_id=_AUTHORIZATION_ID,
        ),
    )
    assert isinstance(authorized, Success)

    submitted = transition_governed_execution(
        authorized.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.SUBMITTED,
            transitioned_at=_NOW + timedelta(seconds=2),
            reason=GovernedExecutionReason.SUBMISSION_ACCEPTED,
            receipt_id=_RECEIPT_ID,
        ),
    )
    assert isinstance(submitted, Success)

    reconciled = transition_governed_execution(
        submitted.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.RECONCILED,
            transitioned_at=_NOW + timedelta(seconds=3),
            reason=GovernedExecutionReason.RECONCILIATION_MATCHED,
            reconciliation_status=ExecutionReconciliationStatus.MATCHED,
        ),
    )
    assert isinstance(reconciled, Success)
    assert reconciled.value.terminal is True
    assert reconciled.value.sequence == 3
    assert reconciled.value.authorization_id == _AUTHORIZATION_ID
    assert reconciled.value.receipt_id == _RECEIPT_ID


def test_requested_cannot_skip_directly_to_submitted() -> None:
    declared = _declare()
    assert isinstance(declared, Success)

    result = transition_governed_execution(
        declared.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.SUBMITTED,
            transitioned_at=_NOW + timedelta(seconds=1),
            reason=GovernedExecutionReason.SUBMISSION_ACCEPTED,
            authorization_id=_AUTHORIZATION_ID,
            receipt_id=_RECEIPT_ID,
        ),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, GovernedExecutionTransitionError)


def test_safety_block_is_terminal_and_has_no_receipt() -> None:
    declared = _declare()
    assert isinstance(declared, Success)

    blocked = transition_governed_execution(
        declared.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.BLOCKED,
            transitioned_at=_NOW + timedelta(seconds=1),
            reason=GovernedExecutionReason.SAFETY_BLOCKED,
        ),
    )
    assert isinstance(blocked, Success)
    assert blocked.value.terminal is True
    assert blocked.value.receipt_id is None

    retry = transition_governed_execution(
        blocked.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.AUTHORIZED,
            transitioned_at=_NOW + timedelta(seconds=2),
            reason=GovernedExecutionReason.AUTHORIZATION_APPROVED,
            authorization_id=_AUTHORIZATION_ID,
        ),
    )
    assert isinstance(retry, Failure)


def test_authorization_identity_cannot_change_after_authorized() -> None:
    declared = _declare()
    assert isinstance(declared, Success)
    authorized = transition_governed_execution(
        declared.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.AUTHORIZED,
            transitioned_at=_NOW + timedelta(seconds=1),
            reason=GovernedExecutionReason.AUTHORIZATION_APPROVED,
            authorization_id=_AUTHORIZATION_ID,
        ),
    )
    assert isinstance(authorized, Success)

    result = transition_governed_execution(
        authorized.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.SUBMITTED,
            transitioned_at=_NOW + timedelta(seconds=2),
            reason=GovernedExecutionReason.SUBMISSION_ACCEPTED,
            authorization_id=_OTHER_AUTHORIZATION_ID,
            receipt_id=_RECEIPT_ID,
        ),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, GovernedExecutionTransitionError)


def test_divergence_is_contained_not_reconciled() -> None:
    declared = _declare()
    assert isinstance(declared, Success)
    authorized = transition_governed_execution(
        declared.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.AUTHORIZED,
            transitioned_at=_NOW + timedelta(seconds=1),
            reason=GovernedExecutionReason.AUTHORIZATION_APPROVED,
            authorization_id=_AUTHORIZATION_ID,
        ),
    )
    assert isinstance(authorized, Success)
    submitted = transition_governed_execution(
        authorized.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.SUBMITTED,
            transitioned_at=_NOW + timedelta(seconds=2),
            reason=GovernedExecutionReason.SUBMISSION_ACCEPTED,
            receipt_id=_RECEIPT_ID,
        ),
    )
    assert isinstance(submitted, Success)

    contained = transition_governed_execution(
        submitted.value,
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.CONTAINED,
            transitioned_at=_NOW + timedelta(seconds=3),
            reason=GovernedExecutionReason.FAILURE_CONTAINED,
            reconciliation_status=ExecutionReconciliationStatus.DIVERGED,
        ),
    )

    assert isinstance(contained, Success)
    assert contained.value.state is GovernedExecutionState.CONTAINED
    assert contained.value.terminal is True
    assert contained.value.reconciliation_status is ExecutionReconciliationStatus.DIVERGED


def test_reconciled_state_rejects_non_matched_evidence() -> None:
    with pytest.raises(GovernedExecutionOrchestrationValidationError):
        from qore.infrastructure.execution_orchestration import GovernedExecutionSnapshot

        GovernedExecutionSnapshot(
            orchestration_id=_ORCHESTRATION_ID,
            intent_id=_INTENT_ID,
            state=GovernedExecutionState.RECONCILED,
            sequence=3,
            observed_at=_NOW,
            reason=GovernedExecutionReason.RECONCILIATION_MATCHED,
            authorization_id=_AUTHORIZATION_ID,
            receipt_id=_RECEIPT_ID,
            reconciliation_status=ExecutionReconciliationStatus.DIVERGED,
        )


def test_naive_transition_timestamp_is_rejected() -> None:
    with pytest.raises(GovernedExecutionOrchestrationValidationError):
        GovernedExecutionTransitionRequest(
            state=GovernedExecutionState.BLOCKED,
            transitioned_at=datetime(2026, 8, 8, 9, 31),
            reason=GovernedExecutionReason.SAFETY_BLOCKED,
        )
