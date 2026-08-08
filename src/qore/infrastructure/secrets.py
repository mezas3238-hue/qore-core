from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from re import fullmatch
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.adapter_configuration import AdapterSecretName
from qore.infrastructure.ports import ExternalPortError, ExternalRequestMetadata
from qore.kernel.result import Result

_RESERVED_SECRET_METADATA_KEYS = frozenset(
    {"password", "secret", "secret_value", "token", "value"}
)
_SENSITIVE_SECRET_KEY_PARTS = frozenset(
    {"api-key", "api_key", "credential", "password", "secret", "token"}
)
_SUSPICIOUS_INLINE_SECRET_PREFIXES = (
    "aki",
    "bearer-",
    "ghp_",
    "github_pat_",
    "sk-",
    "xox",
)
_SUSPICIOUS_INLINE_SECRET_MARKERS = (
    "-----begin",
    "=",
)


class SecretBoundaryError(ExternalPortError):
    """Base error for secret-reference boundary contracts."""

    __slots__ = ()


class SecretBoundaryValidationError(SecretBoundaryError):
    """Violation of a secret-reference contract invariant."""

    __slots__ = ()


def _validate_secret_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int, UUID)):
        return
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise SecretBoundaryValidationError("secret metadata floats must be finite")
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_secret_metadata_value(item)
        return
    raise SecretBoundaryValidationError(
        "secret metadata values must be immutable scalars or tuples"
    )


def _validate_secret_metadata(
    values: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(values, Mapping):
        raise SecretBoundaryValidationError("secret metadata must be a mapping")
    for key, value in values.items():
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise SecretBoundaryValidationError(
                "secret metadata keys must use lowercase letters, digits, dots, "
                "underscores, or hyphens"
            )
        if key in _RESERVED_SECRET_METADATA_KEYS:
            raise SecretBoundaryValidationError(
                f"reserved secret metadata key: {key}"
            )
        if any(part in key for part in _SENSITIVE_SECRET_KEY_PARTS):
            raise SecretBoundaryValidationError(
                "secret metadata must not contain secret-like keys"
            )
        _validate_secret_metadata_value(value)
    ordered = {key: values[key] for key in sorted(values)}
    return MappingProxyType(ordered)


def _looks_like_inline_secret(value: str) -> bool:
    normalized = value.lower()
    return any(
        normalized.startswith(prefix)
        for prefix in _SUSPICIOUS_INLINE_SECRET_PREFIXES
    ) or any(marker in normalized for marker in _SUSPICIOUS_INLINE_SECRET_MARKERS)


@dataclass(frozen=True, slots=True, repr=False)
class SecretRefId:
    """Explicit identity of a secret reference, not a secret value."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise SecretBoundaryValidationError("secret ref id must be a UUID")

    def __repr__(self) -> str:
        return f"SecretRefId({self.value})"

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True, repr=False)
class SecretExternalReference:
    """Canonical external reference path for a future secret resolver."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise SecretBoundaryValidationError(
                "secret external reference must be a non-empty string"
            )
        if self.value != self.value.strip():
            raise SecretBoundaryValidationError(
                "secret external reference must not include surrounding whitespace"
            )
        if fullmatch(r"[a-z][a-z0-9._/-]*", self.value) is None:
            raise SecretBoundaryValidationError(
                "secret external reference must use canonical lowercase path syntax"
            )
        if "/" not in self.value or "//" in self.value:
            raise SecretBoundaryValidationError(
                "secret external reference must be a namespaced path"
            )
        if _looks_like_inline_secret(self.value):
            raise SecretBoundaryValidationError(
                "secret external reference looks like an inline secret value"
            )

    def __repr__(self) -> str:
        return f"SecretExternalReference({self.value!r})"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True, repr=False)
class SecretRef:
    """Opaque secret reference that never stores a sensitive value."""

    ref_id: SecretRefId
    name: AdapterSecretName
    external_reference: SecretExternalReference
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.ref_id, SecretRefId):
            raise SecretBoundaryValidationError("secret ref ref_id must be SecretRefId")
        if not isinstance(self.name, AdapterSecretName):
            raise SecretBoundaryValidationError(
                "secret ref name must be AdapterSecretName"
            )
        if not isinstance(self.external_reference, SecretExternalReference):
            raise SecretBoundaryValidationError(
                "secret ref external_reference must be SecretExternalReference"
            )
        object.__setattr__(
            self,
            "metadata",
            _validate_secret_metadata(self.metadata),
        )

    def __repr__(self) -> str:
        return (
            "SecretRef("
            f"ref_id={self.ref_id}, "
            f"name={self.name.value!r}, "
            f"external_reference={self.external_reference.value!r})"
        )

    def __str__(self) -> str:
        return f"secret-ref:{self.name.value}:{self.ref_id}"

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.ref_id.value),
            self.name.value,
            self.external_reference.value,
            tuple(self.metadata.items()),
        )


class SecretNotFoundError(SecretBoundaryError):
    """Typed error for an absent secret reference."""

    __slots__ = ()

    def __init__(self, ref: SecretRef) -> None:
        if not isinstance(ref, SecretRef):
            raise SecretBoundaryValidationError("secret not found ref must be SecretRef")
        super().__init__(f"secret reference not found: {ref}")


class SecretAccessDeniedError(SecretBoundaryError):
    """Typed error for denied access to a secret reference."""

    __slots__ = ()

    def __init__(self, ref: SecretRef) -> None:
        if not isinstance(ref, SecretRef):
            raise SecretBoundaryValidationError("secret denied ref must be SecretRef")
        super().__init__(f"secret reference access denied: {ref}")


class SecretInvalidError(SecretBoundaryError):
    """Typed error for an invalid secret reference."""

    __slots__ = ()

    def __init__(self, ref: SecretRef) -> None:
        if not isinstance(ref, SecretRef):
            raise SecretBoundaryValidationError("secret invalid ref must be SecretRef")
        super().__init__(f"secret reference invalid: {ref}")


@dataclass(frozen=True, slots=True, repr=False)
class SecretResolutionRequest:
    """Request to validate or resolve a secret reference without exposing a value."""

    ref: SecretRef

    def __post_init__(self) -> None:
        if not isinstance(self.ref, SecretRef):
            raise SecretBoundaryValidationError(
                "secret resolution request ref must be SecretRef"
            )

    def __repr__(self) -> str:
        return f"SecretResolutionRequest(ref={self.ref})"

    def __str__(self) -> str:
        return f"secret-resolution-request:{self.ref.name.value}:{self.ref.ref_id}"

    def logical_values(self) -> tuple[object, ...]:
        return self.ref.logical_values()


@dataclass(frozen=True, slots=True, repr=False)
class SecretResolutionReceipt:
    """Receipt that a secret reference was accepted without carrying the value."""

    ref: SecretRef
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.ref, SecretRef):
            raise SecretBoundaryValidationError(
                "secret resolution receipt ref must be SecretRef"
            )
        object.__setattr__(
            self,
            "metadata",
            _validate_secret_metadata(self.metadata),
        )

    def __repr__(self) -> str:
        return f"SecretResolutionReceipt(ref={self.ref})"

    def __str__(self) -> str:
        return f"secret-resolution-receipt:{self.ref.name.value}:{self.ref.ref_id}"

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.ref.logical_values(),
            tuple(self.metadata.items()),
        )


class SecretResolverBoundary(Protocol):
    """Structural future boundary for secret resolution without implementation."""

    def resolve(
        self,
        request: SecretResolutionRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[SecretResolutionReceipt, SecretBoundaryError]:
        """Resolve or validate a secret reference without exposing the value."""
        ...
