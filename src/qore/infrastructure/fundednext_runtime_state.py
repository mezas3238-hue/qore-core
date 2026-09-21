"""Durable state, heartbeat and single-writer fencing for FundedNext runtime."""

from __future__ import annotations

import ctypes
import json
import os
import platform
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.fundednext.runtime-state.v1"
_ATOMIC_REPLACE_RETRY_DELAYS_SECONDS = (0.01, 0.02, 0.04, 0.08, 0.16, 0.25)


class FundedNextRuntimeStateError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class FundedNextRuntimeState:
    git_sha: str
    account_identity_fingerprint: str
    highest_closed_balance: str
    active_mll: str
    processed_anchors: tuple[str, ...]
    heartbeat_at: datetime
    last_reconciliation_at: datetime
    service_started_at: datetime

    def __post_init__(self) -> None:
        if len(self.git_sha) != 40:
            raise FundedNextRuntimeStateError("runtime state requires full git SHA")
        if len(self.account_identity_fingerprint) != 64:
            raise FundedNextRuntimeStateError("runtime account fingerprint must be SHA-256")
        for name, value in (
            ("heartbeat_at", self.heartbeat_at),
            ("last_reconciliation_at", self.last_reconciliation_at),
            ("service_started_at", self.service_started_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise FundedNextRuntimeStateError(f"{name} must be timezone-aware")
        if tuple(sorted(set(self.processed_anchors))) != self.processed_anchors:
            raise FundedNextRuntimeStateError("processed anchors must be sorted and unique")

    def with_cycle(
        self,
        *,
        highest_closed_balance: str,
        active_mll: str,
        processed_anchor: str | None,
        reconciled_at: datetime,
        heartbeat_at: datetime,
    ) -> FundedNextRuntimeState:
        anchors = set(self.processed_anchors)
        if processed_anchor is not None:
            anchors.add(processed_anchor)
        return FundedNextRuntimeState(
            git_sha=self.git_sha,
            account_identity_fingerprint=self.account_identity_fingerprint,
            highest_closed_balance=highest_closed_balance,
            active_mll=active_mll,
            processed_anchors=tuple(sorted(anchors))[-256:],
            heartbeat_at=heartbeat_at,
            last_reconciliation_at=reconciled_at,
            service_started_at=self.service_started_at,
        )

    def restarted_at(self, started_at: datetime) -> FundedNextRuntimeState:
        if started_at.tzinfo is None or started_at.utcoffset() is None:
            raise FundedNextRuntimeStateError("restart timestamp must be timezone-aware")
        return FundedNextRuntimeState(
            git_sha=self.git_sha,
            account_identity_fingerprint=self.account_identity_fingerprint,
            highest_closed_balance=self.highest_closed_balance,
            active_mll=self.active_mll,
            processed_anchors=self.processed_anchors,
            heartbeat_at=started_at,
            last_reconciliation_at=started_at,
            service_started_at=started_at,
        )


class DurableFundedNextRuntimeStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> FundedNextRuntimeState | None:
        if not self._path.exists():
            return None
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if payload.get("schema") != _SCHEMA:
                raise FundedNextRuntimeStateError("runtime-state schema mismatch")
            return FundedNextRuntimeState(
                git_sha=str(payload["git_sha"]),
                account_identity_fingerprint=str(payload["account_identity_fingerprint"]),
                highest_closed_balance=str(payload["highest_closed_balance"]),
                active_mll=str(payload["active_mll"]),
                processed_anchors=tuple(str(item) for item in payload["processed_anchors"]),
                heartbeat_at=datetime.fromisoformat(str(payload["heartbeat_at"])),
                last_reconciliation_at=datetime.fromisoformat(
                    str(payload["last_reconciliation_at"])
                ),
                service_started_at=datetime.fromisoformat(str(payload["service_started_at"])),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise FundedNextRuntimeStateError("runtime-state is unreadable") from error

    def store(self, state: FundedNextRuntimeState) -> None:
        if not isinstance(state, FundedNextRuntimeState):
            raise FundedNextRuntimeStateError("canonical runtime state required")
        payload = {
            "schema": _SCHEMA,
            "git_sha": state.git_sha,
            "account_identity_fingerprint": state.account_identity_fingerprint,
            "highest_closed_balance": state.highest_closed_balance,
            "active_mll": state.active_mll,
            "processed_anchors": list(state.processed_anchors),
            "heartbeat_at": state.heartbeat_at.astimezone(UTC).isoformat(),
            "last_reconciliation_at": state.last_reconciliation_at.astimezone(UTC).isoformat(),
            "service_started_at": state.service_started_at.astimezone(UTC).isoformat(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{self._path.name}.", suffix=".tmp", dir=self._path.parent
        )
        temp = Path(temp_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            for delay in (*_ATOMIC_REPLACE_RETRY_DELAYS_SECONDS, None):
                try:
                    os.replace(temp, self._path)
                    break
                except OSError as error:
                    if delay is None:
                        raise FundedNextRuntimeStateError(
                            "runtime-state atomic write failed"
                        ) from error
                    time.sleep(delay)
        finally:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                # A scanner may still have the abandoned temp file open. It is
                # never a valid state candidate and a later cleanup can remove it.
                pass


class SingleWriterRuntimeLock:
    """Atomic process fence that safely recovers a stale lock after a crash/reboot."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._held = False

    @staticmethod
    def _pid_is_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        if platform.system() == "Windows":
            win_dll = getattr(ctypes, "WinDLL", None)
            get_last_error = getattr(ctypes, "get_last_error", None)
            if win_dll is None or get_last_error is None:
                # Fail closed if the Windows ctypes surface is unexpectedly unavailable.
                return True
            kernel32 = win_dll("kernel32", use_last_error=True)
            process_query_limited_information = 0x1000
            still_active = 259
            handle = int(kernel32.OpenProcess(process_query_limited_information, False, pid))
            if handle == 0:
                # Access denied still proves that the process exists.
                return int(get_last_error()) == 5
            try:
                exit_code = ctypes.c_ulong()
                query_ok = int(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)))
                if query_ok == 0:
                    # Fail closed: never discard a lock when liveness is uncertain.
                    return True
                return int(exit_code.value) == still_active
            finally:
                kernel32.CloseHandle(handle)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _remove_stale_lock(self) -> bool:
        try:
            raw = self._path.read_text(encoding="ascii").strip()
            pid = int(raw)
        except (OSError, ValueError):
            return False
        if self._pid_is_alive(pid):
            return False
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            return False
        return True

    def acquire(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            try:
                descriptor = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as error:
                if attempt == 0 and self._remove_stale_lock():
                    continue
                raise FundedNextRuntimeStateError(
                    "runtime-single-writer-lock-already-held"
                ) from error
            try:
                os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self._held = True
            return
        raise FundedNextRuntimeStateError("runtime-single-writer-lock-unavailable")

    def release(self) -> None:
        if not self._held:
            return
        try:
            self._path.unlink(missing_ok=True)
        finally:
            self._held = False

    def __enter__(self) -> SingleWriterRuntimeLock:
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        del exc_type, exc, tb
        self.release()


def heartbeat_is_fresh(
    state: FundedNextRuntimeState,
    *,
    now: datetime,
    maximum_age: timedelta = timedelta(minutes=2),
) -> bool:
    if now.tzinfo is None or now.utcoffset() is None:
        raise FundedNextRuntimeStateError("heartbeat check requires aware now")
    return state.heartbeat_at <= now and now - state.heartbeat_at <= maximum_age
