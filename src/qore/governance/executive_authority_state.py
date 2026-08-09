from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from typing import Protocol
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutivePrincipalId,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Result

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password",
    "private_key",
    "secret",
    "token",
)


class ExecutiveAuthorityStateError(DomainError):
    """Base error for current executive authority state contracts."""

    __slots__ = ()


class ExecutiveAuthorityStateValidationError(ExecutiveAuthorityStateError):
    """A current authority-state value violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveAuthorityStateUnavailableError(ExecutiveAuthorityStateError):
    """Typed failure when the authoritative state source cannot answer."""

    __slots__ = ()


class ExecutiveAuthorityStateStatus(StrEnum):
    """Closed current lifecycle state of one executive principal's authority."""

    ACTIVE = "active"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveAuthorityStateValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveAuthorityStateValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_public_ref(value: str) -> str:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9._:/-]*",
        value,
    ) is None:
        raise ExecutiveAuthorityStateValidationError(
            "authority state evidence ref must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ExecutiveAuthorityStateValidationError(
            "authority state evidence ref must not contain sensitive material"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveAuthorityStateRequestId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveAuthorityStateValidationError(
                "authority state request id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveAuthorityStateEvidenceRef:
    """Opaque sanitized reference to the authoritative materialized-state record."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_public_ref(self.value))

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveAuthorityStateRequest:
    request_id: ExecutiveAuthorityStateRequestId
    principal_id: ExecutivePrincipalId
    requested_at: datetime
    correlation_id: CorrelationId

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, ExecutiveAuthorityStateRequestId):
            raise ExecutiveAuthorityStateValidationError(
                "authority state request requires ExecutiveAuthorityStateRequestId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveAuthorityStateValidationError(
                "authority state request requires ExecutivePrincipalId"
            )
        _validate_timestamp(self.requested_at, field_name="requested_at")
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveAuthorityStateValidationError(
                "authority state request requires CorrelationId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_id.logical_values(),
            self.principal_id.logical_values(),
            self.requested_at.isoformat(),
            str(self.correlation_id.value),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveAuthorityStateSnapshot:
    """Authoritative current state; never inferred from incomplete audit history."""

    request_id: ExecutiveAuthorityStateRequestId
    principal_id: ExecutivePrincipalId
    status: ExecutiveAuthorityStateStatus
    observed_at: datetime
    evidence_ref: ExecutiveAuthorityStateEvidenceRef
    grant: ExecutiveAuthorityGrant | None = None
    invalidated_at: datetime | None = None
    superseding_version: ExecutiveAuthorityVersion | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, ExecutiveAuthorityStateRequestId):
            raise ExecutiveAuthorityStateValidationError(
                "authority state snapshot requires ExecutiveAuthorityStateRequestId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveAuthorityStateValidationError(
                "authority state snapshot requires ExecutivePrincipalId"
            )
        if not isinstance(self.status, ExecutiveAuthorityStateStatus):
            raise ExecutiveAuthorityStateValidationError(
                "authority state snapshot requires ExecutiveAuthorityStateStatus"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")
        if not isinstance(self.evidence_ref, ExecutiveAuthorityStateEvidenceRef):
            raise ExecutiveAuthorityStateValidationError(
                "authority state snapshot requires ExecutiveAuthorityStateEvidenceRef"
            )
        if self.invalidated_at is not None:
            _validate_timestamp(self.invalidated_at, field_name="invalidated_at")
            if self.invalidated_at > self.observed_at:
                raise ExecutiveAuthorityStateValidationError(
                    "authority invalidation must not postdate observation"
                )
        if self.superseding_version is not None and not isinstance(
            self.superseding_version,
            ExecutiveAuthorityVersion,
        ):
            raise ExecutiveAuthorityStateValidationError(
                "superseding version must be ExecutiveAuthorityVersion or None"
            )

        if self.status is ExecutiveAuthorityStateStatus.UNKNOWN:
            if (
                self.grant is not None
                or self.invalidated_at is not None
                or self.superseding_version is not None
            ):
                raise ExecutiveAuthorityStateValidationError(
                    "unknown authority state must not fabricate grant lifecycle data"
                )
            return

        if not isinstance(self.grant, ExecutiveAuthorityGrant):
            raise ExecutiveAuthorityStateValidationError(
                "known authority state requires ExecutiveAuthorityGrant"
            )
        if self.grant.principal_id != self.principal_id:
            raise ExecutiveAuthorityStateValidationError(
                "authority state grant principal must match snapshot principal"
            )
        if self.observed_at < self.grant.issued_at:
            raise ExecutiveAuthorityStateValidationError(
                "authority state observation must not predate grant issue"
            )

        if self.status is ExecutiveAuthorityStateStatus.ACTIVE:
            if self.observed_at > self.grant.expires_at:
                raise ExecutiveAuthorityStateValidationError(
                    "active authority state cannot outlive grant expiry"
                )
            if self.invalidated_at is not None or self.superseding_version is not None:
                raise ExecutiveAuthorityStateValidationError(
                    "active authority state must not carry invalidation data"
                )
            return

        if self.status is ExecutiveAuthorityStateStatus.EXPIRED:
            if self.observed_at <= self.grant.expires_at:
                raise ExecutiveAuthorityStateValidationError(
                    "expired authority state requires observation after grant expiry"
                )
            if self.invalidated_at is not None or self.superseding_version is not None:
                raise ExecutiveAuthorityStateValidationError(
                    "expired authority state must not carry invalidation data"
                )
            return

        if self.invalidated_at is None:
            raise ExecutiveAuthorityStateValidationError(
                "revoked or superseded authority state requires invalidated_at"
            )
        if self.invalidated_at < self.grant.issued_at:
            raise ExecutiveAuthorityStateValidationError(
                "authority invalidation must not predate grant issue"
            )

        if self.status is ExecutiveAuthorityStateStatus.REVOKED:
            if self.superseding_version is not None:
                raise ExecutiveAuthorityStateValidationError(
                    "revoked authority state must not carry superseding version"
                )
            return

        if self.status is ExecutiveAuthorityStateStatus.SUPERSEDED:
            if not isinstance(self.superseding_version, ExecutiveAuthorityVersion):
                raise ExecutiveAuthorityStateValidationError(
                    "superseded authority state requires superseding version"
                )
            if self.superseding_version == self.grant.authority_version:
                raise ExecutiveAuthorityStateValidationError(
                    "superseding authority version must differ from replaced version"
                )

    @property
    def is_active(self) -> bool:
        return self.status is ExecutiveAuthorityStateStatus.ACTIVE

    @property
    def active_grant(self) -> ExecutiveAuthorityGrant | None:
        return self.grant if self.is_active else None

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_id.logical_values(),
            self.principal_id.logical_values(),
            self.status.value,
            self.observed_at.isoformat(),
            self.evidence_ref.logical_values(),
            self.grant.logical_values() if self.grant is not None else None,
            self.invalidated_at.isoformat() if self.invalidated_at is not None else None,
            (
                self.superseding_version.logical_values()
                if self.superseding_version is not None
                else None
            ),
        )


class ExecutiveAuthorityStateSource(Protocol):
    """Canonical source of current executive authority lifecycle state."""

    def read_current(
        self,
        request: ExecutiveAuthorityStateRequest,
    ) -> Result[ExecutiveAuthorityStateSnapshot, ExecutiveAuthorityStateError]: ...
