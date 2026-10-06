"""Durable pre-outcome store for GEN-C8 adaptive compound speed.

Append-only, hash-chained, generation-CAS guarded and restart-safe.
Research-only; no capital, Risk, Execution or broker authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_adaptive_compound_speed_shadow import (
    GENC8_POLICY_FROZEN_AT,
    GENC8_POLICY_ID,
    Genc8AdaptiveCompoundSpeedDecision,
    Genc8SpeedPosture,
    genc8_policy_sha256,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

_SCHEMA = "QORE_CIBO_GENC8_ADAPTIVE_COMPOUND_SPEED_STORE_V1"
_GENESIS = "sha256:" + ("0" * 64)


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C8 store {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C8 store {name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class Genc8ShadowDecisionSeal:
    decision_sha256: str
    policy_sha256: str
    decision_id: str
    decision_at: datetime
    sealed_at: datetime
    account_provider_key: str
    account_ref: str
    genc5_decision_sha256: str
    regime_evidence_sha256: str
    fact_evidence_sha256s: tuple[str, ...]
    control_posture: Genc8SpeedPosture
    treatment_posture: Genc8SpeedPosture
    binding_ceiling_posture: Genc8SpeedPosture
    binding_reason: str
    blocker_codes: tuple[str, ...]
    treatment_differs_from_control: bool

    def __post_init__(self) -> None:
        for name in (
            "decision_sha256",
            "policy_sha256",
            "genc5_decision_sha256",
            "regime_evidence_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.policy_sha256 != genc8_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C8 store policy digest drift"
            )
        if (
            not self.decision_id
            or not self.account_provider_key
            or not self.account_ref
            or not self.binding_reason
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 store decision identity/reason is required"
            )
        _aware(self.decision_at, "decision_at")
        _aware(self.sealed_at, "sealed_at")
        if self.decision_at < GENC8_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C8 store cannot seal pre-freeze decision"
            )
        if self.sealed_at < self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C8 store seal cannot predate decision"
            )
        if len(self.fact_evidence_sha256s) != len(
            set(self.fact_evidence_sha256s)
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 store fact SHA list must be unique"
            )
        for item in self.fact_evidence_sha256s:
            _sha(item, "fact_evidence_sha256")
        if self.treatment_posture is not self.binding_ceiling_posture:
            raise CiboCompoundCapitalError(
                "GEN-C8 store treatment/ceiling drift"
            )
        expected_differs = self.treatment_posture is not self.control_posture
        if self.treatment_differs_from_control != expected_differs:
            raise CiboCompoundCapitalError(
                "GEN-C8 store divergence flag drift"
            )
        if len(self.blocker_codes) != len(set(self.blocker_codes)):
            raise CiboCompoundCapitalError(
                "GEN-C8 store blocker codes must be unique"
            )


@dataclass(frozen=True, slots=True)
class Genc8ShadowLedgerRecord:
    sequence: int
    decision_id: str
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
                "GEN-C8 store sequence must be positive int"
            )
        if not self.decision_id:
            raise CiboCompoundCapitalError(
                "GEN-C8 store decision_id is required"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            _sha(getattr(self, name), name)
        if (
            "sha256:" + hashlib.sha256(self.payload_json.encode()).hexdigest()
            != self.payload_sha256
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 store payload digest mismatch"
            )
        if self.chain_sha256 != _next_chain(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            decision_id=self.decision_id,
            payload_sha256=self.payload_sha256,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 store chain digest mismatch"
            )
        _seal_from_json(self.payload_json)


@dataclass(frozen=True, slots=True)
class VersionedGenc8ShadowBook:
    generation: int
    records: tuple[Genc8ShadowLedgerRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 store generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise CiboCompoundCapitalError(
                "GEN-C8 store generation/record count drift"
            )
        ids = tuple(item.decision_id for item in self.records)
        if len(ids) != len(set(ids)):
            raise CiboCompoundCapitalError(
                "GEN-C8 store decision ids must be unique"
            )
        previous = _GENESIS
        for sequence, record in enumerate(self.records, start=1):
            if (
                record.sequence != sequence
                or record.previous_chain_sha256 != previous
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C8 store chain sequence drift"
                )
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    def seal_for_decision(
        self,
        decision_id: str,
    ) -> Genc8ShadowDecisionSeal | None:
        rows = tuple(
            _seal_from_json(item.payload_json)
            for item in self.records
            if item.decision_id == decision_id
        )
        if len(rows) > 1:
            raise CiboCompoundCapitalError(
                "GEN-C8 store duplicate decision id"
            )
        return rows[0] if rows else None


class DurableGenc8AdaptiveCompoundSpeedStore:
    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise CiboCompoundCapitalError(
                "GEN-C8 store path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedGenc8ShadowBook:
        with self._lock:
            return self._load_unlocked()

    def seal(
        self,
        decision: Genc8AdaptiveCompoundSpeedDecision,
        *,
        sealed_at: datetime,
        expected_generation: int,
    ) -> VersionedGenc8ShadowBook:
        if not isinstance(
            decision,
            Genc8AdaptiveCompoundSpeedDecision,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 store requires canonical decision"
            )
        _aware(sealed_at, "sealed_at")
        if sealed_at < decision.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C8 seal cannot predate decision"
            )
        if (
            not isinstance(expected_generation, int)
            or isinstance(expected_generation, bool)
            or expected_generation < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 expected generation must be non-negative int"
            )
        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise CiboCompoundCapitalError(
                        "GEN-C8 store generation conflict"
                    )
                payload_json = _decision_json(
                    decision,
                    sealed_at=sealed_at,
                )
                payload_sha = "sha256:" + hashlib.sha256(
                    payload_json.encode()
                ).hexdigest()
                existing = current.seal_for_decision(decision.decision_id)
                if existing is not None:
                    row = next(
                        item
                        for item in current.records
                        if item.decision_id == decision.decision_id
                    )
                    if row.payload_sha256 == payload_sha:
                        return current
                    raise CiboCompoundCapitalError(
                        "GEN-C8 conflicting decision rewrite"
                    )
                row = Genc8ShadowLedgerRecord(
                    sequence=current.generation + 1,
                    decision_id=decision.decision_id,
                    payload_json=payload_json,
                    payload_sha256=payload_sha,
                    previous_chain_sha256=current.chain_sha256,
                    chain_sha256=_next_chain(
                        previous=current.chain_sha256,
                        sequence=current.generation + 1,
                        decision_id=decision.decision_id,
                        payload_sha256=payload_sha,
                    ),
                )
                updated = VersionedGenc8ShadowBook(
                    generation=current.generation + 1,
                    records=current.records + (row,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedGenc8ShadowBook:
        if not self._path.exists():
            return VersionedGenc8ShadowBook(generation=0)
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C8 store is unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("schema") != _SCHEMA
            or payload.get("policy_id") != GENC8_POLICY_ID
            or payload.get("policy_sha256") != genc8_policy_sha256()
        ):
            raise CiboCompoundCapitalError(
                "GEN-C8 store schema/policy mismatch"
            )
        raw_rows = payload.get("records")
        if not isinstance(raw_rows, list):
            raise CiboCompoundCapitalError(
                "GEN-C8 store records must be list"
            )
        try:
            records = tuple(
                Genc8ShadowLedgerRecord(
                    sequence=int(item["sequence"]),
                    decision_id=str(item["decision_id"]),
                    payload_json=str(item["payload_json"]),
                    payload_sha256=str(item["payload_sha256"]),
                    previous_chain_sha256=str(
                        item["previous_chain_sha256"]
                    ),
                    chain_sha256=str(item["chain_sha256"]),
                )
                for item in raw_rows
                if isinstance(item, dict)
            )
            if len(records) != len(raw_rows):
                raise TypeError("GEN-C8 record must be object")
            generation = int(payload["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C8 store payload invalid"
            ) from error
        book = VersionedGenc8ShadowBook(
            generation=generation,
            records=records,
        )
        if payload.get("chain_sha256") != book.chain_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C8 store terminal chain mismatch"
            )
        return book

    def _write_unlocked(self, book: VersionedGenc8ShadowBook) -> None:
        payload = {
            "schema": _SCHEMA,
            "policy_id": GENC8_POLICY_ID,
            "policy_sha256": genc8_policy_sha256(),
            "generation": book.generation,
            "chain_sha256": book.chain_sha256,
            "records": [
                {
                    "sequence": item.sequence,
                    "decision_id": item.decision_id,
                    "payload_json": item.payload_json,
                    "payload_sha256": item.payload_sha256,
                    "previous_chain_sha256": item.previous_chain_sha256,
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
                "GEN-C8 store write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise CiboCompoundCapitalError(
                "GEN-C8 store writer lock already held"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return


def genc8_decision_sha256(
    decision: Genc8AdaptiveCompoundSpeedDecision,
) -> str:
    payload = _decision_payload(decision)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def _decision_payload(
    decision: Genc8AdaptiveCompoundSpeedDecision,
) -> dict[str, object]:
    return {
        "policy_id": decision.policy_id,
        "policy_sha256": decision.policy_sha256,
        "policy_frozen_at": decision.policy_frozen_at.isoformat(),
        "decision_id": decision.decision_id,
        "decision_at": decision.decision_at.isoformat(),
        "account_provider_key": decision.account_provider_key,
        "account_ref": decision.account_ref,
        "genc5_decision_sha256": decision.genc5_decision_sha256,
        "regime_evidence_sha256": decision.regime_evidence_sha256,
        "fact_evidence_sha256s": list(decision.fact_evidence_sha256s),
        "control_posture": decision.control_posture.value,
        "treatment_posture": decision.treatment_posture.value,
        "binding_ceiling_posture": decision.binding_ceiling_posture.value,
        "binding_reason": decision.binding_reason,
        "blocker_codes": list(decision.blocker_codes),
        "treatment_differs_from_control": (
            decision.treatment_differs_from_control
        ),
        "amount_decided_usd": None,
        "outcome_present_at_seal": decision.outcome_present_at_seal,
        "runtime_authority": decision.runtime_authority,
        "sizing_authority": decision.sizing_authority,
        "risk_authority": decision.risk_authority,
        "execution_authority": decision.execution_authority,
        "live_authority": decision.live_authority,
        "real_capital_authority": decision.real_capital_authority,
    }


def _decision_json(
    decision: Genc8AdaptiveCompoundSpeedDecision,
    *,
    sealed_at: datetime,
) -> str:
    payload = {
        "decision_sha256": genc8_decision_sha256(decision),
        "sealed_at": sealed_at.isoformat(),
        **_decision_payload(decision),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _seal_from_json(value: str) -> Genc8ShadowDecisionSeal:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCompoundCapitalError(
            "GEN-C8 store seal JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            "GEN-C8 store seal payload must be object"
        )
    try:
        fact_shas = payload["fact_evidence_sha256s"]
        blockers = payload["blocker_codes"]
        if not isinstance(fact_shas, list) or not isinstance(blockers, list):
            raise TypeError("GEN-C8 list payload invalid")
        return Genc8ShadowDecisionSeal(
            decision_sha256=str(payload["decision_sha256"]),
            policy_sha256=str(payload["policy_sha256"]),
            decision_id=str(payload["decision_id"]),
            decision_at=datetime.fromisoformat(str(payload["decision_at"])),
            sealed_at=datetime.fromisoformat(str(payload["sealed_at"])),
            account_provider_key=str(payload["account_provider_key"]),
            account_ref=str(payload["account_ref"]),
            genc5_decision_sha256=str(payload["genc5_decision_sha256"]),
            regime_evidence_sha256=str(
                payload["regime_evidence_sha256"]
            ),
            fact_evidence_sha256s=tuple(str(item) for item in fact_shas),
            control_posture=Genc8SpeedPosture(
                str(payload["control_posture"])
            ),
            treatment_posture=Genc8SpeedPosture(
                str(payload["treatment_posture"])
            ),
            binding_ceiling_posture=Genc8SpeedPosture(
                str(payload["binding_ceiling_posture"])
            ),
            binding_reason=str(payload["binding_reason"]),
            blocker_codes=tuple(str(item) for item in blockers),
            treatment_differs_from_control=_strict_bool(
                payload["treatment_differs_from_control"],
                "treatment_differs_from_control",
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "GEN-C8 store seal payload invalid"
        ) from error


def _next_chain(
    *,
    previous: str,
    sequence: int,
    decision_id: str,
    payload_sha256: str,
) -> str:
    raw = f"{previous}|{sequence}|{decision_id}|{payload_sha256}".encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _strict_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise CiboCompoundCapitalError(
            f"GEN-C8 store {name} must be bool"
        )
    return value
