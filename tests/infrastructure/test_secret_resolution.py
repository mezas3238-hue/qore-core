from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.adapter_configuration import AdapterSecretName
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.secret_resolution import (
    MappingSecretMaterialResolver,
    SecretMaterial,
    SecretMaterialResolution,
    SecretMaterialValidationError,
    resolve_supervised_secret_material,
)
from qore.infrastructure.secrets import (
    SecretExternalReference,
    SecretNotFoundError,
    SecretRef,
    SecretRefId,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 4, 30, tzinfo=UTC)
_CORRELATION_ID = CorrelationId(UUID("b9000000-0000-0000-0000-000000000001"))
_CAUSATION_ID = CausationId(UUID("b9000000-0000-0000-0000-000000000002"))
_REF_ID = SecretRefId(UUID("b9000000-0000-0000-0000-000000000003"))
_REFERENCE = SecretExternalReference("provider/reference/api-key")
_SECRET_BYTES = b"extremely-sensitive-test-material"


def _ref(reference: SecretExternalReference = _REFERENCE) -> SecretRef:
    return SecretRef(
        ref_id=_REF_ID,
        name=AdapterSecretName("api-key"),
        external_reference=reference,
    )


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"workflow": "phase-09"},
    )


def test_secret_material_repr_and_str_are_redacted() -> None:
    material = SecretMaterial(_SECRET_BYTES)

    assert repr(material) == "SecretMaterial(<redacted>)"
    assert str(material) == "<redacted-secret-material>"
    assert material.length == len(_SECRET_BYTES)
    assert _SECRET_BYTES.decode() not in repr(material)


def test_secret_material_requires_non_empty_bounded_bytes() -> None:
    with pytest.raises(SecretMaterialValidationError):
        SecretMaterial(b"")
    with pytest.raises(SecretMaterialValidationError):
        SecretMaterial(b"x" * 65537)


def test_mapping_resolver_repr_never_exposes_values() -> None:
    resolver = MappingSecretMaterialResolver({_REFERENCE: _SECRET_BYTES})

    assert repr(resolver) == "MappingSecretMaterialResolver(entries=1)"
    assert _SECRET_BYTES.decode() not in repr(resolver)


def test_supervised_resolution_returns_opaque_material() -> None:
    resolver = MappingSecretMaterialResolver({_REFERENCE: _SECRET_BYTES})

    result = resolve_supervised_secret_material(
        resolver,
        _ref(),
        metadata=_metadata(),
        resolved_at=_NOW,
    )

    assert isinstance(result, Success)
    resolution = result.value
    assert resolution.material.reveal_bytes() == _SECRET_BYTES
    assert _SECRET_BYTES.decode() not in repr(resolution)
    assert _SECRET_BYTES.decode() not in str(resolution)
    assert _SECRET_BYTES not in resolution.logical_values()
    assert resolution.logical_values() == (_ref().logical_values(), _NOW.isoformat())


def test_resolution_receipt_rejects_naive_timestamp() -> None:
    with pytest.raises(SecretMaterialValidationError):
        SecretMaterialResolution(
            ref=_ref(),
            material=SecretMaterial(_SECRET_BYTES),
            resolved_at=datetime(2026, 8, 8, 4, 30),
        )


def test_missing_secret_returns_safe_typed_error() -> None:
    missing = SecretExternalReference("provider/reference/missing")
    resolver = MappingSecretMaterialResolver({_REFERENCE: _SECRET_BYTES})

    result = resolve_supervised_secret_material(
        resolver,
        _ref(missing),
        metadata=_metadata(),
        resolved_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, SecretNotFoundError)
    assert _SECRET_BYTES.decode() not in str(result.error)


def test_material_is_not_value_comparable() -> None:
    first = SecretMaterial(b"same")
    second = SecretMaterial(b"same")

    assert first is not second
    assert first != second
