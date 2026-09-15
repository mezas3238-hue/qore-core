from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


def test_runtime_state_round_trips_atomically(tmp_path) -> None:
    store = DurableFundedNextRuntimeStateStore(tmp_path / "state.json")
    assert store.load() is None
    store.store(_state())
    assert store.load() == _state()


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


def test_single_writer_lock_rejects_second_runtime(tmp_path) -> None:
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


def test_heartbeat_freshness_is_fail_closed() -> None:
    assert heartbeat_is_fresh(_state(), now=_NOW + timedelta(seconds=30)) is True
    assert heartbeat_is_fresh(_state(), now=_NOW + timedelta(minutes=3)) is False
