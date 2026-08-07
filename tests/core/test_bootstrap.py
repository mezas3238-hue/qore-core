from datetime import UTC, datetime

import pytest

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.core.engine import CoreEngine
from qore.core.event_bus import EventBus
from qore.core.lifecycle import ApplicationLifecycle, LifecycleState
from qore.core.service_registry import ServiceRegistry
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import DomainError, KernelError, ValidationError
from qore.kernel.result import Failure, Result, Success

FIXED_TS = datetime(2026, 1, 1, tzinfo=UTC)


def current_state(lifecycle: ApplicationLifecycle) -> LifecycleState:
    """Read lifecycle state without retaining literal narrowing across transitions."""
    return lifecycle.state


class TestConfiguration:
    def test_valid_configuration(self) -> None:
        config = Configuration(application_name="test-app")
        assert config.application_name == "test-app"
        assert config.mode == "GENESIS"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            Configuration(application_name="   ")


class TestServiceRegistry:
    def test_register_and_resolve(self) -> None:
        registry = ServiceRegistry()
        registry.register(str, "hello")
        assert registry.resolve(str) == "hello"

    def test_idempotent_register_same_instance(self) -> None:
        registry = ServiceRegistry()
        value = object()
        registry.register(object, value)
        registry.register(object, value)
        assert registry.resolve_all(object) == [value]

    def test_different_instances_equal_values_preserved(self) -> None:
        registry = ServiceRegistry()
        first = [1, 2]
        second = [1, 2]
        registry.register(list, first)
        registry.register(list, second)
        assert registry.resolve_all(list) == [first, second]

    def test_last_registered_wins_for_resolve(self) -> None:
        registry = ServiceRegistry()
        first = object()
        second = object()
        registry.register(object, first)
        registry.register(object, second)
        assert registry.resolve(object) is second


class TestEventBus:
    def test_publish_without_subscribers_is_success(self) -> None:
        bus = EventBus()
        event = DomainEvent(timestamp=FIXED_TS, event_name="test.event")
        assert isinstance(bus.publish(event), Success)

    def test_publish_continues_after_handler_failure(self) -> None:
        bus = EventBus()
        event = DomainEvent(timestamp=FIXED_TS, event_name="test.event")
        handled: list[str] = []

        class FailingHandler:
            def handle(self, event: DomainEvent) -> None:
                handled.append("failing")
                raise ValueError("boom")

        class GoodHandler:
            def handle(self, event: DomainEvent) -> None:
                handled.append("good")

        bus.subscribe(type(event), FailingHandler())
        bus.subscribe(type(event), GoodHandler())
        result = bus.publish(event)

        assert handled == ["failing", "good"]
        assert isinstance(result, Failure)
        assert isinstance(result.error, KernelError)
        assert "boom" in str(result.error)

    def test_publish_success_when_all_handlers_succeed(self) -> None:
        bus = EventBus()
        event = DomainEvent(timestamp=FIXED_TS, event_name="test.event")

        class GoodHandler:
            def handle(self, event: DomainEvent) -> None:
                return None

        bus.subscribe(type(event), GoodHandler())
        bus.subscribe(type(event), GoodHandler())
        assert isinstance(bus.publish(event), Success)


