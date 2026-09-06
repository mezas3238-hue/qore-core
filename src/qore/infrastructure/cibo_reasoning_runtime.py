from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveBrain,
    CiboExecutiveDirectiveKind,
    CiboExecutiveSynthesis,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.cognitive_contracts import (
    NON_ACTIONABLE_UNCERTAINTY_KINDS,
    CiboCognitiveEvidenceRef,
    CiboCognitiveValidationError,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboFormalRecommendation,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
    contains_secret_material,
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


class CiboReasoningRuntimeError(InfrastructureError):
    """Base error for the external-engine CIBO reasoning runtime."""

    __slots__ = ()


class CiboReasoningRuntimeValidationError(CiboReasoningRuntimeError):
    """A request, engine proposal, or brain translation violated a CIBO invariant."""

    __slots__ = ()


class CiboReasoningEngineError(CiboReasoningRuntimeError):
    """The external reasoning engine could not produce an admissible proposal."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboReasoningRuntimeValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboReasoningRuntimeValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if type(value) is not str or fullmatch(_CODE_RE, value) is None:
        raise CiboReasoningRuntimeValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    if contains_secret_material(value):
        raise CiboReasoningRuntimeValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(value) is not str for value in values):
        raise CiboReasoningRuntimeValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboReasoningRuntimeValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_safe_text(value: str, *, field_name: str, max_length: int) -> str:
    if type(value) is not str or not value.strip():
        raise CiboReasoningRuntimeValidationError(f"{field_name} must be non-empty text")
    if any(ch in value for ch in "\x00\n\r\t"):
        raise CiboReasoningRuntimeValidationError(
            f"{field_name} must not contain control characters"
        )
    if len(value) > max_length:
        raise CiboReasoningRuntimeValidationError(f"{field_name} exceeds maximum length")
    if contains_secret_material(value):
        raise CiboReasoningRuntimeValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_evidence_refs(
    values: tuple[CiboCognitiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboCognitiveEvidenceRef, ...]:
    if type(values) is not tuple or any(
        type(item) is not CiboCognitiveEvidenceRef for item in values
    ):
        raise CiboReasoningRuntimeValidationError(
            f"{field_name} must be an immutable tuple of CiboCognitiveEvidenceRef"
        )
    if not values:
        raise CiboReasoningRuntimeValidationError(f"{field_name} must be non-empty")
    if len(set(values)) != len(values):
        raise CiboReasoningRuntimeValidationError(f"{field_name} must not contain duplicates")
    for item in values:
        try:
            item.revalidate()
        except CiboCognitiveValidationError as error:
            raise CiboReasoningRuntimeValidationError(
                f"{field_name} failed nested revalidation"
            ) from error
    return tuple(sorted(values, key=lambda item: item.value))


def _validate_memory_refs(values: tuple[UUID, ...]) -> tuple[UUID, ...]:
    if type(values) is not tuple or any(type(item) is not UUID for item in values):
        raise CiboReasoningRuntimeValidationError(
            "memory_refs must be an immutable tuple of UUIDs"
        )
    if len(set(values)) != len(values):
        raise CiboReasoningRuntimeValidationError("memory_refs must not contain duplicates")
    return tuple(sorted(values))


@dataclass(frozen=True, slots=True)
class CiboReasoningRequest:
    """One explicit, evidence-bound prompt presented to the external reasoning motor."""

    request_id: UUID
    subject_code: str
    asked_at: datetime
    prompt: str
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    observations: tuple[str, ...] = ()
    memory_refs: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        if type(self.request_id) is not UUID:
            raise CiboReasoningRuntimeValidationError("request_id must be UUID")
        object.__setattr__(
            self,
            "subject_code",
            _validate_code(self.subject_code, field_name="subject_code"),
        )
        _validate_aware_datetime(self.asked_at, field_name="asked_at")
        object.__setattr__(
            self,
            "prompt",
            _validate_safe_text(self.prompt, field_name="prompt", max_length=16000),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="evidence_refs"),
        )
        object.__setattr__(
            self,
            "observations",
            _validate_codes(self.observations, field_name="observations"),
        )
        object.__setattr__(self, "memory_refs", _validate_memory_refs(self.memory_refs))


@dataclass(frozen=True, slots=True)
class CiboReasoningProposal:
    """Authority-free model proposal awaiting CIBO Core validation."""

    directive: CiboExecutiveDirectiveKind
    reasoning_mode: CiboReasoningMode
    uncertainty_kind: CiboUncertaintyKind
    confidence_level: CiboConfidenceLevel | None
    used_evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    response_text: str
    recommendation_code: str | None = None
    questions: tuple[str, ...] = ()
    request_code: str | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.directive) is not CiboExecutiveDirectiveKind:
            raise CiboReasoningRuntimeValidationError(
                "proposal directive must be CiboExecutiveDirectiveKind"
            )
        if type(self.reasoning_mode) is not CiboReasoningMode:
            raise CiboReasoningRuntimeValidationError(
                "proposal reasoning_mode must be CiboReasoningMode"
            )
        if type(self.uncertainty_kind) is not CiboUncertaintyKind:
            raise CiboReasoningRuntimeValidationError(
                "proposal uncertainty_kind must be CiboUncertaintyKind"
            )
        if self.confidence_level is not None and type(
            self.confidence_level
        ) is not CiboConfidenceLevel:
            raise CiboReasoningRuntimeValidationError(
                "proposal confidence_level must be CiboConfidenceLevel or None"
            )
        if (self.uncertainty_kind is CiboUncertaintyKind.BOUNDED_CONFIDENCE) != (
            self.confidence_level is not None
        ):
            raise CiboReasoningRuntimeValidationError(
                "bounded confidence requires a confidence level; "
                "other uncertainty kinds forbid it"
            )
        object.__setattr__(
            self,
            "used_evidence_refs",
            _validate_evidence_refs(
                self.used_evidence_refs,
                field_name="used_evidence_refs",
            ),
        )
        object.__setattr__(
            self,
            "response_text",
            _validate_safe_text(
                self.response_text,
                field_name="response_text",
                max_length=4000,
            ),
        )
        if self.recommendation_code is not None:
            object.__setattr__(
                self,
                "recommendation_code",
                _validate_code(
                    self.recommendation_code,
                    field_name="recommendation_code",
                ),
            )
        object.__setattr__(
            self,
            "questions",
            _validate_codes(self.questions, field_name="questions"),
        )
        if self.request_code is not None:
            object.__setattr__(
                self,
                "request_code",
                _validate_code(self.request_code, field_name="request_code"),
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="limitations"),
        )

        if self.directive is CiboExecutiveDirectiveKind.RECOMMEND:
            if self.recommendation_code is None:
                raise CiboReasoningRuntimeValidationError(
                    "recommend proposal requires recommendation_code"
                )
            if self.questions or self.request_code is not None:
                raise CiboReasoningRuntimeValidationError(
                    "recommend proposal must not carry questions or request_code"
                )
        elif self.directive is CiboExecutiveDirectiveKind.QUESTION:
            if not self.questions:
                raise CiboReasoningRuntimeValidationError(
                    "question proposal requires at least one question code"
                )
            if self.recommendation_code is not None:
                raise CiboReasoningRuntimeValidationError(
                    "question proposal must not carry recommendation_code"
                )
        elif self.directive in (
            CiboExecutiveDirectiveKind.REQUEST_EVIDENCE,
            CiboExecutiveDirectiveKind.REQUEST_RESEARCH,
        ):
            if self.request_code is None:
                raise CiboReasoningRuntimeValidationError(
                    "request proposal requires request_code"
                )
            if self.recommendation_code is not None:
                raise CiboReasoningRuntimeValidationError(
                    "request proposal must not carry recommendation_code"
                )
        elif (
            self.recommendation_code is not None
            or self.questions
            or self.request_code is not None
        ):
            raise CiboReasoningRuntimeValidationError(
                "defer/abstain proposal must not carry recommendation, questions, or request"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.directive.value,
            self.reasoning_mode.value,
            self.uncertainty_kind.value,
            None if self.confidence_level is None else self.confidence_level.value,
            tuple(item.value for item in self.used_evidence_refs),
            self.response_text,
            self.recommendation_code,
            self.questions,
            self.request_code,
            self.limitations,
        )


class CiboReasoningEngine(Protocol):
    """External reasoning motor. It proposes; CIBO Core remains the validator."""

    def reason(
        self,
        request: CiboReasoningRequest,
    ) -> Result[CiboReasoningProposal, CiboReasoningRuntimeError]:
        """Produce one authority-free proposal from explicit request material."""
        ...


@dataclass(frozen=True, slots=True)
class CiboReasoningRuntimeResult:
    """Visible first-ignition result: validated synthesis plus non-authoritative text."""

    request_id: UUID
    synthesis: CiboExecutiveSynthesis
    response_text: str

    def __post_init__(self) -> None:
        if type(self.request_id) is not UUID:
            raise CiboReasoningRuntimeValidationError("result request_id must be UUID")
        if type(self.synthesis) is not CiboExecutiveSynthesis:
            raise CiboReasoningRuntimeValidationError(
                "result synthesis must be CiboExecutiveSynthesis"
            )
        self.synthesis.revalidate()
        _validate_safe_text(
            self.response_text,
            field_name="result response_text",
            max_length=4000,
        )


def _proposal_uuid(request_id: UUID, proposal: CiboReasoningProposal, purpose: str) -> UUID:
    logical = repr(proposal.logical_values())
    return uuid5(
        NAMESPACE_URL,
        f"qore:cibo-reasoning:{request_id}:{purpose}:{logical}",
    )


def _build_uncertainty(proposal: CiboReasoningProposal) -> CiboUncertainty:
    if proposal.uncertainty_kind is CiboUncertaintyKind.BOUNDED_CONFIDENCE:
        if proposal.confidence_level is None:
            raise CiboReasoningRuntimeValidationError(
                "bounded-confidence proposal lost its confidence level"
            )
        return CiboUncertainty(
            kind=proposal.uncertainty_kind,
            confidence=CiboConfidence(
                level=proposal.confidence_level,
                evidence_refs=proposal.used_evidence_refs,
            ),
        )
    return CiboUncertainty(kind=proposal.uncertainty_kind)


@dataclass(frozen=True, slots=True)
class CiboReasoningRuntime:
    """Governed ignition seam: engine proposal -> CIBO Executive Brain validation."""

    engine: CiboReasoningEngine
    brain: CiboExecutiveBrain = CiboExecutiveBrain()

    def run(
        self,
        request: CiboReasoningRequest,
        *,
        synthesized_at: datetime,
    ) -> Result[CiboReasoningRuntimeResult, CiboReasoningRuntimeError]:
        if type(request) is not CiboReasoningRequest:
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "runtime requires CiboReasoningRequest"
                )
            )
        try:
            CiboReasoningRequest.__post_init__(request)
            _validate_aware_datetime(synthesized_at, field_name="synthesized_at")
        except CiboReasoningRuntimeError as error:
            return Failure(error)
        if synthesized_at < request.asked_at:
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "synthesized_at must not predate asked_at"
                )
            )

        proposed = self.engine.reason(request)
        if isinstance(proposed, Failure):
            return proposed
        proposal = proposed.value
        if type(proposal) is not CiboReasoningProposal:
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "reasoning engine returned an invalid proposal type"
                )
            )
        try:
            CiboReasoningProposal.__post_init__(proposal)
        except CiboReasoningRuntimeError as error:
            return Failure(error)

        allowed = set(request.evidence_refs)
        if any(ref not in allowed for ref in proposal.used_evidence_refs):
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "reasoning engine attempted to invent or substitute evidence"
                )
            )

        try:
            uncertainty = _build_uncertainty(proposal)
            recommendation: CiboFormalRecommendation | None = None
            if proposal.directive is CiboExecutiveDirectiveKind.RECOMMEND:
                if proposal.recommendation_code is None:
                    return Failure(
                        CiboReasoningRuntimeValidationError(
                            "recommend proposal lost recommendation_code"
                        )
                    )
                recommendation = CiboFormalRecommendation(
                    recommendation_id=_proposal_uuid(
                        request.request_id,
                        proposal,
                        "recommendation",
                    ),
                    recommendation_code=proposal.recommendation_code,
                    reasoning_mode=proposal.reasoning_mode,
                    summary=proposal.response_text,
                    evidence_refs=proposal.used_evidence_refs,
                    uncertainty=uncertainty,
                    issued_at=synthesized_at,
                )
        except (CiboCognitiveValidationError, CiboReasoningRuntimeError) as error:
            return Failure(
                CiboReasoningRuntimeValidationError(
                    f"proposal could not be translated into CIBO contracts: {error}"
                )
            )

        if (
            proposal.directive is CiboExecutiveDirectiveKind.RECOMMEND
            and proposal.uncertainty_kind in NON_ACTIONABLE_UNCERTAINTY_KINDS
        ):
            return Failure(
                CiboReasoningRuntimeValidationError(
                    "non-actionable uncertainty cannot become a recommendation"
                )
            )

        synthesis = self.brain.synthesize(
            synthesis_id=_proposal_uuid(request.request_id, proposal, "synthesis"),
            directive=proposal.directive,
            reasoning_mode=proposal.reasoning_mode,
            subject_code=request.subject_code,
            synthesized_at=synthesized_at,
            evidence_refs=proposal.used_evidence_refs,
            uncertainty=uncertainty,
            observations=request.observations,
            memory_refs=request.memory_refs,
            recommendation=recommendation,
            questions=proposal.questions,
            request_code=proposal.request_code,
            limitations=proposal.limitations,
        )
        if isinstance(synthesis, Failure):
            return Failure(
                CiboReasoningRuntimeValidationError(
                    f"CIBO Executive Brain rejected engine proposal: {synthesis.error}"
                )
            )
        try:
            return Success(
                CiboReasoningRuntimeResult(
                    request_id=request.request_id,
                    synthesis=synthesis.value,
                    response_text=proposal.response_text,
                )
            )
        except CiboReasoningRuntimeError as error:
            return Failure(error)
