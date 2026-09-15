"""Cross-platform single-instance supervisor for the FundedNext runtime.

The supervisor is deliberately strategy-agnostic. It owns process liveness,
heartbeat evidence, bounded restart backoff, and an external STOP file. It does
not grant broker authority or bypass any QORE execution/risk control.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import IO, Sequence


class FundedNextRuntimeSupervisorError(RuntimeError):
    """Runtime supervision could not proceed safely."""


@dataclass(frozen=True, slots=True)
class FundedNextRuntimeSupervisorConfig:
    state_dir: Path
    heartbeat_seconds: float = 10.0
    restart_initial_seconds: float = 2.0
    restart_max_seconds: float = 60.0
    stop_filename: str = "STOP"

    def __post_init__(self) -> None:
        if self.heartbeat_seconds <= 0:
            raise FundedNextRuntimeSupervisorError(
                "heartbeat_seconds must be positive"
            )
        if self.restart_initial_seconds <= 0:
            raise FundedNextRuntimeSupervisorError(
                "restart_initial_seconds must be positive"
            )
        if self.restart_max_seconds < self.restart_initial_seconds:
            raise FundedNextRuntimeSupervisorError(
                "restart_max_seconds must be >= restart_initial_seconds"
            )
        if not self.stop_filename or Path(self.stop_filename).name != self.stop_filename:
            raise FundedNextRuntimeSupervisorError(
                "stop_filename must be one local filename"
            )


class ExclusiveRuntimeLock:
    """Keep one non-blocking OS file lock for the supervisor lifetime."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle: IO[bytes] | None = None

    def __enter__(self) -> ExclusiveRuntimeLock:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._path.open("a+b")
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.close()
            raise FundedNextRuntimeSupervisorError(
                "fundednext-runtime-already-active"
            ) from error
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()).encode("ascii"))
        handle.flush()
        self._handle = handle
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        del exc_type, exc, tb
        handle = self._handle
        if handle is None:
            return
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            self._handle = None


