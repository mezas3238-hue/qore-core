"""Durable fail-closed store for the CIBO Capital Source Ledger."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalReservation,
    CapitalSourceAccount,
    CapitalSourceLedger,
    ReservationState,
)

_SCHEMA = "CIBO_CAPITAL_SOURCE_LEDGER_V1"


class DurableCapitalLedgerError(CiboCapitalManagementError):
    """Durable capital ledger cannot be trusted or updated safely."""


@dataclass(frozen=True, slots=True)
class VersionedCapitalSourceLedger:
    generation: int
    ledger: CapitalSourceLedger

    def __post_init__(self) -> None:
        if not isinstance(self.generation, int) or isinstance(self.generation, bool):
            raise DurableCapitalLedgerError("generation must be int")
        if self.generation < 0:
            raise DurableCapitalLedgerError("generation cannot be negative")
        if not isinstance(self.ledger, CapitalSourceLedger):
            raise DurableCapitalLedgerError("ledger must be CapitalSourceLedger")


class DurableCapitalSourceLedgerStore:
    """Atomic snapshot store with generation CAS and cross-process writer lock."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise DurableCapitalLedgerError("path must be pathlib.Path")
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedCapitalSourceLedger:
        with self._lock:
            return self._load_unlocked()

    def store(
        self,
        ledger: CapitalSourceLedger,
        *,
        expected_generation: int,
    ) -> VersionedCapitalSourceLedger:
        if not isinstance(ledger, CapitalSourceLedger):
            raise DurableCapitalLedgerError("ledger must be CapitalSourceLedger")
        if (
            not isinstance(expected_generation, int)
            or isinstance(expected_generation, bool)
            or expected_generation < 0
        ):
            raise DurableCapitalLedgerError(
                "expected_generation must be non-negative int"
            )
        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise DurableCapitalLedgerError(
                        "stale capital ledger generation"
                    )
                next_version = VersionedCapitalSourceLedger(
                    generation=current.generation + 1,
                    ledger=ledger,
                )
                self._write_unlocked(next_version)
                return next_version
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedCapitalSourceLedger:
        if not self._path.exists():
            return VersionedCapitalSourceLedger(
                generation=0,
                ledger=CapitalSourceLedger(),
            )
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurableCapitalLedgerError(
                "durable capital ledger is unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise DurableCapitalLedgerError("durable capital ledger schema mismatch")
        generation = raw.get("generation")
        if not isinstance(generation, int) or isinstance(generation, bool):
            raise DurableCapitalLedgerError("durable capital generation invalid")
        accounts_raw = raw.get("accounts")
        reservations_raw = raw.get("reservations")
        if not isinstance(accounts_raw, list) or not isinstance(reservations_raw, list):
            raise DurableCapitalLedgerError("durable capital ledger rows missing")
        try:
            accounts = tuple(_account_from_json(item) for item in accounts_raw)
            reservations = tuple(
                _reservation_from_json(item) for item in reservations_raw
            )
            ledger = CapitalSourceLedger(
                accounts=accounts,
                reservations=reservations,
            )
        except (KeyError, TypeError, ValueError, InvalidOperation) as error:
            raise DurableCapitalLedgerError(
                "durable capital ledger payload invalid"
            ) from error
        _validate_references(ledger)
        return VersionedCapitalSourceLedger(generation=generation, ledger=ledger)

    def _write_unlocked(self, version: VersionedCapitalSourceLedger) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": version.generation,
            "accounts": [
                _account_to_json(item)
                for item in sorted(
                    version.ledger.accounts,
                    key=lambda item: item.source_id,
                )
            ],
            "reservations": [
                _reservation_to_json(item)
                for item in sorted(
                    version.ledger.reservations,
                    key=lambda item: item.reservation_id,
                )
            ],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        except OSError as error:
            raise DurableCapitalLedgerError(
                "durable capital ledger write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurableCapitalLedgerError(
                "capital ledger writer lock already held; reconciliation required"
            ) from error
        except OSError as error:
            raise DurableCapitalLedgerError(
                "capital ledger writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurableCapitalLedgerError(
                "capital ledger writer lock release failed"
            ) from error


def _validate_references(ledger: CapitalSourceLedger) -> None:
    source_ids = {item.source_id for item in ledger.accounts}
    if len(source_ids) != len(ledger.accounts):
        raise DurableCapitalLedgerError("duplicate durable capital source")
    reservation_ids = {item.reservation_id for item in ledger.reservations}
    if len(reservation_ids) != len(ledger.reservations):
        raise DurableCapitalLedgerError("duplicate durable reservation")
    if any(item.source_id not in source_ids for item in ledger.reservations):
        raise DurableCapitalLedgerError("reservation references missing capital source")


def _account_to_json(account: CapitalSourceAccount) -> dict[str, object]:
    return {
        "source_id": account.source_id,
        "source": account.source.value,
        "proven_amount_usd": format(account.proven_amount_usd, "f"),
        "reserved_usd": format(account.reserved_usd, "f"),
        "deployed_usd": format(account.deployed_usd, "f"),
        "consumed_usd": format(account.consumed_usd, "f"),
        "cumulative_released_usd": format(
            account.cumulative_released_usd,
            "f",
        ),
    }


def _account_from_json(value: object) -> CapitalSourceAccount:
    if not isinstance(value, dict):
        raise TypeError("capital account row must be object")
    return CapitalSourceAccount(
        source_id=str(value["source_id"]),
        source=CapitalSource(str(value["source"])),
        proven_amount_usd=Decimal(str(value["proven_amount_usd"])),
        reserved_usd=Decimal(str(value["reserved_usd"])),
        deployed_usd=Decimal(str(value["deployed_usd"])),
        consumed_usd=Decimal(str(value["consumed_usd"])),
        cumulative_released_usd=Decimal(
            str(value["cumulative_released_usd"])
        ),
    )


def _reservation_to_json(
    reservation: CapitalReservation,
) -> dict[str, object]:
    return {
        "reservation_id": reservation.reservation_id,
        "source_id": reservation.source_id,
        "amount_usd": format(reservation.amount_usd, "f"),
        "state": reservation.state.value,
        "returned_capacity_usd": format(
            reservation.returned_capacity_usd,
            "f",
        ),
        "consumed_capacity_usd": format(
            reservation.consumed_capacity_usd,
            "f",
        ),
    }


def _reservation_from_json(value: object) -> CapitalReservation:
    if not isinstance(value, dict):
        raise TypeError("capital reservation row must be object")
    return CapitalReservation(
        reservation_id=str(value["reservation_id"]),
        source_id=str(value["source_id"]),
        amount_usd=Decimal(str(value["amount_usd"])),
        state=ReservationState(str(value["state"])),
        returned_capacity_usd=Decimal(str(value["returned_capacity_usd"])),
        consumed_capacity_usd=Decimal(str(value["consumed_capacity_usd"])),
    )
