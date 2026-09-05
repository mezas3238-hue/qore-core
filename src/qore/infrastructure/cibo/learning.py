"""CF-19 — Learning from Governed Experience.

A lesson is an opinionated, evidence-backed record; it NEVER rewrites code/config
(no such fields exist). A lesson may only be ACCEPTED when evidence is sufficient;
otherwise it may only be REJECTED (or left unaccepted).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalBlockedError,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    _validate_code,
    _validate_codes,
    _validate_evidence_refs,
    _validate_timestamp,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCapabilityProfileValidationError,
    CiboEvidenceRef,
)
from qore.kernel.result import Failure, Result, Success


class CiboLessonState(StrEnum):
    """Lesson governance state; never a code/config rewrite."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


def _revalidate_evidence(evidence: CiboFunctionalEvidence) -> None:
    try:
        CiboFunctionalEvidence.__post_init__(evidence)
    except CiboFunctionalError:
        raise
    except (AttributeError, TypeError):
        raise CiboFunctionalValidationError(
            "evidence must be a valid CiboFunctionalEvidence"
        ) from None


def _validate_outcome_ref(value: CiboEvidenceRef) -> CiboEvidenceRef:
    if not isinstance(value, CiboEvidenceRef):
        raise CiboFunctionalValidationError("outcome ref must be a CiboEvidenceRef")
    try:
        CiboEvidenceRef.__post_init__(value)
    except (CiboCapabilityProfileValidationError, AttributeError, TypeError):
        raise CiboFunctionalValidationError(
            "outcome ref must be a valid CiboEvidenceRef"
        ) from None
    return value


def _decimal_logical(value: Decimal) -> str:
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class CiboLesson:
    """Immutable opinion-only lesson; no code/config rewrite fields exist.

    An ACCEPTED lesson must be backed by sufficient functional evidence; direct
    construction cannot mint an accepted lesson without it, matching the
    ``CiboLearning.accept`` builder ceiling.
    """

    lesson_code: str
    outcome_ref: CiboEvidenceRef
    provenance_codes: tuple[str, ...]
    confidence: Decimal
    evidence_refs: tuple[CiboEvidenceRef, ...]
    evidence: CiboFunctionalEvidence
    applicability_code: str
    state: CiboLessonState
    decided_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "lesson_code",
            _validate_code(self.lesson_code, field_name="lesson code"),
        )
        object.__setattr__(
            self,
            "outcome_ref",
            _validate_outcome_ref(self.outcome_ref),
        )
        object.__setattr__(
            self,
            "provenance_codes",
            _validate_codes(self.provenance_codes, field_name="provenance codes"),
        )
        if not isinstance(self.confidence, Decimal) or not self.confidence.is_finite():
            raise CiboFunctionalValidationError(
                "lesson confidence must be a finite Decimal"
            )
        if self.confidence < Decimal(0) or self.confidence > Decimal(1):
            raise CiboFunctionalValidationError(
                "lesson confidence must be within the closed interval [0, 1]"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="evidence refs"),
        )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "lesson requires CiboFunctionalEvidence"
            )
        _revalidate_evidence(self.evidence)
        object.__setattr__(
            self,
            "applicability_code",
            _validate_code(self.applicability_code, field_name="applicability code"),
        )
        if type(self.state) is not CiboLessonState:
            raise CiboFunctionalValidationError("lesson requires CiboLessonState")
        _validate_timestamp(self.decided_at, field_name="lesson decided_at")
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError("lesson authority must be opinion")
        if (
            self.state is CiboLessonState.ACCEPTED
            and self.evidence.status is not CiboEvidenceStatus.SUFFICIENT
        ):
            raise CiboFunctionalValidationError(
                "accepted lesson requires sufficient evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.lesson_code,
            self.outcome_ref.logical_values(),
            self.provenance_codes,
            _decimal_logical(self.confidence),
            tuple(item.logical_values() for item in self.evidence_refs),
            self.evidence.logical_values(),
            self.applicability_code,
            self.state.value,
            self.decided_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboLearning:
    """Deterministic, stateless learning-from-experience governance."""

    def _build(
        self,
        evidence: CiboFunctionalEvidence,
        *,
        state: CiboLessonState,
        lesson_code: str,
        outcome_ref: CiboEvidenceRef,
        provenance_codes: tuple[str, ...],
        confidence: Decimal,
        evidence_refs: tuple[CiboEvidenceRef, ...],
        applicability_code: str,
        decided_at: datetime,
    ) -> Result[CiboLesson, CiboFunctionalError]:
        try:
            return Success(
                CiboLesson(
                    lesson_code=lesson_code,
                    outcome_ref=outcome_ref,
                    provenance_codes=provenance_codes,
                    confidence=confidence,
                    evidence_refs=evidence_refs,
                    evidence=evidence,
                    applicability_code=applicability_code,
                    state=state,
                    decided_at=decided_at,
                    authority=CiboFunctionalAuthority.OPINION,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)

    def accept(
        self,
        evidence: CiboFunctionalEvidence,
        *,
        lesson_code: str,
        outcome_ref: CiboEvidenceRef,
        provenance_codes: tuple[str, ...],
        confidence: Decimal,
        evidence_refs: tuple[CiboEvidenceRef, ...],
        applicability_code: str,
        decided_at: datetime,
    ) -> Result[CiboLesson, CiboFunctionalError]:
        """Accept a lesson only on sufficient evidence."""
        if not isinstance(evidence, CiboFunctionalEvidence):
            return Failure(
                CiboFunctionalValidationError("evidence must be CiboFunctionalEvidence")
            )
        try:
            _revalidate_evidence(evidence)
        except CiboFunctionalError as error:
            return Failure(error)
        if evidence.status is not CiboEvidenceStatus.SUFFICIENT:
            return Failure(
                CiboFunctionalBlockedError(
                    "accepted lesson requires sufficient evidence"
                )
            )
        return self._build(
            evidence,
            state=CiboLessonState.ACCEPTED,
            lesson_code=lesson_code,
            outcome_ref=outcome_ref,
            provenance_codes=provenance_codes,
            confidence=confidence,
            evidence_refs=evidence_refs,
            applicability_code=applicability_code,
            decided_at=decided_at,
        )

    def reject(
        self,
        evidence: CiboFunctionalEvidence,
        *,
        lesson_code: str,
        outcome_ref: CiboEvidenceRef,
        provenance_codes: tuple[str, ...],
        confidence: Decimal,
        evidence_refs: tuple[CiboEvidenceRef, ...],
        applicability_code: str,
        decided_at: datetime,
    ) -> Result[CiboLesson, CiboFunctionalError]:
        """Reject a lesson; rejection requires no sufficient evidence."""
        if not isinstance(evidence, CiboFunctionalEvidence):
            return Failure(
                CiboFunctionalValidationError("evidence must be CiboFunctionalEvidence")
            )
        try:
            _revalidate_evidence(evidence)
        except CiboFunctionalError as error:
            return Failure(error)
        return self._build(
            evidence,
            state=CiboLessonState.REJECTED,
            lesson_code=lesson_code,
            outcome_ref=outcome_ref,
            provenance_codes=provenance_codes,
            confidence=confidence,
            evidence_refs=evidence_refs,
            applicability_code=applicability_code,
            decided_at=decided_at,
        )
