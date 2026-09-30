from __future__ import annotations

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
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_store import (
    DurablePortfolioAllocationStore,
)
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementRecord
from qore.infrastructure.cibo_cma_settlement_store import (
    DurableCmaSettlementStore,
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
    IntegratedCapitalComponent,
    IntegratedCapitalTransactionError,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)


def _identity(
    account_ref: str = "integrated-component-adapter",
) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.TEST,
    )


def _persisted_stores(
    tmp_path: Path,
    *,
    identity: CiboAccountCapitalIdentity | None = None,
) -> IntegratedCapitalStoreSet:
    identity = identity or _identity()

    source = DurableCapitalSourceLedgerStore(tmp_path / "source.json")
    source.store(
        CapitalSourceLedger().add_source(
            source_id="gen0",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        ),
        expected_generation=0,
    )

    compound = DurableCompoundPortfolioStore(
        tmp_path / "compound.json",
        account_identity=identity,
    )
    compound.store(
        CompoundPortfolioLedger(account_identity=identity),
        expected_generation=0,
    )

    floor = DurableProtectedCapitalFloorStore(
        tmp_path / "floor.json",
        account_identity=identity,
    )
    floor.store(
        ProtectedCapitalFloorLedger(account_identity=identity),
        expected_generation=0,
    )

    t19 = DurablePortfolioAllocationStore(tmp_path / "t19.json")
    t19.initialize(
        PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("EQUITY_BETA", Decimal("10")),
            ),
        )
    )

    settlement = DurableCmaSettlementStore(tmp_path / "settlement.json")
    settlement.apply(
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=1001,
            signal_fingerprint="signal-1",
            position_id=2001,
            net_profit_usd=Decimal("5"),
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


def test_adapter_reads_all_five_real_store_refs(tmp_path: Path) -> None:
    stores = _persisted_stores(tmp_path)
    refs = read_integrated_component_refs(stores)

    assert tuple(item.component for item in refs) == tuple(
        sorted(IntegratedCapitalComponent, key=lambda item: item.value)
    )
    assert all(item.generation == 1 for item in refs)
    assert all(item.sha256.startswith("sha256:") for item in refs)


def test_only_mutated_source_ref_changes(tmp_path: Path) -> None:
    stores = _persisted_stores(tmp_path)
    before = {
        item.component: item
        for item in read_integrated_component_refs(stores)
    }

    current = stores.source_store.load()
    stores.source_store.store(
        current.ledger.add_source(
            source_id="profit-1",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("5"),
        ),
        expected_generation=current.generation,
    )
    after = {
        item.component: item
        for item in read_integrated_component_refs(stores)
    }

    for component in IntegratedCapitalComponent:
        if component is IntegratedCapitalComponent.SOURCE_LEDGER:
            assert after[component].generation == 2
            assert after[component].sha256 != before[component].sha256
        else:
            assert after[component] == before[component]


def test_adapter_rejects_uninitialized_t19(tmp_path: Path) -> None:
    stores = _persisted_stores(tmp_path)
    empty_t19 = DurablePortfolioAllocationStore(
        tmp_path / "empty-t19.json"
    )
    broken = IntegratedCapitalStoreSet(
        account_identity=stores.account_identity,
        source_store=stores.source_store,
        compound_store=stores.compound_store,
        floor_store=stores.floor_store,
        t19_store=empty_t19,
        settlement_store=stores.settlement_store,
        legacy_path_scope_verified=True,
    )

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="T19 allocation ledger is not durably initialized",
    ):
        read_integrated_component_refs(broken)


def test_adapter_requires_explicit_legacy_path_scope(tmp_path: Path) -> None:
    stores = _persisted_stores(tmp_path)

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="account-scope verification",
    ):
        IntegratedCapitalStoreSet(
            account_identity=stores.account_identity,
            source_store=stores.source_store,
            compound_store=stores.compound_store,
            floor_store=stores.floor_store,
            t19_store=stores.t19_store,
            settlement_store=stores.settlement_store,
            legacy_path_scope_verified=False,
        )


def test_adapter_rejects_compound_account_mismatch(tmp_path: Path) -> None:
    stores = _persisted_stores(tmp_path)
    other = _identity("other-account")
    other_compound = DurableCompoundPortfolioStore(
        tmp_path / "other-compound.json",
        account_identity=other,
    )
    other_compound.store(
        CompoundPortfolioLedger(account_identity=other),
        expected_generation=0,
    )
    mismatched = IntegratedCapitalStoreSet(
        account_identity=stores.account_identity,
        source_store=stores.source_store,
        compound_store=other_compound,
        floor_store=stores.floor_store,
        t19_store=stores.t19_store,
        settlement_store=stores.settlement_store,
        legacy_path_scope_verified=True,
    )

    with pytest.raises(
        IntegratedCapitalTransactionError,
        match="compound portfolio account scope differs",
    ):
        read_integrated_component_refs(mismatched)
