from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.executive_authentication import AuthenticatedExecutivePrincipal
from qore.governance.executive_control import ExecutiveControlIntent, ExecutiveReadRequest
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveTransportEnvelopeError(DomainError):
    """Base error for transport-neutral executive ingress envelopes."""

    __slots__ = ()


class ExecutiveTransportEnvelopeValidationError(ExecutiveTransportEnvelopeError):
    """An executive transport envelope violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveTransportSurface(StrEnum):
    MOBILE = "mobile"
    CEO_COMMAND_CENTER = "ceo-command-center"
    API = "api"
    INTERNAL_SERVICE = "internal-service"


class ExecutiveTransportMessageKind(StrEnum):
    CONTROL = "control"
    READ = "read"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveTransportEnvelopeValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveTransportEnvelopeValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ExecutiveTransportEnvelopeId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport envelope id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveTransportSchemaVersion:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z0-9][a-z0-9._-]*", self.value
        ) is None:
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport schema version must use canonical syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


ExecutiveTransportPayload = ExecutiveControlIntent | ExecutiveReadRequest


@dataclass(frozen=True, slots=True)
class ExecutiveTransportEnvelope:
    """Secret-free normalized ingress envelope for future executive surfaces."""

    envelope_id: ExecutiveTransportEnvelopeId
    schema_version: ExecutiveTransportSchemaVersion
    surface: ExecutiveTransportSurface
    message_kind: ExecutiveTransportMessageKind
    authenticated_principal: AuthenticatedExecutivePrincipal
    payload: ExecutiveTransportPayload
    received_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.envelope_id, ExecutiveTransportEnvelopeId):
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport envelope requires ExecutiveTransportEnvelopeId"
            )
        if not isinstance(self.schema_version, ExecutiveTransportSchemaVersion):
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport envelope requires ExecutiveTransportSchemaVersion"
            )
        if not isinstance(self.surface, ExecutiveTransportSurface):
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport envelope requires ExecutiveTransportSurface"
            )
        if not isinstance(self.message_kind, ExecutiveTransportMessageKind):
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport envelope requires ExecutiveTransportMessageKind"
            )
        if not isinstance(self.authenticated_principal, AuthenticatedExecutivePrincipal):
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport envelope requires AuthenticatedExecutivePrincipal"
            )
        if not isinstance(self.payload, (ExecutiveControlIntent, ExecutiveReadRequest)):
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport payload must be control intent or read request"
            )
        _validate_timestamp(self.received_at, field_name="received_at")
        expected_kind = (
            ExecutiveTransportMessageKind.CONTROL
            if isinstance(self.payload, ExecutiveControlIntent)
            else ExecutiveTransportMessageKind.READ
        )
        if self.message_kind is not expected_kind:
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport message kind must match payload type"
            )
        principal = self.authenticated_principal
        if self.payload.principal_id != principal.principal_id:
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport principal must match authenticated assertion"
            )
        if self.payload.correlation_id != principal.correlation_id:
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport correlation must match authenticated assertion"
            )
        if self.payload.requested_at < principal.issued_at:
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport payload cannot predate authentication assertion"
            )
        if self.payload.requested_at > principal.expires_at:
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport payload cannot postdate authentication expiry"
            )
        if self.received_at < self.payload.requested_at:
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport receipt cannot predate payload request"
            )
        if self.received_at > principal.expires_at:
            raise ExecutiveTransportEnvelopeValidationError(
                "executive transport receipt cannot postdate authentication expiry"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.envelope_id.logical_values(),
            self.schema_version.logical_values(),
            self.surface.value,
            self.message_kind.value,
            self.authenticated_principal.logical_values(),
            self.payload.logical_values(),
            self.received_at.isoformat(),
        )


def build_executive_control_transport_envelope(
    authenticated_principal: AuthenticatedExecutivePrincipal,
    intent: ExecutiveControlIntent,
    *,
    envelope_id: ExecutiveTransportEnvelopeId,
    schema_version: ExecutiveTransportSchemaVersion,
    surface: ExecutiveTransportSurface,
    received_at: datetime,
) -> Result[ExecutiveTransportEnvelope, ExecutiveTransportEnvelopeError]:
    if not isinstance(intent, ExecutiveControlIntent):
        return Failure(
            ExecutiveTransportEnvelopeValidationError(
                "control transport builder requires ExecutiveControlIntent"
            )
        )
    try:
        return Success(
            ExecutiveTransportEnvelope(
                envelope_id=envelope_id,
                schema_version=schema_version,
                surface=surface,
                message_kind=ExecutiveTransportMessageKind.CONTROL,
                authenticated_principal=authenticated_principal,
                payload=intent,
                received_at=received_at,
            )
        )
    except ExecutiveTransportEnvelopeError as error:
        return Failure(error)


def build_executive_read_transport_envelope(
    authenticated_principal: AuthenticatedExecutivePrincipal,
    request: ExecutiveReadRequest,
    *,
    envelope_id: ExecutiveTransportEnvelopeId,
    schema_version: ExecutiveTransportSchemaVersion,
    surface: ExecutiveTransportSurface,
    received_at: datetime,
) -> Result[ExecutiveTransportEnvelope, ExecutiveTransportEnvelopeError]:
    if not isinstance(request, ExecutiveReadRequest):
        return Failure(
            ExecutiveTransportEnvelopeValidationError(
                "read transport builder requires ExecutiveReadRequest"
            )
        )
    try:
        return Success(
            ExecutiveTransportEnvelope(
                envelope_id=envelope_id,
                schema_version=schema_version,
                surface=surface,
                message_kind=ExecutiveTransportMessageKind.READ,
                authenticated_principal=authenticated_principal,
                payload=request,
                received_at=received_at,
            )
        )
    except ExecutiveTransportEnvelopeError as error:
        return Failure(error)
