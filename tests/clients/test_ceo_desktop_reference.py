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
from qore.governance.executive_client_gateway import (
    ExecutiveClientGatewayEnvironment,
    ExecutiveClientGatewayProtocol,
    ExecutiveClientGatewayRoute,
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
from qore.governance.executive_control import (
    ExecutivePrincipalId,
    ExecutiveReadRequest,
    ExecutiveReadRequestId,
    ExecutiveReadScope,
)
from qore.governance.executive_transport_envelope import (
    ExecutiveTransportEnvelopeId,
    ExecutiveTransportMessageKind,
    ExecutiveTransportSchemaVersion,
    ExecutiveTransportSurface,
)
from qore.kernel.result import Failure, Success
from qore_clients.desktop_reference import (
    ExecutiveDesktopReferenceClient,
    ExecutiveDesktopReferenceId,
    build_executive_desktop_reference_client,
    normalize_executive_desktop_gateway_ingress,
)

_NOW = datetime(2026, 8, 9, 17, 0, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("60000000-0000-0000-0000-000000000001"))
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_ASSERTION_ID = ExecutiveAuthenticationAssertionId(
    UUID("60000000-0000-0000-0000-000000000002")
)
_SURFACE_ID = ExecutiveClientSurfaceId(
    UUID("60000000-0000-0000-0000-000000000003")
)
_SCHEMA = ExecutiveTransportSchemaVersion("executive.v1")


def _surface(platform: ExecutiveClientPlatform) -> ExecutiveClientSurface:
    result = build_executive_client_surface(
        surface_id=_SURFACE_ID,
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
        assertion_id=_ASSERTION_ID,
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
        authentication_assertion_id=_ASSERTION_ID,
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


def _client(
    *,
    platform: ExecutiveClientPlatform = ExecutiveClientPlatform.DESKTOP,
    composed_at: datetime | None = None,
) -> Success[ExecutiveDesktopReferenceClient]:
    surface = _surface(platform)
    binding = _binding(surface)
    view_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=5)),
        surface_id=surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(),
    )
    assert isinstance(view_result, Success)
    result = build_executive_desktop_reference_client(
        reference_id=ExecutiveDesktopReferenceId(UUID(int=6)),
        surface=surface,
        session_binding=binding,
        command_center=view_result.value,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        composed_at=composed_at or _NOW + timedelta(minutes=3),
    )
    assert isinstance(result, Success)
    return result


def _read() -> ExecutiveReadRequest:
    return ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(UUID(int=7)),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.SYSTEM_HEALTH,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
    )


def test_desktop_reference_lives_outside_core_package_and_composes_boundaries() -> None:
    client = _client().value

    assert ExecutiveDesktopReferenceClient.__module__.startswith("qore_clients.")
    assert client.surface.platform is ExecutiveClientPlatform.DESKTOP
    assert client.surface.transport_surface is ExecutiveTransportSurface.CEO_COMMAND_CENTER
    assert client.command_center.surface_id == client.surface.surface_id
    assert client.session_binding.surface == client.surface
    assert client.logical_values() == client.logical_values()
    assert not client.automatic_redispatch_allowed


def test_non_desktop_surface_fails_closed() -> None:
    surface = _surface(ExecutiveClientPlatform.IOS)
    binding = _binding(surface)
    view_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=8)),
        surface_id=surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(),
    )
    assert isinstance(view_result, Success)

    result = build_executive_desktop_reference_client(
        reference_id=ExecutiveDesktopReferenceId(UUID(int=9)),
        surface=surface,
        session_binding=binding,
        command_center=view_result.value,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        composed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Failure)


def test_session_surface_value_mismatch_fails_closed() -> None:
    surface = _surface(ExecutiveClientPlatform.DESKTOP)
    binding = _binding(surface)
    changed_surface = replace(
        surface,
        client_version=ExecutiveClientVersion("desktop.v2"),
    )
    view_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=10)),
        surface_id=changed_surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(),
    )
    assert isinstance(view_result, Success)

    result = build_executive_desktop_reference_client(
        reference_id=ExecutiveDesktopReferenceId(UUID(int=11)),
        surface=changed_surface,
        session_binding=binding,
        command_center=view_result.value,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        composed_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Failure)


def test_desktop_composition_cannot_outlive_bound_session() -> None:
    surface = _surface(ExecutiveClientPlatform.DESKTOP)
    binding = _binding(surface)
    view_result = build_executive_command_center_view_model(
        view_model_id=ExecutiveCommandCenterViewModelId(UUID(int=12)),
        surface_id=surface.surface_id,
        observed_at=_NOW + timedelta(minutes=2),
        selected_section=ExecutiveCommandCenterSection.HOME,
        state_views=(),
    )
    assert isinstance(view_result, Success)

    result = build_executive_desktop_reference_client(
        reference_id=ExecutiveDesktopReferenceId(UUID(int=13)),
        surface=surface,
        session_binding=binding,
        command_center=view_result.value,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        composed_at=binding.session.expires_at + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)


def test_desktop_request_delegates_to_canonical_client_gateway() -> None:
    client = _client().value
    result = normalize_executive_desktop_gateway_ingress(
        client,
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=14)),
        schema_version=_SCHEMA,
        route=ExecutiveClientGatewayRoute.READ,
        received_at=_NOW + timedelta(minutes=4),
    )

    assert isinstance(result, Success)
    ingress = result.value
    assert ingress.environment is ExecutiveClientGatewayEnvironment.TEST
    assert ingress.protocol is ExecutiveClientGatewayProtocol.HTTP
    assert ingress.route is ExecutiveClientGatewayRoute.READ
    assert ingress.envelope.surface is ExecutiveTransportSurface.CEO_COMMAND_CENTER
    assert ingress.envelope.message_kind is ExecutiveTransportMessageKind.READ


def test_desktop_reference_exposes_no_direct_core_or_execution_surface() -> None:
    client = _client().value

    assert not hasattr(client, "core")
    assert not hasattr(client, "broker")
    assert not hasattr(client, "submit_order")
    assert not hasattr(client, "buy")
    assert not hasattr(client, "sell")
    assert not hasattr(client, "bypass_risk")
    assert not hasattr(client, "retry")
    assert not hasattr(client, "window")
