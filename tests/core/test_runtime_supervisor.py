from __future__ import annotations

import pytest

from qore.core.runtime_plan import RuntimeComponentSpec, RuntimePlan
from qore.core.runtime_supervisor import RuntimeSupervisor
from qore.kernel.errors import DomainError, KernelError, ValidationError
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


class TestRuntimeComponentSpec:
    def test_name_must_match_component_contract(self) -> None:
        component = RecordingComponent("engine", [])

        with pytest.raises(ValidationError):
            RuntimeComponentSpec(component_name="other", component=component)

    def test_duplicate_dependencies_are_rejected(self) -> None:
        component = RecordingComponent("engine", [])

        with pytest.raises(ValidationError):
            RuntimeComponentSpec(
                component_name="engine",
                component=component,
                depends_on=("config", "config"),
            )


class TestRuntimePlan:
    def test_independent_components_keep_declaration_order(self) -> None:
        log: list[str] = []
        first = RecordingComponent("first", log)
        second = RecordingComponent("second", log)
        third = RecordingComponent("third", log)
        plan = RuntimePlan((spec(first), spec(second), spec(third)))

        result = plan.resolve_start_order()

        assert isinstance(result, Success)
        assert tuple(item.component_name for item in result.value) == (
            "first",
            "second",
            "third",
        )

    def test_dependencies_are_resolved_with_stable_topological_order(self) -> None:
        log: list[str] = []
        worker = RecordingComponent("worker", log)
        observer = RecordingComponent("observer", log)
        kernel = RecordingComponent("kernel", log)
        plan = RuntimePlan(
            (
                spec(worker, "kernel"),
                spec(observer),
                spec(kernel),
            )
        )

        result = plan.resolve_start_order()

        assert isinstance(result, Success)
        assert tuple(item.component_name for item in result.value) == (
            "observer",
            "kernel",
            "worker",
        )

    def test_duplicate_component_names_are_rejected_before_execution(self) -> None:
        log: list[str] = []
        first = RecordingComponent("same", log)
        second = RecordingComponent("same", log)
        plan = RuntimePlan((spec(first), spec(second)))

        result = plan.resolve_start_order()

        assert isinstance(result, Failure)
        assert isinstance(result.error, ValidationError)
        assert "unique" in str(result.error)
        assert log == []

    def test_unknown_dependency_is_rejected_before_execution(self) -> None:
        log: list[str] = []
        worker = RecordingComponent("worker", log)
        plan = RuntimePlan((spec(worker, "missing"),))

        result = plan.resolve_start_order()

        assert isinstance(result, Failure)
        assert isinstance(result.error, ValidationError)
        assert "unknown" in str(result.error)
        assert log == []

    def test_dependency_cycle_is_rejected_before_execution(self) -> None:
        log: list[str] = []
        first = RecordingComponent("first", log)
        second = RecordingComponent("second", log)
        plan = RuntimePlan((spec(first, "second"), spec(second, "first")))

        result = plan.resolve_start_order()

        assert isinstance(result, Failure)
        assert isinstance(result.error, ValidationError)
        assert "cycle" in str(result.error)
        assert log == []


class TestRuntimeSupervisor:
    def test_start_and_stop_follow_resolved_and_reverse_order(self) -> None:
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
        assert supervisor.running is True
        assert supervisor.active_component_names == ("observer", "kernel", "worker")
        assert isinstance(supervisor.stop(), Success)
        assert supervisor.running is False
        assert supervisor.active_component_names == ()
        assert log == [
            "start:observer",
            "start:kernel",
            "start:worker",
            "stop:worker",
            "stop:kernel",
            "stop:observer",
        ]

    def test_start_failure_rolls_back_only_started_components(self) -> None:
        log: list[str] = []
        first = RecordingComponent("first", log)
        failing = RecordingComponent("failing", log, fail_start=True)
        never_started = RecordingComponent("never", log)
        supervisor = RuntimeSupervisor(
            RuntimePlan((spec(first), spec(failing), spec(never_started)))
        )

        result = supervisor.start()

        assert isinstance(result, Failure)
        assert str(result.error) == "start failed: failing"
        assert supervisor.running is False
        assert supervisor.active_component_names == ()
        assert log == ["start:first", "start:failing", "stop:first"]

    def test_rollback_failure_preserves_original_start_error_and_residual(self) -> None:
        log: list[str] = []
        sticky = RecordingComponent("sticky", log, fail_stop=True)
        failing = RecordingComponent("failing", log, fail_start=True)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(sticky), spec(failing))))

        result = supervisor.start()

        assert isinstance(result, Failure)
        assert str(result.error) == "start failed: failing"
        assert supervisor.active_component_names == ("sticky",)
        assert isinstance(supervisor.start(), Failure)
        blocked = supervisor.start()
        assert isinstance(blocked, Failure)
        assert isinstance(blocked.error, DomainError)

    def test_stop_continues_after_failure_and_preserves_failed_component(self) -> None:
        log: list[str] = []
        first = RecordingComponent("first", log)
        sticky = RecordingComponent("sticky", log, fail_stop=True)
        last = RecordingComponent("last", log)
        supervisor = RuntimeSupervisor(
            RuntimePlan((spec(first), spec(sticky), spec(last)))
        )
        assert isinstance(supervisor.start(), Success)

        result = supervisor.stop()

        assert isinstance(result, Failure)
        assert str(result.error) == "stop failed: sticky"
        assert supervisor.active_component_names == ("sticky",)
        assert log == [
            "start:first",
            "start:sticky",
            "start:last",
            "stop:last",
            "stop:sticky",
            "stop:first",
        ]

    def test_start_and_stop_are_idempotent_after_success(self) -> None:
        log: list[str] = []
        component = RecordingComponent("only", log)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(component),)))

        assert isinstance(supervisor.start(), Success)
        assert isinstance(supervisor.start(), Success)
        assert isinstance(supervisor.stop(), Success)
        assert isinstance(supervisor.stop(), Success)
        assert log == ["start:only", "stop:only"]
