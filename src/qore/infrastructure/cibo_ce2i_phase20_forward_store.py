"""Durable append-only store for Phase20D forward evidence.

The store seals a complete pre-decision payload before any outcome can be
appended. It uses generation CAS, a writer lock and atomic replace. It has no
trading, Risk, sizing or execution authority.
"""

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
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardDecisionEvidence,
    Phase20ForwardEvidenceKind,
    Phase20ForwardOutcomeEvidence,
    phase20_forward_evidence_json,
    phase20_forward_evidence_sha256,
)

_SCHEMA = "CIBO_PHASE20D_FORWARD_EVIDENCE_BOOK_V1"


class DurablePhase20ForwardEvidenceError(CiboCapitalManagementError):
    """Forward evidence cannot be trusted or updated safely."""


@dataclass(frozen=True, slots=True)
class Phase20ForwardDecisionSeal:
    evidence_id: str
    evidence_sha256: str
    decision_at: datetime
    candidate_id: str
    code_sha: str
    parameter_sha256: str
    signal_fingerprints: tuple[str, ...]
    canonical_payload_json: str

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.candidate_id:
            raise DurablePhase20ForwardEvidenceError(
                "forward decision seal identity is required"
            )
        if not self.evidence_sha256.startswith("sha256:"):
            raise DurablePhase20ForwardEvidenceError(
                "forward decision seal SHA256 is required"
            )
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise DurablePhase20ForwardEvidenceError(
                "forward decision timestamp must be timezone-aware"
            )
        if not self.code_sha or not self.parameter_sha256:
            raise DurablePhase20ForwardEvidenceError(
                "forward decision policy lineage is required"
            )
        if not self.signal_fingerprints:
            raise DurablePhase20ForwardEvidenceError(
                "forward decision must seal at least one candidate"
            )
        if len(self.signal_fingerprints) != len(set(self.signal_fingerprints)):
            raise DurablePhase20ForwardEvidenceError(
                "forward decision candidate fingerprints must be unique"
            )
        try:
            parsed = json.loads(self.canonical_payload_json)
        except json.JSONDecodeError as error:
            raise DurablePhase20ForwardEvidenceError(
                "forward decision canonical payload is invalid JSON"
            ) from error
        if not isinstance(parsed, dict):
            raise DurablePhase20ForwardEvidenceError(
                "forward decision canonical payload must be object"
            )


@dataclass(frozen=True, slots=True)
class Phase20ForwardOutcomeSeal:
    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    observed_at: datetime
    realized_structural_outcome_r: Decimal

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.signal_fingerprint:
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome identity is required"
            )
        if not self.decision_evidence_sha256.startswith("sha256:"):
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome decision SHA256 is required"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome timestamp must be timezone-aware"
            )
        if (
            not isinstance(self.realized_structural_outcome_r, Decimal)
            or not self.realized_structural_outcome_r.is_finite()
        ):
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome must be finite Decimal"
            )


