from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_authentication import (
    AuthenticatedExecutivePrincipal,
    ExecutiveAuthenticationAssertionId,
    ExecutiveAuthenticationContextCode,
    ExecutiveAuthenticationMethodCode,
    ExecutiveIdentityBoundaryRef,
)
from qore.governance.executive_authority_state import (
    ExecutiveAuthorityStateError,
    ExecutiveAuthorityStateEvidenceRef,
    ExecutiveAuthorityStateRequest,
    ExecutiveAuthorityStateRequestId,
    ExecutiveAuthorityStateSnapshot,
    ExecutiveAuthorityStateStatus,
    ExecutiveAuthorityStateUnavailableError,
)
from qore.governance.executive_control import (
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveGrantId,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
)
from qore.governance.executive_request_guard import (
    ExecutiveRequestGuard,
    ExecutiveRequestGuardBlockedError,
    ExecutiveRequestGuardReason,
    ExecutiveRequestGuardStage,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 2, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("43000000-0000-0000-0000-000000000001"))
_AUTHORITY_REQUEST_ID = ExecutiveAuthorityStateRequestId(
    UUID("43000000-0000-0000-0000-000000000002")
)


def _grant(
    *,
    actions: tuple[ExecutiveControlAction, ...] = (ExecutiveControlAction.PAUSE_SYSTEM,),
    scopes: tuple[ExecutiveReadScope, ...] = (ExecutiveReadScope.GOVERNANCE,),
) -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("43000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("authority.v1"),
        allowed_actions=actions,
        allowed_read_scopes=scopes,
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=10),
        reason="mission04 request guard",
    )


def _assertion(
    *,
    principal_id: ExecutivePrincipalId = _PRINCIPAL,
    correlation_id: CorrelationId = _CORRELATION,
    expires_at: datetime | None = None,
) -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("43000000-0000-0000-0000-000000000004")
        ),
        principal_id=principal_id,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:primary"),
        issued_at=_NOW,
        expires_at=expires_at or _NOW + timedelta(minutes=10),
        correlation_id=correlation_id,
    )


def _control_intent(
    *,
    action: ExecutiveControlAction = ExecutiveControlAction.PAUSE_SYSTEM,
    correlation_id: CorrelationId = _CORRELATION,
) -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("43000000-0000-0000-0000-000000000005")),
        principal_id=_PRINCIPAL,
        action=action,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=correlation_id,
        reason="CEO governance control",
    )


def _read_request() -> ExecutiveReadRequest:
    return ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(
            UUID("43000000-0000-0000-0000-000000000006")
        ),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.GOVERNANCE,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
    )


def _authority_request(
    *,
    principal_id: ExecutivePrincipalId = _PRINCIPAL,
    correlation_id: CorrelationId = _CORRELATION,
) -> ExecutiveAuthorityStateRequest:
    return ExecutiveAuthorityStateRequest(
        request_id=_AUTHORITY_REQUEST_ID,
        principal_id=principal_id,
        requested_at=_NOW + timedelta(minutes=2),
        correlation_id=correlation_id,
    )


def _snapshot(
    *,
    status: ExecutiveAuthorityStateStatus = ExecutiveAuthorityStateStatus.ACTIVE,
    request_id: ExecutiveAuthorityStateRequestId = _AUTHORITY_REQUEST_ID,
    grant: ExecutiveAuthorityGrant | None = None,
) -> ExecutiveAuthorityStateSnapshot:
    selected_grant = grant if grant is not None else _grant()
    return ExecutiveAuthorityStateSnapshot(
        request_id=request_id,
        principal_id=_PRINCIPAL,
        status=status,
        observed_at=_NOW + timedelta(minutes=2, seconds=1),
        evidence_ref=ExecutiveAuthorityStateEvidenceRef("authority:state/current"),
        grant=(None if status is ExecutiveAuthorityStateStatus.UNKNOWN else selected_grant),
        invalidated_at=(
            _NOW + timedelta(minutes=2)
            if status
            in {
                ExecutiveAuthorityStateStatus.REVOKED,
                ExecutiveAuthorityStateStatus.SUPERSEDED,
            }
            else None
        ),
        superseding_version=(
            ExecutiveAuthorityVersion("authority.v2")
            if status is ExecutiveAuthorityStateStatus.SUPERSEDED
            else None
        ),
    )


class _FakeAuthoritySource:
    def __init__(
        self,
        *,
        snapshot: ExecutiveAuthorityStateSnapshot | None = None,
        error: ExecutiveAuthorityStateError | None = None,
    ) -> None:
        self.snapshot = snapshot
        self.error = error
        self.requests: list[ExecutiveAuthorityStateRequest] = []

    def read_current(
        self,
        request: ExecutiveAuthorityStateRequest,
    ) -> Result[ExecutiveAuthorityStateSnapshot, ExecutiveAuthorityStateError]:
        self.requests.append(request)
        if self.error is not None:
            return Failure(self.error)
        if self.snapshot is None:
            return Failure(ExecutiveAuthorityStateUnavailableError("state unavailable"))
        return Success(self.snapshot)


