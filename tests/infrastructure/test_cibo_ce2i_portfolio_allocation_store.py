# ruff: noqa: I001
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
    PortfolioAllocationReservationState,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_store import (
    DurablePortfolioAllocationError,
    DurablePortfolioAllocationStore,
)


def _ledger() -> PortfolioAllocationLedger:
    return PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=Decimal("10"),
        total_margin_capacity_usd=Decimal("20"),
        concentration_limit_by_group=(
            ("USD", Decimal("7")),
            ("INDEX", Decimal("5")),
        ),
    )


def _candidate() -> CapitalOpportunityCandidate:
    return CapitalOpportunityCandidate(
        signal_fingerprint="signal-1",
        trader_id=TraderLineage.R38_EURUSD,
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        decision_as_of=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
        expectation=CausalOpportunityExpectation(
            evidence_id="test:expectation:signal-1",
            as_of=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
            basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
            expected_net_value_usd=Decimal("10"),
            ),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("10"),
        expected_capital_minutes=Decimal("10"),
        concentration_group="USD",
        concentration_risk_usd=Decimal("5"),
    )


def test_allocation_reservation_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "allocation.json"
    store = DurablePortfolioAllocationStore(path)
    initialized = store.initialize(_ledger())
    allocated, _ = initialized.ledger.allocate_and_reserve((_candidate(),))
    stored = store.store(
        allocated,
        expected_generation=initialized.generation,
    )

    restarted = DurablePortfolioAllocationStore(path).load()

    assert restarted is not None
    assert restarted.generation == stored.generation
    assert restarted.ledger.used_stop_risk_usd == Decimal("5")
    assert restarted.ledger.used_margin_usd == Decimal("10")
    assert restarted.ledger.active_reservations[0].signal_fingerprint == (
        "signal-1"
    )


def test_release_persists_and_restores_capacity(tmp_path: Path) -> None:
    path = tmp_path / "allocation.json"
    store = DurablePortfolioAllocationStore(path)
    initialized = store.initialize(_ledger())
    allocated, _ = initialized.ledger.allocate_and_reserve((_candidate(),))
    stored = store.store(
        allocated,
        expected_generation=initialized.generation,
    )
    released = stored.ledger.release("signal-1")
    final = store.store(
        released,
        expected_generation=stored.generation,
    )

    assert final.ledger.used_stop_risk_usd == 0
    assert final.ledger.used_margin_usd == 0
    assert final.ledger.reservations[0].state is (
        PortfolioAllocationReservationState.RELEASED
    )


def test_stale_generation_cannot_overwrite_active_allocations(
    tmp_path: Path,
) -> None:
    store = DurablePortfolioAllocationStore(tmp_path / "allocation.json")
    initialized = store.initialize(_ledger())
    allocated, _ = initialized.ledger.allocate_and_reserve((_candidate(),))
    store.store(
        allocated,
        expected_generation=initialized.generation,
    )

    with pytest.raises(DurablePortfolioAllocationError, match="stale"):
        store.store(
            _ledger(),
            expected_generation=initialized.generation,
        )


def test_store_cannot_be_initialized_twice(tmp_path: Path) -> None:
    store = DurablePortfolioAllocationStore(tmp_path / "allocation.json")
    store.initialize(_ledger())

    with pytest.raises(DurablePortfolioAllocationError, match="already"):
        store.initialize(_ledger())


def test_corrupt_store_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "allocation.json"
    path.write_text("{bad-json", encoding="utf-8")

    with pytest.raises(DurablePortfolioAllocationError, match="unreadable"):
        DurablePortfolioAllocationStore(path).load()
