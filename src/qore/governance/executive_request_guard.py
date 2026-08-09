from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from qore.governance.executive_authentication import (
    AuthenticatedExecutivePrincipal,
    evaluate_authenticated_executive_principal,
)
from qore.governance.executive_authority_state import (
    ExecutiveAuthorityStateRequest,
    ExecutiveAuthorityStateSnapshot,
    ExecutiveAuthorityStateSource,
)
from qore.governance.executive_control import (
    AuthorizedExecutiveControlIntent,
    AuthorizedExecutiveReadRequest,
    ExecutiveControlIntent,
    ExecutiveReadRequest,
    authorize_executive_control_intent,
    authorize_executive_read_request,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveRequestGuardError(DomainError):
    """Base error for MISSION-04 unified executive request guarding."""

    __slots__ = ()


class ExecutiveRequestGuardValidationError(ExecutiveRequestGuardError):
    """The request-guard invocation violates a typed input invariant."""

    __slots__ = ()


class ExecutiveRequestGuardStage(StrEnum):
    AUTHENTICATION = "authentication"
    AUTHORITY = "authority"
    AUTHORIZATION = "authorization"


class ExecutiveRequestGuardReason(StrEnum):
    AUTHENTICATION_INVALID = "authentication-invalid"
    PRINCIPAL_MISMATCH = "principal-mismatch"
    CORRELATION_MISMATCH = "correlation-mismatch"
    AUTHORITY_REQUEST_INVALID = "authority-request-invalid"
    AUTHORITY_SOURCE_FAILED = "authority-source-failed"
    AUTHORITY_RESPONSE_MISMATCH = "authority-response-mismatch"
    AUTHORITY_NOT_ACTIVE = "authority-not-active"
    AUTHORIZATION_DENIED = "authorization-denied"


class ExecutiveRequestGuardBlockedError(ExecutiveRequestGuardError):
    """Sanitized fail-closed denial without leaking upstream exception text."""

    __slots__ = ("reason", "stage")

    def __init__(
        self,
        stage: ExecutiveRequestGuardStage,
        reason: ExecutiveRequestGuardReason,
    ) -> None:
        if not isinstance(stage, ExecutiveRequestGuardStage):
            raise ExecutiveRequestGuardValidationError(
                "request guard blocked error requires ExecutiveRequestGuardStage"
            )
        if not isinstance(reason, ExecutiveRequestGuardReason):
            raise ExecutiveRequestGuardValidationError(
                "request guard blocked error requires ExecutiveRequestGuardReason"
            )
        self.stage = stage
        self.reason = reason
        super().__init__(f"{stage.value}.{reason.value}")

    def logical_values(self) -> tuple[str, str]:
        return (self.stage.value, self.reason.value)


def _blocked(
    stage: ExecutiveRequestGuardStage,
    reason: ExecutiveRequestGuardReason,
) -> Failure[ExecutiveRequestGuardError]:
    return Failure(ExecutiveRequestGuardBlockedError(stage, reason))


def _validate_evaluated_at(value: datetime) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveRequestGuardValidationError(
            "request guard evaluated_at must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveRequestGuardValidationError(
            "request guard evaluated_at must be timezone-aware"
        )


def _validate_common_request_binding(
    *,
    assertion: AuthenticatedExecutivePrincipal,
    principal_id: object,
    correlation_id: object,
    requested_at: datetime,
    authority_request: ExecutiveAuthorityStateRequest,
    evaluated_at: datetime,
) -> ExecutiveRequestGuardBlockedError | None:
    if assertion.principal_id != principal_id:
        return ExecutiveRequestGuardBlockedError(
            ExecutiveRequestGuardStage.AUTHENTICATION,
            ExecutiveRequestGuardReason.PRINCIPAL_MISMATCH,
        )
    if assertion.correlation_id != correlation_id:
        return ExecutiveRequestGuardBlockedError(
            ExecutiveRequestGuardStage.AUTHENTICATION,
            ExecutiveRequestGuardReason.CORRELATION_MISMATCH,
        )
    if requested_at < assertion.issued_at:
        return ExecutiveRequestGuardBlockedError(
            ExecutiveRequestGuardStage.AUTHENTICATION,
            ExecutiveRequestGuardReason.AUTHENTICATION_INVALID,
        )
    if authority_request.principal_id != assertion.principal_id:
        return ExecutiveRequestGuardBlockedError(
            ExecutiveRequestGuardStage.AUTHORITY,
            ExecutiveRequestGuardReason.AUTHORITY_REQUEST_INVALID,
        )
    if authority_request.correlation_id != assertion.correlation_id:
        return ExecutiveRequestGuardBlockedError(
            ExecutiveRequestGuardStage.AUTHORITY,
            ExecutiveRequestGuardReason.CORRELATION_MISMATCH,
        )
    if authority_request.requested_at < requested_at:
        return ExecutiveRequestGuardBlockedError(
            ExecutiveRequestGuardStage.AUTHORITY,
            ExecutiveRequestGuardReason.AUTHORITY_REQUEST_INVALID,
        )
    if authority_request.requested_at > evaluated_at:
        return ExecutiveRequestGuardBlockedError(
            ExecutiveRequestGuardStage.AUTHORITY,
            ExecutiveRequestGuardReason.AUTHORITY_REQUEST_INVALID,
        )
    return None


def _read_active_authority(
    *,
    source: ExecutiveAuthorityStateSource,
    request: ExecutiveAuthorityStateRequest,
    evaluated_at: datetime,
) -> Result[ExecutiveAuthorityStateSnapshot, ExecutiveRequestGuardError]:
    result = source.read_current(request)
    if isinstance(result, Failure):
        return _blocked(
            ExecutiveRequestGuardStage.AUTHORITY,
            ExecutiveRequestGuardReason.AUTHORITY_SOURCE_FAILED,
        )
    snapshot = result.value
    if not isinstance(snapshot, ExecutiveAuthorityStateSnapshot):
        return _blocked(
            ExecutiveRequestGuardStage.AUTHORITY,
            ExecutiveRequestGuardReason.AUTHORITY_RESPONSE_MISMATCH,
        )
    if (
        snapshot.request_id != request.request_id
        or snapshot.principal_id != request.principal_id
        or snapshot.observed_at < request.requested_at
        or snapshot.observed_at > evaluated_at
    ):
        return _blocked(
            ExecutiveRequestGuardStage.AUTHORITY,
            ExecutiveRequestGuardReason.AUTHORITY_RESPONSE_MISMATCH,
        )
    if not snapshot.is_active or snapshot.active_grant is None:
        return _blocked(
            ExecutiveRequestGuardStage.AUTHORITY,
            ExecutiveRequestGuardReason.AUTHORITY_NOT_ACTIVE,
        )
    return Success(snapshot)


class ExecutiveRequestGuard:
    """Compose authentication, current authority and existing authorization rules."""

    __slots__ = ("_authority_source",)

    def __init__(self, authority_source: ExecutiveAuthorityStateSource) -> None:
        if not callable(getattr(authority_source, "read_current", None)):
            raise ExecutiveRequestGuardValidationError(
                "request guard requires ExecutiveAuthorityStateSource"
            )
        self._authority_source = authority_source

    def authorize_control(
        self,
        assertion: AuthenticatedExecutivePrincipal,
        intent: ExecutiveControlIntent,
        *,
        authority_request: ExecutiveAuthorityStateRequest,
        evaluated_at: datetime,
    ) -> Result[AuthorizedExecutiveControlIntent, ExecutiveRequestGuardError]:
        if not isinstance(assertion, AuthenticatedExecutivePrincipal):
            return Failure(
                ExecutiveRequestGuardValidationError(
                    "control guard requires AuthenticatedExecutivePrincipal"
                )
            )
        if not isinstance(intent, ExecutiveControlIntent):
            return Failure(
                ExecutiveRequestGuardValidationError(
                    "control guard requires ExecutiveControlIntent"
                )
            )
        if not isinstance(authority_request, ExecutiveAuthorityStateRequest):
            return Failure(
                ExecutiveRequestGuardValidationError(
                    "control guard requires ExecutiveAuthorityStateRequest"
                )
            )
        try:
            _validate_evaluated_at(evaluated_at)
        except ExecutiveRequestGuardError as error:
            return Failure(error)

        authenticated = evaluate_authenticated_executive_principal(
            assertion,
            evaluated_at=evaluated_at,
        )
        if isinstance(authenticated, Failure):
            return _blocked(
                ExecutiveRequestGuardStage.AUTHENTICATION,
                ExecutiveRequestGuardReason.AUTHENTICATION_INVALID,
            )
        binding_error = _validate_common_request_binding(
            assertion=assertion,
            principal_id=intent.principal_id,
            correlation_id=intent.correlation_id,
            requested_at=intent.requested_at,
            authority_request=authority_request,
            evaluated_at=evaluated_at,
        )
        if binding_error is not None:
            return Failure(binding_error)

        state = _read_active_authority(
            source=self._authority_source,
            request=authority_request,
            evaluated_at=evaluated_at,
        )
        if isinstance(state, Failure):
            return state
        grant = state.value.active_grant
        if grant is None:
            return _blocked(
                ExecutiveRequestGuardStage.AUTHORITY,
                ExecutiveRequestGuardReason.AUTHORITY_NOT_ACTIVE,
            )
        authorized = authorize_executive_control_intent(
            intent,
            grant=grant,
            evaluated_at=evaluated_at,
        )
        if isinstance(authorized, Failure):
            return _blocked(
                ExecutiveRequestGuardStage.AUTHORIZATION,
                ExecutiveRequestGuardReason.AUTHORIZATION_DENIED,
            )
        return Success(authorized.value)

    def authorize_read(
        self,
        assertion: AuthenticatedExecutivePrincipal,
        request: ExecutiveReadRequest,
        *,
        authority_request: ExecutiveAuthorityStateRequest,
        evaluated_at: datetime,
    ) -> Result[AuthorizedExecutiveReadRequest, ExecutiveRequestGuardError]:
        if not isinstance(assertion, AuthenticatedExecutivePrincipal):
            return Failure(
                ExecutiveRequestGuardValidationError(
                    "read guard requires AuthenticatedExecutivePrincipal"
                )
            )
        if not isinstance(request, ExecutiveReadRequest):
            return Failure(
                ExecutiveRequestGuardValidationError(
                    "read guard requires ExecutiveReadRequest"
                )
            )
        if not isinstance(authority_request, ExecutiveAuthorityStateRequest):
            return Failure(
                ExecutiveRequestGuardValidationError(
                    "read guard requires ExecutiveAuthorityStateRequest"
                )
            )
        try:
            _validate_evaluated_at(evaluated_at)
        except ExecutiveRequestGuardError as error:
            return Failure(error)

        authenticated = evaluate_authenticated_executive_principal(
            assertion,
            evaluated_at=evaluated_at,
        )
        if isinstance(authenticated, Failure):
            return _blocked(
                ExecutiveRequestGuardStage.AUTHENTICATION,
                ExecutiveRequestGuardReason.AUTHENTICATION_INVALID,
            )
        binding_error = _validate_common_request_binding(
            assertion=assertion,
            principal_id=request.principal_id,
            correlation_id=request.correlation_id,
            requested_at=request.requested_at,
            authority_request=authority_request,
            evaluated_at=evaluated_at,
        )
        if binding_error is not None:
            return Failure(binding_error)

        state = _read_active_authority(
            source=self._authority_source,
            request=authority_request,
            evaluated_at=evaluated_at,
        )
        if isinstance(state, Failure):
            return state
        grant = state.value.active_grant
        if grant is None:
            return _blocked(
                ExecutiveRequestGuardStage.AUTHORITY,
                ExecutiveRequestGuardReason.AUTHORITY_NOT_ACTIVE,
            )
        authorized = authorize_executive_read_request(
            request,
            grant=grant,
            evaluated_at=evaluated_at,
        )
        if isinstance(authorized, Failure):
            return _blocked(
                ExecutiveRequestGuardStage.AUTHORIZATION,
                ExecutiveRequestGuardReason.AUTHORIZATION_DENIED,
            )
        return Success(authorized.value)
