"""Immutable CIBO executive journal foundations.

The journal retains material executive episodes (decisions, lessons, failures,
economic) as append-only, evidence-oriented entries. Later outcomes are linked
through explicit lineage; historical beliefs are never rewritten in hindsight.
Loss/stop analysis treats INSUFFICIENT_EVIDENCE as a first-class diagnosis and
keeps cause hypotheses as non-causal research inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveValidationError,
    CiboConfidence,
    CiboUncertainty,
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


class CiboExecutiveJournalError(InfrastructureError):
    """Base error for immutable CIBO executive journal contracts."""

    __slots__ = ()


class CiboExecutiveJournalValidationError(CiboExecutiveJournalError):
    """A journal value violates a deterministic evidence invariant."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CiboExecutiveJournalValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboExecutiveJournalValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboExecutiveJournalValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    return value


def _validate_codes(
    values: tuple[str, ...],
    *,
    field_name: str,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(not isinstance(v, str) for v in values):
        raise CiboExecutiveJournalValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(v, field_name=field_name) for v in values)
    if len(set(normalized)) != len(normalized):
        raise CiboExecutiveJournalValidationError(f"{field_name} must not contain duplicates")
    if not allow_empty and not normalized:
        raise CiboExecutiveJournalValidationError(f"{field_name} must be non-empty")
    return tuple(sorted(normalized))


