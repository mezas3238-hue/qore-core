"""Bootstrap oficial de QORE con compatibilidad Genesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import overload

from qore.core.application import CoreApplication
from qore.core.configuration import Configuration
from qore.core.engine import CoreEngine
from qore.core.event_bus import EventBus
from qore.core.lifecycle import ApplicationLifecycle, Clock
from qore.core.runtime import RuntimeContext
from qore.core.runtime_plan import RuntimeComponentSpec, RuntimePlan
from qore.core.runtime_supervisor import RuntimeSupervisor
from qore.core.service_registry import ServiceRegistry
from qore.kernel.errors import KernelError, ValidationError
from qore.kernel.result import Failure, Result, Success


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


@overload
def bootstrap(
    configuration: Configuration,
    *,
    runtime_context: RuntimeContext,
    clock: Clock,
) -> Result[CoreApplication, KernelError]: ...


def bootstrap(
    configuration: Configuration | None = None,
    *,
    runtime_context: RuntimeContext | None = None,
    clock: Clock | None = None,
) -> CoreIdentity | Result[CoreApplication, KernelError]:
    """Construir el Core o preservar el bootstrap histórico de Genesis.

    Sin argumentos mantiene la API Genesis ya publicada. Con ``Configuration``
    ensambla una ``CoreApplication`` con ``RuntimePlan`` y ``RuntimeSupervisor``
    oficiales. ``RuntimeContext`` y ``clock`` son opt-in y deben suministrarse
    juntos para activar los eventos deterministas de runtime.
    """
    if configuration is None:
        if runtime_context is not None or clock is not None:
            return Failure(
                ValidationError("configuration is required when runtime arguments are provided")
            )
        return CoreIdentity(name="QORE", version="0.1.0", mode="GENESIS")

    if (runtime_context is None) != (clock is None):
        return Failure(ValidationError("runtime_context and clock must be provided together"))

    service_registry = ServiceRegistry()
    event_bus = EventBus()
    engine = CoreEngine(configuration, service_registry, event_bus)
    runtime_plan = RuntimePlan(
        (
            RuntimeComponentSpec(
                component_name=engine.component_name,
                component=engine,
            ),
        )
    )
    runtime_supervisor = RuntimeSupervisor(
        runtime_plan,
        runtime_context=runtime_context,
    )
    lifecycle = ApplicationLifecycle(
        engine,
        runtime_supervisor=runtime_supervisor,
        runtime_context=runtime_context,
        clock=clock,
    )

    return Success(
        CoreApplication(
            configuration=configuration,
            service_registry=service_registry,
            event_bus=event_bus,
            engine=engine,
            lifecycle=lifecycle,
            runtime_plan=runtime_plan,
            runtime_supervisor=runtime_supervisor,
            runtime_context=runtime_context,
        )
    )
