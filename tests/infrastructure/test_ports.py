from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId, DomainMetadataValue
from qore.infrastructure.ports import (
    AdapterId,
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    PortUnavailableError,
    PortValidationError,
    ReadExternalPort,
    SourceId,
    WriteExternalPort,
)
from qore.kernel.result import Failure, Result, Success

_TIMESTAMP = datetime(2026, 8, 7, 22, 0, tzinfo=UTC)
_ADAPTER_ID = AdapterId(UUID("a1000000-0000-0000-0000-000000000001"))
_SOURCE_ID = SourceId(UUID("a1000000-0000-0000-0000-000000000002"))
_CORRELATION = CorrelationId(UUID("a1000000-0000-0000-0000-000000000003"))
_CAUSATION = CausationId(UUID("a1000000-0000-0000-0000-000000000004"))


def _descriptor() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=_SOURCE_ID,
        port_name=PortName("reference.external"),
    )


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
        attributes={"b": 2, "a": ("stable", 1)},
    )


class FakeReadPort:
    def __init__(self, descriptor: ExternalSourceDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self._descriptor

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        return Success(
            ExternalHealth(
                descriptor=self.descriptor,
                availability=PortAvailability.AVAILABLE,
                checked_at=checked_at,
            )
        )

    def read(
        self,
        request: str,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[int, ExternalPortError]:
        del metadata
        if request == "unavailable":
            return Failure(PortUnavailableError("reference source unavailable"))
        return Success(len(request))


class FakeWritePort:
    def __init__(self, descriptor: ExternalSourceDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self._descriptor

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        return Success(
            ExternalHealth(
                descriptor=self.descriptor,
                availability=PortAvailability.AVAILABLE,
                checked_at=checked_at,
            )
        )

    def write(
        self,
        request: int,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[str, ExternalPortError]:
        del metadata
        return Success(str(request))


def _read_through(
    port: ReadExternalPort[str, int],
    value: str,
) -> Result[int, ExternalPortError]:
    return port.read(value, metadata=_metadata())


def _write_through(
    port: WriteExternalPort[int, str],
    value: int,
) -> Result[str, ExternalPortError]:
    return port.write(value, metadata=_metadata())


def test_identity_and_port_name_are_explicit_and_validated() -> None:
    descriptor = _descriptor()

    assert descriptor.adapter_id == _ADAPTER_ID
    assert descriptor.source_id == _SOURCE_ID
    assert descriptor.port_name == PortName("reference.external")

    with pytest.raises(PortValidationError, match="adapter id"):
        AdapterId(cast(UUID, "not-a-uuid"))
    with pytest.raises(PortValidationError, match="source id"):
        SourceId(cast(UUID, "not-a-uuid"))
    with pytest.raises(PortValidationError, match="port name"):
        PortName("Reference External")


def test_descriptor_keeps_adapter_and_source_as_distinct_types() -> None:
    shared_value = UUID("a1000000-0000-0000-0000-000000000010")
    descriptor = ExternalSourceDescriptor(
        adapter_id=AdapterId(shared_value),
        source_id=SourceId(shared_value),
        port_name=PortName("reference.external"),
    )

    assert isinstance(descriptor.adapter_id, AdapterId)
    assert isinstance(descriptor.source_id, SourceId)

    with pytest.raises(PortValidationError, match="adapter_id"):
        ExternalSourceDescriptor(
            adapter_id=cast(AdapterId, object()),
            source_id=_SOURCE_ID,
            port_name=PortName("reference.external"),
        )


def test_request_metadata_is_sorted_defensively_copied_and_immutable() -> None:
    source: dict[str, DomainMetadataValue] = {"z": 3, "a": ("x", 1)}
    metadata = ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
        attributes=source,
    )
    source["later"] = 5

    assert tuple(metadata.attributes) == ("a", "z")
    assert "later" not in metadata.attributes
    with pytest.raises(TypeError):
        metadata.attributes["x"] = 1  # type: ignore[index]


def test_request_metadata_rejects_reserved_mutable_and_non_finite_values() -> None:
    with pytest.raises(PortValidationError, match="reserved"):
        ExternalRequestMetadata(
            correlation_id=_CORRELATION,
            attributes={"correlation_id": "forbidden"},
        )
    with pytest.raises(PortValidationError, match="immutable"):
        ExternalRequestMetadata(
            correlation_id=_CORRELATION,
            attributes={"payload": cast(DomainMetadataValue, [1, 2])},
        )
    with pytest.raises(PortValidationError, match="finite"):
        ExternalRequestMetadata(
            correlation_id=_CORRELATION,
            attributes={"value": float("nan")},
        )


def test_health_requires_explicit_timezone_and_coherent_availability_message() -> None:
    available = ExternalHealth(
        descriptor=_descriptor(),
        availability=PortAvailability.AVAILABLE,
        checked_at=_TIMESTAMP,
        details={"latency_class": "reference"},
    )
    degraded = ExternalHealth(
        descriptor=_descriptor(),
        availability=PortAvailability.DEGRADED,
        checked_at=_TIMESTAMP,
        message="reference degradation",
    )

    assert available.availability is PortAvailability.AVAILABLE
    assert degraded.message == "reference degradation"

    with pytest.raises(PortValidationError, match="timezone-aware"):
        ExternalHealth(
            descriptor=_descriptor(),
            availability=PortAvailability.AVAILABLE,
            checked_at=datetime(2026, 8, 7, 22, 0),
        )
    with pytest.raises(PortValidationError, match="must not carry"):
        ExternalHealth(
            descriptor=_descriptor(),
            availability=PortAvailability.AVAILABLE,
            checked_at=_TIMESTAMP,
            message="contradiction",
        )
    with pytest.raises(PortValidationError, match="must include"):
        ExternalHealth(
            descriptor=_descriptor(),
            availability=PortAvailability.UNAVAILABLE,
            checked_at=_TIMESTAMP,
        )


def test_health_details_are_defensively_copied_and_logical_values_are_stable() -> None:
    details: dict[str, DomainMetadataValue] = {"z": 2, "a": (1, "x")}
    first = ExternalHealth(
        descriptor=_descriptor(),
        availability=PortAvailability.AVAILABLE,
        checked_at=_TIMESTAMP,
        details=details,
    )
    details["later"] = 3
    second = ExternalHealth(
        descriptor=_descriptor(),
        availability=PortAvailability.AVAILABLE,
        checked_at=_TIMESTAMP,
        details={"a": (1, "x"), "z": 2},
    )

    assert "later" not in first.details
    assert first.logical_values() == second.logical_values()


def test_read_protocol_is_structural_and_uses_typed_result() -> None:
    port = FakeReadPort(_descriptor())

    success = _read_through(port, "qore")
    failure = _read_through(port, "unavailable")
    health = port.health(checked_at=_TIMESTAMP, metadata=_metadata())

    assert isinstance(success, Success)
    assert success.value == 4
    assert isinstance(failure, Failure)
    assert isinstance(failure.error, PortUnavailableError)
    assert isinstance(health, Success)
    assert health.value.descriptor is port.descriptor


def test_write_protocol_is_structural_and_uses_typed_result() -> None:
    port = FakeWritePort(_descriptor())
    result = _write_through(port, 42)

    assert isinstance(result, Success)
    assert result.value == "42"


def test_contracts_never_generate_identity_or_time_implicitly() -> None:
    descriptor = _descriptor()
    metadata = _metadata()
    health = ExternalHealth(
        descriptor=descriptor,
        availability=PortAvailability.AVAILABLE,
        checked_at=_TIMESTAMP,
    )

    assert descriptor.adapter_id is _ADAPTER_ID
    assert descriptor.source_id is _SOURCE_ID
    assert metadata.correlation_id is _CORRELATION
    assert metadata.causation_id is _CAUSATION
    assert health.checked_at is _TIMESTAMP
