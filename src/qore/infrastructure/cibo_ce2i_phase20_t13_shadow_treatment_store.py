"""Append-only pre-outcome ledger for CE2I T13 shadow treatment.

A treatment selection may be sealed only after both prerequisite decisions are
already durable: the official Phase20D baseline policy seal and the T13 reserve
recommendation seal for the same forward evidence. The treatment must still be
sealed within two seconds of the decision epoch and before any same-epoch
outcome exists.

Research-only. No sizing, QORE Risk, execution, DEMO, LIVE or real-capital
authority is granted.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_store import (
    VersionedT13ShadowDecisionBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment import (
    Phase20T13ShadowTreatmentDecision,
)

_SCHEMA = "CIBO_PHASE20_T13_SHADOW_TREATMENT_LEDGER_V1"
_GENESIS = "sha256:" + ("0" * 64)
_MAX_SEAL_LATENCY = timedelta(seconds=2)


class DurableT13ShadowTreatmentError(CiboCapitalManagementError):
    """T13 treatment evidence is stale, conflicting or corrupt."""


@dataclass(frozen=True, slots=True)
class T13ShadowTreatmentSeal:
    treatment_sha256: str
    recommendation_sha256: str
    decision_epoch_id: str
    decision_evidence_sha256: str
    baseline_policy_record_sha256: str
    t13_policy_sha256: str
    decision_at: datetime
    treatment_sealed_at: datetime
    reserve_triggered: bool
    shadow_reserved_risk_usd: Decimal
    baseline_allocator_input_stop_risk_usd: Decimal
    treatment_allocator_input_stop_risk_usd: Decimal
    allocator_input_margin_usd: Decimal
    baseline_selected_signal_fingerprints: tuple[str, ...]
    treatment_selected_signal_fingerprints: tuple[str, ...]
    baseline_only_signal_fingerprints: tuple[str, ...]
    treatment_only_signal_fingerprints: tuple[str, ...]
    selection_changed: bool

    def __post_init__(self) -> None:
        for name in (
            "treatment_sha256",
            "recommendation_sha256",
            "decision_evidence_sha256",
            "baseline_policy_record_sha256",
            "t13_policy_sha256",
        ):
            if not _valid_sha(getattr(self, name)):
                raise DurableT13ShadowTreatmentError(
                    f"T13 treatment {name} must be canonical SHA-256"
                )
        if not self.decision_epoch_id:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment epoch id is required"
            )
        _aware(self.decision_at, "decision_at")
        _aware(self.treatment_sealed_at, "treatment_sealed_at")
        if self.treatment_sealed_at < self.decision_at:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment seal cannot predate decision"
            )
        if (
            self.treatment_sealed_at - self.decision_at
            > _MAX_SEAL_LATENCY
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment seal exceeds frozen two-second window"
            )
        for name in (
            "shadow_reserved_risk_usd",
            "baseline_allocator_input_stop_risk_usd",
            "treatment_allocator_input_stop_risk_usd",
            "allocator_input_margin_usd",
        ):
            _non_negative(getattr(self, name), name)
        expected = max(
            Decimal(0),
            self.baseline_allocator_input_stop_risk_usd
            - self.shadow_reserved_risk_usd,
        )
        if self.treatment_allocator_input_stop_risk_usd != expected:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment sealed risk accounting drift"
            )
        for name in ("reserve_triggered", "selection_changed"):
            if type(getattr(self, name)) is not bool:
                raise DurableT13ShadowTreatmentError(
                    f"T13 treatment {name} must be bool"
                )
        baseline = set(self.baseline_selected_signal_fingerprints)
        treatment = set(self.treatment_selected_signal_fingerprints)
        if len(baseline) != len(self.baseline_selected_signal_fingerprints):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment baseline signals must be unique"
            )
        if len(treatment) != len(self.treatment_selected_signal_fingerprints):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment signals must be unique"
            )
        if set(self.baseline_only_signal_fingerprints) != baseline - treatment:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment baseline-only accounting drift"
            )
        if set(self.treatment_only_signal_fingerprints) != treatment - baseline:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment treatment-only accounting drift"
            )
        if self.selection_changed != (baseline != treatment):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment selection-change flag drift"
            )


@dataclass(frozen=True, slots=True)
class T13ShadowTreatmentLedgerRecord:
    sequence: int
    decision_epoch_id: str
    payload_json: str
    payload_sha256: str
    previous_chain_sha256: str
    chain_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sequence, int)
            or isinstance(self.sequence, bool)
            or self.sequence < 1
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment ledger sequence must be positive int"
            )
        if not self.decision_epoch_id:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment ledger epoch id is required"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            if not _valid_sha(getattr(self, name)):
                raise DurableT13ShadowTreatmentError(
                    f"T13 treatment ledger {name} invalid"
                )
        expected_payload = "sha256:" + hashlib.sha256(
            self.payload_json.encode()
        ).hexdigest()
        if self.payload_sha256 != expected_payload:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment ledger payload SHA mismatch"
            )
        expected_chain = _next_chain(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            epoch_id=self.decision_epoch_id,
            payload_sha256=self.payload_sha256,
        )
        if self.chain_sha256 != expected_chain:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment ledger chain SHA mismatch"
            )
        seal = _seal_from_json(self.payload_json)
        if seal.decision_epoch_id != self.decision_epoch_id:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment ledger epoch binding mismatch"
            )


@dataclass(frozen=True, slots=True)
class VersionedT13ShadowTreatmentBook:
    generation: int
    records: tuple[T13ShadowTreatmentLedgerRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment generation/record count drift"
            )
        previous = _GENESIS
        epochs: set[str] = set()
        evidences: set[str] = set()
        for sequence, record in enumerate(self.records, start=1):
            if record.sequence != sequence:
                raise DurableT13ShadowTreatmentError(
                    "T13 treatment ledger sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise DurableT13ShadowTreatmentError(
                    "T13 treatment previous chain mismatch"
                )
            seal = _seal_from_json(record.payload_json)
            if seal.decision_epoch_id in epochs:
                raise DurableT13ShadowTreatmentError(
                    "T13 treatment duplicate epoch"
                )
            if seal.decision_evidence_sha256 in evidences:
                raise DurableT13ShadowTreatmentError(
                    "T13 treatment duplicate evidence"
                )
            epochs.add(seal.decision_epoch_id)
            evidences.add(seal.decision_evidence_sha256)
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    @property
    def decisions(self) -> tuple[T13ShadowTreatmentSeal, ...]:
        return tuple(_seal_from_json(item.payload_json) for item in self.records)

    def decision_for_evidence(
        self,
        decision_evidence_sha256: str,
    ) -> T13ShadowTreatmentSeal | None:
        matches = tuple(
            item
            for item in self.decisions
            if item.decision_evidence_sha256 == decision_evidence_sha256
        )
        if len(matches) > 1:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment duplicate evidence binding"
            )
        return matches[0] if matches else None


class DurableT13ShadowTreatmentStore:
    """Atomic CAS store for pre-outcome T13 treatment selections."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(path, Path):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment path must be pathlib.Path"
            )
        self._path = path
        self._clock = clock or (lambda: datetime.now(UTC))
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedT13ShadowTreatmentBook:
        with self._lock:
            return self._load_unlocked()

    def seal_treatment(
        self,
        treatment: Phase20T13ShadowTreatmentDecision,
        *,
        evidence_book: VersionedPhase20ForwardEvidenceBook,
        baseline_policy_book: VersionedPhase20ForwardPolicyBook,
        recommendation_book: VersionedT13ShadowDecisionBook,
        expected_generation: int,
    ) -> VersionedT13ShadowTreatmentBook:
        if not isinstance(
            treatment,
            Phase20T13ShadowTreatmentDecision,
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment store requires canonical treatment"
            )
        if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment store requires canonical evidence book"
            )
        if not isinstance(
            baseline_policy_book,
            VersionedPhase20ForwardPolicyBook,
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment store requires canonical policy book"
            )
        if not isinstance(
            recommendation_book,
            VersionedT13ShadowDecisionBook,
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment store requires recommendation book"
            )
        _expected_generation(expected_generation)

        decision = evidence_book.decision_for_sha(
            treatment.decision_evidence_sha256
        )
        if decision is None:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment has no sealed forward evidence"
            )
        if (
            decision.decision_epoch_id != treatment.decision_epoch_id
            or decision.decision_at
            != _decision_at_from_treatment(treatment, decision.decision_at)
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment forward decision binding drift"
            )
        if any(
            outcome.decision_evidence_sha256
            == treatment.decision_evidence_sha256
            for outcome in evidence_book.outcomes
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment cannot seal after outcome exists"
            )
        baseline = baseline_policy_book.decision_for_evidence(
            treatment.decision_evidence_sha256
        )
        if baseline is None:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment requires prior baseline policy seal"
            )
        if (
            baseline.policy_record_sha256
            != treatment.baseline_policy_record_sha256
            or baseline.selected_signal_fingerprints
            != treatment.baseline_selected_signal_fingerprints
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment baseline policy binding drift"
            )
        recommendation = recommendation_book.decision_for_evidence(
            treatment.decision_evidence_sha256
        )
        if recommendation is None:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment requires prior recommendation seal"
            )
        if (
            recommendation.decision_epoch_id != treatment.decision_epoch_id
            or recommendation.policy_sha256 != treatment.t13_policy_sha256
            or recommendation.reserve_triggered
            != treatment.reserve_triggered
            or recommendation.reserved_risk_usd
            != treatment.shadow_reserved_risk_usd
        ):
            raise DurableT13ShadowTreatmentError(
                "T13 treatment recommendation binding drift"
            )

        treatment_sha = _treatment_sha256(treatment)
        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise DurableT13ShadowTreatmentError(
                        "T13 treatment generation conflict"
                    )
                prior = current.decision_for_evidence(
                    treatment.decision_evidence_sha256
                )
                if prior is not None:
                    if prior.treatment_sha256 == treatment_sha:
                        return current
                    raise DurableT13ShadowTreatmentError(
                        "T13 treatment conflicting evidence rewrite"
                    )

                sealed_at = self._clock()
                _aware(sealed_at, "store clock")
                if sealed_at < recommendation.shadow_sealed_at:
                    raise DurableT13ShadowTreatmentError(
                        "T13 treatment cannot predate recommendation seal"
                    )
                seal = T13ShadowTreatmentSeal(
                    treatment_sha256=treatment_sha,
                    recommendation_sha256=(
                        recommendation.recommendation_sha256
                    ),
                    decision_epoch_id=treatment.decision_epoch_id,
                    decision_evidence_sha256=(
                        treatment.decision_evidence_sha256
                    ),
                    baseline_policy_record_sha256=(
                        treatment.baseline_policy_record_sha256
                    ),
                    t13_policy_sha256=treatment.t13_policy_sha256,
                    decision_at=decision.decision_at,
                    treatment_sealed_at=sealed_at,
                    reserve_triggered=treatment.reserve_triggered,
                    shadow_reserved_risk_usd=(
                        treatment.shadow_reserved_risk_usd
                    ),
                    baseline_allocator_input_stop_risk_usd=(
                        treatment.baseline_allocator_input_stop_risk_usd
                    ),
                    treatment_allocator_input_stop_risk_usd=(
                        treatment.treatment_allocator_input_stop_risk_usd
                    ),
                    allocator_input_margin_usd=(
                        treatment.allocator_input_margin_usd
                    ),
                    baseline_selected_signal_fingerprints=(
                        treatment.baseline_selected_signal_fingerprints
                    ),
                    treatment_selected_signal_fingerprints=(
                        treatment.treatment_selected_signal_fingerprints
                    ),
                    baseline_only_signal_fingerprints=(
                        treatment.baseline_only_signal_fingerprints
                    ),
                    treatment_only_signal_fingerprints=(
                        treatment.treatment_only_signal_fingerprints
                    ),
                    selection_changed=treatment.selection_changed,
                )
                record = _record(
                    sequence=current.generation + 1,
                    seal=seal,
                    previous=current.chain_sha256,
                )
                updated = VersionedT13ShadowTreatmentBook(
                    generation=current.generation + 1,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedT13ShadowTreatmentBook:
        if not self._path.exists():
            return VersionedT13ShadowTreatmentBook(generation=0)
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment store is unreadable"
            ) from error
        return _book_from_payload(payload)

    def _write_unlocked(
        self,
        book: VersionedT13ShadowTreatmentBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "chain_sha256": book.chain_sha256,
            "records": [
                {
                    "sequence": item.sequence,
                    "decision_epoch_id": item.decision_epoch_id,
                    "payload_json": item.payload_json,
                    "payload_sha256": item.payload_sha256,
                    "previous_chain_sha256": item.previous_chain_sha256,
                    "chain_sha256": item.chain_sha256,
                }
                for item in book.records
            ],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with temp.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        payload,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self._path)
        except OSError as error:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment store write failed"
            ) from error
        finally:
            temp.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment writer lock already held"
            ) from error
        except OSError as error:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurableT13ShadowTreatmentError(
                "T13 treatment writer lock release failed"
            ) from error


