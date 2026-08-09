from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_authority_state import (
    ExecutiveAuthorityStateEvidenceRef,
    ExecutiveAuthorityStateRequest,
    ExecutiveAuthorityStateRequestId,
    ExecutiveAuthorityStateSnapshot,
    ExecutiveAuthorityStateSource,
    ExecutiveAuthorityStateStatus,
    ExecutiveAuthorityStateValidationError,
)
from qore.governance.executive_control import (
    ExecutiveAuthorityGrant,
    ExecutiveAuthorityVersion,
    ExecutiveControlAction,
    ExecutiveGrantId,
    ExecutivePrincipalId,
    ExecutiveReadScope,
)
from qore.kernel.result import Result, Success

_NOW = datetime(2026, 8, 9, 1, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_REQUEST_ID = ExecutiveAuthorityStateRequestId(
    UUID("42000000-0000-0000-0000-000000000001")
)


def _grant(
    *,
    principal_id: ExecutivePrincipalId = _PRINCIPAL,
    version: str = "authority.v1",
) -> ExecutiveAuthorityGrant:
    return ExecutiveAuthorityGrant(
        grant_id=ExecutiveGrantId(UUID("42000000-0000-0000-0000-000000000002")),
        principal_id=principal_id,
        authority_version=ExecutiveAuthorityVersion(version),
        allowed_actions=(ExecutiveControlAction.PAUSE_SYSTEM,),
        allowed_read_scopes=(ExecutiveReadScope.GOVERNANCE,),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=10),
        reason="mission04 executive authority",
    )


def _request() -> ExecutiveAuthorityStateRequest:
    return ExecutiveAuthorityStateRequest(
        request_id=_REQUEST_ID,
        principal_id=_PRINCIPAL,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=CorrelationId(
            UUID("42000000-0000-0000-0000-000000000003")
        ),
    )


def _snapshot(
    status: ExecutiveAuthorityStateStatus,
    *,
    grant: ExecutiveAuthorityGrant | None = None,
    observed_at: datetime | None = None,
    invalidated_at: datetime | None = None,
    superseding_version: ExecutiveAuthorityVersion | None = None,
) -> ExecutiveAuthorityStateSnapshot:
    return ExecutiveAuthorityStateSnapshot(
        request_id=_REQUEST_ID,
        principal_id=_PRINCIPAL,
        status=status,
        observed_at=observed_at or _NOW + timedelta(minutes=2),
        evidence_ref=ExecutiveAuthorityStateEvidenceRef("authority:state/current"),
        grant=grant,
        invalidated_at=invalidated_at,
        superseding_version=superseding_version,
    )


def test_active_state_exposes_only_exact_active_grant() -> None:
    grant = _grant()
    snapshot = _snapshot(ExecutiveAuthorityStateStatus.ACTIVE, grant=grant)

    assert snapshot.is_active is True
    assert snapshot.active_grant is grant
    assert snapshot.logical_values() == snapshot.logical_values()
    assert "token" not in repr(snapshot.logical_values()).lower()


def test_unknown_state_is_explicitly_non_authorizing_and_carries_no_grant() -> None:
    snapshot = _snapshot(ExecutiveAuthorityStateStatus.UNKNOWN)

    assert snapshot.is_active is False
    assert snapshot.active_grant is None

    with pytest.raises(ExecutiveAuthorityStateValidationError):
        _snapshot(ExecutiveAuthorityStateStatus.UNKNOWN, grant=_grant())


def test_revoked_state_requires_explicit_invalidation_and_never_returns_active_grant() -> None:
    grant = _grant()
    invalidated_at = _NOW + timedelta(minutes=1)
    revoked = _snapshot(
        ExecutiveAuthorityStateStatus.REVOKED,
        grant=grant,
        invalidated_at=invalidated_at,
    )

    assert revoked.active_grant is None
    assert revoked.invalidated_at == invalidated_at

    with pytest.raises(ExecutiveAuthorityStateValidationError):
        _snapshot(ExecutiveAuthorityStateStatus.REVOKED, grant=grant)


