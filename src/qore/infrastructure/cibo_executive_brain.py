"""Provider-neutral CIBO executive brain orchestration seam.

The brain combines observations, memory references, evidence, and optional
deliberation/critique into a typed executive directive (recommend, question,
defer, request evidence/research, or abstain). Its output is advisory and can
never construct a provider order, authorize execution, bypass Risk, or promote a
Trader: downstream authority is only created by separate Policy/Risk/Execution
contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboCognitiveValidationError,
    CiboFormalRecommendation,
    CiboReasoningMode,
    CiboUncertainty,
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


class CiboExecutiveBrainError(InfrastructureError):
    """Base error for the CIBO executive brain orchestration seam."""

    __slots__ = ()


class CiboExecutiveBrainValidationError(CiboExecutiveBrainError):
    """A brain directive violates a deterministic authority-boundary invariant."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CiboExecutiveBrainValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboExecutiveBrainValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboExecutiveBrainValidationError(
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
        raise CiboExecutiveBrainValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(v, field_name=field_name) for v in values)
    if len(set(normalized)) != len(normalized):
        raise CiboExecutiveBrainValidationError(f"{field_name} must not contain duplicates")
    if not allow_empty and not normalized:
        raise CiboExecutiveBrainValidationError(f"{field_name} must be non-empty")
    return tuple(sorted(normalized))


def _canonical_refs(
    values: tuple[CiboCognitiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboCognitiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboCognitiveEvidenceRef) for item in values
    ):
        raise CiboExecutiveBrainValidationError(
            f"{field_name} must be an immutable tuple of CiboCognitiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveBrainValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


def _revalidate_refs(
    values: tuple[CiboCognitiveEvidenceRef, ...],
    *,
    field_name: str,
) -> None:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboCognitiveEvidenceRef) for item in values
    ):
        raise CiboExecutiveBrainValidationError(
            f"{field_name} must be an immutable tuple of CiboCognitiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveBrainValidationError(f"{field_name} must not contain duplicates")
    if values != tuple(sorted(values, key=lambda item: item.value)):
        raise CiboExecutiveBrainValidationError(
            f"{field_name} failed canonical revalidation"
        )
    for ref in values:
        try:
            ref.revalidate()
        except CiboCognitiveValidationError as error:
            raise CiboExecutiveBrainValidationError(
                f"{field_name} failed nested revalidation"
            ) from error


def _canonical_uuid_ids(values: tuple[UUID, ...], *, field_name: str) -> tuple[UUID, ...]:
    if not isinstance(values, tuple) or any(not isinstance(v, UUID) for v in values):
        raise CiboExecutiveBrainValidationError(
            f"{field_name} must be an immutable tuple of UUIDs"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveBrainValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values))


def _revalidate_uncertainty(uncertainty: CiboUncertainty) -> None:
    try:
        uncertainty.revalidate()
    except CiboCognitiveValidationError as error:
        raise CiboExecutiveBrainValidationError(
            "brain uncertainty failed revalidation"
        ) from error


def _revalidate_recommendation(recommendation: CiboFormalRecommendation) -> None:
    try:
        recommendation.revalidate()
    except CiboCognitiveValidationError as error:
        raise CiboExecutiveBrainValidationError(
            "brain recommendation failed revalidation"
        ) from error


class CiboExecutiveDirectiveKind(StrEnum):
    """Typed executive directive; a request for later Policy/Risk, never an order."""

    RECOMMEND = "recommend"
    QUESTION = "question"
    DEFER = "defer"
    REQUEST_EVIDENCE = "request-evidence"
    REQUEST_RESEARCH = "request-research"
    ABSTAIN = "abstain"


