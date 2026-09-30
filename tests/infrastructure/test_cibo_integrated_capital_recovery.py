from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
    PortfolioAllocationReservation,
    PortfolioAllocationReservationState,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_store import (
    DurablePortfolioAllocationStore,
)
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementRecord
from qore.infrastructure.cibo_cma_settlement_store import (
    DurableCmaSettlementStore,
)
from qore.infrastructure.cibo_compound_capital import (
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_floor import (
    ProtectedCapitalFloorLedger,
)
from qore.infrastructure.cibo_compound_floor_store import (
    DurableProtectedCapitalFloorStore,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioLedger,
)
from qore.infrastructure.cibo_compound_portfolio_store import (
    DurableCompoundPortfolioStore,
)
from qore.infrastructure.cibo_integrated_capital_component_adapter import (
    IntegratedCapitalStoreSet,
    read_integrated_component_refs,
)
from qore.infrastructure.cibo_integrated_capital_transaction_store import (
    DurableIntegratedCapitalTransactionStore,
    IntegratedCapitalTransactionError,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 2, 45, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="integrated-recovery",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _stores(root: Path) -> IntegratedCapitalStoreSet:
    identity = _identity()
    source = DurableCapitalSourceLedgerStore(root / "source.json")
    source.store(
        CapitalSourceLedger().add_source(
            source_id="gen0",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        ),
        expected_generation=0,
    )

    compound = DurableCompoundPortfolioStore(
        root / "compound.json",
        account_identity=identity,
    )
    compound.store(
        CompoundPortfolioLedger(account_identity=identity),
        expected_generation=0,
    )

    floor = DurableProtectedCapitalFloorStore(
        root / "floor.json",
        account_identity=identity,
    )
    floor.store(
        ProtectedCapitalFloorLedger(account_identity=identity),
        expected_generation=0,
    )

    t19 = DurablePortfolioAllocationStore(root / "t19.json")
    t19.initialize(
        PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("EQUITY_BETA", Decimal("10")),
            ),
        )
    )

    settlement = DurableCmaSettlementStore(root / "settlement.json")
    settlement.apply(
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=100,
            signal_fingerprint="initial",
            position_id=200,
            net_profit_usd=Decimal("1"),
            position_open_after=False,
        ),
        expected_generation=0,
    )

    return IntegratedCapitalStoreSet(
        account_identity=identity,
        source_store=source,
        compound_store=compound,
        floor_store=floor,
        t19_store=t19,
        settlement_store=settlement,
        legacy_path_scope_verified=True,
    )


def _mutate_source(stores: IntegratedCapitalStoreSet) -> None:
    version = stores.source_store.load()
    stores.source_store.store(
        version.ledger.add_source(
            source_id="profit-advance",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("10"),
        ),
        expected_generation=version.generation,
    )


def _mutate_compound_and_floor(
    stores: IntegratedCapitalStoreSet,
) -> None:
    version = stores.compound_store.load()
    evidence = CompoundRealizedProfitEvidence(
        evidence_id="tx-profit-evidence",
        account_identity=stores.account_identity,
        origin_trader=TraderLineage.VT31_NAS100,
        signal_fingerprint="tx-profit",
        position_id=3001,
        settlement_deal_ids=(4001,),
        realized_net_profit_usd=Decimal("10"),
        realized_at=T0,
        source_settlement_sha256="sha256:" + "a" * 64,
        settlement_reconciled=True,
        position_closed=True,
        floating_pnl_used_as_capital=False,
    )
    lot = create_realized_profit_lot(
        evidence,
        lot_id="tx-gen1",
        created_at=T0,
    )
    ledger = version.ledger.admit_realized_profit(
        lot,
        event_id="tx-admit",
        occurred_at=T0,
    )
    ledger = ledger.transition(
        source_lot_id="tx-gen1",
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal("2"),
        moved_lot_id="tx-retired",
        remainder_lot_id="tx-remainder",
        event_id="tx-retire",
        occurred_at=T0 + timedelta(seconds=1),
    )
    stores.compound_store.store(
        ledger,
        expected_generation=version.generation,
    )

    floor_version = stores.floor_store.load()
    floor = floor_version.ledger.admit_retired_lot(
        ledger.lot("tx-retired"),
        tranche_id="tx-floor",
        event_id="tx-floor-admit",
        admitted_at=T0 + timedelta(seconds=1),
    )
    stores.floor_store.store(
        floor,
        expected_generation=floor_version.generation,
    )


