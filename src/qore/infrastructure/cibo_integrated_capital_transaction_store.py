"""Crash-safe two-phase evidence journal for integrated CIBO capital updates.

The underlying CIBO ledgers remain separate durable stores. This journal does
not pretend their filesystem writes are atomic. Instead it prevents a partial
multi-ledger update from becoming accepted economic truth: a transition is
PREPARED first and COMMITTED only after every component generation/digest and
the derived IntegratedCapitalTruth digest match the prepared target.

An unresolved PREPARE blocks the next transaction until reconciliation.
Research/shadow only; no productive authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from threading import RLock

_SCHEMA = "CIBO_INTEGRATED_CAPITAL_TRANSACTION_BOOK_V1"


class IntegratedCapitalTransactionError(ValueError):
    """Integrated multi-ledger transaction evidence is inconsistent."""


class IntegratedCapitalComponent(StrEnum):
    SOURCE_LEDGER = "SOURCE_LEDGER"
    COMPOUND_PORTFOLIO = "COMPOUND_PORTFOLIO"
    PROTECTED_FLOOR = "PROTECTED_FLOOR"
    T19_ALLOCATION = "T19_ALLOCATION"
    CMA_SETTLEMENT = "CMA_SETTLEMENT"


_REQUIRED_COMPONENTS = frozenset(IntegratedCapitalComponent)


class IntegratedCapitalTransactionEventType(StrEnum):
    PREPARE = "PREPARE"
    COMMIT = "COMMIT"


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise IntegratedCapitalTransactionError(
            f"integrated transaction {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise IntegratedCapitalTransactionError(
            f"integrated transaction {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class IntegratedCapitalComponentRef:
    component: IntegratedCapitalComponent
    generation: int
    sha256: str

    def __post_init__(self) -> None:
        if type(self.component) is not IntegratedCapitalComponent:
            raise IntegratedCapitalTransactionError(
                "integrated transaction component is invalid"
            )
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise IntegratedCapitalTransactionError(
                "integrated transaction component generation is invalid"
            )
        _sha(self.sha256, "component sha256")


@dataclass(frozen=True, slots=True)
class IntegratedCapitalTransactionEvent:
    event_id: str
    transaction_id: str
    event_type: IntegratedCapitalTransactionEventType
    occurred_at: datetime
    before_refs: tuple[IntegratedCapitalComponentRef, ...]
    after_refs: tuple[IntegratedCapitalComponentRef, ...]
    capital_truth_before_sha256: str
    capital_truth_after_sha256: str
    previous_event_sha256: str | None = None
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.event_id or not self.transaction_id:
            raise IntegratedCapitalTransactionError(
                "integrated transaction event identity is required"
            )
        if type(self.event_type) is not IntegratedCapitalTransactionEventType:
            raise IntegratedCapitalTransactionError(
                "integrated transaction event type is invalid"
            )
        _aware(self.occurred_at, "occurred_at")
        _validate_refs(self.before_refs, "before")
        _validate_refs(self.after_refs, "after")
        _sha(
            self.capital_truth_before_sha256,
            "capital_truth_before_sha256",
        )
        _sha(
            self.capital_truth_after_sha256,
            "capital_truth_after_sha256",
        )
        if self.previous_event_sha256 is not None:
            _sha(self.previous_event_sha256, "previous_event_sha256")
        if self.productive_authority:
            raise IntegratedCapitalTransactionError(
                "integrated transaction journal has no productive authority"
            )

    def fingerprint(self) -> str:
        payload = {
            "event_id": self.event_id,
            "transaction_id": self.transaction_id,
            "event_type": self.event_type.value,
            "occurred_at": self.occurred_at.isoformat(),
            "before_refs": [_ref_payload(item) for item in self.before_refs],
            "after_refs": [_ref_payload(item) for item in self.after_refs],
            "capital_truth_before_sha256": (
                self.capital_truth_before_sha256
            ),
            "capital_truth_after_sha256": self.capital_truth_after_sha256,
            "previous_event_sha256": self.previous_event_sha256,
            "productive_authority": self.productive_authority,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class VersionedIntegratedCapitalTransactionBook:
    generation: int
    events: tuple[IntegratedCapitalTransactionEvent, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise IntegratedCapitalTransactionError(
                "integrated transaction generation is invalid"
            )
        event_ids = tuple(item.event_id for item in self.events)
        if len(event_ids) != len(set(event_ids)):
            raise IntegratedCapitalTransactionError(
                "integrated transaction event ids must be unique"
            )
        previous: str | None = None
        for event in self.events:
            if event.previous_event_sha256 != previous:
                raise IntegratedCapitalTransactionError(
                    "integrated transaction hash chain is broken"
                )
            previous = event.fingerprint()
        for tx_id in self.transaction_ids:
            prepares = tuple(
                item for item in self.events
                if item.transaction_id == tx_id
                and item.event_type
                is IntegratedCapitalTransactionEventType.PREPARE
            )
            commits = tuple(
                item for item in self.events
                if item.transaction_id == tx_id
                and item.event_type
                is IntegratedCapitalTransactionEventType.COMMIT
            )
            if len(prepares) != 1 or len(commits) > 1:
                raise IntegratedCapitalTransactionError(
                    "integrated transaction lifecycle is invalid"
                )
            if commits and self.events.index(commits[0]) < self.events.index(
                prepares[0]
            ):
                raise IntegratedCapitalTransactionError(
                    "integrated transaction commit predates prepare"
                )

    @property
    def transaction_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.transaction_id for item in self.events))

    @property
    def unresolved_transaction_ids(self) -> tuple[str, ...]:
        unresolved: list[str] = []
        for tx_id in self.transaction_ids:
            committed = any(
                item.transaction_id == tx_id
                and item.event_type
                is IntegratedCapitalTransactionEventType.COMMIT
                for item in self.events
            )
            if not committed:
                unresolved.append(tx_id)
        return tuple(unresolved)

    def prepare_for(
        self,
        transaction_id: str,
    ) -> IntegratedCapitalTransactionEvent | None:
        rows = tuple(
            item for item in self.events
            if item.transaction_id == transaction_id
            and item.event_type
            is IntegratedCapitalTransactionEventType.PREPARE
        )
        return rows[0] if rows else None


class DurableIntegratedCapitalTransactionStore:
    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise IntegratedCapitalTransactionError(
                "integrated transaction path must be pathlib.Path"
            )
        self._path = path
        self._lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedIntegratedCapitalTransactionBook:
        with self._lock:
            return self._load_unlocked()

    def prepare(
        self,
        *,
        transaction_id: str,
        before_refs: tuple[IntegratedCapitalComponentRef, ...],
        after_refs: tuple[IntegratedCapitalComponentRef, ...],
        capital_truth_before_sha256: str,
        capital_truth_after_sha256: str,
        prepared_at: datetime,
        expected_generation: int,
    ) -> VersionedIntegratedCapitalTransactionBook:
        with self._lock:
            self._acquire_lock()
            try:
                current = self._load_unlocked()
                _require_generation(current.generation, expected_generation)
                existing = current.prepare_for(transaction_id)
                if existing is not None:
                    candidate = _prepare_event(
                        current=current,
                        transaction_id=transaction_id,
                        before_refs=before_refs,
                        after_refs=after_refs,
                        capital_truth_before_sha256=(
                            capital_truth_before_sha256
                        ),
                        capital_truth_after_sha256=capital_truth_after_sha256,
                        prepared_at=prepared_at,
                    )
                    if (
                        existing.before_refs == candidate.before_refs
                        and existing.after_refs == candidate.after_refs
                        and existing.capital_truth_before_sha256
                        == candidate.capital_truth_before_sha256
                        and existing.capital_truth_after_sha256
                        == candidate.capital_truth_after_sha256
                    ):
                        return current
                    raise IntegratedCapitalTransactionError(
                        "conflicting integrated transaction re-prepare"
                    )
                if current.unresolved_transaction_ids:
                    raise IntegratedCapitalTransactionError(
                        "unresolved integrated transaction blocks new prepare"
                    )
                event = _prepare_event(
                    current=current,
                    transaction_id=transaction_id,
                    before_refs=before_refs,
                    after_refs=after_refs,
                    capital_truth_before_sha256=capital_truth_before_sha256,
                    capital_truth_after_sha256=capital_truth_after_sha256,
                    prepared_at=prepared_at,
                )
                next_book = VersionedIntegratedCapitalTransactionBook(
                    generation=current.generation + 1,
                    events=current.events + (event,),
                )
                self._write_unlocked(next_book)
                return next_book
            finally:
                self._release_lock()

    def commit(
        self,
        *,
        transaction_id: str,
        observed_after_refs: tuple[IntegratedCapitalComponentRef, ...],
        observed_capital_truth_sha256: str,
        committed_at: datetime,
        expected_generation: int,
    ) -> VersionedIntegratedCapitalTransactionBook:
        with self._lock:
            self._acquire_lock()
            try:
                current = self._load_unlocked()
                _require_generation(current.generation, expected_generation)
                prepare = current.prepare_for(transaction_id)
                if prepare is None:
                    raise IntegratedCapitalTransactionError(
                        "integrated transaction prepare is missing"
                    )
                if transaction_id not in current.unresolved_transaction_ids:
                    return current
                _validate_refs(observed_after_refs, "observed after")
                _sha(
                    observed_capital_truth_sha256,
                    "observed_capital_truth_sha256",
                )
                if observed_after_refs != prepare.after_refs:
                    raise IntegratedCapitalTransactionError(
                        "observed component state differs from prepared target"
                    )
                if (
                    observed_capital_truth_sha256
                    != prepare.capital_truth_after_sha256
                ):
                    raise IntegratedCapitalTransactionError(
                        "observed capital truth differs from prepared target"
                    )
                _aware(committed_at, "committed_at")
                if committed_at < prepare.occurred_at:
                    raise IntegratedCapitalTransactionError(
                        "integrated transaction commit predates prepare"
                    )
                event = IntegratedCapitalTransactionEvent(
                    event_id=f"{transaction_id}:commit",
                    transaction_id=transaction_id,
                    event_type=IntegratedCapitalTransactionEventType.COMMIT,
                    occurred_at=committed_at,
                    before_refs=prepare.before_refs,
                    after_refs=prepare.after_refs,
                    capital_truth_before_sha256=(
                        prepare.capital_truth_before_sha256
                    ),
                    capital_truth_after_sha256=(
                        prepare.capital_truth_after_sha256
                    ),
                    previous_event_sha256=(
                        current.events[-1].fingerprint()
                        if current.events
                        else None
                    ),
                    productive_authority=False,
                )
                next_book = VersionedIntegratedCapitalTransactionBook(
                    generation=current.generation + 1,
                    events=current.events + (event,),
                )
                self._write_unlocked(next_book)
                return next_book
            finally:
                self._release_lock()

    def _load_unlocked(self) -> VersionedIntegratedCapitalTransactionBook:
        if not self._path.exists():
            return VersionedIntegratedCapitalTransactionBook(generation=0)
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IntegratedCapitalTransactionError(
                "integrated transaction store is unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise IntegratedCapitalTransactionError(
                "integrated transaction store schema mismatch"
            )
        generation = raw.get("generation")
        rows = raw.get("events")
        if (
            not isinstance(generation, int)
            or isinstance(generation, bool)
            or generation < 0
            or not isinstance(rows, list)
        ):
            raise IntegratedCapitalTransactionError(
                "integrated transaction store payload is invalid"
            )
        try:
            events = tuple(_event_from_payload(item) for item in rows)
            return VersionedIntegratedCapitalTransactionBook(
                generation=generation,
                events=events,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise IntegratedCapitalTransactionError(
                "integrated transaction event payload is invalid"
            ) from error

    def _write_unlocked(
        self,
        book: VersionedIntegratedCapitalTransactionBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "events": [_event_payload(item) for item in book.events],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        except OSError as error:
            raise IntegratedCapitalTransactionError(
                "integrated transaction store write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_lock(self) -> None:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._lock_path.mkdir()
        except FileExistsError as error:
            raise IntegratedCapitalTransactionError(
                "integrated transaction writer lock already held"
            ) from error
        except OSError as error:
            raise IntegratedCapitalTransactionError(
                "integrated transaction writer lock unavailable"
            ) from error

    def _release_lock(self) -> None:
        try:
            self._lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise IntegratedCapitalTransactionError(
                "integrated transaction writer lock release failed"
            ) from error


def _prepare_event(
    *,
    current: VersionedIntegratedCapitalTransactionBook,
    transaction_id: str,
    before_refs: tuple[IntegratedCapitalComponentRef, ...],
    after_refs: tuple[IntegratedCapitalComponentRef, ...],
    capital_truth_before_sha256: str,
    capital_truth_after_sha256: str,
    prepared_at: datetime,
) -> IntegratedCapitalTransactionEvent:
    return IntegratedCapitalTransactionEvent(
        event_id=f"{transaction_id}:prepare",
        transaction_id=transaction_id,
        event_type=IntegratedCapitalTransactionEventType.PREPARE,
        occurred_at=prepared_at,
        before_refs=before_refs,
        after_refs=after_refs,
        capital_truth_before_sha256=capital_truth_before_sha256,
        capital_truth_after_sha256=capital_truth_after_sha256,
        previous_event_sha256=(
            current.events[-1].fingerprint() if current.events else None
        ),
        productive_authority=False,
    )


def _validate_refs(
    refs: tuple[IntegratedCapitalComponentRef, ...],
    label: str,
) -> None:
    if not isinstance(refs, tuple) or any(
        not isinstance(item, IntegratedCapitalComponentRef)
        for item in refs
    ):
        raise IntegratedCapitalTransactionError(
            f"integrated transaction {label} refs are invalid"
        )
    components = tuple(item.component for item in refs)
    if len(components) != len(set(components)):
        raise IntegratedCapitalTransactionError(
            f"integrated transaction {label} components are duplicated"
        )
    if set(components) != set(_REQUIRED_COMPONENTS):
        raise IntegratedCapitalTransactionError(
            f"integrated transaction {label} component coverage is incomplete"
        )


def _require_generation(current: int, expected: int) -> None:
    if (
        not isinstance(expected, int)
        or isinstance(expected, bool)
        or expected < 0
        or current != expected
    ):
        raise IntegratedCapitalTransactionError(
            "stale integrated transaction generation"
        )


def _ref_payload(item: IntegratedCapitalComponentRef) -> dict[str, object]:
    return {
        "component": item.component.value,
        "generation": item.generation,
        "sha256": item.sha256,
    }


def _event_payload(
    item: IntegratedCapitalTransactionEvent,
) -> dict[str, object]:
    return {
        "event_id": item.event_id,
        "transaction_id": item.transaction_id,
        "event_type": item.event_type.value,
        "occurred_at": item.occurred_at.isoformat(),
        "before_refs": [_ref_payload(ref) for ref in item.before_refs],
        "after_refs": [_ref_payload(ref) for ref in item.after_refs],
        "capital_truth_before_sha256": item.capital_truth_before_sha256,
        "capital_truth_after_sha256": item.capital_truth_after_sha256,
        "previous_event_sha256": item.previous_event_sha256,
        "productive_authority": item.productive_authority,
    }


def _event_from_payload(
    value: object,
) -> IntegratedCapitalTransactionEvent:
    if not isinstance(value, dict):
        raise TypeError("integrated transaction event must be object")
    return IntegratedCapitalTransactionEvent(
        event_id=str(value["event_id"]),
        transaction_id=str(value["transaction_id"]),
        event_type=IntegratedCapitalTransactionEventType(
            str(value["event_type"])
        ),
        occurred_at=datetime.fromisoformat(str(value["occurred_at"])),
        before_refs=_refs_from_payload(value["before_refs"]),
        after_refs=_refs_from_payload(value["after_refs"]),
        capital_truth_before_sha256=str(
            value["capital_truth_before_sha256"]
        ),
        capital_truth_after_sha256=str(
            value["capital_truth_after_sha256"]
        ),
        previous_event_sha256=(
            None
            if value["previous_event_sha256"] is None
            else str(value["previous_event_sha256"])
        ),
        productive_authority=bool(value["productive_authority"]),
    )


def _refs_from_payload(
    value: object,
) -> tuple[IntegratedCapitalComponentRef, ...]:
    if not isinstance(value, list):
        raise TypeError("integrated transaction refs must be list")
    rows: list[IntegratedCapitalComponentRef] = []
    for item in value:
        if not isinstance(item, dict):
            raise TypeError("integrated transaction ref must be object")
        rows.append(
            IntegratedCapitalComponentRef(
                component=IntegratedCapitalComponent(
                    str(item["component"])
                ),
                generation=int(str(item["generation"])),
                sha256=str(item["sha256"]),
            )
        )
    return tuple(rows)
