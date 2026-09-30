from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.cibo_integrated_capital_transaction_store import (
    DurableIntegratedCapitalTransactionStore,
    IntegratedCapitalComponent,
    IntegratedCapitalComponentRef,
    IntegratedCapitalTransactionError,
)

T0 = datetime(2026, 9, 30, 2, 30, tzinfo=UTC)


def _refs(*, generation: int, digit: str):
    return tuple(
        IntegratedCapitalComponentRef(
            component=component,
            generation=generation,
            sha256="sha256:" + digit * 64,
        )
        for component in IntegratedCapitalComponent
    )


def test_integrated_transaction_restart_detects_unresolved_prepare(
    tmp_path: Path,
) -> None:
    path = tmp_path / "integrated-tx.json"
    store = DurableIntegratedCapitalTransactionStore(path)
    prepared = store.prepare(
        transaction_id="tx-1",
        before_refs=_refs(generation=1, digit="1"),
        after_refs=_refs(generation=2, digit="2"),
        capital_truth_before_sha256="sha256:" + "3" * 64,
        capital_truth_after_sha256="sha256:" + "4" * 64,
        prepared_at=T0,
        expected_generation=0,
    )

    assert prepared.generation == 1
    assert prepared.unresolved_transaction_ids == ("tx-1",)

    restarted = DurableIntegratedCapitalTransactionStore(path).load()
    assert restarted.generation == 1
    assert restarted.unresolved_transaction_ids == ("tx-1",)


def test_unresolved_prepare_blocks_next_transaction(
    tmp_path: Path,
) -> None:
    store = DurableIntegratedCapitalTransactionStore(tmp_path / "tx.json")
    store.prepare(
        transaction_id="tx-1",
        before_refs=_refs(generation=1, digit="1"),
        after_refs=_refs(generation=2, digit="2"),
        capital_truth_before_sha256="sha256:" + "3" * 64,
        capital_truth_after_sha256="sha256:" + "4" * 64,
        prepared_at=T0,
        expected_generation=0,
    )

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="unresolved integrated transaction",
    ):
        store.prepare(
            transaction_id="tx-2",
            before_refs=_refs(generation=2, digit="2"),
            after_refs=_refs(generation=3, digit="5"),
            capital_truth_before_sha256="sha256:" + "4" * 64,
            capital_truth_after_sha256="sha256:" + "6" * 64,
            prepared_at=T0 + timedelta(seconds=1),
            expected_generation=1,
        )


def test_commit_requires_exact_component_and_truth_target(
    tmp_path: Path,
) -> None:
    store = DurableIntegratedCapitalTransactionStore(tmp_path / "tx.json")
    store.prepare(
        transaction_id="tx-1",
        before_refs=_refs(generation=1, digit="1"),
        after_refs=_refs(generation=2, digit="2"),
        capital_truth_before_sha256="sha256:" + "3" * 64,
        capital_truth_after_sha256="sha256:" + "4" * 64,
        prepared_at=T0,
        expected_generation=0,
    )

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="component state differs",
    ):
        store.commit(
            transaction_id="tx-1",
            observed_after_refs=_refs(generation=2, digit="7"),
            observed_capital_truth_sha256="sha256:" + "4" * 64,
            committed_at=T0 + timedelta(seconds=1),
            expected_generation=1,
        )

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="capital truth differs",
    ):
        store.commit(
            transaction_id="tx-1",
            observed_after_refs=_refs(generation=2, digit="2"),
            observed_capital_truth_sha256="sha256:" + "8" * 64,
            committed_at=T0 + timedelta(seconds=1),
            expected_generation=1,
        )


def test_exact_commit_closes_transaction_and_hash_chain_survives_restart(
    tmp_path: Path,
) -> None:
    path = tmp_path / "integrated-tx.json"
    store = DurableIntegratedCapitalTransactionStore(path)
    store.prepare(
        transaction_id="tx-1",
        before_refs=_refs(generation=1, digit="1"),
        after_refs=_refs(generation=2, digit="2"),
        capital_truth_before_sha256="sha256:" + "3" * 64,
        capital_truth_after_sha256="sha256:" + "4" * 64,
        prepared_at=T0,
        expected_generation=0,
    )
    committed = store.commit(
        transaction_id="tx-1",
        observed_after_refs=_refs(generation=2, digit="2"),
        observed_capital_truth_sha256="sha256:" + "4" * 64,
        committed_at=T0 + timedelta(seconds=1),
        expected_generation=1,
    )

    assert committed.generation == 2
    assert committed.unresolved_transaction_ids == ()
    assert len(committed.events) == 2
    assert committed.events[1].previous_event_sha256 == (
        committed.events[0].fingerprint()
    )

    restarted = DurableIntegratedCapitalTransactionStore(path).load()
    assert restarted == committed


def test_transaction_store_rejects_stale_generation(
    tmp_path: Path,
) -> None:
    store = DurableIntegratedCapitalTransactionStore(tmp_path / "tx.json")
    store.prepare(
        transaction_id="tx-1",
        before_refs=_refs(generation=1, digit="1"),
        after_refs=_refs(generation=2, digit="2"),
        capital_truth_before_sha256="sha256:" + "3" * 64,
        capital_truth_after_sha256="sha256:" + "4" * 64,
        prepared_at=T0,
        expected_generation=0,
    )

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="stale integrated transaction generation",
    ):
        store.commit(
            transaction_id="tx-1",
            observed_after_refs=_refs(generation=2, digit="2"),
            observed_capital_truth_sha256="sha256:" + "4" * 64,
            committed_at=T0 + timedelta(seconds=1),
            expected_generation=0,
        )


def test_transaction_component_coverage_is_non_compensatory(
    tmp_path: Path,
) -> None:
    refs = _refs(generation=1, digit="1")[:-1]
    store = DurableIntegratedCapitalTransactionStore(tmp_path / "tx.json")

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="component coverage is incomplete",
    ):
        store.prepare(
            transaction_id="tx-1",
            before_refs=refs,
            after_refs=refs,
            capital_truth_before_sha256="sha256:" + "3" * 64,
            capital_truth_after_sha256="sha256:" + "4" * 64,
            prepared_at=T0,
            expected_generation=0,
        )
