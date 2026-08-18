from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import ValidationError

FIXED_TS = datetime(2026, 1, 1, tzinfo=UTC)


def test_domain_event_requires_explicit_event_id() -> None:
    with pytest.raises(TypeError):
        # Exclude invalid call from strict typing with cast on constructor call.
        cast(Any, DomainEvent)(timestamp=FIXED_TS, event_name="test.event")


def test_domain_event_rejects_non_uuid_event_id() -> None:
    with pytest.raises(ValidationError, match="domain event event_id must be UUID"):
        cast(Any, DomainEvent)(
            timestamp=FIXED_TS,
            event_name="test.event",
            event_id="not-a-uuid",
        )


def test_domain_event_creation_with_explicit_id() -> None:
    event_id = UUID("00000000-0000-0000-0000-000000000001")
    event = DomainEvent(
        timestamp=FIXED_TS,
        event_name="test.event",
        event_id=event_id,
    )
    assert event.event_id == event_id
    assert event.event_name == "test.event"
    assert event.event_version == "1.0"
    assert len(event.metadata) == 0


def test_domain_event_creation_with_all_fields() -> None:
    event_id = UUID("00000000-0000-0000-0000-000000000002")
    metadata = {"trace_id": "abc123", "priority": 1}
    event = DomainEvent(
        timestamp=FIXED_TS,
        event_name="user.registered",
        event_id=event_id,
        event_version="2.0",
        metadata=metadata,
    )
    assert event.event_id == event_id
    assert event.event_version == "2.0"
    assert dict(event.metadata) == metadata


def test_domain_event_metadata_is_immutable_and_defensive() -> None:
    event_id = UUID("00000000-0000-0000-0000-000000000003")
    metadata = {"key": "value"}
    event = DomainEvent(
        timestamp=FIXED_TS,
        event_name="x",
        event_id=event_id,
        metadata=metadata,
    )
    metadata["key"] = "mutated"
    assert event.metadata["key"] == "value"
    with pytest.raises(TypeError):
        mutable_view = cast(dict[str, object], event.metadata)
        mutable_view["new"] = "fail"


def test_domain_event_immutability_by_replacement() -> None:
    event = DomainEvent(
        timestamp=FIXED_TS,
        event_name="test",
        event_id=UUID("00000000-0000-0000-0000-000000000004"),
    )
    altered = replace(event, event_name="nuevo")
    assert event.event_name == "test"
    assert altered.event_name == "nuevo"


def test_domain_event_equality_and_hash_use_id_only() -> None:
    event_id = UUID("00000000-0000-0000-0000-000000000005")
    first = DomainEvent(
        timestamp=FIXED_TS,
        event_name="a",
        event_id=event_id,
    )
    second = DomainEvent(
        timestamp=datetime(2026, 2, 2, tzinfo=UTC),
        event_name="b",
        event_id=event_id,
    )
    assert first == second
    assert hash(first) == hash(second)


def test_domain_event_inequality_for_different_ids() -> None:
    first = DomainEvent(
        timestamp=FIXED_TS,
        event_name="a",
        event_id=UUID("00000000-0000-0000-0000-000000000006"),
    )
    second = DomainEvent(
        timestamp=FIXED_TS,
        event_name="a",
        event_id=UUID("00000000-0000-0000-0000-000000000007"),
    )
    assert first != second


def test_invalid_event_id_sentinel_is_not_exposed() -> None:
    sentinel = "DO_NOT_LEAK_INVALID_VALUE"
    with pytest.raises(ValidationError) as exc_info:
        cast(Any, DomainEvent)(
            timestamp=FIXED_TS,
            event_name="bad",
            event_id=sentinel,
        )
    assert sentinel not in str(exc_info.value)
