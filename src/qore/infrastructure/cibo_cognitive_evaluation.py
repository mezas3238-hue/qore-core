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
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveValidationError,
    contains_secret_material,
    require_exact_int,
    require_exact_str,
)


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


__all__ = [
    "CognitiveEvaluation",
    "CognitiveEvaluationStatus",
    "EvaluationDimension",
    "EvaluationDimensionScore",
    "EvaluationError",
    "EvaluationValidationError",
    "evaluate_cognition",
]
