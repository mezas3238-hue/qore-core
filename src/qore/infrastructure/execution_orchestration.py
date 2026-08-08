from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.execution_boundary import ExecutionReceiptId
from qore.infrastructure.execution_reconciliation import ExecutionReconciliationStatus
from qore.infrastructure.order_intent import OrderIntentId
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.pretrade_safety import PreTradeAuthorizationId
from qore.kernel.result import Failure, Result, Success


class GovernedExecutionOrchestrationError(ExternalPortError):
    """Base error for deterministic execution orchestration state."""

    __slots__ = ()


class GovernedExecutionOrchestrationValidationError(
    GovernedExecutionOrchestrationError
):
    """Violation of orchestration state invariants."""

    __slots__ = ()


class GovernedExecutionTransitionError(GovernedExecutionOrchestrationError):
    """Invalid fail-closed orchestration transition."""

    __slots__ = ()


class GovernedExecutionState(StrEnum):
    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    SUBMITTED = "submitted"
    RECONCILED = "reconciled"
    BLOCKED = "blocked"
    CONTAINED = "contained"


class GovernedExecutionReason(StrEnum):
    REQUEST_DECLARED = "request_declared"
    AUTHORIZATION_APPROVED = "authorization_approved"
    SUBMISSION_ACCEPTED = "submission_accepted"
    RECONCILIATION_MATCHED = "reconciliation_matched"
    SAFETY_BLOCKED = "safety_blocked"
    FAILURE_CONTAINED = "failure_contained"


