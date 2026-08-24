from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.core.engine import CoreEngine
from qore.core.event_bus import EventBus
from qore.core.lifecycle import ApplicationLifecycle, EventIdSource, LifecycleState
from qore.core.runtime import RuntimeContext
from qore.core.runtime_events import RuntimeFailedEvent, RuntimeStartedEvent, RuntimeStoppedEvent
from qore.core.service_registry import ServiceRegistry
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import KernelError, ValidationError
from qore.kernel.result import Failure, Result, Success

FIXED_TS = datetime(2026, 1, 1, tzinfo=UTC)
EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000001")
STARTED_ID = UUID("00000000-0000-0000-0000-000000000010")
STOPPED_ID = UUID("00000000-0000-0000-0000-000000000011")
FAILED_ID = UUID("00000000-0000-0000-0000-000000000012")


def runtime_context() -> RuntimeContext:
    return RuntimeContext(execution_id=EXECUTION_ID, runtime_version="0.2.0")


def fixed_clock() -> datetime:
    return FIXED_TS


class InvalidId:
    def __str__(self) -> str:
        return "DO_NOT_LEAK_INVALID_VALUE"

    def __repr__(self) -> str:
        return "DO_NOT_LEAK_INVALID_VALUE"


class ScriptedEventIdSource:
    def __init__(self, actions: tuple[object, ...]) -> None:
        self._actions = actions
        self.calls = 0

    def __call__(self) -> UUID:
        index = self.calls
        self.calls += 1

        if index >= len(self._actions):
            raise RuntimeError("unexpected event id source call")

        action = self._actions[index]

        if isinstance(action, Exception):
            raise action

        return cast(UUID, action)


class CapturingHandler:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def handle(self, event: DomainEvent) -> None:
        self.events.append(event)


class CountingEngine(CoreEngine):
    def __init__(
        self,
        configuration: Configuration,
        service_registry: ServiceRegistry,
        event_bus: EventBus,
    ) -> None:
        super().__init__(configuration, service_registry, event_bus)
        self.start_count = 0
        self.stop_count = 0

    def start(self) -> Result[None, KernelError]:
        self.start_count += 1
        return Success(None)

    def stop(self) -> Result[None, KernelError]:
        self.stop_count += 1
        return Success(None)


class FailingStartEngine(CoreEngine):
    def start(self) -> Result[None, KernelError]:
        return Failure(KernelError("engine start failed"))


class FailingStopEngine(CoreEngine):
    def stop(self) -> Result[None, KernelError]:
        return Failure(KernelError("engine stop failed"))


def lifecycle_with_source(
    source: EventIdSource,
    *,
    engine: CoreEngine | None = None,
    bus: EventBus | None = None,
) -> ApplicationLifecycle:
    if engine is None:
        engine = CountingEngine(
            Configuration(application_name="test-app"),
            ServiceRegistry(),
            bus or EventBus(),
        )
    return ApplicationLifecycle(
        engine,
        runtime_context=runtime_context(),
        clock=fixed_clock,
        event_id_source=source,
    )


# DomainEvent identity contract

def test_domain_event_requires_explicit_event_id() -> None:
    with pytest.raises(TypeError):
        cast(Any, DomainEvent)(timestamp=FIXED_TS, event_name="missing-id")


def test_domain_event_rejects_non_uuid_event_id() -> None:
    with pytest.raises(ValidationError, match="domain event event_id must be UUID"):
        cast(Any, DomainEvent)(
            timestamp=FIXED_TS,
            event_name="bad-id",
            event_id="not-a-uuid",
        )


def test_direct_invalid_event_id_sentinel_not_exposed() -> None:
    sentinel = "DO_NOT_LEAK_INVALID_VALUE"
    with pytest.raises(ValidationError) as exc_info:
        cast(Any, DomainEvent)(
            timestamp=FIXED_TS,
            event_name="bad-id",
            event_id=sentinel,
        )
    assert sentinel not in str(exc_info.value)


