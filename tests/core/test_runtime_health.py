from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from qore.core.runtime_health import (
    RuntimeHealthReason,
    RuntimeHealthReasonCode,
    RuntimeHealthSnapshot,
    RuntimeHealthStatus,
    RuntimeReadiness,
    evaluate_runtime_health,
)
from qore.core.runtime_plan import RuntimeComponentSpec, RuntimePlan
from qore.core.runtime_state import RuntimeStatus
from qore.core.runtime_supervisor import RuntimeSupervisor
from qore.kernel.errors import KernelError, ValidationError
from qore.kernel.result import Failure, Result, Success


class RecordingComponent:
    def __init__(
        self,
        name: str,
        log: list[str],
        *,
        fail_stop: bool = False,
    ) -> None:
        self._name = name
        self._log = log
        self._fail_stop = fail_stop

    @property
    def component_name(self) -> str:
        return self._name

    def start(self) -> Result[None, KernelError]:
        self._log.append(f"start:{self._name}")
        return Success(None)

    def stop(self) -> Result[None, KernelError]:
        self._log.append(f"stop:{self._name}")
        if self._fail_stop:
            return Failure(KernelError(f"stop failed: {self._name}"))
        return Success(None)


def spec(component: RecordingComponent) -> RuntimeComponentSpec:
    return RuntimeComponentSpec(
        component_name=component.component_name,
        component=component,
    )


class TestRuntimeHealthEvaluation:
    def test_empty_stopped_runtime_is_unhealthy_and_not_ready(self) -> None:
        supervisor = RuntimeSupervisor(RuntimePlan())

        health = evaluate_runtime_health(supervisor.snapshot())

        assert health.runtime.status is RuntimeStatus.STOPPED
        assert health.health is RuntimeHealthStatus.UNHEALTHY
        assert health.readiness is RuntimeReadiness.NOT_READY
        assert health.reasons == (
            RuntimeHealthReason(RuntimeHealthReasonCode.RUNTIME_STOPPED),
        )
        assert health.blocking_component_names == ()
        assert health.degraded_component_names == ()

    def test_empty_running_runtime_is_healthy_and_ready(self) -> None:
        supervisor = RuntimeSupervisor(RuntimePlan())
        assert isinstance(supervisor.start(), Success)

        health = evaluate_runtime_health(supervisor.snapshot())

        assert health.runtime.status is RuntimeStatus.RUNNING
        assert health.health is RuntimeHealthStatus.HEALTHY
        assert health.readiness is RuntimeReadiness.READY
        assert health.reasons == ()
        assert health.blocking_component_names == ()
        assert health.degraded_component_names == ()

    def test_running_runtime_is_healthy_and_ready(self) -> None:
        log: list[str] = []
        first = RecordingComponent("first", log)
        second = RecordingComponent("second", log)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(first), spec(second))))
        assert isinstance(supervisor.start(), Success)

        health = evaluate_runtime_health(supervisor.snapshot())

        assert health.health is RuntimeHealthStatus.HEALTHY
        assert health.readiness is RuntimeReadiness.READY
        assert health.reasons == ()
        assert health.blocking_component_names == ()
        assert health.degraded_component_names == ()

    def test_degraded_runtime_reports_residuals_as_blockers(self) -> None:
        log: list[str] = []
        sticky = RecordingComponent("sticky", log, fail_stop=True)
        clean = RecordingComponent("clean", log)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(sticky), spec(clean))))
        assert isinstance(supervisor.start(), Success)
        assert isinstance(supervisor.stop(), Failure)

        health = evaluate_runtime_health(supervisor.snapshot())

        assert health.runtime.status is RuntimeStatus.DEGRADED
        assert health.health is RuntimeHealthStatus.DEGRADED
        assert health.readiness is RuntimeReadiness.NOT_READY
        assert health.blocking_component_names == ("sticky",)
        assert health.degraded_component_names == ("sticky",)
        assert health.reasons == (
            RuntimeHealthReason(
                RuntimeHealthReasonCode.RESIDUAL_COMPONENTS,
                ("sticky",),
            ),
        )

    def test_repeated_evaluation_is_equivalent_and_returns_new_value(self) -> None:
        snapshot = RuntimeSupervisor(RuntimePlan()).snapshot()

        first = evaluate_runtime_health(snapshot)
        second = evaluate_runtime_health(snapshot)

        assert first == second
        assert first is not second

    def test_evaluation_is_pure_and_does_not_execute_components(self) -> None:
        log: list[str] = []
        component = RecordingComponent("component", log)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(component),)))
        snapshot = supervisor.snapshot()

        evaluate_runtime_health(snapshot)
        evaluate_runtime_health(snapshot)

        assert log == []
        assert supervisor.running is False
        assert supervisor.active_component_names == ()

    def test_health_snapshot_is_immutable(self) -> None:
        health = evaluate_runtime_health(RuntimeSupervisor(RuntimePlan()).snapshot())

        with pytest.raises(FrozenInstanceError):
            health.readiness = RuntimeReadiness.READY  # type: ignore[misc]

        assert isinstance(health.reasons, tuple)
        assert isinstance(health.blocking_component_names, tuple)
        assert isinstance(health.degraded_component_names, tuple)


