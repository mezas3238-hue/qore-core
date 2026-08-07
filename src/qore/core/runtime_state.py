from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from qore.core.runtime import RuntimeContext


class RuntimeStatus(Enum):
    """Estado agregado observable del supervisor."""

    STOPPED = "stopped"
    RUNNING = "running"
    DEGRADED = "degraded"


class RuntimeComponentStatus(Enum):
    """Estado observable de un componente declarado."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    RESIDUAL = "residual"


@dataclass(frozen=True, slots=True)
class RuntimeComponentSnapshot:
    """Vista inmutable de un componente del plan."""

    component_name: str
    status: RuntimeComponentStatus
    depends_on: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """Vista inmutable y determinista del estado del runtime."""

    context: RuntimeContext | None
    status: RuntimeStatus
    components: tuple[RuntimeComponentSnapshot, ...]
    active_component_names: tuple[str, ...]
    residual_component_names: tuple[str, ...]

    @property
    def clean_for_start(self) -> bool:
        """Indicar si no quedan componentes activos ni residuales."""
        return self.status is RuntimeStatus.STOPPED
