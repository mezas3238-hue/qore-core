from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.executive_client_surface import ExecutiveClientSurfaceId
from qore.governance.executive_control import AuthorizedExecutiveControlIntent
from qore.governance.executive_ports import (
    ExecutiveControlReceipt,
    ExecutiveControlReceiptStatus,
)
from qore.governance.executive_replay_idempotency import (
    ExecutiveReplayClaimReceipt,
    ExecutiveReplayClaimStatus,
    ExecutiveReplayOperation,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveGovernanceUxError(DomainError):
    """Base error for CEO governance presentation-state contracts."""

    __slots__ = ()


class ExecutiveGovernanceUxValidationError(ExecutiveGovernanceUxError):
    """A governance UX value violates a deterministic presentation invariant."""

    __slots__ = ()


class ExecutiveGovernanceUxPhase(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    NO_ACTION = "no-action"
    BLOCKED = "blocked"
    FAILED = "failed"
    OUTCOME_UNKNOWN = "outcome-unknown"


_TERMINAL_PHASE_BY_RECEIPT: dict[
    ExecutiveControlReceiptStatus,
    ExecutiveGovernanceUxPhase,
] = {
    ExecutiveControlReceiptStatus.APPLIED: ExecutiveGovernanceUxPhase.APPLIED,
    ExecutiveControlReceiptStatus.NO_CHANGE: ExecutiveGovernanceUxPhase.NO_ACTION,
    ExecutiveControlReceiptStatus.BLOCKED: ExecutiveGovernanceUxPhase.BLOCKED,
    ExecutiveControlReceiptStatus.FAILED: ExecutiveGovernanceUxPhase.FAILED,
}


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveGovernanceUxValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveGovernanceUxValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_reason_code(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ExecutiveGovernanceUxValidationError(
            "governance UX reason code must use canonical lowercase syntax"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceUxStateId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveGovernanceUxValidationError(
                "governance UX state id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _receipt_matches_authorization(
    receipt: ExecutiveControlReceipt,
    authorized: AuthorizedExecutiveControlIntent,
) -> bool:
    intent = authorized.intent
    grant = authorized.grant
    return (
        receipt.intent_id == intent.intent_id
        and receipt.principal_id == intent.principal_id
        and receipt.action is intent.action
        and receipt.target == intent.target
        and receipt.authority_version == grant.authority_version
        and receipt.correlation_id == intent.correlation_id
        and receipt.received_at >= authorized.authorized_at
    )


def _replay_matches_authorization(
    replay: ExecutiveReplayClaimReceipt,
    authorized: AuthorizedExecutiveControlIntent,
) -> bool:
    intent = authorized.intent
    grant = authorized.grant
    return (
        replay.key.operation is ExecutiveReplayOperation.CONTROL_DISPATCH
        and replay.key.value == intent.intent_id.value
        and replay.principal_id == intent.principal_id
        and replay.authority_version == grant.authority_version
        and replay.correlation_id == intent.correlation_id
        and replay.requested_at >= authorized.authorized_at
    )


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceUxState:
    """Presentation-only lifecycle for one already-authorized governance intent."""

    state_id: ExecutiveGovernanceUxStateId
    surface_id: ExecutiveClientSurfaceId
    authorized: AuthorizedExecutiveControlIntent
    phase: ExecutiveGovernanceUxPhase
    observed_at: datetime
    reason_code: str
    receipt: ExecutiveControlReceipt | None = None
    replay_claim: ExecutiveReplayClaimReceipt | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state_id, ExecutiveGovernanceUxStateId):
            raise ExecutiveGovernanceUxValidationError(
                "governance UX state requires ExecutiveGovernanceUxStateId"
            )
        if not isinstance(self.surface_id, ExecutiveClientSurfaceId):
            raise ExecutiveGovernanceUxValidationError(
                "governance UX state requires ExecutiveClientSurfaceId"
            )
        if not isinstance(self.authorized, AuthorizedExecutiveControlIntent):
            raise ExecutiveGovernanceUxValidationError(
                "governance UX state requires AuthorizedExecutiveControlIntent"
            )
        if not isinstance(self.phase, ExecutiveGovernanceUxPhase):
            raise ExecutiveGovernanceUxValidationError(
                "governance UX state requires ExecutiveGovernanceUxPhase"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")
        object.__setattr__(self, "reason_code", _validate_reason_code(self.reason_code))
        if self.observed_at < self.authorized.authorized_at:
            raise ExecutiveGovernanceUxValidationError(
                "governance UX observation cannot predate authorization"
            )

        if self.phase is ExecutiveGovernanceUxPhase.PENDING:
            if self.receipt is not None or self.replay_claim is not None:
                raise ExecutiveGovernanceUxValidationError(
                    "pending governance UX state must not fabricate downstream evidence"
                )
            return

        if self.phase is ExecutiveGovernanceUxPhase.OUTCOME_UNKNOWN:
            if self.receipt is not None:
                raise ExecutiveGovernanceUxValidationError(
                    "unknown governance outcome must not carry a control receipt"
                )
            if not isinstance(self.replay_claim, ExecutiveReplayClaimReceipt):
                raise ExecutiveGovernanceUxValidationError(
                    "unknown governance outcome requires acquired replay evidence"
                )
            if self.replay_claim.status is not ExecutiveReplayClaimStatus.ACQUIRED:
                raise ExecutiveGovernanceUxValidationError(
                    "unknown governance outcome requires an acquired replay claim"
                )
            if not _replay_matches_authorization(self.replay_claim, self.authorized):
                raise ExecutiveGovernanceUxValidationError(
                    "unknown governance outcome replay claim must match authorization"
                )
            if self.observed_at < self.replay_claim.completed_at:
                raise ExecutiveGovernanceUxValidationError(
                    "governance UX observation cannot predate replay claim completion"
                )
            return

        if not isinstance(self.receipt, ExecutiveControlReceipt):
            raise ExecutiveGovernanceUxValidationError(
                "terminal governance UX state requires ExecutiveControlReceipt"
            )
        if self.replay_claim is not None:
            raise ExecutiveGovernanceUxValidationError(
                "terminal governance UX state must not retain replay claim as result evidence"
            )
        if not _receipt_matches_authorization(self.receipt, self.authorized):
            raise ExecutiveGovernanceUxValidationError(
                "governance UX receipt must match exact authorization"
            )
        expected_phase = _TERMINAL_PHASE_BY_RECEIPT[self.receipt.status]
        if self.phase is not expected_phase:
            raise ExecutiveGovernanceUxValidationError(
                "governance UX phase must match canonical control receipt status"
            )
        if self.observed_at < self.receipt.completed_at:
            raise ExecutiveGovernanceUxValidationError(
                "governance UX observation cannot predate receipt completion"
            )

    @property
    def automatic_redispatch_allowed(self) -> bool:
        """Governance UX never grants automatic duplicate dispatch authority."""

        return False

    @property
    def is_confirmed_applied(self) -> bool:
        return self.phase is ExecutiveGovernanceUxPhase.APPLIED

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.state_id.logical_values(),
            self.surface_id.logical_values(),
            self.authorized.logical_values(),
            self.phase.value,
            self.observed_at.isoformat(),
            self.reason_code,
            None if self.receipt is None else self.receipt.logical_values(),
            None if self.replay_claim is None else self.replay_claim.logical_values(),
            self.automatic_redispatch_allowed,
        )


def build_executive_governance_pending_state(
    *,
    state_id: ExecutiveGovernanceUxStateId,
    surface_id: ExecutiveClientSurfaceId,
    authorized: AuthorizedExecutiveControlIntent,
    observed_at: datetime,
) -> Result[ExecutiveGovernanceUxState, ExecutiveGovernanceUxError]:
    """Represent an authorized request before any downstream result is known."""

    try:
        return Success(
            ExecutiveGovernanceUxState(
                state_id=state_id,
                surface_id=surface_id,
                authorized=authorized,
                phase=ExecutiveGovernanceUxPhase.PENDING,
                observed_at=observed_at,
                reason_code="governance.pending",
            )
        )
    except ExecutiveGovernanceUxError as error:
        return Failure(error)


def build_executive_governance_result_state(
    *,
    state_id: ExecutiveGovernanceUxStateId,
    surface_id: ExecutiveClientSurfaceId,
    authorized: AuthorizedExecutiveControlIntent,
    receipt: ExecutiveControlReceipt,
    observed_at: datetime,
) -> Result[ExecutiveGovernanceUxState, ExecutiveGovernanceUxError]:
    """Represent a terminal result derived only from the canonical control receipt."""

    if not isinstance(receipt, ExecutiveControlReceipt):
        return Failure(
            ExecutiveGovernanceUxValidationError(
                "governance result state requires ExecutiveControlReceipt"
            )
        )
    try:
        return Success(
            ExecutiveGovernanceUxState(
                state_id=state_id,
                surface_id=surface_id,
                authorized=authorized,
                phase=_TERMINAL_PHASE_BY_RECEIPT[receipt.status],
                observed_at=observed_at,
                reason_code=receipt.reason_code,
                receipt=receipt,
            )
        )
    except ExecutiveGovernanceUxError as error:
        return Failure(error)


def build_executive_governance_unknown_outcome_state(
    *,
    state_id: ExecutiveGovernanceUxStateId,
    surface_id: ExecutiveClientSurfaceId,
    authorized: AuthorizedExecutiveControlIntent,
    replay_claim: ExecutiveReplayClaimReceipt,
    observed_at: datetime,
) -> Result[ExecutiveGovernanceUxState, ExecutiveGovernanceUxError]:
    """Contain an ambiguous downstream outcome without authorizing redispatch."""

    try:
        return Success(
            ExecutiveGovernanceUxState(
                state_id=state_id,
                surface_id=surface_id,
                authorized=authorized,
                phase=ExecutiveGovernanceUxPhase.OUTCOME_UNKNOWN,
                observed_at=observed_at,
                reason_code="governance.outcome_unknown",
                replay_claim=replay_claim,
            )
        )
    except ExecutiveGovernanceUxError as error:
        return Failure(error)
