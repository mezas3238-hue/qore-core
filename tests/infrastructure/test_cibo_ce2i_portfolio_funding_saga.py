# ruff: noqa: I001
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.cibo_ce2i_portfolio_funding_saga import (
    DurablePortfolioFundingSagaError,
    DurablePortfolioFundingSagaStore,
    PortfolioFundingSagaState,
    VersionedPortfolioFundingSagaBook,
)


NOW = datetime(2026, 9, 26, 13, 0, tzinfo=UTC)


def _prepare(
    store: DurablePortfolioFundingSagaStore,
) -> VersionedPortfolioFundingSagaBook:
    return store.prepare(
        transaction_id="tx-1",
        signal_fingerprint="signal-1",
        funding_reservation_prefix="tx-1",
        updated_at=NOW,
        expected_generation=0,
    )


def test_saga_intent_survives_restart_before_any_resource_reservation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "saga.json"
    store = DurablePortfolioFundingSagaStore(path)
    prepared = _prepare(store)

    restarted = DurablePortfolioFundingSagaStore(path).load()
    record = restarted.record_for("tx-1")

    assert prepared.generation == 1
    assert record is not None
    assert record.state is PortfolioFundingSagaState.PREPARED
    assert record.portfolio_generation is None
    assert record.funding_generation is None


def test_happy_path_records_portfolio_funding_then_ready_for_risk(
    tmp_path: Path,
) -> None:
    store = DurablePortfolioFundingSagaStore(tmp_path / "saga.json")
    book = _prepare(store)
    book = store.transition(
        transaction_id="tx-1",
        target=PortfolioFundingSagaState.PORTFOLIO_RESERVED,
        updated_at=NOW + timedelta(seconds=1),
        expected_generation=book.generation,
        reason="portfolio reservation durable",
        portfolio_generation=7,
    )
    book = store.transition(
        transaction_id="tx-1",
        target=PortfolioFundingSagaState.FUNDING_RESERVED,
        updated_at=NOW + timedelta(seconds=2),
        expected_generation=book.generation,
        reason="funding reservation durable",
        funding_generation=11,
    )
    book = store.transition(
        transaction_id="tx-1",
        target=PortfolioFundingSagaState.READY_FOR_RISK,
        updated_at=NOW + timedelta(seconds=3),
        expected_generation=book.generation,
        reason="both resource reservations reconciled",
    )

    record = book.record_for("tx-1")
    assert record is not None
    assert record.state is PortfolioFundingSagaState.READY_FOR_RISK
    assert record.portfolio_generation == 7
    assert record.funding_generation == 11


def test_cannot_skip_portfolio_reservation_stage(tmp_path: Path) -> None:
    store = DurablePortfolioFundingSagaStore(tmp_path / "saga.json")
    book = _prepare(store)

    with pytest.raises(DurablePortfolioFundingSagaError, match="illegal"):
        store.transition(
            transaction_id="tx-1",
            target=PortfolioFundingSagaState.FUNDING_RESERVED,
            updated_at=NOW + timedelta(seconds=1),
            expected_generation=book.generation,
            reason="invalid skip",
            funding_generation=2,
        )


def test_compensation_and_rollback_are_explicit(tmp_path: Path) -> None:
    store = DurablePortfolioFundingSagaStore(tmp_path / "saga.json")
    book = _prepare(store)
    book = store.transition(
        transaction_id="tx-1",
        target=PortfolioFundingSagaState.PORTFOLIO_RESERVED,
        updated_at=NOW + timedelta(seconds=1),
        expected_generation=book.generation,
        reason="portfolio reserved",
        portfolio_generation=2,
    )
    book = store.transition(
        transaction_id="tx-1",
        target=PortfolioFundingSagaState.COMPENSATION_REQUIRED,
        updated_at=NOW + timedelta(seconds=2),
        expected_generation=book.generation,
        reason="funding reservation failed",
    )
    book = store.transition(
        transaction_id="tx-1",
        target=PortfolioFundingSagaState.ROLLED_BACK,
        updated_at=NOW + timedelta(seconds=3),
        expected_generation=book.generation,
        reason="portfolio reservation released and funding absent",
    )

    record = book.record_for("tx-1")
    assert record is not None
    assert record.state is PortfolioFundingSagaState.ROLLED_BACK


def test_ready_for_risk_is_not_terminal_when_compensation_is_needed(
    tmp_path: Path,
) -> None:
    store = DurablePortfolioFundingSagaStore(tmp_path / "saga.json")
    book = _prepare(store)
    for offset, target, kwargs in (
        (
            1,
            PortfolioFundingSagaState.PORTFOLIO_RESERVED,
            {"portfolio_generation": 2},
        ),
        (
            2,
            PortfolioFundingSagaState.FUNDING_RESERVED,
            {"funding_generation": 3},
        ),
        (3, PortfolioFundingSagaState.READY_FOR_RISK, {}),
    ):
        book = store.transition(
            transaction_id="tx-1",
            target=target,
            updated_at=NOW + timedelta(seconds=offset),
            expected_generation=book.generation,
            reason=f"advance to {target.value}",
            **kwargs,
        )

    compensated = store.transition(
        transaction_id="tx-1",
        target=PortfolioFundingSagaState.COMPENSATION_REQUIRED,
        updated_at=NOW + timedelta(seconds=4),
        expected_generation=book.generation,
        reason="Risk rejected before deployment",
    )
    record = compensated.record_for("tx-1")
    assert record is not None
    assert record.state is PortfolioFundingSagaState.COMPENSATION_REQUIRED


def test_stale_generation_cannot_rewrite_saga(tmp_path: Path) -> None:
    store = DurablePortfolioFundingSagaStore(tmp_path / "saga.json")
    _prepare(store)

    with pytest.raises(DurablePortfolioFundingSagaError, match="stale"):
        store.prepare(
            transaction_id="tx-2",
            signal_fingerprint="signal-2",
            funding_reservation_prefix="tx-2",
            updated_at=NOW,
            expected_generation=0,
        )


def test_corrupt_journal_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "saga.json"
    path.write_text("{bad-json", encoding="utf-8")

    with pytest.raises(DurablePortfolioFundingSagaError, match="unreadable"):
        DurablePortfolioFundingSagaStore(path).load()
