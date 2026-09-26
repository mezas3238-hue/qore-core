"""Durable idempotent settlement book for CIBO CMA position economics."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementLedgerError,
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)

_SCHEMA = "CIBO_CMA_SETTLEMENT_BOOK_V1"


class DurableCmaSettlementStoreError(CmaSettlementLedgerError):
    """Durable settlement evidence cannot be trusted or updated safely."""


@dataclass(frozen=True, slots=True)
class VersionedCmaSettlementBook:
    generation: int
    states: tuple[CmaSettlementState, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurableCmaSettlementStoreError(
                "generation must be non-negative int"
            )
        keys = tuple(
            (state.signal_fingerprint, state.position_id)
            for state in self.states
        )
        if len(keys) != len(set(keys)):
            raise DurableCmaSettlementStoreError(
                "duplicate settlement state identity"
            )

    def state_for(
        self,
        *,
        signal_fingerprint: str,
        position_id: int,
    ) -> CmaSettlementState | None:
        matches = tuple(
            state
            for state in self.states
            if state.signal_fingerprint == signal_fingerprint
            and state.position_id == position_id
        )
        if len(matches) > 1:
            raise DurableCmaSettlementStoreError(
                "duplicate settlement state identity"
            )
        return matches[0] if matches else None


class DurableCmaSettlementStore:
    """Atomic settlement store with generation CAS and restart-safe idempotency."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise DurableCmaSettlementStoreError("path must be pathlib.Path")
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedCmaSettlementBook:
        with self._lock:
            return self._load_unlocked()

    def apply(
        self,
        record: CmaSettlementRecord,
        *,
        expected_generation: int,
    ) -> VersionedCmaSettlementBook:
        if not isinstance(record, CmaSettlementRecord):
            raise DurableCmaSettlementStoreError(
                "record must be CmaSettlementRecord"
            )
        if (
            not isinstance(expected_generation, int)
            or isinstance(expected_generation, bool)
            or expected_generation < 0
        ):
            raise DurableCmaSettlementStoreError(
                "expected_generation must be non-negative int"
            )

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise DurableCmaSettlementStoreError(
                        "stale settlement generation"
                    )
                existing = current.state_for(
                    signal_fingerprint=record.signal_fingerprint,
                    position_id=record.position_id,
                )
                base = existing or CmaSettlementState(
                    signal_fingerprint=record.signal_fingerprint,
                    position_id=record.position_id,
                )
                updated = apply_settlement(base, record)
                if existing is not None and updated == existing:
                    return current

                next_states = tuple(
                    updated
                    if (
                        state.signal_fingerprint == record.signal_fingerprint
                        and state.position_id == record.position_id
                    )
                    else state
                    for state in current.states
                )
                if existing is None:
                    next_states = next_states + (updated,)
                version = VersionedCmaSettlementBook(
                    generation=current.generation + 1,
                    states=tuple(
                        sorted(
                            next_states,
                            key=lambda state: (
                                state.signal_fingerprint,
                                state.position_id,
                            ),
                        )
                    ),
                )
                self._write_unlocked(version)
                return version
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedCmaSettlementBook:
        if not self._path.exists():
            return VersionedCmaSettlementBook(generation=0)
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurableCmaSettlementStoreError(
                "durable settlement store is unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise DurableCmaSettlementStoreError(
                "durable settlement store schema mismatch"
            )
        generation = raw.get("generation")
        rows = raw.get("states")
        if (
            not isinstance(generation, int)
            or isinstance(generation, bool)
            or generation < 0
            or not isinstance(rows, list)
        ):
            raise DurableCmaSettlementStoreError(
                "durable settlement store payload invalid"
            )
        try:
            states = tuple(_state_from_json(item) for item in rows)
            return VersionedCmaSettlementBook(
                generation=generation,
                states=states,
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidOperation,
        ) as error:
            raise DurableCmaSettlementStoreError(
                "durable settlement state invalid"
            ) from error

    def _write_unlocked(self, book: VersionedCmaSettlementBook) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "states": [_state_to_json(state) for state in book.states],
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
            raise DurableCmaSettlementStoreError(
                "durable settlement store write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurableCmaSettlementStoreError(
                "settlement writer lock already held; reconciliation required"
            ) from error
        except OSError as error:
            raise DurableCmaSettlementStoreError(
                "settlement writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurableCmaSettlementStoreError(
                "settlement writer lock release failed"
            ) from error


def _state_to_json(state: CmaSettlementState) -> dict[str, object]:
    return {
        "signal_fingerprint": state.signal_fingerprint,
        "position_id": state.position_id,
        "position_closed": state.position_closed,
        "records": [
            {
                "event": record.event,
                "deal_id": record.deal_id,
                "signal_fingerprint": record.signal_fingerprint,
                "position_id": record.position_id,
                "net_profit_usd": format(record.net_profit_usd, "f"),
                "position_open_after": record.position_open_after,
            }
            for record in state.records
        ],
    }


def _state_from_json(value: object) -> CmaSettlementState:
    if not isinstance(value, dict):
        raise TypeError("settlement state row must be object")
    records_raw = value["records"]
    if not isinstance(records_raw, list):
        raise TypeError("settlement records must be list")
    records = tuple(_record_from_json(item) for item in records_raw)
    closed = value["position_closed"]
    if type(closed) is not bool:
        raise TypeError("position_closed must be bool")
    return CmaSettlementState(
        signal_fingerprint=str(value["signal_fingerprint"]),
        position_id=int(str(value["position_id"])),
        records=records,
        position_closed=closed,
    )


def _record_from_json(value: object) -> CmaSettlementRecord:
    if not isinstance(value, dict):
        raise TypeError("settlement record row must be object")
    open_after = value["position_open_after"]
    if type(open_after) is not bool:
        raise TypeError("position_open_after must be bool")
    return CmaSettlementRecord(
        event=str(value["event"]),
        deal_id=int(str(value["deal_id"])),
        signal_fingerprint=str(value["signal_fingerprint"]),
        position_id=int(str(value["position_id"])),
        net_profit_usd=Decimal(str(value["net_profit_usd"])),
        position_open_after=open_after,
    )
