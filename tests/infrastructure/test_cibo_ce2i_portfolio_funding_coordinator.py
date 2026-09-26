# ruff: noqa: I001
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CapitalStage,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation
from qore.infrastructure.cibo_ce2i_execution_efficiency import (
    ExecutionCostCurveInput,
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
from qore.infrastructure.cibo_ce2i_portfolio_funding_coordinator import (
    reserve_portfolio_and_funding,
)
from qore.infrastructure.cibo_ce2i_portfolio_funding_saga import (
    DurablePortfolioFundingSagaStore,
    PortfolioFundingSagaState,
)


NOW = datetime(2026, 9, 26, 13, 30, tzinfo=UTC)


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="signal-1",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        stop_loss_per_volume=Decimal("2"),
        margin_per_volume=Decimal("3"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
    )


def _observation(*, capacity: str = "20") -> CmaCapitalObservation:
    amount = Decimal(capacity)
    return CmaCapitalObservation(
        event="CIBO_CMA_CAPITAL_OBSERVATION",
        trader=TraderLineage.R38_EURUSD.value,
        symbol="EURUSD",
        signal_fingerprint="signal-1",
        position_id=101,
        stage=CapitalStage.CAPITALIZE,
        evidence_sufficient=True,
        expansion_eligible=True,
        realized_net_pnl_usd=amount,
        remaining_stop_worst_case_pnl_usd=Decimal("0"),
        net_economic_floor_usd=amount,
        base_capital_at_risk_usd=Decimal("0"),
        protected_open_floor_usd=Decimal("0"),
        self_financing_capacity_usd=amount,
        reason="test",
    )


def _curve(*, maximum: str = "4") -> ExecutionCostCurveInput:
    return ExecutionCostCurveInput(
        evidence_id="curve-1",
        volume_step=Decimal("1"),
        maximum_volume=Decimal(maximum),
        gross_edge_per_volume_usd=Decimal("10"),
        spread_cost_per_volume_usd=Decimal("1"),
        commission_cost_per_volume_usd=Decimal("1"),
        slippage_cost_per_volume_usd=Decimal("0"),
        impact_cost_per_volume_squared_usd=Decimal("0"),
    )


def _candidate(*, risk: str = "8", margin: str = "12") -> CapitalOpportunityCandidate:
    return CapitalOpportunityCandidate(
        signal_fingerprint="signal-1",
        trader_id=TraderLineage.R38_EURUSD,
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        expected_net_value_usd=Decimal("10"),
        stop_risk_usd=Decimal(risk),
        margin_usd=Decimal(margin),
        expected_capital_minutes=Decimal("10"),
        concentration_group="EUR",
        concentration_risk_usd=Decimal(risk),
    )


def _allocation_store(tmp_path: Path) -> DurablePortfolioAllocationStore:
    store = DurablePortfolioAllocationStore(tmp_path / "allocation.json")
    store.initialize(
        PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("20"),
            total_margin_capacity_usd=Decimal("30"),
            concentration_limit_by_group=(("EUR", Decimal("20")),),
        )
    )
    return store


def _funding_store(
    tmp_path: Path,
    *,
    amount: str = "20",
) -> DurableCapitalSourceLedgerStore:
    store = DurableCapitalSourceLedgerStore(tmp_path / "funding.json")
    ledger = CapitalSourceLedger().add_source(
        source_id="profit-1",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal(amount),
    )
    store.store(ledger, expected_generation=0)
    return store


def test_happy_path_reaches_ready_for_risk_with_both_reservations(
    tmp_path: Path,
) -> None:
    allocation = _allocation_store(tmp_path)
    funding = _funding_store(tmp_path)
    saga = DurablePortfolioFundingSagaStore(tmp_path / "saga.json")

    result = reserve_portfolio_and_funding(
        transaction_id="tx-1",
        candidate=_candidate(),
        opportunity=_opportunity(),
        observation=_observation(),
        execution_curve=_curve(),
        assigned_capital_usd=Decimal("10000"),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("30"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        allocation_store=allocation,
        funding_store=funding,
        saga_store=saga,
    )

    assert result.state is PortfolioFundingSagaState.READY_FOR_RISK
    assert result.ready_for_risk is True
    assert result.proposal is not None
    allocation_state = allocation.load()
    assert allocation_state is not None
    assert allocation_state.ledger.used_stop_risk_usd == Decimal("8")
    assert funding.load().ledger.accounts[0].reserved_usd == Decimal("8")


def test_unselected_candidate_rolls_back_without_resource_reservation(
    tmp_path: Path,
) -> None:
    allocation = DurablePortfolioAllocationStore(tmp_path / "allocation.json")
    allocation.initialize(
        PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("1"),
            total_margin_capacity_usd=Decimal("30"),
            concentration_limit_by_group=(("EUR", Decimal("20")),),
        )
    )
    funding = _funding_store(tmp_path)
    saga = DurablePortfolioFundingSagaStore(tmp_path / "saga.json")

    result = reserve_portfolio_and_funding(
        transaction_id="tx-2",
        candidate=_candidate(),
        opportunity=_opportunity(),
        observation=_observation(),
        execution_curve=_curve(),
        assigned_capital_usd=Decimal("10000"),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("30"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        allocation_store=allocation,
        funding_store=funding,
        saga_store=saga,
    )

    assert result.state is PortfolioFundingSagaState.ROLLED_BACK
    allocation_state = allocation.load()
    assert allocation_state is not None
    assert allocation_state.ledger.used_stop_risk_usd == 0
    assert funding.load().ledger.reservations == ()


def test_funding_hold_releases_portfolio_reservation(
    tmp_path: Path,
) -> None:
    allocation = _allocation_store(tmp_path)
    funding = _funding_store(tmp_path, amount="0.5")
    saga = DurablePortfolioFundingSagaStore(tmp_path / "saga.json")

    result = reserve_portfolio_and_funding(
        transaction_id="tx-3",
        candidate=_candidate(),
        opportunity=_opportunity(),
        observation=_observation(capacity="0.5"),
        execution_curve=_curve(),
        assigned_capital_usd=Decimal("10000"),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("30"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        allocation_store=allocation,
        funding_store=funding,
        saga_store=saga,
    )

    assert result.state is PortfolioFundingSagaState.ROLLED_BACK
    allocation_state = allocation.load()
    assert allocation_state is not None
    assert allocation_state.ledger.used_stop_risk_usd == 0
    assert funding.load().ledger.reservations == ()


def test_economic_mismatch_compensates_both_known_reservations(
    tmp_path: Path,
) -> None:
    allocation = _allocation_store(tmp_path)
    funding = _funding_store(tmp_path)
    saga = DurablePortfolioFundingSagaStore(tmp_path / "saga.json")

    result = reserve_portfolio_and_funding(
        transaction_id="tx-4",
        candidate=_candidate(risk="10", margin="15"),
        opportunity=_opportunity(),
        observation=_observation(),
        execution_curve=_curve(),
        assigned_capital_usd=Decimal("10000"),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("30"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        allocation_store=allocation,
        funding_store=funding,
        saga_store=saga,
    )

    assert result.state is PortfolioFundingSagaState.ROLLED_BACK
    allocation_state = allocation.load()
    assert allocation_state is not None
    assert allocation_state.ledger.used_stop_risk_usd == 0
    assert funding.load().ledger.accounts[0].reserved_usd == 0
