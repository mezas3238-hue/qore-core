"""Provider-neutral CIBO Cognitive Executive contracts.

This module defines the pure, deterministic semantic foundation for CIBO as a
Cognitive Executive Director. It is intentionally free of any concrete LLM,
model, provider, adapter, or execution authority: it only shapes reasoning
modes, epistemic states, uncertainty, deliberation roles, and formal
recommendations.

Canonical law enforced here:

- CIBO INTELLIGENCE != UNBOUNDED AUTHORITY
- CIBO RECOMMENDATION != RISK BYPASS
- CIBO REASONING != PROVIDER-NATIVE ORDER
- FORMAL_RECOMMENDATION != AUTHORIZED_ACTION

No value object in this module carries an order, intent, account, credential,
quantity, instrument, provider, or promotion field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.kernel.errors import DomainError

_CODE_RE = r"[a-z][a-z0-9._-]*"
_OPAQUE_REF_RE = r"[a-z][a-z0-9._:/-]*"

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)

_CONTROL_CHARS = "\x00\n\r\t"


class CiboCognitiveError(DomainError):
    """Base error for CIBO Cognitive Executive provider-neutral contracts."""

    __slots__ = ()


class CiboCognitiveValidationError(CiboCognitiveError):
    """A CIBO cognitive value violates a deterministic provider-neutral invariant."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CiboCognitiveValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCognitiveValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboCognitiveValidationError(
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
        raise CiboCognitiveValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(v, field_name=field_name) for v in values)
    if len(set(normalized)) != len(normalized):
        raise CiboCognitiveValidationError(f"{field_name} must not contain duplicates")
    if not allow_empty and not normalized:
        raise CiboCognitiveValidationError(f"{field_name} must be non-empty")
    return tuple(sorted(normalized))


def _validate_opaque_ref(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_OPAQUE_REF_RE, value) is None:
        raise CiboCognitiveValidationError(
            f"{field_name} must use canonical opaque-reference syntax"
        )
    lowered = value.lower()
    if any(part in lowered for part in _SENSITIVE_PARTS):
        raise CiboCognitiveValidationError(f"{field_name} must not contain sensitive material")
    return value


def _validate_safe_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CiboCognitiveValidationError(f"{field_name} must be non-empty text")
    if any(ch in value for ch in _CONTROL_CHARS):
        raise CiboCognitiveValidationError(f"{field_name} must not contain control characters")
    lowered = value.lower()
    if any(part in lowered for part in _SENSITIVE_PARTS):
        raise CiboCognitiveValidationError(f"{field_name} must not contain sensitive material")
    return value


