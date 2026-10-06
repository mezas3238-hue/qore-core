"""Durable pre-outcome store for GEN-C4 marginal-capital evidence.

GEN-C4 evidence must exist durably before GEN-C5 shadow decisions can later be
joined to outcomes. The store is append-only, SHA-256 hash chained,
generation-CAS guarded and protected by a cross-process writer lock.

It persists the canonical evidence JSON and enough indexed metadata to bind a
future canonical Phase20 outcome without reconstructing decision-time facts.

Research-only: no sizing, Risk, execution, LIVE or real-capital authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
    marginal_capital_utility_evidence_json,
    marginal_capital_utility_evidence_sha256,
)

_SCHEMA = "QORE_CIBO_GENC4_MARGINAL_EVIDENCE_STORE_V1"
_GENESIS = "sha256:" + ("0" * 64)


@dataclass(frozen=True, slots=True)
class Genc4MarginalEvidenceSeal:
    evidence_sha256: str
    evidence_id: str
    decision_at: datetime
    sealed_at: datetime
    provider_key: str
    account_ref: str
    trader_id: str
    signal_fingerprint: str
    source_opportunity_decision_sha256: str
    source_baseline_policy_record_sha256: str
    current_compound_capacity_usd: Decimal
    requested_incremental_capital_usd: Decimal
    incremental_stop_risk_usd: Decimal
    incremental_margin_usd: Decimal
    incremental_execution_cost_usd: Decimal
    expected_capital_minutes: Decimal
    epistemic_uncertainty: Decimal
    shared_fact_ids_used: tuple[str, ...]
    canonical_evidence_json: str
    outcome_present_at_seal: bool = False
    runtime_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "evidence_sha256",
            "source_opportunity_decision_sha256",
            "source_baseline_policy_record_sha256",
        ):
            _require_sha(getattr(self, name), name)
        if not self.evidence_id or not self.provider_key or not self.account_ref:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable evidence identity/account is required"
            )
        if not self.trader_id or not self.signal_fingerprint:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable evidence Trader/signal is required"
            )
        _aware(self.decision_at, "decision_at")
        _aware(self.sealed_at, "sealed_at")
        if self.sealed_at < self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable evidence seal cannot predate decision"
            )
        for name in (
            "current_compound_capacity_usd",
            "requested_incremental_capital_usd",
            "incremental_stop_risk_usd",
            "incremental_margin_usd",
            "incremental_execution_cost_usd",
            "expected_capital_minutes",
            "epistemic_uncertainty",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C4 durable {name} must be finite non-negative"
                )
        if self.requested_incremental_capital_usd <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable requested capital must be positive"
            )
        if self.incremental_stop_risk_usd <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable incremental stop risk must be positive"
            )
        if self.expected_capital_minutes <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable expected duration must be positive"
            )
        if self.epistemic_uncertainty > 1:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable uncertainty must be in [0,1]"
            )
        if len(self.shared_fact_ids_used) != len(set(self.shared_fact_ids_used)):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable Shared fact ids must be unique"
            )
        try:
            payload = json.loads(self.canonical_evidence_json)
        except json.JSONDecodeError as error:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable canonical evidence is invalid JSON"
            ) from error
        if not isinstance(payload, dict):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable canonical evidence must be object"
            )
        expected = "sha256:" + hashlib.sha256(
            self.canonical_evidence_json.encode()
        ).hexdigest()
        if expected != self.evidence_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable evidence digest mismatch"
            )
        _validate_metadata_binding(self, payload)
        for name in (
            "outcome_present_at_seal",
            "runtime_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C4 durable {name} must be bool"
                )
            if getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C4 durable evidence cannot contain outcome/authority"
                )


@dataclass(frozen=True, slots=True)
class Genc4MarginalEvidenceRecord:
    sequence: int
    evidence_sha256: str
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
            raise CiboCompoundCapitalError(
                "GEN-C4 durable sequence must be positive int"
            )
        for name in (
            "evidence_sha256",
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            _require_sha(getattr(self, name), name)
        payload_digest = "sha256:" + hashlib.sha256(
            self.payload_json.encode()
        ).hexdigest()
        if self.payload_sha256 != payload_digest:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable record payload digest mismatch"
            )
        expected_chain = _next_chain(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            evidence_sha256=self.evidence_sha256,
            payload_sha256=self.payload_sha256,
        )
        if self.chain_sha256 != expected_chain:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable record chain digest mismatch"
            )
        seal = _seal_from_json(self.payload_json)
        if seal.evidence_sha256 != self.evidence_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable record evidence binding drift"
            )


@dataclass(frozen=True, slots=True)
class VersionedGenc4MarginalEvidenceBook:
    generation: int
    records: tuple[Genc4MarginalEvidenceRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable generation/record count drift"
            )
        shas = tuple(item.evidence_sha256 for item in self.records)
        if len(shas) != len(set(shas)):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable evidence SHA must be unique"
            )
        ids = tuple(_seal_from_json(item.payload_json).evidence_id for item in self.records)
        if len(ids) != len(set(ids)):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable evidence id must be unique"
            )
        previous = _GENESIS
        for sequence, record in enumerate(self.records, start=1):
            if record.sequence != sequence:
                raise CiboCompoundCapitalError(
                    "GEN-C4 durable record sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise CiboCompoundCapitalError(
                    "GEN-C4 durable previous-chain drift"
                )
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    def seal_for_sha(
        self,
        evidence_sha256: str,
    ) -> Genc4MarginalEvidenceSeal | None:
        rows = tuple(
            _seal_from_json(item.payload_json)
            for item in self.records
            if item.evidence_sha256 == evidence_sha256
        )
        if len(rows) > 1:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable duplicate evidence SHA"
            )
        return rows[0] if rows else None


class DurableGenc4MarginalEvidenceStore:
    """Atomic append-only GEN-C4 pre-outcome evidence store."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(
            f".{path.name}.writer-lock"
        )
        self._lock = RLock()

    def load(self) -> VersionedGenc4MarginalEvidenceBook:
        with self._lock:
            return self._load_unlocked()

    def seal(
        self,
        evidence: MarginalCapitalUtilityEvidence,
        *,
        sealed_at: datetime,
        expected_generation: int,
    ) -> VersionedGenc4MarginalEvidenceBook:
        if not isinstance(evidence, MarginalCapitalUtilityEvidence):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store requires canonical evidence"
            )
        _aware(sealed_at, "sealed_at")
        _expected_generation(expected_generation)
        seal = _seal(evidence, sealed_at=sealed_at)

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise CiboCompoundCapitalError(
                        "GEN-C4 durable store generation conflict"
                    )
                previous = current.seal_for_sha(seal.evidence_sha256)
                if previous is not None:
                    if previous == seal:
                        return current
                    raise CiboCompoundCapitalError(
                        "GEN-C4 durable conflicting evidence rewrite"
                    )
                if any(
                    _seal_from_json(row.payload_json).evidence_id
                    == seal.evidence_id
                    for row in current.records
                ):
                    raise CiboCompoundCapitalError(
                        "GEN-C4 durable evidence id already exists"
                    )

                payload_json = json.dumps(
                    _seal_payload(seal),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                payload_sha = "sha256:" + hashlib.sha256(
                    payload_json.encode()
                ).hexdigest()
                record = Genc4MarginalEvidenceRecord(
                    sequence=current.generation + 1,
                    evidence_sha256=seal.evidence_sha256,
                    payload_json=payload_json,
                    payload_sha256=payload_sha,
                    previous_chain_sha256=current.chain_sha256,
                    chain_sha256=_next_chain(
                        previous=current.chain_sha256,
                        sequence=current.generation + 1,
                        evidence_sha256=seal.evidence_sha256,
                        payload_sha256=payload_sha,
                    ),
                )
                updated = VersionedGenc4MarginalEvidenceBook(
                    generation=current.generation + 1,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedGenc4MarginalEvidenceBook:
        if not self._path.exists():
            return VersionedGenc4MarginalEvidenceBook(generation=0)
        try:
            payload = json.loads(
                self._path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store is unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("schema") != _SCHEMA
        ):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store schema mismatch"
            )
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store records must be list"
            )
        try:
            records = tuple(
                Genc4MarginalEvidenceRecord(
                    sequence=int(row["sequence"]),
                    evidence_sha256=str(row["evidence_sha256"]),
                    payload_json=str(row["payload_json"]),
                    payload_sha256=str(row["payload_sha256"]),
                    previous_chain_sha256=str(
                        row["previous_chain_sha256"]
                    ),
                    chain_sha256=str(row["chain_sha256"]),
                )
                for row in raw_records
                if isinstance(row, dict)
            )
            if len(records) != len(raw_records):
                raise TypeError("GEN-C4 durable record must be object")
            generation = int(payload["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store payload invalid"
            ) from error
        book = VersionedGenc4MarginalEvidenceBook(
            generation=generation,
            records=records,
        )
        if payload.get("chain_sha256") != book.chain_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable terminal chain mismatch"
            )
        return book

    def _write_unlocked(
        self,
        book: VersionedGenc4MarginalEvidenceBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "chain_sha256": book.chain_sha256,
            "records": [
                {
                    "sequence": item.sequence,
                    "evidence_sha256": item.evidence_sha256,
                    "payload_json": item.payload_json,
                    "payload_sha256": item.payload_sha256,
                    "previous_chain_sha256": (
                        item.previous_chain_sha256
                    ),
                    "chain_sha256": item.chain_sha256,
                }
                for item in book.records
            ],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        payload,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        except OSError as error:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store writer lock already held"
            ) from error
        except OSError as error:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise CiboCompoundCapitalError(
                "GEN-C4 durable store writer lock release failed"
            ) from error