def test_superseded_state_requires_a_different_successor_version() -> None:
    grant = _grant()
    invalidated_at = _NOW + timedelta(minutes=1)
    superseded = _snapshot(
        ExecutiveAuthorityStateStatus.SUPERSEDED,
        grant=grant,
        invalidated_at=invalidated_at,
        superseding_version=ExecutiveAuthorityVersion("authority.v2"),
    )

    assert superseded.active_grant is None
    assert superseded.superseding_version == ExecutiveAuthorityVersion("authority.v2")

    with pytest.raises(ExecutiveAuthorityStateValidationError):
        _snapshot(
            ExecutiveAuthorityStateStatus.SUPERSEDED,
            grant=grant,
            invalidated_at=invalidated_at,
            superseding_version=grant.authority_version,
        )


def test_expired_and_active_states_are_bound_to_grant_time_window() -> None:
    grant = _grant()

    with pytest.raises(ExecutiveAuthorityStateValidationError):
        _snapshot(
            ExecutiveAuthorityStateStatus.ACTIVE,
            grant=grant,
            observed_at=grant.expires_at + timedelta(microseconds=1),
        )

    expired = _snapshot(
        ExecutiveAuthorityStateStatus.EXPIRED,
        grant=grant,
        observed_at=grant.expires_at + timedelta(microseconds=1),
    )
    assert expired.active_grant is None

    with pytest.raises(ExecutiveAuthorityStateValidationError):
        _snapshot(
            ExecutiveAuthorityStateStatus.EXPIRED,
            grant=grant,
            observed_at=grant.expires_at,
        )


def test_state_rejects_principal_mismatch_future_invalidation_and_secret_refs() -> None:
    other_grant = _grant(principal_id=ExecutivePrincipalId("ceo.other"))

    with pytest.raises(ExecutiveAuthorityStateValidationError):
        _snapshot(ExecutiveAuthorityStateStatus.ACTIVE, grant=other_grant)

    with pytest.raises(ExecutiveAuthorityStateValidationError):
        _snapshot(
            ExecutiveAuthorityStateStatus.REVOKED,
            grant=_grant(),
            invalidated_at=_NOW + timedelta(minutes=3),
            observed_at=_NOW + timedelta(minutes=2),
        )

    with pytest.raises(ExecutiveAuthorityStateValidationError):
        ExecutiveAuthorityStateEvidenceRef("authority:token/secret")


def test_request_requires_explicit_aware_time_and_correlation() -> None:
    request = _request()
    assert request.logical_values() == request.logical_values()

    with pytest.raises(ExecutiveAuthorityStateValidationError):
        ExecutiveAuthorityStateRequest(
            request_id=_REQUEST_ID,
            principal_id=_PRINCIPAL,
            requested_at=datetime(2026, 8, 9, 1, 0),
            correlation_id=request.correlation_id,
        )


class _FakeAuthorityStateSource:
    def __init__(self, snapshot: ExecutiveAuthorityStateSnapshot) -> None:
        self.snapshot = snapshot
        self.requests: list[ExecutiveAuthorityStateRequest] = []

    def read_current(
        self,
        request: ExecutiveAuthorityStateRequest,
    ) -> Result[ExecutiveAuthorityStateSnapshot, object]:
        self.requests.append(request)
        return Success(self.snapshot)


def _accept_source(source: ExecutiveAuthorityStateSource) -> ExecutiveAuthorityStateSource:
    return source


def test_source_boundary_is_structural_and_request_driven() -> None:
    snapshot = _snapshot(ExecutiveAuthorityStateStatus.ACTIVE, grant=_grant())
    source = _FakeAuthorityStateSource(snapshot)

    boundary = _accept_source(source)
    result = boundary.read_current(_request())

    assert isinstance(result, Success)
    assert result.value is snapshot
    assert len(source.requests) == 1
