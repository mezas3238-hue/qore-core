"""Durable pre-outcome store for GEN-C5 sequential compounding shadow.

The store seals GEN-C5 treatment/control decisions append-only before later
outcome reconciliation. It is hash chained, generation-CAS guarded, protected
by a cross-process writer lock and rejects conflicting rewrites.

Research-only: no sizing, Risk, execution, DEMO-governed, LIVE, real-capital or
merge authority.
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
    CompoundCapitalState,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    GENC5_SHADOW_POLICY_ID,
    Genc5SequentialCompoundingShadowDecision,
    SequentialCompoundPosture,
    SequentialCompoundShadowAction,
    genc5_shadow_policy_sha256,
)

_SCHEMA = "QORE_CIBO_GENC5_SEQUENTIAL_COMPOUND_SHADOW_STORE_V1"
_GENESIS = "sha256:" + ("0" * 64)


@dataclass(frozen=True, slots=True)
class Genc5ShadowDecisionSeal:
    decision_sha256: str
    policy_sha256: str
    decision_id: str
    decision_at: datetime
    sealed_at: datetime
    account_provider_key: str
    account_ref: str
    source_lot_id: str
    source_lot_state: CompoundCapitalState
    source_lot_amount_usd: Decimal
    portfolio_sha256: str
    marginal_evidence_sha256: str
    policy_protected_floor_usd: Decimal
    candidate_compound_capacity_usd: Decimal
    control_posture: SequentialCompoundPosture
    control_action: SequentialCompoundShadowAction
    control_requested_risk_review_usd: Decimal
    treatment_posture: SequentialCompoundPosture
    treatment_action: SequentialCompoundShadowAction
    treatment_requested_risk_review_usd: Decimal
    blocker_codes: tuple[str, ...]
    treatment_differs_from_control: bool

    def __post_init__(self) -> None:
        for name in (
            "decision_sha256",
            "policy_sha256",
            "portfolio_sha256",
            "marginal_evidence_sha256",
        ):
            _require_sha(getattr(self, name), name)
        if self.policy_sha256 != genc5_shadow_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C5 store policy digest drift"
            )
        if not self.decision_id or not self.account_provider_key:
            raise CiboCompoundCapitalError(
                "GEN-C5 store decision/account identity is required"
            )
        if not self.account_ref or not self.source_lot_id:
            raise CiboCompoundCapitalError(
                "GEN-C5 store account/source lot identity is required"
            )
        _aware(self.decision_at, "decision_at")
        _aware(self.sealed_at, "sealed_at")
        # Historical market decisions may be sealed under the currently
        # frozen research policy. Freeze time identifies the immutable policy
        # version and is not a market-data availability boundary.
        if self.sealed_at < self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C5 store seal cannot predate decision"
            )
        if type(self.source_lot_state) is not CompoundCapitalState:
            raise CiboCompoundCapitalError(
                "GEN-C5 store source state is invalid"
            )
        for name in (
            "source_lot_amount_usd",
            "policy_protected_floor_usd",
            "candidate_compound_capacity_usd",
            "control_requested_risk_review_usd",
            "treatment_requested_risk_review_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C5 store {name} must be finite non-negative"
                )
        if len(self.blocker_codes) != len(set(self.blocker_codes)):
            raise CiboCompoundCapitalError(
                "GEN-C5 store blocker codes must be unique"
            )
        if type(self.treatment_differs_from_control) is not bool:
            raise CiboCompoundCapitalError(
                "GEN-C5 store treatment difference flag must be bool"
            )


@dataclass(frozen=True, slots=True)
class Genc5ShadowLedgerRecord:
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
                "GEN-C5 store sequence must be positive int"
            )
        if not self.decision_id:
            raise CiboCompoundCapitalError(
                "GEN-C5 store decision id is required"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            _require_sha(getattr(self, name), name)
        expected_payload = "sha256:" + hashlib.sha256(
            self.payload_json.encode()
        ).hexdigest()
        if self.payload_sha256 != expected_payload:
            raise CiboCompoundCapitalError(
                "GEN-C5 store payload digest mismatch"
            )
        expected_chain = _next_chain(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            decision_id=self.decision_id,
            payload_sha256=self.payload_sha256,
        )
        if self.chain_sha256 != expected_chain:
            raise CiboCompoundCapitalError(
                "GEN-C5 store chain digest mismatch"
            )
        _seal_from_json(self.payload_json)


@dataclass(frozen=True, slots=True)
class VersionedGenc5ShadowBook:
    generation: int
    records: tuple[Genc5ShadowLedgerRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 store generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise CiboCompoundCapitalError(
                "GEN-C5 store generation/record count drift"
            )
        ids = tuple(item.decision_id for item in self.records)
        if len(ids) != len(set(ids)):
            raise CiboCompoundCapitalError(
                "GEN-C5 store decision ids must be unique"
            )
        previous = _GENESIS
        for expected_sequence, record in enumerate(self.records, start=1):
            if record.sequence != expected_sequence:
                raise CiboCompoundCapitalError(
                    "GEN-C5 store record sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise CiboCompoundCapitalError(
                    "GEN-C5 store previous-chain drift"
                )
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    def seal_for_decision(
        self,
        decision_id: str,
    ) -> Genc5ShadowDecisionSeal | None:
        rows = tuple(
            _seal_from_json(item.payload_json)
            for item in self.records
            if item.decision_id == decision_id
        )
        if len(rows) > 1:
            raise CiboCompoundCapitalError(
                "GEN-C5 store duplicate decision id"
            )
        return rows[0] if rows else None


class DurableGenc5SequentialCompoundingShadowStore:
    """Atomic append-only GEN-C5 shadow store."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise CiboCompoundCapitalError(
                "GEN-C5 store path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(
            f".{path.name}.writer-lock"
        )
        self._lock = RLock()

    def load(self) -> VersionedGenc5ShadowBook:
        with self._lock:
            return self._load_unlocked()

    def seal(
        self,
        decision: Genc5SequentialCompoundingShadowDecision,
        *,
        sealed_at: datetime,
        expected_generation: int,
    ) -> VersionedGenc5ShadowBook:
        if not isinstance(
            decision,
            Genc5SequentialCompoundingShadowDecision,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 store requires canonical shadow decision"
            )
        _aware(sealed_at, "sealed_at")
        _expected_generation(expected_generation)
        seal = _decision_seal(decision, sealed_at=sealed_at)

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise CiboCompoundCapitalError(
                        "GEN-C5 store generation conflict"
                    )
                previous = current.seal_for_decision(decision.decision_id)
                if previous is not None:
                    if previous == seal:
                        return current
                    raise CiboCompoundCapitalError(
                        "GEN-C5 conflicting shadow decision rewrite"
                    )

                payload_json = json.dumps(
                    _seal_payload(seal),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                payload_sha = "sha256:" + hashlib.sha256(
                    payload_json.encode()
                ).hexdigest()
                record = Genc5ShadowLedgerRecord(
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
                updated = VersionedGenc5ShadowBook(
                    generation=current.generation + 1,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedGenc5ShadowBook:
        if not self._path.exists():
            return VersionedGenc5ShadowBook(generation=0)
        try:
            payload = json.loads(
                self._path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C5 store is unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("schema") != _SCHEMA
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 store schema mismatch"
            )
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise CiboCompoundCapitalError(
                "GEN-C5 store records must be list"
            )
        try:
            records = tuple(
                Genc5ShadowLedgerRecord(
                    sequence=int(row["sequence"]),
                    decision_id=str(row["decision_id"]),
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
                raise TypeError("GEN-C5 record must be object")
            generation = int(payload["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C5 store payload invalid"
            ) from error

        book = VersionedGenc5ShadowBook(
            generation=generation,
            records=records,
        )
        if payload.get("chain_sha256") != book.chain_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C5 store terminal chain mismatch"
            )
        return book

    def _write_unlocked(self, book: VersionedGenc5ShadowBook) -> None:
        payload = {
            "schema": _SCHEMA,
            "policy_id": GENC5_SHADOW_POLICY_ID,
            "policy_sha256": genc5_shadow_policy_sha256(),
            "generation": book.generation,
            "chain_sha256": book.chain_sha256,
            "records": [
                {
                    "sequence": item.sequence,
                    "decision_id": item.decision_id,
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
                "GEN-C5 store write failed"
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
                "GEN-C5 store writer lock already held"
            ) from error
        except OSError as error:
            raise CiboCompoundCapitalError(
                "GEN-C5 store writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise CiboCompoundCapitalError(
                "GEN-C5 store writer lock release failed"
            ) from error


def genc5_shadow_decision_json(
    decision: Genc5SequentialCompoundingShadowDecision,
) -> str:
    if not isinstance(
        decision,
        Genc5SequentialCompoundingShadowDecision,
    ):
        raise CiboCompoundCapitalError(
            "GEN-C5 canonical JSON requires shadow decision"
        )
    return json.dumps(
        _decision_payload(decision),
        sort_keys=True,
        separators=(",", ":"),
    )


def genc5_shadow_decision_sha256(
    decision: Genc5SequentialCompoundingShadowDecision,
) -> str:
    return "sha256:" + hashlib.sha256(
        genc5_shadow_decision_json(decision).encode()
    ).hexdigest()


def _decision_seal(
    decision: Genc5SequentialCompoundingShadowDecision,
    *,
    sealed_at: datetime,
) -> Genc5ShadowDecisionSeal:
    if sealed_at < decision.decision_at:
        raise CiboCompoundCapitalError(
            "GEN-C5 seal cannot predate decision"
        )
    return Genc5ShadowDecisionSeal(
        decision_sha256=genc5_shadow_decision_sha256(decision),
        policy_sha256=decision.policy_sha256,
        decision_id=decision.decision_id,
        decision_at=decision.decision_at,
        sealed_at=sealed_at,
        account_provider_key=decision.account_provider_key,
        account_ref=decision.account_ref,
        source_lot_id=decision.source_lot_id,
        source_lot_state=decision.source_lot_state,
        source_lot_amount_usd=decision.source_lot_amount_usd,
        portfolio_sha256=decision.portfolio_sha256,
        marginal_evidence_sha256=decision.marginal_evidence_sha256,
        policy_protected_floor_usd=(
            decision.policy_protected_floor_usd
        ),
        candidate_compound_capacity_usd=(
            decision.candidate_compound_capacity_usd
        ),
        control_posture=decision.control_posture,
        control_action=decision.control_action,
        control_requested_risk_review_usd=(
            decision.control_requested_risk_review_usd
        ),
        treatment_posture=decision.treatment_posture,
        treatment_action=decision.treatment_action,
        treatment_requested_risk_review_usd=(
            decision.treatment_requested_risk_review_usd
        ),
        blocker_codes=decision.blocker_codes,
        treatment_differs_from_control=(
            decision.treatment_differs_from_control
        ),
    )


def _decision_payload(
    decision: Genc5SequentialCompoundingShadowDecision,
) -> dict[str, object]:
    return {
        "policy_id": decision.policy_id,
        "policy_sha256": decision.policy_sha256,
        "policy_frozen_at": decision.policy_frozen_at.isoformat(),
        "decision_id": decision.decision_id,
        "decision_at": decision.decision_at.isoformat(),
        "account_provider_key": decision.account_provider_key,
        "account_ref": decision.account_ref,
        "source_lot_id": decision.source_lot_id,
        "source_lot_state": decision.source_lot_state.value,
        "source_lot_amount_usd": str(decision.source_lot_amount_usd),
        "portfolio_sha256": decision.portfolio_sha256,
        "marginal_evidence_sha256": decision.marginal_evidence_sha256,
        "policy_protected_floor_usd": str(
            decision.policy_protected_floor_usd
        ),
        "candidate_compound_capacity_usd": str(
            decision.candidate_compound_capacity_usd
        ),
        "control_posture": decision.control_posture.value,
        "control_action": decision.control_action.value,
        "control_requested_risk_review_usd": str(
            decision.control_requested_risk_review_usd
        ),
        "treatment_posture": decision.treatment_posture.value,
        "treatment_action": decision.treatment_action.value,
        "treatment_requested_risk_review_usd": str(
            decision.treatment_requested_risk_review_usd
        ),
        "blocker_codes": list(decision.blocker_codes),
        "treatment_differs_from_control": (
            decision.treatment_differs_from_control
        ),
        "outcome_present_at_seal": decision.outcome_present_at_seal,
        "runtime_authority": decision.runtime_authority,
        "risk_authority": decision.risk_authority,
        "execution_authority": decision.execution_authority,
        "live_authority": decision.live_authority,
        "real_capital_authority": decision.real_capital_authority,
    }


def _seal_payload(seal: Genc5ShadowDecisionSeal) -> dict[str, object]:
    return {
        "decision_sha256": seal.decision_sha256,
        "policy_sha256": seal.policy_sha256,
        "decision_id": seal.decision_id,
        "decision_at": seal.decision_at.isoformat(),
        "sealed_at": seal.sealed_at.isoformat(),
        "account_provider_key": seal.account_provider_key,
        "account_ref": seal.account_ref,
        "source_lot_id": seal.source_lot_id,
        "source_lot_state": seal.source_lot_state.value,
        "source_lot_amount_usd": str(seal.source_lot_amount_usd),
        "portfolio_sha256": seal.portfolio_sha256,
        "marginal_evidence_sha256": seal.marginal_evidence_sha256,
        "policy_protected_floor_usd": str(
            seal.policy_protected_floor_usd
        ),
        "candidate_compound_capacity_usd": str(
            seal.candidate_compound_capacity_usd
        ),
        "control_posture": seal.control_posture.value,
        "control_action": seal.control_action.value,
        "control_requested_risk_review_usd": str(
            seal.control_requested_risk_review_usd
        ),
        "treatment_posture": seal.treatment_posture.value,
        "treatment_action": seal.treatment_action.value,
        "treatment_requested_risk_review_usd": str(
            seal.treatment_requested_risk_review_usd
        ),
        "blocker_codes": list(seal.blocker_codes),
        "treatment_differs_from_control": (
            seal.treatment_differs_from_control
        ),
    }


def _seal_from_json(value: str) -> Genc5ShadowDecisionSeal:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCompoundCapitalError(
            "GEN-C5 store seal JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            "GEN-C5 store seal payload must be object"
        )
    try:
        blockers = payload["blocker_codes"]
        if not isinstance(blockers, list):
            raise TypeError("GEN-C5 blockers must be list")
        return Genc5ShadowDecisionSeal(
            decision_sha256=str(payload["decision_sha256"]),
            policy_sha256=str(payload["policy_sha256"]),
            decision_id=str(payload["decision_id"]),
            decision_at=datetime.fromisoformat(
                str(payload["decision_at"])
            ),
            sealed_at=datetime.fromisoformat(str(payload["sealed_at"])),
            account_provider_key=str(
                payload["account_provider_key"]
            ),
            account_ref=str(payload["account_ref"]),
            source_lot_id=str(payload["source_lot_id"]),
            source_lot_state=CompoundCapitalState(
                str(payload["source_lot_state"])
            ),
            source_lot_amount_usd=Decimal(
                str(payload["source_lot_amount_usd"])
            ),
            portfolio_sha256=str(payload["portfolio_sha256"]),
            marginal_evidence_sha256=str(
                payload["marginal_evidence_sha256"]
            ),
            policy_protected_floor_usd=Decimal(
                str(payload["policy_protected_floor_usd"])
            ),
            candidate_compound_capacity_usd=Decimal(
                str(payload["candidate_compound_capacity_usd"])
            ),
            control_posture=SequentialCompoundPosture(
                str(payload["control_posture"])
            ),
            control_action=SequentialCompoundShadowAction(
                str(payload["control_action"])
            ),
            control_requested_risk_review_usd=Decimal(
                str(payload["control_requested_risk_review_usd"])
            ),
            treatment_posture=SequentialCompoundPosture(
                str(payload["treatment_posture"])
            ),
            treatment_action=SequentialCompoundShadowAction(
                str(payload["treatment_action"])
            ),
            treatment_requested_risk_review_usd=Decimal(
                str(payload["treatment_requested_risk_review_usd"])
            ),
            blocker_codes=tuple(str(item) for item in blockers),
            treatment_differs_from_control=_bool(
                payload["treatment_differs_from_control"],
                "treatment_differs_from_control",
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "GEN-C5 store seal payload invalid"
        ) from error


def _next_chain(
    *,
    previous: str,
    sequence: int,
    decision_id: str,
    payload_sha256: str,
) -> str:
    raw = (
        f"{previous}|{sequence}|{decision_id}|{payload_sha256}"
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
            f"GEN-C5 store {name} must be canonical SHA-256"
        )


def _expected_generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            "GEN-C5 store expected generation must be non-negative int"
        )


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise CiboCompoundCapitalError(
            f"GEN-C5 store {name} must be bool"
        )
    return value


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C5 store {name} must be timezone-aware"
        )
