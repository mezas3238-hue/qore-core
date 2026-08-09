from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.governance.executive_client_session import (
    ExecutiveClientSessionBinding,
    bind_executive_client_session,
)
from qore.governance.executive_client_surface import (
    validate_executive_client_envelope_binding,
)
from qore.governance.executive_control import ExecutiveControlIntent, ExecutiveReadRequest
from qore.governance.executive_transport_envelope import (
    ExecutiveTransportEnvelope,
    ExecutiveTransportEnvelopeId,
    ExecutiveTransportMessageKind,
    ExecutiveTransportSchemaVersion,
    build_executive_control_transport_envelope,
    build_executive_read_transport_envelope,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveClientGatewayError(DomainError):
    """Base error for non-production executive client gateway normalization."""

    __slots__ = ()


class ExecutiveClientGatewayValidationError(ExecutiveClientGatewayError):
    """A client gateway value violates a deterministic ingress invariant."""

    __slots__ = ()


class ExecutiveClientGatewayBlockedError(ExecutiveClientGatewayError):
    """A client request cannot safely enter the MISSION-04 transport boundary."""

    __slots__ = ()


class ExecutiveClientGatewayEnvironment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    DEMO = "demo"
    STAGING = "staging"


class ExecutiveClientGatewayProtocol(StrEnum):
    IN_PROCESS = "in-process"
    HTTP = "http"
    WEBSOCKET = "websocket"


class ExecutiveClientGatewayRoute(StrEnum):
    CONTROL = "control"
    READ = "read"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveClientGatewayValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveClientGatewayValidationError(
            f"{field_name} must be timezone-aware"
        )


def _expected_message_kind(route: ExecutiveClientGatewayRoute) -> ExecutiveTransportMessageKind:
    if not isinstance(route, ExecutiveClientGatewayRoute):
        raise ExecutiveClientGatewayValidationError(
            "executive client gateway route must be ExecutiveClientGatewayRoute"
        )
    if route is ExecutiveClientGatewayRoute.CONTROL:
        return ExecutiveTransportMessageKind.CONTROL
    return ExecutiveTransportMessageKind.READ


ExecutiveClientGatewayPayload = ExecutiveControlIntent | ExecutiveReadRequest


@dataclass(frozen=True, slots=True)
class ExecutiveClientGatewayIngress:
    """Safe normalized client ingress ready for the existing Control Plane envelope."""

    environment: ExecutiveClientGatewayEnvironment
    protocol: ExecutiveClientGatewayProtocol
    route: ExecutiveClientGatewayRoute
    session_binding: ExecutiveClientSessionBinding
    envelope: ExecutiveTransportEnvelope
    received_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.environment, ExecutiveClientGatewayEnvironment):
            raise ExecutiveClientGatewayValidationError(
                "executive client gateway ingress requires explicit environment"
            )
        if not isinstance(self.protocol, ExecutiveClientGatewayProtocol):
            raise ExecutiveClientGatewayValidationError(
                "executive client gateway ingress requires explicit protocol"
            )
        if not isinstance(self.route, ExecutiveClientGatewayRoute):
            raise ExecutiveClientGatewayValidationError(
                "executive client gateway ingress requires explicit route"
            )
        if not isinstance(self.session_binding, ExecutiveClientSessionBinding):
            raise ExecutiveClientGatewayValidationError(
                "executive client gateway ingress requires ExecutiveClientSessionBinding"
            )
        if not isinstance(self.envelope, ExecutiveTransportEnvelope):
            raise ExecutiveClientGatewayValidationError(
                "executive client gateway ingress requires ExecutiveTransportEnvelope"
            )
        _validate_timestamp(self.received_at, field_name="received_at")
        if self.received_at != self.envelope.received_at:
            raise ExecutiveClientGatewayValidationError(
                "gateway receipt time must match normalized envelope receipt time"
            )
        if self.received_at != self.session_binding.evaluated_at:
            raise ExecutiveClientGatewayValidationError(
                "gateway receipt time must match session evaluation time"
            )
        if (
            self.envelope.authenticated_principal
            != self.session_binding.authenticated_principal
        ):
            raise ExecutiveClientGatewayBlockedError(
                "gateway envelope principal must match session binding"
            )
        expected_kind = _expected_message_kind(self.route)
        if self.envelope.message_kind is not expected_kind:
            raise ExecutiveClientGatewayBlockedError(
                "gateway route must match normalized envelope message kind"
            )
        surface_result = validate_executive_client_envelope_binding(
            self.session_binding.surface,
            self.envelope,
        )
        if isinstance(surface_result, Failure):
            raise ExecutiveClientGatewayBlockedError(
                "gateway envelope does not satisfy client surface boundary"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.environment.value,
            self.protocol.value,
            self.route.value,
            self.session_binding.logical_values(),
            self.envelope.logical_values(),
            self.received_at.isoformat(),
        )


