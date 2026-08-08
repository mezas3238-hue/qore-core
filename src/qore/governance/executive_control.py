from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveControlError(DomainError):
    """Base error for executive control-plane governance contracts."""

    __slots__ = ()


class ExecutiveControlValidationError(ExecutiveControlError):
    """An executive control-plane value violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveAuthorizationBlockedError(ExecutiveControlError):
    """Fail-closed result when executive authority does not permit a request."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveControlValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveControlValidationError(f"{field_name} must be timezone-aware")


def _validate_safe_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutiveControlValidationError(f"{field_name} must be non-empty")
    normalized = value.strip()
    lowered = normalized.lower()
    forbidden_fragments = (
        "password=",
        "secret=",
        "token=",
        "bearer ",
        "api_key=",
        "apikey=",
        "authorization:",
    )
    if any(fragment in lowered for fragment in forbidden_fragments):
        raise ExecutiveControlValidationError(
            f"{field_name} must not contain secret material"
        )
    return normalized


@dataclass(frozen=True, slots=True)
class ExecutivePrincipalId:
    """Opaque canonical identity for one executive control-plane principal."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]*", self.value
        ) is None:
            raise ExecutiveControlValidationError(
                "executive principal id must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveAuthorityVersion:
    """Explicit version of the authority policy evaluated by the Control Plane."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z0-9][a-z0-9._-]*", self.value
        ) is None:
            raise ExecutiveControlValidationError(
                "executive authority version must use canonical syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveGrantId:
    value: UUID

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveIntentId:
    value: UUID

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveReadRequestId:
    value: UUID

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class ExecutiveControlAction(StrEnum):
    """Closed allowlist of CEO governance actions; never a trading-order surface."""

    PAUSE_SYSTEM = "pause-system"
    RESUME_SYSTEM = "resume-system"
    HALT_NEW_TRADING = "halt-new-trading"
    RESTRICT_MARKET = "restrict-market"
    RESTRICT_ACCOUNT = "restrict-account"
    RESTORE_RESTRICTION = "restore-restriction"
    UPDATE_GOVERNANCE_POLICY = "update-governance-policy"
    ACKNOWLEDGE_INCIDENT = "acknowledge-incident"


class ExecutiveReadScope(StrEnum):
    """Read-model scopes exposed through governed executive query surfaces."""

    SYSTEM_HEALTH = "system-health"
    CIBO_STATE = "cibo-state"
    CAPITAL_STATE = "capital-state"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    MARKETS = "markets"
    TRADERS = "traders"
    VALIDATION_LAB = "validation-lab"
    TRADE_FORENSICS = "trade-forensics"
    AUDIT = "audit"
    CEO_ACCOUNTS = "ceo-accounts"
    CORPORATE_PROFIT_VAULT = "corporate-profit-vault"


@dataclass(frozen=True, slots=True)
class ExecutiveAuthorityGrant:
    """Explicit, expiring CEO authority for control actions and read scopes."""

    grant_id: ExecutiveGrantId
    principal_id: ExecutivePrincipalId
    authority_version: ExecutiveAuthorityVersion
    allowed_actions: tuple[ExecutiveControlAction, ...]
    allowed_read_scopes: tuple[ExecutiveReadScope, ...]
    issued_at: datetime
    expires_at: datetime
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.grant_id, ExecutiveGrantId):
            raise ExecutiveControlValidationError(
                "executive authority grant requires ExecutiveGrantId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveControlValidationError(
                "executive authority grant requires ExecutivePrincipalId"
            )
        if not isinstance(self.authority_version, ExecutiveAuthorityVersion):
            raise ExecutiveControlValidationError(
                "executive authority grant requires ExecutiveAuthorityVersion"
            )
        if not isinstance(self.allowed_actions, tuple) or any(
            not isinstance(item, ExecutiveControlAction) for item in self.allowed_actions
        ):
            raise ExecutiveControlValidationError(
                "executive allowed actions must be a tuple of ExecutiveControlAction"
            )
        if not isinstance(self.allowed_read_scopes, tuple) or any(
            not isinstance(item, ExecutiveReadScope)
            for item in self.allowed_read_scopes
        ):
            raise ExecutiveControlValidationError(
                "executive read scopes must be a tuple of ExecutiveReadScope"
            )
        if not self.allowed_actions and not self.allowed_read_scopes:
            raise ExecutiveControlValidationError(
                "executive authority grant must authorize at least one capability"
            )
        if len(set(self.allowed_actions)) != len(self.allowed_actions):
            raise ExecutiveControlValidationError(
                "executive allowed actions must not contain duplicates"
            )
        if len(set(self.allowed_read_scopes)) != len(self.allowed_read_scopes):
            raise ExecutiveControlValidationError(
                "executive read scopes must not contain duplicates"
            )
        object.__setattr__(
            self,
            "allowed_actions",
            tuple(sorted(self.allowed_actions, key=lambda item: item.value)),
        )
        object.__setattr__(
            self,
            "allowed_read_scopes",
            tuple(sorted(self.allowed_read_scopes, key=lambda item: item.value)),
        )
        _validate_aware_datetime(self.issued_at, field_name="issued_at")
        _validate_aware_datetime(self.expires_at, field_name="expires_at")
        if self.expires_at <= self.issued_at:
            raise ExecutiveControlValidationError(
                "executive authority expiry must be after issue time"
            )
        object.__setattr__(
            self,
            "reason",
            _validate_safe_text(self.reason, field_name="authority reason"),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.grant_id.logical_values(),
            self.principal_id.logical_values(),
            self.authority_version.logical_values(),
            tuple(item.value for item in self.allowed_actions),
            tuple(item.value for item in self.allowed_read_scopes),
            self.issued_at.isoformat(),
            self.expires_at.isoformat(),
            self.reason,
        )


