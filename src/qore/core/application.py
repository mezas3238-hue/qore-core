from __future__ import annotations

from dataclasses import dataclass

from qore.core.configuration import Configuration
from qore.core.engine import CoreEngine
from qore.core.event_bus import EventBus
from qore.core.lifecycle import ApplicationLifecycle
from qore.core.runtime import RuntimeContext
from qore.core.runtime_health import RuntimeHealthSnapshot, evaluate_runtime_health
from qore.core.runtime_plan import RuntimePlan
from qore.core.runtime_state import RuntimeSnapshot
from qore.core.runtime_supervisor import RuntimeSupervisor
from qore.core.service_registry import ServiceRegistry
from qore.domain.composition import DomainComposition


@dataclass(frozen=True, slots=True)
class CoreApplication:
    """Root Object inmutable del Core y su composición oficial de runtime."""

    configuration: Configuration
    service_registry: ServiceRegistry
    event_bus: EventBus
    engine: CoreEngine
    lifecycle: ApplicationLifecycle
    runtime_plan: RuntimePlan
    runtime_supervisor: RuntimeSupervisor
    domain: DomainComposition
    runtime_context: RuntimeContext | None = None

    def runtime_snapshot(self) -> RuntimeSnapshot:
        """Obtener una vista inmutable nueva del runtime oficial."""
        return self.runtime_supervisor.snapshot()

    def runtime_health(self) -> RuntimeHealthSnapshot:
        """Derivar health/readiness desde el snapshot oficial actual."""
        return evaluate_runtime_health(self.runtime_snapshot())
