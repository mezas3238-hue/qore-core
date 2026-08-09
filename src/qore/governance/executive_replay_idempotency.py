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
    ExecutiveAuthorityVersion,
    ExecutivePrincipalId,
)
from qore.governance.executive_governance_mutation import ExecutiveGovernanceMutationRequest
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


class ExecutiveReplayProtectionError(DomainError):
    """Base error for executive replay and idempotency protection."""

    __slots__ = ()


class ExecutiveReplayProtectionValidationError(ExecutiveReplayProtectionError):
    """A replay-protection value violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveReplayProtectionUnavailableError(ExecutiveReplayProtectionError):
    """The authoritative replay-claim boundary cannot answer."""

    __slots__ = ()


class ExecutiveReplayBlockedError(ExecutiveReplayProtectionError):
    """A replay claim failed closed before any protected downstream action."""

    __slots__ = ("reason",)

    def __init__(self, reason: ExecutiveReplayBlockReason) -> None:
        if not isinstance(reason, ExecutiveReplayBlockReason):
            raise ExecutiveReplayProtectionValidationError(
                "replay blocked error requires ExecutiveReplayBlockReason"
            )
        self.reason = reason
        super().__init__(reason.value)

    def logical_values(self) -> tuple[str, ...]:
        return (self.reason.value,)


class ExecutiveReplayOperation(StrEnum):
    CONTROL_DISPATCH = "control-dispatch"
    GOVERNANCE_MUTATION = "governance-mutation"


class ExecutiveReplayClaimStatus(StrEnum):
    ACQUIRED = "acquired"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"


class ExecutiveReplayBlockReason(StrEnum):
    CLAIM_BOUNDARY_FAILED = "claim-boundary-failed"
    CLAIM_RECEIPT_INVALID = "claim-receipt-invalid"
    CLAIM_RECEIPT_MISMATCH = "claim-receipt-mismatch"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveReplayProtectionValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveReplayProtectionValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_component(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z0-9][a-z0-9._:/-]*", value) is None:
        raise ExecutiveReplayProtectionValidationError(
            "replay fingerprint component must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ExecutiveReplayProtectionValidationError(
            "replay fingerprint component must not contain sensitive material"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveReplayKey:
    operation: ExecutiveReplayOperation
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.operation, ExecutiveReplayOperation):
            raise ExecutiveReplayProtectionValidationError(
                "replay key requires ExecutiveReplayOperation"
            )
        if not isinstance(self.value, UUID):
            raise ExecutiveReplayProtectionValidationError("replay key value must be UUID")

    def logical_values(self) -> tuple[str, str]:
        return (self.operation.value, str(self.value))


@dataclass(frozen=True, slots=True)
class ExecutiveReplayFingerprint:
    components: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.components, tuple) or not self.components:
            raise ExecutiveReplayProtectionValidationError(
                "replay fingerprint requires a non-empty immutable tuple"
            )
        validated = tuple(_validate_component(value) for value in self.components)
        object.__setattr__(self, "components", validated)

    def logical_values(self) -> tuple[str, ...]:
        return self.components


@dataclass(frozen=True, slots=True)
class ExecutiveReplayClaimRequest:
    key: ExecutiveReplayKey
    fingerprint: ExecutiveReplayFingerprint
    principal_id: ExecutivePrincipalId
    authority_version: ExecutiveAuthorityVersion
    correlation_id: CorrelationId
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.key, ExecutiveReplayKey):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim request requires ExecutiveReplayKey"
            )
        if not isinstance(self.fingerprint, ExecutiveReplayFingerprint):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim request requires ExecutiveReplayFingerprint"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim request requires ExecutivePrincipalId"
            )
        if not isinstance(self.authority_version, ExecutiveAuthorityVersion):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim request requires ExecutiveAuthorityVersion"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim request requires CorrelationId"
            )
        _validate_timestamp(self.requested_at, field_name="requested_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.key.logical_values(),
            self.fingerprint.logical_values(),
            self.principal_id.logical_values(),
            self.authority_version.logical_values(),
            str(self.correlation_id.value),
            self.requested_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveReplayClaimReceipt:
    key: ExecutiveReplayKey
    requested_fingerprint: ExecutiveReplayFingerprint
    observed_fingerprint: ExecutiveReplayFingerprint
    principal_id: ExecutivePrincipalId
    authority_version: ExecutiveAuthorityVersion
    correlation_id: CorrelationId
    requested_at: datetime
    completed_at: datetime
    status: ExecutiveReplayClaimStatus

    def __post_init__(self) -> None:
        if not isinstance(self.key, ExecutiveReplayKey):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim receipt requires ExecutiveReplayKey"
            )
        for field_name, fingerprint in (
            ("requested_fingerprint", self.requested_fingerprint),
            ("observed_fingerprint", self.observed_fingerprint),
        ):
            if not isinstance(fingerprint, ExecutiveReplayFingerprint):
                raise ExecutiveReplayProtectionValidationError(
                    f"{field_name} must be ExecutiveReplayFingerprint"
                )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim receipt requires ExecutivePrincipalId"
            )
        if not isinstance(self.authority_version, ExecutiveAuthorityVersion):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim receipt requires ExecutiveAuthorityVersion"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim receipt requires CorrelationId"
            )
        _validate_timestamp(self.requested_at, field_name="requested_at")
        _validate_timestamp(self.completed_at, field_name="completed_at")
        if self.completed_at < self.requested_at:
            raise ExecutiveReplayProtectionValidationError(
                "replay claim receipt completion must not predate request"
            )
        if not isinstance(self.status, ExecutiveReplayClaimStatus):
            raise ExecutiveReplayProtectionValidationError(
                "replay claim receipt requires ExecutiveReplayClaimStatus"
            )
        same = self.observed_fingerprint == self.requested_fingerprint
        if self.status in {
            ExecutiveReplayClaimStatus.ACQUIRED,
            ExecutiveReplayClaimStatus.DUPLICATE,
        } and not same:
            raise ExecutiveReplayProtectionValidationError(
                "acquired or duplicate claim must observe requested fingerprint"
            )
        if self.status is ExecutiveReplayClaimStatus.CONFLICT and same:
            raise ExecutiveReplayProtectionValidationError(
                "conflict claim must observe a different fingerprint"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.key.logical_values(),
            self.requested_fingerprint.logical_values(),
            self.observed_fingerprint.logical_values(),
            self.principal_id.logical_values(),
            self.authority_version.logical_values(),
            str(self.correlation_id.value),
            self.requested_at.isoformat(),
            self.completed_at.isoformat(),
            self.status.value,
        )


class ExecutiveReplayClaimPort(Protocol):
    """Authoritative persistence-neutral claim boundary used before dispatch or mutation."""

    def claim(
        self,
        request: ExecutiveReplayClaimRequest,
    ) -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]: ...


def build_executive_control_replay_claim(
    authorized: AuthorizedExecutiveControlIntent,
    *,
    requested_at: datetime,
) -> Result[ExecutiveReplayClaimRequest, ExecutiveReplayProtectionError]:
    if not isinstance(authorized, AuthorizedExecutiveControlIntent):
        return Failure(
            ExecutiveReplayProtectionValidationError(
                "control replay claim requires AuthorizedExecutiveControlIntent"
            )
        )
    try:
        _validate_timestamp(requested_at, field_name="requested_at")
        if requested_at < authorized.authorized_at:
            raise ExecutiveReplayProtectionValidationError(
                "control replay claim cannot predate authorization"
            )
        intent = authorized.intent
        target_components = (
            ("target:none",)
            if intent.target is None
            else (
                f"target-kind:{intent.target.kind.value}",
                f"target:{intent.target.value}",
            )
        )
        fingerprint = ExecutiveReplayFingerprint(
            (
                f"intent:{intent.intent_id.value}",
                f"principal:{intent.principal_id.value}",
                f"action:{intent.action.value}",
                *target_components,
                f"authority:{authorized.grant.authority_version.value}",
                f"correlation:{intent.correlation_id.value}",
            )
        )
        return Success(
            ExecutiveReplayClaimRequest(
                key=ExecutiveReplayKey(
                    operation=ExecutiveReplayOperation.CONTROL_DISPATCH,
                    value=intent.intent_id.value,
                ),
                fingerprint=fingerprint,
                principal_id=intent.principal_id,
                authority_version=authorized.grant.authority_version,
                correlation_id=intent.correlation_id,
                requested_at=requested_at,
            )
        )
    except ExecutiveReplayProtectionError as error:
        return Failure(error)


def build_executive_mutation_replay_claim(
    request: ExecutiveGovernanceMutationRequest,
    *,
    requested_at: datetime,
) -> Result[ExecutiveReplayClaimRequest, ExecutiveReplayProtectionError]:
    if not isinstance(request, ExecutiveGovernanceMutationRequest):
        return Failure(
            ExecutiveReplayProtectionValidationError(
                "mutation replay claim requires ExecutiveGovernanceMutationRequest"
            )
        )
    try:
        _validate_timestamp(requested_at, field_name="requested_at")
        if requested_at < request.requested_at:
            raise ExecutiveReplayProtectionValidationError(
                "mutation replay claim cannot predate mutation request"
            )
        authorized = request.authorized
        intent = authorized.intent
        fingerprint = ExecutiveReplayFingerprint(
            (
                f"mutation:{request.mutation_id.value}",
                f"intent:{intent.intent_id.value}",
                f"principal:{intent.principal_id.value}",
                f"authority:{authorized.grant.authority_version.value}",
                f"correlation:{intent.correlation_id.value}",
                f"source-receipt:{request.source_receipt_id.value}",
                f"expected-snapshot:{request.expected_state.snapshot_id.value}",
                f"expected-version:{request.expected_state.state_version.value}",
                f"requested-snapshot:{request.next_state.snapshot_id.value}",
                f"requested-version:{request.next_state.state_version.value}",
            )
        )
        return Success(
            ExecutiveReplayClaimRequest(
                key=ExecutiveReplayKey(
                    operation=ExecutiveReplayOperation.GOVERNANCE_MUTATION,
                    value=request.mutation_id.value,
                ),
                fingerprint=fingerprint,
                principal_id=intent.principal_id,
                authority_version=authorized.grant.authority_version,
                correlation_id=intent.correlation_id,
                requested_at=requested_at,
            )
        )
    except ExecutiveReplayProtectionError as error:
        return Failure(error)


def build_executive_replay_claim_receipt(
    request: ExecutiveReplayClaimRequest,
    *,
    observed_fingerprint: ExecutiveReplayFingerprint,
    completed_at: datetime,
    status: ExecutiveReplayClaimStatus,
) -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]:
    if not isinstance(request, ExecutiveReplayClaimRequest):
        return Failure(
            ExecutiveReplayProtectionValidationError(
                "replay receipt builder requires ExecutiveReplayClaimRequest"
            )
        )
    try:
        return Success(
            ExecutiveReplayClaimReceipt(
                key=request.key,
                requested_fingerprint=request.fingerprint,
                observed_fingerprint=observed_fingerprint,
                principal_id=request.principal_id,
                authority_version=request.authority_version,
                correlation_id=request.correlation_id,
                requested_at=request.requested_at,
                completed_at=completed_at,
                status=status,
            )
        )
    except ExecutiveReplayProtectionError as error:
        return Failure(error)


def _blocked(reason: ExecutiveReplayBlockReason) -> Failure[ExecutiveReplayProtectionError]:
    return Failure(ExecutiveReplayBlockedError(reason))


class ExecutiveReplayProtector:
    """Fail-closed pre-dispatch replay gate with one claim call and no automatic retry."""

    __slots__ = ("_port",)

    def __init__(self, port: ExecutiveReplayClaimPort) -> None:
        if not callable(getattr(port, "claim", None)):
            raise ExecutiveReplayProtectionValidationError(
                "replay protector requires ExecutiveReplayClaimPort"
            )
        self._port = port

    def protect(
        self,
        request: ExecutiveReplayClaimRequest,
    ) -> Result[ExecutiveReplayClaimReceipt, ExecutiveReplayProtectionError]:
        if not isinstance(request, ExecutiveReplayClaimRequest):
            return Failure(
                ExecutiveReplayProtectionValidationError(
                    "replay protection requires ExecutiveReplayClaimRequest"
                )
            )
        result = self._port.claim(request)
        if isinstance(result, Failure):
            return _blocked(ExecutiveReplayBlockReason.CLAIM_BOUNDARY_FAILED)
        receipt = result.value
        if not isinstance(receipt, ExecutiveReplayClaimReceipt):
            return _blocked(ExecutiveReplayBlockReason.CLAIM_RECEIPT_INVALID)
        if (
            receipt.key != request.key
            or receipt.requested_fingerprint != request.fingerprint
            or receipt.principal_id != request.principal_id
            or receipt.authority_version != request.authority_version
            or receipt.correlation_id != request.correlation_id
            or receipt.requested_at != request.requested_at
            or receipt.completed_at < request.requested_at
        ):
            return _blocked(ExecutiveReplayBlockReason.CLAIM_RECEIPT_MISMATCH)
        if receipt.status is ExecutiveReplayClaimStatus.DUPLICATE:
            return _blocked(ExecutiveReplayBlockReason.DUPLICATE)
        if receipt.status is ExecutiveReplayClaimStatus.CONFLICT:
            return _blocked(ExecutiveReplayBlockReason.CONFLICT)
        return Success(receipt)
