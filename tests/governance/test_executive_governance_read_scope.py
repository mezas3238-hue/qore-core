from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveAuthorizationBlockedError,
    ExecutiveControlAction,
    ExecutiveGrantId,
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
    authorize_executive_read_request,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 23, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION_ID = CorrelationId(UUID("30000000-0000-0000-0000-000000000001"))


def _grant(
    scopes: tuple[ExecutiveReadScope, ...],
) -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(
            UUID("30000000-0000-0000-0000-000000000002")
        ),
        principal_id=_PRINCIPAL,
        authority_version=ExecutiveAuthorityVersion("executive.v2"),
        allowed_actions=(),
        allowed_read_scopes=scopes,
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=15),
        reason="CEO authenticated governance read window",
    )


def _request() -> ExecutiveReadRequest:
    return ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(
            UUID("30000000-0000-0000-0000-000000000003")
        ),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.GOVERNANCE,
        requested_at=_NOW + timedelta(seconds=1),
        correlation_id=_CORRELATION_ID,
    )


def test_governance_is_an_explicit_read_scope_not_a_control_action() -> None:
    assert ExecutiveReadScope.GOVERNANCE.value == "governance"
    assert "governance" not in {item.value for item in ExecutiveControlAction}


def test_governance_read_requires_explicit_grant() -> None:
    result = authorize_executive_read_request(
        _request(),
        grant=_grant((ExecutiveReadScope.GOVERNANCE,)),
        evaluated_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.request.scope is ExecutiveReadScope.GOVERNANCE
    assert result.value.grant.allowed_read_scopes == (ExecutiveReadScope.GOVERNANCE,)


def test_governance_read_fails_closed_when_scope_is_not_granted() -> None:
    result = authorize_executive_read_request(
        _request(),
        grant=_grant((ExecutiveReadScope.AUDIT,)),
        evaluated_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutiveAuthorizationBlockedError)


def test_governance_scope_participates_in_deterministic_grant_ordering() -> None:
    grant = _grant(
        (
            ExecutiveReadScope.SYSTEM_HEALTH,
            ExecutiveReadScope.GOVERNANCE,
            ExecutiveReadScope.AUDIT,
        )
    )

    assert tuple(item.value for item in grant.allowed_read_scopes) == (
        "audit",
        "governance",
        "system-health",
    )
    assert grant.logical_values() == grant.logical_values()
