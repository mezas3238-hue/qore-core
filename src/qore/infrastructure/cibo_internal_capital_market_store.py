"""Durable pre-outcome store for GEN-C6 Internal Capital Market shadow.

Each record seals both the immutable CapitalScarcityEvent and its control /
treatment decision before any terminal outcome may be joined.

Append-only, SHA-256 hash chained, generation-CAS guarded, cross-process writer
locked and restart persistent. Research-only; no runtime capital authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_internal_capital_market import (
    GENC6_MARKET_ID,
    GENC6_POLICY_FROZEN_AT,
    GENC6_POLICY_ID,
    CapitalScarcityEvent,
    Genc6InternalCapitalMarketDecision,
    genc6_policy_sha256,
    genc6_portfolio_state_sha256,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    marginal_capital_utility_evidence_sha256,
)

_SCHEMA = "QORE_CIBO_GENC6_INTERNAL_CAPITAL_MARKET_STORE_V1"
_GENESIS = "sha256:" + ("0" * 64)


@dataclass(frozen=True, slots=True)
class Genc6InternalCapitalMarketSeal:
    decision_id: str
    scarcity_event_id: str
    decision_at: datetime
    sealed_at: datetime
    event_sha256: str
    decision_sha256: str
    policy_sha256: str
    account_provider_key: str
    account_ref: str
    candidate_set_sha256: str
    portfolio_state_sha256: str
    t19_ledger_sha256: str
    event_json: str
    decision_json: str

    def __post_init__(self) -> None:
        if not self.decision_id or not self.scarcity_event_id:
            raise CiboCompoundCapitalError(
                "GEN-C6 store decision/scarcity identity is required"
            )
        _aware(self.decision_at, "decision_at")
        _aware(self.sealed_at, "sealed_at")
        if self.decision_at < GENC6_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C6 store cannot seal pre-freeze decision"
            )
        if self.sealed_at < self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C6 store seal cannot predate decision"
            )
        for name in (
            "event_sha256",
            "decision_sha256",
            "policy_sha256",
            "candidate_set_sha256",
            "portfolio_state_sha256",
            "t19_ledger_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.policy_sha256 != genc6_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C6 store policy digest drift"
            )
        if not self.account_provider_key or not self.account_ref:
            raise CiboCompoundCapitalError(
                "GEN-C6 store account identity is required"
            )
        _verify_json_digest(
            self.event_json,
            self.event_sha256,
            "event",
        )
        _verify_json_digest(
            self.decision_json,
            self.decision_sha256,
            "decision",
        )
        event_payload = _json_object(self.event_json, "event")
        decision_payload = _json_object(self.decision_json, "decision")
        if event_payload.get("event_id") != self.scarcity_event_id:
            raise CiboCompoundCapitalError(
                "GEN-C6 store event identity binding drift"
            )
        if decision_payload.get("decision_id") != self.decision_id:
            raise CiboCompoundCapitalError(
                "GEN-C6 store decision identity binding drift"
            )
        if decision_payload.get("scarcity_event_id") != self.scarcity_event_id:
            raise CiboCompoundCapitalError(
                "GEN-C6 store decision/event binding drift"
            )
        if decision_payload.get("policy_id") != GENC6_POLICY_ID:
            raise CiboCompoundCapitalError(
                "GEN-C6 store policy identity drift"
            )
        if decision_payload.get("market_id") != GENC6_MARKET_ID:
            raise CiboCompoundCapitalError(
                "GEN-C6 store market identity drift"
            )
        if decision_payload.get("policy_sha256") != self.policy_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C6 store decision policy digest binding drift"
            )
        if (
            decision_payload.get("candidate_set_sha256")
            != self.candidate_set_sha256
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 store candidate-set binding drift"
            )
        if (
            decision_payload.get("portfolio_state_sha256")
            != self.portfolio_state_sha256
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 store portfolio-state binding drift"
            )
        if (
            decision_payload.get("t19_ledger_sha256")
            != self.t19_ledger_sha256
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 store T19 binding drift"
            )
        if decision_payload.get("outcome_present_at_seal") is not False:
            raise CiboCompoundCapitalError(
                "GEN-C6 store decision contains outcome at seal"
            )


@dataclass(frozen=True, slots=True)
class Genc6InternalCapitalMarketRecord:
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
                "GEN-C6 store sequence must be positive int"
            )
        if not self.decision_id:
            raise CiboCompoundCapitalError(
                "GEN-C6 store record decision id is required"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            _sha(getattr(self, name), name)
        expected_payload = _digest(self.payload_json)
        if self.payload_sha256 != expected_payload:
            raise CiboCompoundCapitalError(
                "GEN-C6 store record payload digest mismatch"
            )
        expected_chain = _next_chain(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            decision_id=self.decision_id,
            payload_sha256=self.payload_sha256,
        )
        if self.chain_sha256 != expected_chain:
            raise CiboCompoundCapitalError(
                "GEN-C6 store record chain digest mismatch"
            )
        _seal_from_json(self.payload_json)


@dataclass(frozen=True, slots=True)
class VersionedGenc6InternalCapitalMarketBook:
    generation: int
    records: tuple[Genc6InternalCapitalMarketRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 store generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise CiboCompoundCapitalError(
                "GEN-C6 store generation/record count drift"
            )
        ids = tuple(item.decision_id for item in self.records)
        if len(ids) != len(set(ids)):
            raise CiboCompoundCapitalError(
                "GEN-C6 store decision ids must be unique"
            )
        event_ids = tuple(
            _seal_from_json(item.payload_json).scarcity_event_id
            for item in self.records
        )
        if len(event_ids) != len(set(event_ids)):
            raise CiboCompoundCapitalError(
                "GEN-C6 store scarcity event ids must be unique"
            )
        previous = _GENESIS
        for expected_sequence, record in enumerate(self.records, start=1):
            if record.sequence != expected_sequence:
                raise CiboCompoundCapitalError(
                    "GEN-C6 store record sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise CiboCompoundCapitalError(
                    "GEN-C6 store previous-chain drift"
                )
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    def seal_for_decision(
        self,
        decision_id: str,
    ) -> Genc6InternalCapitalMarketSeal | None:
        rows = tuple(
            _seal_from_json(item.payload_json)
            for item in self.records
            if item.decision_id == decision_id
        )
        if len(rows) > 1:
            raise CiboCompoundCapitalError(
                "GEN-C6 store duplicate decision id"
            )
        return rows[0] if rows else None


class DurableGenc6InternalCapitalMarketStore:
    """Atomic append-only GEN-C6 scarcity-event/decision store."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise CiboCompoundCapitalError(
                "GEN-C6 store path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(
            f".{path.name}.writer-lock"
        )
        self._lock = RLock()

    def load(self) -> VersionedGenc6InternalCapitalMarketBook:
        with self._lock:
            return self._load_unlocked()

    def seal(
        self,
        *,
        event: CapitalScarcityEvent,
        decision: Genc6InternalCapitalMarketDecision,
        sealed_at: datetime,
        expected_generation: int,
    ) -> VersionedGenc6InternalCapitalMarketBook:
        if not isinstance(event, CapitalScarcityEvent):
            raise CiboCompoundCapitalError(
                "GEN-C6 store requires canonical scarcity event"
            )
        if not isinstance(decision, Genc6InternalCapitalMarketDecision):
            raise CiboCompoundCapitalError(
                "GEN-C6 store requires canonical market decision"
            )
        _aware(sealed_at, "sealed_at")
        _expected_generation(expected_generation)
        _validate_event_decision_binding(event=event, decision=decision)
        seal = _seal(
            event=event,
            decision=decision,
            sealed_at=sealed_at,
        )

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise CiboCompoundCapitalError(
                        "GEN-C6 store generation conflict"
                    )
                previous = current.seal_for_decision(decision.decision_id)
                if previous is not None:
                    if previous == seal:
                        return current
                    raise CiboCompoundCapitalError(
                        "GEN-C6 conflicting decision rewrite"
                    )
                if any(
                    _seal_from_json(item.payload_json).scarcity_event_id
                    == event.event_id
                    for item in current.records
                ):
                    raise CiboCompoundCapitalError(
                        "GEN-C6 scarcity event already sealed"
                    )

                payload_json = json.dumps(
                    _seal_payload(seal),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                payload_sha = _digest(payload_json)
                record = Genc6InternalCapitalMarketRecord(
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
                updated = VersionedGenc6InternalCapitalMarketBook(
                    generation=current.generation + 1,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedGenc6InternalCapitalMarketBook:
        if not self._path.exists():
            return VersionedGenc6InternalCapitalMarketBook(generation=0)
        try:
            payload = json.loads(
                self._path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C6 store is unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("schema") != _SCHEMA
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 store schema mismatch"
            )
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise CiboCompoundCapitalError(
                "GEN-C6 store records must be list"
            )
        try:
            records = tuple(
                Genc6InternalCapitalMarketRecord(
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
                raise TypeError("GEN-C6 record must be object")
            generation = int(payload["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise CiboCompoundCapitalError(
                "GEN-C6 store payload invalid"
            ) from error
        book = VersionedGenc6InternalCapitalMarketBook(
            generation=generation,
            records=records,
        )
        if payload.get("chain_sha256") != book.chain_sha256:
            raise CiboCompoundCapitalError(
                "GEN-C6 store terminal chain mismatch"
            )
        return book

    def _write_unlocked(
        self,
        book: VersionedGenc6InternalCapitalMarketBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "market_id": GENC6_MARKET_ID,
            "policy_id": GENC6_POLICY_ID,
            "policy_sha256": genc6_policy_sha256(),
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
                "GEN-C6 store write failed"
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
                "GEN-C6 store writer lock already held"
            ) from error
        except OSError as error:
            raise CiboCompoundCapitalError(
                "GEN-C6 store writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise CiboCompoundCapitalError(
                "GEN-C6 store writer lock release failed"
            ) from error


def _validate_event_decision_binding(
    *,
    event: CapitalScarcityEvent,
    decision: Genc6InternalCapitalMarketDecision,
) -> None:
    if decision.scarcity_event_id != event.event_id:
        raise CiboCompoundCapitalError(
            "GEN-C6 store decision/scarcity event mismatch"
        )
    if decision.decision_at != event.decision_at:
        raise CiboCompoundCapitalError(
            "GEN-C6 store decision/event time mismatch"
        )
    if (
        decision.account_provider_key
        != event.account_identity.provider_key
        or decision.account_ref != event.account_identity.account_ref
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 store decision/event account mismatch"
        )
    if decision.candidate_set_sha256 != event.candidate_set_sha256:
        raise CiboCompoundCapitalError(
            "GEN-C6 store decision/event candidate-set mismatch"
        )
    if decision.portfolio_state_sha256 != genc6_portfolio_state_sha256(
        event.portfolio_state
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 store decision/event portfolio-state mismatch"
        )
    if (
        decision.t19_ledger_sha256
        != event.portfolio_state.t19_ledger_sha256
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 store decision/event T19 mismatch"
        )
    expected_c4 = tuple(
        marginal_capital_utility_evidence_sha256(
            item.marginal_evidence
        )
        for item in sorted(event.candidates, key=lambda row: row.candidate_id)
    )
    if decision.candidate_evidence_sha256s != expected_c4:
        raise CiboCompoundCapitalError(
            "GEN-C6 store decision/event GEN-C4 bindings drift"
        )
    expected_c5 = tuple(
        item.genc5_seal.decision_sha256
        for item in sorted(event.candidates, key=lambda row: row.candidate_id)
    )
    if decision.genc5_decision_sha256s != expected_c5:
        raise CiboCompoundCapitalError(
            "GEN-C6 store decision/event GEN-C5 bindings drift"
        )


def _seal(
    *,
    event: CapitalScarcityEvent,
    decision: Genc6InternalCapitalMarketDecision,
    sealed_at: datetime,
) -> Genc6InternalCapitalMarketSeal:
    event_json = _event_json(event)
    decision_json = _decision_json(decision)
    return Genc6InternalCapitalMarketSeal(
        decision_id=decision.decision_id,
        scarcity_event_id=event.event_id,
        decision_at=decision.decision_at,
        sealed_at=sealed_at,
        event_sha256=_digest(event_json),
        decision_sha256=_digest(decision_json),
        policy_sha256=decision.policy_sha256,
        account_provider_key=decision.account_provider_key,
        account_ref=decision.account_ref,
        candidate_set_sha256=decision.candidate_set_sha256,
        portfolio_state_sha256=decision.portfolio_state_sha256,
        t19_ledger_sha256=decision.t19_ledger_sha256,
        event_json=event_json,
        decision_json=decision_json,
    )


def _event_json(event: CapitalScarcityEvent) -> str:
    payload = {
        "event_id": event.event_id,
        "account": {
            "provider_key": event.account_identity.provider_key,
            "account_ref": event.account_identity.account_ref,
        },
        "decision_at": event.decision_at.isoformat(),
        "portfolio_state_sha256": genc6_portfolio_state_sha256(
            event.portfolio_state
        ),
        "t19_ledger_sha256": event.portfolio_state.t19_ledger_sha256,
        "candidate_set_sha256": event.candidate_set_sha256,
        "candidates": [
            {
                "candidate_id": item.candidate_id,
                "trader_id": item.trader_id.value,
                "qore_symbol": item.qore_symbol,
                "provider_symbol": item.provider_symbol,
                "signal_fingerprint": item.signal_fingerprint,
                "decision_at": item.decision_at.isoformat(),
                "valid_from": item.valid_from.isoformat(),
                "valid_until": item.valid_until.isoformat(),
                "technical_valid": item.technical_valid,
                "cancelled": item.cancelled,
                "marginal_unit_index": item.marginal_unit_index,
                "concentration_group": item.concentration_group,
                "requested_capital_usd": str(item.requested_capital_usd),
                "stop_risk_usd": str(item.stop_risk_usd),
                "margin_usd": str(item.margin_usd),
                "concentration_risk_usd": str(
                    item.concentration_risk_usd
                ),
                "marginal_evidence_sha256": (
                    marginal_capital_utility_evidence_sha256(
                        item.marginal_evidence
                    )
                ),
                "genc5_decision_sha256": item.genc5_seal.decision_sha256,
                "provider_feasible": item.provider_feasible,
                "provider_feasibility_evidence_sha256": (
                    item.provider_feasibility_evidence_sha256
                ),
                "facts": [
                    {
                        "fact_id": fact.fact_id,
                        "kind": fact.kind.value,
                        "value": str(fact.value),
                        "direction": fact.direction.value,
                        "evidence_sha256": fact.evidence_sha256,
                        "produced_at": fact.produced_at.isoformat(),
                        "observed_at": fact.observed_at.isoformat(),
                        "source": fact.source,
                        "policy_version": fact.policy_version,
                        "calibration_lineage": fact.calibration_lineage,
                        "use": fact.use.value,
                        "model_identity": fact.model_identity,
                        "calibrated": fact.calibrated,
                        "oos_validated": fact.oos_validated,
                    }
                    for fact in item.comparable_facts
                ],
            }
            for item in sorted(
                event.candidates,
                key=lambda row: row.candidate_id,
            )
        ],
        "reserve": {
            "alternative_id": event.reserve_alternative.alternative_id,
            "evidence_facts": [
                {
                    "fact_id": fact.fact_id,
                    "kind": fact.kind.value,
                    "value": str(fact.value),
                    "direction": fact.direction.value,
                    "evidence_sha256": fact.evidence_sha256,
                    "produced_at": fact.produced_at.isoformat(),
                    "observed_at": fact.observed_at.isoformat(),
                    "source": fact.source,
                    "policy_version": fact.policy_version,
                    "calibration_lineage": fact.calibration_lineage,
                    "use": fact.use.value,
                    "model_identity": fact.model_identity,
                    "calibrated": fact.calibrated,
                    "oos_validated": fact.oos_validated,
                }
                for fact in event.reserve_alternative.evidence_facts
            ],
        },
        "simultaneously_valid_count": event.simultaneously_valid_count,
        "eligible_candidate_count": event.eligible_candidate_count,
        "available_capital_usd": str(event.available_capital_usd),
        "total_requested_capital_usd": str(
            event.total_requested_capital_usd
        ),
        "capital_shortfall_usd": str(event.capital_shortfall_usd),
        "mutually_fundable_candidate_count": (
            event.mutually_fundable_candidate_count
        ),
        "competition_intensity": str(event.competition_intensity),
        "true_scarcity": event.true_scarcity,
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )


def _decision_json(
    decision: Genc6InternalCapitalMarketDecision,
) -> str:
    payload = {
        "market_id": decision.market_id,
        "policy_id": decision.policy_id,
        "policy_sha256": decision.policy_sha256,
        "policy_frozen_at": decision.policy_frozen_at.isoformat(),
        "decision_id": decision.decision_id,
        "scarcity_event_id": decision.scarcity_event_id,
        "decision_at": decision.decision_at.isoformat(),
        "account_provider_key": decision.account_provider_key,
        "account_ref": decision.account_ref,
        "candidate_set_sha256": decision.candidate_set_sha256,
        "candidate_evidence_sha256s": list(
            decision.candidate_evidence_sha256s
        ),
        "genc5_decision_sha256s": list(
            decision.genc5_decision_sha256s
        ),
        "portfolio_state_sha256": decision.portfolio_state_sha256,
        "t19_ledger_sha256": decision.t19_ledger_sha256,
        "available_capital_usd": str(decision.available_capital_usd),
        "true_scarcity": decision.true_scarcity,
        "control_action": decision.control_action.value,
        "control_candidate_id": decision.control_candidate_id,
        "control_amount_usd": str(decision.control_amount_usd),
        "treatment_action": decision.treatment_action.value,
        "treatment_candidate_id": decision.treatment_candidate_id,
        "treatment_amount_usd": str(decision.treatment_amount_usd),
        "reserve_amount_usd": str(decision.reserve_amount_usd),
        "active_comparable_dimensions": [
            item.value for item in decision.active_comparable_dimensions
        ],
        "control_reason": decision.control_reason,
        "treatment_reason": decision.treatment_reason,
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
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )


def _seal_payload(
    seal: Genc6InternalCapitalMarketSeal,
) -> dict[str, object]:
    return {
        "decision_id": seal.decision_id,
        "scarcity_event_id": seal.scarcity_event_id,
        "decision_at": seal.decision_at.isoformat(),
        "sealed_at": seal.sealed_at.isoformat(),
        "event_sha256": seal.event_sha256,
        "decision_sha256": seal.decision_sha256,
        "policy_sha256": seal.policy_sha256,
        "account_provider_key": seal.account_provider_key,
        "account_ref": seal.account_ref,
        "candidate_set_sha256": seal.candidate_set_sha256,
        "portfolio_state_sha256": seal.portfolio_state_sha256,
        "t19_ledger_sha256": seal.t19_ledger_sha256,
        "event_json": seal.event_json,
        "decision_json": seal.decision_json,
    }


def _seal_from_json(value: str) -> Genc6InternalCapitalMarketSeal:
    payload = _json_object(value, "seal")
    try:
        return Genc6InternalCapitalMarketSeal(
            decision_id=str(payload["decision_id"]),
            scarcity_event_id=str(payload["scarcity_event_id"]),
            decision_at=datetime.fromisoformat(
                str(payload["decision_at"])
            ),
            sealed_at=datetime.fromisoformat(str(payload["sealed_at"])),
            event_sha256=str(payload["event_sha256"]),
            decision_sha256=str(payload["decision_sha256"]),
            policy_sha256=str(payload["policy_sha256"]),
            account_provider_key=str(
                payload["account_provider_key"]
            ),
            account_ref=str(payload["account_ref"]),
            candidate_set_sha256=str(payload["candidate_set_sha256"]),
            portfolio_state_sha256=str(
                payload["portfolio_state_sha256"]
            ),
            t19_ledger_sha256=str(payload["t19_ledger_sha256"]),
            event_json=str(payload["event_json"]),
            decision_json=str(payload["decision_json"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CiboCompoundCapitalError):
            raise
        raise CiboCompoundCapitalError(
            "GEN-C6 store seal payload invalid"
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


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def _verify_json_digest(
    value: str,
    expected: str,
    label: str,
) -> None:
    if _digest(value) != expected:
        raise CiboCompoundCapitalError(
            f"GEN-C6 store {label} digest mismatch"
        )


def _json_object(value: str, label: str) -> dict[str, object]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCompoundCapitalError(
            f"GEN-C6 store {label} JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            f"GEN-C6 store {label} payload must be object"
        )
    return payload


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C6 store {name} must be canonical SHA-256"
        )


def _expected_generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 store expected generation must be non-negative int"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C6 store {name} must be timezone-aware"
        )
