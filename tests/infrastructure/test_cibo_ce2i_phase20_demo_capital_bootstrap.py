from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_capital_bootstrap import (
    bootstrap_phase20_demo_assigned_capital,
)
from qore.infrastructure.ctrader_demo_compat import CTraderDemoAccountState
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)

OBSERVED = datetime(2026, 9, 27, 18, 30, tzinfo=UTC)
ACTIVATED = OBSERVED + timedelta(milliseconds=50)
ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="phase20-demo-1",
    environment=MarketRuntimeEnvironment.DEMO,
)


def _account_state(balance: str = "1000000") -> CTraderDemoAccountState:
    return CTraderDemoAccountState(
        balance=Decimal(balance),
        equity=Decimal(balance),
        margin=Decimal("0"),
        free_margin=Decimal(balance),
        observed_at=OBSERVED,
    )


def test_demo_forward_assigned_base_freezes_once_and_survives_restart(
    tmp_path: Path,
) -> None:
    path = tmp_path / "capital.json"
    store = DurableCapitalSourceLedgerStore(path)

    bootstrap, first = bootstrap_phase20_demo_assigned_capital(
        store=store,
        account=ACCOUNT,
        account_state=_account_state(),
        activated_at=ACTIVATED,
    )

    assert first.generation == 1
    assert bootstrap.assigned_base_usd == Decimal("1000000")
    assert first.ledger.accounts[0].source is CapitalSource.ORIGINAL_BASE_CAPITAL
    assert first.ledger.accounts[0].proven_amount_usd == Decimal("1000000")

    # A later balance change cannot rewrite the frozen experiment base.
    restarted, second = bootstrap_phase20_demo_assigned_capital(
        store=DurableCapitalSourceLedgerStore(path),
        account=ACCOUNT,
        account_state=_account_state("1000500"),
        activated_at=ACTIVATED + timedelta(days=1),
    )

    assert second.generation == 1
    assert restarted.source_id == bootstrap.source_id
    assert restarted.activated_at == ACTIVATED
    assert restarted.assigned_base_usd == Decimal("1000000")


def test_demo_forward_restart_does_not_revalidate_frozen_base_against_new_snapshot(
    tmp_path: Path,
) -> None:
    path = tmp_path / "capital.json"
    bootstrap_phase20_demo_assigned_capital(
        store=DurableCapitalSourceLedgerStore(path),
        account=ACCOUNT,
        account_state=_account_state(),
        activated_at=ACTIVATED,
    )

    later_snapshot = CTraderDemoAccountState(
        balance=Decimal("1000500"),
        equity=Decimal("1000500"),
        margin=Decimal("0"),
        free_margin=Decimal("1000500"),
        observed_at=ACTIVATED + timedelta(days=1),
    )
    restarted, state = bootstrap_phase20_demo_assigned_capital(
        store=DurableCapitalSourceLedgerStore(path),
        account=ACCOUNT,
        account_state=later_snapshot,
        activated_at=ACTIVATED,
    )

    assert state.generation == 1
    assert restarted.assigned_base_usd == Decimal("1000000")


def test_demo_forward_new_base_rejects_snapshot_after_activation(
    tmp_path: Path,
) -> None:
    future_snapshot = CTraderDemoAccountState(
        balance=Decimal("1000000"),
        equity=Decimal("1000000"),
        margin=Decimal("0"),
        free_margin=Decimal("1000000"),
        observed_at=ACTIVATED + timedelta(milliseconds=1),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot use future account state",
    ):
        bootstrap_phase20_demo_assigned_capital(
            store=DurableCapitalSourceLedgerStore(tmp_path / "capital.json"),
            account=ACCOUNT,
            account_state=future_snapshot,
            activated_at=ACTIVATED,
        )


def test_demo_forward_assigned_base_rejects_preexisting_nonforward_lineage(
    tmp_path: Path,
) -> None:
    store = DurableCapitalSourceLedgerStore(tmp_path / "capital.json")
    legacy = CapitalSourceLedger().add_source(
        source_id="legacy-base",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
        proven_amount_usd=Decimal("100"),
    )
    store.store(legacy, expected_generation=0)

    with pytest.raises(
        CiboCapitalManagementError,
        match="lineage drift",
    ):
        bootstrap_phase20_demo_assigned_capital(
            store=store,
            account=ACCOUNT,
            account_state=_account_state(),
            activated_at=ACTIVATED,
        )


def test_demo_forward_assigned_base_rejects_observational_reservations(
    tmp_path: Path,
) -> None:
    store = DurableCapitalSourceLedgerStore(tmp_path / "capital.json")
    _, first = bootstrap_phase20_demo_assigned_capital(
        store=store,
        account=ACCOUNT,
        account_state=_account_state(),
        activated_at=ACTIVATED,
    )
    source_id = first.ledger.accounts[0].source_id
    reserved = first.ledger.reserve(
        reservation_id="illegal-shadow-reservation",
        source_id=source_id,
        amount_usd=Decimal("10"),
    )
    store.store(reserved, expected_generation=first.generation)

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot carry reservations",
    ):
        bootstrap_phase20_demo_assigned_capital(
            store=store,
            account=ACCOUNT,
            account_state=_account_state(),
            activated_at=ACTIVATED + timedelta(seconds=1),
        )
