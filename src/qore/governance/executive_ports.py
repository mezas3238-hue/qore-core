from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from typing import Protocol
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    AuthorizedExecutiveControlIntent,
    AuthorizedExecutiveReadRequest,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveControlError,
    ExecutiveControlTarget,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
    validate_executive_control_target_binding,
)
from qore.kernel.result import Failure, Result, Success


class ExecutivePortError(ExecutiveControlError):
    """Base error for transport-neutral executive command/query ports."""

    __slots__ = ()


class ExecutivePortValidationError(ExecutivePortError):
    """An executive port value violates deterministic receipt invariants."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutivePortValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutivePortValidationError(f"{field_name} must be timezone-aware")


def _validate_reason_code(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ExecutivePortValidationError(
            "executive receipt reason code must use canonical lowercase syntax"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveReceiptId:
    value: UUID

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveEvidenceRef:
    """Opaque sanitized reference to evidence stored outside the receipt."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._:/-]*", self.value
        ) is None:
            raise ExecutivePortValidationError(
                "executive evidence reference must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ExecutiveControlReceiptStatus(StrEnum):
    """Downstream governance outcome after an already-authorized CEO intent."""

    APPLIED = "applied"
    NO_CHANGE = "no-change"
    BLOCKED = "blocked"
    FAILED = "failed"


class ExecutiveReadReceiptStatus(StrEnum):
    """Outcome of an already-authorized executive read request."""

    SERVED = "served"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ExecutiveControlReceipt:
    """Audit-safe receipt for one authorized executive governance intent."""

    receipt_id: ExecutiveReceiptId
    intent_id: ExecutiveIntentId
    principal_id: ExecutivePrincipalId
    action: ExecutiveControlAction
    authority_version: ExecutiveAuthorityVersion
    correlation_id: CorrelationId
    received_at: datetime
    completed_at: datetime
    status: ExecutiveControlReceiptStatus
    reason_code: str
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]
    target: ExecutiveControlTarget | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_id, ExecutiveReceiptId):
            raise ExecutivePortValidationError(
                "executive control receipt requires ExecutiveReceiptId"
            )
        if not isinstance(self.intent_id, ExecutiveIntentId):
            raise ExecutivePortValidationError(
                "executive control receipt requires ExecutiveIntentId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutivePortValidationError(
                "executive control receipt requires ExecutivePrincipalId"
            )
        if not isinstance(self.action, ExecutiveControlAction):
            raise ExecutivePortValidationError(
                "executive control receipt requires ExecutiveControlAction"
            )
        try:
            validate_executive_control_target_binding(self.action, self.target)
        except ExecutiveControlError as error:
            raise ExecutivePortValidationError(
                "executive control receipt target does not match action"
            ) from error
        if not isinstance(self.authority_version, ExecutiveAuthorityVersion):
            raise ExecutivePortValidationError(
                "executive control receipt requires ExecutiveAuthorityVersion"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutivePortValidationError(
                "executive control receipt requires CorrelationId"
            )
        _validate_aware_datetime(self.received_at, field_name="received_at")
        _validate_aware_datetime(self.completed_at, field_name="completed_at")
        if self.completed_at < self.received_at:
            raise ExecutivePortValidationError(
                "executive control receipt completion must not predate receipt"
            )
        if not isinstance(self.status, ExecutiveControlReceiptStatus):
            raise ExecutivePortValidationError(
                "executive control receipt requires explicit status"
            )
        object.__setattr__(self, "reason_code", _validate_reason_code(self.reason_code))
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(item, ExecutiveEvidenceRef) for item in self.evidence_refs
        ):
            raise ExecutivePortValidationError(
                "executive control evidence refs must be a tuple of ExecutiveEvidenceRef"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ExecutivePortValidationError(
                "executive control evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.receipt_id.logical_values(),
            self.intent_id.logical_values(),
            self.principal_id.logical_values(),
            self.action.value,
            None if self.target is None else self.target.logical_values(),
            self.authority_version.logical_values(),
            str(self.correlation_id.value),
            self.received_at.isoformat(),
            self.completed_at.isoformat(),
            self.status.value,
            self.reason_code,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveReadReceipt:
    """Audit-safe receipt for one authorized executive read request."""

    receipt_id: ExecutiveReceiptId
    request_id: ExecutiveReadRequestId
    principal_id: ExecutivePrincipalId
    scope: ExecutiveReadScope
    authority_version: ExecutiveAuthorityVersion
    correlation_id: CorrelationId
    received_at: datetime
    completed_at: datetime
    status: ExecutiveReadReceiptStatus
    reason_code: str
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_id, ExecutiveReceiptId):
            raise ExecutivePortValidationError(
                "executive read receipt requires ExecutiveReceiptId"
            )
        if not isinstance(self.request_id, ExecutiveReadRequestId):
            raise ExecutivePortValidationError(
                "executive read receipt requires ExecutiveReadRequestId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutivePortValidationError(
                "executive read receipt requires ExecutivePrincipalId"
            )
        if not isinstance(self.scope, ExecutiveReadScope):
            raise ExecutivePortValidationError(
                "executive read receipt requires ExecutiveReadScope"
            )
        if not isinstance(self.authority_version, ExecutiveAuthorityVersion):
            raise ExecutivePortValidationError(
                "executive read receipt requires ExecutiveAuthorityVersion"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutivePortValidationError(
                "executive read receipt requires CorrelationId"
            )
        _validate_aware_datetime(self.received_at, field_name="received_at")
        _validate_aware_datetime(self.completed_at, field_name="completed_at")
        if self.completed_at < self.received_at:
            raise ExecutivePortValidationError(
                "executive read receipt completion must not predate receipt"
            )
        if not isinstance(self.status, ExecutiveReadReceiptStatus):
            raise ExecutivePortValidationError(
                "executive read receipt requires explicit status"
            )
        object.__setattr__(self, "reason_code", _validate_reason_code(self.reason_code))
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(item, ExecutiveEvidenceRef) for item in self.evidence_refs
        ):
            raise ExecutivePortValidationError(
                "executive read evidence refs must be a tuple of ExecutiveEvidenceRef"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ExecutivePortValidationError(
                "executive read evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.receipt_id.logical_values(),
            self.request_id.logical_values(),
            self.principal_id.logical_values(),
            self.scope.value,
            self.authority_version.logical_values(),
            str(self.correlation_id.value),
            self.received_at.isoformat(),
            self.completed_at.isoformat(),
            self.status.value,
            self.reason_code,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


def build_executive_control_receipt(
    authorized: AuthorizedExecutiveControlIntent,
    *,
    receipt_id: ExecutiveReceiptId,
    received_at: datetime,
    completed_at: datetime,
    status: ExecutiveControlReceiptStatus,
    reason_code: str,
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = (),
) -> Result[ExecutiveControlReceipt, ExecutivePortError]:
    """Build a receipt whose identity is derived from exact authorized authority."""

    if not isinstance(authorized, AuthorizedExecutiveControlIntent):
        return Failure(
            ExecutivePortValidationError(
                "control receipt requires AuthorizedExecutiveControlIntent"
            )
        )
    try:
        _validate_aware_datetime(received_at, field_name="received_at")
        _validate_aware_datetime(completed_at, field_name="completed_at")
        if received_at < authorized.authorized_at:
            raise ExecutivePortValidationError(
                "control port cannot receive intent before authorization"
            )
        return Success(
            ExecutiveControlReceipt(
                receipt_id=receipt_id,
                intent_id=authorized.intent.intent_id,
                principal_id=authorized.intent.principal_id,
                action=authorized.intent.action,
                authority_version=authorized.grant.authority_version,
                correlation_id=authorized.intent.correlation_id,
                received_at=received_at,
                completed_at=completed_at,
                status=status,
                reason_code=reason_code,
                evidence_refs=evidence_refs,
                target=authorized.intent.target,
            )
        )
    except ExecutivePortError as error:
        return Failure(error)


def build_executive_read_receipt(
    authorized: AuthorizedExecutiveReadRequest,
    *,
    receipt_id: ExecutiveReceiptId,
    received_at: datetime,
    completed_at: datetime,
    status: ExecutiveReadReceiptStatus,
    reason_code: str,
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = (),
) -> Result[ExecutiveReadReceipt, ExecutivePortError]:
    """Build a read receipt whose identity is derived from exact authorized authority."""

    if not isinstance(authorized, AuthorizedExecutiveReadRequest):
        return Failure(
            ExecutivePortValidationError(
                "read receipt requires AuthorizedExecutiveReadRequest"
            )
        )
    try:
        _validate_aware_datetime(received_at, field_name="received_at")
        _validate_aware_datetime(completed_at, field_name="completed_at")
        if received_at < authorized.authorized_at:
            raise ExecutivePortValidationError(
                "read port cannot receive request before authorization"
            )
        return Success(
            ExecutiveReadReceipt(
                receipt_id=receipt_id,
                request_id=authorized.request.request_id,
                principal_id=authorized.request.principal_id,
                scope=authorized.request.scope,
                authority_version=authorized.grant.authority_version,
                correlation_id=authorized.request.correlation_id,
                received_at=received_at,
                completed_at=completed_at,
                status=status,
                reason_code=reason_code,
                evidence_refs=evidence_refs,
            )
        )
    except ExecutivePortError as error:
        return Failure(error)


class ExecutiveControlCommandPort(Protocol):
    """Transport-neutral downstream port for already-authorized governance intents."""

    def apply(
        self,
        request: AuthorizedExecutiveControlIntent,
    ) -> Result[ExecutiveControlReceipt, ExecutivePortError]:
        """Apply governance intent and return explicit audit receipt."""
        ...


class ExecutiveReadQueryPort(Protocol):
    """Transport-neutral downstream port for already-authorized read requests."""

    def read(
        self,
        request: AuthorizedExecutiveReadRequest,
    ) -> Result[ExecutiveReadReceipt, ExecutivePortError]:
        """Serve an executive read request and return explicit audit receipt."""
        ...
