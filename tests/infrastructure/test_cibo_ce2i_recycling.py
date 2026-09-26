from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalCapacityDimension,
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import ReservationState
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_ce2i_recycling import (
    RecyclePurpose,
    ReleasedCapacityEvidence,
    deploy_recycled_capacity,
    recycled_reservation_state,
    register_released_capacity,
    release_unused_recycled_capacity,
    reserve_recycled_capacity,
    settle_recycled_capacity,
)


NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _store(tmp_path: Path) -> DurableCapitalSourceLedgerStore:
    return DurableCapitalSourceLedgerStore(tmp_path / "recycling-ledger.json")


def _evidence(
    source: CapitalSource = CapitalSource.RELEASED_RISK_CAPACITY,
    *,
    amount: str = "20",
) -> ReleasedCapacityEvidence:
    return ReleasedCapacityEvidence(
        evidence_id="release-1",
        source=source,
        amount_usd=Decimal(amount),
        reconciled_at=NOW,
        upstream_reference="position-101:settlement-2",
    )


def test_released_risk_capacity_registers_idempotently(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = register_released_capacity(
        _evidence(),
        ledger_store=store,
    )
    second = register_released_capacity(
        _evidence(),
        ledger_store=store,
    )

    assert first.source_id == second.source_id
    assert first.dimension is CapitalCapacityDimension.RELEASED_RISK_HEADROOM
    assert len(store.load().ledger.accounts) == 1


def test_conflicting_duplicate_release_evidence_fails_closed(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    register_released_capacity(_evidence(), ledger_store=store)

    with pytest.raises(CiboCapitalManagementError, match="conflicts"):
        register_released_capacity(
            _evidence(amount="21"),
            ledger_store=store,
        )


def test_unreconciled_capacity_cannot_enter_ledger(tmp_path: Path) -> None:
    store = _store(tmp_path)
    evidence = ReleasedCapacityEvidence(
        evidence_id="release-1",
        source=CapitalSource.RELEASED_RISK_CAPACITY,
        amount_usd=Decimal("20"),
        reconciled_at=NOW,
        upstream_reference="position-101",
        reconciled=False,
    )

    with pytest.raises(CiboCapitalManagementError, match="unreconciled"):
        register_released_capacity(evidence, ledger_store=store)


def test_released_margin_cannot_fund_stop_risk(tmp_path: Path) -> None:
    store = _store(tmp_path)
    registered = register_released_capacity(
        _evidence(CapitalSource.RELEASED_MARGIN_CAPACITY),
        ledger_store=store,
    )

    with pytest.raises(CiboCapitalManagementError, match="dimension"):
        reserve_recycled_capacity(
            reservation_id="r1",
            source_id=registered.source_id,
            purpose=RecyclePurpose.STOP_RISK,
            amount_usd=Decimal("5"),
            ledger_store=store,
        )


def test_released_risk_cannot_impersonate_margin_capacity(tmp_path: Path) -> None:
    store = _store(tmp_path)
    registered = register_released_capacity(
        _evidence(),
        ledger_store=store,
    )

    with pytest.raises(CiboCapitalManagementError, match="dimension"):
        reserve_recycled_capacity(
            reservation_id="r1",
            source_id=registered.source_id,
            purpose=RecyclePurpose.MARGIN,
            amount_usd=Decimal("5"),
            ledger_store=store,
        )


def test_recycled_risk_can_reserve_deploy_and_settle_loss(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    registered = register_released_capacity(_evidence(), ledger_store=store)
    reservation = reserve_recycled_capacity(
        reservation_id="r1",
        source_id=registered.source_id,
        purpose=RecyclePurpose.STOP_RISK,
        amount_usd=Decimal("8"),
        ledger_store=store,
    )
    deploy_recycled_capacity(reservation, ledger_store=store)
    settled = settle_recycled_capacity(
        reservation,
        returned_capacity_usd=Decimal("3"),
        ledger_store=store,
    )

    account = settled.ledger.accounts[0]
    assert account.available_usd == Decimal("15")
    assert account.consumed_usd == Decimal("5")
    assert recycled_reservation_state(
        reservation,
        ledger_store=store,
    ) is ReservationState.SETTLED


def test_recycled_margin_must_return_in_full_on_settlement(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    registered = register_released_capacity(
        _evidence(CapitalSource.RELEASED_MARGIN_CAPACITY),
        ledger_store=store,
    )
    reservation = reserve_recycled_capacity(
        reservation_id="m1",
        source_id=registered.source_id,
        purpose=RecyclePurpose.MARGIN,
        amount_usd=Decimal("8"),
        ledger_store=store,
    )
    deploy_recycled_capacity(reservation, ledger_store=store)

    with pytest.raises(CiboCapitalManagementError, match="cannot be settled"):
        settle_recycled_capacity(
            reservation,
            returned_capacity_usd=Decimal("7"),
            ledger_store=store,
        )

    settled = settle_recycled_capacity(
        reservation,
        returned_capacity_usd=Decimal("8"),
        ledger_store=store,
    )
    assert settled.ledger.accounts[0].consumed_usd == 0


def test_unused_recycled_reservation_returns_capacity(tmp_path: Path) -> None:
    store = _store(tmp_path)
    registered = register_released_capacity(_evidence(), ledger_store=store)
    reservation = reserve_recycled_capacity(
        reservation_id="r1",
        source_id=registered.source_id,
        purpose=RecyclePurpose.STOP_RISK,
        amount_usd=Decimal("8"),
        ledger_store=store,
    )
    released = release_unused_recycled_capacity(
        reservation,
        ledger_store=store,
    )

    assert released.ledger.accounts[0].available_usd == Decimal("20")
    assert recycled_reservation_state(
        reservation,
        ledger_store=store,
    ) is ReservationState.RELEASED
