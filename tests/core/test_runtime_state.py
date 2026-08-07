from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from qore.core.runtime import RuntimeContext
from qore.core.runtime_plan import RuntimeComponentSpec, RuntimePlan
from qore.core.runtime_state import RuntimeComponentStatus, RuntimeSnapshot, RuntimeStatus
from qore.core.runtime_supervisor import RuntimeSupervisor
from qore.kernel.errors import KernelError
from qore.kernel.result import Failure, Result, Success


class RecordingComponent:
    def __init__(
        self,
        name: str,
        log: list[str],
        *,
        fail_start: bool = False,
        fail_stop: bool = False,
    ) -> None:
        self._name = name
        self._log = log
        self._fail_start = fail_start
        self._fail_stop = fail_stop

    @property
    def component_name(self) -> str:
        return self._name

    def start(self) -> Result[None, KernelError]:
        self._log.append(f"start:{self._name}")
        if self._fail_start:
            return Failure(KernelError(f"start failed: {self._name}"))
        return Success(None)

    def stop(self) -> Result[None, KernelError]:
        self._log.append(f"stop:{self._name}")
        if self._fail_stop:
            return Failure(KernelError(f"stop failed: {self._name}"))
        return Success(None)


def spec(
    component: RecordingComponent,
    *dependencies: str,
) -> RuntimeComponentSpec:
    return RuntimeComponentSpec(
        component_name=component.component_name,
        component=component,
        depends_on=dependencies,
    )


def component_statuses(supervisor: RuntimeSupervisor) -> tuple[RuntimeComponentStatus, ...]:
    return tuple(component.status for component in supervisor.snapshot().components)