def _validate_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
    allow_empty: bool = True,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboExecutiveJournalValidationError(
            f"{field_name} must be an immutable tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveJournalValidationError(f"{field_name} must not contain duplicates")
    if not allow_empty and not values:
        raise CiboExecutiveJournalValidationError(f"{field_name} must be non-empty")
    return tuple(sorted(values, key=lambda item: item.value))


def _revalidate_refs(values: tuple[CiboEvidenceRef, ...], *, field_name: str) -> None:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboExecutiveJournalValidationError(
            f"{field_name} must be an immutable tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveJournalValidationError(f"{field_name} must not contain duplicates")
    if values != tuple(sorted(values, key=lambda item: item.value)):
        raise CiboExecutiveJournalValidationError(
            f"{field_name} failed canonical revalidation"
        )
    for ref in values:
        _revalidate_ref(ref, field_name=field_name)


def _revalidate_ref(ref: CiboEvidenceRef, *, field_name: str) -> None:
    if not isinstance(ref, CiboEvidenceRef):
        raise CiboExecutiveJournalValidationError(f"{field_name} must be CiboEvidenceRef")
    try:
        if CiboEvidenceRef(ref.value) != ref:
            raise CiboExecutiveJournalValidationError(
                f"{field_name} failed nested revalidation"
            )
    except CiboExecutiveJournalValidationError:
        raise
    except InfrastructureError as error:
        raise CiboExecutiveJournalValidationError(
            f"{field_name} failed nested revalidation"
        ) from error


def _revalidate_confidence(confidence: CiboConfidence) -> None:
    try:
        confidence.revalidate()
    except CiboCognitiveValidationError as error:
        raise CiboExecutiveJournalValidationError(
            "journal confidence failed revalidation"
        ) from error


def _revalidate_uncertainty(uncertainty: CiboUncertainty) -> None:
    try:
        uncertainty.revalidate()
    except CiboCognitiveValidationError as error:
        raise CiboExecutiveJournalValidationError(
            "journal uncertainty failed revalidation"
        ) from error


def _canonical_uuid_ids(values: tuple[UUID, ...], *, field_name: str) -> tuple[UUID, ...]:
    if not isinstance(values, tuple) or any(not isinstance(v, UUID) for v in values):
        raise CiboExecutiveJournalValidationError(
            f"{field_name} must be an immutable tuple of UUIDs"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveJournalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values))


class CiboJournalEntryKind(StrEnum):
    DECISION = "decision"
    LESSON = "lesson"
    FAILURE = "failure"
    ECONOMIC = "economic"


class CiboEvidenceSufficiency(StrEnum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class CiboLossDiagnosisState(StrEnum):
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    HYPOTHESIZED = "hypothesized"


class CiboLossHypothesis(StrEnum):
    """Advisory, non-causal hypotheses for a loss/stop; never silent parameter changes."""

    RISK_CONTAINMENT = "risk-containment"
    ENTRY_QUALITY = "entry-quality"
    MARKET_NOISE = "market-noise"
    REGIME_CHANGE = "regime-change"
    VOLATILITY_EXPANSION = "volatility-expansion"
    LATE_SIGNAL = "late-signal"
    LIFECYCLE_MISMATCH = "lifecycle-mismatch"
    INSTRUMENT_MISMATCH = "instrument-mismatch"
    STOP_METHODOLOGY = "stop-methodology"
    CONCENTRATION_CORRELATION = "concentration-correlation"
    EXECUTION_COST_DEGRADATION = "execution-cost-degradation"


_ECONOMIC_LINK_FIELDS = (
    "trader_ref",
    "instrument_ref",
    "market_ref",
    "regime_ref",
    "signal_ref",
    "decision_ref",
    "management_ref",
    "risk_decision_ref",
    "receipt_ref",
    "fill_ref",
    "reconciliation_ref",
    "pnl_ref",
    "cost_ref",
    "slippage_ref",
    "carry_ref",
    "stop_ref",
    "target_ref",
    "mfe_ref",
    "mae_ref",
    "drawdown_ref",
    "exposure_ref",
    "trader_attribution_ref",
    "cibo_attribution_ref",
)


@dataclass(frozen=True, slots=True)
class CiboEconomicJournalLink:
    """Link-only semantics to exact economic evidence; it invents no PnL or cause.

    Every field is an optional opaque ``CiboEvidenceRef``. A missing field simply
    means that evidence was not supplied; nothing is fabricated to fill a slot.
    """

    trader_ref: CiboEvidenceRef | None = None
    instrument_ref: CiboEvidenceRef | None = None
    market_ref: CiboEvidenceRef | None = None
    regime_ref: CiboEvidenceRef | None = None
    signal_ref: CiboEvidenceRef | None = None
    decision_ref: CiboEvidenceRef | None = None
    management_ref: CiboEvidenceRef | None = None
    risk_decision_ref: CiboEvidenceRef | None = None
    receipt_ref: CiboEvidenceRef | None = None
    fill_ref: CiboEvidenceRef | None = None
    reconciliation_ref: CiboEvidenceRef | None = None
    pnl_ref: CiboEvidenceRef | None = None
    cost_ref: CiboEvidenceRef | None = None
    slippage_ref: CiboEvidenceRef | None = None
    carry_ref: CiboEvidenceRef | None = None
    stop_ref: CiboEvidenceRef | None = None
    target_ref: CiboEvidenceRef | None = None
    mfe_ref: CiboEvidenceRef | None = None
    mae_ref: CiboEvidenceRef | None = None
    drawdown_ref: CiboEvidenceRef | None = None
    exposure_ref: CiboEvidenceRef | None = None
    trader_attribution_ref: CiboEvidenceRef | None = None
    cibo_attribution_ref: CiboEvidenceRef | None = None
    evidence_sufficiency: CiboEvidenceSufficiency = CiboEvidenceSufficiency.UNKNOWN

    def __post_init__(self) -> None:
        for field_name in _ECONOMIC_LINK_FIELDS:
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, CiboEvidenceRef):
                raise CiboExecutiveJournalValidationError(
                    f"{field_name} must be CiboEvidenceRef or None"
                )
        if not isinstance(self.evidence_sufficiency, CiboEvidenceSufficiency):
            raise CiboExecutiveJournalValidationError(
                "economic link requires CiboEvidenceSufficiency"
            )

    def revalidate(self) -> None:
        for field_name in _ECONOMIC_LINK_FIELDS:
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, CiboEvidenceRef):
                raise CiboExecutiveJournalValidationError(
                    f"{field_name} must be CiboEvidenceRef or None"
                )
            if value is not None:
                _revalidate_ref(value, field_name=field_name)
        if not isinstance(self.evidence_sufficiency, CiboEvidenceSufficiency):
            raise CiboExecutiveJournalValidationError(
                "economic link requires CiboEvidenceSufficiency"
            )

    def logical_values(self) -> tuple[object, ...]:
        ref_values: list[object] = []
        for field_name in _ECONOMIC_LINK_FIELDS:
            ref = getattr(self, field_name)
            ref_values.append(None if ref is None else ref.value)
        return (*ref_values, self.evidence_sufficiency.value)


