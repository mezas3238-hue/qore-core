from __future__ import annotations

from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId, DomainMetadataValue
from qore.infrastructure.adapter_configuration import AdapterSecretName
from qore.infrastructure.ports import ExternalPortError, ExternalRequestMetadata
from qore.infrastructure.secrets import (
    SecretAccessDeniedError,
    SecretBoundaryError,
    SecretBoundaryValidationError,
    SecretExternalReference,
    SecretInvalidError,
    SecretNotFoundError,
    SecretRef,
    SecretRefId,
    SecretResolutionReceipt,
    SecretResolutionRequest,
    SecretResolverBoundary,
)
from qore.kernel.result import Success

_RAW_SECRET = "super-secret-value-123"
_SECRET_ID = SecretRefId(UUID("f5000000-0000-0000-0000-000000000001"))
_SECRET_REFERENCE = SecretExternalReference("vault/qore/reference/api-token")


class _Resolver:
    def __init__(self, receipt: SecretResolutionReceipt) -> None:
        self._receipt = receipt

    def resolve(
        self,
        request: SecretResolutionRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Success[SecretResolutionReceipt]:
        assert request.ref is self._receipt.ref
        assert isinstance(metadata, ExternalRequestMetadata)
        return Success(self._receipt)


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=CorrelationId(UUID("f5000000-0000-0000-0000-000000000010"))
    )


def _secret_ref() -> SecretRef:
    return SecretRef(
        ref_id=_SECRET_ID,
        name=AdapterSecretName("api-token"),
        external_reference=_SECRET_REFERENCE,
        metadata={"purpose": "market-data", "regions": ("ny", "ldn")},
    )


def test_secret_ref_is_canonical_and_never_carries_secret_value() -> None:
    ref = _secret_ref()

    assert ref.logical_values() == (
        "f5000000-0000-0000-0000-000000000001",
        "api-token",
        "vault/qore/reference/api-token",
        (("purpose", "market-data"), ("regions", ("ny", "ldn"))),
    )
    assert str(ref) == (
        "secret-ref:api-token:f5000000-0000-0000-0000-000000000001"
    )
    for surface in (repr(ref), str(ref), repr(ref.logical_values())):
        assert _RAW_SECRET not in surface


def test_secret_resolution_request_and_receipt_do_not_expose_values() -> None:
    ref = _secret_ref()
    request = SecretResolutionRequest(ref)
    receipt = SecretResolutionReceipt(ref, metadata={"status": "accepted"})

    assert request.logical_values() == ref.logical_values()
    assert receipt.logical_values() == (
        ref.logical_values(),
        (("status", "accepted"),),
    )
    for surface in (
        repr(request),
        str(request),
        repr(request.logical_values()),
        repr(receipt),
        str(receipt),
        repr(receipt.logical_values()),
    ):
        assert _RAW_SECRET not in surface


def test_secret_errors_are_typed_and_do_not_leak_values() -> None:
    ref = _secret_ref()

    errors = (
        SecretNotFoundError(ref),
        SecretAccessDeniedError(ref),
        SecretInvalidError(ref),
    )
    for error in errors:
        assert isinstance(error, SecretBoundaryError)
        assert isinstance(error, ExternalPortError)
        assert _RAW_SECRET not in str(error)
        assert ref.name.value in str(error)

    with pytest.raises(SecretBoundaryValidationError, match="SecretRef"):
        SecretNotFoundError(cast(SecretRef, object()))
    with pytest.raises(SecretBoundaryValidationError, match="SecretRef"):
        SecretAccessDeniedError(cast(SecretRef, object()))
    with pytest.raises(SecretBoundaryValidationError, match="SecretRef"):
        SecretInvalidError(cast(SecretRef, object()))


def test_secret_reference_rejects_inline_or_malformed_values() -> None:
    with pytest.raises(SecretBoundaryValidationError, match="non-empty"):
        SecretExternalReference("")
    with pytest.raises(SecretBoundaryValidationError, match="whitespace"):
        SecretExternalReference(" vault/qore/api-token")
    with pytest.raises(SecretBoundaryValidationError, match="lowercase"):
        SecretExternalReference("vault/QORE/api-token")
    with pytest.raises(SecretBoundaryValidationError, match="namespaced"):
        SecretExternalReference("super-secret-value")
    with pytest.raises(SecretBoundaryValidationError, match="inline secret"):
        SecretExternalReference("sk-inline/qore/api-token")


