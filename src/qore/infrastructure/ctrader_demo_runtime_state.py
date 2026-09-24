from __future__ import annotations

import ctypes
import json
import os
import platform
import tempfile
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = "qore.ctrader-demo.runtime-state.v1"
_RETRY_DELAYS = (0.02, 0.05, 0.1, 0.2)


class CTraderDemoRuntimeStateError(RuntimeError):
    pass


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CTraderDemoRuntimeStateError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CTraderDemoRuntimeState:
    git_sha: str
    account_identity_fingerprint: str
    balance: str
    equity: str
    processed_anchors: tuple[str, ...]
    heartbeat_at: datetime
    last_reconciliation_at: datetime
    service_started_at: datetime

    def __post_init__(self) -> None:
        if len(self.git_sha) != 40:
            raise CTraderDemoRuntimeStateError("runtime state requires full git SHA")
        if len(self.account_identity_fingerprint) != 64:
            raise CTraderDemoRuntimeStateError("runtime account fingerprint must be SHA-256")
        for name, value in (
            ("heartbeat_at", self.heartbeat_at),
            ("last_reconciliation_at", self.last_reconciliation_at),
            ("service_started_at", self.service_started_at),
        ):
            _aware(value, name)
        if tuple(sorted(set(self.processed_anchors))) != self.processed_anchors:
            raise CTraderDemoRuntimeStateError("processed anchors must be sorted and unique")

    def with_cycle(
        self,
        *,
        processed_anchor: str | None,
        reconciled_at: datetime,
        heartbeat_at: datetime,
        balance: str | None = None,
        equity: str | None = None,
        highest_closed_balance: str | None = None,
        active_mll: str | None = None,
    ) -> "CTraderDemoRuntimeState":
        # Legacy argument names are accepted only so the frozen trader loop can be
        # migrated incrementally; they are persisted as DEMO balance/equity.
        new_balance = balance if balance is not None else highest_closed_balance
        new_equity = equity if equity is not None else active_mll
        if new_balance is None:
            new_balance = self.balance
        if new_equity is None:
            new_equity = self.equity
        anchors = set(self.processed_anchors)
        if processed_anchor is not None:
            anchors.add(processed_anchor)
        return CTraderDemoRuntimeState(
            git_sha=self.git_sha,
            account_identity_fingerprint=self.account_identity_fingerprint,
            balance=str(new_balance),
            equity=str(new_equity),
            processed_anchors=tuple(sorted(anchors))[-256:],
            heartbeat_at=heartbeat_at,
            last_reconciliation_at=reconciled_at,
            service_started_at=self.service_started_at,
        )

    def restarted_at(self, started_at: datetime) -> "CTraderDemoRuntimeState":
        _aware(started_at, "started_at")
        return replace(
            self,
            heartbeat_at=started_at,
            last_reconciliation_at=started_at,
            service_started_at=started_at,
        )


class DurableCTraderDemoRuntimeStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> CTraderDemoRuntimeState | None:
        if not self._path.exists():
            return None
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if payload.get("schema") != _SCHEMA:
                return None
            return CTraderDemoRuntimeState(
                git_sha=str(payload["git_sha"]),
                account_identity_fingerprint=str(payload["account_identity_fingerprint"]),
                balance=str(payload["balance"]),
                equity=str(payload["equity"]),
                processed_anchors=tuple(str(x) for x in payload["processed_anchors"]),
                heartbeat_at=datetime.fromisoformat(str(payload["heartbeat_at"])),
                last_reconciliation_at=datetime.fromisoformat(str(payload["last_reconciliation_at"])),
                service_started_at=datetime.fromisoformat(str(payload["service_started_at"])),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise CTraderDemoRuntimeStateError("runtime state is unreadable") from error

    def store(self, state: CTraderDemoRuntimeState) -> None:
        if not isinstance(state, CTraderDemoRuntimeState):
            raise CTraderDemoRuntimeStateError("canonical cTrader DEMO runtime state required")
        payload = {
            "schema": _SCHEMA,
            "git_sha": state.git_sha,
            "account_identity_fingerprint": state.account_identity_fingerprint,
            "balance": state.balance,
            "equity": state.equity,
            "processed_anchors": list(state.processed_anchors),
            "heartbeat_at": state.heartbeat_at.astimezone(UTC).isoformat(),
            "last_reconciliation_at": state.last_reconciliation_at.astimezone(UTC).isoformat(),
            "service_started_at": state.service_started_at.astimezone(UTC).isoformat(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self._path.name}.", suffix=".tmp", dir=self._path.parent)
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            for delay in (*_RETRY_DELAYS, None):
                try:
                    os.replace(temp, self._path)
                    break
                except OSError as error:
                    if delay is None:
                        raise CTraderDemoRuntimeStateError("runtime state atomic write failed") from error
                    time.sleep(delay)
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)


class CTraderDemoSingleWriterLock:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._held = False

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        if platform.system() == "Windows":
            win_dll = getattr(ctypes, "WinDLL", None)
            get_last_error = getattr(ctypes, "get_last_error", None)
            if win_dll is None or get_last_error is None:
                return True
            kernel32 = win_dll("kernel32", use_last_error=True)
            handle = int(kernel32.OpenProcess(0x1000, False, pid))
            if handle == 0:
                return int(get_last_error()) == 5
            try:
                exit_code = ctypes.c_ulong()
                if int(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) == 0:
                    return True
                return int(exit_code.value) == 259
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

    def _remove_stale(self) -> bool:
        try:
            pid = int(self._path.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return False
        if self._pid_alive(pid):
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
                fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as error:
                if attempt == 0 and self._remove_stale():
                    continue
                raise CTraderDemoRuntimeStateError("ctrader-demo-single-writer-lock-already-held") from error
            try:
                os.write(fd, f"{os.getpid()}\n".encode("ascii"))
                os.fsync(fd)
            finally:
                os.close(fd)
            self._held = True
            return
        raise CTraderDemoRuntimeStateError("ctrader-demo-single-writer-lock-unavailable")

    def release(self) -> None:
        if not self._held:
            return
        try:
            self._path.unlink(missing_ok=True)
        finally:
            self._held = False

    def __enter__(self) -> "CTraderDemoSingleWriterLock":
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        del exc_type, exc, tb
        self.release()