class TestRuntimeHealthInvariants:
    def test_running_runtime_rejects_unhealthy_or_not_ready_projection(self) -> None:
        supervisor = RuntimeSupervisor(RuntimePlan())
        assert isinstance(supervisor.start(), Success)
        runtime = supervisor.snapshot()

        with pytest.raises(ValidationError):
            RuntimeHealthSnapshot(
                runtime=runtime,
                health=RuntimeHealthStatus.UNHEALTHY,
                readiness=RuntimeReadiness.NOT_READY,
                reasons=(),
                blocking_component_names=(),
                degraded_component_names=(),
            )

        with pytest.raises(ValidationError):
            RuntimeHealthSnapshot(
                runtime=runtime,
                health=RuntimeHealthStatus.HEALTHY,
                readiness=RuntimeReadiness.NOT_READY,
                reasons=(),
                blocking_component_names=(),
                degraded_component_names=(),
            )

    def test_stopped_runtime_rejects_ready_projection(self) -> None:
        runtime = RuntimeSupervisor(RuntimePlan()).snapshot()

        with pytest.raises(ValidationError):
            RuntimeHealthSnapshot(
                runtime=runtime,
                health=RuntimeHealthStatus.UNHEALTHY,
                readiness=RuntimeReadiness.READY,
                reasons=(
                    RuntimeHealthReason(RuntimeHealthReasonCode.RUNTIME_STOPPED),
                ),
                blocking_component_names=(),
                degraded_component_names=(),
            )

    def test_degraded_runtime_requires_exact_residual_component_sets(self) -> None:
        log: list[str] = []
        sticky = RecordingComponent("sticky", log, fail_stop=True)
        supervisor = RuntimeSupervisor(RuntimePlan((spec(sticky),)))
        assert isinstance(supervisor.start(), Success)
        assert isinstance(supervisor.stop(), Failure)
        runtime = supervisor.snapshot()

        with pytest.raises(ValidationError):
            RuntimeHealthSnapshot(
                runtime=runtime,
                health=RuntimeHealthStatus.DEGRADED,
                readiness=RuntimeReadiness.NOT_READY,
                reasons=(
                    RuntimeHealthReason(
                        RuntimeHealthReasonCode.RESIDUAL_COMPONENTS,
                        ("sticky",),
                    ),
                ),
                blocking_component_names=(),
                degraded_component_names=("sticky",),
            )

    def test_health_rejects_undeclared_component_names(self) -> None:
        runtime = RuntimeSupervisor(RuntimePlan()).snapshot()

        with pytest.raises(ValidationError):
            RuntimeHealthSnapshot(
                runtime=runtime,
                health=RuntimeHealthStatus.UNHEALTHY,
                readiness=RuntimeReadiness.NOT_READY,
                reasons=(
                    RuntimeHealthReason(RuntimeHealthReasonCode.RUNTIME_STOPPED),
                ),
                blocking_component_names=("ghost",),
                degraded_component_names=(),
            )

    def test_reason_contract_rejects_invalid_component_payloads(self) -> None:
        with pytest.raises(ValidationError):
            RuntimeHealthReason(
                RuntimeHealthReasonCode.RUNTIME_STOPPED,
                ("component",),
            )

        with pytest.raises(ValidationError):
            RuntimeHealthReason(RuntimeHealthReasonCode.RESIDUAL_COMPONENTS)

        with pytest.raises(ValidationError):
            RuntimeHealthReason(
                RuntimeHealthReasonCode.RESIDUAL_COMPONENTS,
                ("component", "component"),
            )
