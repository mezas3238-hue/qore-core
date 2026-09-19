"""Deterministic in-memory reference implementation of the L4 risk-capacity ledger.

This module owns the single-currency capacity-accounting plane for the DEMO
profitability program. It provides an immutable, deterministic reference ledger
(:class:`RiskCapacityLedger`) plus a lock-free, single-threaded in-memory
integration seam (:class:`InMemoryRiskCapacityStore`).

The external durability/atomicity requirement (a durable transactional store
that survives process and host failure and atomically commits ledger
transitions) is OUTSIDE this repository boundary. :class:`InMemoryRiskCapacityStore`
is deterministic and fail-closed but not durable: it is the reference behaviour
against which a real distributed/durable adapter must be built and reconciled.

No ambient clock, no ambient UUID, no threads, no global mutable state, no
``float``, and exact runtime types throughout. Capacity is accounted using the
``notional`` of each reservation (the authorized notional being reserved).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from qore.infrastructure.proprietary_accounts import MoneyAmount
from qore.infrastructure.risk_authority import (
    RiskError,
    RiskReservation,
    RiskReservationId,
    RiskReservationStatus,
)
from qore.kernel.result import Failure, Result, Success

__all__ = [
    "InMemoryRiskCapacityStore",
    "RiskCapacityConflictError",
    "RiskCapacityError",
    "RiskCapacityLedger",
    "RiskCapacityValidationError",
]


class RiskCapacityError(RiskError):
    """Base error for the L4 risk-capacity ledger."""

    __slots__ = ()


class RiskCapacityValidationError(RiskCapacityError):
    """Violation of a risk-capacity invariant (type, currency, or status)."""

    __slots__ = ()


class RiskCapacityConflictError(RiskCapacityError):
    """A capacity transition conflicts with the current ledger state."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class RiskCapacityLedger:
    """Immutable deterministic reference ledger of capacity reservations.

    A valid ledger has unique reservation identities, exactly one currency
    across all reservations and the capacity bound, and the summed ``notional``
    of non-released/non-expired reservations never exceeds ``capacity``.
    """

    reservations: tuple[RiskReservation, ...]
    generation: int
    capacity: MoneyAmount

    def __post_init__(self) -> None:
        if not isinstance(self.reservations, tuple):
            raise RiskCapacityValidationError("reservations must be a tuple")
        if any(not isinstance(item, RiskReservation) for item in self.reservations):
            raise RiskCapacityValidationError(
                "reservations must contain only RiskReservation values"
            )
        if type(self.generation) is not int or self.generation < 0:
            raise RiskCapacityValidationError(
                "generation must be a non-negative integer"
            )
        if not isinstance(self.capacity, MoneyAmount):
            raise RiskCapacityValidationError("capacity must be MoneyAmount")
        if self.capacity.amount < 0:
            raise RiskCapacityValidationError("capacity must not be negative")

        reservation_ids = [item.reservation_id for item in self.reservations]
        if len(set(reservation_ids)) != len(reservation_ids):
            raise RiskCapacityValidationError("reservation ids must be unique")

        for item in self.reservations:
            if item.notional.currency != self.capacity.currency:
                raise RiskCapacityValidationError(
                    "reservation notional currency must match capacity currency"
                )

        if self.reserved_notional().amount > self.capacity.amount:
            raise RiskCapacityValidationError("reserved notional exceeds capacity")

    def get(self, reservation_id: RiskReservationId) -> RiskReservation | None:
        """Return the reservation with the exact id, or None when absent."""

        if not isinstance(reservation_id, RiskReservationId):
            raise RiskCapacityValidationError("reservation_id must be RiskReservationId")
        return self._find(reservation_id)

    def reserved_notional(self) -> MoneyAmount:
        """Sum of the notional of RESERVED and COMMITTED reservations."""

        return MoneyAmount(self.capacity.currency, self._sum_notional(_RESERVED_OR_COMMITTED))

    def committed_notional(self) -> MoneyAmount:
        """Sum of the notional of COMMITTED reservations."""

        return MoneyAmount(self.capacity.currency, self._sum_notional(_COMMITTED))

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(item.logical_values() for item in self.reservations),
            self.generation,
            self.capacity.logical_values(),
        )

    def reserve(
        self, reservation: RiskReservation
    ) -> Result[RiskCapacityLedger, RiskCapacityError]:
        """Reserve notional under monotonic generation fencing (never mutates)."""

        if not isinstance(reservation, RiskReservation):
            return Failure(RiskCapacityValidationError("reservation must be RiskReservation"))
        if reservation.status is not RiskReservationStatus.RESERVED:
            return Failure(
                RiskCapacityValidationError("only RESERVED reservations can be reserved")
            )
        if reservation.notional.currency != self.capacity.currency:
            return Failure(
                RiskCapacityValidationError(
                    "reservation notional currency must match capacity currency"
                )
            )
        if self._find(reservation.reservation_id) is not None:
            return Failure(RiskCapacityConflictError("reservation id already exists"))
        if reservation.generation <= self.generation:
            return Failure(
                RiskCapacityConflictError("reservation generation must strictly increase")
            )
        if self.reserved_notional().amount + reservation.notional.amount > self.capacity.amount:
            return Failure(RiskCapacityConflictError("risk capacity is exhausted"))
        return self._new_ledger(self.reservations + (reservation,), reservation.generation)

    def commit(
        self, reservation_id: RiskReservationId
    ) -> Result[RiskCapacityLedger, RiskCapacityError]:
        """Transition a RESERVED reservation to COMMITTED (never mutates)."""

        if not isinstance(reservation_id, RiskReservationId):
            return Failure(RiskCapacityValidationError("reservation_id must be RiskReservationId"))
        reservation = self._find(reservation_id)
        if reservation is None:
            return Failure(RiskCapacityConflictError("reservation not found"))
        if reservation.status is RiskReservationStatus.COMMITTED:
            return Success(self)
        if reservation.status in (
            RiskReservationStatus.RELEASED,
            RiskReservationStatus.EXPIRED,
        ):
            return Failure(
                RiskCapacityConflictError("cannot commit a released or expired reservation")
            )
        if reservation.generation < self.generation:
            return Failure(RiskCapacityConflictError("stale reservation"))
        return self._transition(reservation, status=RiskReservationStatus.COMMITTED)

    def release(
        self, reservation_id: RiskReservationId
    ) -> Result[RiskCapacityLedger, RiskCapacityError]:
        """Release a RESERVED or COMMITTED reservation, freeing its notional."""

        if not isinstance(reservation_id, RiskReservationId):
            return Failure(RiskCapacityValidationError("reservation_id must be RiskReservationId"))
        reservation = self._find(reservation_id)
        if reservation is None:
            return Failure(RiskCapacityConflictError("reservation not found"))
        if reservation.status is RiskReservationStatus.RELEASED:
            return Success(self)
        if reservation.status is RiskReservationStatus.EXPIRED:
            return Failure(RiskCapacityConflictError("cannot release an expired reservation"))
        return self._transition(reservation, status=RiskReservationStatus.RELEASED)

    def expire(
        self, reservation_id: RiskReservationId
    ) -> Result[RiskCapacityLedger, RiskCapacityError]:
        """Expire a stale RESERVED reservation, freeing its notional."""

        if not isinstance(reservation_id, RiskReservationId):
            return Failure(RiskCapacityValidationError("reservation_id must be RiskReservationId"))
        reservation = self._find(reservation_id)
        if reservation is None:
            return Failure(RiskCapacityConflictError("reservation not found"))
        if reservation.status is RiskReservationStatus.EXPIRED:
            return Success(self)
        if reservation.status in (
            RiskReservationStatus.COMMITTED,
            RiskReservationStatus.RELEASED,
        ):
            return Failure(
                RiskCapacityConflictError("cannot expire a committed or released reservation")
            )
        return self._transition(reservation, status=RiskReservationStatus.EXPIRED)

    def _find(self, reservation_id: RiskReservationId) -> RiskReservation | None:
        for item in self.reservations:
            if item.reservation_id == reservation_id:
                return item
        return None

    def _sum_notional(
        self, statuses: frozenset[RiskReservationStatus]
    ) -> Decimal:
        total = Decimal(0)
        for item in self.reservations:
            if item.status in statuses:
                total += item.notional.amount
        return total

    def _new_ledger(
        self,
        reservations: tuple[RiskReservation, ...],
        generation: int,
    ) -> Result[RiskCapacityLedger, RiskCapacityError]:
        try:
            return Success(RiskCapacityLedger(reservations, generation, self.capacity))
        except RiskCapacityValidationError as error:
            return Failure(error)

    def _transition(
        self,
        reservation: RiskReservation,
        *,
        status: RiskReservationStatus,
    ) -> Result[RiskCapacityLedger, RiskCapacityError]:
        updated = replace(reservation, status=status)
        updated_reservations = tuple(
            updated if item.reservation_id == reservation.reservation_id else item
            for item in self.reservations
        )
        return self._new_ledger(updated_reservations, self.generation)