def test_equality_and_hash_use_event_id_only() -> None:
    first = DomainEvent(
        timestamp=FIXED_TS,
        event_name="a",
        event_id=STARTED_ID,
    )
    second = DomainEvent(
        timestamp=datetime(2026, 2, 2, tzinfo=UTC),
        event_name="b",
        event_id=STARTED_ID,
    )
    assert first == second
    assert hash(first) == hash(second)


def test_different_explicit_ids_with_same_content_are_unequal() -> None:
    first = DomainEvent(
        timestamp=FIXED_TS,
        event_name="same",
        event_id=STARTED_ID,
    )
    second = DomainEvent(
        timestamp=FIXED_TS,
        event_name="same",
        event_id=STOPPED_ID,
    )
    assert first != second


# Runtime event explicit identity

def test_runtime_events_require_explicit_ids() -> None:
    context = runtime_context()
    with pytest.raises(TypeError):
        cast(Any, RuntimeStartedEvent)(timestamp=FIXED_TS, context=context)
    with pytest.raises(TypeError):
        cast(Any, RuntimeStoppedEvent)(timestamp=FIXED_TS, context=context)
    with pytest.raises(TypeError):
        cast(Any, RuntimeFailedEvent)(
            timestamp=FIXED_TS,
            context=context,
            error=KernelError("x"),
        )


def test_runtime_events_preserve_explicit_ids() -> None:
    context = runtime_context()
    started = RuntimeStartedEvent(
        event_id=STARTED_ID,
        timestamp=FIXED_TS,
        context=context,
    )
    stopped = RuntimeStoppedEvent(
        event_id=STOPPED_ID,
        timestamp=FIXED_TS,
        context=context,
    )
    failed = RuntimeFailedEvent(
        event_id=FAILED_ID,
        timestamp=FIXED_TS,
        context=context,
        error=KernelError("x"),
    )
    assert started.event_id == STARTED_ID
    assert stopped.event_id == STOPPED_ID
    assert failed.event_id == FAILED_ID


def test_runtime_started_rejects_non_uuid_event_id() -> None:
    with pytest.raises(ValidationError, match="domain event event_id must be UUID"):
        cast(Any, RuntimeStartedEvent)(
            event_id="bad",
            timestamp=FIXED_TS,
            context=runtime_context(),
        )


def test_runtime_stopped_rejects_non_uuid_event_id() -> None:
    with pytest.raises(ValidationError, match="domain event event_id must be UUID"):
        cast(Any, RuntimeStoppedEvent)(
            event_id="bad",
            timestamp=FIXED_TS,
            context=runtime_context(),
        )


def test_runtime_failed_rejects_non_uuid_event_id() -> None:
    with pytest.raises(ValidationError, match="domain event event_id must be UUID"):
        cast(Any, RuntimeFailedEvent)(
            event_id="bad",
            timestamp=FIXED_TS,
            context=runtime_context(),
            error=KernelError("x"),
        )


# Activation all-or-none

def _make_engine() -> CoreEngine:
    return CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        EventBus(),
    )


