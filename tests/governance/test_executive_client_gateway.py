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
from qore.governance.executive_client_gateway import (
    ExecutiveClientGatewayEnvironment,
    ExecutiveClientGatewayIngress,
    ExecutiveClientGatewayProtocol,
    ExecutiveClientGatewayRoute,
    ExecutiveClientGatewayValidationError,
    build_executive_client_gateway_ingress,
)
from qore.governance.executive_client_session import (
    ExecutiveClientDeviceRef,
    ExecutiveClientSessionBinding,
    ExecutiveClientSessionId,
    ExecutiveClientSessionStatus,
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
    ExecutiveTransportEnvelopeId,
    ExecutiveTransportMessageKind,
    ExecutiveTransportSchemaVersion,
    ExecutiveTransportSurface,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)
_PRINCIPAL = ExecutivePrincipalId("ceo.primary")
_CORRELATION = CorrelationId(UUID("53000000-0000-0000-0000-000000000001"))
_ASSERTION_ID = ExecutiveAuthenticationAssertionId(
    UUID("53000000-0000-0000-0000-000000000002")
)
_SURFACE_ID = ExecutiveClientSurfaceId(
    UUID("53000000-0000-0000-0000-000000000003")
)
_SCHEMA = ExecutiveTransportSchemaVersion("executive.v1")


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
        platform=ExecutiveClientPlatform.ANDROID,
        client_version=ExecutiveClientVersion("mission05.v1"),
        allowed_message_kinds=(
            ExecutiveTransportMessageKind.CONTROL,
            ExecutiveTransportMessageKind.READ,
        ),
    )
    assert isinstance(result, Success)
    return result.value


def _binding() -> ExecutiveClientSessionBinding:
    assertion = _assertion()
    surface = _surface()
    session_result = build_executive_client_session(
        session_id=ExecutiveClientSessionId(
            UUID("53000000-0000-0000-0000-000000000004")
        ),
        surface_id=_SURFACE_ID,
        device_ref=ExecutiveClientDeviceRef("device:android-primary"),
        principal_id=_PRINCIPAL,
        authentication_assertion_id=_ASSERTION_ID,
        status=ExecutiveClientSessionStatus.ACTIVE,
        established_at=_NOW + timedelta(minutes=1),
        expires_at=_NOW + timedelta(minutes=20),
        correlation_id=_CORRELATION,
    )
    assert isinstance(session_result, Success)
    binding_result = bind_executive_client_session(
        session_result.value,
        surface,
        assertion,
        evaluated_at=_NOW + timedelta(minutes=2),
    )
    assert isinstance(binding_result, Success)
    return binding_result.value


def _control() -> ExecutiveControlIntent:
    return ExecutiveControlIntent(
        intent_id=ExecutiveIntentId(UUID("53000000-0000-0000-0000-000000000005")),
        principal_id=_PRINCIPAL,
        action=ExecutiveControlAction.PAUSE_SYSTEM,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
        reason="CEO governed pause",
    )


def _read() -> ExecutiveReadRequest:
    return ExecutiveReadRequest(
        request_id=ExecutiveReadRequestId(
            UUID("53000000-0000-0000-0000-000000000006")
        ),
        principal_id=_PRINCIPAL,
        scope=ExecutiveReadScope.SYSTEM_HEALTH,
        requested_at=_NOW + timedelta(minutes=1),
        correlation_id=_CORRELATION,
    )


def test_gateway_normalizes_control_into_existing_mission04_envelope() -> None:
    result = build_executive_client_gateway_ingress(
        _binding(),
        _control(),
        envelope_id=ExecutiveTransportEnvelopeId(
            UUID("53000000-0000-0000-0000-000000000007")
        ),
        schema_version=_SCHEMA,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        route=ExecutiveClientGatewayRoute.CONTROL,
        received_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    ingress = result.value
    assert ingress.envelope.message_kind is ExecutiveTransportMessageKind.CONTROL
    assert ingress.envelope.surface is ExecutiveTransportSurface.MOBILE
    assert ingress.environment is ExecutiveClientGatewayEnvironment.TEST
    assert ingress.protocol is ExecutiveClientGatewayProtocol.HTTP
    assert ingress.logical_values() == ingress.logical_values()
    assert not hasattr(ingress, "headers")
    assert not hasattr(ingress, "token")
    assert not hasattr(ingress, "body")
    with pytest.raises(FrozenInstanceError):
        ingress.__setattr__("protocol", ExecutiveClientGatewayProtocol.WEBSOCKET)


def test_gateway_normalizes_read_using_same_surface_and_session() -> None:
    result = build_executive_client_gateway_ingress(
        _binding(),
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=8)),
        schema_version=_SCHEMA,
        environment=ExecutiveClientGatewayEnvironment.DEMO,
        protocol=ExecutiveClientGatewayProtocol.WEBSOCKET,
        route=ExecutiveClientGatewayRoute.READ,
        received_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(result, Success)
    assert result.value.envelope.message_kind is ExecutiveTransportMessageKind.READ
    assert result.value.route is ExecutiveClientGatewayRoute.READ


