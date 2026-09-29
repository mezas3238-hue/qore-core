"""Durable append-only evidence ledger for CE2I T08 OOS netting ablation.

A shadow decision is sealed before its outcomes can be appended. Every ledger
record binds to the previous chain SHA, so later outcomes cannot rewrite the
pre-outcome treatment policy. The store has no sizing, Risk, execution, LIVE or
real-capital authority.
"""

from __future__ import annotations

import hashlib
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
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingShadowEpoch,
)

_SCHEMA = "CIBO_PHASE20_T08_OOS_SHADOW_LEDGER_V1"
_GENESIS = "sha256:" + ("0" * 64)
_DECISION = "DECISION"
_OUTCOME = "OUTCOME"


class DurableT08OosShadowError(CiboCapitalManagementError):
    """T08 OOS shadow evidence cannot be trusted or updated safely."""


@dataclass(frozen=True, slots=True)
class T08ShadowDecisionSeal:
    epoch_id: str
    decision_at: datetime
    shadow_sealed_at: datetime
    baseline_selected_count: int
    treatment_selected_count: int
    treatment_gross_stop_risk_usd: Decimal
    treatment_netted_risk_usd: Decimal
    netting_credit_usd: Decimal
    risk_mapping_evidence_id: str
    correlation_evidence_id: str

    def __post_init__(self) -> None:
        if not self.epoch_id:
            raise DurableT08OosShadowError(
                "T08 shadow decision epoch_id is required"
            )
        _aware(self.decision_at, "T08 shadow decision_at")
        _aware(self.shadow_sealed_at, "T08 shadow shadow_sealed_at")
        if self.shadow_sealed_at < self.decision_at:
            raise DurableT08OosShadowError(
                "T08 shadow decision cannot seal before decision"
            )
        for name in (
            "baseline_selected_count",
            "treatment_selected_count",
        ):
            _non_negative_int(getattr(self, name), name)
        for name in (
            "treatment_gross_stop_risk_usd",
            "treatment_netted_risk_usd",
            "netting_credit_usd",
        ):
            _non_negative_decimal(getattr(self, name), name)
        if self.treatment_gross_stop_risk_usd <= 0:
            raise DurableT08OosShadowError(
                "T08 shadow gross stop risk must be positive"
            )
        if self.treatment_netted_risk_usd <= 0:
            raise DurableT08OosShadowError(
                "T08 shadow netted risk must be positive"
            )
        if (
            self.treatment_netted_risk_usd
            > self.treatment_gross_stop_risk_usd
        ):
            raise DurableT08OosShadowError(
                "T08 shadow netted risk cannot exceed gross stop risk"
            )
        if (
            self.treatment_gross_stop_risk_usd
            - self.treatment_netted_risk_usd
            != self.netting_credit_usd
        ):
            raise DurableT08OosShadowError(
                "T08 shadow decision netting-credit accounting mismatch"
            )
        if (
            self.netting_credit_usd
            / self.treatment_gross_stop_risk_usd
            > Decimal("0.50")
        ):
            raise DurableT08OosShadowError(
                "T08 shadow decision credit exceeds frozen 50% ceiling"
            )
        if not self.risk_mapping_evidence_id:
            raise DurableT08OosShadowError(
                "T08 shadow risk-mapping evidence id is required"
            )
        if not self.correlation_evidence_id:
            raise DurableT08OosShadowError(
                "T08 shadow correlation evidence id is required"
            )

    @property
    def decision_sha256(self) -> str:
        return "sha256:" + _sha256_json(_decision_payload(self))


@dataclass(frozen=True, slots=True)
class T08ShadowOutcomeSeal:
    epoch_id: str
    decision_sha256: str
    outcome_observed_at: datetime
    baseline_realized_net_pnl_usd: Decimal
    treatment_realized_net_pnl_usd: Decimal
    baseline_peak_loss_usd: Decimal
    treatment_peak_loss_usd: Decimal
    outcome_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.epoch_id:
            raise DurableT08OosShadowError(
                "T08 shadow outcome epoch_id is required"
            )
        if not _valid_sha(self.decision_sha256):
            raise DurableT08OosShadowError(
                "T08 shadow outcome decision SHA is invalid"
            )
        _aware(self.outcome_observed_at, "T08 shadow outcome_observed_at")
        for name in (
            "baseline_realized_net_pnl_usd",
            "treatment_realized_net_pnl_usd",
        ):
            _finite_decimal(getattr(self, name), name)
        for name in (
            "baseline_peak_loss_usd",
            "treatment_peak_loss_usd",
        ):
            _non_negative_decimal(getattr(self, name), name)
        if (
            not self.outcome_evidence_ids
            or len(self.outcome_evidence_ids)
            != len(set(self.outcome_evidence_ids))
            or any(not item for item in self.outcome_evidence_ids)
        ):
            raise DurableT08OosShadowError(
                "T08 shadow outcome evidence ids must be unique/non-empty"
            )


