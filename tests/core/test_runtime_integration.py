from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.core.engine import CoreEngine
from qore.core.event_bus import EventBus
from qore.core.lifecycle import ApplicationLifecycle, LifecycleState
from qore.core.runtime import RuntimeContext
from qore.core.runtime_events import RuntimeStartedEvent
from qore.core.runtime_health import RuntimeHealthStatus, RuntimeReadiness
from qore.core.runtime_plan import RuntimeComponentSpec, RuntimePlan
from qore.core.runtime_state import RuntimeStatus
from qore.core.runtime_supervisor import RuntimeSupervisor
from qore.core.service_registry import ServiceRegistry
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import KernelError
from qore.kernel.result import Failure, Result, Success

FIXED_TS = datetime(2026, 1, 1, tzinfo=UTC)
EXECUTION_ID = UUID("00000000-0000-0000-0000-000000000005")
RUNTIME_EVENT_ID = UUID("00000000-0000-0000-0000-000000000020")


def fixed_clock() -> datetime:
    return FIXED_TS


def fixed_event_id() -> UUID:
    return RUNTIME_EVENT_ID


def runtime_context() -> RuntimeContext:
    return RuntimeContext(execution_id=EXECUTION_ID, runtime_version="0.5.0")


class CountingEngine(CoreEngine):
    def __init__(
        self,
        configuration: Configuration,
        service_registry: ServiceRegistry,
        event_bus: EventBus,
        *,
        fail_start: bool = False,
        fail_stop: bool = False,
    ) -> None:
        super().__init__(configuration, service_registry, event_bus)
        self.start_count = 0
        self.stop_count = 0
        self._fail_start = fail_start
        self._fail_stop = fail_stop

    def start(self) -> Result[None, KernelError]:
        self.start_count += 1
        if self._fail_start:
            return Failure(KernelError("engine start failed"))
        return Success(None)

    def stop(self) -> Result[None, KernelError]:
        self.stop_count += 1
        if self._fail_stop:
            return Failure(KernelError("engine stop failed"))
        return Success(None)


def supervised_lifecycle(
    engine: CoreEngine,
    *,
    context: RuntimeContext | None = None,
) -> tuple[ApplicationLifecycle, RuntimeSupervisor]:
    plan = RuntimePlan(
        (
            RuntimeComponentSpec(
                component_name=engine.component_name,
                component=engine,
            ),
        )
    )
    supervisor = RuntimeSupervisor(plan, runtime_context=context)
    lifecycle = ApplicationLifecycle(
        engine,
        runtime_supervisor=supervisor,
        runtime_context=context,
        clock=fixed_clock if context is not None else None,
        event_id_source=fixed_event_id if context is not None else None,
    )
    return lifecycle, supervisor