@dataclass(frozen=True, slots=True)
class CiboLossDiagnosis:
    """Non-causal loss/stop diagnosis; INSUFFICIENT_EVIDENCE is first-class."""

    state: CiboLossDiagnosisState
    hypotheses: tuple[CiboLossHypothesis, ...] = ()
    evidence_refs: tuple[CiboEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.state, CiboLossDiagnosisState):
            raise CiboExecutiveJournalValidationError(
                "loss diagnosis requires CiboLossDiagnosisState"
            )
        if not isinstance(self.hypotheses, tuple) or any(
            not isinstance(h, CiboLossHypothesis) for h in self.hypotheses
        ):
            raise CiboExecutiveJournalValidationError(
                "loss hypotheses must be a tuple of CiboLossHypothesis"
            )
        if len(set(self.hypotheses)) != len(self.hypotheses):
            raise CiboExecutiveJournalValidationError(
                "loss hypotheses must not contain duplicates"
            )
        object.__setattr__(
            self,
            "hypotheses",
            tuple(sorted(self.hypotheses, key=lambda h: h.value)),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_refs(self.evidence_refs, field_name="loss diagnosis evidence"),
        )
        if self.state is CiboLossDiagnosisState.INSUFFICIENT_EVIDENCE:
            if self.hypotheses:
                raise CiboExecutiveJournalValidationError(
                    "insufficient-evidence diagnosis must not assert hypotheses"
                )
        elif not self.hypotheses:
            raise CiboExecutiveJournalValidationError(
                "hypothesized diagnosis requires at least one hypothesis"
            )

    def revalidate(self) -> None:
        if not isinstance(self.state, CiboLossDiagnosisState):
            raise CiboExecutiveJournalValidationError(
                "loss diagnosis requires CiboLossDiagnosisState"
            )
        if not isinstance(self.hypotheses, tuple) or any(
            not isinstance(h, CiboLossHypothesis) for h in self.hypotheses
        ):
            raise CiboExecutiveJournalValidationError(
                "loss hypotheses must be a tuple of CiboLossHypothesis"
            )
        if self.hypotheses != tuple(sorted(self.hypotheses, key=lambda h: h.value)):
            raise CiboExecutiveJournalValidationError(
                "loss hypotheses failed canonical revalidation"
            )
        _revalidate_refs(self.evidence_refs, field_name="loss diagnosis evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.state.value,
            tuple(h.value for h in self.hypotheses),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class CiboJournalEntry:
    """One immutable, evidence-oriented executive journal episode entry."""

    entry_id: UUID
    episode_id: UUID
    kind: CiboJournalEntryKind
    subject_code: str
    recorded_at: datetime
    evidence_refs: tuple[CiboEvidenceRef, ...]
    rationale_ref: CiboEvidenceRef | None = None
    alternatives: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()
    consulted_roles: tuple[str, ...] = ()
    uncertainty: CiboUncertainty | None = None
    loss_diagnosis: CiboLossDiagnosis | None = None
    economic_link: CiboEconomicJournalLink | None = None
    expected_result_code: str | None = None
    risk_assumptions: tuple[str, ...] = ()
    counterfactual_ref: CiboEvidenceRef | None = None
    lesson_ref: CiboEvidenceRef | None = None
    confidence_before: CiboConfidence | None = None
    confidence_after: CiboConfidence | None = None
    supersedes: tuple[UUID, ...] = ()
    superseded_by: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.entry_id, UUID):
            raise CiboExecutiveJournalValidationError("journal entry id must be UUID")
        if not isinstance(self.episode_id, UUID):
            raise CiboExecutiveJournalValidationError("journal episode id must be UUID")
        if not isinstance(self.kind, CiboJournalEntryKind):
            raise CiboExecutiveJournalValidationError(
                "journal entry requires CiboJournalEntryKind"
            )
        object.__setattr__(
            self,
            "subject_code",
            _validate_code(self.subject_code, field_name="journal subject code"),
        )
        _validate_aware_datetime(self.recorded_at, field_name="journal recorded_at")
        refs = _validate_refs(self.evidence_refs, field_name="journal evidence", allow_empty=False)
        object.__setattr__(self, "evidence_refs", refs)
        if self.rationale_ref is not None and not isinstance(
            self.rationale_ref,
            CiboEvidenceRef,
        ):
            raise CiboExecutiveJournalValidationError(
                "journal rationale_ref must be CiboEvidenceRef or None"
            )
        object.__setattr__(
            self,
            "alternatives",
            _validate_codes(self.alternatives, field_name="journal alternatives"),
        )
        object.__setattr__(
            self,
            "questions",
            _validate_codes(self.questions, field_name="journal questions"),
        )
        object.__setattr__(
            self,
            "consulted_roles",
            _validate_codes(self.consulted_roles, field_name="journal consulted roles"),
        )
        if self.uncertainty is not None and not isinstance(
            self.uncertainty,
            CiboUncertainty,
        ):
            raise CiboExecutiveJournalValidationError(
                "journal uncertainty must be CiboUncertainty or None"
            )
        if self.loss_diagnosis is not None and not isinstance(
            self.loss_diagnosis,
            CiboLossDiagnosis,
        ):
            raise CiboExecutiveJournalValidationError(
                "journal loss_diagnosis must be CiboLossDiagnosis or None"
            )
        if self.economic_link is not None and not isinstance(
            self.economic_link,
            CiboEconomicJournalLink,
        ):
            raise CiboExecutiveJournalValidationError(
                "journal economic_link must be CiboEconomicJournalLink or None"
            )
        if self.expected_result_code is not None:
            object.__setattr__(
                self,
                "expected_result_code",
                _validate_code(
                    self.expected_result_code,
                    field_name="journal expected result code",
                ),
            )
        object.__setattr__(
            self,
            "risk_assumptions",
            _validate_codes(self.risk_assumptions, field_name="journal risk assumptions"),
        )
        for field_name, value in (
            ("counterfactual_ref", self.counterfactual_ref),
            ("lesson_ref", self.lesson_ref),
        ):
            if value is not None and not isinstance(value, CiboEvidenceRef):
                raise CiboExecutiveJournalValidationError(
                    f"journal {field_name} must be CiboEvidenceRef or None"
                )
        if self.confidence_before is not None and not isinstance(
            self.confidence_before,
            CiboConfidence,
        ):
            raise CiboExecutiveJournalValidationError(
                "journal confidence_before must be CiboConfidence or None"
            )
        if self.confidence_after is not None and not isinstance(
            self.confidence_after,
            CiboConfidence,
        ):
            raise CiboExecutiveJournalValidationError(
                "journal confidence_after must be CiboConfidence or None"
            )
        object.__setattr__(
            self,
            "supersedes",
            _canonical_uuid_ids(self.supersedes, field_name="journal supersedes"),
        )
        object.__setattr__(
            self,
            "superseded_by",
            _canonical_uuid_ids(self.superseded_by, field_name="journal superseded_by"),
        )
        if self.entry_id in self.supersedes or self.entry_id in self.superseded_by:
            raise CiboExecutiveJournalValidationError(
                "journal entry must not supersede or be superseded by itself"
            )

    def revalidate(self) -> None:
        if not isinstance(self.entry_id, UUID):
            raise CiboExecutiveJournalValidationError("journal entry id must be UUID")
        if not isinstance(self.episode_id, UUID):
            raise CiboExecutiveJournalValidationError("journal episode id must be UUID")
        if not isinstance(self.kind, CiboJournalEntryKind):
            raise CiboExecutiveJournalValidationError(
                "journal entry requires CiboJournalEntryKind"
            )
        _validate_code(self.subject_code, field_name="journal subject code")
        _validate_aware_datetime(self.recorded_at, field_name="journal recorded_at")
        if not self.evidence_refs:
            raise CiboExecutiveJournalValidationError("journal evidence must be non-empty")
        _revalidate_refs(self.evidence_refs, field_name="journal evidence")
        if self.rationale_ref is not None:
            if not isinstance(self.rationale_ref, CiboEvidenceRef):
                raise CiboExecutiveJournalValidationError(
                    "journal rationale_ref must be CiboEvidenceRef or None"
                )
            _revalidate_ref(self.rationale_ref, field_name="journal rationale_ref")
        for field_name, value in (
            ("alternatives", self.alternatives),
            ("questions", self.questions),
            ("consulted_roles", self.consulted_roles),
            ("risk_assumptions", self.risk_assumptions),
        ):
            if value != _validate_codes(value, field_name=f"journal {field_name}"):
                raise CiboExecutiveJournalValidationError(
                    f"journal {field_name} failed canonical revalidation"
                )
        if self.uncertainty is not None:
            if not isinstance(self.uncertainty, CiboUncertainty):
                raise CiboExecutiveJournalValidationError(
                    "journal uncertainty must be CiboUncertainty or None"
                )
            _revalidate_uncertainty(self.uncertainty)
        if self.loss_diagnosis is not None:
            if not isinstance(self.loss_diagnosis, CiboLossDiagnosis):
                raise CiboExecutiveJournalValidationError(
                    "journal loss_diagnosis must be CiboLossDiagnosis or None"
                )
            self.loss_diagnosis.revalidate()
        if self.economic_link is not None:
            if not isinstance(self.economic_link, CiboEconomicJournalLink):
                raise CiboExecutiveJournalValidationError(
                    "journal economic_link must be CiboEconomicJournalLink or None"
                )
            self.economic_link.revalidate()
        if self.expected_result_code is not None:
            _validate_code(self.expected_result_code, field_name="journal expected result code")
        for field_name, ref in (
            ("counterfactual_ref", self.counterfactual_ref),
            ("lesson_ref", self.lesson_ref),
        ):
            if ref is not None:
                if not isinstance(ref, CiboEvidenceRef):
                    raise CiboExecutiveJournalValidationError(
                        f"journal {field_name} must be CiboEvidenceRef or None"
                    )
                _revalidate_ref(ref, field_name=f"journal {field_name}")
        if self.confidence_before is not None:
            if not isinstance(self.confidence_before, CiboConfidence):
                raise CiboExecutiveJournalValidationError(
                    "journal confidence_before must be CiboConfidence or None"
                )
            _revalidate_confidence(self.confidence_before)
        if self.confidence_after is not None:
            if not isinstance(self.confidence_after, CiboConfidence):
                raise CiboExecutiveJournalValidationError(
                    "journal confidence_after must be CiboConfidence or None"
                )
            _revalidate_confidence(self.confidence_after)
        if self.supersedes != _canonical_uuid_ids(
            self.supersedes,
            field_name="journal supersedes",
        ):
            raise CiboExecutiveJournalValidationError(
                "journal supersedes failed canonical revalidation"
            )
        if self.superseded_by != _canonical_uuid_ids(
            self.superseded_by,
            field_name="journal superseded_by",
        ):
            raise CiboExecutiveJournalValidationError(
                "journal superseded_by failed canonical revalidation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.entry_id),
            str(self.episode_id),
            self.kind.value,
            self.subject_code,
            self.recorded_at.isoformat(),
            tuple(item.logical_values() for item in self.evidence_refs),
            None if self.rationale_ref is None else self.rationale_ref.value,
            self.alternatives,
            self.questions,
            self.consulted_roles,
            None if self.uncertainty is None else self.uncertainty.logical_values(),
            None if self.loss_diagnosis is None else self.loss_diagnosis.logical_values(),
            None if self.economic_link is None else self.economic_link.logical_values(),
            self.expected_result_code,
            self.risk_assumptions,
            None if self.counterfactual_ref is None else self.counterfactual_ref.value,
            None if self.lesson_ref is None else self.lesson_ref.value,
            None if self.confidence_before is None else self.confidence_before.logical_values(),
            None if self.confidence_after is None else self.confidence_after.logical_values(),
            tuple(str(v) for v in self.supersedes),
            tuple(str(v) for v in self.superseded_by),
        )


