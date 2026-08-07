from __future__ import annotations

from enum import Enum, auto

from qore.core.engine import CoreEngine
from qore.kernel.errors import DomainError, KernelError
from qore.kernel.result import Failure, Result, Success


class LifecycleState(Enum):
    INITIALIZED = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


class ApplicationLifecycle:
    """Máquina de estados mínima para controlar el Core."""

    def __init__(self, engine: CoreEngine) -> None:
        self._engine = engine
        self._state = LifecycleState.INITIALIZED
        engine.set_lifecycle(self)

    @property
    def state(self) -> LifecycleState:
        return self._state

    def start(self) -> Result[None, KernelError]:
        """Arrancar desde INITIALIZED o STOPPED."""
        if self._state not in (LifecycleState.INITIALIZED, LifecycleState.STOPPED):
            return Failure(DomainError(f"Cannot start from state {self._state}"))

        self._state = LifecycleState.STARTING
        result = self._engine.start()
        self._state = LifecycleState.RUNNING if isinstance(result, Success) else LifecycleState.ERROR
        return result

    def stop(self) -> Result[None, KernelError]:
        """Detener desde RUNNING y reflejar el resultado del motor."""
        if self._state != LifecycleState.RUNNING:
            return Failure(DomainError(f"Cannot stop from state {self._state}"))

        self._state = LifecycleState.STOPPING
        result = self._engine.stop()
        self._state = LifecycleState.STOPPED if isinstance(result, Success) else LifecycleState.ERROR
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