def _assert_activation_rejected(
    *,
    runtime_context: RuntimeContext | None = None,
    clock: Any = None,
    event_id_source: EventIdSource | None = None,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        ApplicationLifecycle(
            _make_engine(),
            runtime_context=runtime_context,
            clock=clock,
            event_id_source=event_id_source,
        )
    assert str(exc_info.value) == (
        "runtime_context, clock and event_id_source must be provided together"
    )


def test_runtime_activation_runtime_context_only_rejected() -> None:
    _assert_activation_rejected(runtime_context=runtime_context())


def test_runtime_activation_clock_only_rejected() -> None:
    _assert_activation_rejected(clock=fixed_clock)


def test_runtime_activation_event_id_source_only_rejected() -> None:
    _assert_activation_rejected(event_id_source=lambda: STARTED_ID)


def test_runtime_activation_context_and_clock_rejected() -> None:
    _assert_activation_rejected(
        runtime_context=runtime_context(),
        clock=fixed_clock,
    )


def test_runtime_activation_context_and_source_rejected() -> None:
    _assert_activation_rejected(
        runtime_context=runtime_context(),
        event_id_source=lambda: STARTED_ID,
    )


def test_runtime_activation_clock_and_source_rejected() -> None:
    _assert_activation_rejected(
        clock=fixed_clock,
        event_id_source=lambda: STARTED_ID,
    )


def test_runtime_activation_all_present_accepted() -> None:
    lifecycle = lifecycle_with_source(lambda: STARTED_ID)
    assert lifecycle.runtime_context is not None


def test_runtime_activation_all_absent_accepted() -> None:
    lifecycle = ApplicationLifecycle(_make_engine())
    assert lifecycle.runtime_context is None


def test_non_callable_event_id_source_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ApplicationLifecycle(
            _make_engine(),
            runtime_context=runtime_context(),
            clock=fixed_clock,
            event_id_source=cast(EventIdSource, object()),
        )
    assert str(exc_info.value) == "event id source must be callable"


def test_bootstrap_rejects_non_callable_source() -> None:
    result = bootstrap(
        Configuration(application_name="test"),
        runtime_context=runtime_context(),
        clock=fixed_clock,
        event_id_source=cast(EventIdSource, object()),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, ValidationError)
    assert str(result.error) == "event id source must be callable"


# Bootstrap propagation

def test_bootstrap_propagates_event_id_source() -> None:
    source = ScriptedEventIdSource((STARTED_ID,))
    result = bootstrap(
        Configuration(application_name="test"),
        runtime_context=runtime_context(),
        clock=fixed_clock,
        event_id_source=source,
    )
    assert isinstance(result, Success)
    app = result.value

    captured: list[RuntimeStartedEvent] = []

    class StartedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStartedEvent)
            captured.append(event)

    app.event_bus.subscribe(RuntimeStartedEvent, StartedHandler())
    assert isinstance(app.lifecycle.start(), Success)

    assert source.calls == 1
    assert len(captured) == 1
    assert captured[0].event_id == STARTED_ID


# EventBus identity preservation

def test_event_bus_preserves_explicit_event_identity() -> None:
    bus = EventBus()
    event = DomainEvent(
        timestamp=FIXED_TS,
        event_name="event-bus-preservation",
        event_id=STARTED_ID,
    )
    captured: list[DomainEvent] = []

    class Handler:
        def handle(self, event: DomainEvent) -> None:
            captured.append(event)

    bus.subscribe(DomainEvent, Handler())

    result = bus.publish(event)

    assert isinstance(result, Success)
    assert len(captured) == 1
    assert captured[0] is event
    assert captured[0].event_id == STARTED_ID


# Normal ID flow and count

def test_started_and_stopped_consume_exact_sequence() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource((STARTED_ID, STOPPED_ID))
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    handler = CapturingHandler()
    bus.subscribe(RuntimeStartedEvent, handler)
    bus.subscribe(RuntimeStoppedEvent, handler)

    assert isinstance(lifecycle.start(), Success)
    assert isinstance(lifecycle.stop(), Success)

    assert source.calls == 2
    assert [event.event_id for event in handler.events] == [STARTED_ID, STOPPED_ID]


def test_clock_failure_does_not_consume_started_event_id() -> None:
    calls = 0

    def failing_source() -> UUID:
        nonlocal calls
        calls += 1
        return STARTED_ID

    def failing_clock() -> datetime:
        raise RuntimeError("clock failed")

    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        EventBus(),
    )
    lifecycle = ApplicationLifecycle(
        engine,
        runtime_context=runtime_context(),
        clock=failing_clock,
        event_id_source=failing_source,
    )

    with pytest.raises(RuntimeError, match="clock failed"):
        lifecycle.start()

    assert calls == 0


# Start failure paths

