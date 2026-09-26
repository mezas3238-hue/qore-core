"""Durable lifecycle state for CIBO CMA positions.

The store persists CMA stage transitions across restart and validates every
transition through the canonical state machine. It has no broker mutation
authority.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_capital_management_authority import CapitalStage
from qore.infrastructure.cibo_capital_state_machine import (
    CmaStateMachineError,
    validate_transition,
)

_SCHEMA = "CIBO_CMA_LIFECYCLE_BOOK_V1"


class DurableCmaLifecycleError(CmaStateMachineError):
    """Durable CMA lifecycle state cannot be trusted or updated safely."""


@dataclass(frozen=True, slots=True)
class CmaLifecycleRecord:
    signal_fingerprint: str
    position_id: int
    stage: CapitalStage
    transition_count: int
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise DurableCmaLifecycleError("signal_fingerprint is required")
        if (
            not isinstance(self.position_id, int)
            or isinstance(self.position_id, bool)
            or self.position_id <= 0
        ):
            raise DurableCmaLifecycleError("position_id must be positive int")
        if type(self.stage) is not CapitalStage:
            raise DurableCmaLifecycleError("stage must be CapitalStage")
        if (
            not isinstance(self.transition_count, int)
            or isinstance(self.transition_count, bool)
            or self.transition_count < 0
        ):
            raise DurableCmaLifecycleError(
                "transition_count must be non-negative int"
            )
        if (
            not isinstance(self.observed_at, datetime)
            or self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise DurableCmaLifecycleError(
                "observed_at must be timezone-aware datetime"
            )


@dataclass(frozen=True, slots=True)
class VersionedCmaLifecycleBook:
    generation: int
    records: tuple[CmaLifecycleRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurableCmaLifecycleError(
                "generation must be non-negative int"
            )
        keys = tuple(
            (record.signal_fingerprint, record.position_id)
            for record in self.records
        )
        if len(keys) != len(set(keys)):
            raise DurableCmaLifecycleError(
                "duplicate lifecycle identity"
            )

    def record_for(
        self,
        *,
        signal_fingerprint: str,
        position_id: int,
    ) -> CmaLifecycleRecord | None:
        found = tuple(
            record
            for record in self.records
            if record.signal_fingerprint == signal_fingerprint
            and record.position_id == position_id
        )
        if len(found) > 1:
            raise DurableCmaLifecycleError(
                "duplicate lifecycle identity"
            )
        return found[0] if found else None


class DurableCmaLifecycleStore:
    """CAS-protected durable CMA lifecycle store."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise DurableCmaLifecycleError("path must be pathlib.Path")
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedCmaLifecycleBook:
        with self._lock:
            return self._load_unlocked()

    def register_seed(
        self,
        *,
        signal_fingerprint: str,
        position_id: int,
        observed_at: datetime,
        expected_generation: int,
    ) -> VersionedCmaLifecycleBook:
        record = CmaLifecycleRecord(
            signal_fingerprint=signal_fingerprint,
            position_id=position_id,
            stage=CapitalStage.MINIMAL_SEED,
            transition_count=0,
            observed_at=observed_at,
        )
        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                self._assert_generation(current, expected_generation)
                existing = current.record_for(
                    signal_fingerprint=signal_fingerprint,
                    position_id=position_id,
                )
                if existing is not None:
                    if existing == record:
                        return current
                    raise DurableCmaLifecycleError(
                        "lifecycle seed identity already registered"
                    )
                next_book = VersionedCmaLifecycleBook(
                    generation=current.generation + 1,
                    records=tuple(
                        sorted(
                            current.records + (record,),
                            key=lambda item: (
                                item.signal_fingerprint,
                                item.position_id,
                            ),
                        )
                    ),
                )
                self._write_unlocked(next_book)
                return next_book
            finally:
                self._release_writer_lock()

    def advance(
        self,
        *,
        signal_fingerprint: str,
        position_id: int,
        target_stage: CapitalStage,
        observed_at: datetime,
        expected_generation: int,
    ) -> VersionedCmaLifecycleBook:
        if type(target_stage) is not CapitalStage:
            raise DurableCmaLifecycleError(
                "target_stage must be CapitalStage"
            )
        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                self._assert_generation(current, expected_generation)
                record = current.record_for(
                    signal_fingerprint=signal_fingerprint,
                    position_id=position_id,
                )
                if record is None:
                    raise DurableCmaLifecycleError(
                        "lifecycle seed must be registered before transition"
                    )
                validate_transition(record.stage, target_stage)
                if target_stage is record.stage:
                    return current
                if observed_at < record.observed_at:
                    raise DurableCmaLifecycleError(
                        "lifecycle observation time moved backwards"
                    )
                updated = CmaLifecycleRecord(
                    signal_fingerprint=record.signal_fingerprint,
                    position_id=record.position_id,
                    stage=target_stage,
                    transition_count=record.transition_count + 1,
                    observed_at=observed_at,
                )
                records = tuple(
                    updated
                    if (
                        item.signal_fingerprint == signal_fingerprint
                        and item.position_id == position_id
                    )
                    else item
                    for item in current.records
                )
                next_book = VersionedCmaLifecycleBook(
                    generation=current.generation + 1,
                    records=records,
                )
                self._write_unlocked(next_book)
                return next_book
            finally:
                self._release_writer_lock()

    def _assert_generation(
        self,
        book: VersionedCmaLifecycleBook,
        expected_generation: int,
    ) -> None:
        if (
            not isinstance(expected_generation, int)
            or isinstance(expected_generation, bool)
            or expected_generation < 0
        ):
            raise DurableCmaLifecycleError(
                "expected_generation must be non-negative int"
            )
        if book.generation != expected_generation:
            raise DurableCmaLifecycleError(
                "stale lifecycle generation"
            )

    def _load_unlocked(self) -> VersionedCmaLifecycleBook:
        if not self._path.exists():
            return VersionedCmaLifecycleBook(generation=0)
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurableCmaLifecycleError(
                "durable lifecycle store is unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise DurableCmaLifecycleError(
                "durable lifecycle schema mismatch"
            )
        generation = raw.get("generation")
        rows = raw.get("records")
        if (
            not isinstance(generation, int)
            or isinstance(generation, bool)
            or generation < 0
            or not isinstance(rows, list)
        ):
            raise DurableCmaLifecycleError(
                "durable lifecycle payload invalid"
            )
        try:
            records = tuple(_record_from_json(item) for item in rows)
            return VersionedCmaLifecycleBook(
                generation=generation,
                records=records,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DurableCmaLifecycleError(
                "durable lifecycle record invalid"
            ) from error

    def _write_unlocked(
        self,
        book: VersionedCmaLifecycleBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "records": [_record_to_json(record) for record in book.records],
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
            raise DurableCmaLifecycleError(
                "durable lifecycle write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurableCmaLifecycleError(
                "lifecycle writer lock already held; reconciliation required"
            ) from error
        except OSError as error:
            raise DurableCmaLifecycleError(
                "lifecycle writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurableCmaLifecycleError(
                "lifecycle writer lock release failed"
            ) from error


def _record_to_json(record: CmaLifecycleRecord) -> dict[str, object]:
    return {
        "signal_fingerprint": record.signal_fingerprint,
        "position_id": record.position_id,
        "stage": record.stage.value,
        "transition_count": record.transition_count,
        "observed_at": record.observed_at.astimezone(UTC).isoformat(),
    }


def _record_from_json(value: object) -> CmaLifecycleRecord:
    if not isinstance(value, dict):
        raise TypeError("lifecycle row must be object")
    return CmaLifecycleRecord(
        signal_fingerprint=str(value["signal_fingerprint"]),
        position_id=int(str(value["position_id"])),
        stage=CapitalStage(str(value["stage"])),
        transition_count=int(str(value["transition_count"])),
        observed_at=datetime.fromisoformat(str(value["observed_at"])),
    )
