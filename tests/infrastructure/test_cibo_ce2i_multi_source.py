# ruff: noqa: I001
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CapitalStage,
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalSourceLedger,
    ReservationState,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation
from qore.infrastructure.cibo_ce2i_multi_source import (
    deploy_multi_source_expansion,
    multi_source_reservation_states,
    release_multi_source_expansion,
    reserve_multi_source_expansion,
)


NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


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


def _observation() -> CmaCapitalObservation:
    return CmaCapitalObservation(
        event="CIBO_CMA_CAPITAL_OBSERVATION",
        trader=TraderLineage.R38_EURUSD.value,
        symbol="EURUSD",
        signal_fingerprint="signal-1",
        position_id=101,
        stage=CapitalStage.CAPITALIZE,
        evidence_sufficient=True,
        expansion_eligible=True,
        realized_net_pnl_usd=Decimal("5"),
        remaining_stop_worst_case_pnl_usd=Decimal("0"),
        net_economic_floor_usd=Decimal("12"),
        base_capital_at_risk_usd=Decimal("0"),
        protected_open_floor_usd=Decimal("7"),
        self_financing_capacity_usd=Decimal("12"),
        reason="test",
    )


def _store(tmp_path: Path) -> DurableCapitalSourceLedgerStore:
    store = DurableCapitalSourceLedgerStore(tmp_path / "multi-source.json")
    ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id="realized-1",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("5"),
        )
        .add_source(
            source_id="protected-1",
            source=CapitalSource.PROTECTED_ECONOMIC_FLOOR,
            proven_amount_usd=Decimal("7"),
        )
    )
    store.store(ledger, expected_generation=0)
    return store


def test_multi_source_combines_realized_then_protected_atomically(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    proposal = reserve_multi_source_expansion(
        reservation_group_id="group-1",
        request_id="risk-1",
        opportunity=_opportunity(),
        observation=_observation(),
        assigned_capital_usd=Decimal("10000"),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("100"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        ledger_store=store,
        maximum_expansion_volume=Decimal("6"),
    )

    assert proposal.volume == Decimal("6")
    assert proposal.stop_risk_usd == Decimal("12")
    assert proposal.risk_request.requested_volume == Decimal("6")
    assert tuple(item.amount_usd for item in proposal.funding_slices) == (
        Decimal("5"),
        Decimal("7"),
    )
    assert tuple(item.source for item in proposal.funding_slices) == (
        CapitalSource.REALIZED_PROFIT,
        CapitalSource.PROTECTED_ECONOMIC_FLOOR,
    )
    assert multi_source_reservation_states(
        proposal,
        ledger_store=store,
    ) == (ReservationState.RESERVED, ReservationState.RESERVED)


def test_multi_source_never_exceeds_observed_source_evidence(
    tmp_path: Path,
) -> None:
    store = DurableCapitalSourceLedgerStore(tmp_path / "multi-source.json")
    ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id="realized-a",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("20"),
        )
        .add_source(
            source_id="protected-a",
            source=CapitalSource.PROTECTED_ECONOMIC_FLOOR,
            proven_amount_usd=Decimal("20"),
        )
    )
    store.store(ledger, expected_generation=0)

    proposal = reserve_multi_source_expansion(
        reservation_group_id="group-2",
        request_id="risk-2",
        opportunity=_opportunity(),
        observation=_observation(),
        assigned_capital_usd=Decimal("10000"),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("100"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        ledger_store=store,
    )

    assert proposal.stop_risk_usd == Decimal("12")
    assert sum(
        (item.amount_usd for item in proposal.funding_slices),
        Decimal(0),
    ) == Decimal("12")


def test_single_source_case_is_rejected_from_multi_source_path(
    tmp_path: Path,
) -> None:
    store = DurableCapitalSourceLedgerStore(tmp_path / "single.json")
    ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id="realized-1",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("20"),
        )
        .add_source(
            source_id="protected-1",
            source=CapitalSource.PROTECTED_ECONOMIC_FLOOR,
            proven_amount_usd=Decimal("1"),
        )
    )
    store.store(ledger, expected_generation=0)

    with pytest.raises(CiboCapitalManagementError, match="single source"):
        reserve_multi_source_expansion(
            reservation_group_id="group-3",
            request_id="risk-3",
            opportunity=_opportunity(),
            observation=_observation(),
            assigned_capital_usd=Decimal("10000"),
            hard_risk_headroom_usd=Decimal("100"),
            margin_headroom_usd=Decimal("100"),
            requested_at=NOW,
            expires_at=NOW + timedelta(seconds=30),
            ledger_store=store,
            maximum_expansion_volume=Decimal("2"),
        )


def test_deploy_and_release_apply_to_every_slice(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proposal = reserve_multi_source_expansion(
        reservation_group_id="group-4",
        request_id="risk-4",
        opportunity=_opportunity(),
        observation=_observation(),
        assigned_capital_usd=Decimal("10000"),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("100"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        ledger_store=store,
        maximum_expansion_volume=Decimal("6"),
    )
    deploy_multi_source_expansion(proposal, ledger_store=store)
    assert multi_source_reservation_states(
        proposal,
        ledger_store=store,
    ) == (ReservationState.DEPLOYED, ReservationState.DEPLOYED)


def test_release_unused_multi_source_returns_every_slice(tmp_path: Path) -> None:
    store = _store(tmp_path)
    proposal = reserve_multi_source_expansion(
        reservation_group_id="group-5",
        request_id="risk-5",
        opportunity=_opportunity(),
        observation=_observation(),
        assigned_capital_usd=Decimal("10000"),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("100"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        ledger_store=store,
        maximum_expansion_volume=Decimal("6"),
    )
    version = release_multi_source_expansion(
        proposal,
        ledger_store=store,
    )

    assert multi_source_reservation_states(
        proposal,
        ledger_store=store,
    ) == (ReservationState.RELEASED, ReservationState.RELEASED)
    assert all(account.available_usd == account.proven_amount_usd for account in version.ledger.accounts)