def test_engine_start_failure_consumes_only_failed_id() -> None:
    bus = EventBus()
    engine = FailingStartEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource((FAILED_ID,))
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    started_events: list[RuntimeStartedEvent] = []
    failed_events: list[RuntimeFailedEvent] = []

    class StartedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStartedEvent)
            started_events.append(event)

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeStartedEvent, StartedHandler())
    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    result = lifecycle.start()

    assert isinstance(result, Failure)
    assert str(result.error) == "engine start failed"
    assert lifecycle.state is LifecycleState.ERROR
    assert source.calls == 1
    assert started_events == []
    assert len(failed_events) == 1
    assert failed_events[0].event_id == FAILED_ID
    assert failed_events[0].metadata["error_type"] == "KernelError"
    assert failed_events[0].metadata["error_message"] == "engine start failed"


def test_engine_start_failure_priority_when_failed_id_fails() -> None:
    bus = EventBus()
    engine = FailingStartEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource((RuntimeError("FAILED_ID_SENTINEL"),))
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    started_events: list[RuntimeStartedEvent] = []
    failed_events: list[RuntimeFailedEvent] = []

    class StartedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStartedEvent)
            started_events.append(event)

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeStartedEvent, StartedHandler())
    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    result = lifecycle.start()

    assert isinstance(result, Failure)
    assert str(result.error) == "engine start failed"
    assert lifecycle.state is LifecycleState.ERROR
    assert source.calls == 1
    assert started_events == []
    assert failed_events == []


def test_started_identity_failure_rolls_back_and_attempts_failed_id() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource(
        (
            RuntimeError("DO_NOT_LEAK_SENTINEL"),
            FAILED_ID,
        )
    )
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    failed_events: list[RuntimeFailedEvent] = []

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    result = lifecycle.start()

    assert isinstance(result, Failure)
    assert type(result.error) is KernelError
    assert str(result.error) == "event id source failed"
    assert "DO_NOT_LEAK_SENTINEL" not in str(result.error)
    assert lifecycle.state is LifecycleState.ERROR
    assert engine.start_count == 1
    assert engine.stop_count == 1
    assert source.calls == 2
    assert len(failed_events) == 1
    assert failed_events[0].event_id == FAILED_ID
    assert failed_events[0].metadata["error_type"] == "KernelError"
    assert failed_events[0].metadata["error_message"] == "event id source failed"
    assert "DO_NOT_LEAK_SENTINEL" not in str(failed_events[0].metadata)


def test_started_invalid_source_return_rolls_back_and_attempts_failed_id() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource(
        (
            InvalidId(),
            FAILED_ID,
        )
    )
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    failed_events: list[RuntimeFailedEvent] = []

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    result = lifecycle.start()

    assert isinstance(result, Failure)
    assert type(result.error) is ValidationError
    assert str(result.error) == "event id source must return UUID"
    assert "DO_NOT_LEAK_INVALID_VALUE" not in str(result.error)
    assert lifecycle.state is LifecycleState.ERROR
    assert engine.start_count == 1
    assert engine.stop_count == 1
    assert source.calls == 2
    assert len(failed_events) == 1
    assert failed_events[0].event_id == FAILED_ID
    assert failed_events[0].metadata["error_type"] == "ValidationError"
    assert failed_events[0].metadata["error_message"] == "event id source must return UUID"
    assert "DO_NOT_LEAK_INVALID_VALUE" not in str(failed_events[0].metadata)


def test_started_publication_failure_consumes_started_then_failed() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource((STARTED_ID, FAILED_ID))
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    started_events: list[RuntimeStartedEvent] = []
    failed_events: list[RuntimeFailedEvent] = []

    class StartedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStartedEvent)
            started_events.append(event)
            raise RuntimeError("started handler failure")

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeStartedEvent, StartedHandler())
    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    result = lifecycle.start()

    assert isinstance(result, Failure)
    assert "started handler failure" in str(result.error)
    assert lifecycle.state is LifecycleState.ERROR
    assert engine.start_count == 1
    assert engine.stop_count == 1
    assert source.calls == 2
    assert started_events[0].event_id == STARTED_ID
    assert failed_events[0].event_id == FAILED_ID
    assert failed_events[0].metadata["error_type"] == "KernelError"