_RESERVED_OR_COMMITTED = frozenset(
    {RiskReservationStatus.RESERVED, RiskReservationStatus.COMMITTED}
)
_COMMITTED = frozenset({RiskReservationStatus.COMMITTED})


class InMemoryRiskCapacityStore:
    """Lock-free, single-threaded, deterministic in-memory capacity store.

    This is the mutable integration seam that implements the
    :class:`qore.infrastructure.risk_authority.RiskCapacityStore` protocol. It
    delegates every transition to the pure :class:`RiskCapacityLedger` and swaps
    in the returned immutable ledger on success, so a failed transition never
    mutates observable state.

    This is NOT a durable store: the external durability/atomicity requirement
    is outside this repository boundary.
    """

    def __init__(self, capacity: MoneyAmount) -> None:
        self._ledger = RiskCapacityLedger((), 0, capacity)

    @property
    def ledger(self) -> RiskCapacityLedger:
        return self._ledger

    @property
    def capacity(self) -> MoneyAmount:
        return self._ledger.capacity

    def reserve(self, reservation: RiskReservation) -> Result[RiskReservation, RiskError]:
        result = self._ledger.reserve(reservation)
        if isinstance(result, Failure):
            return result
        self._ledger = result.value
        return Success(reservation)

    def commit(self, reservation_id: RiskReservationId) -> Result[RiskReservation, RiskError]:
        result = self._ledger.commit(reservation_id)
        if isinstance(result, Failure):
            return result
        committed = result.value.get(reservation_id)
        if committed is None:
            return Failure(RiskCapacityConflictError("reservation not found after commit"))
        self._ledger = result.value
        return Success(committed)

    def release(self, reservation_id: RiskReservationId) -> Result[RiskReservation, RiskError]:
        result = self._ledger.release(reservation_id)
        if isinstance(result, Failure):
            return result
        released = result.value.get(reservation_id)
        if released is None:
            return Failure(RiskCapacityConflictError("reservation not found after release"))
        self._ledger = result.value
        return Success(released)

    def expire(self, reservation_id: RiskReservationId) -> Result[RiskReservation, RiskError]:
        result = self._ledger.expire(reservation_id)
        if isinstance(result, Failure):
            return result
        expired = result.value.get(reservation_id)
        if expired is None:
            return Failure(RiskCapacityConflictError("reservation not found after expire"))
        self._ledger = result.value
        return Success(expired)

    def get(self, reservation_id: RiskReservationId) -> Result[RiskReservation | None, RiskError]:
        if not isinstance(reservation_id, RiskReservationId):
            return Failure(RiskCapacityValidationError("reservation_id must be RiskReservationId"))
        return Success(self._ledger.get(reservation_id))
