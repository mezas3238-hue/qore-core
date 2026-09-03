"""CIBO Cognitive Evaluation Framework (CA-17).

An evaluation framework that assesses, *without self-certifying authority*:

- evidence sufficiency;
- provenance completeness;
- contradiction handling;
- calibration/abstention quality;
- decision/recommendation consistency references;
- counterfactual quality;
- memory-usefulness references;
- planning consistency;
- replay completeness;
- incremental contribution evidence hooks.

Evaluation outputs distinguish ``SUFFICIENT_FOR_EVALUATION``,
``INSUFFICIENT_EVIDENCE``, ``CONTRADICTORY_EVIDENCE``, and
``EVALUATION_NOT_APPLICABLE`` using names/types that do not collide with
Batch 006 ownership. An evaluation is a cognitive assessment only: it cannot
confer execution, Risk, Production, or promotion authority.

Architecture laws honoured: no self-certifying authority (3, 4, 13), exact int
scores / ``bool != int`` (15), deterministic ordering (19), secret-bearing
strings fail closed (20), no ambient time/RNG (14), no global mutable state
(21).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import compile
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    TraderSubject,
    contains_secret_material,
    fingerprint_material,
    require_aware_datetime,
    require_exact_int,
    require_exact_str,
)
from qore.kernel.temporal import canonical_instant

_IDENTITY_TOKEN = compile(r"[0-9A-Za-z._-]{1,128}")
_REF_TOKEN = compile(r"[0-9A-Za-z._:/-]{1,256}")


class EvaluationError(CiboCognitiveError):
    """Base error for the CIBO cognitive evaluation framework."""

    __slots__ = ()


class EvaluationValidationError(EvaluationError, CiboCognitiveValidationError):
    """Violation of a cognitive evaluation invariant."""

    __slots__ = ()


class CognitiveEvaluationStatus(StrEnum):
    """Explicit, authority-free evaluation outcome."""

    SUFFICIENT_FOR_EVALUATION = "sufficient-for-evaluation"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    CONTRADICTORY_EVIDENCE = "contradictory-evidence"
    EVALUATION_NOT_APPLICABLE = "evaluation-not-applicable"


class EvaluationDimension(StrEnum):
    """Assessment dimensions of a cognitive episode (no authority)."""

    EVIDENCE_SUFFICIENCY = "evidence-sufficiency"
    PROVENANCE_COMPLETENESS = "provenance-completeness"
    CONTRADICTION_HANDLING = "contradiction-handling"
    CALIBRATION_ABSTENTION = "calibration-abstention"
    DECISION_CONSISTENCY = "decision-consistency"
    COUNTERFACTUAL_QUALITY = "counterfactual-quality"
    MEMORY_USEFULNESS = "memory-usefulness"
    PLANNING_CONSISTENCY = "planning-consistency"
    REPLAY_COMPLETENESS = "replay-completeness"
    CONTRIBUTION_EVIDENCE = "contribution-evidence"


@dataclass(frozen=True, slots=True)
class EvaluationDimensionScore:
    """A bounded score for one evaluation dimension."""

    dimension: EvaluationDimension
    score: int
    note: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.dimension) is not EvaluationDimension:
            raise EvaluationValidationError(
                "evaluation dimension must be an EvaluationDimension"
            )
        require_exact_int(self.score, field="evaluation dimension score")
        if not 0 <= self.score <= 100:
            raise EvaluationValidationError("evaluation dimension score must be in [0, 100]")
        require_exact_str(self.note, field="evaluation dimension note")
        if not self.note.strip():
            raise EvaluationValidationError("evaluation dimension note must not be blank")
        if contains_secret_material(self.note):
            raise EvaluationValidationError(
                "evaluation dimension note must not carry secret-bearing material"
            )

    def logical_values(self) -> tuple[str, int, str]:
        return (self.dimension.value, self.score, self.note)


def _require_refs(value: object, *, field: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise EvaluationValidationError(f"{field} must be a tuple")
    result = []
    for item in value:
        require_exact_str(item, field=f"{field} item")
        if not item.strip():
            raise EvaluationValidationError(f"{field} item must not be blank")
        if contains_secret_material(item):
            raise EvaluationValidationError(f"{field} item must not carry secret-bearing material")
        result.append(item)
    return tuple(result)


def _derive_status(
    evaluated_reference: str,
    dimensions: tuple[EvaluationDimensionScore, ...],
    evidence_refs: tuple[str, ...],
    contradiction_refs: tuple[str, ...],
) -> CognitiveEvaluationStatus:
    if not evaluated_reference.strip() or not dimensions:
        return CognitiveEvaluationStatus.EVALUATION_NOT_APPLICABLE
    if contradiction_refs:
        return CognitiveEvaluationStatus.CONTRADICTORY_EVIDENCE
    if not evidence_refs:
        return CognitiveEvaluationStatus.INSUFFICIENT_EVIDENCE
    return CognitiveEvaluationStatus.SUFFICIENT_FOR_EVALUATION


@dataclass(frozen=True, slots=True)
class CognitiveEvaluation:
    """Immutable, authority-free cognitive assessment result."""

    evaluation_id: UUID
    evaluated_reference: str
    dimensions: tuple[EvaluationDimensionScore, ...]
    status: CognitiveEvaluationStatus
    evidence_refs: tuple[str, ...]
    contradiction_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.evaluation_id) is not UUID:
            raise EvaluationValidationError("evaluation id must be a UUID")
        require_exact_str(self.evaluated_reference, field="evaluated reference")
        if type(self.dimensions) is not tuple:
            raise EvaluationValidationError("evaluation dimensions must be a tuple")
        seen: set[EvaluationDimension] = set()
        for dimension in self.dimensions:
            if type(dimension) is not EvaluationDimensionScore:
                raise EvaluationValidationError(
                    "evaluation dimensions must contain only EvaluationDimensionScore values"
                )
            dimension.revalidate()
            if dimension.dimension in seen:
                raise EvaluationValidationError("evaluation dimensions must be unique")
            seen.add(dimension.dimension)
        ordered = tuple(sorted(self.dimensions, key=lambda d: d.dimension.value))
        if self.dimensions != ordered:
            raise EvaluationValidationError("evaluation dimensions must be canonically ordered")
        if type(self.status) is not CognitiveEvaluationStatus:
            raise EvaluationValidationError(
                "evaluation status must be a CognitiveEvaluationStatus"
            )
        evidence_refs = _require_refs(self.evidence_refs, field="evaluation evidence refs")
        contradiction_refs = _require_refs(
            self.contradiction_refs, field="evaluation contradiction refs"
        )
        derived = _derive_status(
            self.evaluated_reference, self.dimensions, evidence_refs, contradiction_refs
        )
        if self.status is not derived:
            raise EvaluationValidationError(
                "evaluation status does not match its evidence and dimensions"
            )


def evaluate_cognition(
    *,
    evaluation_id: UUID,
    evaluated_reference: str,
    dimensions: Sequence[EvaluationDimensionScore],
    evidence_refs: Sequence[str] = (),
    contradiction_refs: Sequence[str] = (),
) -> CognitiveEvaluation:
    """Evaluate a cognitive episode deterministically, without conferring authority."""
    if type(evaluation_id) is not UUID:
        raise EvaluationValidationError("evaluation id must be a UUID")
    require_exact_str(evaluated_reference, field="evaluated reference")
    if not isinstance(dimensions, Sequence):
        raise EvaluationValidationError("dimensions must be a sequence")
    if not isinstance(evidence_refs, Sequence):
        raise EvaluationValidationError("evidence refs must be a sequence")
    if not isinstance(contradiction_refs, Sequence):
        raise EvaluationValidationError("contradiction refs must be a sequence")
    validated_dims: list[EvaluationDimensionScore] = []
    for dimension in dimensions:
        if type(dimension) is not EvaluationDimensionScore:
            raise EvaluationValidationError(
                "evaluation dimensions must contain only EvaluationDimensionScore values"
            )
        dimension.revalidate()
        validated_dims.append(dimension)
    dims = tuple(sorted(validated_dims, key=lambda d: d.dimension.value))
    evidence = tuple(evidence_refs)
    contradictions = tuple(contradiction_refs)
    status = _derive_status(evaluated_reference, dims, evidence, contradictions)
    return CognitiveEvaluation(
        evaluation_id=evaluation_id,
        evaluated_reference=evaluated_reference,
        dimensions=dims,
        status=status,
        evidence_refs=evidence,
        contradiction_refs=contradictions,
    )


class InterventionAttributionDisposition(StrEnum):
    """Typed, authority-free disposition of a Trader-development intervention.

    SUPPORTED_CONTRIBUTION is the strongest claim and is only derivable when
    non-empty CAPABILITY evidence exists in BOTH the pre- and post-intervention
    windows, with no contradiction and no hindsight reordering. Economic-outcome
    evidence (profit) is retained but is never, on its own, causal proof.
    """

    SUPPORTED_CONTRIBUTION = "supported-contribution"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    CONTRADICTORY_EVIDENCE = "contradictory-evidence"
    NOT_APPLICABLE = "not-applicable"


class CapabilityEvidenceKind(StrEnum):
    """Evidence kind: capability observation vs. economic-outcome observation.

    ECONOMIC_OUTCOME evidence (e.g. profit) is retained for lineage but is never
    counted as capability evidence, so profit alone can never establish
    SUPPORTED_CONTRIBUTION.
    """

    CAPABILITY = "capability"
    ECONOMIC_OUTCOME = "economic-outcome"


class CapabilityOutcome(StrEnum):
    """Declared capability delta observed in the post-intervention window."""

    IMPROVED = "improved"
    DEGRADED = "degraded"
    UNCHANGED = "unchanged"


class InterventionKind(StrEnum):
    """Whether the intervention is a development intervention attributable here."""

    DEVELOPMENT = "development"
    NON_DEVELOPMENT = "non-development"


@dataclass(frozen=True, slots=True)
class CapabilityEvidence:
    """Evidence-bound capability/outcome observation at an explicit time.

    ``outcome`` is only meaningful for CAPABILITY evidence and is only valid in
    the post-intervention window; pre-intervention baseline evidence must carry
    no outcome (hindsight is unrepresentable).
    """

    reference: str
    capability: str
    observed_at: datetime
    evidence_fingerprint: CiboCognitiveFingerprint
    kind: CapabilityEvidenceKind = CapabilityEvidenceKind.CAPABILITY
    outcome: CapabilityOutcome | None = None

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        require_exact_str(self.reference, field="capability evidence reference")
        if _REF_TOKEN.fullmatch(self.reference) is None:
            raise EvaluationValidationError(
                "capability evidence reference must be a non-blank reference token"
            )
        if contains_secret_material(self.reference):
            raise EvaluationValidationError(
                "capability evidence reference must not carry secret-bearing material"
            )
        require_exact_str(self.capability, field="capability evidence capability")
        if _IDENTITY_TOKEN.fullmatch(self.capability) is None:
            raise EvaluationValidationError(
                "capability evidence capability must be a non-blank identity token"
            )
        if contains_secret_material(self.capability):
            raise EvaluationValidationError(
                "capability evidence capability must not carry secret-bearing material"
            )
        require_aware_datetime(self.observed_at, field="capability evidence observed_at")
        if type(self.evidence_fingerprint) is not CiboCognitiveFingerprint:
            raise EvaluationValidationError(
                "capability evidence fingerprint must be a CiboCognitiveFingerprint"
            )
        self.evidence_fingerprint.revalidate()
        if type(self.kind) is not CapabilityEvidenceKind:
            raise EvaluationValidationError(
                "capability evidence kind must be a CapabilityEvidenceKind"
            )
        if self.outcome is not None and type(self.outcome) is not CapabilityOutcome:
            raise EvaluationValidationError(
                "capability evidence outcome must be a CapabilityOutcome or None"
            )
        if self.kind is CapabilityEvidenceKind.ECONOMIC_OUTCOME and self.outcome is not None:
            raise EvaluationValidationError(
                "economic-outcome evidence must not carry a capability outcome"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.reference,
            self.capability,
            canonical_instant(self.observed_at),
            self.evidence_fingerprint.value,
            self.kind.value,
            None if self.outcome is None else self.outcome.value,
        )

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.reference,
            self.capability,
            canonical_instant(self.observed_at),
            self.evidence_fingerprint.value,
            "" if self.outcome is None else self.outcome.value,
        )


@dataclass(frozen=True, slots=True)
class InterventionIdentity:
    """Exact CIBO development intervention identity + version + fingerprint.

    ``target_trader_fingerprint`` binds the intervention to exactly one Trader
    version; a different trader or version yields a different self-fingerprint.
    ``kind`` distinguishes a development intervention (attributable here) from a
    non-development intervention (NOT_APPLICABLE).
    """

    intervention_id: str
    intervention_version: str
    target_trader_fingerprint: CiboCognitiveFingerprint
    kind: InterventionKind
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        require_exact_str(self.intervention_id, field="intervention id")
        if _IDENTITY_TOKEN.fullmatch(self.intervention_id) is None:
            raise EvaluationValidationError(
                "intervention id must be a non-blank identity token"
            )
        if contains_secret_material(self.intervention_id):
            raise EvaluationValidationError(
                "intervention id must not carry secret-bearing material"
            )
        require_exact_str(self.intervention_version, field="intervention version")
        if _IDENTITY_TOKEN.fullmatch(self.intervention_version) is None:
            raise EvaluationValidationError(
                "intervention version must be a non-blank identity token"
            )
        if contains_secret_material(self.intervention_version):
            raise EvaluationValidationError(
                "intervention version must not carry secret-bearing material"
            )
        if type(self.target_trader_fingerprint) is not CiboCognitiveFingerprint:
            raise EvaluationValidationError(
                "intervention target trader fingerprint must be a CiboCognitiveFingerprint"
            )
        self.target_trader_fingerprint.revalidate()
        if type(self.kind) is not InterventionKind:
            raise EvaluationValidationError(
                "intervention kind must be an InterventionKind"
            )
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise EvaluationValidationError(
                "intervention fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        expected = fingerprint_material(
            (
                self.intervention_id,
                self.intervention_version,
                self.target_trader_fingerprint.value,
                self.kind.value,
            )
        )
        if self.fingerprint != expected:
            raise EvaluationValidationError(
                "intervention fingerprint does not match its identity/version/target"
            )

    def logical_values(self) -> tuple[str, str, str, str, str]:
        return (
            self.intervention_id,
            self.intervention_version,
            self.target_trader_fingerprint.value,
            self.kind.value,
            self.fingerprint.value,
        )


def _canonical_ref_codes(
    values: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    """Validate, deduplicate, and canonically order a tuple of reference codes."""
    if type(values) is not tuple or any(type(value) is not str for value in values):
        raise EvaluationValidationError(
            f"{field_name} must be an immutable tuple of exact strings"
        )
    normalized = []
    for value in values:
        if _REF_TOKEN.fullmatch(value) is None:
            raise EvaluationValidationError(
                f"{field_name} must contain only non-blank reference tokens"
            )
        if contains_secret_material(value):
            raise EvaluationValidationError(
                f"{field_name} must not carry secret-bearing material"
            )
        normalized.append(value)
    if len(set(normalized)) != len(normalized):
        raise EvaluationValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _canonical_evidence(
    values: tuple[CapabilityEvidence, ...],
    *,
    field_name: str,
) -> tuple[CapabilityEvidence, ...]:
    """Validate, deduplicate, and canonically order capability evidence."""
    if type(values) is not tuple or any(
        type(item) is not CapabilityEvidence for item in values
    ):
        raise EvaluationValidationError(
            f"{field_name} must be an immutable tuple of CapabilityEvidence"
        )
    for item in values:
        item.revalidate()
    if len(set(values)) != len(values):
        raise EvaluationValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.sort_key()))


def _derive_attribution_disposition(
    intervention_kind: InterventionKind,
    development_hypothesis: str,
    target_capability: str,
    contradiction_refs: tuple[str, ...],
    pre_evidence: tuple[CapabilityEvidence, ...],
    post_evidence: tuple[CapabilityEvidence, ...],
) -> InterventionAttributionDisposition:
    if intervention_kind is not InterventionKind.DEVELOPMENT:
        return InterventionAttributionDisposition.NOT_APPLICABLE
    if contradiction_refs:
        return InterventionAttributionDisposition.CONTRADICTORY_EVIDENCE
    if not development_hypothesis.strip() or not target_capability.strip():
        return InterventionAttributionDisposition.NOT_APPLICABLE
    pre_capability = [
        item
        for item in pre_evidence
        if item.kind is CapabilityEvidenceKind.CAPABILITY
        and item.capability == target_capability
    ]
    post_capability = [
        item
        for item in post_evidence
        if item.kind is CapabilityEvidenceKind.CAPABILITY
        and item.capability == target_capability
    ]
    if not pre_capability or not post_capability:
        return InterventionAttributionDisposition.INSUFFICIENT_EVIDENCE
    outcomes = [item.outcome for item in post_capability]
    if any(outcome is CapabilityOutcome.DEGRADED for outcome in outcomes):
        return InterventionAttributionDisposition.CONTRADICTORY_EVIDENCE
    if any(outcome is CapabilityOutcome.IMPROVED for outcome in outcomes):
        return InterventionAttributionDisposition.SUPPORTED_CONTRIBUTION
    return InterventionAttributionDisposition.INSUFFICIENT_EVIDENCE


@dataclass(frozen=True, slots=True)
class TraderDevelopmentAttribution:
    """Typed, authority-free attribution of a Trader-development intervention.

    Pre-intervention evidence must not postdate ``applied_at`` and post-
    intervention evidence must postdate it (no hidden clock; no hindsight
    replacement of pre-intervention state). SUPPORTED_CONTRIBUTION requires
    CAPABILITY evidence in both windows and is never derived from economic
    profit alone. The object exposes no execution, Risk, promotion, DEMO, or
    Production authority.
    """

    attribution_id: UUID
    trader: TraderSubject
    intervention: InterventionIdentity
    development_hypothesis: str
    target_capability: str
    curriculum_refs: tuple[str, ...]
    applied_at: datetime
    pre_intervention_evidence: tuple[CapabilityEvidence, ...]
    post_intervention_evidence: tuple[CapabilityEvidence, ...]
    contradiction_refs: tuple[str, ...]
    disposition: InterventionAttributionDisposition
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.attribution_id) is not UUID:
            raise EvaluationValidationError("attribution id must be a UUID")
        if type(self.trader) is not TraderSubject:
            raise EvaluationValidationError("attribution trader must be a TraderSubject")
        self.trader.revalidate()
        if type(self.intervention) is not InterventionIdentity:
            raise EvaluationValidationError(
                "attribution intervention must be an InterventionIdentity"
            )
        self.intervention.revalidate()
        if self.intervention.target_trader_fingerprint != self.trader.fingerprint:
            raise EvaluationValidationError(
                "attribution intervention does not target the attribution trader"
            )
        require_exact_str(self.development_hypothesis, field="development hypothesis")
        if not self.development_hypothesis.strip():
            raise EvaluationValidationError("development hypothesis must not be blank")
        if contains_secret_material(self.development_hypothesis):
            raise EvaluationValidationError(
                "development hypothesis must not carry secret-bearing material"
            )
        require_exact_str(self.target_capability, field="target capability")
        if _IDENTITY_TOKEN.fullmatch(self.target_capability) is None:
            raise EvaluationValidationError(
                "target capability must be a non-blank identity token"
            )
        if contains_secret_material(self.target_capability):
            raise EvaluationValidationError(
                "target capability must not carry secret-bearing material"
            )
        if self.curriculum_refs != _canonical_ref_codes(
            self.curriculum_refs, field_name="attribution curriculum refs"
        ):
            raise EvaluationValidationError(
                "attribution curriculum refs failed canonical revalidation"
            )
        require_aware_datetime(self.applied_at, field="attribution applied_at")
        pre = _canonical_evidence(
            self.pre_intervention_evidence, field_name="pre-intervention evidence"
        )
        if self.pre_intervention_evidence != pre:
            raise EvaluationValidationError(
                "pre-intervention evidence failed canonical revalidation"
            )
        post = _canonical_evidence(
            self.post_intervention_evidence, field_name="post-intervention evidence"
        )
        if self.post_intervention_evidence != post:
            raise EvaluationValidationError(
                "post-intervention evidence failed canonical revalidation"
            )
        for item in pre:
            if item.observed_at > self.applied_at:
                raise EvaluationValidationError(
                    "pre-intervention evidence must not postdate the intervention"
                )
            if item.kind is CapabilityEvidenceKind.CAPABILITY and item.outcome is not None:
                raise EvaluationValidationError(
                    "pre-intervention capability evidence must not carry an outcome"
                )
        for item in post:
            if item.observed_at <= self.applied_at:
                raise EvaluationValidationError(
                    "post-intervention evidence must postdate the intervention"
                )
            if item.kind is CapabilityEvidenceKind.CAPABILITY and item.outcome is None:
                raise EvaluationValidationError(
                    "post-intervention capability evidence must carry an outcome"
                )
        if self.contradiction_refs != _canonical_ref_codes(
            self.contradiction_refs, field_name="attribution contradiction refs"
        ):
            raise EvaluationValidationError(
                "attribution contradiction refs failed canonical revalidation"
            )
        if type(self.disposition) is not InterventionAttributionDisposition:
            raise EvaluationValidationError(
                "attribution disposition must be an InterventionAttributionDisposition"
            )
        derived = _derive_attribution_disposition(
            self.intervention.kind,
            self.development_hypothesis,
            self.target_capability,
            self.contradiction_refs,
            pre,
            post,
        )
        if self.disposition is not derived:
            raise EvaluationValidationError(
                "attribution disposition does not match its evidence"
            )
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise EvaluationValidationError(
                "attribution fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        if self.fingerprint != fingerprint_material(self.logical_values()):
            raise EvaluationValidationError(
                "attribution fingerprint does not match its canonical content"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.attribution_id),
            self.trader.logical_values(),
            self.intervention.logical_values(),
            self.development_hypothesis,
            self.target_capability,
            self.curriculum_refs,
            canonical_instant(self.applied_at),
            tuple(item.logical_values() for item in self.pre_intervention_evidence),
            tuple(item.logical_values() for item in self.post_intervention_evidence),
            self.contradiction_refs,
            self.disposition.value,
        )


def build_trader_development_attribution(
    *,
    attribution_id: UUID,
    trader: TraderSubject,
    intervention: InterventionIdentity,
    development_hypothesis: str,
    target_capability: str,
    applied_at: datetime,
    curriculum_refs: Sequence[str] = (),
    pre_intervention_evidence: Sequence[CapabilityEvidence] = (),
    post_intervention_evidence: Sequence[CapabilityEvidence] = (),
    contradiction_refs: Sequence[str] = (),
) -> TraderDevelopmentAttribution:
    """Build a validated, canonically ordered, fingerprinted intervention attribution."""
    if type(attribution_id) is not UUID:
        raise EvaluationValidationError("attribution id must be a UUID")
    if type(trader) is not TraderSubject:
        raise EvaluationValidationError("attribution trader must be a TraderSubject")
    trader.revalidate()
    if type(intervention) is not InterventionIdentity:
        raise EvaluationValidationError(
            "attribution intervention must be an InterventionIdentity"
        )
    intervention.revalidate()
    if not isinstance(curriculum_refs, Sequence):
        raise EvaluationValidationError("curriculum refs must be a sequence")
    if not isinstance(pre_intervention_evidence, Sequence):
        raise EvaluationValidationError("pre-intervention evidence must be a sequence")
    if not isinstance(post_intervention_evidence, Sequence):
        raise EvaluationValidationError("post-intervention evidence must be a sequence")
    if not isinstance(contradiction_refs, Sequence):
        raise EvaluationValidationError("contradiction refs must be a sequence")
    curriculum = _canonical_ref_codes(
        tuple(curriculum_refs), field_name="attribution curriculum refs"
    )
    pre = _canonical_evidence(
        tuple(pre_intervention_evidence), field_name="pre-intervention evidence"
    )
    post = _canonical_evidence(
        tuple(post_intervention_evidence), field_name="post-intervention evidence"
    )
    contradictions = _canonical_ref_codes(
        tuple(contradiction_refs), field_name="attribution contradiction refs"
    )
    disposition = _derive_attribution_disposition(
        intervention.kind,
        development_hypothesis,
        target_capability,
        contradictions,
        pre,
        post,
    )
    logical = (
        str(attribution_id),
        trader.logical_values(),
        intervention.logical_values(),
        development_hypothesis,
        target_capability,
        curriculum,
        canonical_instant(applied_at),
        tuple(item.logical_values() for item in pre),
        tuple(item.logical_values() for item in post),
        contradictions,
        disposition.value,
    )
    return TraderDevelopmentAttribution(
        attribution_id=attribution_id,
        trader=trader,
        intervention=intervention,
        development_hypothesis=development_hypothesis,
        target_capability=target_capability,
        curriculum_refs=curriculum,
        applied_at=applied_at,
        pre_intervention_evidence=pre,
        post_intervention_evidence=post,
        contradiction_refs=contradictions,
        disposition=disposition,
        fingerprint=fingerprint_material(logical),
    )


__all__ = [
    "CapabilityEvidence",
    "CapabilityEvidenceKind",
    "CapabilityOutcome",
    "CognitiveEvaluation",
    "CognitiveEvaluationStatus",
    "EvaluationDimension",
    "EvaluationDimensionScore",
    "EvaluationError",
    "EvaluationValidationError",
    "InterventionAttributionDisposition",
    "InterventionIdentity",
    "InterventionKind",
    "TraderDevelopmentAttribution",
    "build_trader_development_attribution",
    "evaluate_cognition",
]