def _mutate_t19(stores: IntegratedCapitalStoreSet) -> None:
    version = stores.t19_store.load()
    assert version is not None
    reservation = PortfolioAllocationReservation(
        signal_fingerprint="tx-profit",
        trader_id=TraderLineage.VT31_NAS100,
        qore_symbol="NAS100",
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("2"),
        concentration_group="EQUITY_BETA",
        concentration_risk_usd=Decimal("1"),
        state=PortfolioAllocationReservationState.ACTIVE,
    )
    stores.t19_store.store(
        replace(
            version.ledger,
            reservations=version.ledger.reservations + (reservation,),
        ),
        expected_generation=version.generation,
    )


def _mutate_settlement(stores: IntegratedCapitalStoreSet) -> None:
    version = stores.settlement_store.load()
    stores.settlement_store.apply(
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=4001,
            signal_fingerprint="tx-profit",
            position_id=3001,
            net_profit_usd=Decimal("10"),
            position_open_after=False,
        ),
        expected_generation=version.generation,
    )


def _mutate_remaining(stores: IntegratedCapitalStoreSet) -> None:
    _mutate_compound_and_floor(stores)
    _mutate_t19(stores)
    _mutate_settlement(stores)


def test_partial_write_restart_blocks_until_all_real_stores_match(
    tmp_path: Path,
) -> None:
    actual = _stores(tmp_path / "actual")
    expected = _stores(tmp_path / "expected")
    before_refs = read_integrated_component_refs(actual)

    _mutate_source(expected)
    _mutate_remaining(expected)
    target_refs = read_integrated_component_refs(expected)

    journal_path = tmp_path / "integrated-journal.json"
    journal = DurableIntegratedCapitalTransactionStore(journal_path)
    prepared = journal.prepare(
        transaction_id="tx-real-stores",
        before_refs=before_refs,
        after_refs=target_refs,
        capital_truth_before_sha256="sha256:" + "b" * 64,
        capital_truth_after_sha256="sha256:" + "c" * 64,
        prepared_at=T0,
        expected_generation=0,
    )
    assert prepared.unresolved_transaction_ids == ("tx-real-stores",)

    _mutate_source(actual)
    partial_refs = read_integrated_component_refs(actual)
    assert partial_refs != target_refs

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="component state differs from prepared target",
    ):
        journal.commit(
            transaction_id="tx-real-stores",
            observed_after_refs=partial_refs,
            observed_capital_truth_sha256="sha256:" + "c" * 64,
            committed_at=T0 + timedelta(seconds=2),
            expected_generation=1,
        )

    restarted = DurableIntegratedCapitalTransactionStore(journal_path)
    assert restarted.load().unresolved_transaction_ids == (
        "tx-real-stores",
    )

    _mutate_remaining(actual)
    recovered_refs = read_integrated_component_refs(actual)
    assert recovered_refs == target_refs

    committed = restarted.commit(
        transaction_id="tx-real-stores",
        observed_after_refs=recovered_refs,
        observed_capital_truth_sha256="sha256:" + "c" * 64,
        committed_at=T0 + timedelta(seconds=3),
        expected_generation=1,
    )
    assert committed.generation == 2
    assert committed.unresolved_transaction_ids == ()
    assert (
        DurableIntegratedCapitalTransactionStore(journal_path)
        .load()
        == committed
    )
