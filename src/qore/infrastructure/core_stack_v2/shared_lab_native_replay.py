"""Native replay executor for QORE Shared Lab."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class ReplayRunner(StrEnum):
    PYTHON_MODULE = "PYTHON_MODULE"
    PYTEST = "PYTEST"
    SCRIPT = "SCRIPT"


@dataclass(frozen=True, slots=True)
class ReplayScenario:
    scenario_id: str
    runner: ReplayRunner
    target: str
    args: tuple[str, ...] = ()

    def command(self) -> tuple[str, ...]:
        if self.runner is ReplayRunner.PYTHON_MODULE:
            return (sys.executable, "-m", self.target, *self.args)
        if self.runner is ReplayRunner.PYTEST:
            return (sys.executable, "-m", "pytest", "-q", self.target, *self.args)
        return (sys.executable, self.target, *self.args)


_BUILTINS: dict[str, ReplayScenario] = {
    "global-exam": ReplayScenario(
        "global-exam",
        ReplayRunner.PYTHON_MODULE,
        "qore.infrastructure.core_stack_v2.shared_lab_global_exam",
    ),
    "data-exam": ReplayScenario(
        "data-exam",
        ReplayRunner.PYTHON_MODULE,
        "qore.infrastructure.core_stack_v2.shared_lab_data_exam",
    ),
    "determinism": ReplayScenario(
        "determinism",
        ReplayRunner.PYTEST,
        "tests/infrastructure/test_core_stack_v2_shared_lab_replay.py",
    ),
}


def load_scenario(value: str) -> ReplayScenario:
    if value in _BUILTINS:
        return _BUILTINS[value]
    path = Path(value)
    if not path.exists():
        raise FileNotFoundError(f"replay scenario not found: {value}")
    payload: dict[str, Any] = json.loads(path.read_text())
    return ReplayScenario(
        scenario_id=str(payload["scenario_id"]),
        runner=ReplayRunner(str(payload["runner"])),
        target=str(payload["target"]),
        args=tuple(str(item) for item in payload.get("args", [])),
    )


def execute_scenario(value: str) -> int:
    scenario = load_scenario(value)
    completed = subprocess.run(
        scenario.command(),
        check=False,
        text=True,
    )
    return completed.returncode


def main() -> None:
    parser = argparse.ArgumentParser(prog="qore-shared-lab-native-replay")
    parser.add_argument("--scenario", required=True)
    args = parser.parse_args()
    raise SystemExit(execute_scenario(str(args.scenario)))


if __name__ == "__main__":
    main()