def test_secret_metadata_is_immutable_and_rejects_sensitive_keys() -> None:
    ref = _secret_ref()

    with pytest.raises(TypeError):
        cast(dict[str, DomainMetadataValue], ref.metadata)["new"] = "value"

    with pytest.raises(SecretBoundaryValidationError, match="secret-like"):
        SecretRef(
            ref_id=_SECRET_ID,
            name=AdapterSecretName("api-token"),
            external_reference=_SECRET_REFERENCE,
            metadata={"api_key": "inline"},
        )
    with pytest.raises(SecretBoundaryValidationError, match="reserved"):
        SecretRef(
            ref_id=_SECRET_ID,
            name=AdapterSecretName("api-token"),
            external_reference=_SECRET_REFERENCE,
            metadata={"value": "inline"},
        )
    with pytest.raises(SecretBoundaryValidationError, match="finite"):
        SecretRef(
            ref_id=_SECRET_ID,
            name=AdapterSecretName("api-token"),
            external_reference=_SECRET_REFERENCE,
            metadata={"latency": float("nan")},
        )
    with pytest.raises(SecretBoundaryValidationError, match="immutable"):
        SecretRef(
            ref_id=_SECRET_ID,
            name=AdapterSecretName("api-token"),
            external_reference=_SECRET_REFERENCE,
            metadata={"payload": cast(DomainMetadataValue, object())},
        )


def test_secret_contracts_reject_runtime_type_bypasses() -> None:
    with pytest.raises(SecretBoundaryValidationError, match="UUID"):
        SecretRefId(cast(UUID, "not-a-uuid"))
    with pytest.raises(SecretBoundaryValidationError, match="ref_id"):
        SecretRef(
            ref_id=cast(SecretRefId, object()),
            name=AdapterSecretName("api-token"),
            external_reference=_SECRET_REFERENCE,
        )
    with pytest.raises(SecretBoundaryValidationError, match="name"):
        SecretRef(
            ref_id=_SECRET_ID,
            name=cast(AdapterSecretName, object()),
            external_reference=_SECRET_REFERENCE,
        )
    with pytest.raises(SecretBoundaryValidationError, match="external_reference"):
        SecretRef(
            ref_id=_SECRET_ID,
            name=AdapterSecretName("api-token"),
            external_reference=cast(SecretExternalReference, object()),
        )
    with pytest.raises(SecretBoundaryValidationError, match="mapping"):
        SecretRef(
            ref_id=_SECRET_ID,
            name=AdapterSecretName("api-token"),
            external_reference=_SECRET_REFERENCE,
            metadata=cast(dict[str, DomainMetadataValue], object()),
        )
    with pytest.raises(SecretBoundaryValidationError, match="SecretRef"):
        SecretResolutionRequest(cast(SecretRef, object()))
    with pytest.raises(SecretBoundaryValidationError, match="SecretRef"):
        SecretResolutionReceipt(cast(SecretRef, object()))


def test_secret_resolver_boundary_is_structural_without_secret_value() -> None:
    ref = _secret_ref()
    receipt = SecretResolutionReceipt(ref, metadata={"status": "accepted"})
    resolver: SecretResolverBoundary = _Resolver(receipt)

    result = resolver.resolve(SecretResolutionRequest(ref), metadata=_metadata())

    assert isinstance(result, Success)
    assert result.value is receipt
    assert _RAW_SECRET not in repr(result.value.logical_values())


def test_public_exports_include_secret_boundary_contracts() -> None:
    import qore.infrastructure as infrastructure

    assert infrastructure.SecretAccessDeniedError is SecretAccessDeniedError
    assert infrastructure.SecretBoundaryError is SecretBoundaryError
    assert issubclass(SecretBoundaryError, ExternalPortError)
    assert (
        infrastructure.SecretBoundaryValidationError is SecretBoundaryValidationError
    )
    assert infrastructure.SecretExternalReference is SecretExternalReference
    assert infrastructure.SecretInvalidError is SecretInvalidError
    assert infrastructure.SecretNotFoundError is SecretNotFoundError
    assert infrastructure.SecretRef is SecretRef
    assert infrastructure.SecretRefId is SecretRefId
    assert infrastructure.SecretResolutionReceipt is SecretResolutionReceipt
    assert infrastructure.SecretResolutionRequest is SecretResolutionRequest
    assert infrastructure.SecretResolverBoundary is SecretResolverBoundary