class TestLifecycle:
    def test_stop_failure_sets_error(self) -> None:
        class FailingStopEngine(CoreEngine):
            def stop(self) -> Result[None, KernelError]:
                return Failure(KernelError("stop failed"))

        engine = FailingStopEngine(
            Configuration(application_name="test-app"),
            ServiceRegistry(),
            EventBus(),
        )
        lifecycle = ApplicationLifecycle(engine)

        assert isinstance(lifecycle.start(), Success)
        assert current_state(lifecycle) == LifecycleState.RUNNING
        assert isinstance(lifecycle.stop(), Failure)
        assert current_state(lifecycle) == LifecycleState.ERROR

    def test_restart_from_error(self) -> None:
        class FaultyStartEngine(CoreEngine):
            def __init__(
                self,
                configuration: Configuration,
                service_registry: ServiceRegistry,
                event_bus: EventBus,
            ) -> None:
                super().__init__(configuration, service_registry, event_bus)
                self.start_count: int = 0

            def start(self) -> Result[None, KernelError]:
                self.start_count += 1
                if self.start_count == 1:
                    return Failure(KernelError("first start fails"))
                return Success(None)

        engine = FaultyStartEngine(
            Configuration(application_name="test-app"),
            ServiceRegistry(),
            EventBus(),
        )
        lifecycle = ApplicationLifecycle(engine)

        assert isinstance(lifecycle.start(), Failure)
        assert current_state(lifecycle) == LifecycleState.ERROR
        assert isinstance(lifecycle.restart(), Success)
        assert current_state(lifecycle) == LifecycleState.RUNNING

    def test_cannot_start_twice(self) -> None:
        lifecycle = ApplicationLifecycle(
            CoreEngine(
                Configuration(application_name="test-app"),
                ServiceRegistry(),
                EventBus(),
            )
        )
        assert isinstance(lifecycle.start(), Success)
        second = lifecycle.start()
        assert isinstance(second, Failure)
        assert isinstance(second.error, DomainError)

    def test_normal_start_stop_flow(self) -> None:
        lifecycle = ApplicationLifecycle(
            CoreEngine(
                Configuration(application_name="test-app"),
                ServiceRegistry(),
                EventBus(),
            )
        )
        assert isinstance(lifecycle.start(), Success)
        assert current_state(lifecycle) == LifecycleState.RUNNING
        assert isinstance(lifecycle.stop(), Success)
        assert current_state(lifecycle) == LifecycleState.STOPPED


class TestBootstrap:
    def test_legacy_genesis_bootstrap_remains_compatible(self) -> None:
        identity = bootstrap()
        assert identity.name == "QORE"
        assert identity.version == "0.1.0"
        assert identity.mode == "GENESIS"

    def test_valid_configuration_returns_core_application(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))
        assert isinstance(result, Success)
        assert isinstance(result.value, CoreApplication)

    def test_core_application_contains_all_components(self) -> None:
        config = Configuration(application_name="test-app")
        result = bootstrap(config)
        assert isinstance(result, Success)
        app = result.value
        assert app.configuration == config
        assert isinstance(app.service_registry, ServiceRegistry)
        assert isinstance(app.event_bus, EventBus)
        assert isinstance(app.engine, CoreEngine)
        assert isinstance(app.lifecycle, ApplicationLifecycle)

    def test_service_registry_starts_empty(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))
        assert isinstance(result, Success)
        assert result.value.service_registry.resolve(object) is None

    def test_event_bus_starts_with_no_subscriptions(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))
        assert isinstance(result, Success)
        event = DomainEvent(timestamp=FIXED_TS, event_name="test")
        assert isinstance(result.value.event_bus.publish(event), Success)

    def test_lifecycle_initial_state_is_initialized(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))
        assert isinstance(result, Success)
        assert result.value.lifecycle.state == LifecycleState.INITIALIZED

    def test_engine_receives_dependencies(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))
        assert isinstance(result, Success)
        app = result.value
        assert app.engine.configuration == app.configuration
        assert app.engine.service_registry is app.service_registry
        assert app.engine.event_bus is app.event_bus

    def test_determinism_same_topology_and_state(self) -> None:
        config = Configuration(application_name="test-app")
        first_result = bootstrap(config)
        second_result = bootstrap(config)
        assert isinstance(first_result, Success)
        assert isinstance(second_result, Success)
        first = first_result.value
        second = second_result.value

        assert first.configuration == second.configuration
        assert type(first.service_registry) is type(second.service_registry)
        assert type(first.event_bus) is type(second.event_bus)
        assert type(first.engine) is type(second.engine)
        assert type(first.lifecycle) is type(second.lifecycle)
        assert first.service_registry.resolve(object) is None
        assert second.service_registry.resolve(object) is None
        assert first.lifecycle.state == LifecycleState.INITIALIZED
        assert second.lifecycle.state == LifecycleState.INITIALIZED
        assert first.engine.service_registry is first.service_registry
        assert second.engine.service_registry is second.service_registry
