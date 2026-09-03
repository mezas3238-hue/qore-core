"""Adversarial CIBO council deliberation foundations.

A deliberation retains independent, evidence-bound positions and never collapses
disagreement into fabricated consensus. Every role emits an argument, critique,
or opinion — never an order. Executive synthesis is only present when justified
by evidence and the absence of unresolved disagreement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.kernel.errors import InfrastructureError
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboCognitiveValidationError,
    CiboDeliberationRole,
    CiboUncertainty,
    contains_secret_material,
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


class CiboExecutiveDeliberationError(InfrastructureError):
    """Base error for adversarial CIBO council deliberation contracts."""

    __slots__ = ()


class CiboExecutiveDeliberationValidationError(CiboExecutiveDeliberationError):
    """A deliberation value violates a deterministic disagreement invariant."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboExecutiveDeliberationValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str, *, field_name: str) -> str:
    if type(value) is not str or fullmatch(_CODE_RE, value) is None:
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    return value


def _validate_codes(
    values: tuple[str, ...],
    *,
    field_name: str,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(v) is not str for v in values):
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(v, field_name=field_name) for v in values)
    if len(set(normalized)) != len(normalized):
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must not contain duplicates"
        )
    if not allow_empty and not normalized:
        raise CiboExecutiveDeliberationValidationError(f"{field_name} must be non-empty")
    return tuple(sorted(normalized))


def _validate_safe_text(value: str, *, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise CiboExecutiveDeliberationValidationError(f"{field_name} must be non-empty text")
    if any(ch in value for ch in "\x00\n\r\t"):
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must not contain control characters"
        )
    if contains_secret_material(value):
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _canonical_refs(
    values: tuple[CiboCognitiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboCognitiveEvidenceRef, ...]:
    if type(values) is not tuple or any(
        type(item) is not CiboCognitiveEvidenceRef for item in values
    ):
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must be an immutable tuple of CiboCognitiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must not contain duplicates"
        )
    return tuple(sorted(values, key=lambda item: item.value))


def _revalidate_refs(
    values: tuple[CiboCognitiveEvidenceRef, ...],
    *,
    field_name: str,
) -> None:
    if type(values) is not tuple or any(
        type(item) is not CiboCognitiveEvidenceRef for item in values
    ):
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must be an immutable tuple of CiboCognitiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} must not contain duplicates"
        )
    if values != tuple(sorted(values, key=lambda item: item.value)):
        raise CiboExecutiveDeliberationValidationError(
            f"{field_name} failed canonical revalidation"
        )
    for ref in values:
        try:
            ref.revalidate()
        except CiboCognitiveValidationError as error:
            raise CiboExecutiveDeliberationValidationError(
                f"{field_name} failed nested revalidation"
            ) from error


def _revalidate_uncertainty(uncertainty: CiboUncertainty) -> None:
    try:
        uncertainty.revalidate()
    except CiboCognitiveValidationError as error:
        raise CiboExecutiveDeliberationValidationError(
            "deliberation uncertainty failed revalidation"
        ) from error


class CiboContributionKind(StrEnum):
    ARGUMENT = "argument"
    CRITIQUE = "critique"
    OPINION = "opinion"


