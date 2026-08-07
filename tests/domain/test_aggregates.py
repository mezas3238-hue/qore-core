from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.domain.aggregates import (
    AggregateInvariantError,
    AggregateRoot,
    AggregateVersion,
    DomainService,
    Entity,
    EntityId,
    ValueObject,
)
from qore.domain.events import (
    BusinessDomainEvent,
    CorrelationId,
    DomainEventCategory,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.kernel.errors import ValidationError

AGGREGATE_ID = EntityId(UUID("00000000-0000-0000-0000-000000000301"))
CORRELATION_ID = CorrelationId(UUID("00000000-0000-0000-0000-000000000302"))
TIMESTAMP = datetime(2026, 1, 3, tzinfo=UTC)


def domain_event(sequence: int) -> BusinessDomainEvent:
    return BusinessDomainEvent(
        timestamp=TIMESTAMP,
        event_name=f"qore.test.event-{sequence}",
        event_id=DomainEventId(
            UUID(f"00000000-0000-0000-0000-{sequence:012d}")
        ),
        event_version=DomainEventVersion("1.0"),
        metadata=DomainEventMetadata(
            category=DomainEventCategory("test"),
            correlation_id=CORRELATION_ID,
            attributes={"sequence": sequence},
        ),
    )


class ExampleEntity(Entity):
    pass


class OtherEntity(Entity):
    pass


class TestEntityAndVersionContracts:
    def test_entity_equality_and_hash_are_identity_based(self) -> None:
        first = ExampleEntity(entity_id=AGGREGATE_ID)
        second = ExampleEntity(entity_id=AGGREGATE_ID)
        other_type = OtherEntity(entity_id=AGGREGATE_ID)

        assert first == second
        assert hash(first) == hash(second)
        assert first != other_type

    def test_aggregate_version_is_non_negative_and_monotonic(self) -> None:
        assert AggregateVersion(0).next() == AggregateVersion(1)
        with pytest.raises(ValidationError):
            AggregateVersion(-1)


class TestAggregateRootContracts:
    def test_record_event_preserves_order_and_advances_version(self) -> None:
        aggregate = AggregateRoot(aggregate_id=AGGREGATE_ID)
        first = domain_event(1)
        second = domain_event(2)

        aggregate.record_event(first)
        aggregate.record_event(second)

        assert aggregate.version == AggregateVersion(2)
        assert aggregate.pending_events == (first, second)

    def test_pull_events_returns_immutable_snapshot_and_drains_buffer(self) -> None:
        aggregate = AggregateRoot(aggregate_id=AGGREGATE_ID)
        first = domain_event(1)
        aggregate.record_event(first)

        pulled = aggregate.pull_events()

        assert pulled == (first,)
        assert aggregate.pending_events == ()
        assert aggregate.version == AggregateVersion(1)

    def test_initial_version_is_respected(self) -> None:
        aggregate = AggregateRoot(
            aggregate_id=AGGREGATE_ID,
            version=AggregateVersion(7),
        )
        aggregate.record_event(domain_event(1))

        assert aggregate.version == AggregateVersion(8)

    def test_failed_invariant_does_not_mutate_aggregate(self) -> None:
        aggregate = AggregateRoot(aggregate_id=AGGREGATE_ID)

        with pytest.raises(AggregateInvariantError):
            aggregate.ensure(False, "invariant failed")

        assert aggregate.version == AggregateVersion(0)
        assert aggregate.pending_events == ()
        aggregate.ensure(True, "unused")


@dataclass(frozen=True, slots=True)
class Money:
    amount: int
    currency: str

    def logical_values(self) -> tuple[object, ...]:
        return (self.amount, self.currency)


class PriceService:
    def execute(self) -> Money:
        return Money(10, "USD")


class TestValueObjectAndDomainServiceContracts:
    def test_value_object_protocol_is_structural(self) -> None:
        value: ValueObject = Money(10, "USD")
        assert value.logical_values() == (10, "USD")

    def test_domain_service_protocol_is_structural(self) -> None:
        service: DomainService[Money] = PriceService()
        assert service.execute() == Money(10, "USD")