def _treatment_sha256(
    treatment: Phase20T13ShadowTreatmentDecision,
) -> str:
    payload = {
        "decision_epoch_id": treatment.decision_epoch_id,
        "decision_evidence_sha256": treatment.decision_evidence_sha256,
        "baseline_policy_record_sha256": (
            treatment.baseline_policy_record_sha256
        ),
        "t13_policy_sha256": treatment.t13_policy_sha256,
        "reserve_triggered": treatment.reserve_triggered,
        "shadow_reserved_risk_usd": str(
            treatment.shadow_reserved_risk_usd
        ),
        "baseline_allocator_input_stop_risk_usd": str(
            treatment.baseline_allocator_input_stop_risk_usd
        ),
        "treatment_allocator_input_stop_risk_usd": str(
            treatment.treatment_allocator_input_stop_risk_usd
        ),
        "allocator_input_margin_usd": str(
            treatment.allocator_input_margin_usd
        ),
        "baseline_selected_signal_fingerprints": list(
            treatment.baseline_selected_signal_fingerprints
        ),
        "treatment_selected_signal_fingerprints": list(
            treatment.treatment_selected_signal_fingerprints
        ),
        "baseline_only_signal_fingerprints": list(
            treatment.baseline_only_signal_fingerprints
        ),
        "treatment_only_signal_fingerprints": list(
            treatment.treatment_only_signal_fingerprints
        ),
        "selection_changed": treatment.selection_changed,
        "treatment_allocator_disposition": (
            treatment.treatment_allocator.disposition.value
        ),
        "treatment_allocator_applied_tools": list(
            treatment.treatment_allocator.applied_tools
        ),
        "treatment_allocator_deployable_stop_risk_usd": str(
            treatment.treatment_allocator.deployable_stop_risk_usd
        ),
        "treatment_allocator_deployable_margin_usd": str(
            treatment.treatment_allocator.deployable_margin_usd
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _seal_payload(seal: T13ShadowTreatmentSeal) -> dict[str, object]:
    return {
        "treatment_sha256": seal.treatment_sha256,
        "recommendation_sha256": seal.recommendation_sha256,
        "decision_epoch_id": seal.decision_epoch_id,
        "decision_evidence_sha256": seal.decision_evidence_sha256,
        "baseline_policy_record_sha256": (
            seal.baseline_policy_record_sha256
        ),
        "t13_policy_sha256": seal.t13_policy_sha256,
        "decision_at": seal.decision_at.isoformat(),
        "treatment_sealed_at": seal.treatment_sealed_at.isoformat(),
        "reserve_triggered": seal.reserve_triggered,
        "shadow_reserved_risk_usd": str(seal.shadow_reserved_risk_usd),
        "baseline_allocator_input_stop_risk_usd": str(
            seal.baseline_allocator_input_stop_risk_usd
        ),
        "treatment_allocator_input_stop_risk_usd": str(
            seal.treatment_allocator_input_stop_risk_usd
        ),
        "allocator_input_margin_usd": str(seal.allocator_input_margin_usd),
        "baseline_selected_signal_fingerprints": list(
            seal.baseline_selected_signal_fingerprints
        ),
        "treatment_selected_signal_fingerprints": list(
            seal.treatment_selected_signal_fingerprints
        ),
        "baseline_only_signal_fingerprints": list(
            seal.baseline_only_signal_fingerprints
        ),
        "treatment_only_signal_fingerprints": list(
            seal.treatment_only_signal_fingerprints
        ),
        "selection_changed": seal.selection_changed,
    }


def _seal_from_json(value: str) -> T13ShadowTreatmentSeal:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise DurableT13ShadowTreatmentError(
            "T13 treatment seal JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise DurableT13ShadowTreatmentError(
            "T13 treatment seal payload must be object"
        )
    try:
        baseline = _strings(
            payload["baseline_selected_signal_fingerprints"]
        )
        treatment = _strings(
            payload["treatment_selected_signal_fingerprints"]
        )
        baseline_only = _strings(
            payload["baseline_only_signal_fingerprints"]
        )
        treatment_only = _strings(
            payload["treatment_only_signal_fingerprints"]
        )
        return T13ShadowTreatmentSeal(
            treatment_sha256=str(payload["treatment_sha256"]),
            recommendation_sha256=str(payload["recommendation_sha256"]),
            decision_epoch_id=str(payload["decision_epoch_id"]),
            decision_evidence_sha256=str(
                payload["decision_evidence_sha256"]
            ),
            baseline_policy_record_sha256=str(
                payload["baseline_policy_record_sha256"]
            ),
            t13_policy_sha256=str(payload["t13_policy_sha256"]),
            decision_at=datetime.fromisoformat(str(payload["decision_at"])),
            treatment_sealed_at=datetime.fromisoformat(
                str(payload["treatment_sealed_at"])
            ),
            reserve_triggered=_bool(
                payload["reserve_triggered"],
                "reserve_triggered",
            ),
            shadow_reserved_risk_usd=_decimal(
                payload["shadow_reserved_risk_usd"]
            ),
            baseline_allocator_input_stop_risk_usd=_decimal(
                payload["baseline_allocator_input_stop_risk_usd"]
            ),
            treatment_allocator_input_stop_risk_usd=_decimal(
                payload["treatment_allocator_input_stop_risk_usd"]
            ),
            allocator_input_margin_usd=_decimal(
                payload["allocator_input_margin_usd"]
            ),
            baseline_selected_signal_fingerprints=baseline,
            treatment_selected_signal_fingerprints=treatment,
            baseline_only_signal_fingerprints=baseline_only,
            treatment_only_signal_fingerprints=treatment_only,
            selection_changed=_bool(
                payload["selection_changed"],
                "selection_changed",
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DurableT13ShadowTreatmentError(
            "T13 treatment seal payload invalid"
        ) from error


def _record(
    *,
    sequence: int,
    seal: T13ShadowTreatmentSeal,
    previous: str,
) -> T13ShadowTreatmentLedgerRecord:
    payload_json = json.dumps(
        _seal_payload(seal),
        sort_keys=True,
        separators=(",", ":"),
    )
    payload_sha = "sha256:" + hashlib.sha256(
        payload_json.encode()
    ).hexdigest()
    return T13ShadowTreatmentLedgerRecord(
        sequence=sequence,
        decision_epoch_id=seal.decision_epoch_id,
        payload_json=payload_json,
        payload_sha256=payload_sha,
        previous_chain_sha256=previous,
        chain_sha256=_next_chain(
            previous=previous,
            sequence=sequence,
            epoch_id=seal.decision_epoch_id,
            payload_sha256=payload_sha,
        ),
    )


def _next_chain(
    *,
    previous: str,
    sequence: int,
    epoch_id: str,
    payload_sha256: str,
) -> str:
    raw = f"{previous}|{sequence}|{epoch_id}|{payload_sha256}".encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _book_from_payload(
    payload: object,
) -> VersionedT13ShadowTreatmentBook:
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        raise DurableT13ShadowTreatmentError(
            "T13 treatment store schema mismatch"
        )
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise DurableT13ShadowTreatmentError(
            "T13 treatment records must be list"
        )
    try:
        records = tuple(
            T13ShadowTreatmentLedgerRecord(
                sequence=int(row["sequence"]),
                decision_epoch_id=str(row["decision_epoch_id"]),
                payload_json=str(row["payload_json"]),
                payload_sha256=str(row["payload_sha256"]),
                previous_chain_sha256=str(
                    row["previous_chain_sha256"]
                ),
                chain_sha256=str(row["chain_sha256"]),
            )
            for row in rows
            if isinstance(row, dict)
        )
        if len(records) != len(rows):
            raise TypeError("T13 treatment record must be object")
        generation = int(payload["generation"])
    except (KeyError, TypeError, ValueError) as error:
        raise DurableT13ShadowTreatmentError(
            "T13 treatment store payload invalid"
        ) from error
    book = VersionedT13ShadowTreatmentBook(
        generation=generation,
        records=records,
    )
    if payload.get("chain_sha256") != book.chain_sha256:
        raise DurableT13ShadowTreatmentError(
            "T13 treatment terminal chain mismatch"
        )
    return book


def _decision_at_from_treatment(
    treatment: Phase20T13ShadowTreatmentDecision,
    decision_at: datetime,
) -> datetime:
    if not treatment.decision_epoch_id:
        raise DurableT13ShadowTreatmentError(
            "T13 treatment epoch id missing"
        )
    return decision_at


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError("T13 treatment signal list must be list")
    return tuple(str(item) for item in value)


def _valid_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def _expected_generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise DurableT13ShadowTreatmentError(
            "T13 treatment expected generation must be non-negative int"
        )


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise DurableT13ShadowTreatmentError(
            "T13 treatment decimal field invalid"
        ) from error
    if not result.is_finite():
        raise DurableT13ShadowTreatmentError(
            "T13 treatment decimal field must be finite"
        )
    return result


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise DurableT13ShadowTreatmentError(
            f"T13 treatment {name} must be bool"
        )
    return value


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise DurableT13ShadowTreatmentError(
            f"T13 treatment {name} must be timezone-aware"
        )


def _non_negative(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise DurableT13ShadowTreatmentError(
            f"T13 treatment {name} must be finite non-negative"
        )
