"""Durable append-only store for Phase20D observational policy decisions.

The forward evidence store is authoritative for the pre-decision payload. This
store binds the deterministic Phase20I/Phase20H result to that exact evidence
SHA after the evidence has already been sealed.

Research-only. No QORE Risk, execution or broker mutation authority.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardDecisionRecord,
    phase20_forward_decision_record_json,
    phase20_forward_decision_record_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)

_SCHEMA = "CIBO_PHASE20D_FORWARD_POLICY_BOOK_V1"


class DurablePhase20ForwardPolicyError(CiboCapitalManagementError):
    """Observational policy evidence cannot be trusted or updated safely."""


@dataclass(frozen=True, slots=True)
class Phase20ForwardPolicyDecisionSeal:
    evidence_sha256: str
    policy_record_sha256: str
    allocator_disposition: str
    selected_signal_fingerprints: tuple[str, ...]
    canonical_record_json: str

    def __post_init__(self) -> None:
        for name in ("evidence_sha256", "policy_record_sha256"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise DurablePhase20ForwardPolicyError(
                    f"forward policy {name} must be canonical SHA-256"
                )
        if not self.allocator_disposition:
            raise DurablePhase20ForwardPolicyError(
                "forward policy allocator disposition is required"
            )
        if len(self.selected_signal_fingerprints) != len(
            set(self.selected_signal_fingerprints)
        ):
            raise DurablePhase20ForwardPolicyError(
                "forward policy selected signals must be unique"
            )
        try:
            parsed = json.loads(self.canonical_record_json)
        except json.JSONDecodeError as error:
            raise DurablePhase20ForwardPolicyError(
                "forward policy canonical record is invalid JSON"
            ) from error
        if not isinstance(parsed, dict):
            raise DurablePhase20ForwardPolicyError(
                "forward policy canonical record must be object"
            )


@dataclass(frozen=True, slots=True)
class VersionedPhase20ForwardPolicyBook:
    generation: int
    decisions: tuple[Phase20ForwardPolicyDecisionSeal, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurablePhase20ForwardPolicyError(
                "forward policy generation must be non-negative int"
            )
        evidence_ids = tuple(item.evidence_sha256 for item in self.decisions)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise DurablePhase20ForwardPolicyError(
                "duplicate forward policy decision for evidence"
            )

    def decision_for_evidence(
        self,
        evidence_sha256: str,
    ) -> Phase20ForwardPolicyDecisionSeal | None:
        rows = tuple(
            item
            for item in self.decisions
            if item.evidence_sha256 == evidence_sha256
        )
        if len(rows) > 1:
            raise DurablePhase20ForwardPolicyError(
                "duplicate forward policy decision for evidence"
            )
        return rows[0] if rows else None


class DurablePhase20ForwardPolicyStore:
    """Atomic append-only policy store with CAS and a cross-process lock."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise DurablePhase20ForwardPolicyError(
                "forward policy path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedPhase20ForwardPolicyBook:
        with self._lock:
            return self._load_unlocked()

    def seal_policy_decision(
        self,
        record: Phase20ForwardDecisionRecord,
        *,
        evidence_store: DurablePhase20ForwardEvidenceStore,
        expected_generation: int,
    ) -> VersionedPhase20ForwardPolicyBook:
        if not isinstance(record, Phase20ForwardDecisionRecord):
            raise DurablePhase20ForwardPolicyError(
                "forward policy record must be canonical"
            )
        if not isinstance(evidence_store, DurablePhase20ForwardEvidenceStore):
            raise DurablePhase20ForwardPolicyError(
                "forward policy requires canonical evidence store"
            )
        _generation(expected_generation)

        evidence_book = evidence_store.load()
        if evidence_book.decision_for_sha(record.evidence_sha256) is None:
            raise DurablePhase20ForwardPolicyError(
                "forward policy has no previously sealed evidence"
            )
        seal = _policy_seal(record)

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise DurablePhase20ForwardPolicyError(
                        "stale forward policy generation"
                    )
                previous = current.decision_for_evidence(
                    seal.evidence_sha256
                )
                if previous is not None:
                    if previous == seal:
                        return current
                    raise DurablePhase20ForwardPolicyError(
                        "conflicting forward policy decision rewrite"
                    )
                updated = VersionedPhase20ForwardPolicyBook(
                    generation=current.generation + 1,
                    decisions=current.decisions + (seal,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedPhase20ForwardPolicyBook:
        if not self._path.exists():
            return VersionedPhase20ForwardPolicyBook(generation=0)
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurablePhase20ForwardPolicyError(
                "durable forward policy store is unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise DurablePhase20ForwardPolicyError(
                "durable forward policy schema mismatch"
            )
        try:
            generation = int(str(raw["generation"]))
            decisions = raw["decisions"]
            if not isinstance(decisions, list):
                raise TypeError("forward policy decisions must be list")
            return VersionedPhase20ForwardPolicyBook(
                generation=generation,
                decisions=tuple(
                    _policy_from_json(item) for item in decisions
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DurablePhase20ForwardPolicyError(
                "durable forward policy payload invalid"
            ) from error

    def _write_unlocked(
        self,
        book: VersionedPhase20ForwardPolicyBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "decisions": [_policy_to_json(item) for item in book.decisions],
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
            raise DurablePhase20ForwardPolicyError(
                "durable forward policy write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurablePhase20ForwardPolicyError(
                "forward policy writer lock already held"
            ) from error
        except OSError as error:
            raise DurablePhase20ForwardPolicyError(
                "forward policy writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurablePhase20ForwardPolicyError(
                "forward policy writer lock release failed"
            ) from error


def _policy_seal(
    record: Phase20ForwardDecisionRecord,
) -> Phase20ForwardPolicyDecisionSeal:
    allocation = record.allocator_decision.allocation
    selected = (
        allocation.selected_signal_fingerprints
        if allocation is not None
        else ()
    )
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=record.evidence_sha256,
        policy_record_sha256=phase20_forward_decision_record_sha256(record),
        allocator_disposition=record.allocator_decision.disposition.value,
        selected_signal_fingerprints=selected,
        canonical_record_json=phase20_forward_decision_record_json(record),
    )


def _policy_to_json(
    item: Phase20ForwardPolicyDecisionSeal,
) -> dict[str, object]:
    return {
        "evidence_sha256": item.evidence_sha256,
        "policy_record_sha256": item.policy_record_sha256,
        "allocator_disposition": item.allocator_disposition,
        "selected_signal_fingerprints": list(
            item.selected_signal_fingerprints
        ),
        "canonical_record_json": item.canonical_record_json,
    }


def _policy_from_json(value: object) -> Phase20ForwardPolicyDecisionSeal:
    if not isinstance(value, dict):
        raise TypeError("forward policy row must be object")
    selected = value["selected_signal_fingerprints"]
    if not isinstance(selected, list):
        raise TypeError("forward policy selected signals must be list")
    return Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=str(value["evidence_sha256"]),
        policy_record_sha256=str(value["policy_record_sha256"]),
        allocator_disposition=str(value["allocator_disposition"]),
        selected_signal_fingerprints=tuple(str(item) for item in selected),
        canonical_record_json=str(value["canonical_record_json"]),
    )


def _generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise DurablePhase20ForwardPolicyError(
            "expected forward policy generation must be non-negative int"
        )