def _canonical_evidence_refs(
    values: tuple[CiboCognitiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboCognitiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboCognitiveEvidenceRef) for item in values
    ):
        raise CiboCognitiveValidationError(
            f"{field_name} must be an immutable tuple of CiboCognitiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboCognitiveValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


class CiboReasoningMode(StrEnum):
    """Reasoning-policy semantics, never a concrete model/token/API setting."""

    FAST = "fast"
    HIGH = "high"
    MAX = "max"
    COUNCIL_ADVERSARIAL = "council-adversarial"


class CiboEpistemicState(StrEnum):
    """Epistemic strength of a CIBO cognitive statement. None is an action."""

    OBSERVATION = "observation"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    OPINION = "opinion"
    FORMAL_RECOMMENDATION = "formal-recommendation"


class CiboUncertaintyKind(StrEnum):
    """Explicit uncertainty outcomes; bounded confidence is only one possibility."""

    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    UNRESOLVED_CONTRADICTION = "unresolved-contradiction"
    COMPETING_HYPOTHESES = "competing-hypotheses"
    MORE_EVIDENCE_REQUESTED = "more-evidence-requested"
    ABSTAIN_DEFER = "abstain-defer"
    BOUNDED_CONFIDENCE = "bounded-confidence"


class CiboConfidenceLevel(StrEnum):
    """Bounded confidence levels; never a raw float or bool."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class CiboCognitiveEvidenceRef:
    """Opaque sanitized reference to evidence stored outside the cognitive value."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_opaque_ref(self.value, field_name="CIBO cognitive evidence ref"),
        )

    def revalidate(self) -> None:
        _validate_opaque_ref(self.value, field_name="CIBO cognitive evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboDeliberationRole:
    """Canonical provider-neutral deliberation faculty/role identity.

    A role emits an evidence-bound argument, critique, or opinion; it carries no
    operational privilege and no execution/promotion authority.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="CIBO deliberation role"),
        )

    def revalidate(self) -> None:
        _validate_code(self.value, field_name="CIBO deliberation role")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboConfidence:
    """Bounded confidence that is always justified by explicit evidence."""

    level: CiboConfidenceLevel
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.level, CiboConfidenceLevel):
            raise CiboCognitiveValidationError(
                "CIBO confidence requires CiboConfidenceLevel"
            )
        refs = _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO confidence evidence",
        )
        if not refs:
            raise CiboCognitiveValidationError(
                "bounded confidence requires explicit backing evidence"
            )
        object.__setattr__(self, "evidence_refs", refs)

    def revalidate(self) -> None:
        if not isinstance(self.level, CiboConfidenceLevel):
            raise CiboCognitiveValidationError(
                "CIBO confidence requires CiboConfidenceLevel"
            )
        if not self.evidence_refs:
            raise CiboCognitiveValidationError(
                "bounded confidence requires explicit backing evidence"
            )
        if self.evidence_refs != _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO confidence evidence",
        ):
            raise CiboCognitiveValidationError(
                "CIBO confidence evidence failed canonical revalidation"
            )
        for ref in self.evidence_refs:
            ref.revalidate()

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.level.value,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class CiboUncertainty:
    """Explicit uncertainty carried by a cognitive statement.

    BOUNDED_CONFIDENCE requires a ``CiboConfidence``; COMPETING_HYPOTHESES and
    UNRESOLVED_CONTRADICTION require non-empty detail codes so uncertainty is
    never collapsed into fabricated certainty.
    """

    kind: CiboUncertaintyKind
    detail_codes: tuple[str, ...] = ()
    confidence: CiboConfidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CiboUncertaintyKind):
            raise CiboCognitiveValidationError(
                "CIBO uncertainty requires CiboUncertaintyKind"
            )
        object.__setattr__(
            self,
            "detail_codes",
            _validate_codes(self.detail_codes, field_name="CIBO uncertainty detail"),
        )
        if self.kind is CiboUncertaintyKind.BOUNDED_CONFIDENCE:
            if not isinstance(self.confidence, CiboConfidence):
                raise CiboCognitiveValidationError(
                    "bounded confidence uncertainty requires CiboConfidence"
                )
            if self.detail_codes:
                raise CiboCognitiveValidationError(
                    "bounded confidence uncertainty must not carry detail codes"
                )
        else:
            if self.confidence is not None:
                raise CiboCognitiveValidationError(
                    "non-bounded uncertainty must not carry confidence"
                )
            if self.kind in (
                CiboUncertaintyKind.COMPETING_HYPOTHESES,
                CiboUncertaintyKind.UNRESOLVED_CONTRADICTION,
            ) and not self.detail_codes:
                raise CiboCognitiveValidationError(
                    f"{self.kind.value} uncertainty requires detail codes"
                )

    def revalidate(self) -> None:
        if not isinstance(self.kind, CiboUncertaintyKind):
            raise CiboCognitiveValidationError(
                "CIBO uncertainty requires CiboUncertaintyKind"
            )
        if self.detail_codes != _validate_codes(
            self.detail_codes,
            field_name="CIBO uncertainty detail",
        ):
            raise CiboCognitiveValidationError(
                "CIBO uncertainty detail failed canonical revalidation"
            )
        if self.kind is CiboUncertaintyKind.BOUNDED_CONFIDENCE:
            if not isinstance(self.confidence, CiboConfidence):
                raise CiboCognitiveValidationError(
                    "bounded confidence uncertainty requires CiboConfidence"
                )
            if self.detail_codes:
                raise CiboCognitiveValidationError(
                    "bounded confidence uncertainty must not carry detail codes"
                )
            self.confidence.revalidate()
        elif self.confidence is not None:
            raise CiboCognitiveValidationError(
                "non-bounded uncertainty must not carry confidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.detail_codes,
            None if self.confidence is None else self.confidence.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CiboEpistemicClaim:
    """One evidence-bound cognitive statement (observation/…/hypothesis/opinion)."""

    claim_id: UUID
    epistemic_state: CiboEpistemicState
    reasoning_mode: CiboReasoningMode
    content_code: str
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    uncertainty: CiboUncertainty
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.claim_id, UUID):
            raise CiboCognitiveValidationError("CIBO epistemic claim id must be UUID")
        if not isinstance(self.epistemic_state, CiboEpistemicState):
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboEpistemicState"
            )
        if self.epistemic_state is CiboEpistemicState.FORMAL_RECOMMENDATION:
            raise CiboCognitiveValidationError(
                "formal recommendations must use CiboFormalRecommendation"
            )
        if not isinstance(self.reasoning_mode, CiboReasoningMode):
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboReasoningMode"
            )
        object.__setattr__(
            self,
            "content_code",
            _validate_code(self.content_code, field_name="CIBO claim content code"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _canonical_evidence_refs(self.evidence_refs, field_name="CIBO claim evidence"),
        )
        if not isinstance(self.uncertainty, CiboUncertainty):
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboUncertainty"
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="CIBO claim limitations"),
        )

    def revalidate(self) -> None:
        if not isinstance(self.claim_id, UUID):
            raise CiboCognitiveValidationError("CIBO epistemic claim id must be UUID")
        if not isinstance(self.epistemic_state, CiboEpistemicState):
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboEpistemicState"
            )
        if not isinstance(self.reasoning_mode, CiboReasoningMode):
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboReasoningMode"
            )
        _validate_code(self.content_code, field_name="CIBO claim content code")
        if self.evidence_refs != _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO claim evidence",
        ):
            raise CiboCognitiveValidationError(
                "CIBO claim evidence failed canonical revalidation"
            )
        for ref in self.evidence_refs:
            ref.revalidate()
        if not isinstance(self.uncertainty, CiboUncertainty):
            raise CiboCognitiveValidationError(
                "CIBO epistemic claim requires CiboUncertainty"
            )
        self.uncertainty.revalidate()
        if self.limitations != _validate_codes(
            self.limitations,
            field_name="CIBO claim limitations",
        ):
            raise CiboCognitiveValidationError(
                "CIBO claim limitations failed canonical revalidation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.claim_id),
            self.epistemic_state.value,
            self.reasoning_mode.value,
            self.content_code,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.uncertainty.logical_values(),
            self.limitations,
        )


@dataclass(frozen=True, slots=True)
class CiboFormalRecommendation:
    """A formal, evidence-bound recommendation. Advisory only: never an action.

    This value object deliberately exposes no order, intent, account, quantity,
    instrument, provider, promotion, or authorization field. Downstream
    operational authority can only be created by separate Policy/Risk/Execution
    contracts, never by this recommendation.
    """

    recommendation_id: UUID
    recommendation_code: str
    reasoning_mode: CiboReasoningMode
    summary: str
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    uncertainty: CiboUncertainty
    issued_at: datetime
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.recommendation_id, UUID):
            raise CiboCognitiveValidationError(
                "CIBO recommendation id must be UUID"
            )
        object.__setattr__(
            self,
            "recommendation_code",
            _validate_code(self.recommendation_code, field_name="CIBO recommendation code"),
        )
        if not isinstance(self.reasoning_mode, CiboReasoningMode):
            raise CiboCognitiveValidationError(
                "CIBO recommendation requires CiboReasoningMode"
            )
        object.__setattr__(
            self,
            "summary",
            _validate_safe_text(self.summary, field_name="CIBO recommendation summary"),
        )
        refs = _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO recommendation evidence",
        )
        if not refs:
            raise CiboCognitiveValidationError(
                "a formal recommendation requires explicit backing evidence"
            )
        object.__setattr__(self, "evidence_refs", refs)
        if not isinstance(self.uncertainty, CiboUncertainty):
            raise CiboCognitiveValidationError(
                "CIBO recommendation requires CiboUncertainty"
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="CIBO recommendation limitations"),
        )
        _validate_aware_datetime(self.issued_at, field_name="CIBO recommendation issued_at")

    @property
    def epistemic_state(self) -> CiboEpistemicState:
        """A formal recommendation is FORMAL_RECOMMENDATION, never an action."""
        return CiboEpistemicState.FORMAL_RECOMMENDATION

    def revalidate(self) -> None:
        if not isinstance(self.recommendation_id, UUID):
            raise CiboCognitiveValidationError("CIBO recommendation id must be UUID")
        _validate_code(self.recommendation_code, field_name="CIBO recommendation code")
        if not isinstance(self.reasoning_mode, CiboReasoningMode):
            raise CiboCognitiveValidationError(
                "CIBO recommendation requires CiboReasoningMode"
            )
        _validate_safe_text(self.summary, field_name="CIBO recommendation summary")
        if not self.evidence_refs:
            raise CiboCognitiveValidationError(
                "a formal recommendation requires explicit backing evidence"
            )
        if self.evidence_refs != _canonical_evidence_refs(
            self.evidence_refs,
            field_name="CIBO recommendation evidence",
        ):
            raise CiboCognitiveValidationError(
                "CIBO recommendation evidence failed canonical revalidation"
            )
        for ref in self.evidence_refs:
            ref.revalidate()
        if not isinstance(self.uncertainty, CiboUncertainty):
            raise CiboCognitiveValidationError(
                "CIBO recommendation requires CiboUncertainty"
            )
        self.uncertainty.revalidate()
        if self.limitations != _validate_codes(
            self.limitations,
            field_name="CIBO recommendation limitations",
        ):
            raise CiboCognitiveValidationError(
                "CIBO recommendation limitations failed canonical revalidation"
            )
        _validate_aware_datetime(self.issued_at, field_name="CIBO recommendation issued_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.recommendation_id),
            self.recommendation_code,
            self.reasoning_mode.value,
            self.summary,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.uncertainty.logical_values(),
            self.limitations,
            self.issued_at.isoformat(),
        )
