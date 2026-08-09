from __future__ import annotations

from enum import StrEnum

from qore.governance.executive_control import AuthorizedExecutiveReadRequest
from qore.governance.executive_ports import (
    ExecutiveReadDelivery,
    ExecutiveReadQueryPort,
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


class ExecutiveQueryDispatchError(DomainError):
    """Base error for MISSION-04 executive read dispatch."""

    __slots__ = ()


class ExecutiveQueryDispatchValidationError(ExecutiveQueryDispatchError):
    """The query-dispatch invocation violates a typed invariant."""

    __slots__ = ()


class ExecutiveQueryDispatchReason(StrEnum):
    DOWNSTREAM_FAILED = "downstream-failed"
    DELIVERY_INVALID = "delivery-invalid"
    DELIVERY_MISMATCH = "delivery-mismatch"
    RECEIPT_UNSAFE = "receipt-unsafe"


class ExecutiveQueryDispatchBlockedError(ExecutiveQueryDispatchError):
    """Sanitized query-dispatch failure without arbitrary downstream text."""

    __slots__ = ("reason",)

    def __init__(self, reason: ExecutiveQueryDispatchReason) -> None:
        if not isinstance(reason, ExecutiveQueryDispatchReason):
            raise ExecutiveQueryDispatchValidationError(
                "query dispatch blocked error requires ExecutiveQueryDispatchReason"
            )
        self.reason = reason
        super().__init__(reason.value)

    def logical_values(self) -> tuple[str, ...]:
        return (self.reason.value,)


def _blocked(
    reason: ExecutiveQueryDispatchReason,
) -> Failure[ExecutiveQueryDispatchError]:
    return Failure(ExecutiveQueryDispatchBlockedError(reason))


def _contains_sensitive_material(value: str) -> bool:
    normalized = value.lower()
    return any(part in normalized for part in _SENSITIVE_PARTS)


def _receipt_is_safe(delivery: ExecutiveReadDelivery) -> bool:
    receipt = delivery.receipt
    if _contains_sensitive_material(receipt.reason_code):
        return False
    return all(
        not _contains_sensitive_material(reference.value)
        for reference in receipt.evidence_refs
    )


class ExecutiveQueryDispatcher:
    """Dispatch one already-authorized executive read exactly once."""

    __slots__ = ("_port",)

    def __init__(self, port: ExecutiveReadQueryPort) -> None:
        if not callable(getattr(port, "read", None)):
            raise ExecutiveQueryDispatchValidationError(
                "query dispatcher requires ExecutiveReadQueryPort"
            )
        self._port = port

    def dispatch(
        self,
        authorized: AuthorizedExecutiveReadRequest,
    ) -> Result[ExecutiveReadDelivery, ExecutiveQueryDispatchError]:
        if not isinstance(authorized, AuthorizedExecutiveReadRequest):
            return Failure(
                ExecutiveQueryDispatchValidationError(
                    "query dispatch requires AuthorizedExecutiveReadRequest"
                )
            )

        result = self._port.read(authorized)
        if isinstance(result, Failure):
            return _blocked(ExecutiveQueryDispatchReason.DOWNSTREAM_FAILED)
        delivery = result.value
        if not isinstance(delivery, ExecutiveReadDelivery):
            return _blocked(ExecutiveQueryDispatchReason.DELIVERY_INVALID)
        if delivery.authorized_request != authorized:
            return _blocked(ExecutiveQueryDispatchReason.DELIVERY_MISMATCH)
        if not _receipt_is_safe(delivery):
            return _blocked(ExecutiveQueryDispatchReason.RECEIPT_UNSAFE)
        return Success(delivery)