def _seal(
    evidence: MarginalCapitalUtilityEvidence,
    *,
    sealed_at: datetime,
) -> Genc4MarginalEvidenceSeal:
    if sealed_at < evidence.decision_at:
        raise CiboCompoundCapitalError(
            "GEN-C4 durable seal cannot predate decision"
        )
    return Genc4MarginalEvidenceSeal(
        evidence_sha256=marginal_capital_utility_evidence_sha256(evidence),
        evidence_id=evidence.evidence_id,
        decision_at=evidence.decision_at,
        sealed_at=sealed_at,
        provider_key=evidence.account_identity.provider_key,
        account_ref=evidence.account_identity.account_ref,
        trader_id=evidence.trader_id.value,
        signal_fingerprint=evidence.signal_fingerprint,
        source_opportunity_decision_sha256=(
            evidence.source_opportunity_decision_sha256
        ),
        source_baseline_policy_record_sha256=(
            evidence.source_baseline_policy_record_sha256
        ),
        current_compound_capacity_usd=(
            evidence.current_compound_capacity_usd
        ),
        requested_incremental_capital_usd=(
            evidence.requested_incremental_capital_usd
        ),
        incremental_stop_risk_usd=evidence.incremental_stop_risk_usd,
        incremental_margin_usd=evidence.incremental_margin_usd,
        incremental_execution_cost_usd=(
            evidence.incremental_execution_cost_usd
        ),
        expected_capital_minutes=evidence.expected_capital_minutes,
        epistemic_uncertainty=evidence.epistemic_uncertainty,
        shared_fact_ids_used=evidence.shared_fact_ids_used,
        canonical_evidence_json=(
            marginal_capital_utility_evidence_json(evidence)
        ),
        outcome_present_at_seal=False,
        runtime_authority=False,
        risk_authority=False,
        execution_authority=False,
    )


