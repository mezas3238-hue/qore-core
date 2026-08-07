from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from qore.core.runtime_state import RuntimeSnapshot, RuntimeStatus
from qore.kernel.errors import ValidationError


class RuntimeHealthStatus(Enum):
    """Condición operativa agregada derivada del runtime."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class RuntimeReadiness(Enum):
    """Disponibilidad del runtime para aceptar trabajo del Core."""

    READY = "ready"
    NOT_READY = "not_ready"


class RuntimeHealthReasonCode(Enum):
    """Motivos estructurados de health/readiness de PHASE-02."""

    RUNTIME_STOPPED = "runtime_stopped"
    RESIDUAL_COMPONENTS = "residual_components"


@dataclass(frozen=True, slots=True)
class RuntimeHealthReason:
    """Motivo inmutable de una condición no saludable o no lista."""

    code: RuntimeHealthReasonCode
    component_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(set(self.component_names)) != len(self.component_names):
            raise ValidationError("health reason component names must be unique")
        if self.code is RuntimeHealthReasonCode.RUNTIME_STOPPED and self.component_names:
            raise ValidationError("runtime stopped reason cannot reference components")
        if self.code is RuntimeHealthReasonCode.RESIDUAL_COMPONENTS and not self.component_names:
            raise ValidationError("residual components reason requires component names")


@dataclass(frozen=True, slots=True)
class RuntimeHealthSnapshot:
    """Proyección inmutable de health/readiness desde un RuntimeSnapshot."""

    runtime: RuntimeSnapshot
    health: RuntimeHealthStatus
    readiness: RuntimeReadiness
    reasons: tuple[RuntimeHealthReason, ...]
    blocking_component_names: tuple[str, ...]
    degraded_component_names: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(set(self.blocking_component_names)) != len(self.blocking_component_names):
            raise ValidationError("blocking component names must be unique")
        if len(set(self.degraded_component_names)) != len(self.degraded_component_names):
            raise ValidationError("degraded component names must be unique")

        declared = {component.component_name for component in self.runtime.components}
        blocking = set(self.blocking_component_names)
        degraded = set(self.degraded_component_names)
        if not blocking.issubset(declared) or not degraded.issubset(declared):
            raise ValidationError("health references undeclared runtime components")

        if self.runtime.status is RuntimeStatus.RUNNING:
            if self.health is not RuntimeHealthStatus.HEALTHY:
                raise ValidationError("running runtime must be healthy")
            if self.readiness is not RuntimeReadiness.READY:
                raise ValidationError("running runtime must be ready")
            if self.reasons or blocking or degraded:
                raise ValidationError("healthy runtime cannot contain health blockers")
            return

        if self.runtime.status is RuntimeStatus.STOPPED:
            if self.health is not RuntimeHealthStatus.UNHEALTHY:
                raise ValidationError("stopped runtime must be unhealthy")
            if self.readiness is not RuntimeReadiness.NOT_READY:
                raise ValidationError("stopped runtime must not be ready")
            if blocking or degraded:
                raise ValidationError("stopped runtime cannot report degraded components")
            expected = (RuntimeHealthReason(RuntimeHealthReasonCode.RUNTIME_STOPPED),)
            if self.reasons != expected:
                raise ValidationError("stopped runtime requires runtime-stopped reason")
            return

        if self.health is not RuntimeHealthStatus.DEGRADED:
            raise ValidationError("degraded runtime must have degraded health")
        if self.readiness is not RuntimeReadiness.NOT_READY:
            raise ValidationError("degraded runtime must not be ready")
        residuals = self.runtime.residual_component_names
        if not residuals:
            raise ValidationError("degraded runtime requires residual components")
        if self.blocking_component_names != residuals:
            raise ValidationError("blocking components must match runtime residuals")
        if self.degraded_component_names != residuals:
            raise ValidationError("degraded components must match runtime residuals")
        expected = (
            RuntimeHealthReason(
                RuntimeHealthReasonCode.RESIDUAL_COMPONENTS,
                residuals,
            ),
        )
        if self.reasons != expected:
            raise ValidationError("degraded runtime requires residual-components reason")


def evaluate_runtime_health(snapshot: RuntimeSnapshot) -> RuntimeHealthSnapshot:
    """Derivar health/readiness de forma pura y determinista."""
    if snapshot.status is RuntimeStatus.RUNNING:
        return RuntimeHealthSnapshot(
            runtime=snapshot,
            health=RuntimeHealthStatus.HEALTHY,
            readiness=RuntimeReadiness.READY,
            reasons=(),
            blocking_component_names=(),
            degraded_component_names=(),
        )

    if snapshot.status is RuntimeStatus.STOPPED:
        return RuntimeHealthSnapshot(
            runtime=snapshot,
            health=RuntimeHealthStatus.UNHEALTHY,
            readiness=RuntimeReadiness.NOT_READY,
            reasons=(RuntimeHealthReason(RuntimeHealthReasonCode.RUNTIME_STOPPED),),
            blocking_component_names=(),
            degraded_component_names=(),
        )

    residuals = snapshot.residual_component_names
    return RuntimeHealthSnapshot(
        runtime=snapshot,
        health=RuntimeHealthStatus.DEGRADED,
        readiness=RuntimeReadiness.NOT_READY,
        reasons=(
            RuntimeHealthReason(
                RuntimeHealthReasonCode.RESIDUAL_COMPONENTS,
                residuals,
            ),
        ),
        blocking_component_names=residuals,
        degraded_component_names=residuals,
    )
