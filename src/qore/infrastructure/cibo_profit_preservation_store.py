"""Durable pre-outcome store for GEN-C7 profit-preservation shadow.

Append-only, hash-chained, generation-CAS guarded, restart-safe and conflicting
rewrite safe. Research-only: no capital mutation, Risk or Execution authority.
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

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_profit_preservation_shadow import (
    GENC7_POLICY_FROZEN_AT,
    GENC7_POLICY_ID,
    Genc7Action,
    Genc7ProfitPreservationShadowDecision,
    Genc7SourceBucket,
    genc7_policy_sha256,
)

_SCHEMA = "QORE_CIBO_GENC7_PROFIT_PRESERVATION_SHADOW_STORE_V1"
_GENESIS = "sha256:" + ("0" * 64)


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C7 store {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C7 store {name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class Genc7ShadowDecisionSeal:
    decision_sha256: str
    policy_sha256: str
    decision_id: str
    decision_at: datetime
    sealed_at: datetime
    account_provider_key: str
    account_ref: str
    state_evidence_sha256: str
    proposal_evidence_sha256: str
    proposal_action: Genc7Action
    proposal_source_bucket: Genc7SourceBucket
    proposal_amount_usd: Decimal
    evaluation_horizon_minutes: int
    initial_realized_capital_usd: Decimal
    initial_realized_profit_usd: Decimal
    initial_protected_floor_usd: Decimal
    initial_base_capital_usd: Decimal
    initial_compound_capital_usd: Decimal
    control_action: Genc7Action
    control_amount_usd: Decimal
    treatment_action: Genc7Action
    treatment_amount_usd: Decimal
    blocker_codes: tuple[str, ...]
    giveback_amount_usd: Decimal
    profit_retention_ratio: Decimal
    floor_growth_rate: Decimal | None
    base_drawdown_usd: Decimal
    compound_drawdown_usd: Decimal
    treatment_differs_from_control: bool

    def __post_init__(self) -> None:
        for name in (
            "decision_sha256",
            "policy_sha256",
            "state_evidence_sha256",
            "proposal_evidence_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.policy_sha256 != genc7_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C7 store policy digest drift"
            )
        if (
            not self.decision_id
            or not self.account_provider_key
            or not self.account_ref
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 store decision/account identity is required"
            )
        if (
            not isinstance(self.evaluation_horizon_minutes, int)
            or isinstance(self.evaluation_horizon_minutes, bool)
            or self.evaluation_horizon_minutes <= 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 store evaluation horizon must be positive int"
            )
        _aware(self.decision_at, "decision_at")
        _aware(self.sealed_at, "sealed_at")
        if self.decision_at < GENC7_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C7 store cannot seal pre-freeze decision"
            )
        if self.sealed_at < self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C7 store seal cannot predate decision"
            )
        if self.proposal_action is Genc7Action.HOLD_CURRENT_CAPITAL_STATE:
            raise CiboCompoundCapitalError(
                "GEN-C7 store proposal action cannot be control HOLD"
            )
        if self.proposal_amount_usd <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C7 store proposal amount must be positive"
            )
        for name in (
            "proposal_amount_usd",
            "initial_realized_capital_usd",
            "initial_realized_profit_usd",
            "initial_protected_floor_usd",
            "initial_base_capital_usd",
            "initial_compound_capital_usd",
            "control_amount_usd",
            "treatment_amount_usd",
            "giveback_amount_usd",
            "profit_retention_ratio",
            "base_drawdown_usd",
            "compound_drawdown_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C7 store {name} must be finite non-negative"
                )
        if self.floor_growth_rate is not None and (
            not isinstance(self.floor_growth_rate, Decimal)
            or not self.floor_growth_rate.is_finite()
            or self.floor_growth_rate < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 store floor_growth_rate is invalid"
            )
        if len(self.blocker_codes) != len(set(self.blocker_codes)):
            raise CiboCompoundCapitalError(
                "GEN-C7 store blocker codes must be unique"
            )
        if type(self.treatment_differs_from_control) is not bool:
            raise CiboCompoundCapitalError(
                "GEN-C7 store divergence flag must be bool"
            )
        if (
            self.control_action is not Genc7Action.HOLD_CURRENT_CAPITAL_STATE
            or self.control_amount_usd != 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 store control must HOLD with zero amount"
            )
        active = (
            self.treatment_action
            is not Genc7Action.HOLD_CURRENT_CAPITAL_STATE
        )
        if active:
            if (
                self.treatment_action is not self.proposal_action
                or self.treatment_amount_usd != self.proposal_amount_usd
                or self.blocker_codes
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C7 store active treatment/proposal drift"
                )
        elif self.treatment_amount_usd != 0:
            raise CiboCompoundCapitalError(
                "GEN-C7 store held treatment must have zero amount"
            )
        if self.treatment_differs_from_control != active:
            raise CiboCompoundCapitalError(
                "GEN-C7 store divergence flag drift"
            )


@dataclass(frozen=True, slots=True)
class Genc7ShadowLedgerRecord:
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
                "GEN-C7 store sequence must be positive int"
            )
        if not self.decision_id:
            raise CiboCompoundCapitalError(
                "GEN-C7 store decision id is required"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            _sha(getattr(self, name), name)
        expected_payload = "sha256:" + hashlib.sha256(
            self.payload_json.encode()
        ).hexdigest()
        if expected_payload != self.payload_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C7 store payload digest mismatch"
            )
        expected_chain = _next_chain(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            decision_id=self.decision_id,
            payload_sha256=self.payload_sha256,
        )
        if expected_chain != self.chain_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C7 store chain digest mismatch"
            )
        _seal_from_json(self.payload_json)


@dataclass(frozen=True, slots=True)
class VersionedGenc7ShadowBook:
    generation: int
    records: tuple[Genc7ShadowLedgerRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 store generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise CiboCompoundCapitalError(
                "GEN-C7 store generation/record count drift"
            )
        ids = tuple(item.decision_id for item in self.records)
        if len(ids) != len(set(ids)):
            raise CiboCompoundCapitalError(
                "GEN-C7 store decision ids must be unique"
            )
        previous = _GENESIS
        for sequence, record in enumerate(self.records, start=1):
            if record.sequence != sequence:
                raise CiboCompoundCapitalError(
                    "GEN-C7 store record sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise CiboCompoundCapitalError(
                    "GEN-C7 store previous-chain drift"
                )
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    def seal_for_decision(
        self,
        decision_id: str,
    ) -> Genc7ShadowDecisionSeal | None:
        rows = tuple(
            _seal_from_json(item.payload_json)
            for item in self.records
            if item.decision_id == decision_id
        )
        if len(rows) > 1:
            raise CiboCompoundCapitalError(
                "GEN-C7 store duplicate decision id"
            )
        return rows[0] if rows else None


class DurableGenc7ProfitPreservationShadowStore:
    """Atomic append-only GEN-C7 shadow decision store."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise CiboCompoundCapitalError(
                "GEN-C7 store path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(
            f".{path.name}.writer-lock"
        )
        self._lock = RLock()

    def load(self) -> VersionedGenc7ShadowBook:
        with self._lock:
            return self._load_unlocked()

    def seal(
        self,
        decision: Genc7ProfitPreservationShadowDecision,
        *,
        sealed_at: datetime,
        expected_generation: int,
    ) -> VersionedGenc7ShadowBook:
        if not isinstance(
            decision,
            Genc7ProfitPreservationShadowDecision,
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 store requires canonical shadow decision"
            )
        _aware(sealed_at, "sealed_at")
        if sealed_at < decision.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C7 seal cannot predate decision"
            )
        if (
            not isinstance(expected_generation, int)
            or isinstance(expected_generation, bool)
            or expected_generation < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 expected generation must be non-negative int"
            )

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise CiboCompoundCapitalError(
                        "GEN-C7 store generation conflict"
                    )
                existing = current.seal_for_decision(decision.decision_id)
                payload_json = genc7_shadow_decision_json(
                    decision,
                    sealed_at=sealed_at,
                )
                payload_sha = "sha256:" + hashlib.sha256(
                    payload_json.encode()
                ).hexdigest()
                if existing is not None:
                    existing_record = next(
                        item
                        for item in current.records
                        if item.decision_id == decision.decision_id
                    )
                    if existing_record.payload_sha256 == payload_sha:
                        return current
                    raise CiboCompoundCapitalError(
                        "GEN-C7 conflicting decision rewrite"
                    )

                record = Genc7ShadowLedgerRecord(
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
                updated = VersionedGenc7ShadowBook(
                    generation=current.generation + 1,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedGenc7ShadowBook:
        if not self._path.exists():
            return VersionedGenc7ShadowBook(generation=0)
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C7 store is unreadable"
            ) from error
        if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
            raise CiboCompoundCapitalError(
                "GEN-C7 store schema mismatch"
            )
        if (
            payload.get("policy_id") != GENC7_POLICY_ID
            or payload.get("policy_sha256") != genc7_policy_sha256()
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 store policy identity drift"
            )
        rows = payload.get("records")
        if not isinstance(rows, list):
            raise CiboCompoundCapitalError(
                "GEN-C7 store records must be list"
            )
        try:
            records = tuple(
                Genc7ShadowLedgerRecord(
                    sequence=int(item["sequence"]),
                    decision_id=str(item["decision_id"]),
                    payload_json=str(item["payload_json"]),
                    payload_sha256=str(item["payload_sha256"]),
                    previous_chain_sha256=str(
                        item["previous_chain_sha256"]
                    ),
                    chain_sha256=str(item["chain_sha256"]),
                )
                for item in rows
                if isinstance(item, dict)
            )
            if len(records) != len(rows):
                raise TypeError("GEN-C7 record must be object")
            generation = int(payload["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C7 store payload invalid"
            ) from error
        book = VersionedGenc7ShadowBook(
            generation=generation,
            records=records,
        )
        if payload.get("chain_sha256") != book.chain_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C7 store terminal chain mismatch"
            )
        return book

    def _write_unlocked(self, book: VersionedGenc7ShadowBook) -> None:
        payload = {
            "schema": _SCHEMA,
            "policy_id": GENC7_POLICY_ID,
            "policy_sha256": genc7_policy_sha256(),
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
                "GEN-C7 store write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise CiboCompoundCapitalError(
                "GEN-C7 store writer lock already held"
            ) from error
        except OSError as error:
            raise CiboCompoundCapitalError(
                "GEN-C7 store writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise CiboCompoundCapitalError(
                "GEN-C7 store writer lock release failed"
            ) from error


def genc7_shadow_decision_json(
    decision: Genc7ProfitPreservationShadowDecision,
    *,
    sealed_at: datetime,
) -> str:
    _aware(sealed_at, "sealed_at")
    payload = {
        "decision_sha256": genc7_shadow_decision_sha256(decision),
        "policy_sha256": decision.policy_sha256,
        "decision_id": decision.decision_id,
        "decision_at": decision.decision_at.isoformat(),
        "sealed_at": sealed_at.isoformat(),
        "account_provider_key": decision.account_provider_key,
        "account_ref": decision.account_ref,
        "state_evidence_sha256": decision.state_evidence_sha256,
        "proposal_evidence_sha256": decision.proposal_evidence_sha256,
        "proposal_action": decision.proposal_action.value,
        "proposal_source_bucket": decision.proposal_source_bucket.value,
        "proposal_amount_usd": str(decision.proposal_amount_usd),
        "evaluation_horizon_minutes": decision.evaluation_horizon_minutes,
        "initial_realized_capital_usd": str(
            decision.initial_realized_capital_usd
        ),
        "initial_realized_profit_usd": str(
            decision.initial_realized_profit_usd
        ),
        "initial_protected_floor_usd": str(
            decision.initial_protected_floor_usd
        ),
        "initial_base_capital_usd": str(
            decision.initial_base_capital_usd
        ),
        "initial_compound_capital_usd": str(
            decision.initial_compound_capital_usd
        ),
        "control_action": decision.control_action.value,
        "control_amount_usd": str(decision.control_amount_usd),
        "treatment_action": decision.treatment_action.value,
        "treatment_amount_usd": str(decision.treatment_amount_usd),
        "blocker_codes": list(decision.blocker_codes),
        "giveback_amount_usd": str(decision.giveback_amount_usd),
        "profit_retention_ratio": str(decision.profit_retention_ratio),
        "floor_growth_rate": (
            None
            if decision.floor_growth_rate is None
            else str(decision.floor_growth_rate)
        ),
        "base_drawdown_usd": str(decision.base_drawdown_usd),
        "compound_drawdown_usd": str(decision.compound_drawdown_usd),
        "treatment_differs_from_control": (
            decision.treatment_differs_from_control
        ),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def genc7_shadow_decision_sha256(
    decision: Genc7ProfitPreservationShadowDecision,
) -> str:
    payload = {
        "policy_id": decision.policy_id,
        "policy_sha256": decision.policy_sha256,
        "policy_frozen_at": decision.policy_frozen_at.isoformat(),
        "decision_id": decision.decision_id,
        "decision_at": decision.decision_at.isoformat(),
        "account_provider_key": decision.account_provider_key,
        "account_ref": decision.account_ref,
        "state_evidence_sha256": decision.state_evidence_sha256,
        "proposal_evidence_sha256": decision.proposal_evidence_sha256,
        "proposal_action": decision.proposal_action.value,
        "proposal_source_bucket": decision.proposal_source_bucket.value,
        "proposal_amount_usd": str(decision.proposal_amount_usd),
        "evaluation_horizon_minutes": decision.evaluation_horizon_minutes,
        "initial_realized_capital_usd": str(
            decision.initial_realized_capital_usd
        ),
        "initial_realized_profit_usd": str(
            decision.initial_realized_profit_usd
        ),
        "initial_protected_floor_usd": str(
            decision.initial_protected_floor_usd
        ),
        "initial_base_capital_usd": str(
            decision.initial_base_capital_usd
        ),
        "initial_compound_capital_usd": str(
            decision.initial_compound_capital_usd
        ),
        "control_action": decision.control_action.value,
        "control_amount_usd": str(decision.control_amount_usd),
        "treatment_action": decision.treatment_action.value,
        "treatment_amount_usd": str(decision.treatment_amount_usd),
        "blocker_codes": list(decision.blocker_codes),
        "giveback_amount_usd": str(decision.giveback_amount_usd),
        "profit_retention_ratio": str(decision.profit_retention_ratio),
        "floor_growth_rate": (
            None
            if decision.floor_growth_rate is None
            else str(decision.floor_growth_rate)
        ),
        "base_drawdown_usd": str(decision.base_drawdown_usd),
        "compound_drawdown_usd": str(decision.compound_drawdown_usd),
        "treatment_differs_from_control": (
            decision.treatment_differs_from_control
        ),
        "outcome_present_at_seal": decision.outcome_present_at_seal,
        "runtime_authority": decision.runtime_authority,
        "sizing_authority": decision.sizing_authority,
        "risk_authority": decision.risk_authority,
        "execution_authority": decision.execution_authority,
        "live_authority": decision.live_authority,
        "real_capital_authority": decision.real_capital_authority,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def _seal_from_json(value: str) -> Genc7ShadowDecisionSeal:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCompoundCapitalError(
            "GEN-C7 store seal JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            "GEN-C7 store seal payload must be object"
        )
    try:
        blockers = payload["blocker_codes"]
        if not isinstance(blockers, list):
            raise TypeError("GEN-C7 blockers must be list")
        floor_raw = payload["floor_growth_rate"]
        return Genc7ShadowDecisionSeal(
            decision_sha256=str(payload["decision_sha256"]),
            policy_sha256=str(payload["policy_sha256"]),
            decision_id=str(payload["decision_id"]),
            decision_at=datetime.fromisoformat(str(payload["decision_at"])),
            sealed_at=datetime.fromisoformat(str(payload["sealed_at"])),
            account_provider_key=str(payload["account_provider_key"]),
            account_ref=str(payload["account_ref"]),
            state_evidence_sha256=str(payload["state_evidence_sha256"]),
            proposal_evidence_sha256=str(
                payload["proposal_evidence_sha256"]
            ),
            proposal_action=Genc7Action(str(payload["proposal_action"])),
            proposal_source_bucket=Genc7SourceBucket(
                str(payload["proposal_source_bucket"])
            ),
            proposal_amount_usd=Decimal(
                str(payload["proposal_amount_usd"])
            ),
            evaluation_horizon_minutes=int(
                payload["evaluation_horizon_minutes"]
            ),
            initial_realized_capital_usd=Decimal(
                str(payload["initial_realized_capital_usd"])
            ),
            initial_realized_profit_usd=Decimal(
                str(payload["initial_realized_profit_usd"])
            ),
            initial_protected_floor_usd=Decimal(
                str(payload["initial_protected_floor_usd"])
            ),
            initial_base_capital_usd=Decimal(
                str(payload["initial_base_capital_usd"])
            ),
            initial_compound_capital_usd=Decimal(
                str(payload["initial_compound_capital_usd"])
            ),
            control_action=Genc7Action(str(payload["control_action"])),
            control_amount_usd=Decimal(str(payload["control_amount_usd"])),
            treatment_action=Genc7Action(str(payload["treatment_action"])),
            treatment_amount_usd=Decimal(
                str(payload["treatment_amount_usd"])
            ),
            blocker_codes=tuple(str(item) for item in blockers),
            giveback_amount_usd=Decimal(
                str(payload["giveback_amount_usd"])
            ),
            profit_retention_ratio=Decimal(
                str(payload["profit_retention_ratio"])
            ),
            floor_growth_rate=(
                None if floor_raw is None else Decimal(str(floor_raw))
            ),
            base_drawdown_usd=Decimal(
                str(payload["base_drawdown_usd"])
            ),
            compound_drawdown_usd=Decimal(
                str(payload["compound_drawdown_usd"])
            ),
            treatment_differs_from_control=_strict_bool(
                payload["treatment_differs_from_control"],
                "treatment_differs_from_control",
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "GEN-C7 store seal payload invalid"
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
            f"GEN-C7 store {name} must be bool"
        )
    return value