def _seal_payload(seal: Genc4MarginalEvidenceSeal) -> dict[str, object]:
    return {
        "evidence_sha256": seal.evidence_sha256,
        "evidence_id": seal.evidence_id,
        "decision_at": seal.decision_at.isoformat(),
        "sealed_at": seal.sealed_at.isoformat(),
        "provider_key": seal.provider_key,
        "account_ref": seal.account_ref,
        "trader_id": seal.trader_id,
        "signal_fingerprint": seal.signal_fingerprint,
        "source_opportunity_decision_sha256": (
            seal.source_opportunity_decision_sha256
        ),
        "source_baseline_policy_record_sha256": (
            seal.source_baseline_policy_record_sha256
        ),
        "current_compound_capacity_usd": str(
            seal.current_compound_capacity_usd
        ),
        "requested_incremental_capital_usd": str(
            seal.requested_incremental_capital_usd
        ),
        "incremental_stop_risk_usd": str(
            seal.incremental_stop_risk_usd
        ),
        "incremental_margin_usd": str(seal.incremental_margin_usd),
        "incremental_execution_cost_usd": str(
            seal.incremental_execution_cost_usd
        ),
        "expected_capital_minutes": str(seal.expected_capital_minutes),
        "epistemic_uncertainty": str(seal.epistemic_uncertainty),
        "shared_fact_ids_used": list(seal.shared_fact_ids_used),
        "canonical_evidence_json": seal.canonical_evidence_json,
        "outcome_present_at_seal": seal.outcome_present_at_seal,
        "runtime_authority": seal.runtime_authority,
        "risk_authority": seal.risk_authority,
        "execution_authority": seal.execution_authority,
    }


