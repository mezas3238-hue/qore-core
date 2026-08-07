from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.core.runtime import RuntimeContext
from qore.core.runtime_events import RuntimeStartedEvent
from qore.domain.events import (
    BusinessDomainEvent,
    CausationId,
    CorrelationId,
    DomainEventCategory,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
    DomainMetadataValue,
)
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import ValidationError

EVENT_ID = DomainEventId(UUID("00000000-0000-0000-0000-000000000101"))
CORRELATION_ID = CorrelationId(UUID("00000000-0000-0000-0000-000000000102"))
CAUSATION_ID = CausationId(UUID("00000000-0000-0000-0000-000000000103"))
TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)


def metadata() -> DomainEventMetadata:
    return DomainEventMetadata(
        category=DomainEventCategory("portfolio"),
        correlation_id=CORRELATION_ID,
        causation_id=CAUSATION_ID,
        attributes={"source": "test", "aggregate": "portfolio-1"},
    )


def event() -> BusinessDomainEvent:
    return BusinessDomainEvent(
        timestamp=TIMESTAMP,
        event_name="qore.portfolio.created",
        event_id=EVENT_ID,
        event_version=DomainEventVersion("1.0"),
        metadata=metadata(),
    )


class TestDomainEventValueContracts:
    def test_valid_contract_is_explicit_and_immutable(self) -> None:
        domain_event = event()

        assert domain_event.timestamp == TIMESTAMP
        assert domain_event.domain_event_id == EVENT_ID
        assert domain_event.domain_event_version == DomainEventVersion("1.0")
        assert domain_event.domain_metadata.category == DomainEventCategory("portfolio")
        assert domain_event.domain_metadata.correlation_id == CORRELATION_ID
        assert domain_event.domain_metadata.causation_id == CAUSATION_ID

        with pytest.raises(FrozenInstanceError):
            domain_event.domain_metadata.category = DomainEventCategory("other")  # type: ignore[misc]

    def test_metadata_is_defensively_copied_and_read_only(self) -> None:
        attributes = {"b": 2, "a": 1}
        value = DomainEventMetadata(
            category=DomainEventCategory("test"),
            correlation_id=CORRELATION_ID,
            attributes=attributes,
        )
        attributes["c"] = 3

        assert tuple(value.attributes) == ("a", "b")
        assert "c" not in value.attributes
        with pytest.raises(TypeError):
            value.attributes["x"] = 1  # type: ignore[index]

    def test_reserved_metadata_keys_are_rejected(self) -> None:
        for reserved in ("category", "correlation_id", "causation_id"):
            with pytest.raises(ValidationError):
                DomainEventMetadata(
                    category=DomainEventCategory("test"),
                    correlation_id=CORRELATION_ID,
                    attributes={reserved: "forged"},
                )

    def test_mutable_or_nondeterministic_metadata_values_are_rejected(self) -> None:
        invalid_values: tuple[object, ...] = (
            ["mutable"],
            {"nested": "mapping"},
            {"unordered"},
            ("valid-prefix", ["nested-mutable"]),
            float("nan"),
            float("inf"),
        )

        for invalid in invalid_values:
            unsafe = cast(Mapping[str, DomainMetadataValue], {"value": invalid})
            with pytest.raises(ValidationError):
                DomainEventMetadata(
                    category=DomainEventCategory("test"),
                    correlation_id=CORRELATION_ID,
                    attributes=unsafe,
                )

    def test_immutable_tuple_metadata_is_supported(self) -> None:
        value = DomainEventMetadata(
            category=DomainEventCategory("test"),
            correlation_id=CORRELATION_ID,
            attributes={"path": ("portfolio", 1, True, None)},
        )

        assert value.attributes["path"] == ("portfolio", 1, True, None)

    def test_empty_name_category_and_version_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DomainEventCategory("   ")
        with pytest.raises(ValidationError):
            DomainEventVersion("")
        with pytest.raises(ValidationError):
            BusinessDomainEvent(
                timestamp=TIMESTAMP,
                event_name=" ",
                event_id=EVENT_ID,
                event_version=DomainEventVersion("1.0"),
                metadata=metadata(),
            )

    def test_empty_metadata_key_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DomainEventMetadata(
                category=DomainEventCategory("test"),
                correlation_id=CORRELATION_ID,
                attributes={" ": "invalid"},
            )

    def test_causation_is_optional_but_correlation_is_explicit(self) -> None:
        value = DomainEventMetadata(
            category=DomainEventCategory("test"),
            correlation_id=CORRELATION_ID,
        )

        assert value.correlation_id == CORRELATION_ID
        assert value.causation_id is None

    def test_constructor_requires_explicit_identity_and_timestamp(self) -> None:
        with pytest.raises(TypeError):
            BusinessDomainEvent(  # type: ignore[call-arg]
                event_name="qore.test.event",
                event_version=DomainEventVersion("1.0"),
                metadata=metadata(),
            )

        with pytest.raises(TypeError):
            BusinessDomainEvent(  # type: ignore[call-arg]
                timestamp=TIMESTAMP,
                event_name="qore.test.event",
                event_version=DomainEventVersion("1.0"),
                metadata=metadata(),
            )


class TestDomainEventCompatibility:
    def test_business_event_is_a_kernel_domain_event(self) -> None:
        domain_event = event()

        assert isinstance(domain_event, DomainEvent)
        assert domain_event.event_id == EVENT_ID.value
        assert domain_event.event_version == "1.0"
        assert domain_event.metadata["category"] == "portfolio"
        assert domain_event.metadata["correlation_id"] == str(CORRELATION_ID.value)
        assert domain_event.metadata["causation_id"] == str(CAUSATION_ID.value)

    def test_runtime_events_remain_kernel_events_not_business_events(self) -> None:
        context = RuntimeContext(
            execution_id=UUID("00000000-0000-0000-0000-000000000104"),
            runtime_version="0.2.0",
        )
        runtime_event = RuntimeStartedEvent(timestamp=TIMESTAMP, context=context)

        assert isinstance(runtime_event, DomainEvent)
        assert not isinstance(runtime_event, BusinessDomainEvent)
        assert runtime_event.event_name == "qore.runtime.started"

    def test_same_explicit_values_produce_same_logical_representation(self) -> None:
        first = event()
        second = event()

        assert first.logical_values() == second.logical_values()
        assert first == second

    def test_logical_values_include_sorted_metadata_values(self) -> None:
        domain_event = event()

        assert domain_event.logical_values() == (
            str(EVENT_ID.value),
            TIMESTAMP.isoformat(),
            "qore.portfolio.created",
            "1.0",
            "portfolio",
            str(CORRELATION_ID.value),
            str(CAUSATION_ID.value),
            (("aggregate", "portfolio-1"), ("source", "test")),
        )
