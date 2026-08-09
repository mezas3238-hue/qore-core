from __future__ import annotations

from dataclasses import FrozenInstanceError
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
from qore.governance.executive_client_surface import (
    ExecutiveClientPlatform,
    ExecutiveClientSurface,
    ExecutiveClientSurfaceId,
    ExecutiveClientSurfaceValidationError,
    ExecutiveClientVersion,
    build_executive_client_surface,
    expected_transport_surface,
    validate_executive_client_envelope_binding,
)
from qore.governance.executive_control import (
    ExecutiveControlAction,
    ExecutiveControlIntent,
    ExecutiveIntentId,
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
)
from qore.governance.executive_transport_envelope import (
    ExecutiveTransportEnvelope,
    ExecutiveTransportEnvelopeId,
    ExecutiveTransportMessageKind,
    ExecutiveTransportSchemaVersion,
    ExecutiveTransportSurface,
    build_executive_control_transport_envelope,
    build_executive_read_transport_envelope,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 8, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("51000000-0000-0000-0000-000000000001"))
_SCHEMA = ExecutiveTransportSchemaVersion("executive.v1")
_VERSION = ExecutiveClientVersion("mission05.v1")


def _assertion() -> AuthenticatedExecutivePrincipal:
    return AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("51000000-0000-0000-0000-000000000002")
        ),
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:primary"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        correlation_id=_CORRELATION,
    )


def _intent() -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("51000000-0000-0000-0000-000000000003")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="CEO governed pause",
    )


def _read() -> ExecutiveReadRequest:
    return ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(
            UUID("51000000-0000-0000-0000-000000000004")
        ),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.SYSTEM_HEALTH,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
    )


def _surface(
    platform: ExecutiveClientPlatform,
    *,
    allowed: tuple[ExecutiveTransportMessageKind, ...] = (
        ExecutiveTransportMessageKind.CONTROL,
        ExecutiveTransportMessageKind.READ,
    ),
) -> ExecutiveClientSurface:
    result = build_executive_client_surface(
        surface_id=ExecutiveClientSurfaceId(
            UUID("51000000-0000-0000-0000-000000000005")
        ),
        platform=platform,
        client_version=_VERSION,
        allowed_message_kinds=allowed,
    )
    assert isinstance(result, Success)
    return result.value


