from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from qore.governance.executive_client_gateway import (
    ExecutiveClientGatewayEnvironment,
    ExecutiveClientGatewayError,
    ExecutiveClientGatewayIngress,
    ExecutiveClientGatewayPayload,
    ExecutiveClientGatewayProtocol,
    ExecutiveClientGatewayRoute,
    build_executive_client_gateway_ingress,
)
from qore.governance.executive_client_session import ExecutiveClientSessionBinding
from qore.governance.executive_client_surface import (
    ExecutiveClientPlatform,
    ExecutiveClientSurface,
)
from qore.governance.executive_command_center_view_model import (
    ExecutiveCommandCenterViewModel,
)
from qore.governance.executive_governance_ux import ExecutiveGovernanceUxState
from qore.governance.executive_transport_envelope import (
    ExecutiveTransportEnvelopeId,
    ExecutiveTransportSchemaVersion,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveAndroidReferenceError(DomainError):
    """Base error for the non-production CEO Android reference client."""

    __slots__ = ()


class ExecutiveAndroidReferenceValidationError(ExecutiveAndroidReferenceError):
    """An Android reference composition violates a deterministic invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveAndroidReferenceValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveAndroidReferenceValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ExecutiveAndroidReferenceId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveAndroidReferenceValidationError(
                "Android reference id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveAndroidReferenceClient:
    """Framework-free Android composition over approved MISSION-05 boundaries."""

    reference_id: ExecutiveAndroidReferenceId
    surface: ExecutiveClientSurface
    session_binding: ExecutiveClientSessionBinding
    command_center: ExecutiveCommandCenterViewModel
    environment: ExecutiveClientGatewayEnvironment
    protocol: ExecutiveClientGatewayProtocol
    composed_at: datetime
    governance_ux: ExecutiveGovernanceUxState | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reference_id, ExecutiveAndroidReferenceId):
            raise ExecutiveAndroidReferenceValidationError(
                "Android reference requires ExecutiveAndroidReferenceId"
            )
        if not isinstance(self.surface, ExecutiveClientSurface):
            raise ExecutiveAndroidReferenceValidationError(
                "Android reference requires ExecutiveClientSurface"
            )
        if self.surface.platform is not ExecutiveClientPlatform.ANDROID:
            raise ExecutiveAndroidReferenceValidationError(
                "Android reference requires ANDROID client platform"
            )
        if not isinstance(self.session_binding, ExecutiveClientSessionBinding):
            raise ExecutiveAndroidReferenceValidationError(
                "Android reference requires ExecutiveClientSessionBinding"
            )
        if self.session_binding.surface != self.surface:
            raise ExecutiveAndroidReferenceValidationError(
                "Android session binding must use the exact Android surface"
            )
        if not isinstance(self.command_center, ExecutiveCommandCenterViewModel):
            raise ExecutiveAndroidReferenceValidationError(
                "Android reference requires ExecutiveCommandCenterViewModel"
            )
        if self.command_center.surface_id != self.surface.surface_id:
            raise ExecutiveAndroidReferenceValidationError(
                "Android Command Center must use the exact Android surface"
            )
        if not isinstance(self.environment, ExecutiveClientGatewayEnvironment):
            raise ExecutiveAndroidReferenceValidationError(
                "Android reference requires explicit non-production environment"
            )
        if not isinstance(self.protocol, ExecutiveClientGatewayProtocol):
            raise ExecutiveAndroidReferenceValidationError(
                "Android reference requires ExecutiveClientGatewayProtocol"
            )
        _validate_timestamp(self.composed_at, field_name="composed_at")
        if self.composed_at < self.session_binding.evaluated_at:
            raise ExecutiveAndroidReferenceValidationError(
                "Android composition cannot predate session evaluation"
            )
        if self.composed_at > self.session_binding.session.expires_at:
            raise ExecutiveAndroidReferenceValidationError(
                "Android composition cannot outlive the bound client session"
            )
        if self.composed_at < self.command_center.observed_at:
            raise ExecutiveAndroidReferenceValidationError(
                "Android composition cannot predate Command Center observation"
            )
        if self.governance_ux is not None:
            if not isinstance(self.governance_ux, ExecutiveGovernanceUxState):
                raise ExecutiveAndroidReferenceValidationError(
                    "Android governance UX must be ExecutiveGovernanceUxState"
                )
            if self.governance_ux.surface_id != self.surface.surface_id:
                raise ExecutiveAndroidReferenceValidationError(
                    "Android governance UX must use the exact Android surface"
                )
            if self.composed_at < self.governance_ux.observed_at:
                raise ExecutiveAndroidReferenceValidationError(
                    "Android composition cannot predate Governance UX observation"
                )

    @property
    def automatic_redispatch_allowed(self) -> bool:
        return False

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.reference_id.logical_values(),
            self.surface.logical_values(),
            self.session_binding.logical_values(),
            self.command_center.logical_values(),
            self.environment.value,
            self.protocol.value,
            self.composed_at.isoformat(),
            None if self.governance_ux is None else self.governance_ux.logical_values(),
            self.automatic_redispatch_allowed,
        )


def build_executive_android_reference_client(
    *,
    reference_id: ExecutiveAndroidReferenceId,
    surface: ExecutiveClientSurface,
    session_binding: ExecutiveClientSessionBinding,
    command_center: ExecutiveCommandCenterViewModel,
    environment: ExecutiveClientGatewayEnvironment,
    protocol: ExecutiveClientGatewayProtocol,
    composed_at: datetime,
    governance_ux: ExecutiveGovernanceUxState | None = None,
) -> Result[ExecutiveAndroidReferenceClient, ExecutiveAndroidReferenceError]:
    try:
        return Success(
            ExecutiveAndroidReferenceClient(
                reference_id=reference_id,
                surface=surface,
                session_binding=session_binding,
                command_center=command_center,
                environment=environment,
                protocol=protocol,
                composed_at=composed_at,
                governance_ux=governance_ux,
            )
        )
    except ExecutiveAndroidReferenceError as error:
        return Failure(error)


def normalize_executive_android_gateway_ingress(
    client: ExecutiveAndroidReferenceClient,
    payload: ExecutiveClientGatewayPayload,
    *,
    envelope_id: ExecutiveTransportEnvelopeId,
    schema_version: ExecutiveTransportSchemaVersion,
    route: ExecutiveClientGatewayRoute,
    received_at: datetime,
) -> Result[ExecutiveClientGatewayIngress, ExecutiveClientGatewayError]:
    """Delegate Android ingress to the canonical MISSION-05 gateway boundary."""

    return build_executive_client_gateway_ingress(
        client.session_binding,
        payload,
        envelope_id=envelope_id,
        schema_version=schema_version,
        environment=client.environment,
        protocol=client.protocol,
        route=route,
        received_at=received_at,
    )