def build_executive_client_gateway_ingress(
    session_binding: ExecutiveClientSessionBinding,
    payload: ExecutiveClientGatewayPayload,
    *,
    envelope_id: ExecutiveTransportEnvelopeId,
    schema_version: ExecutiveTransportSchemaVersion,
    environment: ExecutiveClientGatewayEnvironment,
    protocol: ExecutiveClientGatewayProtocol,
    route: ExecutiveClientGatewayRoute,
    received_at: datetime,
) -> Result[ExecutiveClientGatewayIngress, ExecutiveClientGatewayError]:
    """Normalize one safe non-production client request into MISSION-04 ingress."""

    if not isinstance(session_binding, ExecutiveClientSessionBinding):
        return Failure(
            ExecutiveClientGatewayValidationError(
                "client gateway requires ExecutiveClientSessionBinding"
            )
        )
    if not isinstance(environment, ExecutiveClientGatewayEnvironment):
        return Failure(
            ExecutiveClientGatewayValidationError(
                "client gateway requires ExecutiveClientGatewayEnvironment"
            )
        )
    if not isinstance(protocol, ExecutiveClientGatewayProtocol):
        return Failure(
            ExecutiveClientGatewayValidationError(
                "client gateway requires ExecutiveClientGatewayProtocol"
            )
        )
    if not isinstance(route, ExecutiveClientGatewayRoute):
        return Failure(
            ExecutiveClientGatewayValidationError(
                "client gateway requires ExecutiveClientGatewayRoute"
            )
        )
    try:
        _validate_timestamp(received_at, field_name="received_at")
        expected_kind = _expected_message_kind(route)
    except ExecutiveClientGatewayError as error:
        return Failure(error)

    refreshed_session_result = bind_executive_client_session(
        session_binding.session,
        session_binding.surface,
        session_binding.authenticated_principal,
        evaluated_at=received_at,
    )
    if isinstance(refreshed_session_result, Failure):
        return Failure(
            ExecutiveClientGatewayBlockedError(
                "client session is not valid at gateway receipt time"
            )
        )
    refreshed_session = refreshed_session_result.value

    if isinstance(payload, ExecutiveControlIntent):
        if expected_kind is not ExecutiveTransportMessageKind.CONTROL:
            return Failure(
                ExecutiveClientGatewayBlockedError(
                    "client gateway route does not match control payload"
                )
            )
        envelope_result = build_executive_control_transport_envelope(
            refreshed_session.authenticated_principal,
            payload,
            envelope_id=envelope_id,
            schema_version=schema_version,
            surface=refreshed_session.surface.transport_surface,
            received_at=received_at,
        )
    elif isinstance(payload, ExecutiveReadRequest):
        if expected_kind is not ExecutiveTransportMessageKind.READ:
            return Failure(
                ExecutiveClientGatewayBlockedError(
                    "client gateway route does not match read payload"
                )
            )
        envelope_result = build_executive_read_transport_envelope(
            refreshed_session.authenticated_principal,
            payload,
            envelope_id=envelope_id,
            schema_version=schema_version,
            surface=refreshed_session.surface.transport_surface,
            received_at=received_at,
        )
    else:
        return Failure(
            ExecutiveClientGatewayValidationError(
                "client gateway payload must be control intent or read request"
            )
        )

    if isinstance(envelope_result, Failure):
        return Failure(
            ExecutiveClientGatewayBlockedError(
                "client payload could not be normalized into executive transport envelope"
            )
        )

    try:
        return Success(
            ExecutiveClientGatewayIngress(
                environment=environment,
                protocol=protocol,
                route=route,
                session_binding=refreshed_session,
                envelope=envelope_result.value,
                received_at=received_at,
            )
        )
    except ExecutiveClientGatewayError as error:
        return Failure(error)