class CiboCouncilOutcome(StrEnum):
    """First-class council outcome; disagreement is never collapsed to consensus."""

    DECISION = "decision"
    NO_DECISION = "no-decision"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    DISAGREEMENT = "disagreement"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CiboDeliberationContext:
    """Exact deliberation identity/version/subject binding."""

    deliberation_id: UUID
    version_code: str
    subject_code: str
    as_of: datetime
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if type(self.deliberation_id) is not UUID:
            raise CiboExecutiveDeliberationValidationError(
                "deliberation id must be UUID"
            )
        object.__setattr__(
            self,
            "version_code",
            _validate_code(self.version_code, field_name="deliberation version code"),
        )
        object.__setattr__(
            self,
            "subject_code",
            _validate_code(self.subject_code, field_name="deliberation subject code"),
        )
        _validate_aware_datetime(self.as_of, field_name="deliberation as_of")
        object.__setattr__(
            self,
            "evidence_refs",
            _canonical_refs(self.evidence_refs, field_name="deliberation context evidence"),
        )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.deliberation_id) is not UUID:
            raise CiboExecutiveDeliberationValidationError("deliberation id must be UUID")
        _validate_code(self.version_code, field_name="deliberation version code")
        _validate_code(self.subject_code, field_name="deliberation subject code")
        _validate_aware_datetime(self.as_of, field_name="deliberation as_of")
        _revalidate_refs(self.evidence_refs, field_name="deliberation context evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.deliberation_id),
            self.version_code,
            self.subject_code,
            self.as_of.isoformat(),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class CiboDeliberationContribution:
    """One evidence-bound participant position/argument/critique/opinion."""

    contribution_id: UUID
    role: CiboDeliberationRole
    kind: CiboContributionKind
    position_code: str
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    uncertainty: CiboUncertainty
    contributed_at: datetime
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.contribution_id) is not UUID:
            raise CiboExecutiveDeliberationValidationError(
                "contribution id must be UUID"
            )
        if type(self.role) is not CiboDeliberationRole:
            raise CiboExecutiveDeliberationValidationError(
                "contribution requires CiboDeliberationRole"
            )
        if type(self.kind) is not CiboContributionKind:
            raise CiboExecutiveDeliberationValidationError(
                "contribution requires CiboContributionKind"
            )
        object.__setattr__(
            self,
            "position_code",
            _validate_code(self.position_code, field_name="contribution position code"),
        )
        refs = _canonical_refs(self.evidence_refs, field_name="contribution evidence")
        if not refs:
            raise CiboExecutiveDeliberationValidationError(
                "contribution requires explicit backing evidence"
            )
        object.__setattr__(self, "evidence_refs", refs)
        if type(self.uncertainty) is not CiboUncertainty:
            raise CiboExecutiveDeliberationValidationError(
                "contribution requires CiboUncertainty"
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="contribution limitations"),
        )
        _validate_aware_datetime(self.contributed_at, field_name="contribution contributed_at")
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.contribution_id) is not UUID:
            raise CiboExecutiveDeliberationValidationError("contribution id must be UUID")
        if type(self.role) is not CiboDeliberationRole:
            raise CiboExecutiveDeliberationValidationError(
                "contribution requires CiboDeliberationRole"
            )
        try:
            self.role.revalidate()
        except CiboCognitiveValidationError as error:
            raise CiboExecutiveDeliberationValidationError(
                "contribution role failed nested revalidation"
            ) from error
        if type(self.kind) is not CiboContributionKind:
            raise CiboExecutiveDeliberationValidationError(
                "contribution requires CiboContributionKind"
            )
        _validate_code(self.position_code, field_name="contribution position code")
        if not self.evidence_refs:
            raise CiboExecutiveDeliberationValidationError(
                "contribution requires explicit backing evidence"
            )
        _revalidate_refs(self.evidence_refs, field_name="contribution evidence")
        if type(self.uncertainty) is not CiboUncertainty:
            raise CiboExecutiveDeliberationValidationError(
                "contribution requires CiboUncertainty"
            )
        _revalidate_uncertainty(self.uncertainty)
        if self.limitations != _validate_codes(
            self.limitations,
            field_name="contribution limitations",
        ):
            raise CiboExecutiveDeliberationValidationError(
                "contribution limitations failed canonical revalidation"
            )
        _validate_aware_datetime(self.contributed_at, field_name="contribution contributed_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.contribution_id),
            self.role.logical_values(),
            self.kind.value,
            self.position_code,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.uncertainty.logical_values(),
            self.limitations,
            self.contributed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboDisagreement:
    """A retained disagreement between two contributions; never collapsed."""

    a_ref: UUID
    b_ref: UUID
    reason_code: str
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if type(self.a_ref) is not UUID or type(self.b_ref) is not UUID:
            raise CiboExecutiveDeliberationValidationError(
                "disagreement references must be UUIDs"
            )
        if self.a_ref == self.b_ref:
            raise CiboExecutiveDeliberationValidationError(
                "disagreement must reference two distinct contributions"
            )
        object.__setattr__(
            self,
            "reason_code",
            _validate_code(self.reason_code, field_name="disagreement reason code"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _canonical_refs(self.evidence_refs, field_name="disagreement evidence"),
        )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.a_ref) is not UUID or type(self.b_ref) is not UUID:
            raise CiboExecutiveDeliberationValidationError(
                "disagreement references must be UUIDs"
            )
        _validate_code(self.reason_code, field_name="disagreement reason code")
        _revalidate_refs(self.evidence_refs, field_name="disagreement evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.a_ref),
            str(self.b_ref),
            self.reason_code,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class CiboAdversarialCritique:
    """An adversarial critique of one contribution, retained independently."""

    target_ref: UUID
    critique_reason_codes: tuple[str, ...]
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if type(self.target_ref) is not UUID:
            raise CiboExecutiveDeliberationValidationError(
                "critique target must be a UUID"
            )
        object.__setattr__(
            self,
            "critique_reason_codes",
            _validate_codes(
                self.critique_reason_codes,
                field_name="critique reason codes",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _canonical_refs(self.evidence_refs, field_name="critique evidence"),
        )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.target_ref) is not UUID:
            raise CiboExecutiveDeliberationValidationError("critique target must be a UUID")
        if self.critique_reason_codes != _validate_codes(
            self.critique_reason_codes,
            field_name="critique reason codes",
            allow_empty=False,
        ):
            raise CiboExecutiveDeliberationValidationError(
                "critique reason codes failed canonical revalidation"
            )
        _revalidate_refs(self.evidence_refs, field_name="critique evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.target_ref),
            self.critique_reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class CiboCouncilSynthesis:
    """Executive synthesis, present only when evidence justifies it."""

    synthesis_id: UUID
    summary: str
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    uncertainty: CiboUncertainty
    synthesized_at: datetime
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.synthesis_id) is not UUID:
            raise CiboExecutiveDeliberationValidationError("synthesis id must be UUID")
        object.__setattr__(
            self,
            "summary",
            _validate_safe_text(self.summary, field_name="synthesis summary"),
        )
        refs = _canonical_refs(self.evidence_refs, field_name="synthesis evidence")
        if not refs:
            raise CiboExecutiveDeliberationValidationError(
                "synthesis requires explicit backing evidence"
            )
        object.__setattr__(self, "evidence_refs", refs)
        if type(self.uncertainty) is not CiboUncertainty:
            raise CiboExecutiveDeliberationValidationError(
                "synthesis requires CiboUncertainty"
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="synthesis limitations"),
        )
        _validate_aware_datetime(self.synthesized_at, field_name="synthesis synthesized_at")
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.synthesis_id) is not UUID:
            raise CiboExecutiveDeliberationValidationError("synthesis id must be UUID")
        _validate_safe_text(self.summary, field_name="synthesis summary")
        if not self.evidence_refs:
            raise CiboExecutiveDeliberationValidationError(
                "synthesis requires explicit backing evidence"
            )
        _revalidate_refs(self.evidence_refs, field_name="synthesis evidence")
        if type(self.uncertainty) is not CiboUncertainty:
            raise CiboExecutiveDeliberationValidationError(
                "synthesis requires CiboUncertainty"
            )
        _revalidate_uncertainty(self.uncertainty)
        if self.limitations != _validate_codes(
            self.limitations,
            field_name="synthesis limitations",
        ):
            raise CiboExecutiveDeliberationValidationError(
                "synthesis limitations failed canonical revalidation"
            )
        _validate_aware_datetime(self.synthesized_at, field_name="synthesis synthesized_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.synthesis_id),
            self.summary,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.uncertainty.logical_values(),
            self.limitations,
            self.synthesized_at.isoformat(),
        )


