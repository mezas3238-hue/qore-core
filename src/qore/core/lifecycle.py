from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import Enum, auto

from qore.core.engine import CoreEngine
from qore.core.runtime import RuntimeContext
from qore.core.runtime_events import RuntimeFailedEvent, RuntimeStartedEvent, RuntimeStoppedEvent
from qore.core.runtime_supervisor import RuntimeSupervisor
from qore.kernel.errors import DomainError, KernelError, ValidationError
from qore.kernel.result import Failure, Result, Success

Clock = Callable[[], datetime]


class LifecycleState(Enum):
    INITIALIZED = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


class ApplicationLifecycle:
    """Máquina de estados del Core con ejecución supervisada opcional."""

    def __init__(
        self,
        engine: CoreEngine,
        *,
        runtime_supervisor: RuntimeSupervisor | None = None,
        runtime_context: RuntimeContext | None = None,
        clock: Clock | None = None,
    ) -> None:
        if (runtime_context is None) != (clock is None):
            raise ValidationError("runtime_context and clock must be provided together")
        self._engine = engine
        self._runtime_supervisor = runtime_supervisor
        self._runtime_context = runtime_context
        self._clock = clock
        self._state = LifecycleState.INITIALIZED
        engine.set_lifecycle(self)

    @property
    def state(self) -> LifecycleState:
        return self._state

    @property
    def runtime_context(self) -> RuntimeContext | None:
        return self._runtime_context

    @property
    def runtime_supervisor(self) -> RuntimeSupervisor | None:
        return self._runtime_supervisor

    def _start_execution(self) -> Result[None, KernelError]:
        supervisor = self._runtime_supervisor
        if supervisor is not None:
            return supervisor.start()
        return self._engine.start()

    def _stop_execution(self) -> Result[None, KernelError]:
        supervisor = self._runtime_supervisor
        if supervisor is not None:
            return supervisor.stop()
        return self._engine.stop()

    def _publish_started(self) -> Result[None, KernelError]:
        context = self._runtime_context
        clock = self._clock
        if context is None or clock is None:
            return Success(None)
        event = RuntimeStartedEvent(timestamp=clock(), context=context)
        return self._engine.event_bus.publish(event)

    def _publish_stopped(self) -> Result[None, KernelError]:
        context = self._runtime_context
        clock = self._clock
        if context is None or clock is None:
            return Success(None)
        event = RuntimeStoppedEvent(timestamp=clock(), context=context)
        return self._engine.event_bus.publish(event)

    def _publish_failed(self, error: KernelError) -> None:
        context = self._runtime_context
        clock = self._clock
        if context is None or clock is None:
            return
        self._engine.event_bus.publish(
            RuntimeFailedEvent(timestamp=clock(), context=context, error=error)
        )

    def start(self) -> Result[None, KernelError]:
        """Arrancar desde INITIALIZED o STOPPED por la ruta oficial de ejecución."""
        if self._state not in (LifecycleState.INITIALIZED, LifecycleState.STOPPED):
            return Failure(DomainError(f"Cannot start from state {self._state}"))

        self._state = LifecycleState.STARTING
        result = self._start_execution()
        if isinstance(result, Failure):
            self._state = LifecycleState.ERROR
            self._publish_failed(result.error)
            return result

        self._state = LifecycleState.RUNNING
        event_result = self._publish_started()
        if isinstance(event_result, Failure):
            self._stop_execution()
            self._state = LifecycleState.ERROR
            self._publish_failed(event_result.error)
            return event_result

        return result

    def stop(self) -> Result[None, KernelError]:
        """Detener desde RUNNING por la misma ruta oficial de ejecución."""
        if self._state != LifecycleState.RUNNING:
            return Failure(DomainError(f"Cannot stop from state {self._state}"))

        self._state = LifecycleState.STOPPING
        result = self._stop_execution()
        if isinstance(result, Failure):
            self._state = LifecycleState.ERROR
            self._publish_failed(result.error)
            return result

        self._state = LifecycleState.STOPPED
        event_result = self._publish_stopped()
        if isinstance(event_result, Failure):
            self._state = LifecycleState.ERROR
            self._publish_failed(event_result.error)
            return event_result

        return result

    def restart(self) -> Result[None, KernelError]:
        """Reiniciar desde RUNNING o recuperar desde ERROR."""
        if self._state == LifecycleState.ERROR:
            self._state = LifecycleState.INITIALIZED
            return self.start()

        if self._state == LifecycleState.RUNNING:
            stop_result = self.stop()
            if isinstance(stop_result, Failure):
                return stop_result
            return self.start()

        return Failure(DomainError(f"Cannot restart from state {self._state}"))
