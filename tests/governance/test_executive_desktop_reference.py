from __future__ import annotations

from dataclasses import replace
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
from qore.governance.executive_client_session import (
    ExecutiveClientDeviceRef,
    ExecutiveClientSession,
    ExecutiveClientSessionBinding,
    ExecutiveClientSessionId,
    ExecutiveClientSessionStatus,
)
from qore.governance.executive_client_surface import (
    ExecutiveClientPlatform,
    ExecutiveClientSurface,
    ExecutiveClientSurfaceId,
    ExecutiveClientVersion,
    build_executive_client_surface,
)
from qore.governance.executive_command_center_view_model import (
    ExecutiveCommandCenterSection,
    ExecutiveCommandCenterViewModelId,
    build_executive_command_center_view_model,
)
from qore.governance.executive_control import ExecutivePrincipalId
from qore.governance.executive_desktop_reference import (
    ExecutiveDesktopReferenceId,
    build_executive_desktop_reference_state,
)
from qore.governance.executive_transport_envelope import ExecutiveTransportMessageKind
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 17, 0, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("60000000-0000-0000-0000-000000000001"))
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")


def _surface(platform: ExecutiveClientPlatform) -> ExecutiveClientSurface:
    result = build_executive_client_surface(
        surface_id=ExecutiveClientSurfaceId(UUID("60000000-0000-0000-0000-000000000002")),
        platform=platform,
        client_version=ExecutiveClientVersion("desktop.v1"),
        allowed_message_kinds=(
            ExecutiveTransportMessageKind.CONTROL,
            ExecutiveTransportMessageKind.READ,
        ),
    )
    assert isinstance(result, Success)
    return result.value


def _binding(surface: ExecutiveClientSurface) -> ExecutiveClientSessionBinding:
    assertion = AuthenticatedExecutivePrincipal(
        assertion_id=ExecutiveAuthenticationAssertionId(
            UUID("60000000-0000-0000-0000-000000000003")
        ),
        principal_id=_PRINCIPAL,
        method=ExecutiveAuthenticationMethodCode("passkey"),
        context=ExecutiveAuthenticationContextCode("mfa.strong"),
        identity_boundary_ref=ExecutiveIdentityBoundaryRef("identity:desktop"),
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=30),
        correlation_id=_CORRELATION,
    )
    session = ExecutiveClientSession(
        session_id=ExecutiveClientSessionId(
            UUID("60000000-0000-0000-0000-000000000004")
        ),
        surface_id=surface.surface_id,
        device_ref=ExecutiveClientDeviceRef("device:desktop-reference"),
        principal_id=_PRINCIPAL,
        authentication_assertion_id=assertion.assertion_id,
        status=ExecutiveClientSessionStatus.ACTIVE,
        established_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(minutes=20),
        correlation_id=_CORRELATION,
    )
    return ExecutiveClientSessionBinding(
        session=session,
        surface=surface,
        authenticated_principal=assertion,
        evaluated_at=_NOW + timedelta(minutes=2),
    )


def test_desktop_reference_composes_exact_approved_boundaries() -> None:
    surface = _surface(ExecutiveClientPlatform.DESKTOP)
    binding = _binding(surface)
    command_center_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=5)),
        surface_id=surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(),
    )
    assert isinstance(command_center_result, Success)

    result = build_executive_desktop_reference_state(
        reference_id=ExecutiveDesktopReferenceId(UUID(int=6)),
        surface=surface,
        session_binding=binding,
        command_center=command_center_result.value,
        composed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assert result.value.surface.platform is ExecutiveClientPlatform.DESKTOP
    assert result.value.logical_values() == result.value.logical_values()


def test_non_desktop_surface_fails_closed() -> None:
    surface = _surface(ExecutiveClientPlatform.IOS)
    binding = _binding(surface)
    command_center_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=7)),
        surface_id=surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(),
    )
    assert isinstance(command_center_result, Success)

    result = build_executive_desktop_reference_state(
        reference_id=ExecutiveDesktopReferenceId(UUID(int=8)),
        surface=surface,
        session_binding=binding,
        command_center=command_center_result.value,
        composed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Failure)


def test_surface_mismatch_between_session_and_view_model_fails_closed() -> None:
    surface = _surface(ExecutiveClientPlatform.DESKTOP)
    binding = _binding(surface)
    other_id = ExecutiveClientSurfaceId(UUID(int=9))
    command_center_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=10)),
        surface_id=other_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(),
    )
    assert isinstance(command_center_result, Success)

    result = build_executive_desktop_reference_state(
        reference_id=ExecutiveDesktopReferenceId(UUID(int=11)),
        surface=surface,
        session_binding=binding,
        command_center=command_center_result.value,
        composed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Failure)


def test_session_binding_must_use_exact_surface_value() -> None:
    surface = _surface(ExecutiveClientPlatform.DESKTOP)
    binding = _binding(surface)
    changed_surface = replace(
        surface,
        client_version=ExecutiveClientVersion("desktop.v2"),
    )
    command_center_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=12)),
        surface_id=changed_surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(),
    )
    assert isinstance(command_center_result, Success)

    result = build_executive_desktop_reference_state(
        reference_id=ExecutiveDesktopReferenceId(UUID(int=13)),
        surface=changed_surface,
        session_binding=binding,
        command_center=command_center_result.value,
        composed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Failure)


def test_desktop_reference_exposes_no_direct_core_or_execution_surface() -> None:
    surface = _surface(ExecutiveClientPlatform.DESKTOP)
    binding = _binding(surface)
    command_center_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=14)),
        surface_id=surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.CIBO,
        state_views=(),
    )
    assert isinstance(command_center_result, Success)
    result = build_executive_desktop_reference_state(
        reference_id=ExecutiveDesktopReferenceId(UUID(int=15)),
        surface=surface,
        session_binding=binding,
        command_center=command_center_result.value,
        composed_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(result, Success)
    desktop = result.value

    assert not hasattr(desktop, "core")
    assert not hasattr(desktop, "broker")
    assert not hasattr(desktop, "submit_order")
    assert not hasattr(desktop, "buy")
    assert not hasattr(desktop, "sell")
    assert not hasattr(desktop, "window")
    assert not hasattr(desktop, "retry")
