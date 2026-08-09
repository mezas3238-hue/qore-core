from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch
from uuid import UUID

from qore.domain.events import CorrelationId
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


class ExecutiveAuthenticationError(DomainError):
    """Base error for executive authentication assertion contracts."""

    __slots__ = ()


class ExecutiveAuthenticationValidationError(ExecutiveAuthenticationError):
    """An executive authentication value violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveAuthenticationBlockedError(ExecutiveAuthenticationError):
    """The supplied authentication assertion is not valid at evaluation time."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveAuthenticationValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveAuthenticationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_public_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9._-]*",
        value,
    ) is None:
        raise ExecutiveAuthenticationValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ExecutiveAuthenticationValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_boundary_ref(value: str) -> str:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9._:/-]*",
        value,
    ) is None:
        raise ExecutiveAuthenticationValidationError(
            "identity boundary ref must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ExecutiveAuthenticationValidationError(
            "identity boundary ref must not contain sensitive material"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveAuthenticationAssertionId:
    """Explicit identity of one external authentication assertion."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveAuthenticationValidationError(
                "authentication assertion id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveAuthenticationMethodCode:
    """Provider-neutral authentication method classification, never credential data."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_public_code(self.value, field_name="authentication method"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveAuthenticationContextCode:
    """Safe assurance/context classification supplied by the identity boundary."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_public_code(self.value, field_name="authentication context"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveIdentityBoundaryRef:
    """Opaque public reference to the external identity boundary that asserted identity."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_boundary_ref(self.value))

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class AuthenticatedExecutivePrincipal:
    """Secret-free assertion consumed by the QORE Executive Control Plane."""

    assertion_id: ExecutiveAuthenticationAssertionId
    principal_id: ExecutivePrincipalId
    method: ExecutiveAuthenticationMethodCode
    context: ExecutiveAuthenticationContextCode
    identity_boundary_ref: ExecutiveIdentityBoundaryRef
    issued_at: datetime
    expires_at: datetime
    correlation_id: CorrelationId

    def __post_init__(self) -> None:
        if not isinstance(self.assertion_id, ExecutiveAuthenticationAssertionId):
            raise ExecutiveAuthenticationValidationError(
                "authenticated principal requires ExecutiveAuthenticationAssertionId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveAuthenticationValidationError(
                "authenticated principal requires ExecutivePrincipalId"
            )
        if not isinstance(self.method, ExecutiveAuthenticationMethodCode):
            raise ExecutiveAuthenticationValidationError(
                "authenticated principal requires ExecutiveAuthenticationMethodCode"
            )
        if not isinstance(self.context, ExecutiveAuthenticationContextCode):
            raise ExecutiveAuthenticationValidationError(
                "authenticated principal requires ExecutiveAuthenticationContextCode"
            )
        if not isinstance(self.identity_boundary_ref, ExecutiveIdentityBoundaryRef):
            raise ExecutiveAuthenticationValidationError(
                "authenticated principal requires ExecutiveIdentityBoundaryRef"
            )
        _validate_timestamp(self.issued_at, field_name="issued_at")
        _validate_timestamp(self.expires_at, field_name="expires_at")
        if self.expires_at <= self.issued_at:
            raise ExecutiveAuthenticationValidationError(
                "authentication assertion expiry must be after issue time"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveAuthenticationValidationError(
                "authenticated principal requires CorrelationId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assertion_id.logical_values(),
            self.principal_id.logical_values(),
            self.method.logical_values(),
            self.context.logical_values(),
            self.identity_boundary_ref.logical_values(),
            self.issued_at.isoformat(),
            self.expires_at.isoformat(),
            str(self.correlation_id.value),
        )


def evaluate_authenticated_executive_principal(
    assertion: AuthenticatedExecutivePrincipal,
    *,
    evaluated_at: datetime,
) -> Result[AuthenticatedExecutivePrincipal, ExecutiveAuthenticationError]:
    """Validate assertion currency without consulting a clock or handling credentials."""

    if not isinstance(assertion, AuthenticatedExecutivePrincipal):
        return Failure(
            ExecutiveAuthenticationValidationError(
                "authentication evaluation requires AuthenticatedExecutivePrincipal"
            )
        )
    try:
        _validate_timestamp(evaluated_at, field_name="evaluated_at")
    except ExecutiveAuthenticationError as error:
        return Failure(error)
    if evaluated_at < assertion.issued_at:
        return Failure(
            ExecutiveAuthenticationBlockedError(
                "authentication assertion is not yet valid"
            )
        )
    if evaluated_at > assertion.expires_at:
        return Failure(
            ExecutiveAuthenticationBlockedError(
                "authentication assertion has expired"
            )
        )
    return Success(assertion)
