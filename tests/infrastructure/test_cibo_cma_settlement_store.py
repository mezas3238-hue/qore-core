from decimal import Decimal

import pytest

from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementRecord
from qore.infrastructure.cibo_cma_settlement_store import (
    DurableCmaSettlementStore,
    DurableCmaSettlementStoreError,
)


def _record(
    *,
    deal_id: int = 1,
    net: str = "5",
    event: str = "CTRADER_DEMO_PARTIAL_SETTLEMENT",
    open_after: bool = True,
) -> CmaSettlementRecord:
    return CmaSettlementRecord(
        event=event,
        deal_id=deal_id,
        signal_fingerprint="signal-1",
        position_id=101,
        net_profit_usd=Decimal(net),
        position_open_after=open_after,
    )


def test_store_survives_restart_and_preserves_realized_pnl(tmp_path) -> None:
    path = tmp_path / "settlements.json"
    store = DurableCmaSettlementStore(path)
    version = store.apply(_record(), expected_generation=0)

    restarted = DurableCmaSettlementStore(path).load()
    state = restarted.state_for(
        signal_fingerprint="signal-1",
        position_id=101,
    )

    assert version.generation == 1
    assert restarted.generation == 1
    assert state is not None
    assert state.realized_net_pnl_usd == Decimal("5")


def test_exact_duplicate_is_idempotent_without_generation_bump(tmp_path) -> None:
    store = DurableCmaSettlementStore(tmp_path / "settlements.json")
    first = store.apply(_record(), expected_generation=0)
    duplicate = store.apply(_record(), expected_generation=first.generation)

    assert duplicate.generation == first.generation
    assert len(duplicate.states[0].records) == 1


def test_conflicting_duplicate_fails_closed(tmp_path) -> None:
    store = DurableCmaSettlementStore(tmp_path / "settlements.json")
    first = store.apply(_record(), expected_generation=0)

    with pytest.raises(ValueError, match="conflicting duplicate"):
        store.apply(
            _record(net="7"),
            expected_generation=first.generation,
        )


def test_stale_generation_cannot_overwrite_settlement_book(tmp_path) -> None:
    store = DurableCmaSettlementStore(tmp_path / "settlements.json")
    store.apply(_record(), expected_generation=0)

    with pytest.raises(DurableCmaSettlementStoreError, match="stale"):
        store.apply(_record(deal_id=2), expected_generation=0)


def test_terminal_exit_persists_closed_state(tmp_path) -> None:
    store = DurableCmaSettlementStore(tmp_path / "settlements.json")
    first = store.apply(_record(), expected_generation=0)
    second = store.apply(
        _record(
            deal_id=2,
            net="3",
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            open_after=False,
        ),
        expected_generation=first.generation,
    )
    state = second.states[0]

    assert state.position_closed is True
    assert state.realized_net_pnl_usd == Decimal("8")


def test_corrupt_store_fails_closed(tmp_path) -> None:
    path = tmp_path / "settlements.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(DurableCmaSettlementStoreError, match="unreadable"):
        DurableCmaSettlementStore(path).load()
