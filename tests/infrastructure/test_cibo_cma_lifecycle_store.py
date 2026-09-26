from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import CapitalStage
from qore.infrastructure.cibo_cma_lifecycle_store import (
    DurableCmaLifecycleError,
    DurableCmaLifecycleStore,
    VersionedCmaLifecycleBook,
)


NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _register(
    store: DurableCmaLifecycleStore,
) -> VersionedCmaLifecycleBook:
    return store.register_seed(
        signal_fingerprint="signal-1",
        position_id=101,
        observed_at=NOW,
        expected_generation=0,
    )


def test_seed_and_observe_survive_restart(tmp_path: Path) -> None:
    path = tmp_path / "lifecycle.json"
    store = DurableCmaLifecycleStore(path)
    first = _register(store)
    second = store.advance(
        signal_fingerprint="signal-1",
        position_id=101,
        target_stage=CapitalStage.OBSERVE,
        observed_at=NOW + timedelta(seconds=1),
        expected_generation=first.generation,
    )

    restarted = DurableCmaLifecycleStore(path).load()
    record = restarted.record_for(
        signal_fingerprint="signal-1",
        position_id=101,
    )

    assert second.generation == 2
    assert restarted.generation == 2
    assert record is not None
    assert record.stage is CapitalStage.OBSERVE
    assert record.transition_count == 1


def test_direct_seed_to_capitalize_is_rejected(tmp_path: Path) -> None:
    store = DurableCmaLifecycleStore(tmp_path / "lifecycle.json")
    first = _register(store)

    with pytest.raises(ValueError, match="illegal CMA transition"):
        store.advance(
            signal_fingerprint="signal-1",
            position_id=101,
            target_stage=CapitalStage.CAPITALIZE,
            observed_at=NOW + timedelta(seconds=1),
            expected_generation=first.generation,
        )


def test_valid_recovery_path_can_reach_capitalize(tmp_path: Path) -> None:
    store = DurableCmaLifecycleStore(tmp_path / "lifecycle.json")
    book = _register(store)
    for offset, stage in enumerate(
        (
            CapitalStage.OBSERVE,
            CapitalStage.PROTECT_BASE,
            CapitalStage.BASE_RECOVERED,
            CapitalStage.CAPITALIZE,
        ),
        start=1,
    ):
        book = store.advance(
            signal_fingerprint="signal-1",
            position_id=101,
            target_stage=stage,
            observed_at=NOW + timedelta(seconds=offset),
            expected_generation=book.generation,
        )

    record = book.record_for(
        signal_fingerprint="signal-1",
        position_id=101,
    )
    assert record is not None
    assert record.stage is CapitalStage.CAPITALIZE
    assert record.transition_count == 4


def test_release_is_terminal_across_restart(tmp_path: Path) -> None:
    path = tmp_path / "lifecycle.json"
    store = DurableCmaLifecycleStore(path)
    book = _register(store)
    book = store.advance(
        signal_fingerprint="signal-1",
        position_id=101,
        target_stage=CapitalStage.RELEASE,
        observed_at=NOW + timedelta(seconds=1),
        expected_generation=book.generation,
    )

    restarted = DurableCmaLifecycleStore(path)
    with pytest.raises(ValueError, match="illegal CMA transition"):
        restarted.advance(
            signal_fingerprint="signal-1",
            position_id=101,
            target_stage=CapitalStage.CAPITALIZE,
            observed_at=NOW + timedelta(seconds=2),
            expected_generation=book.generation,
        )


def test_stale_generation_cannot_advance_lifecycle(tmp_path: Path) -> None:
    store = DurableCmaLifecycleStore(tmp_path / "lifecycle.json")
    _register(store)

    with pytest.raises(DurableCmaLifecycleError, match="stale"):
        store.advance(
            signal_fingerprint="signal-1",
            position_id=101,
            target_stage=CapitalStage.OBSERVE,
            observed_at=NOW + timedelta(seconds=1),
            expected_generation=0,
        )


def test_time_cannot_move_backwards(tmp_path: Path) -> None:
    store = DurableCmaLifecycleStore(tmp_path / "lifecycle.json")
    book = _register(store)

    with pytest.raises(DurableCmaLifecycleError, match="backwards"):
        store.advance(
            signal_fingerprint="signal-1",
            position_id=101,
            target_stage=CapitalStage.OBSERVE,
            observed_at=NOW - timedelta(seconds=1),
            expected_generation=book.generation,
        )
