# ruff: noqa: I001
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalSourceAccount,
    CapitalSourceLedger,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_store import (
    DurablePortfolioAllocationStore,
)
from qore.infrastructure.cibo_ce2i_portfolio_batch import (
    plan_and_reserve_portfolio_batch,
)


def _candidate(
    fingerprint: str,
    trader: TraderLineage,
    *,
    net: str,
    minutes: str,
    group: str,
) -> CapitalOpportunityCandidate:
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        expected_net_value_usd=Decimal(net),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("10"),
        expected_capital_minutes=Decimal(minutes),
        concentration_group=group,
        concentration_risk_usd=Decimal("5"),
    )


def _allocation_store(tmp_path: Path) -> DurablePortfolioAllocationStore:
    store = DurablePortfolioAllocationStore(tmp_path / "allocation.json")
    store.initialize(
        PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("20"),
            concentration_limit_by_group=(
                ("USD", Decimal("5")),
                ("INDEX", Decimal("5")),
            ),
        )
    )
    return store


def _capital_sources() -> tuple[CapitalSourceAccount, ...]:
    return (
        CapitalSourceLedger()
        .add_source(
            source_id="profit-1",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("20"),
        )
        .accounts
    )


def test_batch_graph_competition_and_reservation_share_one_generation(
    tmp_path: Path,
) -> None:
    store = _allocation_store(tmp_path)
    decision = plan_and_reserve_portfolio_batch(
        candidates=(
            _candidate(
                "eur",
                TraderLineage.R38_EURUSD,
                net="10",
                minutes="20",
                group="USD",
            ),
            _candidate(
                "nas",
                TraderLineage.VT31_NAS100,
                net="9",
                minutes="5",
                group="INDEX",
            ),
        ),
        capital_sources=_capital_sources(),
        allocation_store=store,
    )

    assert decision.selected_signal_fingerprints == ("nas", "eur")
    assert decision.allocation_generation == 2
    persisted = store.load()
    assert persisted is not None
    assert persisted.generation == 2
    assert persisted.ledger.used_stop_risk_usd == Decimal("10")


def test_second_batch_competes_against_persisted_remaining_capacity(
    tmp_path: Path,
) -> None:
    store = _allocation_store(tmp_path)
    first = plan_and_reserve_portfolio_batch(
        candidates=(
            _candidate(
                "nas",
                TraderLineage.VT31_NAS100,
                net="10",
                minutes="5",
                group="INDEX",
            ),
        ),
        capital_sources=_capital_sources(),
        allocation_store=store,
    )
    second = plan_and_reserve_portfolio_batch(
        candidates=(
            _candidate(
                "eur",
                TraderLineage.R38_EURUSD,
                net="8",
                minutes="5",
                group="USD",
            ),
            _candidate(
                "gbp",
                TraderLineage.R43_GBPUSD,
                net="7",
                minutes="5",
                group="USD",
            ),
        ),
        capital_sources=_capital_sources(),
        allocation_store=store,
    )

    assert first.selected_signal_fingerprints == ("nas",)
    assert second.selected_signal_fingerprints == ("eur",)
    persisted = store.load()
    assert persisted is not None
    assert persisted.ledger.used_stop_risk_usd == Decimal("10")


def test_batch_requires_initialized_allocation_store(tmp_path: Path) -> None:
    store = DurablePortfolioAllocationStore(tmp_path / "allocation.json")

    with pytest.raises(CiboCapitalManagementError, match="initialized"):
        plan_and_reserve_portfolio_batch(
            candidates=(),
            capital_sources=(),
            allocation_store=store,
        )