@dataclass(frozen=True, slots=True)
class ExecutiveControlIntent:
    """One CEO governance request entering the Control Plane."""

    intent_id: ExecutiveIntentId
    principal_id: ExecutivePrincipalId
    action: ExecutiveControlAction
    requested_at: datetime
    correlation_id: CorrelationId
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.intent_id, ExecutiveIntentId):
            raise ExecutiveControlValidationError(
                "executive control intent requires ExecutiveIntentId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveControlValidationError(
                "executive control intent requires ExecutivePrincipalId"
            )
        if not isinstance(self.action, ExecutiveControlAction):
            raise ExecutiveControlValidationError(
                "executive control intent requires ExecutiveControlAction"
            )
        _validate_aware_datetime(self.requested_at, field_name="requested_at")
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveControlValidationError(
                "executive control intent requires CorrelationId"
            )
        object.__setattr__(
            self,
            "reason",
            _validate_safe_text(self.reason, field_name="control intent reason"),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.intent_id.logical_values(),
            self.principal_id.logical_values(),
            self.action.value,
            self.requested_at.isoformat(),
            str(self.correlation_id.value),
            self.reason,
        )


@dataclass(frozen=True, slots=True)
class AuthorizedExecutiveControlIntent:
    """Control intent paired with the exact authority grant that allowed it."""

    intent: ExecutiveControlIntent
    grant: ExecutiveAuthorityGrant
    authorized_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.intent, ExecutiveControlIntent):
            raise ExecutiveControlValidationError(
                "authorized control intent requires ExecutiveControlIntent"
            )
        if not isinstance(self.grant, ExecutiveAuthorityGrant):
            raise ExecutiveControlValidationError(
                "authorized control intent requires ExecutiveAuthorityGrant"
            )
        _validate_aware_datetime(self.authorized_at, field_name="authorized_at")
        if self.intent.principal_id != self.grant.principal_id:
            raise ExecutiveControlValidationError(
                "authorized control principal must match authority grant"
            )
        if self.intent.action not in self.grant.allowed_actions:
            raise ExecutiveControlValidationError(
                "authorized control action must be present in authority grant"
            )
        if self.intent.requested_at < self.grant.issued_at:
            raise ExecutiveControlValidationError(
                "control intent must not predate authority grant"
            )
        if self.authorized_at < self.intent.requested_at:
            raise ExecutiveControlValidationError(
                "control authorization must not predate intent"
            )
        if self.authorized_at > self.grant.expires_at:
            raise ExecutiveControlValidationError(
                "control authorization must not outlive authority grant"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.intent.logical_values(),
            self.grant.logical_values(),
            self.authorized_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveReadRequest:
    """One read-only executive query request; never an execution command."""

    request_id: ExecutiveReadRequestId
    principal_id: ExecutivePrincipalId
    scope: ExecutiveReadScope
    requested_at: datetime
    correlation_id: CorrelationId

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, ExecutiveReadRequestId):
            raise ExecutiveControlValidationError(
                "executive read request requires ExecutiveReadRequestId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveControlValidationError(
                "executive read request requires ExecutivePrincipalId"
            )
        if not isinstance(self.scope, ExecutiveReadScope):
            raise ExecutiveControlValidationError(
                "executive read request requires ExecutiveReadScope"
            )
        _validate_aware_datetime(self.requested_at, field_name="requested_at")
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveControlValidationError(
                "executive read request requires CorrelationId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_id.logical_values(),
            self.principal_id.logical_values(),
            self.scope.value,
            self.requested_at.isoformat(),
            str(self.correlation_id.value),
        )