class FundedNextRuntimeSupervisor:
    """Run one child forever with heartbeat, STOP and bounded restart semantics."""

    def __init__(
        self,
        config: FundedNextRuntimeSupervisorConfig,
        *,
        git_sha: str | None = None,
    ) -> None:
        if not isinstance(config, FundedNextRuntimeSupervisorConfig):
            raise FundedNextRuntimeSupervisorError("supervisor config is required")
        if git_sha is not None and (
            len(git_sha) != 40 or any(ch not in "0123456789abcdef" for ch in git_sha)
        ):
            raise FundedNextRuntimeSupervisorError(
                "git_sha must be lowercase full commit sha"
            )
        self._config = config
        self._git_sha = git_sha
        self._stop = Event()
        self._child: subprocess.Popen[bytes] | None = None

    @property
    def heartbeat_path(self) -> Path:
        return self._config.state_dir / "heartbeat.json"

    @property
    def stop_path(self) -> Path:
        return self._config.state_dir / self._config.stop_filename

    def request_stop(self) -> None:
        self._stop.set()

    def run(self, command: Sequence[str], *, once: bool = False) -> int:
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise FundedNextRuntimeSupervisorError(
                "supervisor command must contain non-empty strings"
            )
        self._config.state_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self._config.state_dir / "runtime.lock"
        restart_count = 0
        backoff = self._config.restart_initial_seconds
        with ExclusiveRuntimeLock(lock_path):
            previous_handlers = self._install_signal_handlers()
            try:
                while True:
                    if self._stop_requested():
                        self._write_heartbeat(
                            state="STOPPED",
                            restart_count=restart_count,
                            child_pid=None,
                            child_exit_code=None,
                        )
                        return 0
                    self._child = subprocess.Popen(tuple(command))
                    child = self._child
                    self._write_heartbeat(
                        state="RUNNING",
                        restart_count=restart_count,
                        child_pid=child.pid,
                        child_exit_code=None,
                    )
                    last_heartbeat = time.monotonic()
                    while child.poll() is None:
                        if self._stop_requested():
                            self._terminate_child(child)
                            self._write_heartbeat(
                                state="STOPPED",
                                restart_count=restart_count,
                                child_pid=child.pid,
                                child_exit_code=child.returncode,
                            )
                            return 0
                        now = time.monotonic()
                        if now - last_heartbeat >= self._config.heartbeat_seconds:
                            self._write_heartbeat(
                                state="RUNNING",
                                restart_count=restart_count,
                                child_pid=child.pid,
                                child_exit_code=None,
                            )
                            last_heartbeat = now
                        time.sleep(min(0.5, self._config.heartbeat_seconds / 2))
                    exit_code = int(child.returncode or 0)
                    self._write_heartbeat(
                        state="CHILD_EXITED",
                        restart_count=restart_count,
                        child_pid=child.pid,
                        child_exit_code=exit_code,
                    )
                    self._child = None
                    if once:
                        return exit_code
                    restart_count += 1
                    self._restart_wait(backoff, restart_count, exit_code)
                    backoff = min(backoff * 2, self._config.restart_max_seconds)
            finally:
                self._restore_signal_handlers(previous_handlers)
                child = self._child
                if child is not None and child.poll() is None:
                    self._terminate_child(child)
                self._child = None

    def _stop_requested(self) -> bool:
        return self._stop.is_set() or self.stop_path.exists()

    def _restart_wait(
        self,
        seconds: float,
        restart_count: int,
        child_exit_code: int,
    ) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._stop_requested():
                return
            self._write_heartbeat(
                state="RESTART_WAIT",
                restart_count=restart_count,
                child_pid=None,
                child_exit_code=child_exit_code,
            )
            time.sleep(min(0.5, max(0.0, deadline - time.monotonic())))

    @staticmethod
    def _terminate_child(child: subprocess.Popen[bytes]) -> None:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)

    def _write_heartbeat(
        self,
        *,
        state: str,
        restart_count: int,
        child_pid: int | None,
        child_exit_code: int | None,
    ) -> None:
        payload = {
            "schema": "qore.fundednext.runtime-heartbeat.v1",
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "supervisor_pid": os.getpid(),
            "child_pid": child_pid,
            "child_exit_code": child_exit_code,
            "restart_count": restart_count,
            "state": state,
            "git_sha": self._git_sha,
            "stop_file_present": self.stop_path.exists(),
        }
        _atomic_json_write(self.heartbeat_path, payload)

    def _install_signal_handlers(self) -> dict[int, object]:
        previous: dict[int, object] = {}
        for signum in (signal.SIGINT, signal.SIGTERM):
            try:
                previous[signum] = signal.getsignal(signum)
                signal.signal(signum, lambda _signum, _frame: self.request_stop())
            except ValueError:
                return {}
        return previous

    @staticmethod
    def _restore_signal_handlers(previous: dict[int, object]) -> None:
        for signum, handler in previous.items():
            signal.signal(signum, handler)  # type: ignore[arg-type]


def _atomic_json_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_runtime_heartbeat(path: Path) -> dict[str, object]:
    """Load one heartbeat; malformed evidence fails closed."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FundedNextRuntimeSupervisorError(
            "runtime-heartbeat-unavailable-or-invalid"
        ) from error
    if payload.get("schema") != "qore.fundednext.runtime-heartbeat.v1":
        raise FundedNextRuntimeSupervisorError("runtime-heartbeat-schema-mismatch")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--git-sha")
    parser.add_argument("--heartbeat-seconds", type=float, default=10.0)
    parser.add_argument("--restart-initial-seconds", type=float, default=2.0)
    parser.add_argument("--restart-max-seconds", type=float, default=60.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    config = FundedNextRuntimeSupervisorConfig(
        state_dir=args.state_dir,
        heartbeat_seconds=args.heartbeat_seconds,
        restart_initial_seconds=args.restart_initial_seconds,
        restart_max_seconds=args.restart_max_seconds,
    )
    supervisor = FundedNextRuntimeSupervisor(config, git_sha=args.git_sha)
    return supervisor.run(command, once=args.once)


if __name__ == "__main__":
    sys.exit(main())