@dataclass(frozen=True, slots=True)
class VersionedPhase20ForwardEvidenceBook:
    generation: int
    decisions: tuple[Phase20ForwardDecisionSeal, ...] = ()
    outcomes: tuple[Phase20ForwardOutcomeSeal, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurablePhase20ForwardEvidenceError(
                "forward evidence generation must be non-negative int"
            )
        decision_ids = tuple(item.evidence_id for item in self.decisions)
        decision_shas = tuple(item.evidence_sha256 for item in self.decisions)
        outcome_ids = tuple(item.evidence_id for item in self.outcomes)
        outcome_keys = tuple(
            (item.decision_evidence_sha256, item.signal_fingerprint)
            for item in self.outcomes
        )
        if len(decision_ids) != len(set(decision_ids)):
            raise DurablePhase20ForwardEvidenceError(
                "duplicate forward decision evidence_id"
            )
        if len(decision_shas) != len(set(decision_shas)):
            raise DurablePhase20ForwardEvidenceError(
                "duplicate forward decision SHA256"
            )
        if len(outcome_ids) != len(set(outcome_ids)):
            raise DurablePhase20ForwardEvidenceError(
                "duplicate forward outcome evidence_id"
            )
        if len(outcome_keys) != len(set(outcome_keys)):
            raise DurablePhase20ForwardEvidenceError(
                "duplicate forward outcome decision/signal"
            )

    def decision_for_sha(
        self,
        evidence_sha256: str,
    ) -> Phase20ForwardDecisionSeal | None:
        rows = tuple(
            item
            for item in self.decisions
            if item.evidence_sha256 == evidence_sha256
        )
        if len(rows) > 1:
            raise DurablePhase20ForwardEvidenceError(
                "duplicate forward decision SHA256"
            )
        return rows[0] if rows else None


class DurablePhase20ForwardEvidenceStore:
    """Atomic append-only forward-evidence store with CAS and writer lock."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise DurablePhase20ForwardEvidenceError(
                "forward evidence path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedPhase20ForwardEvidenceBook:
        with self._lock:
            return self._load_unlocked()

    def seal_decision(
        self,
        evidence: Phase20ForwardDecisionEvidence,
        *,
        expected_generation: int,
    ) -> VersionedPhase20ForwardEvidenceBook:
        if not isinstance(evidence, Phase20ForwardDecisionEvidence):
            raise DurablePhase20ForwardEvidenceError(
                "forward decision evidence must be canonical"
            )
        if evidence.evidence_kind is not Phase20ForwardEvidenceKind.FORWARD_OBSERVED:
            raise DurablePhase20ForwardEvidenceError(
                "forward collector accepts FORWARD_OBSERVED decisions only"
            )
        _generation(expected_generation)
        seal = _decision_seal(evidence)

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise DurablePhase20ForwardEvidenceError(
                        "stale forward evidence generation"
                    )
                same_id = tuple(
                    item
                    for item in current.decisions
                    if item.evidence_id == seal.evidence_id
                )
                if same_id:
                    if same_id[0] == seal:
                        return current
                    raise DurablePhase20ForwardEvidenceError(
                        "conflicting forward decision rewrite"
                    )
                if current.decision_for_sha(seal.evidence_sha256) is not None:
                    raise DurablePhase20ForwardEvidenceError(
                        "forward decision payload already sealed under another id"
                    )
                updated = VersionedPhase20ForwardEvidenceBook(
                    generation=current.generation + 1,
                    decisions=current.decisions + (seal,),
                    outcomes=current.outcomes,
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def append_outcome(
        self,
        outcome: Phase20ForwardOutcomeEvidence,
        *,
        expected_generation: int,
    ) -> VersionedPhase20ForwardEvidenceBook:
        if not isinstance(outcome, Phase20ForwardOutcomeEvidence):
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome evidence must be canonical"
            )
        _generation(expected_generation)

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise DurablePhase20ForwardEvidenceError(
                        "stale forward evidence generation"
                    )
                decision = current.decision_for_sha(
                    outcome.decision_evidence_sha256
                )
                if decision is None:
                    raise DurablePhase20ForwardEvidenceError(
                        "forward outcome has no sealed decision"
                    )
                if outcome.observed_at <= decision.decision_at:
                    raise DurablePhase20ForwardEvidenceError(
                        "forward outcome must be strictly after decision"
                    )
                if outcome.signal_fingerprint not in decision.signal_fingerprints:
                    raise DurablePhase20ForwardEvidenceError(
                        "forward outcome signal was not sealed pre-decision"
                    )
                if not outcome.outcome_reconciled:
                    raise DurablePhase20ForwardEvidenceError(
                        "forward outcome must be reconciled"
                    )
                seal = Phase20ForwardOutcomeSeal(
                    evidence_id=outcome.evidence_id,
                    decision_evidence_sha256=outcome.decision_evidence_sha256,
                    signal_fingerprint=outcome.signal_fingerprint,
                    observed_at=outcome.observed_at,
                    realized_structural_outcome_r=(
                        outcome.realized_structural_outcome_r
                    ),
                )
                same_id = tuple(
                    item
                    for item in current.outcomes
                    if item.evidence_id == seal.evidence_id
                )
                if same_id:
                    if same_id[0] == seal:
                        return current
                    raise DurablePhase20ForwardEvidenceError(
                        "conflicting forward outcome rewrite"
                    )
                same_key = tuple(
                    item
                    for item in current.outcomes
                    if (
                        item.decision_evidence_sha256
                        == seal.decision_evidence_sha256
                        and item.signal_fingerprint
                        == seal.signal_fingerprint
                    )
                )
                if same_key:
                    raise DurablePhase20ForwardEvidenceError(
                        "forward outcome already sealed for decision/signal"
                    )
                updated = VersionedPhase20ForwardEvidenceBook(
                    generation=current.generation + 1,
                    decisions=current.decisions,
                    outcomes=current.outcomes + (seal,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedPhase20ForwardEvidenceBook:
        if not self._path.exists():
            return VersionedPhase20ForwardEvidenceBook(generation=0)
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurablePhase20ForwardEvidenceError(
                "durable forward evidence store is unreadable"
            ) from error
        if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
            raise DurablePhase20ForwardEvidenceError(
                "durable forward evidence schema mismatch"
            )
        try:
            generation = int(str(raw["generation"]))
            decisions_raw = raw["decisions"]
            outcomes_raw = raw["outcomes"]
            if not isinstance(decisions_raw, list) or not isinstance(
                outcomes_raw,
                list,
            ):
                raise TypeError("forward decisions/outcomes must be lists")
            return VersionedPhase20ForwardEvidenceBook(
                generation=generation,
                decisions=tuple(
                    _decision_from_json(item) for item in decisions_raw
                ),
                outcomes=tuple(
                    _outcome_from_json(item) for item in outcomes_raw
                ),
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidOperation,
        ) as error:
            raise DurablePhase20ForwardEvidenceError(
                "durable forward evidence payload invalid"
            ) from error

    def _write_unlocked(
        self,
        book: VersionedPhase20ForwardEvidenceBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "decisions": [_decision_to_json(item) for item in book.decisions],
            "outcomes": [_outcome_to_json(item) for item in book.outcomes],
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
            raise DurablePhase20ForwardEvidenceError(
                "durable forward evidence write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurablePhase20ForwardEvidenceError(
                "forward evidence writer lock already held"
            ) from error
        except OSError as error:
            raise DurablePhase20ForwardEvidenceError(
                "forward evidence writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurablePhase20ForwardEvidenceError(
                "forward evidence writer lock release failed"
            ) from error


def _decision_seal(
    evidence: Phase20ForwardDecisionEvidence,
) -> Phase20ForwardDecisionSeal:
    payload = phase20_forward_evidence_json(evidence)
    return Phase20ForwardDecisionSeal(
        evidence_id=evidence.evidence_id,
        evidence_sha256=phase20_forward_evidence_sha256(evidence),
        decision_at=evidence.decision_at,
        candidate_id=evidence.lineage.candidate_id,
        code_sha=evidence.lineage.code_sha,
        parameter_sha256=evidence.lineage.parameter_sha256,
        signal_fingerprints=tuple(
            item.candidate.signal_fingerprint for item in evidence.candidates
        ),
        canonical_payload_json=payload,
    )


def _generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise DurablePhase20ForwardEvidenceError(
            "expected_generation must be non-negative int"
        )


def _decision_to_json(
    value: Phase20ForwardDecisionSeal,
) -> dict[str, object]:
    return {
        "evidence_id": value.evidence_id,
        "evidence_sha256": value.evidence_sha256,
        "decision_at": value.decision_at.isoformat(),
        "candidate_id": value.candidate_id,
        "code_sha": value.code_sha,
        "parameter_sha256": value.parameter_sha256,
        "signal_fingerprints": list(value.signal_fingerprints),
        "canonical_payload_json": value.canonical_payload_json,
    }


def _decision_from_json(value: object) -> Phase20ForwardDecisionSeal:
    if not isinstance(value, dict):
        raise TypeError("forward decision row must be object")
    fingerprints = value["signal_fingerprints"]
    if not isinstance(fingerprints, list):
        raise TypeError("forward signal_fingerprints must be list")
    return Phase20ForwardDecisionSeal(
        evidence_id=str(value["evidence_id"]),
        evidence_sha256=str(value["evidence_sha256"]),
        decision_at=datetime.fromisoformat(str(value["decision_at"])),
        candidate_id=str(value["candidate_id"]),
        code_sha=str(value["code_sha"]),
        parameter_sha256=str(value["parameter_sha256"]),
        signal_fingerprints=tuple(str(item) for item in fingerprints),
        canonical_payload_json=str(value["canonical_payload_json"]),
    )


def _outcome_to_json(
    value: Phase20ForwardOutcomeSeal,
) -> dict[str, object]:
    return {
        "evidence_id": value.evidence_id,
        "decision_evidence_sha256": value.decision_evidence_sha256,
        "signal_fingerprint": value.signal_fingerprint,
        "observed_at": value.observed_at.isoformat(),
        "realized_structural_outcome_r": format(
            value.realized_structural_outcome_r,
            "f",
        ),
    }


def _outcome_from_json(value: object) -> Phase20ForwardOutcomeSeal:
    if not isinstance(value, dict):
        raise TypeError("forward outcome row must be object")
    return Phase20ForwardOutcomeSeal(
        evidence_id=str(value["evidence_id"]),
        decision_evidence_sha256=str(value["decision_evidence_sha256"]),
        signal_fingerprint=str(value["signal_fingerprint"]),
        observed_at=datetime.fromisoformat(str(value["observed_at"])),
        realized_structural_outcome_r=Decimal(
            str(value["realized_structural_outcome_r"])
        ),
    )