@dataclass(frozen=True, slots=True)
class T08ShadowLedgerRecord:
    sequence: int
    kind: str
    epoch_id: str
    payload_json: str
    payload_sha256: str
    previous_chain_sha256: str
    chain_sha256: str

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise DurableT08OosShadowError(
                "T08 shadow ledger sequence must be positive"
            )
        if self.kind not in {_DECISION, _OUTCOME}:
            raise DurableT08OosShadowError(
                "T08 shadow ledger record kind is invalid"
            )
        if not self.epoch_id:
            raise DurableT08OosShadowError(
                "T08 shadow ledger record epoch id is required"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            if not _valid_sha(getattr(self, name)):
                raise DurableT08OosShadowError(
                    f"T08 shadow ledger {name} is invalid"
                )
        try:
            payload = json.loads(self.payload_json)
        except json.JSONDecodeError as error:
            raise DurableT08OosShadowError(
                "T08 shadow ledger payload JSON invalid"
            ) from error
        if not isinstance(payload, dict):
            raise DurableT08OosShadowError(
                "T08 shadow ledger payload must be object"
            )
        expected_payload = "sha256:" + hashlib.sha256(
            self.payload_json.encode()
        ).hexdigest()
        if self.payload_sha256 != expected_payload:
            raise DurableT08OosShadowError(
                "T08 shadow ledger payload SHA mismatch"
            )
        expected_chain = _next_chain(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            kind=self.kind,
            epoch_id=self.epoch_id,
            payload_sha256=self.payload_sha256,
        )
        if self.chain_sha256 != expected_chain:
            raise DurableT08OosShadowError(
                "T08 shadow ledger chain SHA mismatch"
            )


@dataclass(frozen=True, slots=True)
class VersionedT08OosShadowBook:
    generation: int
    records: tuple[T08ShadowLedgerRecord, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurableT08OosShadowError(
                "T08 shadow generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise DurableT08OosShadowError(
                "T08 shadow generation/record count drift"
            )
        previous = _GENESIS
        seen_decisions: dict[str, str] = {}
        seen_outcomes: set[str] = set()
        for expected_sequence, record in enumerate(self.records, start=1):
            if record.sequence != expected_sequence:
                raise DurableT08OosShadowError(
                    "T08 shadow ledger sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise DurableT08OosShadowError(
                    "T08 shadow ledger previous chain mismatch"
                )
            if record.kind == _DECISION:
                if record.epoch_id in seen_decisions:
                    raise DurableT08OosShadowError(
                        "T08 shadow duplicate decision epoch"
                    )
                decision = _decision_from_json(record.payload_json)
                if decision.epoch_id != record.epoch_id:
                    raise DurableT08OosShadowError(
                        "T08 shadow decision epoch binding mismatch"
                    )
                seen_decisions[record.epoch_id] = decision.decision_sha256
            else:
                if record.epoch_id in seen_outcomes:
                    raise DurableT08OosShadowError(
                        "T08 shadow duplicate outcome epoch"
                    )
                outcome = _outcome_from_json(record.payload_json)
                expected_sha = seen_decisions.get(record.epoch_id)
                if expected_sha is None:
                    raise DurableT08OosShadowError(
                        "T08 shadow outcome precedes decision seal"
                    )
                if outcome.decision_sha256 != expected_sha:
                    raise DurableT08OosShadowError(
                        "T08 shadow outcome decision binding mismatch"
                    )
                decision = self.decision_for_epoch(record.epoch_id)
                if outcome.outcome_observed_at <= decision.shadow_sealed_at:
                    raise DurableT08OosShadowError(
                        "T08 shadow outcome must postdate decision seal"
                    )
                seen_outcomes.add(record.epoch_id)
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    @property
    def decisions(self) -> tuple[T08ShadowDecisionSeal, ...]:
        return tuple(
            _decision_from_json(item.payload_json)
            for item in self.records
            if item.kind == _DECISION
        )

    @property
    def outcomes(self) -> tuple[T08ShadowOutcomeSeal, ...]:
        return tuple(
            _outcome_from_json(item.payload_json)
            for item in self.records
            if item.kind == _OUTCOME
        )

    def decision_for_epoch(self, epoch_id: str) -> T08ShadowDecisionSeal:
        for item in self.records:
            if item.kind == _DECISION and item.epoch_id == epoch_id:
                return _decision_from_json(item.payload_json)
        raise DurableT08OosShadowError(
            "T08 shadow decision epoch not found"
        )

    def complete_epochs(self) -> tuple[T08NettingShadowEpoch, ...]:
        outcomes = {item.epoch_id: item for item in self.outcomes}
        result: list[T08NettingShadowEpoch] = []
        for decision in self.decisions:
            outcome = outcomes.get(decision.epoch_id)
            if outcome is None:
                continue
            result.append(
                T08NettingShadowEpoch(
                    epoch_id=decision.epoch_id,
                    decision_at=decision.decision_at,
                    shadow_sealed_at=decision.shadow_sealed_at,
                    outcome_observed_at=outcome.outcome_observed_at,
                    baseline_selected_count=decision.baseline_selected_count,
                    treatment_selected_count=decision.treatment_selected_count,
                    baseline_realized_net_pnl_usd=(
                        outcome.baseline_realized_net_pnl_usd
                    ),
                    treatment_realized_net_pnl_usd=(
                        outcome.treatment_realized_net_pnl_usd
                    ),
                    baseline_peak_loss_usd=outcome.baseline_peak_loss_usd,
                    treatment_peak_loss_usd=outcome.treatment_peak_loss_usd,
                    treatment_gross_stop_risk_usd=(
                        decision.treatment_gross_stop_risk_usd
                    ),
                    treatment_netted_risk_usd=(
                        decision.treatment_netted_risk_usd
                    ),
                    netting_credit_usd=decision.netting_credit_usd,
                    risk_mapping_evidence_id=(
                        decision.risk_mapping_evidence_id
                    ),
                    correlation_evidence_id=(
                        decision.correlation_evidence_id
                    ),
                    outcome_evidence_ids=outcome.outcome_evidence_ids,
                )
            )
        return tuple(sorted(result, key=lambda item: item.decision_at))


class DurableT08OosShadowStore:
    """Atomic CAS store for the T08 append-only shadow ledger."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()

    def load(self) -> VersionedT08OosShadowBook:
        with self._lock:
            if not self.path.exists():
                return VersionedT08OosShadowBook(
                    generation=0,
                    records=(),
                )
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise DurableT08OosShadowError(
                    "T08 shadow store unreadable"
                ) from error
            return _book_from_payload(payload)

    def append_decision(
        self,
        decision: T08ShadowDecisionSeal,
        *,
        expected_generation: int,
    ) -> VersionedT08OosShadowBook:
        if not isinstance(decision, T08ShadowDecisionSeal):
            raise DurableT08OosShadowError(
                "T08 shadow append_decision requires canonical decision"
            )
        with self._lock:
            current = self.load()
            _generation(current, expected_generation)
            existing = tuple(
                item
                for item in current.decisions
                if item.epoch_id == decision.epoch_id
            )
            if existing:
                if existing[0] == decision:
                    return current
                raise DurableT08OosShadowError(
                    "T08 shadow conflicting decision epoch"
                )
            record = _record(
                sequence=current.generation + 1,
                kind=_DECISION,
                epoch_id=decision.epoch_id,
                payload=_decision_payload(decision),
                previous=current.chain_sha256,
            )
            updated = VersionedT08OosShadowBook(
                generation=current.generation + 1,
                records=current.records + (record,),
            )
            self._write(updated)
            return updated

    def append_outcome(
        self,
        outcome: T08ShadowOutcomeSeal,
        *,
        expected_generation: int,
    ) -> VersionedT08OosShadowBook:
        if not isinstance(outcome, T08ShadowOutcomeSeal):
            raise DurableT08OosShadowError(
                "T08 shadow append_outcome requires canonical outcome"
            )
        with self._lock:
            current = self.load()
            _generation(current, expected_generation)
            decision = current.decision_for_epoch(outcome.epoch_id)
            if outcome.decision_sha256 != decision.decision_sha256:
                raise DurableT08OosShadowError(
                    "T08 shadow outcome decision SHA mismatch"
                )
            if outcome.outcome_observed_at <= decision.shadow_sealed_at:
                raise DurableT08OosShadowError(
                    "T08 shadow outcome must postdate decision seal"
                )
            existing = tuple(
                item
                for item in current.outcomes
                if item.epoch_id == outcome.epoch_id
            )
            if existing:
                if existing[0] == outcome:
                    return current
                raise DurableT08OosShadowError(
                    "T08 shadow conflicting outcome epoch"
                )
            record = _record(
                sequence=current.generation + 1,
                kind=_OUTCOME,
                epoch_id=outcome.epoch_id,
                payload=_outcome_payload(outcome),
                previous=current.chain_sha256,
            )
            updated = VersionedT08OosShadowBook(
                generation=current.generation + 1,
                records=current.records + (record,),
            )
            self._write(updated)
            return updated

    def _write(self, book: VersionedT08OosShadowBook) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + ".tmp")
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "chain_sha256": book.chain_sha256,
            "records": [
                {
                    "sequence": item.sequence,
                    "kind": item.kind,
                    "epoch_id": item.epoch_id,
                    "payload_json": item.payload_json,
                    "payload_sha256": item.payload_sha256,
                    "previous_chain_sha256": item.previous_chain_sha256,
                    "chain_sha256": item.chain_sha256,
                }
                for item in book.records
            ],
        }
        try:
            temp.write_text(
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(temp, self.path)
        finally:
            if temp.exists():
                temp.unlink()


def _record(
    *,
    sequence: int,
    kind: str,
    epoch_id: str,
    payload: dict[str, object],
    previous: str,
) -> T08ShadowLedgerRecord:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload_sha = "sha256:" + hashlib.sha256(payload_json.encode()).hexdigest()
    return T08ShadowLedgerRecord(
        sequence=sequence,
        kind=kind,
        epoch_id=epoch_id,
        payload_json=payload_json,
        payload_sha256=payload_sha,
        previous_chain_sha256=previous,
        chain_sha256=_next_chain(
            previous=previous,
            sequence=sequence,
            kind=kind,
            epoch_id=epoch_id,
            payload_sha256=payload_sha,
        ),
    )


def _next_chain(
    *,
    previous: str,
    sequence: int,
    kind: str,
    epoch_id: str,
    payload_sha256: str,
) -> str:
    material = (
        f"{previous}|{sequence}|{kind}|{epoch_id}|{payload_sha256}"
    ).encode()
    return "sha256:" + hashlib.sha256(material).hexdigest()


def _decision_payload(
    item: T08ShadowDecisionSeal,
) -> dict[str, object]:
    return {
        "epoch_id": item.epoch_id,
        "decision_at": item.decision_at.isoformat(),
        "shadow_sealed_at": item.shadow_sealed_at.isoformat(),
        "baseline_selected_count": item.baseline_selected_count,
        "treatment_selected_count": item.treatment_selected_count,
        "treatment_gross_stop_risk_usd": str(
            item.treatment_gross_stop_risk_usd
        ),
        "treatment_netted_risk_usd": str(
            item.treatment_netted_risk_usd
        ),
        "netting_credit_usd": str(item.netting_credit_usd),
        "risk_mapping_evidence_id": item.risk_mapping_evidence_id,
        "correlation_evidence_id": item.correlation_evidence_id,
    }


def _outcome_payload(
    item: T08ShadowOutcomeSeal,
) -> dict[str, object]:
    return {
        "epoch_id": item.epoch_id,
        "decision_sha256": item.decision_sha256,
        "outcome_observed_at": item.outcome_observed_at.isoformat(),
        "baseline_realized_net_pnl_usd": str(
            item.baseline_realized_net_pnl_usd
        ),
        "treatment_realized_net_pnl_usd": str(
            item.treatment_realized_net_pnl_usd
        ),
        "baseline_peak_loss_usd": str(item.baseline_peak_loss_usd),
        "treatment_peak_loss_usd": str(item.treatment_peak_loss_usd),
        "outcome_evidence_ids": list(item.outcome_evidence_ids),
    }


def _decision_from_json(value: str) -> T08ShadowDecisionSeal:
    payload = _object(value, "decision")
    try:
        return T08ShadowDecisionSeal(
            epoch_id=str(payload["epoch_id"]),
            decision_at=datetime.fromisoformat(str(payload["decision_at"])),
            shadow_sealed_at=datetime.fromisoformat(
                str(payload["shadow_sealed_at"])
            ),
            baseline_selected_count=int(
                str(payload["baseline_selected_count"])
            ),
            treatment_selected_count=int(
                str(payload["treatment_selected_count"])
            ),
            treatment_gross_stop_risk_usd=_decimal(
                payload["treatment_gross_stop_risk_usd"]
            ),
            treatment_netted_risk_usd=_decimal(
                payload["treatment_netted_risk_usd"]
            ),
            netting_credit_usd=_decimal(payload["netting_credit_usd"]),
            risk_mapping_evidence_id=str(
                payload["risk_mapping_evidence_id"]
            ),
            correlation_evidence_id=str(
                payload["correlation_evidence_id"]
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DurableT08OosShadowError(
            "T08 shadow decision payload invalid"
        ) from error


def _outcome_from_json(value: str) -> T08ShadowOutcomeSeal:
    payload = _object(value, "outcome")
    raw_refs = payload.get("outcome_evidence_ids")
    if not isinstance(raw_refs, list):
        raise DurableT08OosShadowError(
            "T08 shadow outcome evidence ids must be list"
        )
    try:
        return T08ShadowOutcomeSeal(
            epoch_id=str(payload["epoch_id"]),
            decision_sha256=str(payload["decision_sha256"]),
            outcome_observed_at=datetime.fromisoformat(
                str(payload["outcome_observed_at"])
            ),
            baseline_realized_net_pnl_usd=_decimal(
                payload["baseline_realized_net_pnl_usd"]
            ),
            treatment_realized_net_pnl_usd=_decimal(
                payload["treatment_realized_net_pnl_usd"]
            ),
            baseline_peak_loss_usd=_decimal(
                payload["baseline_peak_loss_usd"]
            ),
            treatment_peak_loss_usd=_decimal(
                payload["treatment_peak_loss_usd"]
            ),
            outcome_evidence_ids=tuple(str(item) for item in raw_refs),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DurableT08OosShadowError(
            "T08 shadow outcome payload invalid"
        ) from error


def _book_from_payload(payload: object) -> VersionedT08OosShadowBook:
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        raise DurableT08OosShadowError(
            "T08 shadow store schema mismatch"
        )
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        raise DurableT08OosShadowError(
            "T08 shadow store records must be list"
        )
    records: list[T08ShadowLedgerRecord] = []
    try:
        for row in raw_records:
            if not isinstance(row, dict):
                raise DurableT08OosShadowError(
                    "T08 shadow store record must be object"
                )
            records.append(
                T08ShadowLedgerRecord(
                    sequence=int(row["sequence"]),
                    kind=str(row["kind"]),
                    epoch_id=str(row["epoch_id"]),
                    payload_json=str(row["payload_json"]),
                    payload_sha256=str(row["payload_sha256"]),
                    previous_chain_sha256=str(
                        row["previous_chain_sha256"]
                    ),
                    chain_sha256=str(row["chain_sha256"]),
                )
            )
        generation = int(payload["generation"])
    except (KeyError, TypeError, ValueError) as error:
        raise DurableT08OosShadowError(
            "T08 shadow store payload invalid"
        ) from error
    book = VersionedT08OosShadowBook(
        generation=generation,
        records=tuple(records),
    )
    if payload.get("chain_sha256") != book.chain_sha256:
        raise DurableT08OosShadowError(
            "T08 shadow store terminal chain mismatch"
        )
    return book


def _object(value: str, name: str) -> dict[str, object]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise DurableT08OosShadowError(
            f"T08 shadow {name} JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise DurableT08OosShadowError(
            f"T08 shadow {name} payload must be object"
        )
    return payload


def _generation(
    book: VersionedT08OosShadowBook,
    expected: int,
) -> None:
    if book.generation != expected:
        raise DurableT08OosShadowError(
            "T08 shadow evidence generation conflict"
        )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _valid_sha(value: str) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise DurableT08OosShadowError(
            "T08 shadow decimal field invalid"
        ) from error
    if not result.is_finite():
        raise DurableT08OosShadowError(
            "T08 shadow decimal field must be finite"
        )
    return result


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DurableT08OosShadowError(
            f"{name} must be timezone-aware"
        )


def _finite_decimal(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise DurableT08OosShadowError(
            f"T08 shadow {name} must be finite Decimal"
        )


def _non_negative_decimal(value: Decimal, name: str) -> None:
    _finite_decimal(value, name)
    if value < 0:
        raise DurableT08OosShadowError(
            f"T08 shadow {name} must be non-negative"
        )


def _non_negative_int(value: int, name: str) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise DurableT08OosShadowError(
            f"T08 shadow {name} must be non-negative int"
        )