@dataclass(frozen=True, slots=True)
class CiboExecutiveSynthesis:
    """The advisory output of the executive brain. It carries no authority."""

    synthesis_id: UUID
    directive: CiboExecutiveDirectiveKind
    reasoning_mode: CiboReasoningMode
    subject_code: str
    synthesized_at: datetime
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    uncertainty: CiboUncertainty
    observations: tuple[str, ...] = ()
    memory_refs: tuple[UUID, ...] = ()
    deliberation_ref: UUID | None = None
    recommendation: CiboFormalRecommendation | None = None
    questions: tuple[str, ...] = ()
    request_code: str | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.synthesis_id, UUID):
            raise CiboExecutiveBrainValidationError("synthesis id must be UUID")
        if not isinstance(self.directive, CiboExecutiveDirectiveKind):
            raise CiboExecutiveBrainValidationError(
                "synthesis requires CiboExecutiveDirectiveKind"
            )
        if not isinstance(self.reasoning_mode, CiboReasoningMode):
            raise CiboExecutiveBrainValidationError(
                "synthesis requires CiboReasoningMode"
            )
        object.__setattr__(
            self,
            "subject_code",
            _validate_code(self.subject_code, field_name="synthesis subject code"),
        )
        _validate_aware_datetime(self.synthesized_at, field_name="synthesis synthesized_at")
        refs = _canonical_refs(self.evidence_refs, field_name="synthesis evidence")
        if not refs:
            raise CiboExecutiveBrainValidationError(
                "synthesis requires explicit backing evidence"
            )
        object.__setattr__(self, "evidence_refs", refs)
        if not isinstance(self.uncertainty, CiboUncertainty):
            raise CiboExecutiveBrainValidationError(
                "synthesis requires CiboUncertainty"
            )
        object.__setattr__(
            self,
            "observations",
            _validate_codes(self.observations, field_name="synthesis observations"),
        )
        object.__setattr__(
            self,
            "memory_refs",
            _canonical_uuid_ids(self.memory_refs, field_name="synthesis memory refs"),
        )
        if self.deliberation_ref is not None and not isinstance(
            self.deliberation_ref,
            UUID,
        ):
            raise CiboExecutiveBrainValidationError(
                "synthesis deliberation_ref must be UUID or None"
            )
        if self.recommendation is not None and not isinstance(
            self.recommendation,
            CiboFormalRecommendation,
        ):
            raise CiboExecutiveBrainValidationError(
                "synthesis recommendation must be CiboFormalRecommendation or None"
            )
        object.__setattr__(
            self,
            "questions",
            _validate_codes(self.questions, field_name="synthesis questions"),
        )
        if self.request_code is not None:
            object.__setattr__(
                self,
                "request_code",
                _validate_code(self.request_code, field_name="synthesis request code"),
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="synthesis limitations"),
        )
        if self.directive is CiboExecutiveDirectiveKind.RECOMMEND:
            if self.recommendation is None:
                raise CiboExecutiveBrainValidationError(
                    "recommend directive requires a formal recommendation"
                )
            if self.questions or self.request_code is not None:
                raise CiboExecutiveBrainValidationError(
                    "recommend directive must not carry questions or a request code"
                )
        elif self.directive is CiboExecutiveDirectiveKind.QUESTION:
            if not self.questions:
                raise CiboExecutiveBrainValidationError(
                    "question directive requires at least one question"
                )
            if self.recommendation is not None:
                raise CiboExecutiveBrainValidationError(
                    "question directive must not carry a recommendation"
                )
        elif self.directive in (
            CiboExecutiveDirectiveKind.REQUEST_EVIDENCE,
            CiboExecutiveDirectiveKind.REQUEST_RESEARCH,
        ):
            if self.request_code is None:
                raise CiboExecutiveBrainValidationError(
                    "request directive requires a request code"
                )
            if self.recommendation is not None:
                raise CiboExecutiveBrainValidationError(
                    "request directive must not carry a recommendation"
                )
        elif self.recommendation is not None or self.questions or self.request_code is not None:
            raise CiboExecutiveBrainValidationError(
                "defer/abstain directive must not carry recommendation, questions, or request"
            )

    def revalidate(self) -> None:
        if not isinstance(self.synthesis_id, UUID):
            raise CiboExecutiveBrainValidationError("synthesis id must be UUID")
        if not isinstance(self.directive, CiboExecutiveDirectiveKind):
            raise CiboExecutiveBrainValidationError(
                "synthesis requires CiboExecutiveDirectiveKind"
            )
        if not isinstance(self.reasoning_mode, CiboReasoningMode):
            raise CiboExecutiveBrainValidationError("synthesis requires CiboReasoningMode")
        _validate_code(self.subject_code, field_name="synthesis subject code")
        _validate_aware_datetime(self.synthesized_at, field_name="synthesis synthesized_at")
        if not self.evidence_refs:
            raise CiboExecutiveBrainValidationError(
                "synthesis requires explicit backing evidence"
            )
        _revalidate_refs(self.evidence_refs, field_name="synthesis evidence")
        if not isinstance(self.uncertainty, CiboUncertainty):
            raise CiboExecutiveBrainValidationError("synthesis requires CiboUncertainty")
        _revalidate_uncertainty(self.uncertainty)
        if self.observations != _validate_codes(
            self.observations,
            field_name="synthesis observations",
        ):
            raise CiboExecutiveBrainValidationError(
                "synthesis observations failed canonical revalidation"
            )
        if self.memory_refs != _canonical_uuid_ids(
            self.memory_refs,
            field_name="synthesis memory refs",
        ):
            raise CiboExecutiveBrainValidationError(
                "synthesis memory refs failed canonical revalidation"
            )
        if self.deliberation_ref is not None and not isinstance(
            self.deliberation_ref,
            UUID,
        ):
            raise CiboExecutiveBrainValidationError(
                "synthesis deliberation_ref must be UUID or None"
            )
        if self.recommendation is not None:
            if not isinstance(self.recommendation, CiboFormalRecommendation):
                raise CiboExecutiveBrainValidationError(
                    "synthesis recommendation must be CiboFormalRecommendation or None"
                )
            _revalidate_recommendation(self.recommendation)
        if self.questions != _validate_codes(
            self.questions,
            field_name="synthesis questions",
        ):
            raise CiboExecutiveBrainValidationError(
                "synthesis questions failed canonical revalidation"
            )
        if self.request_code is not None:
            _validate_code(self.request_code, field_name="synthesis request code")
        if self.limitations != _validate_codes(
            self.limitations,
            field_name="synthesis limitations",
        ):
            raise CiboExecutiveBrainValidationError(
                "synthesis limitations failed canonical revalidation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.synthesis_id),
            self.directive.value,
            self.reasoning_mode.value,
            self.subject_code,
            self.synthesized_at.isoformat(),
            tuple(item.logical_values() for item in self.evidence_refs),
            self.uncertainty.logical_values(),
            self.observations,
            tuple(str(v) for v in self.memory_refs),
            None if self.deliberation_ref is None else str(self.deliberation_ref),
            None if self.recommendation is None else self.recommendation.logical_values(),
            self.questions,
            self.request_code,
            self.limitations,
        )