class TestRuntimeSnapshot:
    def test_new_supervisor_is_stopped_and_clean(self) -> None:
        log: list[str] = []
        first = RecordingComponent("first", log)
        second = RecordingComponent("second", log)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(first), spec(second, "first"))))

        snapshot = supervisor.snapshot()

        assert snapshot.status is RuntimeStatus.STOPPED
        assert snapshot.clean_for_start is True
        assert snapshot.active_component_names == ()
        assert snapshot.residual_component_names == ()
        assert tuple(component.component_name for component in snapshot.components) == (
            "first",
            "second",
        )
        assert component_statuses(supervisor) == (
            RuntimeComponentStatus.INACTIVE,
            RuntimeComponentStatus.INACTIVE,
        )
        assert log == []

    def test_running_snapshot_uses_declaration_and_effective_start_orders(self) -> None:
        log: list[str] = []
        worker = RecordingComponent("worker", log)
        observer = RecordingComponent("observer", log)
        kernel = RecordingComponent("kernel", log)
        supervisor = RuntimeSupervisor(
            RuntimePlan(
                (
                    spec(worker, "kernel"),
                    spec(observer),
                    spec(kernel),
                )
            )
        )

        assert isinstance(supervisor.start(), Success)
        snapshot = supervisor.snapshot()

        assert snapshot.status is RuntimeStatus.RUNNING
        assert snapshot.clean_for_start is False
        assert tuple(component.component_name for component in snapshot.components) == (
            "worker",
            "observer",
            "kernel",
        )
        assert snapshot.active_component_names == ("observer", "kernel", "worker")
        assert snapshot.residual_component_names == ()
        assert tuple(component.status for component in snapshot.components) == (
            RuntimeComponentStatus.ACTIVE,
            RuntimeComponentStatus.ACTIVE,
            RuntimeComponentStatus.ACTIVE,
        )
        assert snapshot.components[0].depends_on == ("kernel",)

    def test_successful_stop_returns_to_stopped(self) -> None:
        log: list[str] = []
        component = RecordingComponent("component", log)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(component),)))

        assert isinstance(supervisor.start(), Success)
        assert isinstance(supervisor.stop(), Success)
        snapshot = supervisor.snapshot()

        assert snapshot.status is RuntimeStatus.STOPPED
        assert snapshot.clean_for_start is True
        assert snapshot.active_component_names == ()
        assert snapshot.residual_component_names == ()
        assert component_statuses(supervisor) == (RuntimeComponentStatus.INACTIVE,)

    def test_runtime_context_is_preserved_without_generation(self) -> None:
        context = RuntimeContext(
            execution_id=UUID("00000000-0000-0000-0000-000000000003"),
            runtime_version="0.3.0",
        )
        supervisor = RuntimeSupervisor(RuntimePlan(), runtime_context=context)

        snapshot = supervisor.snapshot()

        assert snapshot.context is context

    def test_repeated_snapshots_are_equivalent_and_new_values(self) -> None:
        supervisor = RuntimeSupervisor(RuntimePlan())

        first = supervisor.snapshot()
        second = supervisor.snapshot()

        assert first == second
        assert first is not second

    def test_clean_for_start_is_derived_from_state_collections(self) -> None:
        clean = RuntimeSnapshot(
            context=None,
            status=RuntimeStatus.RUNNING,
            components=(),
            active_component_names=(),
            residual_component_names=(),
        )
        active = RuntimeSnapshot(
            context=None,
            status=RuntimeStatus.STOPPED,
            components=(),
            active_component_names=("component",),
            residual_component_names=(),
        )
        residual = RuntimeSnapshot(
            context=None,
            status=RuntimeStatus.STOPPED,
            components=(),
            active_component_names=(),
            residual_component_names=("component",),
        )

        assert clean.clean_for_start is True
        assert active.clean_for_start is False
        assert residual.clean_for_start is False

    def test_snapshot_is_immutable_and_does_not_expose_internal_lists(self) -> None:
        log: list[str] = []
        component = RecordingComponent("component", log)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(component),)))
        snapshot = supervisor.snapshot()

        with pytest.raises(FrozenInstanceError):
            snapshot.status = RuntimeStatus.RUNNING  # type: ignore[misc]

        assert isinstance(snapshot.components, tuple)
        assert isinstance(snapshot.active_component_names, tuple)
        assert isinstance(snapshot.residual_component_names, tuple)
        assert supervisor.active_component_names == ()

    def test_snapshot_read_is_pure_and_does_not_execute_components(self) -> None:
        log: list[str] = []
        component = RecordingComponent("component", log)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(component),)))

        supervisor.snapshot()
        supervisor.snapshot()

        assert log == []

    def test_clean_rollback_after_start_failure_is_stopped(self) -> None:
        log: list[str] = []
        first = RecordingComponent("first", log)
        failing = RecordingComponent("failing", log, fail_start=True)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(first), spec(failing))))

        result = supervisor.start()
        snapshot = supervisor.snapshot()

        assert isinstance(result, Failure)
        assert snapshot.status is RuntimeStatus.STOPPED
        assert snapshot.clean_for_start is True
        assert snapshot.residual_component_names == ()
        assert component_statuses(supervisor) == (
            RuntimeComponentStatus.INACTIVE,
            RuntimeComponentStatus.INACTIVE,
        )

    def test_incomplete_rollback_is_degraded_with_only_real_residuals(self) -> None:
        log: list[str] = []
        sticky = RecordingComponent("sticky", log, fail_stop=True)
        clean = RecordingComponent("clean", log)
        failing = RecordingComponent("failing", log, fail_start=True)
        supervisor = RuntimeSupervisor(
            RuntimePlan((spec(sticky), spec(clean), spec(failing)))
        )

        result = supervisor.start()
        snapshot = supervisor.snapshot()

        assert isinstance(result, Failure)
        assert snapshot.status is RuntimeStatus.DEGRADED
        assert snapshot.clean_for_start is False
        assert snapshot.active_component_names == ()
        assert snapshot.residual_component_names == ("sticky",)
        assert tuple(component.status for component in snapshot.components) == (
            RuntimeComponentStatus.RESIDUAL,
            RuntimeComponentStatus.INACTIVE,
            RuntimeComponentStatus.INACTIVE,
        )

    def test_incomplete_stop_is_degraded_with_failed_components_only(self) -> None:
        log: list[str] = []
        sticky = RecordingComponent("sticky", log, fail_stop=True)
        clean = RecordingComponent("clean", log)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(sticky), spec(clean))))

        assert isinstance(supervisor.start(), Success)
        result = supervisor.stop()
        snapshot = supervisor.snapshot()

        assert isinstance(result, Failure)
        assert snapshot.status is RuntimeStatus.DEGRADED
        assert snapshot.clean_for_start is False
        assert snapshot.active_component_names == ()
        assert snapshot.residual_component_names == ("sticky",)
        assert tuple(component.status for component in snapshot.components) == (
            RuntimeComponentStatus.RESIDUAL,
            RuntimeComponentStatus.INACTIVE,
        )