def _seal_from_json(value: str) -> Genc4MarginalEvidenceSeal:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCompoundCapitalError(
            "GEN-C4 durable seal JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            "GEN-C4 durable seal payload must be object"
        )
    try:
        facts = payload["shared_fact_ids_used"]
        if not isinstance(facts, list):
            raise TypeError("GEN-C4 durable Shared fact ids must be list")
        return Genc4MarginalEvidenceSeal(
            evidence_sha256=str(payload["evidence_sha256"]),
            evidence_id=str(payload["evidence_id"]),
            decision_at=datetime.fromisoformat(
                str(payload["decision_at"])
            ),
            sealed_at=datetime.fromisoformat(str(payload["sealed_at"])),
            provider_key=str(payload["provider_key"]),
            account_ref=str(payload["account_ref"]),
            trader_id=str(payload["trader_id"]),
            signal_fingerprint=str(payload["signal_fingerprint"]),
            source_opportunity_decision_sha256=str(
                payload["source_opportunity_decision_sha256"]
            ),
            source_baseline_policy_record_sha256=str(
                payload["source_baseline_policy_record_sha256"]
            ),
            current_compound_capacity_usd=Decimal(
                str(payload["current_compound_capacity_usd"])
            ),
            requested_incremental_capital_usd=Decimal(
                str(payload["requested_incremental_capital_usd"])
            ),
            incremental_stop_risk_usd=Decimal(
                str(payload["incremental_stop_risk_usd"])
            ),
            incremental_margin_usd=Decimal(
                str(payload["incremental_margin_usd"])
            ),
            incremental_execution_cost_usd=Decimal(
                str(payload["incremental_execution_cost_usd"])
            ),
            expected_capital_minutes=Decimal(
                str(payload["expected_capital_minutes"])
            ),
            epistemic_uncertainty=Decimal(
                str(payload["epistemic_uncertainty"])
            ),
            shared_fact_ids_used=tuple(str(item) for item in facts),
            canonical_evidence_json=str(
                payload["canonical_evidence_json"]
            ),
            outcome_present_at_seal=_bool(
                payload["outcome_present_at_seal"],
                "outcome_present_at_seal",
            ),
            runtime_authority=_bool(
                payload["runtime_authority"],
                "runtime_authority",
            ),
            risk_authority=_bool(
                payload["risk_authority"],
                "risk_authority",
            ),
            execution_authority=_bool(
                payload["execution_authority"],
                "execution_authority",
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "GEN-C4 durable seal payload invalid"
        ) from error


def _validate_metadata_binding(
    seal: Genc4MarginalEvidenceSeal,
    payload: dict[str, object],
) -> None:
    account = payload.get("account_identity")
    if not isinstance(account, dict):
        raise CiboCompoundCapitalError(
            "GEN-C4 durable canonical account binding missing"
        )
    expected: tuple[tuple[object, object, str], ...] = (
        (payload.get("evidence_id"), seal.evidence_id, "evidence id"),
        (
            payload.get("decision_at"),
            seal.decision_at.isoformat(),
            "decision time",
        ),
        (account.get("provider_key"), seal.provider_key, "provider"),
        (account.get("account_ref"), seal.account_ref, "account"),
        (payload.get("trader_id"), seal.trader_id, "Trader"),
        (
            payload.get("signal_fingerprint"),
            seal.signal_fingerprint,
            "signal",
        ),
        (
            payload.get("source_opportunity_decision_sha256"),
            seal.source_opportunity_decision_sha256,
            "source decision",
        ),
        (
            payload.get("source_baseline_policy_record_sha256"),
            seal.source_baseline_policy_record_sha256,
            "source baseline policy",
        ),
        (
            payload.get("current_compound_capacity_usd"),
            str(seal.current_compound_capacity_usd),
            "compound capacity",
        ),
        (
            payload.get("requested_incremental_capital_usd"),
            str(seal.requested_incremental_capital_usd),
            "requested capital",
        ),
        (
            payload.get("incremental_stop_risk_usd"),
            str(seal.incremental_stop_risk_usd),
            "stop risk",
        ),
        (
            payload.get("incremental_margin_usd"),
            str(seal.incremental_margin_usd),
            "margin",
        ),
        (
            payload.get("incremental_execution_cost_usd"),
            str(seal.incremental_execution_cost_usd),
            "execution cost",
        ),
        (
            payload.get("expected_capital_minutes"),
            str(seal.expected_capital_minutes),
            "capital duration",
        ),
        (
            payload.get("epistemic_uncertainty"),
            str(seal.epistemic_uncertainty),
            "uncertainty",
        ),
    )
    for observed, required, label in expected:
        if observed != required:
            raise CiboCompoundCapitalError(
                f"GEN-C4 durable canonical {label} binding drift"
            )
    if payload.get("shared_fact_ids_used") != list(
        seal.shared_fact_ids_used
    ):
        raise CiboCompoundCapitalError(
            "GEN-C4 durable canonical Shared fact binding drift"
        )
    if payload.get("outcome_present") is not False:
        raise CiboCompoundCapitalError(
            "GEN-C4 durable canonical evidence contains outcome"
        )
    if payload.get("utility_score_computed") is not False:
        raise CiboCompoundCapitalError(
            "GEN-C4 durable canonical evidence contains utility score"
        )


def _next_chain(
    *,
    previous: str,
    sequence: int,
    evidence_sha256: str,
    payload_sha256: str,
) -> str:
    raw = (
        f"{previous}|{sequence}|{evidence_sha256}|{payload_sha256}"
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _require_sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C4 durable {name} must be canonical SHA-256"
        )


def _expected_generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            "GEN-C4 durable expected generation must be non-negative int"
        )


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise CiboCompoundCapitalError(
            f"GEN-C4 durable {name} must be bool"
        )
    return value


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C4 durable {name} must be timezone-aware"
        )
