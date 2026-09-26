from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalSourceLedger,
    ReservationState,
)


def _ledger() -> CapitalSourceLedger:
    return CapitalSourceLedger().add_source(
        source_id="profit-1",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("20"),
    )


def test_reservation_reduces_available_capacity() -> None:
    ledger = _ledger().reserve(
        reservation_id="r1",
        source_id="profit-1",
        amount_usd=Decimal("8"),
    )

    account = ledger.accounts[0]
    assert account.available_usd == Decimal("12")
    assert account.reserved_usd == Decimal("8")


def test_same_capacity_cannot_be_reserved_twice() -> None:
    ledger = _ledger().reserve(
        reservation_id="r1",
        source_id="profit-1",
        amount_usd=Decimal("15"),
    )

    with pytest.raises(CiboCapitalManagementError, match="insufficient"):
        ledger.reserve(
            reservation_id="r2",
            source_id="profit-1",
            amount_usd=Decimal("10"),
        )


def test_deploy_moves_reserved_to_deployed_without_changing_available() -> None:
    reserved = _ledger().reserve(
        reservation_id="r1",
        source_id="profit-1",
        amount_usd=Decimal("8"),
    )
    deployed = reserved.deploy("r1")

    account = deployed.accounts[0]
    assert account.reserved_usd == 0
    assert account.deployed_usd == Decimal("8")
    assert account.available_usd == Decimal("12")
    assert deployed.reservations[0].state is ReservationState.DEPLOYED


def test_unused_reservation_release_returns_full_capacity() -> None:
    ledger = (
        _ledger()
        .reserve(
            reservation_id="r1",
            source_id="profit-1",
            amount_usd=Decimal("8"),
        )
        .release_unused("r1")
    )

    account = ledger.accounts[0]
    assert account.available_usd == Decimal("20")
    assert account.reserved_usd == 0
    assert account.cumulative_released_usd == Decimal("8")
    assert ledger.reservations[0].state is ReservationState.RELEASED


def test_deployed_loss_is_consumed_and_not_recycled() -> None:
    ledger = (
        _ledger()
        .reserve(
            reservation_id="r1",
            source_id="profit-1",
            amount_usd=Decimal("8"),
        )
        .deploy("r1")
        .settle_deployment("r1", returned_capacity_usd=Decimal("3"))
    )

    account = ledger.accounts[0]
    assert account.available_usd == Decimal("15")
    assert account.deployed_usd == 0
    assert account.consumed_usd == Decimal("5")
    assert account.cumulative_released_usd == Decimal("3")
    reservation = ledger.reservations[0]
    assert reservation.state is ReservationState.SETTLED
    assert reservation.returned_capacity_usd == Decimal("3")
    assert reservation.consumed_capacity_usd == Decimal("5")


def test_fully_consumed_deployment_does_not_return_capacity() -> None:
    ledger = (
        _ledger()
        .reserve(
            reservation_id="r1",
            source_id="profit-1",
            amount_usd=Decimal("8"),
        )
        .deploy("r1")
        .settle_deployment("r1", returned_capacity_usd=Decimal("0"))
    )

    account = ledger.accounts[0]
    assert account.available_usd == Decimal("12")
    assert account.consumed_usd == Decimal("8")
    assert account.cumulative_released_usd == 0


def test_deployed_capacity_cannot_use_unused_release_path() -> None:
    ledger = (
        _ledger()
        .reserve(
            reservation_id="r1",
            source_id="profit-1",
            amount_usd=Decimal("8"),
        )
        .deploy("r1")
    )

    with pytest.raises(CiboCapitalManagementError, match="only RESERVED"):
        ledger.release_unused("r1")


def test_returned_capacity_cannot_exceed_deployment() -> None:
    ledger = (
        _ledger()
        .reserve(
            reservation_id="r1",
            source_id="profit-1",
            amount_usd=Decimal("8"),
        )
        .deploy("r1")
    )

    with pytest.raises(CiboCapitalManagementError, match="outside deployed"):
        ledger.settle_deployment("r1", returned_capacity_usd=Decimal("9"))


def test_duplicate_reservation_id_is_rejected() -> None:
    ledger = _ledger().reserve(
        reservation_id="r1",
        source_id="profit-1",
        amount_usd=Decimal("5"),
    )

    with pytest.raises(CiboCapitalManagementError, match="duplicate reservation_id"):
        ledger.reserve(
            reservation_id="r1",
            source_id="profit-1",
            amount_usd=Decimal("1"),
        )