@dataclass(frozen=True, slots=True)
class CiboExecutiveBrain:
    """Pure, provider-neutral, deterministic executive orchestration seam."""

    def synthesize(
        self,
        *,
        synthesis_id: UUID,
        directive: CiboExecutiveDirectiveKind,
        reasoning_mode: CiboReasoningMode,
        subject_code: str,
        synthesized_at: datetime,
        evidence_refs: tuple[CiboCognitiveEvidenceRef, ...],
        uncertainty: CiboUncertainty,
        observations: tuple[str, ...] = (),
        memory_refs: tuple[UUID, ...] = (),
        deliberation_ref: UUID | None = None,
        recommendation: CiboFormalRecommendation | None = None,
        questions: tuple[str, ...] = (),
        request_code: str | None = None,
        limitations: tuple[str, ...] = (),
    ) -> Result[CiboExecutiveSynthesis, CiboExecutiveBrainError]:
        """Combine evidence/memory/deliberation into an advisory directive."""
        try:
            return Success(
                CiboExecutiveSynthesis(
                    synthesis_id=synthesis_id,
                    directive=directive,
                    reasoning_mode=reasoning_mode,
                    subject_code=subject_code,
                    synthesized_at=synthesized_at,
                    evidence_refs=evidence_refs,
                    uncertainty=uncertainty,
                    observations=observations,
                    memory_refs=memory_refs,
                    deliberation_ref=deliberation_ref,
                    recommendation=recommendation,
                    questions=questions,
                    request_code=request_code,
                    limitations=limitations,
                )
            )
        except CiboExecutiveBrainError as error:
            return Failure(error)
