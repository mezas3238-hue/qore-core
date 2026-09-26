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
from qore.infrastructure.cibo_ce2i_expansion_proposal import (
    CmaExpansionProposal,
    deploy_reserved_expansion,
    release_rejected_expansion,
    reserve_expansion_proposal,
    reservation_state,
    settle_expansion_capacity,
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
        intended_entry=Decimal("1.1000"),
        stop_loss=Decimal("1.0950"),
        take_profit=Decimal("1.1100"),
        stop_loss_per_volume=Decimal("100"),
        margin_per_volume=Decimal("200"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("10"),
    )


def _observation(
    *,
    realized: str = "10",
    protected: str = "0",
    capacity: str = "10",
    eligible: bool = True,
) -> CmaCapitalObservation:
    return CmaCapitalObservation(
        event="CIBO_CMA_CAPITAL_OBSERVATION",
        trader=TraderLineage.R38_EURUSD.value,
        symbol="EURUSD",
        signal_fingerprint="signal-1",
        position_id=101,
        stage=CapitalStage.CAPITALIZE if eligible else CapitalStage.PROTECT_BASE,
        evidence_sufficient=eligible,
        expansion_eligible=eligible,
        realized_net_pnl_usd=Decimal(realized),
        remaining_stop_worst_case_pnl_usd=Decimal("0"),
        net_economic_floor_usd=Decimal(capacity) if eligible else Decimal("-1"),
        base_capital_at_risk_usd=Decimal("0") if eligible else Decimal("1"),
        protected_open_floor_usd=Decimal(protected),
        self_financing_capacity_usd=Decimal(capacity) if eligible else Decimal("0"),
        reason="test",
    )


def _store(
    tmp_path: Path,
    *,
    source: CapitalSource = CapitalSource.REALIZED_PROFIT,
    amount: str = "20",
) -> DurableCapitalSourceLedgerStore:
    store = DurableCapitalSourceLedgerStore(tmp_path / "capital-ledger.json")
    ledger = CapitalSourceLedger().add_source(
        source_id="source-1",
        source=source,
        proven_amount_usd=Decimal(amount),
    )
    store.store(ledger, expected_generation=0)
    return store


def _reserve(
    tmp_path: Path,
    *,
    source: CapitalSource = CapitalSource.REALIZED_PROFIT,
    observation: CmaCapitalObservation | None = None,
) -> tuple[DurableCapitalSourceLedgerStore, CmaExpansionProposal]:
    store = _store(tmp_path, source=source)
    proposal = reserve_expansion_proposal(
        reservation_id="expansion-1",
        source_id="source-1",
        opportunity=_opportunity(),
        observation=observation or _observation(),
        hard_risk_headroom_usd=Decimal("50"),
        margin_headroom_usd=Decimal("1000"),
        assigned_capital_usd=Decimal("10000"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        request_id="risk-expansion-1",
        ledger_store=store,
    )
    return store, proposal


def test_realized_profit_expansion_is_reserved_before_risk_handoff(
    tmp_path: Path,
) -> None:
    store, proposal = _reserve(tmp_path)

    assert proposal.source is CapitalSource.REALIZED_PROFIT
    assert proposal.plan.stop_risk_usd == Decimal("10")
    assert proposal.plan.volume == Decimal("0.10")
    assert proposal.risk_request.requested_volume == Decimal("0.10")
    assert reservation_state(
        proposal,
        ledger_store=store,
    ) is ReservationState.RESERVED
    account = store.load().ledger.accounts[0]
    assert account.available_usd == Decimal("10")
    assert account.reserved_usd == Decimal("10")


def test_observation_capacity_caps_larger_ledger_source(tmp_path: Path) -> None:
    store, proposal = _reserve(
        tmp_path,
        observation=_observation(realized="50", capacity="7"),
    )

    assert proposal.plan.stop_risk_usd == Decimal("7")
    assert store.load().ledger.accounts[0].reserved_usd == Decimal("7")


def test_protected_floor_expansion_uses_only_protected_capacity(
    tmp_path: Path,
) -> None:
    store, proposal = _reserve(
        tmp_path,
        source=CapitalSource.PROTECTED_ECONOMIC_FLOOR,
        observation=_observation(
            realized="0",
            protected="8",
            capacity="8",
        ),
    )

    assert proposal.source is CapitalSource.PROTECTED_ECONOMIC_FLOOR
    assert proposal.plan.stop_risk_usd == Decimal("8")
    assert store.load().ledger.accounts[0].reserved_usd == Decimal("8")


def test_original_base_capital_cannot_be_selected_for_expansion(
    tmp_path: Path,
) -> None:
    store = _store(
        tmp_path,
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
    )

    with pytest.raises(CiboCapitalManagementError, match="not eligible"):
        reserve_expansion_proposal(
            reservation_id="expansion-1",
            source_id="source-1",
            opportunity=_opportunity(),
            observation=_observation(),
            hard_risk_headroom_usd=Decimal("50"),
            margin_headroom_usd=Decimal("1000"),
            assigned_capital_usd=Decimal("10000"),
            requested_at=NOW,
            expires_at=NOW + timedelta(seconds=30),
            request_id="risk-expansion-1",
            ledger_store=store,
        )


def test_noneligible_observation_cannot_reserve_capacity(tmp_path: Path) -> None:
    store = _store(tmp_path)

    with pytest.raises(CiboCapitalManagementError, match="not eligible"):
        reserve_expansion_proposal(
            reservation_id="expansion-1",
            source_id="source-1",
            opportunity=_opportunity(),
            observation=_observation(eligible=False),
            hard_risk_headroom_usd=Decimal("50"),
            margin_headroom_usd=Decimal("1000"),
            assigned_capital_usd=Decimal("10000"),
            requested_at=NOW,
            expires_at=NOW + timedelta(seconds=30),
            request_id="risk-expansion-1",
            ledger_store=store,
        )


def test_second_reservation_cannot_double_spend_same_capacity(
    tmp_path: Path,
) -> None:
    store, first = _reserve(tmp_path)
    assert first.plan.stop_risk_usd == Decimal("10")

    second = reserve_expansion_proposal(
        reservation_id="expansion-2",
        source_id="source-1",
        opportunity=_opportunity(),
        observation=_observation(),
        hard_risk_headroom_usd=Decimal("50"),
        margin_headroom_usd=Decimal("1000"),
        assigned_capital_usd=Decimal("10000"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        request_id="risk-expansion-2",
        ledger_store=store,
    )

    assert second.plan.stop_risk_usd == Decimal("10")
    assert store.load().ledger.accounts[0].available_usd == Decimal("0")

    with pytest.raises(CiboCapitalManagementError, match="no reconciled available"):
        reserve_expansion_proposal(
            reservation_id="expansion-3",
            source_id="source-1",
            opportunity=_opportunity(),
            observation=_observation(),
            hard_risk_headroom_usd=Decimal("50"),
            margin_headroom_usd=Decimal("1000"),
            assigned_capital_usd=Decimal("10000"),
            requested_at=NOW,
            expires_at=NOW + timedelta(seconds=30),
            request_id="risk-expansion-3",
            ledger_store=store,
        )


def test_risk_rejection_releases_unused_reservation(tmp_path: Path) -> None:
    store, proposal = _reserve(tmp_path)

    version = release_rejected_expansion(
        reservation_id=proposal.reservation_id,
        ledger_store=store,
    )

    assert version.ledger.accounts[0].available_usd == Decimal("20")
    assert reservation_state(
        proposal,
        ledger_store=store,
    ) is ReservationState.RELEASED


def test_deployed_expansion_settlement_does_not_recycle_consumed_loss(
    tmp_path: Path,
) -> None:
    store, proposal = _reserve(tmp_path)
    deploy_reserved_expansion(
        reservation_id=proposal.reservation_id,
        ledger_store=store,
    )
    settled = settle_expansion_capacity(
        reservation_id=proposal.reservation_id,
        returned_capacity_usd=Decimal("4"),
        ledger_store=store,
    )

    account = settled.ledger.accounts[0]
    assert account.available_usd == Decimal("14")
    assert account.consumed_usd == Decimal("6")
    assert account.cumulative_released_usd == Decimal("4")
    assert reservation_state(
        proposal,
        ledger_store=store,
    ) is ReservationState.SETTLED
