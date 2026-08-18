from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from qore.core.configuration import Configuration
from qore.core.lifecycle import EventIdSource
from qore.core.runtime import RuntimeContext
from qore.core.runtime_events import RuntimeStartedEvent
from qore.governance.composition import compose_functional_governance
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import ValidationError
from qore.kernel.result import Failure, Success

_RUNTIME_CONTEXT = RuntimeContext(
    execution_id=UUID("70000000-0000-0000-0000-000000000001"),
    runtime_version="1.0",
)
_NOW = datetime(2026, 8, 7, 23, 45, tzinfo=UTC)
_SOURCE_ID = UUID("70000000-0000-0000-0000-000000000099")


class SequenceEventIdSource:
    def __init__(self, ids: tuple[UUID, ...]) -> None:
        self._ids = ids
        self.calls = 0

    def __call__(self) -> UUID:
        index = self.calls
        self.calls += 1
        return self._ids[index]


def _source() -> UUID:
    return _SOURCE_ID


def test_functional_composition_preserves_deterministic_runtime_context() -> None:
    composed = compose_functional_governance(
        Configuration(application_name="qore-functional-runtime-test"),
        runtime_context=_RUNTIME_CONTEXT,
        clock=lambda: _NOW,
        event_id_source=_source,
    )

    assert isinstance(composed, Success)
    assert composed.value.core.runtime_context is _RUNTIME_CONTEXT
    assert composed.value.core.lifecycle.runtime_context is _RUNTIME_CONTEXT


def test_functional_composition_propagates_event_id_source() -> None:
    source = SequenceEventIdSource((_SOURCE_ID,))
    composed = compose_functional_governance(
        Configuration(application_name="qore-functional-runtime-source"),
        runtime_context=_RUNTIME_CONTEXT,
        clock=lambda: _NOW,
        event_id_source=source,
    )
    assert isinstance(composed, Success)
    application = composed.value

    captured: list[RuntimeStartedEvent] = []

    class Handler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStartedEvent)
            captured.append(event)

    application.core.event_bus.subscribe(RuntimeStartedEvent, Handler())
    assert isinstance(application.core.lifecycle.start(), Success)

    assert source.calls == 1
    assert len(captured) == 1
    assert captured[0].event_id == _SOURCE_ID


def test_functional_composition_rejects_partial_runtime_configuration() -> None:
    composed = compose_functional_governance(
        Configuration(application_name="qore-functional-runtime-test"),
        runtime_context=_RUNTIME_CONTEXT,
    )

    assert isinstance(composed, Failure)
    assert isinstance(composed.error, ValidationError)


def test_functional_composition_rejects_non_callable_event_id_source() -> None:
    source = cast(EventIdSource, object())
    composed = compose_functional_governance(
        Configuration(application_name="qore-functional-noncallable"),
        runtime_context=_RUNTIME_CONTEXT,
        clock=lambda: _NOW,
        event_id_source=source,
    )

    assert isinstance(composed, Failure)
    assert isinstance(composed.error, ValidationError)
    assert str(composed.error) == "event id source must be callable"
