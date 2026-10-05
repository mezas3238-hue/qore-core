from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_lab_native_replay import (
    ReplayRunner,
    load_scenario,
)


def test_builtin_replay_scenario_resolves_without_github() -> None:
    scenario = load_scenario("global-exam")
    assert scenario.runner is ReplayRunner.PYTHON_MODULE
    assert "shared_lab_global_exam" in scenario.target


def test_json_replay_scenario_is_extensible(tmp_path: Path) -> None:
    path = tmp_path / "scenario.json"
    path.write_text(
        '{"scenario_id":"x","runner":"PYTEST","target":"tests/test_x.py","args":[]}'
    )
    scenario = load_scenario(str(path))
    assert scenario.scenario_id == "x"
    assert scenario.runner is ReplayRunner.PYTEST
