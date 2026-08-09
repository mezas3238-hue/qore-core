from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.executive_transport_envelope import (
    ExecutiveTransportEnvelope,
    ExecutiveTransportMessageKind,
    ExecutiveTransportSurface,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveClientSurfaceError(DomainError):
    """Base error for platform-neutral executive client-surface contracts."""

    __slots__ = ()


class ExecutiveClientSurfaceValidationError(ExecutiveClientSurfaceError):
    """A client-surface value violates a deterministic boundary invariant."""

    __slots__ = ()


class ExecutiveClientPlatform(StrEnum):
    """Presentation platforms authorized to compose through MISSION-04."""

    DESKTOP = "desktop"
    IOS = "ios"
    ANDROID = "android"


@dataclass(frozen=True, slots=True)
class ExecutiveClientSurfaceId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveClientSurfaceValidationError(
                "executive client surface id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveClientVersion:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z0-9][a-z0-9._-]*", self.value
        ) is None:
            raise ExecutiveClientSurfaceValidationError(
                "executive client version must use canonical syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def expected_transport_surface(
    platform: ExecutiveClientPlatform,
) -> ExecutiveTransportSurface:
    if not isinstance(platform, ExecutiveClientPlatform):
        raise ExecutiveClientSurfaceValidationError(
            "executive client platform must be ExecutiveClientPlatform"
        )
    if platform is ExecutiveClientPlatform.DESKTOP:
        return ExecutiveTransportSurface.CEO_COMMAND_CENTER
    return ExecutiveTransportSurface.MOBILE


@dataclass(frozen=True, slots=True)
class ExecutiveClientSurface:
    """Secret-free descriptor for one external CEO presentation surface.

    The descriptor binds Desktop/iOS/Android presentation to an already-existing
    MISSION-04 transport surface. It intentionally contains no Core, provider,
    broker, credential, socket, storage or UI-framework object.
    """

    surface_id: ExecutiveClientSurfaceId
    platform: ExecutiveClientPlatform
    client_version: ExecutiveClientVersion
    transport_surface: ExecutiveTransportSurface
    allowed_message_kinds: tuple[ExecutiveTransportMessageKind, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.surface_id, ExecutiveClientSurfaceId):
            raise ExecutiveClientSurfaceValidationError(
                "executive client surface requires ExecutiveClientSurfaceId"
            )
        if not isinstance(self.platform, ExecutiveClientPlatform):
            raise ExecutiveClientSurfaceValidationError(
                "executive client surface requires ExecutiveClientPlatform"
            )
        if not isinstance(self.client_version, ExecutiveClientVersion):
            raise ExecutiveClientSurfaceValidationError(
                "executive client surface requires ExecutiveClientVersion"
            )
        if not isinstance(self.transport_surface, ExecutiveTransportSurface):
            raise ExecutiveClientSurfaceValidationError(
                "executive client surface requires ExecutiveTransportSurface"
            )
        expected_surface = expected_transport_surface(self.platform)
        if self.transport_surface is not expected_surface:
            raise ExecutiveClientSurfaceValidationError(
                "executive client platform must bind to its approved transport surface"
            )
        if not isinstance(self.allowed_message_kinds, tuple) or not self.allowed_message_kinds:
            raise ExecutiveClientSurfaceValidationError(
                "executive client surface requires explicit allowed message kinds"
            )
        if any(
            not isinstance(item, ExecutiveTransportMessageKind)
            for item in self.allowed_message_kinds
        ):
            raise ExecutiveClientSurfaceValidationError(
                "allowed message kinds must contain ExecutiveTransportMessageKind values"
            )
        if len(set(self.allowed_message_kinds)) != len(self.allowed_message_kinds):
            raise ExecutiveClientSurfaceValidationError(
                "allowed message kinds must not contain duplicates"
            )
        object.__setattr__(
            self,
            "allowed_message_kinds",
            tuple(sorted(self.allowed_message_kinds, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.surface_id.logical_values(),
            self.platform.value,
            self.client_version.logical_values(),
            self.transport_surface.value,
            tuple(item.value for item in self.allowed_message_kinds),
        )


def build_executive_client_surface(
    *,
    surface_id: ExecutiveClientSurfaceId,
    platform: ExecutiveClientPlatform,
    client_version: ExecutiveClientVersion,
    allowed_message_kinds: tuple[ExecutiveTransportMessageKind, ...],
) -> Result[ExecutiveClientSurface, ExecutiveClientSurfaceError]:
    """Build a surface descriptor with the only approved transport binding."""

    try:
        return Success(
            ExecutiveClientSurface(
                surface_id=surface_id,
                platform=platform,
                client_version=client_version,
                transport_surface=expected_transport_surface(platform),
                allowed_message_kinds=allowed_message_kinds,
            )
        )
    except ExecutiveClientSurfaceError as error:
        return Failure(error)


def validate_executive_client_envelope_binding(
    surface: ExecutiveClientSurface,
    envelope: ExecutiveTransportEnvelope,
) -> Result[ExecutiveTransportEnvelope, ExecutiveClientSurfaceError]:
    """Fail closed unless an existing MISSION-04 envelope fits the client surface."""

    if not isinstance(surface, ExecutiveClientSurface):
        return Failure(
            ExecutiveClientSurfaceValidationError(
                "client envelope binding requires ExecutiveClientSurface"
            )
        )
    if not isinstance(envelope, ExecutiveTransportEnvelope):
        return Failure(
            ExecutiveClientSurfaceValidationError(
                "client envelope binding requires ExecutiveTransportEnvelope"
            )
        )
    if envelope.surface is not surface.transport_surface:
        return Failure(
            ExecutiveClientSurfaceValidationError(
                "executive envelope transport surface does not match client surface"
            )
        )
    if envelope.message_kind not in surface.allowed_message_kinds:
        return Failure(
            ExecutiveClientSurfaceValidationError(
                "executive envelope message kind is not allowed by client surface"
            )
        )
    return Success(envelope)
