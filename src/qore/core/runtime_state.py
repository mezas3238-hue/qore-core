from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from qore.core.runtime import RuntimeContext
from qore.kernel.errors import ValidationError


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

    def __post_init__(self) -> None:
        """Rechazar snapshots contradictorios con las invariantes del runtime."""
        active = set(self.active_component_names)
        residual = set(self.residual_component_names)

        if active & residual:
            raise ValidationError("runtime components cannot be active and residual")

        if self.status is RuntimeStatus.STOPPED and (active or residual):
            raise ValidationError("stopped runtime cannot contain active or residual components")
        if self.status is RuntimeStatus.RUNNING and residual:
            raise ValidationError("running runtime cannot contain residual components")
        if self.status is RuntimeStatus.DEGRADED and (active or not residual):
            raise ValidationError(
                "degraded runtime requires residual components and no active components"
            )

        declared_names = {component.component_name for component in self.components}
        if not active.issubset(declared_names) or not residual.issubset(declared_names):
            raise ValidationError("runtime state references undeclared components")

        for component in self.components:
            expected = RuntimeComponentStatus.INACTIVE
            if component.component_name in active:
                expected = RuntimeComponentStatus.ACTIVE
            elif component.component_name in residual:
                expected = RuntimeComponentStatus.RESIDUAL
            if component.status is not expected:
                raise ValidationError(
                    f"component status does not match runtime state: {component.component_name}"
                )

    @property
    def clean_for_start(self) -> bool:
        """Indicar si el runtime está detenido y libre de estado residual."""
        return self.status is RuntimeStatus.STOPPED