class TestBootstrappedRuntimeComposition:
    def test_bootstrap_exposes_single_official_runtime_composition(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))

        assert isinstance(result, Success)
        app = result.value
        assert app.lifecycle.runtime_supervisor is app.runtime_supervisor
        assert app.runtime_plan.components[0].component is app.engine
        assert app.runtime_plan.components[0].component_name == "core-engine"
        assert len(app.runtime_plan.components) == 1

    def test_initial_snapshot_and_health_are_official_and_stopped(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))
        assert isinstance(result, Success)
        app = result.value

        snapshot = app.runtime_snapshot()
        health = app.runtime_health()

        assert snapshot.status is RuntimeStatus.STOPPED
        assert snapshot.active_component_names == ()
        assert health.runtime == snapshot
        assert health.health is RuntimeHealthStatus.UNHEALTHY
        assert health.readiness is RuntimeReadiness.NOT_READY

    def test_start_produces_running_snapshot_and_healthy_ready(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))
        assert isinstance(result, Success)
        app = result.value

        assert isinstance(app.lifecycle.start(), Success)
        snapshot = app.runtime_snapshot()
        health = app.runtime_health()

        assert app.runtime_supervisor.running is True
        assert snapshot.status is RuntimeStatus.RUNNING
        assert snapshot.active_component_names == ("core-engine",)
        assert health.health is RuntimeHealthStatus.HEALTHY
        assert health.readiness is RuntimeReadiness.READY

    def test_stop_returns_runtime_to_stopped_and_not_ready(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))
        assert isinstance(result, Success)
        app = result.value

        assert isinstance(app.lifecycle.start(), Success)
        assert isinstance(app.lifecycle.stop(), Success)
        snapshot = app.runtime_snapshot()
        health = app.runtime_health()

        assert app.runtime_supervisor.running is False
        assert snapshot.status is RuntimeStatus.STOPPED
        assert health.health is RuntimeHealthStatus.UNHEALTHY
        assert health.readiness is RuntimeReadiness.NOT_READY

    def test_runtime_without_context_is_supervised_but_emits_no_runtime_events(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))
        assert isinstance(result, Success)
        app = result.value
        captured: list[DomainEvent] = []

        class Handler:
            def handle(self, event: DomainEvent) -> None:
                captured.append(event)

        app.event_bus.subscribe(RuntimeStartedEvent, Handler())
        assert isinstance(app.lifecycle.start(), Success)

        assert app.runtime_context is None
        assert app.runtime_supervisor.running is True
        assert captured == []

    def test_runtime_with_context_preserves_context_in_official_snapshot(self) -> None:
        context = runtime_context()
        result = bootstrap(
            Configuration(application_name="test-app"),
            runtime_context=context,
            clock=fixed_clock,
            event_id_source=fixed_event_id,
        )
        assert isinstance(result, Success)
        app = result.value

        assert app.runtime_snapshot().context is context
        assert app.lifecycle.runtime_context is context
        assert app.runtime_supervisor.snapshot().context is context


class TestSupervisedLifecycleExecution:
    def test_supervised_start_and_stop_invoke_engine_exactly_once(self) -> None:
        engine = CountingEngine(
            Configuration(application_name="test-app"),
            ServiceRegistry(),
            EventBus(),
        )
        lifecycle, supervisor = supervised_lifecycle(engine)

        assert isinstance(lifecycle.start(), Success)
        assert isinstance(lifecycle.stop(), Success)

        assert engine.start_count == 1
        assert engine.stop_count == 1
        assert supervisor.snapshot().status is RuntimeStatus.STOPPED

    def test_supervised_start_failure_preserves_original_error(self) -> None:
        engine = CountingEngine(
            Configuration(application_name="test-app"),
            ServiceRegistry(),
            EventBus(),
            fail_start=True,
        )
        lifecycle, supervisor = supervised_lifecycle(engine)

        result = lifecycle.start()

        assert isinstance(result, Failure)
        assert str(result.error) == "engine start failed"
        assert lifecycle.state is LifecycleState.ERROR
        assert engine.start_count == 1
        assert engine.stop_count == 0
        assert supervisor.snapshot().status is RuntimeStatus.STOPPED

    def test_started_event_failure_rolls_back_supervised_execution(self) -> None:
        bus = EventBus()
        engine = CountingEngine(
            Configuration(application_name="test-app"),
            ServiceRegistry(),
            bus,
        )
        lifecycle, supervisor = supervised_lifecycle(engine, context=runtime_context())

        class FailingHandler:
            def handle(self, event: DomainEvent) -> None:
                raise RuntimeError(f"cannot handle {event.event_name}")

        bus.subscribe(RuntimeStartedEvent, FailingHandler())

        result = lifecycle.start()

        assert isinstance(result, Failure)
        assert "cannot handle qore.runtime.started" in str(result.error)
        assert lifecycle.state is LifecycleState.ERROR
        assert engine.start_count == 1
        assert engine.stop_count == 1
        assert supervisor.snapshot().status is RuntimeStatus.STOPPED

    def test_direct_lifecycle_without_supervisor_remains_compatible(self) -> None:
        engine = CountingEngine(
            Configuration(application_name="test-app"),
            ServiceRegistry(),
            EventBus(),
        )
        lifecycle = ApplicationLifecycle(engine)

        assert isinstance(lifecycle.start(), Success)
        assert isinstance(lifecycle.stop(), Success)
        assert engine.start_count == 1
        assert engine.stop_count == 1
        assert lifecycle.runtime_supervisor is None