def _blocked_reason(result: object) -> tuple[ExecutiveRequestGuardStage, ExecutiveRequestGuardReason]:
    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveRequestGuardBlockedError)
    return result.error.stage, result.error.reason


def test_valid_control_composes_authentication_current_authority_and_existing_authorizer() -> None:
    source = _FakeAuthoritySource(snapshot=_snapshot())
    guard = ExecutiveRequestGuard(source)

    result = guard.authorize_control(
        _assertion(),
        _control_intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assert result.value.intent == _control_intent()
    assert result.value.grant == _grant()
    assert len(source.requests) == 1


def test_valid_read_uses_same_guard_and_existing_read_authorizer() -> None:
    source = _FakeAuthoritySource(snapshot=_snapshot())
    guard = ExecutiveRequestGuard(source)

    result = guard.authorize_read(
        _assertion(),
        _read_request(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assert result.value.request == _read_request()
    assert result.value.grant == _grant()
    assert len(source.requests) == 1


def test_expired_authentication_blocks_before_authority_source() -> None:
    source = _FakeAuthoritySource(snapshot=_snapshot())
    guard = ExecutiveRequestGuard(source)
    assertion = _assertion(expires_at=_NOW + timedelta(minutes=2))

    result = guard.authorize_control(
        assertion,
        _control_intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert _blocked_reason(result) == (
        ExecutiveRequestGuardStage.AUTHENTICATION,
        ExecutiveRequestGuardReason.AUTHENTICATION_INVALID,
    )
    assert source.requests == []


def test_principal_and_correlation_mismatch_block_before_authority_source() -> None:
    source = _FakeAuthoritySource(snapshot=_snapshot())
    guard = ExecutiveRequestGuard(source)

    principal_result = guard.authorize_control(
        _assertion(principal_id=ExecutivePrincipalId("ceo.other")),
        _control_intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=3),
    )
    correlation_result = guard.authorize_control(
        _assertion(),
        _control_intent(
            correlation_id=CorrelationId(
                UUID("43000000-0000-0000-0000-000000000009")
            )
        ),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert _blocked_reason(principal_result)[1] is ExecutiveRequestGuardReason.PRINCIPAL_MISMATCH
    assert _blocked_reason(correlation_result)[1] is ExecutiveRequestGuardReason.CORRELATION_MISMATCH
    assert source.requests == []


def test_non_active_or_unavailable_authority_fails_closed_without_authorization() -> None:
    revoked_source = _FakeAuthoritySource(
        snapshot=_snapshot(status=ExecutiveAuthorityStateStatus.REVOKED)
    )
    unavailable_source = _FakeAuthoritySource(
        error=ExecutiveAuthorityStateUnavailableError("database password=private")
    )

    revoked = ExecutiveRequestGuard(revoked_source).authorize_control(
        _assertion(),
        _control_intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=3),
    )
    unavailable = ExecutiveRequestGuard(unavailable_source).authorize_control(
        _assertion(),
        _control_intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert _blocked_reason(revoked) == (
        ExecutiveRequestGuardStage.AUTHORITY,
        ExecutiveRequestGuardReason.AUTHORITY_NOT_ACTIVE,
    )
    assert _blocked_reason(unavailable) == (
        ExecutiveRequestGuardStage.AUTHORITY,
        ExecutiveRequestGuardReason.AUTHORITY_SOURCE_FAILED,
    )
    assert "password" not in str(unavailable.error).lower()


def test_mismatched_authority_response_is_rejected() -> None:
    other_request_id = ExecutiveAuthorityStateRequestId(
        UUID("43000000-0000-0000-0000-000000000010")
    )
    source = _FakeAuthoritySource(snapshot=_snapshot(request_id=other_request_id))

    result = ExecutiveRequestGuard(source).authorize_control(
        _assertion(),
        _control_intent(),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert _blocked_reason(result) == (
        ExecutiveRequestGuardStage.AUTHORITY,
        ExecutiveRequestGuardReason.AUTHORITY_RESPONSE_MISMATCH,
    )


def test_existing_authorizer_denial_is_preserved_as_sanitized_guard_failure() -> None:
    source = _FakeAuthoritySource(snapshot=_snapshot())

    result = ExecutiveRequestGuard(source).authorize_control(
        _assertion(),
        _control_intent(action=ExecutiveControlAction.RESUME_SYSTEM),
        authority_request=_authority_request(),
        evaluated_at=_NOW + timedelta(minutes=3),
    )

    assert _blocked_reason(result) == (
        ExecutiveRequestGuardStage.AUTHORIZATION,
        ExecutiveRequestGuardReason.AUTHORIZATION_DENIED,
    )
