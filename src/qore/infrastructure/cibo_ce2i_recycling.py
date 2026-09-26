"""CE2I T05 released-capacity recycling.

Released risk and released margin are different non-fungible capacities.
This module registers reconciled release evidence and reserves it atomically
for its own economic dimension. It never creates broker orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalCapacityDimension,
    CapitalSource,
    CiboCapitalManagementError,
    capital_source_dimension,
)
from qore.infrastructure.cibo_capital_source_ledger import ReservationState
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
    VersionedCapitalSourceLedger,
)


class RecyclePurpose(StrEnum):
    STOP_RISK = "STOP_RISK"
    MARGIN = "MARGIN"


@dataclass(frozen=True, slots=True)
class ReleasedCapacityEvidence:
    evidence_id: str
    source: CapitalSource
    amount_usd: Decimal
    reconciled_at: datetime
    upstream_reference: str
    reconciled: bool = True

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.upstream_reference:
            raise CiboCapitalManagementError(
                "evidence_id/upstream_reference required"
            )
        if self.source not in {
            CapitalSource.RELEASED_RISK_CAPACITY,
            CapitalSource.RELEASED_MARGIN_CAPACITY,
        }:
            raise CiboCapitalManagementError(
                "released-capacity evidence source invalid"
            )
        if (
            not isinstance(self.amount_usd, Decimal)
            or not self.amount_usd.is_finite()
            or self.amount_usd <= 0
        ):
            raise CiboCapitalManagementError(
                "released capacity amount must be finite positive Decimal"
            )
        if (
            not isinstance(self.reconciled_at, datetime)
            or self.reconciled_at.tzinfo is None
            or self.reconciled_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "reconciled_at must be timezone-aware"
            )
        if type(self.reconciled) is not bool:
            raise CiboCapitalManagementError("reconciled must be bool")


@dataclass(frozen=True, slots=True)
class RegisteredReleasedCapacity:
    source_id: str
    source: CapitalSource
    dimension: CapitalCapacityDimension
    amount_usd: Decimal
    ledger_generation: int


@dataclass(frozen=True, slots=True)
class RecycledCapacityReservation:
    reservation_id: str
    source_id: str
    purpose: RecyclePurpose
    amount_usd: Decimal
    ledger_generation: int


def register_released_capacity(
    evidence: ReleasedCapacityEvidence,
    *,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> RegisteredReleasedCapacity:
    """Register one release exactly once from reconciled evidence."""

    if not isinstance(evidence, ReleasedCapacityEvidence):
        raise CiboCapitalManagementError(
            "evidence must be ReleasedCapacityEvidence"
        )
    if not isinstance(ledger_store, DurableCapitalSourceLedgerStore):
        raise CiboCapitalManagementError(
            "ledger_store must be DurableCapitalSourceLedgerStore"
        )
    if not evidence.reconciled:
        raise CiboCapitalManagementError(
            "unreconciled released capacity cannot enter ledger"
        )

    source_id = f"{evidence.source.value}:{evidence.evidence_id}"
    version = ledger_store.load()
    existing = tuple(
        account
        for account in version.ledger.accounts
        if account.source_id == source_id
    )
    if existing:
        if len(existing) != 1:
            raise CiboCapitalManagementError(
                "duplicate released-capacity source identity"
            )
        account = existing[0]
        if (
            account.source is not evidence.source
            or account.proven_amount_usd != evidence.amount_usd
        ):
            raise CiboCapitalManagementError(
                "released-capacity evidence conflicts with existing source"
            )
        return RegisteredReleasedCapacity(
            source_id=source_id,
            source=account.source,
            dimension=capital_source_dimension(account.source),
            amount_usd=account.proven_amount_usd,
            ledger_generation=version.generation,
        )

    ledger = version.ledger.add_source(
        source_id=source_id,
        source=evidence.source,
        proven_amount_usd=evidence.amount_usd,
    )
    stored = ledger_store.store(
        ledger,
        expected_generation=version.generation,
    )
    return RegisteredReleasedCapacity(
        source_id=source_id,
        source=evidence.source,
        dimension=capital_source_dimension(evidence.source),
        amount_usd=evidence.amount_usd,
        ledger_generation=stored.generation,
    )


def reserve_recycled_capacity(
    *,
    reservation_id: str,
    source_id: str,
    purpose: RecyclePurpose,
    amount_usd: Decimal,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> RecycledCapacityReservation:
    """Reserve released capacity only for its matching economic dimension."""

    if type(purpose) is not RecyclePurpose:
        raise CiboCapitalManagementError("purpose must be RecyclePurpose")
    if (
        not isinstance(amount_usd, Decimal)
        or not amount_usd.is_finite()
        or amount_usd <= 0
    ):
        raise CiboCapitalManagementError(
            "recycled reservation amount must be finite positive Decimal"
        )
    version = ledger_store.load()
    accounts = tuple(
        account
        for account in version.ledger.accounts
        if account.source_id == source_id
    )
    if len(accounts) != 1:
        raise CiboCapitalManagementError("released capital source not found")
    account = accounts[0]
    required = (
        CapitalCapacityDimension.RELEASED_RISK_HEADROOM
        if purpose is RecyclePurpose.STOP_RISK
        else CapitalCapacityDimension.MARGIN_HEADROOM
    )
    if capital_source_dimension(account.source) is not required:
        raise CiboCapitalManagementError(
            "released capacity dimension does not match recycle purpose"
        )

    ledger = version.ledger.reserve(
        reservation_id=reservation_id,
        source_id=source_id,
        amount_usd=amount_usd,
    )
    stored = ledger_store.store(
        ledger,
        expected_generation=version.generation,
    )
    return RecycledCapacityReservation(
        reservation_id=reservation_id,
        source_id=source_id,
        purpose=purpose,
        amount_usd=amount_usd,
        ledger_generation=stored.generation,
    )


def deploy_recycled_capacity(
    reservation: RecycledCapacityReservation,
    *,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> VersionedCapitalSourceLedger:
    version = ledger_store.load()
    deployed = version.ledger.deploy(reservation.reservation_id)
    return ledger_store.store(
        deployed,
        expected_generation=version.generation,
    )


def release_unused_recycled_capacity(
    reservation: RecycledCapacityReservation,
    *,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> VersionedCapitalSourceLedger:
    version = ledger_store.load()
    released = version.ledger.release_unused(reservation.reservation_id)
    return ledger_store.store(
        released,
        expected_generation=version.generation,
    )


def settle_recycled_capacity(
    reservation: RecycledCapacityReservation,
    *,
    returned_capacity_usd: Decimal,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> VersionedCapitalSourceLedger:
    """Settle recycled capacity; margin capacity can never be economically consumed."""

    version = ledger_store.load()
    rows = tuple(
        item
        for item in version.ledger.reservations
        if item.reservation_id == reservation.reservation_id
    )
    if len(rows) != 1:
        raise CiboCapitalManagementError("recycled reservation not found")
    row = rows[0]
    accounts = tuple(
        account
        for account in version.ledger.accounts
        if account.source_id == row.source_id
    )
    if len(accounts) != 1:
        raise CiboCapitalManagementError("recycled source not found")
    dimension = capital_source_dimension(accounts[0].source)
    if (
        dimension is CapitalCapacityDimension.MARGIN_HEADROOM
        and returned_capacity_usd != row.amount_usd
    ):
        raise CiboCapitalManagementError(
            "margin headroom cannot be settled as consumed economic loss"
        )
    settled = version.ledger.settle_deployment(
        reservation.reservation_id,
        returned_capacity_usd=returned_capacity_usd,
    )
    return ledger_store.store(
        settled,
        expected_generation=version.generation,
    )


def recycled_reservation_state(
    reservation: RecycledCapacityReservation,
    *,
    ledger_store: DurableCapitalSourceLedgerStore,
) -> ReservationState:
    version = ledger_store.load()
    found = tuple(
        row
        for row in version.ledger.reservations
        if row.reservation_id == reservation.reservation_id
    )
    if len(found) != 1:
        raise CiboCapitalManagementError("recycled reservation not found")
    return found[0].state
