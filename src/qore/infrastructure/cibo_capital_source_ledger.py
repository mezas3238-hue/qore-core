"""Atomic research ledger for CIBO capital sources.

The ledger prevents the same proven capital capacity from being reserved or
deployed twice. It distinguishes unused reservation release from settlement of
deployed capacity, because deployed capital can be economically consumed.
It performs no broker action.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)


class ReservationState(StrEnum):
    RESERVED = "RESERVED"
    DEPLOYED = "DEPLOYED"
    SETTLED = "SETTLED"
    RELEASED = "RELEASED"


@dataclass(frozen=True, slots=True)
class CapitalSourceAccount:
    source_id: str
    source: CapitalSource
    proven_amount_usd: Decimal
    reserved_usd: Decimal = Decimal(0)
    deployed_usd: Decimal = Decimal(0)
    consumed_usd: Decimal = Decimal(0)
    cumulative_released_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if not self.source_id:
            raise CiboCapitalManagementError("source_id is required")
        if type(self.source) is not CapitalSource:
            raise CiboCapitalManagementError("source must be CapitalSource")
        for name in (
            "proven_amount_usd",
            "reserved_usd",
            "deployed_usd",
            "consumed_usd",
            "cumulative_released_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(f"{name} must be finite non-negative")
        if self.reserved_usd + self.deployed_usd + self.consumed_usd > self.proven_amount_usd:
            raise CiboCapitalManagementError("capital source is over-allocated")

    @property
    def available_usd(self) -> Decimal:
        return (
            self.proven_amount_usd
            - self.reserved_usd
            - self.deployed_usd
            - self.consumed_usd
        )


@dataclass(frozen=True, slots=True)
class CapitalReservation:
    reservation_id: str
    source_id: str
    amount_usd: Decimal
    state: ReservationState
    returned_capacity_usd: Decimal = Decimal(0)
    consumed_capacity_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if not self.reservation_id or not self.source_id:
            raise CiboCapitalManagementError("reservation/source id required")
        for name in ("amount_usd", "returned_capacity_usd", "consumed_capacity_usd"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(f"{name} must be finite non-negative")
        if self.amount_usd <= 0:
            raise CiboCapitalManagementError("reservation amount must be positive")
        if type(self.state) is not ReservationState:
            raise CiboCapitalManagementError("reservation state invalid")
        if self.returned_capacity_usd + self.consumed_capacity_usd > self.amount_usd:
            raise CiboCapitalManagementError("reservation settlement exceeds amount")


@dataclass(frozen=True, slots=True)
class CapitalSourceLedger:
    accounts: tuple[CapitalSourceAccount, ...] = ()
    reservations: tuple[CapitalReservation, ...] = ()

    def add_source(
        self,
        *,
        source_id: str,
        source: CapitalSource,
        proven_amount_usd: Decimal,
    ) -> CapitalSourceLedger:
        if any(item.source_id == source_id for item in self.accounts):
            raise CiboCapitalManagementError("duplicate source_id")
        account = CapitalSourceAccount(
            source_id=source_id,
            source=source,
            proven_amount_usd=proven_amount_usd,
        )
        return replace(self, accounts=self.accounts + (account,))

    def reserve(
        self,
        *,
        reservation_id: str,
        source_id: str,
        amount_usd: Decimal,
    ) -> CapitalSourceLedger:
        if any(item.reservation_id == reservation_id for item in self.reservations):
            raise CiboCapitalManagementError("duplicate reservation_id")
        account = self._account(source_id)
        if amount_usd <= 0:
            raise CiboCapitalManagementError("reservation amount must be positive")
        if amount_usd > account.available_usd:
            raise CiboCapitalManagementError("insufficient available capital capacity")
        updated = replace(account, reserved_usd=account.reserved_usd + amount_usd)
        reservation = CapitalReservation(
            reservation_id=reservation_id,
            source_id=source_id,
            amount_usd=amount_usd,
            state=ReservationState.RESERVED,
        )
        return CapitalSourceLedger(
            accounts=self._replace_account(updated),
            reservations=self.reservations + (reservation,),
        )

    def deploy(self, reservation_id: str) -> CapitalSourceLedger:
        reservation = self._reservation(reservation_id)
        if reservation.state is not ReservationState.RESERVED:
            raise CiboCapitalManagementError("only RESERVED capacity can deploy")
        account = self._account(reservation.source_id)
        updated = replace(
            account,
            reserved_usd=account.reserved_usd - reservation.amount_usd,
            deployed_usd=account.deployed_usd + reservation.amount_usd,
        )
        return CapitalSourceLedger(
            accounts=self._replace_account(updated),
            reservations=self._replace_reservation(
                replace(reservation, state=ReservationState.DEPLOYED)
            ),
        )

    def release_unused(self, reservation_id: str) -> CapitalSourceLedger:
        """Release capacity that was reserved but never economically deployed."""

        reservation = self._reservation(reservation_id)
        if reservation.state is not ReservationState.RESERVED:
            raise CiboCapitalManagementError("only RESERVED capacity can release unused")
        account = self._account(reservation.source_id)
        updated = replace(
            account,
            reserved_usd=account.reserved_usd - reservation.amount_usd,
            cumulative_released_usd=(
                account.cumulative_released_usd + reservation.amount_usd
            ),
        )
        return CapitalSourceLedger(
            accounts=self._replace_account(updated),
            reservations=self._replace_reservation(
                replace(
                    reservation,
                    state=ReservationState.RELEASED,
                    returned_capacity_usd=reservation.amount_usd,
                )
            ),
        )

    def settle_deployment(
        self,
        reservation_id: str,
        *,
        returned_capacity_usd: Decimal,
    ) -> CapitalSourceLedger:
        """Settle deployed capacity with explicit returned vs consumed amount."""

        reservation = self._reservation(reservation_id)
        if reservation.state is not ReservationState.DEPLOYED:
            raise CiboCapitalManagementError("only DEPLOYED capacity can settle")
        if (
            not isinstance(returned_capacity_usd, Decimal)
            or not returned_capacity_usd.is_finite()
            or returned_capacity_usd < 0
            or returned_capacity_usd > reservation.amount_usd
        ):
            raise CiboCapitalManagementError("returned capacity outside deployed amount")
        consumed = reservation.amount_usd - returned_capacity_usd
        account = self._account(reservation.source_id)
        updated = replace(
            account,
            deployed_usd=account.deployed_usd - reservation.amount_usd,
            consumed_usd=account.consumed_usd + consumed,
            cumulative_released_usd=(
                account.cumulative_released_usd + returned_capacity_usd
            ),
        )
        return CapitalSourceLedger(
            accounts=self._replace_account(updated),
            reservations=self._replace_reservation(
                replace(
                    reservation,
                    state=ReservationState.SETTLED,
                    returned_capacity_usd=returned_capacity_usd,
                    consumed_capacity_usd=consumed,
                )
            ),
        )

    def _account(self, source_id: str) -> CapitalSourceAccount:
        found = tuple(item for item in self.accounts if item.source_id == source_id)
        if len(found) != 1:
            raise CiboCapitalManagementError("capital source not found")
        return found[0]

    def _reservation(self, reservation_id: str) -> CapitalReservation:
        found = tuple(
            item for item in self.reservations if item.reservation_id == reservation_id
        )
        if len(found) != 1:
            raise CiboCapitalManagementError("reservation not found")
        return found[0]

    def _replace_account(
        self,
        replacement: CapitalSourceAccount,
    ) -> tuple[CapitalSourceAccount, ...]:
        return tuple(
            replacement if item.source_id == replacement.source_id else item
            for item in self.accounts
        )

    def _replace_reservation(
        self,
        replacement: CapitalReservation,
    ) -> tuple[CapitalReservation, ...]:
        return tuple(
            replacement if item.reservation_id == replacement.reservation_id else item
            for item in self.reservations
        )
