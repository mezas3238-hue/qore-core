# ruff: noqa: I001
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
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


def _candidate(
    fingerprint: str,
    trader: TraderLineage,
    *,
    net: str,
    risk: str = "5",
    margin: str = "10",
    minutes: str = "10",
    group: str = "USD",
    concentration: str = "5",
) -> CapitalOpportunityCandidate:
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        decision_as_of=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
        expectation=CausalOpportunityExpectation(
            evidence_id=f"test:expectation:{fingerprint}",
            as_of=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
            basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
            expected_net_value_usd=Decimal(net),
            ),
        stop_risk_usd=Decimal(risk),
        margin_usd=Decimal(margin),
        expected_capital_minutes=Decimal(minutes),
        concentration_group=group,
        concentration_risk_usd=Decimal(concentration),
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


def test_competition_and_reservation_are_one_atomic_ledger_transition() -> None:
    ledger, decision = _ledger().allocate_and_reserve(
        (
            _candidate(
                "fast",
                TraderLineage.R43_GBPUSD,
                net="10",
                minutes="5",
            ),
            _candidate(
                "slow",
                TraderLineage.R38_EURUSD,
                net="10",
                minutes="20",
            ),
        )
    )

    assert decision.selected_signal_fingerprints == ("fast",)
    assert ledger.used_stop_risk_usd == Decimal("5")
    assert ledger.used_margin_usd == Decimal("10")
    assert ledger.active_reservations[0].signal_fingerprint == "fast"


def test_second_batch_sees_only_remaining_shared_capacity() -> None:
    first, _ = _ledger().allocate_and_reserve(
        (
            _candidate(
                "a",
                TraderLineage.R38_EURUSD,
                net="10",
                group="INDEX",
                concentration="5",
            ),
        )
    )
    second, decision = first.allocate_and_reserve(
        (
            _candidate(
                "b",
                TraderLineage.VT31_NAS100,
                net="20",
                group="INDEX",
                concentration="5",
            ),
            _candidate(
                "c",
                TraderLineage.R43_GBPUSD,
                net="8",
                group="USD",
                concentration="5",
            ),
        )
    )

    assert decision.selected_signal_fingerprints == ("c",)
    assert second.used_stop_risk_usd == Decimal("10")
    assert dict(second.active_concentration_by_group) == {
        "INDEX": Decimal("5"),
        "USD": Decimal("5"),
    }


def test_release_restores_risk_margin_and_concentration_capacity() -> None:
    reserved, _ = _ledger().allocate_and_reserve(
        (
            _candidate(
                "a",
                TraderLineage.R38_EURUSD,
                net="10",
                group="INDEX",
                concentration="5",
            ),
        )
    )
    released = reserved.release("a")
    budget = released.remaining_budget()

    assert released.used_stop_risk_usd == 0
    assert released.used_margin_usd == 0
    assert budget.stop_risk_headroom_usd == Decimal("10")
    assert budget.margin_headroom_usd == Decimal("20")
    assert dict(budget.concentration_limit_by_group)["INDEX"] == Decimal("5")
    assert released.reservations[0].state is (
        PortfolioAllocationReservationState.RELEASED
    )


def test_same_signal_cannot_hold_two_active_allocations() -> None:
    reserved, _ = _ledger().allocate_and_reserve(
        (
            _candidate(
                "a",
                TraderLineage.R38_EURUSD,
                net="10",
            ),
        )
    )

    with pytest.raises(CiboCapitalManagementError, match="already has active"):
        reserved.allocate_and_reserve(
            (
                _candidate(
                    "a",
                    TraderLineage.R38_EURUSD,
                    net="20",
                ),
            )
        )


def test_unselected_opportunity_never_reserves_capacity() -> None:
    ledger, decision = _ledger().allocate_and_reserve(
        (
            _candidate(
                "good",
                TraderLineage.R38_EURUSD,
                net="10",
            ),
            _candidate(
                "bad",
                TraderLineage.R43_GBPUSD,
                net="-1",
            ),
        )
    )

    assert decision.selected_signal_fingerprints == ("good",)
    assert tuple(
        item.signal_fingerprint for item in ledger.active_reservations
    ) == ("good",)
