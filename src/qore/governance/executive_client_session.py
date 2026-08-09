from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_authentication import (
    AuthenticatedExecutivePrincipal,
    ExecutiveAuthenticationAssertionId,
    evaluate_authenticated_executive_principal,
)
from qore.governance.executive_client_surface import (
    ExecutiveClientSurface,
    ExecutiveClientSurfaceId,
)
from qore.governance.executive_control import ExecutivePrincipalId
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


class ExecutiveClientSessionError(DomainError):
    """Base error for client session provenance and binding contracts."""

    __slots__ = ()


class ExecutiveClientSessionValidationError(ExecutiveClientSessionError):
    """A client session violates a deterministic contract invariant."""

    __slots__ = ()


class ExecutiveClientSessionBlockedError(ExecutiveClientSessionError):
    """A client session is not safe to bind at the requested evaluation time."""

    __slots__ = ()


class ExecutiveClientSessionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveClientSessionValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveClientSessionValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_device_ref(value: str) -> str:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9._:/-]*",
        value,
    ) is None:
        raise ExecutiveClientSessionValidationError(
            "executive client device ref must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ExecutiveClientSessionValidationError(
            "executive client device ref must not contain sensitive material"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveClientSessionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveClientSessionValidationError(
                "executive client session id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveClientDeviceRef:
    """Opaque safe device reference, never hardware identity or secret material."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_device_ref(self.value))

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveClientSession:
    """Secret-free external session provenance consumed by MISSION-05."""

    session_id: ExecutiveClientSessionId
    surface_id: ExecutiveClientSurfaceId
    device_ref: ExecutiveClientDeviceRef
    principal_id: ExecutivePrincipalId
    authentication_assertion_id: ExecutiveAuthenticationAssertionId
    status: ExecutiveClientSessionStatus
    established_at: datetime
    expires_at: datetime
    correlation_id: CorrelationId

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, ExecutiveClientSessionId):
            raise ExecutiveClientSessionValidationError(
                "executive client session requires ExecutiveClientSessionId"
            )
        if not isinstance(self.surface_id, ExecutiveClientSurfaceId):
            raise ExecutiveClientSessionValidationError(
                "executive client session requires ExecutiveClientSurfaceId"
            )
        if not isinstance(self.device_ref, ExecutiveClientDeviceRef):
            raise ExecutiveClientSessionValidationError(
                "executive client session requires ExecutiveClientDeviceRef"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveClientSessionValidationError(
                "executive client session requires ExecutivePrincipalId"
            )
        if not isinstance(
            self.authentication_assertion_id,
            ExecutiveAuthenticationAssertionId,
        ):
            raise ExecutiveClientSessionValidationError(
                "executive client session requires ExecutiveAuthenticationAssertionId"
            )
        if not isinstance(self.status, ExecutiveClientSessionStatus):
            raise ExecutiveClientSessionValidationError(
                "executive client session requires explicit status"
            )
        _validate_timestamp(self.established_at, field_name="established_at")
        _validate_timestamp(self.expires_at, field_name="expires_at")
        if self.expires_at <= self.established_at:
            raise ExecutiveClientSessionValidationError(
                "executive client session expiry must follow establishment"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveClientSessionValidationError(
                "executive client session requires CorrelationId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.session_id.logical_values(),
            self.surface_id.logical_values(),
            self.device_ref.logical_values(),
            self.principal_id.logical_values(),
            self.authentication_assertion_id.logical_values(),
            self.status.value,
            self.established_at.isoformat(),
            self.expires_at.isoformat(),
            str(self.correlation_id.value),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveClientSessionBinding:
    """Exact safe binding of one active client session to one auth assertion."""

    session: ExecutiveClientSession
    surface: ExecutiveClientSurface
    authenticated_principal: AuthenticatedExecutivePrincipal
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.session, ExecutiveClientSession):
            raise ExecutiveClientSessionValidationError(
                "client session binding requires ExecutiveClientSession"
            )
        if not isinstance(self.surface, ExecutiveClientSurface):
            raise ExecutiveClientSessionValidationError(
                "client session binding requires ExecutiveClientSurface"
            )
        if not isinstance(
            self.authenticated_principal,
            AuthenticatedExecutivePrincipal,
        ):
            raise ExecutiveClientSessionValidationError(
                "client session binding requires AuthenticatedExecutivePrincipal"
            )
        _validate_timestamp(self.evaluated_at, field_name="evaluated_at")
        if self.session.status is not ExecutiveClientSessionStatus.ACTIVE:
            raise ExecutiveClientSessionBlockedError(
                "executive client session is not active"
            )
        if self.session.surface_id != self.surface.surface_id:
            raise ExecutiveClientSessionBlockedError(
                "executive client session surface does not match client surface"
            )
        principal = self.authenticated_principal
        if self.session.principal_id != principal.principal_id:
            raise ExecutiveClientSessionBlockedError(
                "executive client session principal does not match authentication"
            )
        if self.session.authentication_assertion_id != principal.assertion_id:
            raise ExecutiveClientSessionBlockedError(
                "executive client session assertion does not match authentication"
            )
        if self.session.correlation_id != principal.correlation_id:
            raise ExecutiveClientSessionBlockedError(
                "executive client session correlation does not match authentication"
            )
        if self.session.established_at < principal.issued_at:
            raise ExecutiveClientSessionBlockedError(
                "executive client session cannot predate authentication assertion"
            )
        if self.session.expires_at > principal.expires_at:
            raise ExecutiveClientSessionBlockedError(
                "executive client session cannot outlive authentication assertion"
            )
        if self.evaluated_at < self.session.established_at:
            raise ExecutiveClientSessionBlockedError(
                "executive client session is not yet active"
            )
        if self.evaluated_at > self.session.expires_at:
            raise ExecutiveClientSessionBlockedError(
                "executive client session has expired"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.session.logical_values(),
            self.surface.logical_values(),
            self.authenticated_principal.logical_values(),
            self.evaluated_at.isoformat(),
        )


def build_executive_client_session(
    *,
    session_id: ExecutiveClientSessionId,
    surface_id: ExecutiveClientSurfaceId,
    device_ref: ExecutiveClientDeviceRef,
    principal_id: ExecutivePrincipalId,
    authentication_assertion_id: ExecutiveAuthenticationAssertionId,
    status: ExecutiveClientSessionStatus,
    established_at: datetime,
    expires_at: datetime,
    correlation_id: CorrelationId,
) -> Result[ExecutiveClientSession, ExecutiveClientSessionError]:
    try:
        return Success(
            ExecutiveClientSession(
                session_id=session_id,
                surface_id=surface_id,
                device_ref=device_ref,
                principal_id=principal_id,
                authentication_assertion_id=authentication_assertion_id,
                status=status,
                established_at=established_at,
                expires_at=expires_at,
                correlation_id=correlation_id,
            )
        )
    except ExecutiveClientSessionError as error:
        return Failure(error)


def bind_executive_client_session(
    session: ExecutiveClientSession,
    surface: ExecutiveClientSurface,
    authenticated_principal: AuthenticatedExecutivePrincipal,
    *,
    evaluated_at: datetime,
) -> Result[ExecutiveClientSessionBinding, ExecutiveClientSessionError]:
    if not isinstance(session, ExecutiveClientSession):
        return Failure(
            ExecutiveClientSessionValidationError(
                "client session binding requires ExecutiveClientSession"
            )
        )
    if not isinstance(surface, ExecutiveClientSurface):
        return Failure(
            ExecutiveClientSessionValidationError(
                "client session binding requires ExecutiveClientSurface"
            )
        )
    if not isinstance(authenticated_principal, AuthenticatedExecutivePrincipal):
        return Failure(
            ExecutiveClientSessionValidationError(
                "client session binding requires AuthenticatedExecutivePrincipal"
            )
        )
    authentication_result = evaluate_authenticated_executive_principal(
        authenticated_principal,
        evaluated_at=evaluated_at,
    )
    if isinstance(authentication_result, Failure):
        return Failure(
            ExecutiveClientSessionBlockedError(
                "authenticated principal is not valid for client session binding"
            )
        )
    try:
        return Success(
            ExecutiveClientSessionBinding(
                session=session,
                surface=surface,
                authenticated_principal=authenticated_principal,
                evaluated_at=evaluated_at,
            )
        )
    except ExecutiveClientSessionError as error:
        return Failure(error)
