from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.fundednext_runtime_state import (
    DurableFundedNextRuntimeStateStore,
    FundedNextRuntimeState,
    FundedNextRuntimeStateError,
    SingleWriterRuntimeLock,
    heartbeat_is_fresh,
)

_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)


def _state() -> FundedNextRuntimeState:
    return FundedNextRuntimeState(
        git_sha="a" * 40,
        account_identity_fingerprint="b" * 64,
        highest_closed_balance="2000",
        active_mll="1880",
        processed_anchors=("GBPUSD|2026-09-15T09:00:00+00:00",),
        heartbeat_at=_NOW,
        last_reconciliation_at=_NOW,
        service_started_at=_NOW,
    )


def test_runtime_state_round_trips_atomically(tmp_path: Path) -> None:
    store = DurableFundedNextRuntimeStateStore(tmp_path / "state.json")
    assert store.load() is None
    store.store(_state())
    assert store.load() == _state()


def test_runtime_state_retries_transient_windows_replace_contention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state.json"
    store = DurableFundedNextRuntimeStateStore(path)
    real_replace = os.replace
    attempts = 0
    delays: list[float] = []

    def replace_with_transient_contention(source: Path, target: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("reader temporarily denies delete sharing")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", replace_with_transient_contention)
    monkeypatch.setattr("qore.infrastructure.fundednext_runtime_state.time.sleep", delays.append)

    store.store(_state())

    assert store.load() == _state()
    assert attempts == 3
    assert delays == [0.01, 0.02]


def test_runtime_state_fails_closed_after_bounded_replace_contention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = DurableFundedNextRuntimeStateStore(tmp_path / "state.json")
    delays: list[float] = []

    def replace_blocked(_source: Path, _target: Path) -> None:
        raise PermissionError("persistent delete-sharing violation")

    monkeypatch.setattr(os, "replace", replace_blocked)
    monkeypatch.setattr("qore.infrastructure.fundednext_runtime_state.time.sleep", delays.append)

    with pytest.raises(FundedNextRuntimeStateError, match="atomic write failed"):
        store.store(_state())

    assert sum(delays) < 1.0
    assert not tuple(tmp_path.glob("*.tmp"))


def test_processed_anchor_is_durable_and_unique() -> None:
    state = _state().with_cycle(
        highest_closed_balance="2010",
        active_mll="1890",
        processed_anchor="GBPUSD|2026-09-15T09:00:00+00:00",
        reconciled_at=_NOW + timedelta(seconds=10),
        heartbeat_at=_NOW + timedelta(seconds=10),
    )
    assert len(state.processed_anchors) == 1
    assert state.highest_closed_balance == "2010"


def test_restart_refreshes_service_and_reconciliation_timestamps() -> None:
    restarted = _state().restarted_at(_NOW + timedelta(minutes=5))
    assert restarted.service_started_at == _NOW + timedelta(minutes=5)
    assert restarted.heartbeat_at == restarted.service_started_at
    assert restarted.last_reconciliation_at == restarted.service_started_at
    assert restarted.processed_anchors == _state().processed_anchors


def test_single_writer_lock_rejects_second_runtime(tmp_path: Path) -> None:
    path = tmp_path / "runtime.lock"
    first = SingleWriterRuntimeLock(path)
    second = SingleWriterRuntimeLock(path)
    first.acquire()
    try:
        with pytest.raises(FundedNextRuntimeStateError, match="already-held"):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()


def test_pid_liveness_probe_never_interrupts_current_process() -> None:
    assert SingleWriterRuntimeLock._pid_is_alive(os.getpid()) is True


def test_single_writer_lock_recovers_stale_crash_pid(tmp_path: Path) -> None:
    path = tmp_path / "runtime.lock"
    path.write_text("99999999\n", encoding="ascii")
    lock = SingleWriterRuntimeLock(path)
    lock.acquire()
    try:
        assert path.exists()
    finally:
        lock.release()


def test_heartbeat_freshness_is_fail_closed() -> None:
    assert heartbeat_is_fresh(_state(), now=_NOW + timedelta(seconds=30)) is True
    assert heartbeat_is_fresh(_state(), now=_NOW + timedelta(minutes=3)) is False
