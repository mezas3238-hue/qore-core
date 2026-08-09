from __future__ import annotations

from enum import StrEnum

from qore.governance.executive_control import AuthorizedExecutiveControlIntent
from qore.governance.executive_ports import (
    ExecutiveControlCommandPort,
    ExecutiveControlReceipt,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password",
    "private_key",
    "secret",
    "token",
)


class ExecutiveCommandDispatchError(DomainError):
    """Base error for MISSION-04 executive governance command dispatch."""

    __slots__ = ()


class ExecutiveCommandDispatchValidationError(ExecutiveCommandDispatchError):
    """The command-dispatch invocation violates a typed invariant."""

    __slots__ = ()


class ExecutiveCommandDispatchReason(StrEnum):
    DOWNSTREAM_FAILED = "downstream-failed"
    RECEIPT_INVALID = "receipt-invalid"
    RECEIPT_MISMATCH = "receipt-mismatch"
    RECEIPT_UNSAFE = "receipt-unsafe"


class ExecutiveCommandDispatchBlockedError(ExecutiveCommandDispatchError):
    """Sanitized dispatch failure that never copies arbitrary downstream text."""

    __slots__ = ("reason",)

    def __init__(self, reason: ExecutiveCommandDispatchReason) -> None:
        if not isinstance(reason, ExecutiveCommandDispatchReason):
            raise ExecutiveCommandDispatchValidationError(
                "command dispatch blocked error requires ExecutiveCommandDispatchReason"
            )
        self.reason = reason
        super().__init__(reason.value)

    def logical_values(self) -> tuple[str, ...]:
        return (self.reason.value,)


def _blocked(
    reason: ExecutiveCommandDispatchReason,
) -> Failure[ExecutiveCommandDispatchError]:
    return Failure(ExecutiveCommandDispatchBlockedError(reason))


def _contains_sensitive_material(value: str) -> bool:
    normalized = value.lower()
    return any(part in normalized for part in _SENSITIVE_PARTS)


def _receipt_is_safe(receipt: ExecutiveControlReceipt) -> bool:
    if _contains_sensitive_material(receipt.reason_code):
        return False
    return all(
        not _contains_sensitive_material(reference.value)
        for reference in receipt.evidence_refs
    )


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


class ExecutiveCommandDispatcher:
    """Dispatch one already-authorized governance intent exactly once."""

    __slots__ = ("_port",)

    def __init__(self, port: ExecutiveControlCommandPort) -> None:
        if not callable(getattr(port, "apply", None)):
            raise ExecutiveCommandDispatchValidationError(
                "command dispatcher requires ExecutiveControlCommandPort"
            )
        self._port = port

    def dispatch(
        self,
        authorized: AuthorizedExecutiveControlIntent,
    ) -> Result[ExecutiveControlReceipt, ExecutiveCommandDispatchError]:
        if not isinstance(authorized, AuthorizedExecutiveControlIntent):
            return Failure(
                ExecutiveCommandDispatchValidationError(
                    "command dispatch requires AuthorizedExecutiveControlIntent"
                )
            )

        result = self._port.apply(authorized)
        if isinstance(result, Failure):
            return _blocked(ExecutiveCommandDispatchReason.DOWNSTREAM_FAILED)
        receipt = result.value
        if not isinstance(receipt, ExecutiveControlReceipt):
            return _blocked(ExecutiveCommandDispatchReason.RECEIPT_INVALID)
        if not _receipt_matches_authorization(receipt, authorized):
            return _blocked(ExecutiveCommandDispatchReason.RECEIPT_MISMATCH)
        if not _receipt_is_safe(receipt):
            return _blocked(ExecutiveCommandDispatchReason.RECEIPT_UNSAFE)
        return Success(receipt)