def test_started_publication_failure_priority_when_failed_id_fails() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource(
        (
            STARTED_ID,
            RuntimeError("evidence source failed"),
        )
    )
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    failed_events: list[RuntimeFailedEvent] = []

    class StartedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStartedEvent)
            raise RuntimeError("started handler failure")

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeStartedEvent, StartedHandler())
    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    result = lifecycle.start()

    assert isinstance(result, Failure)
    assert "started handler failure" in str(result.error)
    assert lifecycle.state is LifecycleState.ERROR
    assert engine.start_count == 1
    assert engine.stop_count == 1
    assert source.calls == 2
    assert failed_events == []


def test_no_third_source_call_after_failed_id_failure() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource(
        (
            RuntimeError("PRIMARY_SENTINEL"),
            RuntimeError("EVIDENCE_SENTINEL"),
        )
    )
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    failed_events: list[RuntimeFailedEvent] = []

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    result = lifecycle.start()

    assert isinstance(result, Failure)
    assert type(result.error) is KernelError
    assert str(result.error) == "event id source failed"
    assert lifecycle.state is LifecycleState.ERROR
    assert engine.start_count == 1
    assert engine.stop_count == 1
    assert source.calls == 2
    assert failed_events == []


# Stop failure paths

def test_stop_failure_consumes_only_failed_id() -> None:
    bus = EventBus()
    engine = FailingStopEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource((STARTED_ID, FAILED_ID))
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    stopped_events: list[RuntimeStoppedEvent] = []
    failed_events: list[RuntimeFailedEvent] = []

    class StoppedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStoppedEvent)
            stopped_events.append(event)

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeStoppedEvent, StoppedHandler())
    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    assert isinstance(lifecycle.start(), Success)
    calls_before_stop = source.calls
    result = lifecycle.stop()

    assert isinstance(result, Failure)
    assert str(result.error) == "engine stop failed"
    assert lifecycle.state is LifecycleState.ERROR
    assert calls_before_stop == 1
    assert source.calls == 2
    assert stopped_events == []
    assert len(failed_events) == 1
    assert failed_events[0].event_id == FAILED_ID


def test_stop_failure_priority_when_failed_id_fails() -> None:
    bus = EventBus()
    engine = FailingStopEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource(
        (
            STARTED_ID,
            RuntimeError("failed evidence source"),
        )
    )
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    failed_events: list[RuntimeFailedEvent] = []

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    assert isinstance(lifecycle.start(), Success)
    result = lifecycle.stop()

    assert isinstance(result, Failure)
    assert str(result.error) == "engine stop failed"
    assert lifecycle.state is LifecycleState.ERROR
    assert source.calls == 2
    assert failed_events == []


def test_stopped_identity_failure_sets_error_and_attempts_failed_id() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource(
        (
            STARTED_ID,
            RuntimeError("STOPPED_IDENTITY_SENTINEL"),
            FAILED_ID,
        )
    )
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    failed_events: list[RuntimeFailedEvent] = []

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    assert isinstance(lifecycle.start(), Success)
    result = lifecycle.stop()

    assert isinstance(result, Failure)
    assert type(result.error) is KernelError
    assert str(result.error) == "event id source failed"
    assert lifecycle.state is LifecycleState.ERROR
    assert engine.stop_count == 1
    assert source.calls == 3
    assert len(failed_events) == 1
    assert failed_events[0].event_id == FAILED_ID


def test_stopped_publication_failure_consumes_started_stopped_failed() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource((STARTED_ID, STOPPED_ID, FAILED_ID))
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    started_events: list[RuntimeStartedEvent] = []
    stopped_events: list[RuntimeStoppedEvent] = []
    failed_events: list[RuntimeFailedEvent] = []

    class StartedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStartedEvent)
            started_events.append(event)

    class StoppedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStoppedEvent)
            stopped_events.append(event)
            raise RuntimeError("stopped handler failure")

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeStartedEvent, StartedHandler())
    bus.subscribe(RuntimeStoppedEvent, StoppedHandler())
    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    assert isinstance(lifecycle.start(), Success)
    result = lifecycle.stop()

    assert isinstance(result, Failure)
    assert "stopped handler failure" in str(result.error)
    assert lifecycle.state is LifecycleState.ERROR
    assert source.calls == 3
    assert started_events[0].event_id == STARTED_ID
    assert stopped_events[0].event_id == STOPPED_ID
    assert failed_events[0].event_id == FAILED_ID


