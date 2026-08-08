from __future__ import annotations

from dataclasses import fields
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.providers import (
    ProviderBoundaryError,
    ProviderBoundaryValidationError,
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderGovernanceBoundary,
    ProviderId,
    ProviderName,
)

_PROVIDER_ID = ProviderId(UUID("f3000000-0000-0000-0000-000000000001"))


class _StructuralProviderBoundary:
    def __init__(self, descriptor: ProviderDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def provider_descriptor(self) -> ProviderDescriptor:
        return self._descriptor

    @property
    def provider_capabilities(self) -> ProviderCapabilitySet:
        return self._descriptor.capabilities


def _capabilities() -> ProviderCapabilitySet:
    return ProviderCapabilitySet(
        (
            ProviderCapability.PERSISTENCE_READ,
            ProviderCapability.HEALTH,
            ProviderCapability.MARKET_DATA_READ,
        )
    )


def _descriptor(
    *,
    enablement: ProviderEnablement = ProviderEnablement.READ_ONLY,
) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("reference-provider"),
        enablement=enablement,
        capabilities=_capabilities(),
        metadata={"regions": ("ny", "ldn"), "tier": "reference"},
    )


def test_provider_descriptor_is_canonical_and_independent_from_source_identity() -> None:
    descriptor = _descriptor()

    assert descriptor.is_enabled is True
    assert descriptor.capabilities.logical_values() == (
        "health",
        "market_data.read",
        "persistence.read",
    )
    assert descriptor.logical_values() == (
        "f3000000-0000-0000-0000-000000000001",
        "reference-provider",
        "read_only",
        ("health", "market_data.read", "persistence.read"),
        (("regions", ("ny", "ldn")), ("tier", "reference")),
    )
    field_names = {field.name for field in fields(ProviderDescriptor)}
    assert "adapter_id" not in field_names
    assert "source_id" not in field_names


def test_disabled_provider_state_is_explicit() -> None:
    descriptor = _descriptor(enablement=ProviderEnablement.DISABLED)

    assert descriptor.is_enabled is False
    assert descriptor.logical_values()[2] == "disabled"


def test_provider_capability_set_is_validated_and_queryable() -> None:
    capabilities = _capabilities()

    assert capabilities.supports(ProviderCapability.HEALTH) is True
    assert capabilities.supports(ProviderCapability.PERSISTENCE_WRITE) is False

    with pytest.raises(
        ProviderBoundaryValidationError,
        match="must be a tuple",
    ):
        ProviderCapabilitySet(
            cast(tuple[ProviderCapability, ...], [ProviderCapability.HEALTH])
        )
    with pytest.raises(
        ProviderBoundaryValidationError,
        match="must not contain duplicates",
    ):
        ProviderCapabilitySet(
            (ProviderCapability.HEALTH, ProviderCapability.HEALTH)
        )
    with pytest.raises(
        ProviderBoundaryValidationError,
        match="entries must be ProviderCapability",
    ):
        ProviderCapabilitySet(cast(tuple[ProviderCapability, ...], (object(),)))
    with pytest.raises(
        ProviderBoundaryValidationError,
        match="check must use ProviderCapability",
    ):
        capabilities.supports(cast(ProviderCapability, object()))


def test_provider_descriptor_rejects_runtime_type_bypasses() -> None:
    with pytest.raises(ProviderBoundaryValidationError, match="provider id"):
        ProviderId(cast(UUID, "not-a-uuid"))
    with pytest.raises(ProviderBoundaryValidationError, match="provider name"):
        ProviderName("ReferenceProvider")
    with pytest.raises(ProviderBoundaryValidationError, match="provider_id"):
        ProviderDescriptor(
            provider_id=cast(ProviderId, object()),
            provider_name=ProviderName("reference-provider"),
            enablement=ProviderEnablement.READ_ONLY,
            capabilities=_capabilities(),
        )
    with pytest.raises(ProviderBoundaryValidationError, match="provider_name"):
        ProviderDescriptor(
            provider_id=_PROVIDER_ID,
            provider_name=cast(ProviderName, object()),
            enablement=ProviderEnablement.READ_ONLY,
            capabilities=_capabilities(),
        )
    with pytest.raises(ProviderBoundaryValidationError, match="enablement"):
        ProviderDescriptor(
            provider_id=_PROVIDER_ID,
            provider_name=ProviderName("reference-provider"),
            enablement=cast(ProviderEnablement, "read_only"),
            capabilities=_capabilities(),
        )
    with pytest.raises(ProviderBoundaryValidationError, match="capabilities"):
        ProviderDescriptor(
            provider_id=_PROVIDER_ID,
            provider_name=ProviderName("reference-provider"),
            enablement=ProviderEnablement.READ_ONLY,
            capabilities=cast(ProviderCapabilitySet, (ProviderCapability.HEALTH,)),
        )


def test_provider_metadata_is_canonical_and_rejects_mutable_values() -> None:
    descriptor = ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("reference-provider"),
        enablement=ProviderEnablement.SIMULATION,
        capabilities=_capabilities(),
        metadata={"z": 1, "a": (UUID("f3000000-0000-0000-0000-000000000002"), None)},
    )

    assert tuple(descriptor.metadata.items()) == (
        ("a", (UUID("f3000000-0000-0000-0000-000000000002"), None)),
        ("z", 1),
    )

    with pytest.raises(ProviderBoundaryValidationError, match="non-empty"):
        ProviderDescriptor(
            provider_id=_PROVIDER_ID,
            provider_name=ProviderName("reference-provider"),
            enablement=ProviderEnablement.READ_ONLY,
            metadata={"": "invalid"},
        )
    with pytest.raises(ProviderBoundaryValidationError, match="reserved"):
        ProviderDescriptor(
            provider_id=_PROVIDER_ID,
            provider_name=ProviderName("reference-provider"),
            enablement=ProviderEnablement.READ_ONLY,
            metadata={"provider_id": "inline"},
        )
    with pytest.raises(ProviderBoundaryValidationError, match="immutable"):
        ProviderDescriptor(
            provider_id=_PROVIDER_ID,
            provider_name=ProviderName("reference-provider"),
            enablement=ProviderEnablement.READ_ONLY,
            metadata={"value": cast(DomainMetadataValue, [])},
        )
    with pytest.raises(ProviderBoundaryValidationError, match="finite"):
        ProviderDescriptor(
            provider_id=_PROVIDER_ID,
            provider_name=ProviderName("reference-provider"),
            enablement=ProviderEnablement.READ_ONLY,
            metadata={"value": float("nan")},
        )


def test_provider_governance_boundary_is_structural() -> None:
    descriptor = _descriptor()
    boundary: ProviderGovernanceBoundary = _StructuralProviderBoundary(descriptor)

    assert boundary.provider_descriptor is descriptor
    assert boundary.provider_capabilities is descriptor.capabilities


def test_public_exports_include_provider_boundary_contracts() -> None:
    import qore.infrastructure as infrastructure

    assert infrastructure.ProviderId is ProviderId
    assert infrastructure.ProviderName is ProviderName
    assert infrastructure.ProviderEnablement is ProviderEnablement
    assert infrastructure.ProviderCapability is ProviderCapability
    assert infrastructure.ProviderCapabilitySet is ProviderCapabilitySet
    assert infrastructure.ProviderDescriptor is ProviderDescriptor
    assert infrastructure.ProviderGovernanceBoundary is ProviderGovernanceBoundary
    assert issubclass(infrastructure.ProviderBoundaryError, ExternalPortError)
    assert issubclass(
        infrastructure.ProviderBoundaryValidationError,
        ProviderBoundaryError,
    )
