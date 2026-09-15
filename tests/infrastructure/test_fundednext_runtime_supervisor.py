from __future__ import annotations

import sys
from pathlib import Path

import pytest

from qore.infrastructure.fundednext_runtime_supervisor import (
    ExclusiveRuntimeLock,
    FundedNextRuntimeSupervisor,
    FundedNextRuntimeSupervisorConfig,
    FundedNextRuntimeSupervisorError,
    read_runtime_heartbeat,
)

_SHA = "a" * 40


def _config(tmp_path: Path) -> FundedNextRuntimeSupervisorConfig:
    return FundedNextRuntimeSupervisorConfig(
        state_dir=tmp_path,
        heartbeat_seconds=0.05,
        restart_initial_seconds=0.05,
        restart_max_seconds=0.1,
    )


def test_once_mode_records_child_exit_without_restart(tmp_path: Path) -> None:
    supervisor = FundedNextRuntimeSupervisor(_config(tmp_path), git_sha=_SHA)
    result = supervisor.run(
        [sys.executable, "-c", "raise SystemExit(0)"],
        once=True,
    )
    assert result == 0
    heartbeat = read_runtime_heartbeat(tmp_path / "heartbeat.json")
    assert heartbeat["state"] == "CHILD_EXITED"
    assert heartbeat["restart_count"] == 0
    assert heartbeat["git_sha"] == _SHA


def test_stop_file_blocks_child_launch(tmp_path: Path) -> None:
    (tmp_path / "STOP").write_text("stop\n", encoding="utf-8")
    supervisor = FundedNextRuntimeSupervisor(_config(tmp_path), git_sha=_SHA)
    result = supervisor.run(
        [sys.executable, "-c", "raise SystemExit(99)"],
        once=True,
    )
    assert result == 0
    heartbeat = read_runtime_heartbeat(tmp_path / "heartbeat.json")
    assert heartbeat["state"] == "STOPPED"
    assert heartbeat["child_pid"] is None
    assert heartbeat["stop_file_present"] is True


def test_exclusive_runtime_lock_rejects_second_instance(tmp_path: Path) -> None:
    lock_path = tmp_path / "runtime.lock"
    with ExclusiveRuntimeLock(lock_path):
        with pytest.raises(
            FundedNextRuntimeSupervisorError,
            match="already-active",
        ):
            with ExclusiveRuntimeLock(lock_path):
                pass


def test_invalid_git_sha_and_restart_geometry_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(FundedNextRuntimeSupervisorError, match="git_sha"):
        FundedNextRuntimeSupervisor(_config(tmp_path), git_sha="short")
    with pytest.raises(FundedNextRuntimeSupervisorError, match="restart_max"):
        FundedNextRuntimeSupervisorConfig(
            state_dir=tmp_path,
            restart_initial_seconds=5,
            restart_max_seconds=1,
        )
