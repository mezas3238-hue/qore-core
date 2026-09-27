"""Durable append-only store for Phase20 executed-risk evidence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)

_SCHEMA = "CIBO_PHASE20D_EXECUTED_RISK_BOOK_V1"


class DurablePhase20ExecutedRiskError(CiboCapitalManagementError):
    """Executed-risk evidence is conflicting, corrupt or not safely writable."""


@dataclass(frozen=True, slots=True)
class VersionedPhase20ExecutedRiskBook:
    generation: int
    evidences: tuple[Phase20ExecutedRiskEvidence, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurablePhase20ExecutedRiskError(
                "executed-risk generation must be non-negative int"
            )
        ids = tuple(item.evidence_id for item in self.evidences)
        keys = tuple(
            (
                item.decision_evidence_sha256,
                item.signal_fingerprint,
                item.position_id,
            )
            for item in self.evidences
        )
        if len(ids) != len(set(ids)):
            raise DurablePhase20ExecutedRiskError(
                "duplicate executed-risk evidence_id"
            )
        if len(keys) != len(set(keys)):
            raise DurablePhase20ExecutedRiskError(
                "duplicate executed-risk decision/signal/position"
            )

    def risk_for(
        self,
        *,
        decision_evidence_sha256: str,
        signal_fingerprint: str,
        position_id: int,
    ) -> Phase20ExecutedRiskEvidence | None:
        matches = tuple(
            item
            for item in self.evidences
            if (
                item.decision_evidence_sha256 == decision_evidence_sha256
                and item.signal_fingerprint == signal_fingerprint
                and item.position_id == position_id
            )
        )
        if len(matches) > 1:
            raise DurablePhase20ExecutedRiskError(
                "duplicate executed-risk decision/signal/position"
            )
        return matches[0] if matches else None


class DurablePhase20ExecutedRiskStore:
    """Atomic CAS store for exact fill-derived Phase20 risk denominators."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise DurablePhase20ExecutedRiskError(
                "executed-risk path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedPhase20ExecutedRiskBook:
        with self._lock:
            return self._load_unlocked()

    def seal(
        self,
        evidence: Phase20ExecutedRiskEvidence,
        *,
        expected_generation: int,
    ) -> VersionedPhase20ExecutedRiskBook:
        if not isinstance(evidence, Phase20ExecutedRiskEvidence):
            raise DurablePhase20ExecutedRiskError(
                "executed-risk evidence must be canonical"
            )
        _generation(expected_generation)

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise DurablePhase20ExecutedRiskError(
                        "stale executed-risk generation"
                    )
                same_id = tuple(
                    item
                    for item in current.evidences
                    if item.evidence_id == evidence.evidence_id
                )
                if same_id:
                    if same_id[0] == evidence:
                        return current
                    raise DurablePhase20ExecutedRiskError(
                        "conflicting executed-risk evidence rewrite"
                    )
                previous = current.risk_for(
                    decision_evidence_sha256=(
                        evidence.decision_evidence_sha256
                    ),
                    signal_fingerprint=evidence.signal_fingerprint,
                    position_id=evidence.position_id,
                )
                if previous is not None:
                    if previous == evidence:
                        return current
                    raise DurablePhase20ExecutedRiskError(
                        "conflicting executed-risk decision/signal/position"
                    )
                updated = VersionedPhase20ExecutedRiskBook(
                    generation=current.generation + 1,
                    evidences=current.evidences + (evidence,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedPhase20ExecutedRiskBook:
        if not self._path.exists():
            return VersionedPhase20ExecutedRiskBook(generation=0)
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurablePhase20ExecutedRiskError(
                "durable executed-risk store is unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise DurablePhase20ExecutedRiskError(
                "durable executed-risk schema mismatch"
            )
        generation = raw.get("generation")
        rows = raw.get("evidences")
        if (
            not isinstance(generation, int)
            or isinstance(generation, bool)
            or generation < 0
            or not isinstance(rows, list)
        ):
            raise DurablePhase20ExecutedRiskError(
                "durable executed-risk payload invalid"
            )
        try:
            return VersionedPhase20ExecutedRiskBook(
                generation=generation,
                evidences=tuple(_from_json(item) for item in rows),
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidOperation,
        ) as error:
            raise DurablePhase20ExecutedRiskError(
                "durable executed-risk evidence invalid"
            ) from error

    def _write_unlocked(
        self,
        book: VersionedPhase20ExecutedRiskBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "evidences": [_to_json(item) for item in book.evidences],
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
            raise DurablePhase20ExecutedRiskError(
                "durable executed-risk write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurablePhase20ExecutedRiskError(
                "executed-risk writer lock already held"
            ) from error
        except OSError as error:
            raise DurablePhase20ExecutedRiskError(
                "executed-risk writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurablePhase20ExecutedRiskError(
                "executed-risk writer lock release failed"
            ) from error


def _to_json(item: Phase20ExecutedRiskEvidence) -> dict[str, object]:
    return {
        "evidence_id": item.evidence_id,
        "decision_evidence_sha256": item.decision_evidence_sha256,
        "signal_fingerprint": item.signal_fingerprint,
        "position_id": item.position_id,
        "executed_initial_stop_risk_usd": format(
            item.executed_initial_stop_risk_usd,
            "f",
        ),
        "observed_at": item.observed_at.isoformat(),
        "fill_evidence_refs": list(item.fill_evidence_refs),
        "fill_reconciled": item.fill_reconciled,
        "mutation_outcome_known": item.mutation_outcome_known,
    }


def _from_json(value: object) -> Phase20ExecutedRiskEvidence:
    if not isinstance(value, dict):
        raise TypeError("executed-risk row must be object")
    refs = value["fill_evidence_refs"]
    if not isinstance(refs, list):
        raise TypeError("executed-risk fill refs must be list")
    return Phase20ExecutedRiskEvidence(
        evidence_id=str(value["evidence_id"]),
        decision_evidence_sha256=str(
            value["decision_evidence_sha256"]
        ),
        signal_fingerprint=str(value["signal_fingerprint"]),
        position_id=int(str(value["position_id"])),
        executed_initial_stop_risk_usd=Decimal(
            str(value["executed_initial_stop_risk_usd"])
        ),
        observed_at=datetime.fromisoformat(str(value["observed_at"])),
        fill_evidence_refs=tuple(str(item) for item in refs),
        fill_reconciled=bool(value["fill_reconciled"]),
        mutation_outcome_known=bool(value["mutation_outcome_known"]),
    )


def _generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise DurablePhase20ExecutedRiskError(
            "expected executed-risk generation must be non-negative int"
        )