@dataclass(frozen=True, slots=True)
class ExecutionOrchestrationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise GovernedExecutionOrchestrationValidationError(
                "execution orchestration id must be UUID"
            )

    def logical_values(self) -> tuple[UUID, ...]:
        return (self.value,)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise GovernedExecutionOrchestrationValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise GovernedExecutionOrchestrationValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class GovernedExecutionSnapshot:
    orchestration_id: ExecutionOrchestrationId
    intent_id: OrderIntentId
    state: GovernedExecutionState
    sequence: int
    observed_at: datetime
    reason: GovernedExecutionReason
    authorization_id: PreTradeAuthorizationId | None = None
    receipt_id: ExecutionReceiptId | None = None
    reconciliation_status: ExecutionReconciliationStatus | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.orchestration_id, ExecutionOrchestrationId):
            raise GovernedExecutionOrchestrationValidationError(
                "orchestration_id must be ExecutionOrchestrationId"
            )
        if not isinstance(self.intent_id, OrderIntentId):
            raise GovernedExecutionOrchestrationValidationError(
                "intent_id must be OrderIntentId"
            )
        if not isinstance(self.state, GovernedExecutionState):
            raise GovernedExecutionOrchestrationValidationError(
                "state must be GovernedExecutionState"
            )
        if (
            not isinstance(self.sequence, int)
            or isinstance(self.sequence, bool)
            or self.sequence < 0
        ):
            raise GovernedExecutionOrchestrationValidationError(
                "sequence must be a non-negative int"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")
        if not isinstance(self.reason, GovernedExecutionReason):
            raise GovernedExecutionOrchestrationValidationError(
                "reason must be GovernedExecutionReason"
            )
        if self.authorization_id is not None and not isinstance(
            self.authorization_id, PreTradeAuthorizationId
        ):
            raise GovernedExecutionOrchestrationValidationError(
                "authorization_id must be PreTradeAuthorizationId or None"
            )
        if self.receipt_id is not None and not isinstance(
            self.receipt_id, ExecutionReceiptId
        ):
            raise GovernedExecutionOrchestrationValidationError(
                "receipt_id must be ExecutionReceiptId or None"
            )
        if self.reconciliation_status is not None and not isinstance(
            self.reconciliation_status, ExecutionReconciliationStatus
        ):
            raise GovernedExecutionOrchestrationValidationError(
                "reconciliation_status must be ExecutionReconciliationStatus or None"
            )
        self._validate_state_evidence()

    def _validate_state_evidence(self) -> None:
        if self.state is GovernedExecutionState.REQUESTED:
            if (
                self.authorization_id is not None
                or self.receipt_id is not None
                or self.reconciliation_status is not None
            ):
                raise GovernedExecutionOrchestrationValidationError(
                    "requested execution must not contain downstream evidence"
                )
        elif self.state is GovernedExecutionState.AUTHORIZED:
            if self.authorization_id is None:
                raise GovernedExecutionOrchestrationValidationError(
                    "authorized execution requires authorization_id"
                )
            if self.receipt_id is not None or self.reconciliation_status is not None:
                raise GovernedExecutionOrchestrationValidationError(
                    "authorized execution must not contain submit/reconciliation evidence"
                )
        elif self.state is GovernedExecutionState.SUBMITTED:
            if self.authorization_id is None or self.receipt_id is None:
                raise GovernedExecutionOrchestrationValidationError(
                    "submitted execution requires authorization_id and receipt_id"
                )
            if self.reconciliation_status is not None:
                raise GovernedExecutionOrchestrationValidationError(
                    "submitted execution must not contain reconciliation evidence"
                )
        elif self.state is GovernedExecutionState.RECONCILED:
            if self.authorization_id is None or self.receipt_id is None:
                raise GovernedExecutionOrchestrationValidationError(
                    "reconciled execution requires authorization_id and receipt_id"
                )
            if self.reconciliation_status is not ExecutionReconciliationStatus.MATCHED:
                raise GovernedExecutionOrchestrationValidationError(
                    "reconciled execution requires MATCHED reconciliation"
                )
        elif self.state is GovernedExecutionState.BLOCKED:
            if self.receipt_id is not None or self.reconciliation_status is not None:
                raise GovernedExecutionOrchestrationValidationError(
                    "blocked execution must not contain receipt/reconciliation evidence"
                )
        elif self.state is GovernedExecutionState.CONTAINED:
            if self.reconciliation_status is ExecutionReconciliationStatus.MATCHED:
                raise GovernedExecutionOrchestrationValidationError(
                    "contained execution must not carry MATCHED reconciliation"
                )

    @property
    def terminal(self) -> bool:
        return self.state in {
            GovernedExecutionState.RECONCILED,
            GovernedExecutionState.BLOCKED,
            GovernedExecutionState.CONTAINED,
        }

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.orchestration_id.logical_values(),
            self.intent_id.logical_values(),
            self.state.value,
            self.sequence,
            self.observed_at.isoformat(),
            self.reason.value,
            (
                self.authorization_id.logical_values()
                if self.authorization_id is not None
                else None
            ),
            self.receipt_id.logical_values() if self.receipt_id is not None else None,
            (
                self.reconciliation_status.value
                if self.reconciliation_status is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class GovernedExecutionTransitionRequest:
    state: GovernedExecutionState
    transitioned_at: datetime
    reason: GovernedExecutionReason
    authorization_id: PreTradeAuthorizationId | None = None
    receipt_id: ExecutionReceiptId | None = None
    reconciliation_status: ExecutionReconciliationStatus | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, GovernedExecutionState):
            raise GovernedExecutionOrchestrationValidationError(
                "transition state must be GovernedExecutionState"
            )
        _validate_timestamp(self.transitioned_at, field_name="transitioned_at")
        if not isinstance(self.reason, GovernedExecutionReason):
            raise GovernedExecutionOrchestrationValidationError(
                "transition reason must be GovernedExecutionReason"
            )
        if self.authorization_id is not None and not isinstance(
            self.authorization_id, PreTradeAuthorizationId
        ):
            raise GovernedExecutionOrchestrationValidationError(
                "transition authorization_id must be PreTradeAuthorizationId or None"
            )
        if self.receipt_id is not None and not isinstance(
            self.receipt_id, ExecutionReceiptId
        ):
            raise GovernedExecutionOrchestrationValidationError(
                "transition receipt_id must be ExecutionReceiptId or None"
            )
        if self.reconciliation_status is not None and not isinstance(
            self.reconciliation_status, ExecutionReconciliationStatus
        ):
            raise GovernedExecutionOrchestrationValidationError(
                "transition reconciliation_status must be valid or None"
            )


_ALLOWED_TRANSITIONS: dict[GovernedExecutionState, frozenset[GovernedExecutionState]] = {
    GovernedExecutionState.REQUESTED: frozenset(
        {GovernedExecutionState.AUTHORIZED, GovernedExecutionState.BLOCKED}
    ),
    GovernedExecutionState.AUTHORIZED: frozenset(
        {
            GovernedExecutionState.SUBMITTED,
            GovernedExecutionState.BLOCKED,
            GovernedExecutionState.CONTAINED,
        }
    ),
    GovernedExecutionState.SUBMITTED: frozenset(
        {GovernedExecutionState.RECONCILED, GovernedExecutionState.CONTAINED}
    ),
    GovernedExecutionState.RECONCILED: frozenset(),
    GovernedExecutionState.BLOCKED: frozenset(),
    GovernedExecutionState.CONTAINED: frozenset(),
}

_EXPECTED_REASON: dict[GovernedExecutionState, GovernedExecutionReason] = {
    GovernedExecutionState.AUTHORIZED: GovernedExecutionReason.AUTHORIZATION_APPROVED,
    GovernedExecutionState.SUBMITTED: GovernedExecutionReason.SUBMISSION_ACCEPTED,
    GovernedExecutionState.RECONCILED: GovernedExecutionReason.RECONCILIATION_MATCHED,
    GovernedExecutionState.BLOCKED: GovernedExecutionReason.SAFETY_BLOCKED,
    GovernedExecutionState.CONTAINED: GovernedExecutionReason.FAILURE_CONTAINED,
}


def declare_governed_execution(
    orchestration_id: ExecutionOrchestrationId,
    intent_id: OrderIntentId,
    *,
    requested_at: datetime,
) -> Result[GovernedExecutionSnapshot, GovernedExecutionOrchestrationError]:
    try:
        return Success(
            GovernedExecutionSnapshot(
                orchestration_id=orchestration_id,
                intent_id=intent_id,
                state=GovernedExecutionState.REQUESTED,
                sequence=0,
                observed_at=requested_at,
                reason=GovernedExecutionReason.REQUEST_DECLARED,
            )
        )
    except GovernedExecutionOrchestrationError as error:
        return Failure(error)


def transition_governed_execution(
    snapshot: GovernedExecutionSnapshot,
    request: GovernedExecutionTransitionRequest,
) -> Result[GovernedExecutionSnapshot, GovernedExecutionOrchestrationError]:
    if not isinstance(snapshot, GovernedExecutionSnapshot):
        return Failure(
            GovernedExecutionOrchestrationValidationError(
                "snapshot must be GovernedExecutionSnapshot"
            )
        )
    if not isinstance(request, GovernedExecutionTransitionRequest):
        return Failure(
            GovernedExecutionOrchestrationValidationError(
                "request must be GovernedExecutionTransitionRequest"
            )
        )
    if request.transitioned_at <= snapshot.observed_at:
        return Failure(
            GovernedExecutionTransitionError(
                "transition timestamp must be after current snapshot"
            )
        )
    if request.state not in _ALLOWED_TRANSITIONS[snapshot.state]:
        return Failure(
            GovernedExecutionTransitionError(
                f"invalid execution transition: {snapshot.state.value} -> {request.state.value}"
            )
        )
    expected_reason = _EXPECTED_REASON[request.state]
    if request.reason is not expected_reason:
        return Failure(
            GovernedExecutionTransitionError(
                "transition reason does not match target execution state"
            )
        )

    authorization_id = request.authorization_id
    receipt_id = request.receipt_id
    reconciliation_status = request.reconciliation_status

    if request.state in {
        GovernedExecutionState.SUBMITTED,
        GovernedExecutionState.RECONCILED,
        GovernedExecutionState.CONTAINED,
    }:
        if authorization_id is None:
            authorization_id = snapshot.authorization_id
    if request.state in {
        GovernedExecutionState.RECONCILED,
        GovernedExecutionState.CONTAINED,
    }:
        if receipt_id is None:
            receipt_id = snapshot.receipt_id

    if (
        snapshot.authorization_id is not None
        and authorization_id is not None
        and authorization_id != snapshot.authorization_id
    ):
        return Failure(
            GovernedExecutionTransitionError(
                "transition must preserve authorization identity"
            )
        )
    if (
        snapshot.receipt_id is not None
        and receipt_id is not None
        and receipt_id != snapshot.receipt_id
    ):
        return Failure(
            GovernedExecutionTransitionError(
                "transition must preserve receipt identity"
            )
        )

    try:
        next_snapshot = GovernedExecutionSnapshot(
            orchestration_id=snapshot.orchestration_id,
            intent_id=snapshot.intent_id,
            state=request.state,
            sequence=snapshot.sequence + 1,
            observed_at=request.transitioned_at,
            reason=request.reason,
            authorization_id=authorization_id,
            receipt_id=receipt_id,
            reconciliation_status=reconciliation_status,
        )
    except GovernedExecutionOrchestrationError as error:
        return Failure(error)
    return Success(next_snapshot)
