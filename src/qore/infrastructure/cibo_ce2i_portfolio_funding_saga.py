"""Durable saga journal for CE2I portfolio + funding reservations.

A portfolio allocation store and a capital-source ledger are two independent
durable resources. This journal does NOT pretend they can be committed as one
filesystem-atomic transaction. Instead it records a recoverable saga:

PREPARED
-> PORTFOLIO_RESERVED
-> FUNDING_RESERVED
-> READY_FOR_RISK

Failures move to COMPENSATION_REQUIRED and finally ROLLED_BACK after both
reservations are reconciled/released. Ambiguous evidence moves to
RECONCILIATION_REQUIRED and must fail closed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


_SCHEMA = "CIBO_CE2I_PORTFOLIO_FUNDING_SAGA_V1"


class PortfolioFundingSagaState(StrEnum):
    PREPARED = "PREPARED"
    PORTFOLIO_RESERVED = "PORTFOLIO_RESERVED"
    FUNDING_RESERVED = "FUNDING_RESERVED"
    READY_FOR_RISK = "READY_FOR_RISK"
    COMPENSATION_REQUIRED = "COMPENSATION_REQUIRED"
    ROLLED_BACK = "ROLLED_BACK"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


_ALLOWED: dict[PortfolioFundingSagaState, frozenset[PortfolioFundingSagaState]] = {
    PortfolioFundingSagaState.PREPARED: frozenset(
        {
            PortfolioFundingSagaState.PORTFOLIO_RESERVED,
            PortfolioFundingSagaState.COMPENSATION_REQUIRED,
            PortfolioFundingSagaState.RECONCILIATION_REQUIRED,
        }
    ),
    PortfolioFundingSagaState.PORTFOLIO_RESERVED: frozenset(
        {
            PortfolioFundingSagaState.FUNDING_RESERVED,
            PortfolioFundingSagaState.COMPENSATION_REQUIRED,
            PortfolioFundingSagaState.RECONCILIATION_REQUIRED,
        }
    ),
    PortfolioFundingSagaState.FUNDING_RESERVED: frozenset(
        {
            PortfolioFundingSagaState.READY_FOR_RISK,
            PortfolioFundingSagaState.COMPENSATION_REQUIRED,
            PortfolioFundingSagaState.RECONCILIATION_REQUIRED,
        }
    ),
    PortfolioFundingSagaState.READY_FOR_RISK: frozenset(
        {
            PortfolioFundingSagaState.COMPENSATION_REQUIRED,
            PortfolioFundingSagaState.RECONCILIATION_REQUIRED,
        }
    ),
    PortfolioFundingSagaState.COMPENSATION_REQUIRED: frozenset(
        {
            PortfolioFundingSagaState.ROLLED_BACK,
            PortfolioFundingSagaState.RECONCILIATION_REQUIRED,
        }
    ),
    PortfolioFundingSagaState.ROLLED_BACK: frozenset(),
    PortfolioFundingSagaState.RECONCILIATION_REQUIRED: frozenset(
        {
            PortfolioFundingSagaState.COMPENSATION_REQUIRED,
            PortfolioFundingSagaState.ROLLED_BACK,
        }
    ),
}


class DurablePortfolioFundingSagaError(CiboCapitalManagementError):
    """Portfolio/funding saga state is invalid, stale or ambiguous."""


@dataclass(frozen=True, slots=True)
class PortfolioFundingSagaRecord:
    transaction_id: str
    signal_fingerprint: str
    state: PortfolioFundingSagaState
    funding_reservation_prefix: str
    portfolio_generation: int | None
    funding_generation: int | None
    updated_at: datetime
    reason: str

    def __post_init__(self) -> None:
        if not self.transaction_id or not self.signal_fingerprint:
            raise DurablePortfolioFundingSagaError(
                "transaction_id/signal_fingerprint required"
            )
        if not self.funding_reservation_prefix:
            raise DurablePortfolioFundingSagaError(
                "funding reservation prefix required"
            )
        if type(self.state) is not PortfolioFundingSagaState:
            raise DurablePortfolioFundingSagaError(
                "state must be PortfolioFundingSagaState"
            )
        for name in ("portfolio_generation", "funding_generation"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 1
            ):
                raise DurablePortfolioFundingSagaError(
                    f"{name} must be positive int/null"
                )
        if (
            not isinstance(self.updated_at, datetime)
            or self.updated_at.tzinfo is None
            or self.updated_at.utcoffset() is None
        ):
            raise DurablePortfolioFundingSagaError(
                "updated_at must be timezone-aware"
            )
        if not self.reason:
            raise DurablePortfolioFundingSagaError("reason required")


@dataclass(frozen=True, slots=True)
class VersionedPortfolioFundingSagaBook:
    generation: int
    records: tuple[PortfolioFundingSagaRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurablePortfolioFundingSagaError(
                "generation must be non-negative int"
            )
        ids = tuple(item.transaction_id for item in self.records)
        if len(ids) != len(set(ids)):
            raise DurablePortfolioFundingSagaError(
                "duplicate portfolio funding transaction_id"
            )

    def record_for(
        self,
        transaction_id: str,
    ) -> PortfolioFundingSagaRecord | None:
        found = tuple(
            item for item in self.records if item.transaction_id == transaction_id
        )
        if len(found) > 1:
            raise DurablePortfolioFundingSagaError(
                "duplicate portfolio funding transaction_id"
            )
        return found[0] if found else None


class DurablePortfolioFundingSagaStore:
    """CAS-protected journal used to recover cross-ledger reservation sagas."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise DurablePortfolioFundingSagaError("path must be pathlib.Path")
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedPortfolioFundingSagaBook:
        with self._lock:
            return self._load_unlocked()

    def prepare(
        self,
        *,
        transaction_id: str,
        signal_fingerprint: str,
        funding_reservation_prefix: str,
        updated_at: datetime,
        expected_generation: int,
    ) -> VersionedPortfolioFundingSagaBook:
        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                self._assert_generation(current, expected_generation)
                if current.record_for(transaction_id) is not None:
                    raise DurablePortfolioFundingSagaError(
                        "transaction_id already exists"
                    )
                record = PortfolioFundingSagaRecord(
                    transaction_id=transaction_id,
                    signal_fingerprint=signal_fingerprint,
                    state=PortfolioFundingSagaState.PREPARED,
                    funding_reservation_prefix=funding_reservation_prefix,
                    portfolio_generation=None,
                    funding_generation=None,
                    updated_at=updated_at,
                    reason="saga intent persisted before resource reservation",
                )
                next_book = VersionedPortfolioFundingSagaBook(
                    generation=current.generation + 1,
                    records=current.records + (record,),
                )
                self._write_unlocked(next_book)
                return next_book
            finally:
                self._release_writer_lock()

    def transition(
        self,
        *,
        transaction_id: str,
        target: PortfolioFundingSagaState,
        updated_at: datetime,
        expected_generation: int,
        reason: str,
        portfolio_generation: int | None = None,
        funding_generation: int | None = None,
    ) -> VersionedPortfolioFundingSagaBook:
        if type(target) is not PortfolioFundingSagaState:
            raise DurablePortfolioFundingSagaError(
                "target must be PortfolioFundingSagaState"
            )
        if not reason:
            raise DurablePortfolioFundingSagaError("transition reason required")

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                self._assert_generation(current, expected_generation)
                record = current.record_for(transaction_id)
                if record is None:
                    raise DurablePortfolioFundingSagaError(
                        "portfolio funding transaction not found"
                    )
                if target not in _ALLOWED[record.state]:
                    raise DurablePortfolioFundingSagaError(
                        f"illegal saga transition {record.state.value}->{target.value}"
                    )
                if updated_at < record.updated_at:
                    raise DurablePortfolioFundingSagaError(
                        "saga update time moved backwards"
                    )
                updated = replace(
                    record,
                    state=target,
                    portfolio_generation=(
                        portfolio_generation
                        if portfolio_generation is not None
                        else record.portfolio_generation
                    ),
                    funding_generation=(
                        funding_generation
                        if funding_generation is not None
                        else record.funding_generation
                    ),
                    updated_at=updated_at,
                    reason=reason,
                )
                records = tuple(
                    updated if item.transaction_id == transaction_id else item
                    for item in current.records
                )
                next_book = VersionedPortfolioFundingSagaBook(
                    generation=current.generation + 1,
                    records=records,
                )
                self._write_unlocked(next_book)
                return next_book
            finally:
                self._release_writer_lock()

    def _assert_generation(
        self,
        book: VersionedPortfolioFundingSagaBook,
        expected_generation: int,
    ) -> None:
        if (
            not isinstance(expected_generation, int)
            or isinstance(expected_generation, bool)
            or expected_generation < 0
        ):
            raise DurablePortfolioFundingSagaError(
                "expected_generation must be non-negative int"
            )
        if book.generation != expected_generation:
            raise DurablePortfolioFundingSagaError(
                "stale portfolio funding saga generation"
            )

    def _load_unlocked(self) -> VersionedPortfolioFundingSagaBook:
        if not self._path.exists():
            return VersionedPortfolioFundingSagaBook(generation=0)
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurablePortfolioFundingSagaError(
                "portfolio funding saga store unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise DurablePortfolioFundingSagaError(
                "portfolio funding saga schema mismatch"
            )
        generation = raw.get("generation")
        rows = raw.get("records")
        if (
            not isinstance(generation, int)
            or isinstance(generation, bool)
            or generation < 0
            or not isinstance(rows, list)
        ):
            raise DurablePortfolioFundingSagaError(
                "portfolio funding saga payload invalid"
            )
        try:
            records = tuple(_record_from_json(item) for item in rows)
            return VersionedPortfolioFundingSagaBook(
                generation=generation,
                records=records,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DurablePortfolioFundingSagaError(
                "portfolio funding saga record invalid"
            ) from error

    def _write_unlocked(
        self,
        book: VersionedPortfolioFundingSagaBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "records": [_record_to_json(item) for item in book.records],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        except OSError as error:
            raise DurablePortfolioFundingSagaError(
                "portfolio funding saga write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurablePortfolioFundingSagaError(
                "portfolio funding saga writer lock already held"
            ) from error
        except OSError as error:
            raise DurablePortfolioFundingSagaError(
                "portfolio funding saga writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurablePortfolioFundingSagaError(
                "portfolio funding saga writer lock release failed"
            ) from error


def _record_to_json(record: PortfolioFundingSagaRecord) -> dict[str, object]:
    return {
        "transaction_id": record.transaction_id,
        "signal_fingerprint": record.signal_fingerprint,
        "state": record.state.value,
        "funding_reservation_prefix": record.funding_reservation_prefix,
        "portfolio_generation": record.portfolio_generation,
        "funding_generation": record.funding_generation,
        "updated_at": record.updated_at.isoformat(),
        "reason": record.reason,
    }


def _record_from_json(value: object) -> PortfolioFundingSagaRecord:
    if not isinstance(value, dict):
        raise TypeError("saga row must be object")
    portfolio_generation = value["portfolio_generation"]
    funding_generation = value["funding_generation"]
    return PortfolioFundingSagaRecord(
        transaction_id=str(value["transaction_id"]),
        signal_fingerprint=str(value["signal_fingerprint"]),
        state=PortfolioFundingSagaState(str(value["state"])),
        funding_reservation_prefix=str(value["funding_reservation_prefix"]),
        portfolio_generation=(
            None
            if portfolio_generation is None
            else int(str(portfolio_generation))
        ),
        funding_generation=(
            None
            if funding_generation is None
            else int(str(funding_generation))
        ),
        updated_at=datetime.fromisoformat(str(value["updated_at"])),
        reason=str(value["reason"]),
    )
