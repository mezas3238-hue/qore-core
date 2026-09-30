"""Durable CMA capital-ledger invariants."""
# ruff: noqa: I001

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalLedgerError,
    DurableCapitalSourceLedgerStore,
)


def _ledger() -> CapitalSourceLedger:
    return (
        CapitalSourceLedger()
        .add_source(
            source_id="profit-1",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("20"),
        )
        .reserve(
            reservation_id="r1",
            source_id="profit-1",
            amount_usd=Decimal("8"),
        )
        .deploy("r1")
    )


def test_durable_ledger_round_trip_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "cma-capital-ledger.json"
    first = DurableCapitalSourceLedgerStore(path)
    stored = first.store(_ledger(), expected_generation=0)

    restarted = DurableCapitalSourceLedgerStore(path)
    loaded = restarted.load()

    assert stored.generation == 1
    assert loaded == stored
    assert loaded.ledger.accounts[0].deployed_usd == Decimal("8")


def test_stale_generation_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "cma-capital-ledger.json"
    store = DurableCapitalSourceLedgerStore(path)
    store.store(_ledger(), expected_generation=0)

    with pytest.raises(DurableCapitalLedgerError, match="stale"):
        store.store(_ledger(), expected_generation=0)


def test_existing_writer_lock_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "cma-capital-ledger.json"
    lock = path.with_name(f".{path.name}.writer-lock")
    lock.mkdir()

    with pytest.raises(DurableCapitalLedgerError, match="writer lock"):
        DurableCapitalSourceLedgerStore(path).store(
            _ledger(),
            expected_generation=0,
        )


def test_corrupt_snapshot_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "cma-capital-ledger.json"
    path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(DurableCapitalLedgerError, match="unreadable"):
        DurableCapitalSourceLedgerStore(path).load()


def test_unknown_schema_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "cma-capital-ledger.json"
    path.write_text(
        json.dumps({"schema": "WRONG", "generation": 0}),
        encoding="utf-8",
    )

    with pytest.raises(DurableCapitalLedgerError, match="schema mismatch"):
        DurableCapitalSourceLedgerStore(path).load()


def test_consumed_deployment_remains_consumed_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "cma-capital-ledger.json"
    store = DurableCapitalSourceLedgerStore(path)
    settled = _ledger().settle_deployment(
        "r1",
        returned_capacity_usd=Decimal("3"),
    )
    store.store(settled, expected_generation=0)

    loaded = DurableCapitalSourceLedgerStore(path).load()
    account = loaded.ledger.accounts[0]

    assert account.available_usd == Decimal("15")
    assert account.consumed_usd == Decimal("5")
    assert account.cumulative_released_usd == Decimal("3")
