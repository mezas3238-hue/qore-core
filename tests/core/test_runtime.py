from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.core.engine import CoreEngine
from qore.core.event_bus import EventBus
from qore.core.lifecycle import ApplicationLifecycle, LifecycleState
from qore.core.runtime import RuntimeComponent, RuntimeContext
from qore.core.runtime_events import RuntimeFailedEvent, RuntimeStartedEvent, RuntimeStoppedEvent
from qore.core.service_registry import ServiceRegistry
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import KernelError, ValidationError
from qore.kernel.result import Failure, Result, Success

FIXED_TS = datetime(2026, 1, 1, tzinfo=UTC)
EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000001")


def fixed_clock() -> datetime:
    return FIXED_TS


def runtime_context() -> RuntimeContext:
    return RuntimeContext(execution_id=EXECUTION_ID, runtime_version="0.2.0")


class CapturingHandler:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def handle(self, event: DomainEvent) -> None:
        self.events.append(event)


class TestRuntimeContext:
    def test_context_is_explicit_and_value_based(self) -> None:
        first = runtime_context()
        second = runtime_context()

        assert first == second
        assert first.execution_id == EXECUTION_ID
        assert first.runtime_version == "0.2.0"

    def test_empty_runtime_version_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RuntimeContext(execution_id=EXECUTION_ID, runtime_version="   ")


class TestRuntimeComponentContract:
    def test_core_engine_satisfies_runtime_component_protocol(self) -> None:
        engine = CoreEngine(
            Configuration(application_name="test-app"),
            ServiceRegistry(),
            EventBus(),
        )
        component: RuntimeComponent = engine

        assert component.component_name == "core-engine"
        assert isinstance(component.start(), Success)
        assert isinstance(component.stop(), Success)


class TestTypedServiceRegistry:
    def test_resolution_preserves_registered_type(self) -> None:
        registry = ServiceRegistry()
        registry.register(str, "runtime-service")

        resolved: str | None = registry.resolve(str)
        resolved_all: list[str] = registry.resolve_all(str)

        assert resolved == "runtime-service"
        assert resolved_all == ["runtime-service"]


class TestRuntimeBootstrap:
    def test_runtime_composition_is_explicit(self) -> None:
        context = runtime_context()
        result = bootstrap(
            Configuration(application_name="test-app"),
            runtime_context=context,
            clock=fixed_clock,
        )

        assert isinstance(result, Success)
        app = result.value
        assert app.runtime_context == context
        assert app.lifecycle.runtime_context == context

    def test_phase_one_bootstrap_remains_runtime_free(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))

        assert isinstance(result, Success)
        assert result.value.runtime_context is None
        assert result.value.lifecycle.runtime_context is None


class TestRuntimeLifecycleEvents:
    def test_start_and_stop_emit_deterministic_runtime_events(self) -> None:
        bus = EventBus()
        engine = CoreEngine(Configuration(application_name="test-app"), ServiceRegistry(), bus)
        lifecycle = ApplicationLifecycle(
            engine,
            runtime_context=runtime_context(),
            clock=fixed_clock,
        )
        started = CapturingHandler()
        stopped = CapturingHandler()
        bus.subscribe(RuntimeStartedEvent, started)
        bus.subscribe(RuntimeStoppedEvent, stopped)

        assert isinstance(lifecycle.start(), Success)
        assert lifecycle.state == LifecycleState.RUNNING
        assert isinstance(lifecycle.stop(), Success)
        assert lifecycle.state == LifecycleState.STOPPED

        assert len(started.events) == 1
        assert len(stopped.events) == 1
        assert started.events[0].timestamp == FIXED_TS
        assert stopped.events[0].timestamp == FIXED_TS
        assert started.events[0].metadata["execution_id"] == str(EXECUTION_ID)
        assert stopped.events[0].metadata["runtime_version"] == "0.2.0"

    def test_engine_failure_emits_runtime_failed_and_preserves_original_failure(self) -> None:
        class FailingEngine(CoreEngine):
            def start(self) -> Result[None, KernelError]:
                return Failure(KernelError("engine start failed"))

        bus = EventBus()
        engine = FailingEngine(
            Configuration(application_name="test-app"),
            ServiceRegistry(),
            bus,
        )
        lifecycle = ApplicationLifecycle(
            engine,
            runtime_context=runtime_context(),
            clock=fixed_clock,
        )
        failed = CapturingHandler()
        bus.subscribe(RuntimeFailedEvent, failed)

        result = lifecycle.start()

        assert isinstance(result, Failure)
        assert str(result.error) == "engine start failed"
        assert lifecycle.state == LifecycleState.ERROR
        assert len(failed.events) == 1
        assert failed.events[0].timestamp == FIXED_TS
        assert failed.events[0].metadata["error_message"] == "engine start failed"

    def test_started_event_handler_failure_is_propagated(self) -> None:
        class FailingHandler:
            def handle(self, event: DomainEvent) -> None:
                raise RuntimeError(f"cannot handle {event.event_name}")

        bus = EventBus()
        engine = CoreEngine(Configuration(application_name="test-app"), ServiceRegistry(), bus)
        lifecycle = ApplicationLifecycle(
            engine,
            runtime_context=runtime_context(),
            clock=fixed_clock,
        )
        failed = CapturingHandler()
        bus.subscribe(RuntimeStartedEvent, FailingHandler())
        bus.subscribe(RuntimeFailedEvent, failed)

        result = lifecycle.start()

        assert isinstance(result, Failure)
        assert "cannot handle qore.runtime.started" in str(result.error)
        assert lifecycle.state == LifecycleState.ERROR
        assert len(failed.events) == 1