_DISAGREEMENT_OUTCOMES = frozenset(
    {
        CiboCouncilOutcome.DISAGREEMENT,
        CiboCouncilOutcome.NO_DECISION,
        CiboCouncilOutcome.BLOCKED,
    }
)


@dataclass(frozen=True, slots=True)
class CiboExecutiveDeliberation:
    """One bounded adversarial council deliberation with explicit outcome."""

    context: CiboDeliberationContext
    participants: tuple[CiboDeliberationContribution, ...]
    concluded_at: datetime
    disagreements: tuple[CiboDisagreement, ...] = ()
    critiques: tuple[CiboAdversarialCritique, ...] = ()
    synthesis: CiboCouncilSynthesis | None = None
    outcome: CiboCouncilOutcome = CiboCouncilOutcome.NO_DECISION

    def __post_init__(self) -> None:
        if type(self.context) is not CiboDeliberationContext:
            raise CiboExecutiveDeliberationValidationError(
                "deliberation requires CiboDeliberationContext"
            )
        if type(self.participants) is not tuple or not self.participants or any(
            type(item) is not CiboDeliberationContribution for item in self.participants
        ):
            raise CiboExecutiveDeliberationValidationError(
                "deliberation requires a non-empty tuple of CiboDeliberationContribution"
            )
        for participant in self.participants:
            participant.revalidate()
        contribution_ids = tuple(item.contribution_id for item in self.participants)
        if len(set(contribution_ids)) != len(contribution_ids):
            raise CiboExecutiveDeliberationValidationError(
                "deliberation contributions must have unique ids"
            )
        roles = tuple(item.role.value for item in self.participants)
        if len(set(roles)) != len(roles):
            raise CiboExecutiveDeliberationValidationError(
                "deliberation contributions must have unique roles"
            )
        object.__setattr__(
            self,
            "participants",
            tuple(sorted(self.participants, key=lambda item: item.role.value)),
        )
        if type(self.disagreements) is not tuple or any(
            type(item) is not CiboDisagreement for item in self.disagreements
        ):
            raise CiboExecutiveDeliberationValidationError(
                "disagreements must be a tuple of CiboDisagreement"
            )
        if len(set(self.disagreements)) != len(self.disagreements):
            raise CiboExecutiveDeliberationValidationError(
                "deliberation disagreements must not contain duplicates"
            )
        object.__setattr__(
            self,
            "disagreements",
            tuple(sorted(self.disagreements, key=lambda d: (str(d.a_ref), str(d.b_ref)))),
        )
        if type(self.critiques) is not tuple or any(
            type(item) is not CiboAdversarialCritique for item in self.critiques
        ):
            raise CiboExecutiveDeliberationValidationError(
                "critiques must be a tuple of CiboAdversarialCritique"
            )
        if len({item.target_ref for item in self.critiques}) != len(self.critiques):
            raise CiboExecutiveDeliberationValidationError(
                "deliberation critiques must not duplicate targets"
            )
        object.__setattr__(
            self,
            "critiques",
            tuple(sorted(self.critiques, key=lambda c: str(c.target_ref))),
        )
        if type(self.outcome) is not CiboCouncilOutcome:
            raise CiboExecutiveDeliberationValidationError(
                "deliberation requires CiboCouncilOutcome"
            )
        known_ids = set(contribution_ids)
        for disagreement in self.disagreements:
            if disagreement.a_ref not in known_ids or disagreement.b_ref not in known_ids:
                raise CiboExecutiveDeliberationValidationError(
                    "disagreement must reference existing contributions"
                )
        for critique in self.critiques:
            if critique.target_ref not in known_ids:
                raise CiboExecutiveDeliberationValidationError(
                    "critique must reference an existing contribution"
                )
        if self.synthesis is not None and type(self.synthesis) is not CiboCouncilSynthesis:
            raise CiboExecutiveDeliberationValidationError(
                "synthesis must be CiboCouncilSynthesis or None"
            )
        if self.disagreements:
            if self.outcome not in _DISAGREEMENT_OUTCOMES:
                raise CiboExecutiveDeliberationValidationError(
                    "disagreements must not be collapsed into a decision"
                )
            if self.synthesis is not None:
                raise CiboExecutiveDeliberationValidationError(
                    "synthesis is forbidden while disagreements remain"
                )
        if self.synthesis is not None and self.outcome is not CiboCouncilOutcome.DECISION:
            raise CiboExecutiveDeliberationValidationError(
                "synthesis requires a decision outcome"
            )
        _validate_aware_datetime(self.concluded_at, field_name="deliberation concluded_at")
        if self.concluded_at < self.context.as_of:
            raise CiboExecutiveDeliberationValidationError(
                "deliberation conclusion cannot predate its context"
            )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.context) is not CiboDeliberationContext:
            raise CiboExecutiveDeliberationValidationError(
                "deliberation requires CiboDeliberationContext"
            )
        self.context.revalidate()
        if type(self.participants) is not tuple or not self.participants or any(
            type(item) is not CiboDeliberationContribution for item in self.participants
        ):
            raise CiboExecutiveDeliberationValidationError(
                "deliberation requires a non-empty tuple of CiboDeliberationContribution"
            )
        if self.participants != tuple(
            sorted(self.participants, key=lambda item: item.role.value)
        ):
            raise CiboExecutiveDeliberationValidationError(
                "participants failed canonical revalidation"
            )
        for participant in self.participants:
            participant.revalidate()
        if type(self.disagreements) is not tuple or any(
            type(item) is not CiboDisagreement for item in self.disagreements
        ):
            raise CiboExecutiveDeliberationValidationError(
                "disagreements must be a tuple of CiboDisagreement"
            )
        if self.disagreements != tuple(
            sorted(self.disagreements, key=lambda d: (str(d.a_ref), str(d.b_ref)))
        ):
            raise CiboExecutiveDeliberationValidationError(
                "disagreements failed canonical revalidation"
            )
        for disagreement in self.disagreements:
            disagreement.revalidate()
        if type(self.critiques) is not tuple or any(
            type(item) is not CiboAdversarialCritique for item in self.critiques
        ):
            raise CiboExecutiveDeliberationValidationError(
                "critiques must be a tuple of CiboAdversarialCritique"
            )
        if self.critiques != tuple(sorted(self.critiques, key=lambda c: str(c.target_ref))):
            raise CiboExecutiveDeliberationValidationError(
                "critiques failed canonical revalidation"
            )
        for critique in self.critiques:
            critique.revalidate()
        if type(self.outcome) is not CiboCouncilOutcome:
            raise CiboExecutiveDeliberationValidationError(
                "deliberation requires CiboCouncilOutcome"
            )
        if self.synthesis is not None:
            if type(self.synthesis) is not CiboCouncilSynthesis:
                raise CiboExecutiveDeliberationValidationError(
                    "synthesis must be CiboCouncilSynthesis or None"
                )
            self.synthesis.revalidate()
        _validate_aware_datetime(self.concluded_at, field_name="deliberation concluded_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.context.logical_values(),
            tuple(item.logical_values() for item in self.participants),
            tuple(item.logical_values() for item in self.disagreements),
            tuple(item.logical_values() for item in self.critiques),
            None if self.synthesis is None else self.synthesis.logical_values(),
            self.outcome.value,
            self.concluded_at.isoformat(),
        )
