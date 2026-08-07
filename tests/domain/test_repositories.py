from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from qore.domain.aggregates import AggregateRoot, AggregateVersion, EntityId
from qore.domain.events import BusinessDomainEvent
from qore.domain.repositories import (
    AggregateSnapshot,
    EventStore,
    Repository,
    SnapshotStore,
    UnitOfWork,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success

AGGREGATE_ID = EntityId(UUID("00000000-0000-0000-0000-000000000401"))


class ExampleAggregate(AggregateRoot):
    pass


class ExampleRepository:
    def get(
        self,
        aggregate_id: EntityId,
    ) -> Result[ExampleAggregate | None, DomainError]:
        if aggregate_id == AGGREGATE_ID:
            return Success(ExampleAggregate(aggregate_id=aggregate_id))
        return Success(None)

    def save(
        self,
        aggregate: ExampleAggregate,
        *,
        expected_version: AggregateVersion | None = None,
    ) -> Result[None, DomainError]:
        _ = aggregate, expected_version
        return Success(None)


class ExampleUnitOfWork:
    def commit(self) -> Result[None, DomainError]:
        return Success(None)

    def rollback(self) -> Result[None, DomainError]:
        return Success(None)


class ExampleSnapshotStore:
    def load(
        self,
        aggregate_id: EntityId,
    ) -> Result[AggregateSnapshot[tuple[str, ...]] | None, DomainError]:
        if aggregate_id != AGGREGATE_ID:
            return Success(None)
        return Success(
            AggregateSnapshot(
                aggregate_id=aggregate_id,
                version=AggregateVersion(3),
                state=("ready",),
            )
        )

    def save(
        self,
        snapshot: AggregateSnapshot[tuple[str, ...]],
    ) -> Result[None, DomainError]:
        _ = snapshot
        return Success(None)


class ExampleEventStore:
    def load(
        self,
        aggregate_id: EntityId,
        *,
        after_version: AggregateVersion | None = None,
    ) -> Result[tuple[BusinessDomainEvent, ...], DomainError]:
        _ = aggregate_id, after_version
        return Success(())

    def append(
        self,
        aggregate_id: EntityId,
        events: tuple[BusinessDomainEvent, ...],
        *,
        expected_version: AggregateVersion,
    ) -> Result[AggregateVersion, DomainError]:
        _ = aggregate_id
        return Success(AggregateVersion(expected_version.value + len(events)))


class TestRepositoryContracts:
    def test_repository_protocol_is_structural(self) -> None:
        repository: Repository[ExampleAggregate] = ExampleRepository()
        result = repository.get(AGGREGATE_ID)
        assert isinstance(result, Success)
        assert isinstance(result.value, ExampleAggregate)
        assert isinstance(
            repository.save(result.value, expected_version=AggregateVersion(0)),
            Success,
        )

    def test_unit_of_work_protocol_is_structural(self) -> None:
        unit_of_work: UnitOfWork = ExampleUnitOfWork()
        assert isinstance(unit_of_work.commit(), Success)
        assert isinstance(unit_of_work.rollback(), Success)

    def test_snapshot_is_immutable_and_store_is_structural(self) -> None:
        snapshot = AggregateSnapshot(
            aggregate_id=AGGREGATE_ID,
            version=AggregateVersion(3),
            state=("ready",),
        )
        with pytest.raises(FrozenInstanceError):
            snapshot.version = AggregateVersion(4)  # type: ignore[misc]

        store: SnapshotStore[tuple[str, ...]] = ExampleSnapshotStore()
        loaded = store.load(AGGREGATE_ID)
        assert isinstance(loaded, Success)
        assert loaded.value == snapshot
        assert isinstance(store.save(snapshot), Success)

    def test_event_store_protocol_preserves_explicit_version_contract(self) -> None:
        store: EventStore = ExampleEventStore()
        loaded = store.load(AGGREGATE_ID, after_version=AggregateVersion(2))
        appended = store.append(
            AGGREGATE_ID,
            (),
            expected_version=AggregateVersion(2),
        )
        assert isinstance(loaded, Success)
        assert loaded.value == ()
        assert isinstance(appended, Success)
        assert appended.value == AggregateVersion(2)
