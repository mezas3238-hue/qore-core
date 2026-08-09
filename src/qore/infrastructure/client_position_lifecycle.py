from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.functional.decisions import DecisionId
from qore.infrastructure.account_policy import AccountPolicySnapshotId
from qore.infrastructure.client_accounts import AccountPolicyReference, TradingAccountId
from qore.infrastructure.client_execution_agent import (
    ClientExecutionPlan,
    ClientExecutionPolicyId,
    ProtectionPolicyReference,
    TrailingPolicyReference,
)
from qore.infrastructure.execution_boundary import (
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionStatus,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionReconciliationSnapshot,
    ExecutionReconciliationStatus,
)
from qore.infrastructure.order_intent import OrderPrice, OrderSide
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ClientPositionLifecycleError(InfrastructureError):
    """Base error for client position lifecycle contracts."""

    __slots__ = ()


class ClientPositionLifecycleValidationError(ClientPositionLifecycleError):
    """Violation of a client position lifecycle invariant."""

    __slots__ = ()


class ClientPositionLifecycleConflictError(ClientPositionLifecycleError):
    """A lifecycle transition conflicts with current position state."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ClientPositionLifecycleValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ClientPositionLifecycleValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ClientPositionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ClientPositionLifecycleValidationError(
                "client position id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ClientPositionActionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ClientPositionLifecycleValidationError(
                "client position action id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ClientPositionEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ClientPositionLifecycleValidationError(
                "client position evidence reference must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ClientPositionRationaleCode:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]{2,79}", self.value
        ) is None:
            raise ClientPositionLifecycleValidationError(
                "position rationale code must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ClientPositionState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class ClientPositionActionKind(StrEnum):
    OPEN = "open"
    TRAILING_STOP = "trailing_stop"
    EXIT = "exit"


class ClientPositionExitReason(StrEnum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    CORE_POLICY = "core_policy"
    AUTHORIZED_MANUAL = "authorized_manual"


@dataclass(frozen=True, slots=True)
class ClientExecutionConfirmation:
    """Matched execution evidence used to establish a position lifecycle."""

    plan: ClientExecutionPlan
    receipt: ExecutionReceipt
    reconciliation: ExecutionReconciliationSnapshot
    fill_price: OrderPrice
    confirmed_at: datetime
    evidence_ref: ClientPositionEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.plan, ClientExecutionPlan):
            raise ClientPositionLifecycleValidationError(
                "execution confirmation plan must be ClientExecutionPlan"
            )
        _validate_matched_execution(
            self.receipt,
            self.reconciliation,
            event_at=self.confirmed_at,
        )
        if not isinstance(self.fill_price, OrderPrice):
            raise ClientPositionLifecycleValidationError(
                "execution confirmation fill_price must be OrderPrice"
            )
        if not isinstance(self.evidence_ref, ClientPositionEvidenceReference):
            raise ClientPositionLifecycleValidationError(
                "execution confirmation evidence_ref must be ClientPositionEvidenceReference"
            )
        if self.confirmed_at < self.plan.created_at:
            raise ClientPositionLifecycleValidationError(
                "execution confirmation must not predate execution plan"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.plan.logical_values(),
            self.receipt.logical_values(),
            self.reconciliation.logical_values(),
            self.fill_price.logical_values(),
            self.confirmed_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ClientPositionAction:
    """One auditable position action with complete causal provenance."""

    action_id: ClientPositionActionId
    kind: ClientPositionActionKind
    position_id: ClientPositionId
    account_id: TradingAccountId
    decision_id: DecisionId
    occurred_at: datetime
    evidence_ref: ClientPositionEvidenceReference
    rationale_code: ClientPositionRationaleCode
    account_policy_ref: AccountPolicyReference
    account_policy_snapshot_id: AccountPolicySnapshotId
    execution_policy_id: ClientExecutionPolicyId
    protection_policy_ref: ProtectionPolicyReference
    trailing_policy_ref: TrailingPolicyReference | None
    execution_receipt_id: ExecutionReceiptId | None = None
    previous_stop: OrderPrice | None = None
    new_stop: OrderPrice | None = None
    exit_price: OrderPrice | None = None
    exit_reason: ClientPositionExitReason | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ClientPositionActionId):
            raise ClientPositionLifecycleValidationError(
                "position action_id must be ClientPositionActionId"
            )
        if not isinstance(self.kind, ClientPositionActionKind):
            raise ClientPositionLifecycleValidationError(
                "position action kind must be ClientPositionActionKind"
            )
        if not isinstance(self.position_id, ClientPositionId):
            raise ClientPositionLifecycleValidationError(
                "position action position_id must be ClientPositionId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientPositionLifecycleValidationError(
                "position action account_id must be TradingAccountId"
            )
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise ClientPositionLifecycleValidationError(
                "position action decision_id must be UUID-backed DecisionId"
            )
        _validate_timestamp(self.occurred_at, field_name="position action occurred_at")
        if not isinstance(self.evidence_ref, ClientPositionEvidenceReference):
            raise ClientPositionLifecycleValidationError(
                "position action evidence_ref must be ClientPositionEvidenceReference"
            )
        if not isinstance(self.rationale_code, ClientPositionRationaleCode):
            raise ClientPositionLifecycleValidationError(
                "position action rationale_code must be ClientPositionRationaleCode"
            )
        if not isinstance(self.account_policy_ref, AccountPolicyReference):
            raise ClientPositionLifecycleValidationError(
                "position action account_policy_ref must be AccountPolicyReference"
            )
        if not isinstance(self.account_policy_snapshot_id, AccountPolicySnapshotId):
            raise ClientPositionLifecycleValidationError(
                "position action account_policy_snapshot_id must be AccountPolicySnapshotId"
            )
        if not isinstance(self.execution_policy_id, ClientExecutionPolicyId):
            raise ClientPositionLifecycleValidationError(
                "position action execution_policy_id must be ClientExecutionPolicyId"
            )
        if not isinstance(self.protection_policy_ref, ProtectionPolicyReference):
            raise ClientPositionLifecycleValidationError(
                "position action protection_policy_ref must be ProtectionPolicyReference"
            )
        if self.trailing_policy_ref is not None and not isinstance(
            self.trailing_policy_ref, TrailingPolicyReference
        ):
            raise ClientPositionLifecycleValidationError(
                "position action trailing_policy_ref must be TrailingPolicyReference or None"
            )
        self._validate_kind_fields()

    def _validate_kind_fields(self) -> None:
        if self.kind is ClientPositionActionKind.OPEN:
            if not isinstance(self.execution_receipt_id, ExecutionReceiptId):
                raise ClientPositionLifecycleValidationError(
                    "OPEN action requires execution_receipt_id"
                )
            if self.previous_stop is not None or not isinstance(self.new_stop, OrderPrice):
                raise ClientPositionLifecycleValidationError(
                    "OPEN action requires initial new_stop and no previous_stop"
                )
            if self.exit_price is not None or self.exit_reason is not None:
                raise ClientPositionLifecycleValidationError(
                    "OPEN action must not carry exit fields"
                )
            return
        if self.kind is ClientPositionActionKind.TRAILING_STOP:
            if self.execution_receipt_id is not None:
                raise ClientPositionLifecycleValidationError(
                    "TRAILING_STOP action must not carry execution_receipt_id"
                )
            if not isinstance(self.trailing_policy_ref, TrailingPolicyReference):
                raise ClientPositionLifecycleValidationError(
                    "TRAILING_STOP action requires trailing_policy_ref"
                )
            if not isinstance(self.previous_stop, OrderPrice) or not isinstance(
                self.new_stop, OrderPrice
            ):
                raise ClientPositionLifecycleValidationError(
                    "TRAILING_STOP action requires previous_stop and new_stop"
                )
            if self.exit_price is not None or self.exit_reason is not None:
                raise ClientPositionLifecycleValidationError(
                    "TRAILING_STOP action must not carry exit fields"
                )
            return
        if not isinstance(self.execution_receipt_id, ExecutionReceiptId):
            raise ClientPositionLifecycleValidationError(
                "EXIT action requires execution_receipt_id"
            )
        if self.previous_stop is not None or self.new_stop is not None:
            raise ClientPositionLifecycleValidationError(
                "EXIT action must not carry stop mutation fields"
            )
        if not isinstance(self.exit_price, OrderPrice) or not isinstance(
            self.exit_reason, ClientPositionExitReason
        ):
            raise ClientPositionLifecycleValidationError(
                "EXIT action requires exit_price and exit_reason"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.action_id.logical_values(),
            self.kind.value,
            self.position_id.logical_values(),
            self.account_id.logical_values(),
            str(self.decision_id.value),
            self.occurred_at.isoformat(),
            self.evidence_ref.logical_values(),
            self.rationale_code.logical_values(),
            self.account_policy_ref.logical_values(),
            self.account_policy_snapshot_id.logical_values(),
            self.execution_policy_id.logical_values(),
            self.protection_policy_ref.logical_values(),
            (
                self.trailing_policy_ref.logical_values()
                if self.trailing_policy_ref is not None
                else None
            ),
            (
                self.execution_receipt_id.logical_values()
                if self.execution_receipt_id is not None
                else None
            ),
            self.previous_stop.logical_values() if self.previous_stop else None,
            self.new_stop.logical_values() if self.new_stop else None,
            self.exit_price.logical_values() if self.exit_price else None,
            self.exit_reason.value if self.exit_reason is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ClientPositionLifecycle:
    """Immutable append-only causal history for one client position."""

    plan: ClientExecutionPlan
    position_id: ClientPositionId
    state: ClientPositionState
    entry_price: OrderPrice
    current_stop: OrderPrice
    take_profit: OrderPrice
    opened_at: datetime
    closed_at: datetime | None
    actions: tuple[ClientPositionAction, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.plan, ClientExecutionPlan):
            raise ClientPositionLifecycleValidationError(
                "position lifecycle plan must be ClientExecutionPlan"
            )
        if not isinstance(self.position_id, ClientPositionId):
            raise ClientPositionLifecycleValidationError(
                "position lifecycle position_id must be ClientPositionId"
            )
        if not isinstance(self.state, ClientPositionState):
            raise ClientPositionLifecycleValidationError(
                "position lifecycle state must be ClientPositionState"
            )
        for field_name, value in (
            ("entry_price", self.entry_price),
            ("current_stop", self.current_stop),
            ("take_profit", self.take_profit),
        ):
            if not isinstance(value, OrderPrice):
                raise ClientPositionLifecycleValidationError(
                    f"position lifecycle {field_name} must be OrderPrice"
                )
        _validate_timestamp(self.opened_at, field_name="position opened_at")
        if self.closed_at is not None:
            _validate_timestamp(self.closed_at, field_name="position closed_at")
            if self.closed_at < self.opened_at:
                raise ClientPositionLifecycleValidationError(
                    "position closed_at must not predate opened_at"
                )
        if not isinstance(self.actions, tuple) or not self.actions:
            raise ClientPositionLifecycleValidationError(
                "position lifecycle requires non-empty action tuple"
            )
        self._validate_actions()

    def _validate_actions(self) -> None:
        if self.actions[0].kind is not ClientPositionActionKind.OPEN:
            raise ClientPositionLifecycleValidationError(
                "position lifecycle first action must be OPEN"
            )
        if self.actions[0].occurred_at != self.opened_at:
            raise ClientPositionLifecycleValidationError(
                "position lifecycle opened_at must match OPEN action"
            )
        action_ids: set[ClientPositionActionId] = set()
        expected_stop = self.plan.stop_loss
        previous_at: datetime | None = None
        exit_seen = False
        for action in self.actions:
            if action.action_id in action_ids:
                raise ClientPositionLifecycleValidationError(
                    "position lifecycle action ids must be unique"
                )
            action_ids.add(action.action_id)
            self._validate_action_provenance(action)
            if previous_at is not None and action.occurred_at < previous_at:
                raise ClientPositionLifecycleValidationError(
                    "position lifecycle actions must be chronological"
                )
            previous_at = action.occurred_at
            if exit_seen:
                raise ClientPositionLifecycleValidationError(
                    "position lifecycle cannot contain actions after EXIT"
                )
            if action.kind is ClientPositionActionKind.OPEN:
                if action is not self.actions[0] or action.new_stop != expected_stop:
                    raise ClientPositionLifecycleValidationError(
                        "position lifecycle OPEN action must bind initial stop"
                    )
            elif action.kind is ClientPositionActionKind.TRAILING_STOP:
                if action.previous_stop != expected_stop:
                    raise ClientPositionLifecycleValidationError(
                        "trailing action previous_stop breaks stop continuity"
                    )
                if action.new_stop is None:
                    raise ClientPositionLifecycleValidationError(
                        "trailing action requires new_stop"
                    )
                self._validate_trailing_move(expected_stop, action.new_stop)
                expected_stop = action.new_stop
            else:
                exit_seen = True
        if expected_stop != self.current_stop:
            raise ClientPositionLifecycleValidationError(
                "position lifecycle current_stop must match action history"
            )
        if self.state is ClientPositionState.OPEN:
            if exit_seen or self.closed_at is not None:
                raise ClientPositionLifecycleValidationError(
                    "OPEN position cannot contain EXIT or closed_at"
                )
        else:
            if not exit_seen or self.closed_at != self.actions[-1].occurred_at:
                raise ClientPositionLifecycleValidationError(
                    "CLOSED position requires terminal EXIT matching closed_at"
                )

    def _validate_action_provenance(self, action: ClientPositionAction) -> None:
        if action.position_id != self.position_id:
            raise ClientPositionLifecycleValidationError(
                "position action position_id does not match lifecycle"
            )
        if action.account_id != self.plan.account_id:
            raise ClientPositionLifecycleValidationError(
                "position action account_id does not match execution plan"
            )
        if action.decision_id != self.plan.decision_id:
            raise ClientPositionLifecycleValidationError(
                "position action decision_id does not match execution plan"
            )
        if action.account_policy_ref != self.plan.account_policy_ref:
            raise ClientPositionLifecycleValidationError(
                "position action account policy does not match execution plan"
            )
        if action.account_policy_snapshot_id != self.plan.account_policy_snapshot_id:
            raise ClientPositionLifecycleValidationError(
                "position action account policy snapshot does not match plan"
            )
        if action.execution_policy_id != self.plan.execution_policy_id:
            raise ClientPositionLifecycleValidationError(
                "position action execution policy does not match plan"
            )
        if action.protection_policy_ref != self.plan.protection_policy_ref:
            raise ClientPositionLifecycleValidationError(
                "position action protection policy does not match plan"
            )
        if action.trailing_policy_ref != self.plan.trailing_policy_ref:
            raise ClientPositionLifecycleValidationError(
                "position action trailing policy does not match plan"
            )

    def _validate_trailing_move(self, previous: OrderPrice, new: OrderPrice) -> None:
        if self.plan.side is OrderSide.BUY:
            valid = previous.value < new.value < self.take_profit.value
        else:
            valid = self.take_profit.value < new.value < previous.value
        if not valid:
            raise ClientPositionLifecycleValidationError(
                "trailing stop must improve protection without crossing take profit"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.plan.logical_values(),
            self.position_id.logical_values(),
            self.state.value,
            self.entry_price.logical_values(),
            self.current_stop.logical_values(),
            self.take_profit.logical_values(),
            self.opened_at.isoformat(),
            self.closed_at.isoformat() if self.closed_at is not None else None,
            tuple(action.logical_values() for action in self.actions),
        )


def _validate_matched_execution(
    receipt: ExecutionReceipt,
    reconciliation: ExecutionReconciliationSnapshot,
    *,
    event_at: datetime,
) -> None:
    if not isinstance(receipt, ExecutionReceipt):
        raise ClientPositionLifecycleValidationError(
            "position transition requires ExecutionReceipt"
        )
    if receipt.status is not ExecutionStatus.ACCEPTED:
        raise ClientPositionLifecycleValidationError(
            "position transition requires ACCEPTED execution receipt"
        )
    if not isinstance(reconciliation, ExecutionReconciliationSnapshot):
        raise ClientPositionLifecycleValidationError(
            "position transition requires ExecutionReconciliationSnapshot"
        )
    if reconciliation.status is not ExecutionReconciliationStatus.MATCHED:
        raise ClientPositionLifecycleValidationError(
            "position transition requires MATCHED execution reconciliation"
        )
    if reconciliation.expected != receipt or reconciliation.observed is None:
        raise ClientPositionLifecycleValidationError(
            "position transition reconciliation must bind exact receipt"
        )
    _validate_timestamp(event_at, field_name="position transition event_at")
    if event_at < receipt.recorded_at or event_at < reconciliation.reconciled_at:
        raise ClientPositionLifecycleValidationError(
            "position transition must not predate execution evidence"
        )


def _action_from_plan(
    *,
    plan: ClientExecutionPlan,
    action_id: ClientPositionActionId,
    kind: ClientPositionActionKind,
    position_id: ClientPositionId,
    occurred_at: datetime,
    evidence_ref: ClientPositionEvidenceReference,
    rationale_code: ClientPositionRationaleCode,
    execution_receipt_id: ExecutionReceiptId | None = None,
    previous_stop: OrderPrice | None = None,
    new_stop: OrderPrice | None = None,
    exit_price: OrderPrice | None = None,
    exit_reason: ClientPositionExitReason | None = None,
) -> ClientPositionAction:
    return ClientPositionAction(
        action_id=action_id,
        kind=kind,
        position_id=position_id,
        account_id=plan.account_id,
        decision_id=plan.decision_id,
        occurred_at=occurred_at,
        evidence_ref=evidence_ref,
        rationale_code=rationale_code,
        account_policy_ref=plan.account_policy_ref,
        account_policy_snapshot_id=plan.account_policy_snapshot_id,
        execution_policy_id=plan.execution_policy_id,
        protection_policy_ref=plan.protection_policy_ref,
        trailing_policy_ref=plan.trailing_policy_ref,
        execution_receipt_id=execution_receipt_id,
        previous_stop=previous_stop,
        new_stop=new_stop,
        exit_price=exit_price,
        exit_reason=exit_reason,
    )


def open_client_position(
    confirmation: ClientExecutionConfirmation,
    *,
    position_id: ClientPositionId,
    action_id: ClientPositionActionId,
    rationale_code: ClientPositionRationaleCode,
    opened_at: datetime,
) -> Result[ClientPositionLifecycle, ClientPositionLifecycleError]:
    """Create one position only from a matched, plan-bound execution confirmation."""

    if not isinstance(confirmation, ClientExecutionConfirmation):
        return Failure(
            ClientPositionLifecycleValidationError(
                "position open requires ClientExecutionConfirmation"
            )
        )
    try:
        _validate_timestamp(opened_at, field_name="position opened_at")
        if opened_at < confirmation.confirmed_at:
            raise ClientPositionLifecycleValidationError(
                "position open must not predate execution confirmation"
            )
        action = _action_from_plan(
            plan=confirmation.plan,
            action_id=action_id,
            kind=ClientPositionActionKind.OPEN,
            position_id=position_id,
            occurred_at=opened_at,
            evidence_ref=confirmation.evidence_ref,
            rationale_code=rationale_code,
            execution_receipt_id=confirmation.receipt.receipt_id,
            new_stop=confirmation.plan.stop_loss,
        )
        return Success(
            ClientPositionLifecycle(
                plan=confirmation.plan,
                position_id=position_id,
                state=ClientPositionState.OPEN,
                entry_price=confirmation.fill_price,
                current_stop=confirmation.plan.stop_loss,
                take_profit=confirmation.plan.take_profit,
                opened_at=opened_at,
                closed_at=None,
                actions=(action,),
            )
        )
    except ClientPositionLifecycleError as error:
        return Failure(error)


def apply_client_trailing_stop(
    lifecycle: ClientPositionLifecycle,
    *,
    action_id: ClientPositionActionId,
    new_stop: OrderPrice,
    evidence_ref: ClientPositionEvidenceReference,
    rationale_code: ClientPositionRationaleCode,
    occurred_at: datetime,
) -> Result[ClientPositionLifecycle, ClientPositionLifecycleError]:
    """Append one policy-bound monotonic trailing stop mutation."""

    if not isinstance(lifecycle, ClientPositionLifecycle):
        return Failure(
            ClientPositionLifecycleValidationError(
                "trailing stop requires ClientPositionLifecycle"
            )
        )
    if lifecycle.state is not ClientPositionState.OPEN:
        return Failure(
            ClientPositionLifecycleConflictError(
                "cannot trail a position that is not OPEN"
            )
        )
    if lifecycle.plan.trailing_policy_ref is None:
        return Failure(
            ClientPositionLifecycleConflictError(
                "position execution plan does not authorize trailing"
            )
        )
    try:
        _validate_timestamp(occurred_at, field_name="trailing occurred_at")
        if occurred_at < lifecycle.actions[-1].occurred_at:
            raise ClientPositionLifecycleValidationError(
                "trailing action must not predate prior lifecycle action"
            )
        action = _action_from_plan(
            plan=lifecycle.plan,
            action_id=action_id,
            kind=ClientPositionActionKind.TRAILING_STOP,
            position_id=lifecycle.position_id,
            occurred_at=occurred_at,
            evidence_ref=evidence_ref,
            rationale_code=rationale_code,
            previous_stop=lifecycle.current_stop,
            new_stop=new_stop,
        )
        return Success(
            replace(
                lifecycle,
                current_stop=new_stop,
                actions=(*lifecycle.actions, action),
            )
        )
    except ClientPositionLifecycleError as error:
        return Failure(error)


def close_client_position(
    lifecycle: ClientPositionLifecycle,
    receipt: ExecutionReceipt,
    reconciliation: ExecutionReconciliationSnapshot,
    *,
    action_id: ClientPositionActionId,
    exit_price: OrderPrice,
    exit_reason: ClientPositionExitReason,
    evidence_ref: ClientPositionEvidenceReference,
    rationale_code: ClientPositionRationaleCode,
    closed_at: datetime,
) -> Result[ClientPositionLifecycle, ClientPositionLifecycleError]:
    """Close one position from matched execution evidence without redispatch."""

    if not isinstance(lifecycle, ClientPositionLifecycle):
        return Failure(
            ClientPositionLifecycleValidationError(
                "position close requires ClientPositionLifecycle"
            )
        )
    if lifecycle.state is not ClientPositionState.OPEN:
        return Failure(
            ClientPositionLifecycleConflictError(
                "cannot close a position that is not OPEN"
            )
        )
    try:
        _validate_matched_execution(receipt, reconciliation, event_at=closed_at)
        if receipt.receipt_id == lifecycle.actions[0].execution_receipt_id:
            raise ClientPositionLifecycleValidationError(
                "position exit must use distinct execution receipt"
            )
        if closed_at < lifecycle.actions[-1].occurred_at:
            raise ClientPositionLifecycleValidationError(
                "position exit must not predate prior lifecycle action"
            )
        action = _action_from_plan(
            plan=lifecycle.plan,
            action_id=action_id,
            kind=ClientPositionActionKind.EXIT,
            position_id=lifecycle.position_id,
            occurred_at=closed_at,
            evidence_ref=evidence_ref,
            rationale_code=rationale_code,
            execution_receipt_id=receipt.receipt_id,
            exit_price=exit_price,
            exit_reason=exit_reason,
        )
        return Success(
            replace(
                lifecycle,
                state=ClientPositionState.CLOSED,
                closed_at=closed_at,
                actions=(*lifecycle.actions, action),
            )
        )
    except ClientPositionLifecycleError as error:
        return Failure(error)
