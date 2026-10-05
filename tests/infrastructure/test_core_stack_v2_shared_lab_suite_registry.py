import json

from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    ExecutionMode,
    LabScope,
    ResourcePolicy,
    RunRequest,
)
from qore.infrastructure.core_stack_v2.shared_lab_suite_registry import (
    NativeSuiteRegistry,
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


def test_default_lab_suites_are_harness_bound() -> None:
    registry = default_native_suite_registry()
    assert registry.definitions()
    assert all(
        definition.execution_origin == "HARNESS"
        for definition in registry.definitions()
    )


def test_target_plugin_carries_exact_task_dataset_binding(tmp_path) -> None:
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    payload = {
        "task_id": "producer-science",
        "suite": "FUNCTIONAL",
        "scope": "cognition",
        "dependencies": [],
        "command": ["python", "producer.py", "{dataset_path}"],
        "component_globs": ["producer.py"],
        "dataset_id": "sealed-science",
        "dataset_version": "7",
    }
    (plugin_dir / "producer.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    registry = NativeSuiteRegistry()
    registry.load_plugins(plugin_dir)
    definition = registry.get("producer-science")
    assert definition.execution_origin == "TARGET"
    assert definition.dataset_id == "sealed-science"
    assert definition.dataset_version == "7"
