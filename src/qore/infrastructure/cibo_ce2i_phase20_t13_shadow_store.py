"""Append-only pre-outcome decision ledger for CE2I T13 shadow reserve.

Only preregistered T13 recommendations may be sealed. The physical seal must
occur within two seconds of the decision epoch, must bind the exact forward
evidence SHA and is rejected if any outcome for that epoch already exists.
The ledger is research-only and has no sizing, Risk or broker authority.
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
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    Phase20T13ShadowRecommendation,
    t13_shadow_policy_sha256,
)

_SCHEMA = "CIBO_PHASE20_T13_SHADOW_DECISION_LEDGER_V1"
_GENESIS = "sha256:" + ("0" * 64)
_MAX_SEAL_LATENCY = timedelta(seconds=2)


class DurableT13ShadowDecisionError(CiboCapitalManagementError):
    """T13 shadow decision evidence is stale, conflicting or corrupt."""


@dataclass(frozen=True, slots=True)
class T13ShadowDecisionSeal:
    recommendation_sha256: str
    policy_sha256: str
    decision_epoch_id: str
    decision_evidence_sha256: str
    decision_at: datetime
    shadow_sealed_at: datetime
    reserve_triggered: bool
    reserved_risk_usd: Decimal
    minimum_seed_risk_usd: Decimal | None
    hard_risk_headroom_usd: Decimal
    full_seed_preserved: bool
    source_decision_sha256s: tuple[str, ...]
    source_outcome_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "recommendation_sha256",
            "policy_sha256",
            "decision_evidence_sha256",
        ):
            if not _valid_sha(getattr(self, name)):
                raise DurableT13ShadowDecisionError(
                    f"T13 shadow {name} must be canonical SHA-256"
                )
        if self.policy_sha256 != t13_shadow_policy_sha256():
            raise DurableT13ShadowDecisionError(
                "T13 shadow policy digest drift"
            )
        if not self.decision_epoch_id:
            raise DurableT13ShadowDecisionError(
                "T13 shadow decision epoch id is required"
            )
        _aware(self.decision_at, "decision_at")
        _aware(self.shadow_sealed_at, "shadow_sealed_at")
        if self.shadow_sealed_at < self.decision_at:
            raise DurableT13ShadowDecisionError(
                "T13 shadow seal cannot predate decision"
            )
        if self.shadow_sealed_at - self.decision_at > _MAX_SEAL_LATENCY:
            raise DurableT13ShadowDecisionError(
                "T13 shadow seal exceeds frozen two-second window"
            )
        if type(self.reserve_triggered) is not bool:
            raise DurableT13ShadowDecisionError(
                "T13 shadow reserve_triggered must be bool"
            )
        if type(self.full_seed_preserved) is not bool:
            raise DurableT13ShadowDecisionError(
                "T13 shadow full_seed_preserved must be bool"
            )
        _non_negative(self.reserved_risk_usd, "reserved_risk_usd")
        _non_negative(self.hard_risk_headroom_usd, "hard_risk_headroom_usd")
        if self.minimum_seed_risk_usd is not None:
            _positive(self.minimum_seed_risk_usd, "minimum_seed_risk_usd")
        if self.reserve_triggered:
            if self.minimum_seed_risk_usd is None:
                raise DurableT13ShadowDecisionError(
                    "T13 shadow triggered reserve requires minimum seed"
                )
            expected = min(
                self.hard_risk_headroom_usd,
                self.minimum_seed_risk_usd,
            )
            if self.reserved_risk_usd != expected or expected <= 0:
                raise DurableT13ShadowDecisionError(
                    "T13 shadow reserve amount drift"
                )
            if self.full_seed_preserved != (
                self.hard_risk_headroom_usd
                >= self.minimum_seed_risk_usd
            ):
                raise DurableT13ShadowDecisionError(
                    "T13 shadow full seed flag drift"
                )
        elif self.reserved_risk_usd != 0 or self.full_seed_preserved:
            raise DurableT13ShadowDecisionError(
                "T13 shadow inactive reserve must be zero"
            )
        for values, label in (
            (self.source_decision_sha256s, "decision sources"),
            (self.source_outcome_evidence_ids, "outcome sources"),
        ):
            if len(values) != len(set(values)) or any(not item for item in values):
                raise DurableT13ShadowDecisionError(
                    f"T13 shadow {label} must be unique/non-empty"
                )


@dataclass(frozen=True, slots=True)
class T13ShadowLedgerRecord:
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
            raise DurableT13ShadowDecisionError(
                "T13 shadow ledger sequence must be positive int"
            )
        if not self.decision_epoch_id:
            raise DurableT13ShadowDecisionError(
                "T13 shadow ledger epoch id is required"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            if not _valid_sha(getattr(self, name)):
                raise DurableT13ShadowDecisionError(
                    f"T13 shadow ledger {name} invalid"
                )
        expected_payload = "sha256:" + hashlib.sha256(
            self.payload_json.encode()
        ).hexdigest()
        if self.payload_sha256 != expected_payload:
            raise DurableT13ShadowDecisionError(
                "T13 shadow ledger payload SHA mismatch"
            )
        expected_chain = _next_chain(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            epoch_id=self.decision_epoch_id,
            payload_sha256=self.payload_sha256,
        )
        if self.chain_sha256 != expected_chain:
            raise DurableT13ShadowDecisionError(
                "T13 shadow ledger chain SHA mismatch"
            )
        seal = _seal_from_json(self.payload_json)
        if seal.decision_epoch_id != self.decision_epoch_id:
            raise DurableT13ShadowDecisionError(
                "T13 shadow ledger epoch binding mismatch"
            )


@dataclass(frozen=True, slots=True)
class VersionedT13ShadowDecisionBook:
    generation: int
    records: tuple[T13ShadowLedgerRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurableT13ShadowDecisionError(
                "T13 shadow generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise DurableT13ShadowDecisionError(
                "T13 shadow generation/record count drift"
            )
        previous = _GENESIS
        epochs: set[str] = set()
        evidences: set[str] = set()
        for sequence, record in enumerate(self.records, start=1):
            if record.sequence != sequence:
                raise DurableT13ShadowDecisionError(
                    "T13 shadow ledger sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise DurableT13ShadowDecisionError(
                    "T13 shadow ledger previous chain mismatch"
                )
            seal = _seal_from_json(record.payload_json)
            if seal.decision_epoch_id in epochs:
                raise DurableT13ShadowDecisionError(
                    "T13 shadow duplicate decision epoch"
                )
            if seal.decision_evidence_sha256 in evidences:
                raise DurableT13ShadowDecisionError(
                    "T13 shadow duplicate decision evidence"
                )
            epochs.add(seal.decision_epoch_id)
            evidences.add(seal.decision_evidence_sha256)
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    @property
    def decisions(self) -> tuple[T13ShadowDecisionSeal, ...]:
        return tuple(_seal_from_json(item.payload_json) for item in self.records)

    def decision_for_evidence(
        self,
        decision_evidence_sha256: str,
    ) -> T13ShadowDecisionSeal | None:
        matches = tuple(
            item
            for item in self.decisions
            if item.decision_evidence_sha256 == decision_evidence_sha256
        )
        if len(matches) > 1:
            raise DurableT13ShadowDecisionError(
                "T13 shadow duplicate evidence binding"
            )
        return matches[0] if matches else None


class DurableT13ShadowDecisionStore:
    """Atomic CAS store for T13 preregistered shadow decisions."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(path, Path):
            raise DurableT13ShadowDecisionError(
                "T13 shadow store path must be pathlib.Path"
            )
        self._path = path
        self._clock = clock or (lambda: datetime.now(UTC))
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedT13ShadowDecisionBook:
        with self._lock:
            return self._load_unlocked()

    def seal_recommendation(
        self,
        recommendation: Phase20T13ShadowRecommendation,
        *,
        evidence_book: VersionedPhase20ForwardEvidenceBook,
        expected_generation: int,
    ) -> VersionedT13ShadowDecisionBook:
        if not isinstance(
            recommendation,
            Phase20T13ShadowRecommendation,
        ):
            raise DurableT13ShadowDecisionError(
                "T13 shadow store requires canonical recommendation"
            )
        if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
            raise DurableT13ShadowDecisionError(
                "T13 shadow store requires canonical evidence book"
            )
        _expected_generation(expected_generation)
        decision = evidence_book.decision_for_sha(
            recommendation.decision_evidence_sha256
        )
        if decision is None:
            raise DurableT13ShadowDecisionError(
                "T13 shadow recommendation has no sealed forward decision"
            )
        if (
            decision.decision_epoch_id != recommendation.decision_epoch_id
            or decision.decision_at != recommendation.decision_at
        ):
            raise DurableT13ShadowDecisionError(
                "T13 shadow recommendation decision binding drift"
            )
        if any(
            outcome.decision_evidence_sha256
            == recommendation.decision_evidence_sha256
            for outcome in evidence_book.outcomes
        ):
            raise DurableT13ShadowDecisionError(
                "T13 shadow recommendation cannot seal after outcome exists"
            )

        recommendation_sha = _recommendation_sha256(recommendation)
        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise DurableT13ShadowDecisionError(
                        "T13 shadow generation conflict"
                    )
                previous = current.decision_for_evidence(
                    recommendation.decision_evidence_sha256
                )
                if previous is not None:
                    if previous.recommendation_sha256 == recommendation_sha:
                        return current
                    raise DurableT13ShadowDecisionError(
                        "T13 shadow conflicting decision evidence"
                    )

                sealed_at = self._clock()
                _aware(sealed_at, "store clock")
                seal = T13ShadowDecisionSeal(
                    recommendation_sha256=recommendation_sha,
                    policy_sha256=recommendation.policy_sha256,
                    decision_epoch_id=recommendation.decision_epoch_id,
                    decision_evidence_sha256=(
                        recommendation.decision_evidence_sha256
                    ),
                    decision_at=recommendation.decision_at,
                    shadow_sealed_at=sealed_at,
                    reserve_triggered=recommendation.reserve_triggered,
                    reserved_risk_usd=recommendation.reserved_risk_usd,
                    minimum_seed_risk_usd=(
                        recommendation.minimum_seed_risk_usd
                    ),
                    hard_risk_headroom_usd=(
                        recommendation.hard_risk_headroom_usd
                    ),
                    full_seed_preserved=(
                        recommendation.full_seed_preserved
                    ),
                    source_decision_sha256s=(
                        recommendation.source_decision_sha256s
                    ),
                    source_outcome_evidence_ids=(
                        recommendation.source_outcome_evidence_ids
                    ),
                )
                record = _record(
                    sequence=current.generation + 1,
                    seal=seal,
                    previous=current.chain_sha256,
                )
                updated = VersionedT13ShadowDecisionBook(
                    generation=current.generation + 1,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedT13ShadowDecisionBook:
        if not self._path.exists():
            return VersionedT13ShadowDecisionBook(generation=0)
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurableT13ShadowDecisionError(
                "T13 shadow store is unreadable"
            ) from error
        return _book_from_payload(payload)

    def _write_unlocked(
        self,
        book: VersionedT13ShadowDecisionBook,
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
            raise DurableT13ShadowDecisionError(
                "T13 shadow store write failed"
            ) from error
        finally:
            temp.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurableT13ShadowDecisionError(
                "T13 shadow writer lock already held"
            ) from error
        except OSError as error:
            raise DurableT13ShadowDecisionError(
                "T13 shadow writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurableT13ShadowDecisionError(
                "T13 shadow writer lock release failed"
            ) from error


def _recommendation_sha256(
    recommendation: Phase20T13ShadowRecommendation,
) -> str:
    payload = {
        "policy_id": recommendation.policy_id,
        "policy_sha256": recommendation.policy_sha256,
        "decision_epoch_id": recommendation.decision_epoch_id,
        "decision_evidence_sha256": recommendation.decision_evidence_sha256,
        "decision_at": recommendation.decision_at.isoformat(),
        "causal_pressure_active": recommendation.causal_pressure_active,
        "arrival_evidence_available": (
            recommendation.arrival_evidence_available
        ),
        "reserve_triggered": recommendation.reserve_triggered,
        "reserved_risk_usd": str(recommendation.reserved_risk_usd),
        "minimum_seed_risk_usd": (
            None
            if recommendation.minimum_seed_risk_usd is None
            else str(recommendation.minimum_seed_risk_usd)
        ),
        "hard_risk_headroom_usd": str(
            recommendation.hard_risk_headroom_usd
        ),
        "full_seed_preserved": recommendation.full_seed_preserved,
        "source_decision_sha256s": list(
            recommendation.source_decision_sha256s
        ),
        "source_outcome_evidence_ids": list(
            recommendation.source_outcome_evidence_ids
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _seal_payload(seal: T13ShadowDecisionSeal) -> dict[str, object]:
    return {
        "recommendation_sha256": seal.recommendation_sha256,
        "policy_sha256": seal.policy_sha256,
        "decision_epoch_id": seal.decision_epoch_id,
        "decision_evidence_sha256": seal.decision_evidence_sha256,
        "decision_at": seal.decision_at.isoformat(),
        "shadow_sealed_at": seal.shadow_sealed_at.isoformat(),
        "reserve_triggered": seal.reserve_triggered,
        "reserved_risk_usd": str(seal.reserved_risk_usd),
        "minimum_seed_risk_usd": (
            None
            if seal.minimum_seed_risk_usd is None
            else str(seal.minimum_seed_risk_usd)
        ),
        "hard_risk_headroom_usd": str(seal.hard_risk_headroom_usd),
        "full_seed_preserved": seal.full_seed_preserved,
        "source_decision_sha256s": list(seal.source_decision_sha256s),
        "source_outcome_evidence_ids": list(
            seal.source_outcome_evidence_ids
        ),
    }


def _seal_from_json(value: str) -> T13ShadowDecisionSeal:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise DurableT13ShadowDecisionError(
            "T13 shadow seal JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise DurableT13ShadowDecisionError(
            "T13 shadow seal payload must be object"
        )
    decisions = payload.get("source_decision_sha256s")
    outcomes = payload.get("source_outcome_evidence_ids")
    if not isinstance(decisions, list) or not isinstance(outcomes, list):
        raise DurableT13ShadowDecisionError(
            "T13 shadow seal provenance must be lists"
        )
    try:
        minimum_raw = payload.get("minimum_seed_risk_usd")
        return T13ShadowDecisionSeal(
            recommendation_sha256=str(payload["recommendation_sha256"]),
            policy_sha256=str(payload["policy_sha256"]),
            decision_epoch_id=str(payload["decision_epoch_id"]),
            decision_evidence_sha256=str(
                payload["decision_evidence_sha256"]
            ),
            decision_at=datetime.fromisoformat(str(payload["decision_at"])),
            shadow_sealed_at=datetime.fromisoformat(
                str(payload["shadow_sealed_at"])
            ),
            reserve_triggered=_bool(
                payload["reserve_triggered"],
                "reserve_triggered",
            ),
            reserved_risk_usd=_decimal(payload["reserved_risk_usd"]),
            minimum_seed_risk_usd=(
                None if minimum_raw is None else _decimal(minimum_raw)
            ),
            hard_risk_headroom_usd=_decimal(
                payload["hard_risk_headroom_usd"]
            ),
            full_seed_preserved=_bool(
                payload["full_seed_preserved"],
                "full_seed_preserved",
            ),
            source_decision_sha256s=tuple(
                str(item) for item in decisions
            ),
            source_outcome_evidence_ids=tuple(
                str(item) for item in outcomes
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DurableT13ShadowDecisionError(
            "T13 shadow seal payload invalid"
        ) from error


def _record(
    *,
    sequence: int,
    seal: T13ShadowDecisionSeal,
    previous: str,
) -> T13ShadowLedgerRecord:
    payload_json = json.dumps(
        _seal_payload(seal),
        sort_keys=True,
        separators=(",", ":"),
    )
    payload_sha = "sha256:" + hashlib.sha256(
        payload_json.encode()
    ).hexdigest()
    return T13ShadowLedgerRecord(
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
    raw = (
        f"{previous}|{sequence}|{epoch_id}|{payload_sha256}"
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _book_from_payload(
    payload: object,
) -> VersionedT13ShadowDecisionBook:
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        raise DurableT13ShadowDecisionError(
            "T13 shadow store schema mismatch"
        )
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise DurableT13ShadowDecisionError(
            "T13 shadow store records must be list"
        )
    try:
        records = tuple(
            T13ShadowLedgerRecord(
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
            raise TypeError("T13 shadow record must be object")
        generation = int(payload["generation"])
    except (KeyError, TypeError, ValueError) as error:
        raise DurableT13ShadowDecisionError(
            "T13 shadow store payload invalid"
        ) from error
    book = VersionedT13ShadowDecisionBook(
        generation=generation,
        records=records,
    )
    if payload.get("chain_sha256") != book.chain_sha256:
        raise DurableT13ShadowDecisionError(
            "T13 shadow terminal chain mismatch"
        )
    return book


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
        raise DurableT13ShadowDecisionError(
            "T13 shadow expected generation must be non-negative int"
        )


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise DurableT13ShadowDecisionError(
            "T13 shadow decimal field invalid"
        ) from error
    if not result.is_finite():
        raise DurableT13ShadowDecisionError(
            "T13 shadow decimal field must be finite"
        )
    return result


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise DurableT13ShadowDecisionError(
            f"T13 shadow {name} must be bool"
        )
    return value


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise DurableT13ShadowDecisionError(
            f"T13 shadow {name} must be timezone-aware"
        )


def _non_negative(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise DurableT13ShadowDecisionError(
            f"T13 shadow {name} must be finite non-negative"
        )


def _positive(value: Decimal, name: str) -> None:
    _non_negative(value, name)
    if value <= 0:
        raise DurableT13ShadowDecisionError(
            f"T13 shadow {name} must be positive"
        )
