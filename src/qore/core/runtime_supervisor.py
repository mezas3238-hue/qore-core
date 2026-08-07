from __future__ import annotations

from qore.core.runtime import RuntimeContext
from qore.core.runtime_plan import RuntimeComponentSpec, RuntimePlan
from qore.core.runtime_state import (
    RuntimeComponentSnapshot,
    RuntimeComponentStatus,
    RuntimeSnapshot,
    RuntimeStatus,
)
from qore.kernel.errors import DomainError, KernelError
from qore.kernel.result import Failure, Result, Success


class RuntimeSupervisor:
    """Orquestador determinista del ciclo de vida de componentes del runtime."""

    def __init__(
        self,
        plan: RuntimePlan,
        *,
        runtime_context: RuntimeContext | None = None,
    ) -> None:
        self._plan = plan
        self._runtime_context = runtime_context
        self._active: list[RuntimeComponentSpec] = []
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    @property
    def active_component_names(self) -> tuple[str, ...]:
        """Nombres activos en el orden efectivo de arranque."""
        return tuple(spec.component_name for spec in self._active)

    def _state_projection(
        self,
    ) -> tuple[
        RuntimeStatus,
        RuntimeComponentStatus,
        tuple[str, ...],
        tuple[str, ...],
    ]:
        """Derivar una única representación observable del estado interno."""
        active_names = self.active_component_names
        if self._running:
            return (
                RuntimeStatus.RUNNING,
                RuntimeComponentStatus.ACTIVE,
                active_names,
                (),
            )
        if active_names:
            return (
                RuntimeStatus.DEGRADED,
                RuntimeComponentStatus.RESIDUAL,
                (),
                active_names,
            )
        return (
            RuntimeStatus.STOPPED,
            RuntimeComponentStatus.INACTIVE,
            (),
            (),
        )

    def snapshot(self) -> RuntimeSnapshot:
        """Construir una vista de solo lectura del estado actual del runtime."""
        status, present_status, active_names, residual_names = self._state_projection()
        present_names = set(active_names or residual_names)

        components = tuple(
            RuntimeComponentSnapshot(
                component_name=spec.component_name,
                status=(
                    present_status
                    if spec.component_name in present_names
                    else RuntimeComponentStatus.INACTIVE
                ),
                depends_on=tuple(spec.depends_on),
            )
            for spec in self._plan.components
        )

        return RuntimeSnapshot(
            context=self._runtime_context,
            status=status,
            components=components,
            active_component_names=active_names,
            residual_component_names=residual_names,
        )

    def start(self) -> Result[None, KernelError]:
        """Arrancar el plan en orden determinista con rollback ante fallos."""
        if self._running:
            return Success(None)
        if self._active:
            return Failure(
                DomainError("cannot start runtime with residual active components")
            )

        order_result = self._plan.resolve_start_order()
        if isinstance(order_result, Failure):
            return order_result

        for spec in order_result.value:
            result = spec.component.start()
            if isinstance(result, Failure):
                self._rollback_started_components()
                return result
            self._active.append(spec)

        self._running = True
        return Success(None)

    def stop(self) -> Result[None, KernelError]:
        """Detener componentes activos en orden inverso al arranque efectivo."""
        if not self._active:
            self._running = False
            return Success(None)

        first_error: KernelError | None = None
        failed_to_stop: list[RuntimeComponentSpec] = []

        for spec in reversed(self._active):
            result = spec.component.stop()
            if isinstance(result, Failure):
                if first_error is None:
                    first_error = result.error
                failed_to_stop.append(spec)

        self._active = list(reversed(failed_to_stop))
        self._running = False

        if first_error is not None:
            return Failure(first_error)
        return Success(None)

    def _rollback_started_components(self) -> None:
        """Intentar revertir componentes iniciados sin ocultar el fallo original."""
        failed_to_stop: list[RuntimeComponentSpec] = []

        for spec in reversed(self._active):
            result = spec.component.stop()
            if isinstance(result, Failure):
                failed_to_stop.append(spec)

        self._active = list(reversed(failed_to_stop))
        self._running = False