def _control_envelope(
    transport_surface: ExecutiveTransportSurface,
) -> ExecutiveTransportEnvelope:
    result = build_executive_control_transport_envelope(
        _assertion(),
        _intent(),
        envelope_id=ExecutiveTransportEnvelopeId(
            UUID("51000000-0000-0000-0000-000000000006")
        ),
        schema_version=_SCHEMA,
        surface=transport_surface,
        received_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(result, Success)
    return result.value


def _read_envelope(
    transport_surface: ExecutiveTransportSurface,
) -> ExecutiveTransportEnvelope:
    result = build_executive_read_transport_envelope(
        _assertion(),
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(
            UUID("51000000-0000-0000-0000-000000000007")
        ),
        schema_version=_SCHEMA,
        surface=transport_surface,
        received_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(result, Success)
    return result.value


def test_platforms_bind_only_to_existing_mission04_transport_surfaces() -> None:
    desktop = _surface(ExecutiveClientPlatform.DESKTOP)
    ios = _surface(ExecutiveClientPlatform.IOS)
    android = _surface(ExecutiveClientPlatform.ANDROID)

    assert desktop.transport_surface is ExecutiveTransportSurface.CEO_COMMAND_CENTER
    assert ios.transport_surface is ExecutiveTransportSurface.MOBILE
    assert android.transport_surface is ExecutiveTransportSurface.MOBILE
    assert expected_transport_surface(ExecutiveClientPlatform.DESKTOP) is desktop.transport_surface
    assert expected_transport_surface(ExecutiveClientPlatform.IOS) is ios.transport_surface


def test_surface_is_immutable_secret_free_and_deterministically_ordered() -> None:
    surface = _surface(
        ExecutiveClientPlatform.IOS,
        allowed=(
            ExecutiveTransportMessageKind.READ,
            ExecutiveTransportMessageKind.CONTROL,
        ),
    )

    assert surface.allowed_message_kinds == (
        ExecutiveTransportMessageKind.CONTROL,
        ExecutiveTransportMessageKind.READ,
    )
    assert surface.logical_values() == surface.logical_values()
    assert not hasattr(surface, "token")
    assert not hasattr(surface, "credentials")
    assert not hasattr(surface, "provider")
    assert not hasattr(surface, "core_application")
    with pytest.raises(FrozenInstanceError):
        surface.__setattr__("platform", ExecutiveClientPlatform.ANDROID)


def test_surface_rejects_duplicate_or_empty_message_kinds() -> None:
    duplicate = build_executive_client_surface(
        surface_id=ExecutiveClientSurfaceId(UUID(int=10)),
        platform=ExecutiveClientPlatform.ANDROID,
        client_version=_VERSION,
        allowed_message_kinds=(
            ExecutiveTransportMessageKind.READ,
            ExecutiveTransportMessageKind.READ,
        ),
    )
    empty = build_executive_client_surface(
        surface_id=ExecutiveClientSurfaceId(UUID(int=11)),
        platform=ExecutiveClientPlatform.ANDROID,
        client_version=_VERSION,
        allowed_message_kinds=(),
    )

    assert isinstance(duplicate, Failure)
    assert isinstance(empty, Failure)


def test_surface_types_fail_closed_without_coercion() -> None:
    with pytest.raises(ExecutiveClientSurfaceValidationError):
        ExecutiveClientSurfaceId(cast(UUID, "surface"))
    with pytest.raises(ExecutiveClientSurfaceValidationError):
        ExecutiveClientVersion("Mission 05")
    with pytest.raises(ExecutiveClientSurfaceValidationError):
        expected_transport_surface(cast(ExecutiveClientPlatform, "ios"))


def test_envelope_binding_accepts_only_matching_transport_and_allowed_kind() -> None:
    desktop = _surface(
        ExecutiveClientPlatform.DESKTOP,
        allowed=(ExecutiveTransportMessageKind.READ,),
    )
    matching = _read_envelope(ExecutiveTransportSurface.CEO_COMMAND_CENTER)
    wrong_transport = _read_envelope(ExecutiveTransportSurface.MOBILE)
    wrong_kind = _control_envelope(ExecutiveTransportSurface.CEO_COMMAND_CENTER)

    accepted = validate_executive_client_envelope_binding(desktop, matching)
    rejected_transport = validate_executive_client_envelope_binding(
        desktop,
        wrong_transport,
    )
    rejected_kind = validate_executive_client_envelope_binding(desktop, wrong_kind)

    assert isinstance(accepted, Success)
    assert accepted.value is matching
    assert isinstance(rejected_transport, Failure)
    assert isinstance(rejected_kind, Failure)


def test_direct_manual_platform_transport_mismatch_fails_closed() -> None:
    with pytest.raises(ExecutiveClientSurfaceValidationError):
        ExecutiveClientSurface(
            surface_id=ExecutiveClientSurfaceId(UUID(int=12)),
            platform=ExecutiveClientPlatform.IOS,
            client_version=_VERSION,
            transport_surface=ExecutiveTransportSurface.CEO_COMMAND_CENTER,
            allowed_message_kinds=(ExecutiveTransportMessageKind.READ,),
        )


def test_binding_rejects_non_contract_values() -> None:
    surface = _surface(ExecutiveClientPlatform.ANDROID)
    envelope = _read_envelope(ExecutiveTransportSurface.MOBILE)

    invalid_surface = validate_executive_client_envelope_binding(
        cast(ExecutiveClientSurface, object()),
        envelope,
    )
    invalid_envelope = validate_executive_client_envelope_binding(
        surface,
        cast(ExecutiveTransportEnvelope, object()),
    )

    assert isinstance(invalid_surface, Failure)
    assert isinstance(invalid_envelope, Failure)
