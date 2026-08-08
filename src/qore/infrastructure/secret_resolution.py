from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Protocol

from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.secrets import (
    SecretBoundaryError,
    SecretBoundaryValidationError,
    SecretExternalReference,
    SecretNotFoundError,
    SecretRef,
)
from qore.infrastructure.transport import (
    ExternalTransportError,
    ExternalTransportRequest,
    ExternalTransportResponse,
)
from qore.kernel.result import Failure, Result, Success


class SecretMaterialResolutionError(SecretBoundaryError):
    """Base error for supervised secret-material resolution."""

    __slots__ = ()


class SecretMaterialValidationError(SecretMaterialResolutionError):
    """Violation of a secret-material invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True, repr=False, eq=False)
class SecretMaterial:
    """Opaque resolved material usable only at the final external boundary."""

    _value: bytes = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self._value, bytes) or not self._value:
            raise SecretMaterialValidationError(
                "secret material must be non-empty bytes"
            )
        if len(self._value) > 65536:
            raise SecretMaterialValidationError(
                "secret material exceeds the maximum supported size"
            )

    def __repr__(self) -> str:
        return "SecretMaterial(<redacted>)"

    def __str__(self) -> str:
        return "<redacted-secret-material>"

    @property
    def length(self) -> int:
        """Return material length without exposing contents."""
        return len(self._value)

    def reveal_bytes(self) -> bytes:
        """Reveal bytes only to an explicitly secret-aware external boundary."""
        return self._value


@dataclass(frozen=True, slots=True, repr=False)
class SecretMaterialResolution:
    """Sanitized resolution receipt paired with opaque material."""

    ref: SecretRef
    material: SecretMaterial = field(repr=False, compare=False, hash=False)
    resolved_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.ref, SecretRef):
            raise SecretMaterialValidationError(
                "secret material resolution ref must be SecretRef"
            )
        if not isinstance(self.material, SecretMaterial):
            raise SecretMaterialValidationError(
                "secret material resolution material must be SecretMaterial"
            )
        if not isinstance(self.resolved_at, datetime):
            raise SecretMaterialValidationError(
                "secret material resolved_at must be a datetime"
            )
        if self.resolved_at.tzinfo is None or self.resolved_at.utcoffset() is None:
            raise SecretMaterialValidationError(
                "secret material resolved_at must be timezone-aware"
            )

    def __repr__(self) -> str:
        return (
            "SecretMaterialResolution("
            f"ref={self.ref}, resolved_at={self.resolved_at.isoformat()}, "
            "material=<redacted>)"
        )

    def __str__(self) -> str:
        return f"secret-material-resolution:{self.ref}:{self.resolved_at.isoformat()}"

    def logical_values(self) -> tuple[object, ...]:
        return (self.ref.logical_values(), self.resolved_at.isoformat())


class SecretMaterialResolverBoundary(Protocol):
    """Structural resolver allowed to produce opaque material for infrastructure."""

    def resolve_material(
        self,
        ref: SecretRef,
        *,
        metadata: ExternalRequestMetadata,
        resolved_at: datetime,
    ) -> Result[SecretMaterialResolution, SecretBoundaryError]:
        """Resolve one reference without exposing material in observable state."""
        ...


class SecretAuthenticatedTransportBoundary(Protocol):
    """Transport boundary that receives secret material separately from requests."""

    def execute_authenticated(
        self,
        request: ExternalTransportRequest,
        *,
        secret: SecretMaterial,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExternalTransportError]:
        """Execute one read-only request using opaque material out of band."""
        ...


@dataclass(frozen=True, slots=True, repr=False)
class MappingSecretMaterialResolver:
    """Injected deterministic resolver; callers own loading of the secret mapping."""

    _values: Mapping[SecretExternalReference, bytes] = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self._values, Mapping):
            raise SecretMaterialValidationError(
                "secret material resolver values must be a mapping"
            )
        copied: dict[SecretExternalReference, bytes] = {}
        for ref, value in self._values.items():
            if not isinstance(ref, SecretExternalReference):
                raise SecretMaterialValidationError(
                    "secret material resolver keys must be SecretExternalReference"
                )
            if not isinstance(value, bytes) or not value:
                raise SecretMaterialValidationError(
                    "secret material resolver values must be non-empty bytes"
                )
            copied[ref] = value
        object.__setattr__(self, "_values", MappingProxyType(copied))

    def __repr__(self) -> str:
        return f"MappingSecretMaterialResolver(entries={len(self._values)})"

    def resolve_material(
        self,
        ref: SecretRef,
        *,
        metadata: ExternalRequestMetadata,
        resolved_at: datetime,
    ) -> Result[SecretMaterialResolution, SecretBoundaryError]:
        if not isinstance(ref, SecretRef):
            return Failure(
                SecretBoundaryValidationError(
                    "secret material resolution requires SecretRef"
                )
            )
        if not isinstance(metadata, ExternalRequestMetadata):
            return Failure(
                SecretBoundaryValidationError(
                    "secret material resolution metadata must be ExternalRequestMetadata"
                )
            )
        try:
            material_bytes = self._values[ref.external_reference]
        except KeyError:
            return Failure(SecretNotFoundError(ref))
        try:
            resolution = SecretMaterialResolution(
                ref=ref,
                material=SecretMaterial(material_bytes),
                resolved_at=resolved_at,
            )
        except SecretBoundaryError as error:
            return Failure(error)
        return Success(resolution)


def resolve_supervised_secret_material(
    resolver: SecretMaterialResolverBoundary,
    ref: SecretRef,
    *,
    metadata: ExternalRequestMetadata,
    resolved_at: datetime,
) -> Result[SecretMaterialResolution, SecretBoundaryError]:
    """Resolve through an injected boundary and preserve typed failures."""
    if not isinstance(ref, SecretRef):
        return Failure(
            SecretBoundaryValidationError(
                "supervised secret material ref must be SecretRef"
            )
        )
    if not isinstance(metadata, ExternalRequestMetadata):
        return Failure(
            SecretBoundaryValidationError(
                "supervised secret material metadata must be ExternalRequestMetadata"
            )
        )
    return resolver.resolve_material(
        ref,
        metadata=metadata,
        resolved_at=resolved_at,
    )
