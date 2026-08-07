"""Bootstrap oficial de QORE con compatibilidad Genesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import overload

from qore.core.application import CoreApplication
from qore.core.configuration import Configuration
from qore.core.engine import CoreEngine
from qore.core.event_bus import EventBus
from qore.core.lifecycle import ApplicationLifecycle
from qore.core.service_registry import ServiceRegistry
from qore.kernel.errors import KernelError
from qore.kernel.result import Result, Success


@dataclass(frozen=True, slots=True)
class CoreIdentity:
    """Identidad histórica retornada por el bootstrap de Genesis."""

    name: str
    version: str
    mode: str


@overload
def bootstrap() -> CoreIdentity: ...


@overload
def bootstrap(configuration: Configuration) -> Result[CoreApplication, KernelError]: ...


def bootstrap(
    configuration: Configuration | None = None,
) -> CoreIdentity | Result[CoreApplication, KernelError]:
    """Construir el Core o preservar el bootstrap histórico de Genesis.

    Sin argumentos mantiene la API Genesis ya publicada. Con ``Configuration``
    ensambla el Core mínimo sin infraestructura, reloj, estado global ni efectos externos.
    """
    if configuration is None:
        return CoreIdentity(name="QORE", version="0.1.0", mode="GENESIS")

    service_registry = ServiceRegistry()
    event_bus = EventBus()
    engine = CoreEngine(configuration, service_registry, event_bus)
    lifecycle = ApplicationLifecycle(engine)

    return Success(
        CoreApplication(
            configuration=configuration,
            service_registry=service_registry,
            event_bus=event_bus,
            engine=engine,
            lifecycle=lifecycle,
        )
    )