def _link_superseded_by(entry: CiboJournalEntry, superseding_id: UUID) -> CiboJournalEntry:
    return CiboJournalEntry(
        entry_id=entry.entry_id,
        episode_id=entry.episode_id,
        kind=entry.kind,
        subject_code=entry.subject_code,
        recorded_at=entry.recorded_at,
        evidence_refs=entry.evidence_refs,
        rationale_ref=entry.rationale_ref,
        alternatives=entry.alternatives,
        questions=entry.questions,
        consulted_roles=entry.consulted_roles,
        uncertainty=entry.uncertainty,
        loss_diagnosis=entry.loss_diagnosis,
        economic_link=entry.economic_link,
        expected_result_code=entry.expected_result_code,
        risk_assumptions=entry.risk_assumptions,
        counterfactual_ref=entry.counterfactual_ref,
        lesson_ref=entry.lesson_ref,
        confidence_before=entry.confidence_before,
        confidence_after=entry.confidence_after,
        supersedes=entry.supersedes,
        superseded_by=tuple(sorted({*entry.superseded_by, superseding_id})),
    )


@dataclass(frozen=True, slots=True)
class CiboJournalStore:
    """Append-only, deterministic executive journal.

    Recording returns a new store and never rewrites an existing entry's
    content. Lineage is added via explicit supersedes/superseded_by links.
    """

    entries: tuple[CiboJournalEntry, ...] = ()

    def record(
        self,
        entry: CiboJournalEntry,
    ) -> Result[CiboJournalStore, CiboExecutiveJournalError]:
        """Append one validated entry; reject duplicates and fabricated lineage."""
        if not isinstance(entry, CiboJournalEntry):
            return Failure(
                CiboExecutiveJournalValidationError("record requires CiboJournalEntry")
            )
        try:
            entry.revalidate()
        except CiboExecutiveJournalError as error:
            return Failure(
                CiboExecutiveJournalValidationError(
                    f"journal entry failed revalidation: {error}"
                )
            )
        existing_ids = {e.entry_id for e in self.entries}
        if entry.entry_id in existing_ids:
            return Failure(
                CiboExecutiveJournalValidationError("journal entry id already recorded")
            )
        for superseded_id in entry.supersedes:
            if superseded_id not in existing_ids:
                return Failure(
                    CiboExecutiveJournalValidationError(
                        "journal supersedes references an unknown entry"
                    )
                )
        rebuilt: list[CiboJournalEntry] = []
        for existing in self.entries:
            if existing.entry_id in entry.supersedes:
                rebuilt.append(_link_superseded_by(existing, entry.entry_id))
            else:
                rebuilt.append(existing)
        rebuilt.append(entry)
        return Success(CiboJournalStore(entries=tuple(rebuilt)))

    def retrieve(self, *, kind: CiboJournalEntryKind | None = None) -> tuple[CiboJournalEntry, ...]:
        """Deterministically return recorded entries, optionally by kind."""
        if kind is not None and not isinstance(kind, CiboJournalEntryKind):
            raise CiboExecutiveJournalValidationError(
                "retrieve kind must be CiboJournalEntryKind"
            )
        ordered = tuple(
            sorted(self.entries, key=lambda e: (e.recorded_at, str(e.entry_id)))
        )
        if kind is None:
            return ordered
        return tuple(entry for entry in ordered if entry.kind is kind)
