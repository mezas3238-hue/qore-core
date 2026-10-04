from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    ExecutionMode,
    LabScope,
    ResourcePolicy,
    RunRequest,
)
from qore.infrastructure.core_stack_v2.shared_lab_suite_registry import (
    default_native_suite_registry,
)


def request(mode: ExecutionMode, scope: LabScope) -> RunRequest:
    return RunRequest(
        repository="owner/repo",
        repo_path=".",
        commit_sha="a" * 40,
        branch="branch",
        dataset_id="builtin-engineering",
        dataset_version="1",
        mode=mode,
        scope=scope,
        workers=4,
        policy=ResourcePolicy(),
    )


def test_quick_full_stack_does_not_expand_to_full_dag() -> None:
    registry = default_native_suite_registry()
    tasks = registry.plan(
        request(ExecutionMode.QUICK, LabScope.FULL_STACK),
        (),
    )
    assert {task.task_id for task in tasks} == {"unit", "contract"}


def test_component_mode_uses_changed_path_impact() -> None:
    registry = default_native_suite_registry()
    tasks = registry.plan(
        request(ExecutionMode.COMPONENT, LabScope.SENSOR),
        ("tests/infrastructure/test_core_stack_v2_shared_lab_sensor_harness.py",),
    )
    ids = {task.task_id for task in tasks}
    assert "sensor-reality" in ids
    assert "contract" in ids
    assert "unit" in ids


def test_full_plan_contains_parallel_reality_branches_and_final_full_stack() -> None:
    registry = default_native_suite_registry()
    tasks = registry.plan(
        request(ExecutionMode.FULL, LabScope.FULL_STACK),
        (),
    )
    by_id = {task.task_id: task for task in tasks}
    assert "data-reality" in by_id
    assert "sensor-reality" in by_id
    assert "identity-reality" in by_id
    assert "temporal-reality" in by_id
    assert "provider-reality" in by_id
    assert set(by_id["integration"].dependencies) == {
        "data-reality",
        "sensor-reality",
        "identity-reality",
        "temporal-reality",
        "provider-reality",
    }
    assert "full-stack" in by_id
