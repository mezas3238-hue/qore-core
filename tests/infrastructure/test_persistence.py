from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.persistence import (
    LoadPersistenceRequest,
    PersistenceConflictError,
    PersistenceKey,
    PersistencePort,
    PersistenceValidationError,
    PersistenceVersion,
    SavePersistenceRequest,
    StoredRecord,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure, Result, Success

_STORED_AT = datetime(2026, 8, 7, 22, 30, tzinfo=UTC)
_CHECKED_AT = datetime(2026, 8, 7, 22, 31, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("c1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("c1000000-0000-0000-0000-000000000002")),
    port_name=PortName("persistence.reference"),
)
_CORRELATION = CorrelationId(UUID("c1000000-0000-0000-0000-000000000003"))
_CAUSATION = CausationId(UUID("c1000000-0000-0000-0000-000000000004"))
_KEY = PersistenceKey("statistics", "snapshot/alpha")


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _record(
    *,
    version: PersistenceVersion = PersistenceVersion(0),
    value: str = "payload-v0",
) -> StoredRecord[str]:
    return StoredRecord(
        key=_KEY,
        version=version,
        value=value,
        source=_SOURCE,
        stored_at=_STORED_AT,
    )


class FakePersistencePort:
    def __init__(self, descriptor: ExternalSourceDescriptor) -> None:
        self._descriptor = descriptor
        self._records: dict[PersistenceKey, StoredRecord[str]] = {}

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

    def load(
        self,
        request: LoadPersistenceRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[StoredRecord[str] | None, ExternalPortError]:
        del metadata
        return Success(self._records.get(request.key))

    def save(
        self,
        request: SavePersistenceRequest[str],
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[PersistenceVersion, ExternalPortError]:
        del metadata
        current = self._records.get(request.record.key)
        if request.expected_version is None:
            if current is not None:
                return Failure(
                    PersistenceConflictError("record already exists")
                )
        elif current is None or current.version != request.expected_version:
            return Failure(
                PersistenceConflictError("expected version does not match")
            )
        self._records[request.record.key] = request.record
        return Success(request.record.version)


def _load_through(
    port: PersistencePort[str],
    request: LoadPersistenceRequest,
) -> Result[StoredRecord[str] | None, ExternalPortError]:
    return port.load(request, metadata=_metadata())


def _save_through(
    port: PersistencePort[str],
    request: SavePersistenceRequest[str],
) -> Result[PersistenceVersion, ExternalPortError]:
    return port.save(request, metadata=_metadata())


def test_persistence_key_is_canonical_and_explicit() -> None:
    key = PersistenceKey("specialized.knowledge", "record/ABC-123")

    assert key.logical_values() == ("specialized.knowledge", "record/ABC-123")

    with pytest.raises(PersistenceValidationError, match="namespace"):
        PersistenceKey("Statistics", "snapshot")
    with pytest.raises(PersistenceValidationError, match="namespace"):
        PersistenceKey("statistics data", "snapshot")
    with pytest.raises(PersistenceValidationError, match="canonical token"):
        PersistenceKey("statistics", "")
    with pytest.raises(PersistenceValidationError, match="canonical token"):
        PersistenceKey("statistics", "contains spaces")


def test_persistence_version_is_zero_based_explicit_and_bool_safe() -> None:
    version = PersistenceVersion(0)

    assert version.next() == PersistenceVersion(1)
    assert version == PersistenceVersion(0)

    with pytest.raises(PersistenceValidationError, match="non-negative int"):
        PersistenceVersion(-1)
    with pytest.raises(PersistenceValidationError, match="non-negative int"):
        PersistenceVersion(cast(int, True))


def test_stored_record_requires_persistence_source_and_explicit_time() -> None:
    record = _record()

    assert record.key is _KEY
    assert record.source is _SOURCE
    assert record.stored_at is _STORED_AT
    assert record.logical_values() == (
        _KEY.logical_values(),
        0,
        _SOURCE.logical_values(),
        _STORED_AT.isoformat(),
        "payload-v0",
    )

    wrong_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("c1000000-0000-0000-0000-000000000010")),
        source_id=SourceId(UUID("c1000000-0000-0000-0000-000000000011")),
        port_name=PortName("market-data.reference"),
    )
    with pytest.raises(PersistenceValidationError, match="persistence namespace"):
        StoredRecord(
            key=_KEY,
            version=PersistenceVersion(0),
            value="payload",
            source=wrong_source,
            stored_at=_STORED_AT,
        )
    with pytest.raises(PersistenceValidationError, match="timezone-aware"):
        StoredRecord(
            key=_KEY,
            version=PersistenceVersion(0),
            value="payload",
            source=_SOURCE,
            stored_at=datetime(2026, 8, 7, 22, 30),
        )


def test_stored_record_rejects_runtime_type_bypasses() -> None:
    with pytest.raises(PersistenceValidationError, match="key"):
        StoredRecord(
            key=cast(PersistenceKey, object()),
            version=PersistenceVersion(0),
            value="payload",
            source=_SOURCE,
            stored_at=_STORED_AT,
        )
    with pytest.raises(PersistenceValidationError, match="version"):
        StoredRecord(
            key=_KEY,
            version=cast(PersistenceVersion, object()),
            value="payload",
            source=_SOURCE,
            stored_at=_STORED_AT,
        )


def test_save_request_enforces_explicit_create_and_update_versions() -> None:
    create = SavePersistenceRequest(record=_record())
    update = SavePersistenceRequest(
        record=_record(version=PersistenceVersion(1), value="payload-v1"),
        expected_version=PersistenceVersion(0),
    )

    assert create.expected_version is None
    assert update.record.version == PersistenceVersion(1)

    with pytest.raises(PersistenceValidationError, match="version 0"):
        SavePersistenceRequest(
            record=_record(version=PersistenceVersion(1)),
        )
    with pytest.raises(PersistenceValidationError, match="expected_version \+ 1"):
        SavePersistenceRequest(
            record=_record(version=PersistenceVersion(2)),
            expected_version=PersistenceVersion(0),
        )
    with pytest.raises(PersistenceValidationError, match="expected_version"):
        SavePersistenceRequest(
            record=_record(),
            expected_version=cast(PersistenceVersion, object()),
        )


def test_load_request_rejects_runtime_type_bypass() -> None:
    request = LoadPersistenceRequest(_KEY)
    assert request.key is _KEY

    with pytest.raises(PersistenceValidationError, match="load request key"):
        LoadPersistenceRequest(cast(PersistenceKey, object()))


def test_persistence_port_represents_absence_without_failure() -> None:
    port = FakePersistencePort(_SOURCE)

    result = _load_through(port, LoadPersistenceRequest(_KEY))

    assert isinstance(result, Success)
    assert result.value is None


def test_persistence_port_is_structural_and_preserves_explicit_versions() -> None:
    port = FakePersistencePort(_SOURCE)
    create_request = SavePersistenceRequest(record=_record())

    created = _save_through(port, create_request)
    loaded = _load_through(port, LoadPersistenceRequest(_KEY))

    assert isinstance(created, Success)
    assert created.value == PersistenceVersion(0)
    assert isinstance(loaded, Success)
    assert loaded.value is create_request.record

    update_record = _record(
        version=PersistenceVersion(1),
        value="payload-v1",
    )
    updated = _save_through(
        port,
        SavePersistenceRequest(
            record=update_record,
            expected_version=PersistenceVersion(0),
        ),
    )

    assert isinstance(updated, Success)
    assert updated.value == PersistenceVersion(1)
    latest = _load_through(port, LoadPersistenceRequest(_KEY))
    assert isinstance(latest, Success)
    assert latest.value is update_record


def test_persistence_port_returns_typed_conflict_failure() -> None:
    port = FakePersistencePort(_SOURCE)
    initial = SavePersistenceRequest(record=_record())
    assert isinstance(_save_through(port, initial), Success)

    duplicate_create = _save_through(port, initial)
    stale_update = _save_through(
        port,
        SavePersistenceRequest(
            record=_record(
                version=PersistenceVersion(1),
                value="stale",
            ),
            expected_version=PersistenceVersion(0),
        ),
    )

    assert isinstance(duplicate_create, Failure)
    assert isinstance(duplicate_create.error, PersistenceConflictError)
    assert isinstance(stale_update, Success)

    second_stale = _save_through(
        port,
        SavePersistenceRequest(
            record=_record(
                version=PersistenceVersion(1),
                value="second-stale",
            ),
            expected_version=PersistenceVersion(0),
        ),
    )
    assert isinstance(second_stale, Failure)
    assert isinstance(second_stale.error, PersistenceConflictError)


def test_health_and_record_identity_time_are_never_generated_implicitly() -> None:
    port = FakePersistencePort(_SOURCE)
    record = _record()
    health = port.health(checked_at=_CHECKED_AT, metadata=_metadata())

    assert record.source is _SOURCE
    assert record.stored_at is _STORED_AT
    assert record.version == PersistenceVersion(0)
    assert isinstance(health, Success)
    assert health.value.checked_at is _CHECKED_AT
    assert health.value.descriptor is _SOURCE