def test_stopped_publication_failure_priority_when_failed_id_fails() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    source = ScriptedEventIdSource(
        (
            STARTED_ID,
            STOPPED_ID,
            RuntimeError("failed evidence source"),
        )
    )
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    failed_events: list[RuntimeFailedEvent] = []

    class StoppedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStoppedEvent)
            raise RuntimeError("stopped handler failure")

    class FailedHandler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeFailedEvent)
            failed_events.append(event)

    bus.subscribe(RuntimeStoppedEvent, StoppedHandler())
    bus.subscribe(RuntimeFailedEvent, FailedHandler())

    assert isinstance(lifecycle.start(), Success)
    result = lifecycle.stop()

    assert isinstance(result, Failure)
    assert "stopped handler failure" in str(result.error)
    assert lifecycle.state is LifecycleState.ERROR
    assert source.calls == 3
    assert failed_events == []


# Distinct / reproducible occurrences

def test_start_stop_start_uses_distinct_ids() -> None:
    bus = EventBus()
    engine = CountingEngine(
        Configuration(application_name="test"),
        ServiceRegistry(),
        bus,
    )
    ids = (
        UUID("00000000-0000-0000-0000-000000000101"),
        UUID("00000000-0000-0000-0000-000000000102"),
        UUID("00000000-0000-0000-0000-000000000103"),
    )
    source = ScriptedEventIdSource(ids)
    lifecycle = lifecycle_with_source(source, engine=engine, bus=bus)

    handler = CapturingHandler()
    bus.subscribe(RuntimeStartedEvent, handler)
    bus.subscribe(RuntimeStoppedEvent, handler)

    assert isinstance(lifecycle.start(), Success)
    assert isinstance(lifecycle.stop(), Success)
    assert isinstance(lifecycle.start(), Success)

    assert source.calls == 3
    assert [event.event_id for event in handler.events] == list(ids)


def test_two_failed_events_different_ids() -> None:
    context = runtime_context()
    first = RuntimeFailedEvent(
        event_id=FAILED_ID,
        timestamp=FIXED_TS,
        context=context,
        error=KernelError("same"),
    )
    second = RuntimeFailedEvent(
        event_id=UUID("00000000-0000-0000-0000-000000000200"),
        timestamp=FIXED_TS,
        context=context,
        error=KernelError("same"),
    )
    assert first.event_id != second.event_id
    assert first != second


def test_deterministic_source_reproduces_ids() -> None:
    ids = (
        UUID("00000000-0000-0000-0000-000000000301"),
        UUID("00000000-0000-0000-0000-000000000302"),
    )

    def run(
        sequence: tuple[UUID, ...],
    ) -> tuple[tuple[UUID, ...], int]:
        bus = EventBus()
        engine = CountingEngine(
            Configuration(application_name="test"),
            ServiceRegistry(),
            bus,
        )
        source = ScriptedEventIdSource(sequence)
        lifecycle = ApplicationLifecycle(
            engine,
            runtime_context=runtime_context(),
            clock=fixed_clock,
            event_id_source=source,
        )
        handler = CapturingHandler()
        bus.subscribe(RuntimeStartedEvent, handler)
        bus.subscribe(RuntimeStoppedEvent, handler)

        assert isinstance(lifecycle.start(), Success)
        assert isinstance(lifecycle.stop(), Success)

        return tuple(event.event_id for event in handler.events), source.calls

    first_sequence, first_calls = run(ids)
    second_sequence, second_calls = run(ids)

    assert first_sequence == ids
    assert second_sequence == ids
    assert first_sequence == second_sequence
    assert first_calls == 2
    assert second_calls == 2