def test_route_payload_mismatch_fails_closed() -> None:
    control_as_read = build_executive_client_gateway_ingress(
        _binding(),
        _control(),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=9)),
        schema_version=_SCHEMA,
        environment=ExecutiveClientGatewayEnvironment.LOCAL,
        protocol=ExecutiveClientGatewayProtocol.IN_PROCESS,
        route=ExecutiveClientGatewayRoute.READ,
        received_at=_NOW + timedelta(minutes=3),
    )
    read_as_control = build_executive_client_gateway_ingress(
        _binding(),
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=10)),
        schema_version=_SCHEMA,
        environment=ExecutiveClientGatewayEnvironment.LOCAL,
        protocol=ExecutiveClientGatewayProtocol.IN_PROCESS,
        route=ExecutiveClientGatewayRoute.CONTROL,
        received_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(control_as_read, Failure)
    assert isinstance(read_as_control, Failure)


def test_gateway_rechecks_session_currency_at_receive_time() -> None:
    binding = _binding()
    result = build_executive_client_gateway_ingress(
        binding,
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=11)),
        schema_version=_SCHEMA,
        environment=ExecutiveClientGatewayEnvironment.STAGING,
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        route=ExecutiveClientGatewayRoute.READ,
        received_at=binding.session.expires_at + timedelta(microseconds=1),
    )

    assert isinstance(result, Failure)


def test_gateway_environment_has_no_production_value() -> None:
    assert {item.value for item in ExecutiveClientGatewayEnvironment} == {
        "local",
        "test",
        "demo",
        "staging",
    }
    result = build_executive_client_gateway_ingress(
        _binding(),
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=12)),
        schema_version=_SCHEMA,
        environment=cast(ExecutiveClientGatewayEnvironment, "production"),
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        route=ExecutiveClientGatewayRoute.READ,
        received_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(result, Failure)


def test_gateway_rejects_non_contract_protocol_route_and_payload() -> None:
    invalid_protocol = build_executive_client_gateway_ingress(
        _binding(),
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=13)),
        schema_version=_SCHEMA,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=cast(ExecutiveClientGatewayProtocol, "tcp"),
        route=ExecutiveClientGatewayRoute.READ,
        received_at=_NOW + timedelta(minutes=3),
    )
    invalid_route = build_executive_client_gateway_ingress(
        _binding(),
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=14)),
        schema_version=_SCHEMA,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        route=cast(ExecutiveClientGatewayRoute, "orders"),
        received_at=_NOW + timedelta(minutes=3),
    )
    invalid_payload = build_executive_client_gateway_ingress(
        _binding(),
        cast(ExecutiveReadRequest, object()),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=15)),
        schema_version=_SCHEMA,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        route=ExecutiveClientGatewayRoute.READ,
        received_at=_NOW + timedelta(minutes=3),
    )

    assert isinstance(invalid_protocol, Failure)
    assert isinstance(invalid_route, Failure)
    assert isinstance(invalid_payload, Failure)


def test_direct_ingress_requires_exact_route_kind_and_receive_time() -> None:
    valid = build_executive_client_gateway_ingress(
        _binding(),
        _read(),
        envelope_id=ExecutiveTransportEnvelopeId(UUID(int=16)),
        schema_version=_SCHEMA,
        environment=ExecutiveClientGatewayEnvironment.TEST,
        protocol=ExecutiveClientGatewayProtocol.HTTP,
        route=ExecutiveClientGatewayRoute.READ,
        received_at=_NOW + timedelta(minutes=3),
    )
    assert isinstance(valid, Success)

    with pytest.raises(ExecutiveClientGatewayValidationError):
        ExecutiveClientGatewayIngress(
            environment=valid.value.environment,
            protocol=valid.value.protocol,
            route=valid.value.route,
            session_binding=valid.value.session_binding,
            envelope=valid.value.envelope,
            received_at=valid.value.received_at + timedelta(microseconds=1),
        )
