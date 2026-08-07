from __future__ import annotations

from typing import TYPE_CHECKING

from qore.core.configuration import Configuration
from qore.core.event_bus import EventBus
from qore.core.service_registry import ServiceRegistry
from qore.kernel.errors import KernelError
from qore.kernel.result import Result, Success

if TYPE_CHECKING:
    from qore.core.lifecycle import ApplicationLifecycle


class CoreEngine:
    """Coordinador mínimo del ciclo de ejecución del Core."""

    def __init__(
        self,
        configuration: Configuration,
        service_registry: ServiceRegistry,
        event_bus: EventBus,
    ) -> None:
        self._config = configuration
        self._registry = service_registry
        self._bus = event_bus
        self._lifecycle: ApplicationLifecycle | None = None

    def set_lifecycle(self, lifecycle: ApplicationLifecycle) -> None:
        """Vincular el ciclo de vida ya construido por Bootstrap."""
        self._lifecycle = lifecycle

    @property
    def configuration(self) -> Configuration:
        return self._config

    @property
    def service_registry(self) -> ServiceRegistry:
        return self._registry

    @property
    def event_bus(self) -> EventBus:
        return self._bus

    def start(self) -> Result[None, KernelError]:
        """Iniciar el motor mínimo sin ejecutar lógica de negocio."""
        return Success(None)

    def stop(self) -> Result[None, KernelError]:
        """Detener el motor mínimo."""
        return Success(None)
