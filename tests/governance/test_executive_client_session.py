from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_authentication import (
    AuthenticatedExecutivePrincipal,
    ExecutiveAuthenticationAssertionId,
    ExecutiveAuthenticationContextCode,
    ExecutiveAuthenticationMethodCode,
    ExecutiveIdentityBoundaryRef,
)
from qore.governance.executive_client_session import (
    ExecutiveClientDeviceRef,
    ExecutiveClientSession,
    ExecutiveClientSessionId,
    ExecutiveClientSessionStatus,
    ExecutiveClientSessionValidationError,
    bind_executive_client_session,
    build_executive_client_session,
)
from qore.governance.executive_client_surface import (
    ExecutiveClientPlatform,
    ExecutiveClientSurface,
    ExecutiveClientSurfaceId,
    ExecutiveClientVersion,
    build_executive_client_surface,
)
from qore.governance.executive_control import ExecutivePrincipalId
from qore.governance.executive_transport_envelope import ExecutiveTransportMessageKind
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("52000000-0000-0000-0000-000000000001"))
_ASSERTION_ID = ExecutiveAuthenticationAssertionId(
    UUID("52000000-0000-0000-0000-000000000002")
)
_SURFACE_ID = ExecutiveClientSurfaceId(
    UUID("52000000-0000-0000-0000-000000000003")
)


def _assertion() -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=_ASSERTION_ID,
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:primary"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        correlation_id=_CORRELATION,
    )


def _surface() -> ExecutiveClientSurface:
    result = build_executive_client_surface(
        surface_id=_SURFACE_ID,
        platform=ExecutiveClientPlatform.IOS,
        client_version=ExecutiveClientVersion("mission05.v1"),
        allowed_message_kinds=(
            ExecutiveTransportMessageKind.CONTROL,
            ExecutiveTransportMessageKind.READ,
        ),
    )
    assert isinstance(result, Success)
    return result.value


def _session(
    *,
    status: ExecutiveClientSessionStatus = ExecutiveClientSessionStatus.ACTIVE,
) -> ExecutiveClientSession:
    result = build_executive_client_session(
        session_id=ExecutiveClientSessionId(
            UUID("52000000-0000-0000-0000-000000000004")
        ),
        surface_id=_SURFACE_ID,
        device_ref=ExecutiveClientDeviceRef("device:ios-primary"),
        principal_id=_PRINCIPAL,
        authentication_assertion_id=_ASSERTION_ID,
        status=status,
        established_at=_NOW + timedelta(minutes=1),
        expires_at=_NOW + timedelta(minutes=20),
        correlation_id=_CORRELATION,
    )
    assert isinstance(result, Success)
    return result.value


def test_active_session_binds_exact_surface_principal_assertion_and_correlation() -> None:
    session = _session()
    assertion = _assertion()
    result = bind_executive_client_session(
        session,
        _surface(),
        assertion,
        evaluated_at=_NOW + timedelta(minutes=2),
    )

    assert isinstance(result, Success)
    binding = result.value
    assert binding.session is session
    assert binding.authenticated_principal is assertion
    assert binding.logical_values() == binding.logical_values()
    assert not hasattr(binding, "token")
    assert not hasattr(binding, "credentials")
    with pytest.raises(FrozenInstanceError):
        binding.__setattr__("evaluated_at", _NOW)


def test_revoked_or_unknown_session_fails_closed() -> None:
    for status in (
        ExecutiveClientSessionStatus.REVOKED,
        ExecutiveClientSessionStatus.UNKNOWN,
    ):
        result = bind_executive_client_session(
            _session(status=status),
            _surface(),
            _assertion(),
            evaluated_at=_NOW + timedelta(minutes=2),
        )
        assert isinstance(result, Failure)


def test_expired_or_not_yet_active_session_fails_closed() -> None:
    session = _session()
    early = bind_executive_client_session(
        session,
        _surface(),
        _assertion(),
        evaluated_at=session.established_at - timedelta(microseconds=1),
    )
    expired = bind_executive_client_session(
        session,
        _surface(),
        _assertion(),
        evaluated_at=session.expires_at + timedelta(microseconds=1),
    )

    assert isinstance(early, Failure)
    assert isinstance(expired, Failure)


def test_session_cannot_outlive_or_predate_authentication_assertion() -> None:
    assertion = _assertion()
    session = _session()
    predating = replace(session, established_at=assertion.issued_at - timedelta(seconds=1))
    outliving = replace(session, expires_at=assertion.expires_at + timedelta(seconds=1))

    for invalid in (predating, outliving):
        result = bind_executive_client_session(
            invalid,
            _surface(),
            assertion,
            evaluated_at=_NOW + timedelta(minutes=2),
        )
        assert isinstance(result, Failure)


def test_surface_principal_assertion_or_correlation_mismatch_fails_closed() -> None:
    session = _session()
    assertion = _assertion()
    other_surface = build_executive_client_surface(
        surface_id=ExecutiveClientSurfaceId(UUID(int=100)),
        platform=ExecutiveClientPlatform.IOS,
        client_version=ExecutiveClientVersion("mission05.v1"),
        allowed_message_kinds=(ExecutiveTransportMessageKind.READ,),
    )
    assert isinstance(other_surface, Success)

    mismatches = (
        (session, other_surface.value, assertion),
        (
            replace(session, principal_id=ExecutivePrincipalId("ceo.other")),
            _surface(),
            assertion,
        ),
        (
            replace(
                session,
                authentication_assertion_id=ExecutiveAuthenticationAssertionId(
                    UUID(int=101)
                ),
            ),
            _surface(),
            assertion,
        ),
        (
            replace(session, correlation_id=CorrelationId(UUID(int=102))),
            _surface(),
            assertion,
        ),
    )

    for invalid_session, invalid_surface, invalid_assertion in mismatches:
        result = bind_executive_client_session(
            invalid_session,
            invalid_surface,
            invalid_assertion,
            evaluated_at=_NOW + timedelta(minutes=2),
        )
        assert isinstance(result, Failure)


def test_expired_authenticated_principal_blocks_session_binding() -> None:
    assertion = _assertion()
    session = replace(_session(), expires_at=assertion.expires_at)
    result = bind_executive_client_session(
        session,
        _surface(),
        assertion,
        evaluated_at=assertion.expires_at + timedelta(microseconds=1),
    )

    assert isinstance(result, Failure)


def test_device_reference_rejects_secret_bearing_or_noncanonical_values() -> None:
    for value in (
        "Bearer abc",
        "device:token-value",
        "device password",
        "Device:IOS",
    ):
        with pytest.raises(ExecutiveClientSessionValidationError):
            ExecutiveClientDeviceRef(value)


def test_session_types_and_chronology_fail_closed_without_coercion() -> None:
    with pytest.raises(ExecutiveClientSessionValidationError):
        ExecutiveClientSessionId(cast(UUID, "session"))

    result = build_executive_client_session(
        session_id=ExecutiveClientSessionId(UUID(int=103)),
        surface_id=_SURFACE_ID,
        device_ref=ExecutiveClientDeviceRef("device:ios-primary"),
        principal_id=_PRINCIPAL,
        authentication_assertion_id=_ASSERTION_ID,
        status=ExecutiveClientSessionStatus.ACTIVE,
        established_at=_NOW + timedelta(minutes=5),
        expires_at=_NOW + timedelta(minutes=4),
        correlation_id=_CORRELATION,
    )
    assert isinstance(result, Failure)