@dataclass(frozen=True, slots=True)
class AuthorizedExecutiveReadRequest:
    """Read request paired with the exact authority grant that allowed it."""

    request: ExecutiveReadRequest
    grant: ExecutiveAuthorityGrant
    authorized_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request, ExecutiveReadRequest):
            raise ExecutiveControlValidationError(
                "authorized read requires ExecutiveReadRequest"
            )
        if not isinstance(self.grant, ExecutiveAuthorityGrant):
            raise ExecutiveControlValidationError(
                "authorized read requires ExecutiveAuthorityGrant"
            )
        _validate_aware_datetime(self.authorized_at, field_name="authorized_at")
        if self.request.principal_id != self.grant.principal_id:
            raise ExecutiveControlValidationError(
                "authorized read principal must match authority grant"
            )
        if self.request.scope not in self.grant.allowed_read_scopes:
            raise ExecutiveControlValidationError(
                "authorized read scope must be present in authority grant"
            )
        if self.request.requested_at < self.grant.issued_at:
            raise ExecutiveControlValidationError(
                "read request must not predate authority grant"
            )
        if self.authorized_at < self.request.requested_at:
            raise ExecutiveControlValidationError(
                "read authorization must not predate request"
            )
        if self.authorized_at > self.grant.expires_at:
            raise ExecutiveControlValidationError(
                "read authorization must not outlive authority grant"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request.logical_values(),
            self.grant.logical_values(),
            self.authorized_at.isoformat(),
        )


def authorize_executive_control_intent(
    intent: ExecutiveControlIntent,
    *,
    grant: ExecutiveAuthorityGrant,
    evaluated_at: datetime,
) -> Result[AuthorizedExecutiveControlIntent, ExecutiveControlError]:
    """Authorize one governance intent or fail closed without dispatching anything."""

    if not isinstance(intent, ExecutiveControlIntent):
        return Failure(
            ExecutiveControlValidationError(
                "executive control authorization requires ExecutiveControlIntent"
            )
        )
    if not isinstance(grant, ExecutiveAuthorityGrant):
        return Failure(
            ExecutiveControlValidationError(
                "executive control authorization requires ExecutiveAuthorityGrant"
            )
        )
    try:
        _validate_aware_datetime(evaluated_at, field_name="evaluated_at")
    except ExecutiveControlError as error:
        return Failure(error)
    if intent.principal_id != grant.principal_id:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive principal does not match authority grant"
            )
        )
    if intent.action not in grant.allowed_actions:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive action is not allowed by authority grant"
            )
        )
    if intent.requested_at < grant.issued_at:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive intent predates authority grant"
            )
        )
    if evaluated_at < intent.requested_at:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive authorization cannot predate intent"
            )
        )
    if evaluated_at > grant.expires_at:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive authority grant has expired"
            )
        )
    try:
        return Success(
            AuthorizedExecutiveControlIntent(
                intent=intent,
                grant=grant,
                authorized_at=evaluated_at,
            )
        )
    except ExecutiveControlError as error:
        return Failure(error)


def authorize_executive_read_request(
    request: ExecutiveReadRequest,
    *,
    grant: ExecutiveAuthorityGrant,
    evaluated_at: datetime,
) -> Result[AuthorizedExecutiveReadRequest, ExecutiveControlError]:
    """Authorize one executive read request or fail closed without data access."""

    if not isinstance(request, ExecutiveReadRequest):
        return Failure(
            ExecutiveControlValidationError(
                "executive read authorization requires ExecutiveReadRequest"
            )
        )
    if not isinstance(grant, ExecutiveAuthorityGrant):
        return Failure(
            ExecutiveControlValidationError(
                "executive read authorization requires ExecutiveAuthorityGrant"
            )
        )
    try:
        _validate_aware_datetime(evaluated_at, field_name="evaluated_at")
    except ExecutiveControlError as error:
        return Failure(error)
    if request.principal_id != grant.principal_id:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive principal does not match authority grant"
            )
        )
    if request.scope not in grant.allowed_read_scopes:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive read scope is not allowed by authority grant"
            )
        )
    if request.requested_at < grant.issued_at:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive read request predates authority grant"
            )
        )
    if evaluated_at < request.requested_at:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive read authorization cannot predate request"
            )
        )
    if evaluated_at > grant.expires_at:
        return Failure(
            ExecutiveAuthorizationBlockedError(
                "executive authority grant has expired"
            )
        )
    try:
        return Success(
            AuthorizedExecutiveReadRequest(
                request=request,
                grant=grant,
                authorized_at=evaluated_at,
            )
        )
    except ExecutiveControlError as error:
        return Failure(error)
