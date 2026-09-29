"""Durable pre-outcome ledger for the CE2I T12 shadow ablation.

The ledger seals the preregistered T12 treatment/control comparison only after
the canonical forward decision and baseline policy record already exist, and
strictly before any outcome for that decision is present.

Persistence is append-only, hash chained, generation-CAS guarded and protected
by a cross-process writer lock. The store is research-only and has no sizing,
Risk, execution, DEMO-governed, LIVE, real-capital or merge authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_policy import (
    T12_SHADOW_POLICY_FROZEN_AT,
    Phase20T12ToolEligibilityShadowDecision,
    t12_shadow_policy_sha256,
)

_SCHEMA = "CIBO_PHASE20_T12_SHADOW_DECISION_LEDGER_V1"
_GENESIS = "sha256:" + ("0" * 64)
_MAX_SEAL_LATENCY = timedelta(seconds=2)


class DurableT12ShadowDecisionError(CiboCapitalManagementError):
    """T12 shadow evidence is stale, conflicting or corrupt."""


@dataclass(frozen=True, slots=True)
class T12ShadowDecisionSeal:
    shadow_decision_sha256: str
    policy_sha256: str
    decision_epoch_id: str
    decision_evidence_sha256: str
    baseline_policy_record_sha256: str
    decision_at: datetime
    shadow_sealed_at: datetime
    treatment_enabled_tools: tuple[str, ...]
    treatment_blocked_tools: tuple[str, ...]
    control_enabled_tools: tuple[str, ...]
    control_blocked_tools: tuple[str, ...]
    treatment_allocator_disposition: str
    control_allocator_disposition: str
    treatment_allocator_applied_tools: tuple[str, ...]
    control_allocator_applied_tools: tuple[str, ...]
    treatment_selected_signal_fingerprints: tuple[str, ...]
    control_selected_signal_fingerprints: tuple[str, ...]
    selection_changed: bool
    allocator_changed: bool

    def __post_init__(self) -> None:
        for name in (
            "shadow_decision_sha256",
            "policy_sha256",
            "decision_evidence_sha256",
            "baseline_policy_record_sha256",
        ):
            if not _valid_sha(getattr(self, name)):
                raise DurableT12ShadowDecisionError(
                    f"T12 shadow {name} must be canonical SHA-256"
                )
        if self.policy_sha256 != t12_shadow_policy_sha256():
            raise DurableT12ShadowDecisionError(
                "T12 shadow policy digest drift"
            )
        if not self.decision_epoch_id:
            raise DurableT12ShadowDecisionError(
                "T12 shadow decision epoch id is required"
            )
        _aware(self.decision_at, "decision_at")
        _aware(self.shadow_sealed_at, "shadow_sealed_at")
        if self.decision_at < T12_SHADOW_POLICY_FROZEN_AT:
            raise DurableT12ShadowDecisionError(
                "T12 shadow cannot seal a pre-freeze decision"
            )
        if self.shadow_sealed_at < self.decision_at:
            raise DurableT12ShadowDecisionError(
                "T12 shadow seal cannot predate decision"
            )
        if self.shadow_sealed_at - self.decision_at > _MAX_SEAL_LATENCY:
            raise DurableT12ShadowDecisionError(
                "T12 shadow seal exceeds frozen two-second window"
            )
        for name in (
            "treatment_enabled_tools",
            "treatment_blocked_tools",
            "control_enabled_tools",
            "control_blocked_tools",
            "treatment_allocator_applied_tools",
            "control_allocator_applied_tools",
            "treatment_selected_signal_fingerprints",
            "control_selected_signal_fingerprints",
        ):
            values = getattr(self, name)
            if len(values) != len(set(values)) or any(
                not isinstance(item, str) or not item for item in values
            ):
                raise DurableT12ShadowDecisionError(
                    f"T12 shadow {name} must be unique/non-empty strings"
                )
        if set(self.treatment_enabled_tools) & set(
            self.treatment_blocked_tools
        ):
            raise DurableT12ShadowDecisionError(
                "T12 shadow treatment tool overlap"
            )
        if self.control_blocked_tools:
            raise DurableT12ShadowDecisionError(
                "T12 shadow control must neutralize regime tool blocking"
            )
        if not set(self.treatment_enabled_tools).issubset(
            set(self.control_enabled_tools)
        ):
            raise DurableT12ShadowDecisionError(
                "T12 shadow control surface does not contain treatment"
            )
        if not self.treatment_allocator_disposition:
            raise DurableT12ShadowDecisionError(
                "T12 shadow treatment disposition is required"
            )
        if not self.control_allocator_disposition:
            raise DurableT12ShadowDecisionError(
                "T12 shadow control disposition is required"
            )
        expected_selection_changed = (
            self.treatment_selected_signal_fingerprints
            != self.control_selected_signal_fingerprints
        )
        if self.selection_changed != expected_selection_changed:
            raise DurableT12ShadowDecisionError(
                "T12 shadow selection flag drift"
            )
        expected_allocator_changed = (
            self.treatment_allocator_disposition
            != self.control_allocator_disposition
            or self.treatment_allocator_applied_tools
            != self.control_allocator_applied_tools
            or expected_selection_changed
        )
        if self.allocator_changed != expected_allocator_changed:
            raise DurableT12ShadowDecisionError(
                "T12 shadow allocator flag drift"
            )


@dataclass(frozen=True, slots=True)
class T12ShadowLedgerRecord:
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
            raise DurableT12ShadowDecisionError(
                "T12 shadow ledger sequence must be positive int"
            )
        if not self.decision_epoch_id:
            raise DurableT12ShadowDecisionError(
                "T12 shadow ledger epoch id is required"
            )
        for name in (
            "payload_sha256",
            "previous_chain_sha256",
            "chain_sha256",
        ):
            if not _valid_sha(getattr(self, name)):
                raise DurableT12ShadowDecisionError(
                    f"T12 shadow ledger {name} invalid"
                )
        expected_payload = "sha256:" + hashlib.sha256(
            self.payload_json.encode()
        ).hexdigest()
        if self.payload_sha256 != expected_payload:
            raise DurableT12ShadowDecisionError(
                "T12 shadow ledger payload SHA mismatch"
            )
        expected_chain = _next_chain(
            previous=self.previous_chain_sha256,
            sequence=self.sequence,
            epoch_id=self.decision_epoch_id,
            payload_sha256=self.payload_sha256,
        )
        if self.chain_sha256 != expected_chain:
            raise DurableT12ShadowDecisionError(
                "T12 shadow ledger chain SHA mismatch"
            )
        seal = _seal_from_json(self.payload_json)
        if seal.decision_epoch_id != self.decision_epoch_id:
            raise DurableT12ShadowDecisionError(
                "T12 shadow ledger epoch binding mismatch"
            )


@dataclass(frozen=True, slots=True)
class VersionedT12ShadowDecisionBook:
    generation: int
    records: tuple[T12ShadowLedgerRecord, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise DurableT12ShadowDecisionError(
                "T12 shadow generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise DurableT12ShadowDecisionError(
                "T12 shadow generation/record count drift"
            )
        previous = _GENESIS
        epochs: set[str] = set()
        evidences: set[str] = set()
        for sequence, record in enumerate(self.records, start=1):
            if record.sequence != sequence:
                raise DurableT12ShadowDecisionError(
                    "T12 shadow ledger sequence drift"
                )
            if record.previous_chain_sha256 != previous:
                raise DurableT12ShadowDecisionError(
                    "T12 shadow previous chain mismatch"
                )
            seal = _seal_from_json(record.payload_json)
            if seal.decision_epoch_id in epochs:
                raise DurableT12ShadowDecisionError(
                    "T12 shadow duplicate decision epoch"
                )
            if seal.decision_evidence_sha256 in evidences:
                raise DurableT12ShadowDecisionError(
                    "T12 shadow duplicate decision evidence"
                )
            epochs.add(seal.decision_epoch_id)
            evidences.add(seal.decision_evidence_sha256)
            previous = record.chain_sha256

    @property
    def chain_sha256(self) -> str:
        return self.records[-1].chain_sha256 if self.records else _GENESIS

    @property
    def decisions(self) -> tuple[T12ShadowDecisionSeal, ...]:
        return tuple(_seal_from_json(item.payload_json) for item in self.records)

    def decision_for_evidence(
        self,
        decision_evidence_sha256: str,
    ) -> T12ShadowDecisionSeal | None:
        matches = tuple(
            item
            for item in self.decisions
            if item.decision_evidence_sha256 == decision_evidence_sha256
        )
        if len(matches) > 1:
            raise DurableT12ShadowDecisionError(
                "T12 shadow duplicate evidence binding"
            )
        return matches[0] if matches else None


class DurableT12ShadowDecisionStore:
    """Atomic CAS store for preregistered T12 shadow decisions."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(path, Path):
            raise DurableT12ShadowDecisionError(
                "T12 shadow store path must be pathlib.Path"
            )
        self._path = path
        self._clock = clock or (lambda: datetime.now(UTC))
        self._writer_lock_path = path.with_name(
            f".{path.name}.writer-lock"
        )
        self._lock = RLock()

    def load(self) -> VersionedT12ShadowDecisionBook:
        with self._lock:
            return self._load_unlocked()

    def seal_shadow_decision(
        self,
        shadow: Phase20T12ToolEligibilityShadowDecision,
        *,
        evidence_book: VersionedPhase20ForwardEvidenceBook,
        policy_book: VersionedPhase20ForwardPolicyBook,
        expected_generation: int,
    ) -> VersionedT12ShadowDecisionBook:
        if not isinstance(
            shadow,
            Phase20T12ToolEligibilityShadowDecision,
        ):
            raise DurableT12ShadowDecisionError(
                "T12 shadow store requires canonical shadow decision"
            )
        if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
            raise DurableT12ShadowDecisionError(
                "T12 shadow store requires canonical evidence book"
            )
        if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
            raise DurableT12ShadowDecisionError(
                "T12 shadow store requires canonical policy book"
            )
        _expected_generation(expected_generation)

        decision = evidence_book.decision_for_sha(
            shadow.decision_evidence_sha256
        )
        if decision is None:
            raise DurableT12ShadowDecisionError(
                "T12 shadow has no sealed forward decision"
            )
        if decision.decision_epoch_id != shadow.decision_epoch_id:
            raise DurableT12ShadowDecisionError(
                "T12 shadow decision epoch binding drift"
            )
        if decision.decision_at < T12_SHADOW_POLICY_FROZEN_AT:
            raise DurableT12ShadowDecisionError(
                "T12 shadow cannot bind pre-freeze evidence"
            )
        if any(
            outcome.decision_evidence_sha256
            == shadow.decision_evidence_sha256
            for outcome in evidence_book.outcomes
        ):
            raise DurableT12ShadowDecisionError(
                "T12 shadow cannot seal after outcome exists"
            )

        baseline = policy_book.decision_for_evidence(
            shadow.decision_evidence_sha256
        )
        if baseline is None:
            raise DurableT12ShadowDecisionError(
                "T12 shadow requires prior baseline policy seal"
            )
        _validate_baseline_binding(
            baseline=baseline,
            shadow=shadow,
        )

        shadow_sha = _shadow_decision_sha256(shadow)
        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise DurableT12ShadowDecisionError(
                        "T12 shadow generation conflict"
                    )
                prior = current.decision_for_evidence(
                    shadow.decision_evidence_sha256
                )
                if prior is not None:
                    if prior.shadow_decision_sha256 == shadow_sha:
                        return current
                    raise DurableT12ShadowDecisionError(
                        "T12 shadow conflicting decision evidence"
                    )

                sealed_at = self._clock()
                _aware(sealed_at, "store clock")
                seal = T12ShadowDecisionSeal(
                    shadow_decision_sha256=shadow_sha,
                    policy_sha256=shadow.policy_sha256,
                    decision_epoch_id=shadow.decision_epoch_id,
                    decision_evidence_sha256=(
                        shadow.decision_evidence_sha256
                    ),
                    baseline_policy_record_sha256=(
                        shadow.baseline_policy_record_sha256
                    ),
                    decision_at=decision.decision_at,
                    shadow_sealed_at=sealed_at,
                    treatment_enabled_tools=shadow.treatment_enabled_tools,
                    treatment_blocked_tools=shadow.treatment_blocked_tools,
                    control_enabled_tools=shadow.control_enabled_tools,
                    control_blocked_tools=shadow.control_blocked_tools,
                    treatment_allocator_disposition=(
                        shadow.treatment_allocator_disposition
                    ),
                    control_allocator_disposition=(
                        shadow.control_allocator_disposition
                    ),
                    treatment_allocator_applied_tools=(
                        shadow.treatment_allocator_applied_tools
                    ),
                    control_allocator_applied_tools=(
                        shadow.control_allocator_applied_tools
                    ),
                    treatment_selected_signal_fingerprints=(
                        shadow.treatment_selected_signal_fingerprints
                    ),
                    control_selected_signal_fingerprints=(
                        shadow.control_selected_signal_fingerprints
                    ),
                    selection_changed=shadow.selection_changed,
                    allocator_changed=shadow.allocator_changed,
                )
                record = _record(
                    sequence=current.generation + 1,
                    seal=seal,
                    previous=current.chain_sha256,
                )
                updated = VersionedT12ShadowDecisionBook(
                    generation=current.generation + 1,
                    records=current.records + (record,),
                )
                self._write_unlocked(updated)
                return updated
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedT12ShadowDecisionBook:
        if not self._path.exists():
            return VersionedT12ShadowDecisionBook(generation=0)
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DurableT12ShadowDecisionError(
                "T12 shadow store is unreadable"
            ) from error
        return _book_from_payload(payload)

    def _write_unlocked(
        self,
        book: VersionedT12ShadowDecisionBook,
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
            raise DurableT12ShadowDecisionError(
                "T12 shadow store write failed"
            ) from error
        finally:
            temp.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise DurableT12ShadowDecisionError(
                "T12 shadow writer lock already held"
            ) from error
        except OSError as error:
            raise DurableT12ShadowDecisionError(
                "T12 shadow writer lock unavailable"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            return
        except OSError as error:
            raise DurableT12ShadowDecisionError(
                "T12 shadow writer lock release failed"
            ) from error


def _validate_baseline_binding(
    *,
    baseline: object,
    shadow: Phase20T12ToolEligibilityShadowDecision,
) -> None:
    policy_record_sha256 = getattr(
        baseline,
        "policy_record_sha256",
        None,
    )
    canonical_record_json = getattr(
        baseline,
        "canonical_record_json",
        None,
    )
    if not isinstance(canonical_record_json, str):
        raise DurableT12ShadowDecisionError(
            "T12 baseline canonical policy record missing"
        )
    expected_policy_sha = "sha256:" + hashlib.sha256(
        canonical_record_json.encode("utf-8")
    ).hexdigest()
    if (
        policy_record_sha256 != expected_policy_sha
        or policy_record_sha256
        != shadow.baseline_policy_record_sha256
    ):
        raise DurableT12ShadowDecisionError(
            "T12 baseline policy digest binding drift"
        )
    selected = getattr(
        baseline,
        "selected_signal_fingerprints",
        None,
    )
    if selected != shadow.treatment_selected_signal_fingerprints:
        raise DurableT12ShadowDecisionError(
            "T12 baseline selected-signal binding drift"
        )
    disposition = getattr(baseline, "allocator_disposition", None)
    if disposition != shadow.treatment_allocator_disposition:
        raise DurableT12ShadowDecisionError(
            "T12 baseline allocator disposition binding drift"
        )
    try:
        record = json.loads(canonical_record_json)
    except json.JSONDecodeError as error:
        raise DurableT12ShadowDecisionError(
            "T12 baseline canonical policy JSON invalid"
        ) from error
    allocator = (
        record.get("allocator_decision")
        if isinstance(record, dict)
        else None
    )
    if not isinstance(allocator, dict):
        raise DurableT12ShadowDecisionError(
            "T12 baseline canonical allocator missing"
        )
    applied = allocator.get("applied_tools")
    if not isinstance(applied, list) or any(
        not isinstance(item, str) for item in applied
    ):
        raise DurableT12ShadowDecisionError(
            "T12 baseline canonical applied tools invalid"
        )
    if tuple(applied) != shadow.treatment_allocator_applied_tools:
        raise DurableT12ShadowDecisionError(
            "T12 baseline applied-tool binding drift"
        )


def _shadow_decision_sha256(
    shadow: Phase20T12ToolEligibilityShadowDecision,
) -> str:
    payload = {
        "policy_id": shadow.policy_id,
        "policy_sha256": shadow.policy_sha256,
        "policy_frozen_at": shadow.policy_frozen_at.isoformat(),
        "decision_epoch_id": shadow.decision_epoch_id,
        "decision_evidence_sha256": shadow.decision_evidence_sha256,
        "baseline_policy_record_sha256": (
            shadow.baseline_policy_record_sha256
        ),
        "treatment_enabled_tools": list(shadow.treatment_enabled_tools),
        "treatment_blocked_tools": list(shadow.treatment_blocked_tools),
        "control_enabled_tools": list(shadow.control_enabled_tools),
        "control_blocked_tools": list(shadow.control_blocked_tools),
        "treatment_allocator_disposition": (
            shadow.treatment_allocator_disposition
        ),
        "control_allocator_disposition": (
            shadow.control_allocator_disposition
        ),
        "treatment_allocator_applied_tools": list(
            shadow.treatment_allocator_applied_tools
        ),
        "control_allocator_applied_tools": list(
            shadow.control_allocator_applied_tools
        ),
        "treatment_selected_signal_fingerprints": list(
            shadow.treatment_selected_signal_fingerprints
        ),
        "control_selected_signal_fingerprints": list(
            shadow.control_selected_signal_fingerprints
        ),
        "selection_changed": shadow.selection_changed,
        "allocator_changed": shadow.allocator_changed,
        "outcome_present_at_seal": shadow.outcome_present_at_seal,
        "runtime_authority": shadow.runtime_authority,
        "risk_authority": shadow.risk_authority,
        "execution_authority": shadow.execution_authority,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _seal_payload(seal: T12ShadowDecisionSeal) -> dict[str, object]:
    return {
        "shadow_decision_sha256": seal.shadow_decision_sha256,
        "policy_sha256": seal.policy_sha256,
        "decision_epoch_id": seal.decision_epoch_id,
        "decision_evidence_sha256": seal.decision_evidence_sha256,
        "baseline_policy_record_sha256": (
            seal.baseline_policy_record_sha256
        ),
        "decision_at": seal.decision_at.isoformat(),
        "shadow_sealed_at": seal.shadow_sealed_at.isoformat(),
        "treatment_enabled_tools": list(seal.treatment_enabled_tools),
        "treatment_blocked_tools": list(seal.treatment_blocked_tools),
        "control_enabled_tools": list(seal.control_enabled_tools),
        "control_blocked_tools": list(seal.control_blocked_tools),
        "treatment_allocator_disposition": (
            seal.treatment_allocator_disposition
        ),
        "control_allocator_disposition": (
            seal.control_allocator_disposition
        ),
        "treatment_allocator_applied_tools": list(
            seal.treatment_allocator_applied_tools
        ),
        "control_allocator_applied_tools": list(
            seal.control_allocator_applied_tools
        ),
        "treatment_selected_signal_fingerprints": list(
            seal.treatment_selected_signal_fingerprints
        ),
        "control_selected_signal_fingerprints": list(
            seal.control_selected_signal_fingerprints
        ),
        "selection_changed": seal.selection_changed,
        "allocator_changed": seal.allocator_changed,
    }


def _seal_from_json(value: str) -> T12ShadowDecisionSeal:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise DurableT12ShadowDecisionError(
            "T12 shadow seal JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise DurableT12ShadowDecisionError(
            "T12 shadow seal payload must be object"
        )
    try:
        return T12ShadowDecisionSeal(
            shadow_decision_sha256=str(
                payload["shadow_decision_sha256"]
            ),
            policy_sha256=str(payload["policy_sha256"]),
            decision_epoch_id=str(payload["decision_epoch_id"]),
            decision_evidence_sha256=str(
                payload["decision_evidence_sha256"]
            ),
            baseline_policy_record_sha256=str(
                payload["baseline_policy_record_sha256"]
            ),
            decision_at=datetime.fromisoformat(
                str(payload["decision_at"])
            ),
            shadow_sealed_at=datetime.fromisoformat(
                str(payload["shadow_sealed_at"])
            ),
            treatment_enabled_tools=_strings(
                payload["treatment_enabled_tools"]
            ),
            treatment_blocked_tools=_strings(
                payload["treatment_blocked_tools"]
            ),
            control_enabled_tools=_strings(
                payload["control_enabled_tools"]
            ),
            control_blocked_tools=_strings(
                payload["control_blocked_tools"]
            ),
            treatment_allocator_disposition=str(
                payload["treatment_allocator_disposition"]
            ),
            control_allocator_disposition=str(
                payload["control_allocator_disposition"]
            ),
            treatment_allocator_applied_tools=_strings(
                payload["treatment_allocator_applied_tools"]
            ),
            control_allocator_applied_tools=_strings(
                payload["control_allocator_applied_tools"]
            ),
            treatment_selected_signal_fingerprints=_strings(
                payload["treatment_selected_signal_fingerprints"]
            ),
            control_selected_signal_fingerprints=_strings(
                payload["control_selected_signal_fingerprints"]
            ),
            selection_changed=_bool(
                payload["selection_changed"],
                "selection_changed",
            ),
            allocator_changed=_bool(
                payload["allocator_changed"],
                "allocator_changed",
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DurableT12ShadowDecisionError(
            "T12 shadow seal payload invalid"
        ) from error


def _record(
    *,
    sequence: int,
    seal: T12ShadowDecisionSeal,
    previous: str,
) -> T12ShadowLedgerRecord:
    payload_json = json.dumps(
        _seal_payload(seal),
        sort_keys=True,
        separators=(",", ":"),
    )
    payload_sha = "sha256:" + hashlib.sha256(
        payload_json.encode()
    ).hexdigest()
    return T12ShadowLedgerRecord(
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
) -> VersionedT12ShadowDecisionBook:
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        raise DurableT12ShadowDecisionError(
            "T12 shadow store schema mismatch"
        )
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise DurableT12ShadowDecisionError(
            "T12 shadow records must be list"
        )
    try:
        records = tuple(
            T12ShadowLedgerRecord(
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
            raise TypeError("T12 shadow record must be object")
        generation = int(payload["generation"])
    except (KeyError, TypeError, ValueError) as error:
        raise DurableT12ShadowDecisionError(
            "T12 shadow store payload invalid"
        ) from error
    book = VersionedT12ShadowDecisionBook(
        generation=generation,
        records=records,
    )
    if payload.get("chain_sha256") != book.chain_sha256:
        raise DurableT12ShadowDecisionError(
            "T12 shadow terminal chain mismatch"
        )
    return book


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError("T12 shadow string tuple must be list")
    return tuple(str(item) for item in value)


def _valid_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise DurableT12ShadowDecisionError(
            f"T12 shadow {name} must be bool"
        )
    return value


def _expected_generation(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise DurableT12ShadowDecisionError(
            "T12 shadow expected generation must be non-negative int"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise DurableT12ShadowDecisionError(
            f"T12 shadow {name} must be timezone-aware"
        )
