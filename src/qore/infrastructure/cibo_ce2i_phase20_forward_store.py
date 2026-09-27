"""Durable append-only store for Phase20D forward evidence.

The store seals a complete pre-decision payload before any outcome can be
appended. It uses generation CAS, a writer lock and atomic replace. It has no
trading, Risk, sizing or execution authority.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
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

_SCHEMA = "CIBO_PHASE20D_FORWARD_EVIDENCE_BOOK_V4"
_READABLE_SCHEMAS = {
    "CIBO_PHASE20D_FORWARD_EVIDENCE_BOOK_V3",
    _SCHEMA,
}


class DurablePhase20ForwardEvidenceError(CiboCapitalManagementError):
    """Forward evidence cannot be trusted or updated safely."""


@dataclass(frozen=True, slots=True)
class Phase20ForwardDecisionSeal:
    evidence_id: str
    decision_epoch_id: str
    evidence_sha256: str
    decision_at: datetime
    candidate_id: str
    code_sha: str
    parameter_sha256: str
    signal_fingerprints: tuple[str, ...]
    canonical_payload_json: str
    sealed_at: datetime | None = None
    seal_deadline_at: datetime | None = None

    def __post_init__(self) -> None:
        if (
            not self.evidence_id
            or not self.decision_epoch_id
            or not self.candidate_id
        ):
            raise DurablePhase20ForwardEvidenceError(
                "forward decision seal evidence/epoch identity is required"
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
        for name in ("sealed_at", "seal_deadline_at"):
            value = getattr(self, name)
            if (
                value is not None
                and (value.tzinfo is None or value.utcoffset() is None)
            ):
                raise DurablePhase20ForwardEvidenceError(
                    f"forward decision {name} must be timezone-aware"
                )
        if (
            self.seal_deadline_at is not None
            and self.seal_deadline_at < self.decision_at
        ):
            raise DurablePhase20ForwardEvidenceError(
                "forward decision seal deadline cannot predate decision"
            )
        # A complete causal epoch may legitimately contain zero candidates.
        # Those epochs must remain in the durable population to avoid
        # conditioning qualification only on signal-producing periods.
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

    @property
    def sealed_within_deadline(self) -> bool:
        return (
            self.sealed_at is not None
            and self.seal_deadline_at is not None
            and self.decision_at <= self.sealed_at <= self.seal_deadline_at
        )


@dataclass(frozen=True, slots=True)
class Phase20ForwardOutcomeSeal:
    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    position_id: int
    execution_risk_evidence_id: str
    settlement_deal_ids: tuple[int, ...]
    fill_evidence_refs: tuple[str, ...]
    observed_at: datetime
    realized_net_pnl_usd: Decimal
    executed_initial_stop_risk_usd: Decimal
    realized_structural_outcome_r: Decimal
    capital_deployed_at: datetime | None = None
    capital_released_at: datetime | None = None
    capital_minutes: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.signal_fingerprint:
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome identity is required"
            )
        if not self.decision_evidence_sha256.startswith("sha256:"):
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome decision SHA256 is required"
            )
        if (
            not isinstance(self.position_id, int)
            or isinstance(self.position_id, bool)
            or self.position_id <= 0
        ):
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome position_id must be positive int"
            )
        if not self.execution_risk_evidence_id:
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome risk evidence id is required"
            )
        if (
            not self.settlement_deal_ids
            or len(self.settlement_deal_ids)
            != len(set(self.settlement_deal_ids))
            or any(
                not isinstance(item, int)
                or isinstance(item, bool)
                or item <= 0
                for item in self.settlement_deal_ids
            )
        ):
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome settlement deal ids invalid"
            )
        if (
            not self.fill_evidence_refs
            or len(self.fill_evidence_refs) != len(set(self.fill_evidence_refs))
            or any(
                not isinstance(item, str) or not item
                for item in self.fill_evidence_refs
            )
        ):
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome fill evidence refs invalid"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome timestamp must be timezone-aware"
            )
        for name in (
            "realized_net_pnl_usd",
            "executed_initial_stop_risk_usd",
            "realized_structural_outcome_r",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise DurablePhase20ForwardEvidenceError(
                    f"forward outcome {name} must be finite Decimal"
                )
        if self.executed_initial_stop_risk_usd <= 0:
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome executed risk must be positive"
            )
        if (
            self.realized_net_pnl_usd
            / self.executed_initial_stop_risk_usd
            != self.realized_structural_outcome_r
        ):
            raise DurablePhase20ForwardEvidenceError(
                "forward outcome structural R identity mismatch"
            )
        timing = (
            self.capital_deployed_at,
            self.capital_released_at,
            self.capital_minutes,
        )
        if any(item is not None for item in timing):
            if any(item is None for item in timing):
                raise DurablePhase20ForwardEvidenceError(
                    "forward outcome capital timing must be complete"
                )
            assert self.capital_deployed_at is not None
            assert self.capital_released_at is not None
            assert self.capital_minutes is not None
            if (
                self.capital_deployed_at.tzinfo is None
                or self.capital_deployed_at.utcoffset() is None
                or self.capital_released_at.tzinfo is None
                or self.capital_released_at.utcoffset() is None
            ):
                raise DurablePhase20ForwardEvidenceError(
                    "forward outcome capital timestamps must be timezone-aware"
                )
            if self.capital_released_at <= self.capital_deployed_at:
                raise DurablePhase20ForwardEvidenceError(
                    "forward outcome capital release must follow deployment"
                )
            if (
                not isinstance(self.capital_minutes, Decimal)
                or not self.capital_minutes.is_finite()
                or self.capital_minutes <= 0
            ):
                raise DurablePhase20ForwardEvidenceError(
                    "forward outcome capital minutes invalid"
                )
            expected_minutes = Decimal(
                str(
                    (
                        self.capital_released_at
                        - self.capital_deployed_at
                    ).total_seconds()
                )
            ) / Decimal("60")
            if self.capital_minutes != expected_minutes:
                raise DurablePhase20ForwardEvidenceError(
                    "forward outcome capital minutes identity mismatch"
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
        decision_epoch_ids = tuple(
            item.decision_epoch_id for item in self.decisions
        )
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
        if len(decision_epoch_ids) != len(set(decision_epoch_ids)):
            raise DurablePhase20ForwardEvidenceError(
                "duplicate forward decision epoch identity"
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

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(path, Path):
            raise DurablePhase20ForwardEvidenceError(
                "forward evidence path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = RLock()

    def load(self) -> VersionedPhase20ForwardEvidenceBook:
        with self._lock:
            return self._load_unlocked()

    def seal_decision(
        self,
        evidence: Phase20ForwardDecisionEvidence,
        *,
        expected_generation: int,
        seal_deadline_at: datetime | None = None,
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
        if seal_deadline_at is not None:
            if (
                seal_deadline_at.tzinfo is None
                or seal_deadline_at.utcoffset() is None
            ):
                raise DurablePhase20ForwardEvidenceError(
                    "forward decision seal deadline must be timezone-aware"
                )
            if seal_deadline_at < evidence.decision_at:
                raise DurablePhase20ForwardEvidenceError(
                    "forward decision seal deadline cannot predate decision"
                )

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
                    if item.evidence_id == evidence.evidence_id
                )
                if same_id:
                    if _decision_matches_evidence(same_id[0], evidence):
                        return current
                    raise DurablePhase20ForwardEvidenceError(
                        "conflicting forward decision rewrite"
                    )
                same_epoch = tuple(
                    item
                    for item in current.decisions
                    if item.decision_epoch_id == evidence.decision_epoch_id
                )
                if same_epoch:
                    if _decision_matches_evidence(same_epoch[0], evidence):
                        return current
                    raise DurablePhase20ForwardEvidenceError(
                        "conflicting forward decision epoch rewrite"
                    )
                evidence_sha256 = phase20_forward_evidence_sha256(evidence)
                if current.decision_for_sha(evidence_sha256) is not None:
                    raise DurablePhase20ForwardEvidenceError(
                        "forward decision payload already sealed under another id"
                    )
                provisional_seal = _decision_seal(
                    evidence,
                    sealed_at=None,
                    seal_deadline_at=seal_deadline_at,
                )
                provisional = VersionedPhase20ForwardEvidenceBook(
                    generation=current.generation + 1,
                    decisions=current.decisions + (provisional_seal,),
                    outcomes=current.outcomes,
                )
                # First make the pre-decision evidence physically durable.
                # Until the completion witness below is persisted, sealed_at
                # stays None and qualification must fail closed.
                self._write_unlocked(provisional)

                sealed_at = self._clock()
                if sealed_at.tzinfo is None or sealed_at.utcoffset() is None:
                    raise DurablePhase20ForwardEvidenceError(
                        "forward decision physical seal timestamp must be timezone-aware"
                    )
                seal = _decision_seal(
                    evidence,
                    sealed_at=sealed_at,
                    seal_deadline_at=seal_deadline_at,
                )
                updated = VersionedPhase20ForwardEvidenceBook(
                    generation=provisional.generation,
                    decisions=current.decisions + (seal,),
                    outcomes=current.outcomes,
                )
                # Persist the completion witness without changing the decision
                # payload or generation. A crash before this write leaves the
                # durable decision explicitly incomplete/ineligible.
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
                    position_id=outcome.position_id,
                    execution_risk_evidence_id=(
                        outcome.execution_risk_evidence_id
                    ),
                    settlement_deal_ids=outcome.settlement_deal_ids,
                    fill_evidence_refs=outcome.fill_evidence_refs,
                    observed_at=outcome.observed_at,
                    realized_net_pnl_usd=outcome.realized_net_pnl_usd,
                    executed_initial_stop_risk_usd=(
                        outcome.executed_initial_stop_risk_usd
                    ),
                    realized_structural_outcome_r=(
                        outcome.realized_structural_outcome_r
                    ),
                    capital_deployed_at=outcome.capital_deployed_at,
                    capital_released_at=outcome.capital_released_at,
                    capital_minutes=outcome.capital_minutes,
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
        if (
            not isinstance(raw, dict)
            or raw.get("schema") not in _READABLE_SCHEMAS
        ):
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
    *,
    sealed_at: datetime | None,
    seal_deadline_at: datetime | None,
) -> Phase20ForwardDecisionSeal:
    payload = phase20_forward_evidence_json(evidence)
    return Phase20ForwardDecisionSeal(
        evidence_id=evidence.evidence_id,
        decision_epoch_id=evidence.decision_epoch_id,
        evidence_sha256=phase20_forward_evidence_sha256(evidence),
        decision_at=evidence.decision_at,
        candidate_id=evidence.lineage.candidate_id,
        code_sha=evidence.lineage.code_sha,
        parameter_sha256=evidence.lineage.parameter_sha256,
        signal_fingerprints=tuple(
            item.candidate.signal_fingerprint for item in evidence.candidates
        ),
        canonical_payload_json=payload,
        sealed_at=sealed_at,
        seal_deadline_at=seal_deadline_at,
    )


def _decision_matches_evidence(
    seal: Phase20ForwardDecisionSeal,
    evidence: Phase20ForwardDecisionEvidence,
) -> bool:
    return (
        seal.evidence_id == evidence.evidence_id
        and seal.decision_epoch_id == evidence.decision_epoch_id
        and seal.evidence_sha256 == phase20_forward_evidence_sha256(evidence)
        and seal.decision_at == evidence.decision_at
        and seal.candidate_id == evidence.lineage.candidate_id
        and seal.code_sha == evidence.lineage.code_sha
        and seal.parameter_sha256 == evidence.lineage.parameter_sha256
        and seal.signal_fingerprints
        == tuple(
            item.candidate.signal_fingerprint for item in evidence.candidates
        )
        and seal.canonical_payload_json == phase20_forward_evidence_json(evidence)
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
        "decision_epoch_id": value.decision_epoch_id,
        "evidence_sha256": value.evidence_sha256,
        "decision_at": value.decision_at.isoformat(),
        "candidate_id": value.candidate_id,
        "code_sha": value.code_sha,
        "parameter_sha256": value.parameter_sha256,
        "signal_fingerprints": list(value.signal_fingerprints),
        "canonical_payload_json": value.canonical_payload_json,
        "sealed_at": (
            None if value.sealed_at is None else value.sealed_at.isoformat()
        ),
        "seal_deadline_at": (
            None
            if value.seal_deadline_at is None
            else value.seal_deadline_at.isoformat()
        ),
    }


def _decision_from_json(value: object) -> Phase20ForwardDecisionSeal:
    if not isinstance(value, dict):
        raise TypeError("forward decision row must be object")
    fingerprints = value["signal_fingerprints"]
    if not isinstance(fingerprints, list):
        raise TypeError("forward signal_fingerprints must be list")
    return Phase20ForwardDecisionSeal(
        evidence_id=str(value["evidence_id"]),
        decision_epoch_id=str(value["decision_epoch_id"]),
        evidence_sha256=str(value["evidence_sha256"]),
        decision_at=datetime.fromisoformat(str(value["decision_at"])),
        candidate_id=str(value["candidate_id"]),
        code_sha=str(value["code_sha"]),
        parameter_sha256=str(value["parameter_sha256"]),
        signal_fingerprints=tuple(str(item) for item in fingerprints),
        canonical_payload_json=str(value["canonical_payload_json"]),
        sealed_at=(
            None
            if value.get("sealed_at") is None
            else datetime.fromisoformat(str(value["sealed_at"]))
        ),
        seal_deadline_at=(
            None
            if value.get("seal_deadline_at") is None
            else datetime.fromisoformat(str(value["seal_deadline_at"]))
        ),
    )


def _outcome_to_json(
    value: Phase20ForwardOutcomeSeal,
) -> dict[str, object]:
    return {
        "evidence_id": value.evidence_id,
        "decision_evidence_sha256": value.decision_evidence_sha256,
        "signal_fingerprint": value.signal_fingerprint,
        "position_id": value.position_id,
        "execution_risk_evidence_id": value.execution_risk_evidence_id,
        "settlement_deal_ids": list(value.settlement_deal_ids),
        "fill_evidence_refs": list(value.fill_evidence_refs),
        "observed_at": value.observed_at.isoformat(),
        "realized_net_pnl_usd": format(
            value.realized_net_pnl_usd,
            "f",
        ),
        "executed_initial_stop_risk_usd": format(
            value.executed_initial_stop_risk_usd,
            "f",
        ),
        "realized_structural_outcome_r": format(
            value.realized_structural_outcome_r,
            "f",
        ),
        "capital_deployed_at": (
            None
            if value.capital_deployed_at is None
            else value.capital_deployed_at.isoformat()
        ),
        "capital_released_at": (
            None
            if value.capital_released_at is None
            else value.capital_released_at.isoformat()
        ),
        "capital_minutes": (
            None
            if value.capital_minutes is None
            else format(value.capital_minutes, "f")
        ),
    }


def _outcome_from_json(value: object) -> Phase20ForwardOutcomeSeal:
    if not isinstance(value, dict):
        raise TypeError("forward outcome row must be object")
    deal_ids = value["settlement_deal_ids"]
    fill_refs = value["fill_evidence_refs"]
    if not isinstance(deal_ids, list) or not isinstance(fill_refs, list):
        raise TypeError("forward outcome provenance must be lists")
    return Phase20ForwardOutcomeSeal(
        evidence_id=str(value["evidence_id"]),
        decision_evidence_sha256=str(value["decision_evidence_sha256"]),
        signal_fingerprint=str(value["signal_fingerprint"]),
        position_id=int(str(value["position_id"])),
        execution_risk_evidence_id=str(
            value["execution_risk_evidence_id"]
        ),
        settlement_deal_ids=tuple(int(str(item)) for item in deal_ids),
        fill_evidence_refs=tuple(str(item) for item in fill_refs),
        observed_at=datetime.fromisoformat(str(value["observed_at"])),
        realized_net_pnl_usd=Decimal(str(value["realized_net_pnl_usd"])),
        executed_initial_stop_risk_usd=Decimal(
            str(value["executed_initial_stop_risk_usd"])
        ),
        realized_structural_outcome_r=Decimal(
            str(value["realized_structural_outcome_r"])
        ),
        capital_deployed_at=(
            None
            if value.get("capital_deployed_at") is None
            else datetime.fromisoformat(str(value["capital_deployed_at"]))
        ),
        capital_released_at=(
            None
            if value.get("capital_released_at") is None
            else datetime.fromisoformat(str(value["capital_released_at"]))
        ),
        capital_minutes=(
            None
            if value.get("capital_minutes") is None
            else Decimal(str(value["capital_minutes"]))
        ),
    )
