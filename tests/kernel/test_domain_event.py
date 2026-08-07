from dataclasses import replace
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from qore.kernel.domain_event import DomainEvent


def test_domain_event_creation_with_minimal_fields() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    event = DomainEvent(timestamp=timestamp, event_name="test.event")
    assert event.event_name == "test.event"
    assert event.timestamp == timestamp
    assert event.event_version == "1.0"
    assert isinstance(event.event_id, UUID)
    assert len(event.metadata) == 0


def test_domain_event_creation_with_all_fields() -> None:
    event_id = uuid4()
    timestamp = datetime(2026, 2, 2, tzinfo=UTC)
    metadata = {"trace_id": "abc123", "priority": 1}
    event = DomainEvent(
        event_id=event_id,
        timestamp=timestamp,
        event_name="user.registered",
        event_version="2.0",
        metadata=metadata,
    )
    assert event.event_id == event_id
    assert event.timestamp == timestamp
    assert event.event_name == "user.registered"
    assert event.event_version == "2.0"
    assert dict(event.metadata) == metadata


def test_domain_event_metadata_is_immutable_and_defensive() -> None:
    metadata = {"key": "value"}
    event = DomainEvent(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        event_name="x",
        metadata=metadata,
    )
    metadata["key"] = "mutated"
    assert event.metadata["key"] == "value"
    with pytest.raises(TypeError):
        mutable_view = cast(dict[str, object], event.metadata)
        mutable_view["new"] = "fail"


def test_domain_event_immutability_by_replacement() -> None:
    event = DomainEvent(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        event_name="test",
    )
    altered = replace(event, event_name="nuevo")
    assert event.event_name == "test"
    assert altered.event_name == "nuevo"
    assert altered is not event


def test_domain_event_equality_and_hash_use_id_only() -> None:
    event_id = uuid4()
    first = DomainEvent(
        event_id=event_id,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        event_name="a",
    )
    second = DomainEvent(
        event_id=event_id,
        timestamp=datetime(2026, 2, 2, tzinfo=UTC),
        event_name="b",
    )
    assert first == second
    assert hash(first) == hash(second)


def test_domain_event_inequality() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    assert DomainEvent(timestamp=timestamp, event_name="a") != DomainEvent(
        timestamp=timestamp,
        event_name="a",
    )
    assert DomainEvent(timestamp=timestamp, event_name="a") != "not an event"
