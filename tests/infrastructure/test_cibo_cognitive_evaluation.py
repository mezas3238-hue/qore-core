"""Tests for the CIBO Cognitive Evaluation Framework (CA-17)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from qore.infrastructure.cibo_cognitive_common import CiboCognitiveValidationError
from qore.infrastructure.cibo_cognitive_evaluation import (
    CognitiveEvaluation,
    CognitiveEvaluationStatus,
    EvaluationDimension,
    EvaluationDimensionScore,
    evaluate_cognition,
)

_EVALUATION = UUID("00000000-0000-0000-0000-0000000000a9")


def _score(dimension: EvaluationDimension, score: int = 60) -> EvaluationDimensionScore:
    return EvaluationDimensionScore(
        dimension=dimension, score=score, note=f"note for {dimension.value}"
    )


def _dimensions() -> tuple[EvaluationDimensionScore, ...]:
    return (
        _score(EvaluationDimension.EVIDENCE_SUFFICIENCY, 70),
        _score(EvaluationDimension.REPLAY_COMPLETENESS, 80),
    )


def test_missing_evidence_yields_insufficient_evidence() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=_dimensions(),
        evidence_refs=(),
        contradiction_refs=(),
    )
    assert evaluation.status is CognitiveEvaluationStatus.INSUFFICIENT_EVIDENCE


def test_contradictory_evidence_yields_contradictory_evidence() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=_dimensions(),
        evidence_refs=("ev-1",),
        contradiction_refs=("contradiction-1",),
    )
    assert evaluation.status is CognitiveEvaluationStatus.CONTRADICTORY_EVIDENCE


def test_sufficient_for_evaluation() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=_dimensions(),
        evidence_refs=("ev-1",),
        contradiction_refs=(),
    )
    assert evaluation.status is CognitiveEvaluationStatus.SUFFICIENT_FOR_EVALUATION


def test_evaluation_not_applicable_for_blank_reference() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="   ",
        dimensions=_dimensions(),
        evidence_refs=("ev-1",),
        contradiction_refs=(),
    )
    assert evaluation.status is CognitiveEvaluationStatus.EVALUATION_NOT_APPLICABLE


def test_evaluation_not_applicable_for_empty_dimensions() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=(),
        evidence_refs=("ev-1",),
        contradiction_refs=(),
    )
    assert evaluation.status is CognitiveEvaluationStatus.EVALUATION_NOT_APPLICABLE


def test_evaluation_cannot_confer_authority() -> None:
    assert set(CognitiveEvaluationStatus.__members__) == {
        "SUFFICIENT_FOR_EVALUATION",
        "INSUFFICIENT_EVIDENCE",
        "CONTRADICTORY_EVIDENCE",
        "EVALUATION_NOT_APPLICABLE",
    }
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=_dimensions(),
        evidence_refs=("ev-1",),
        contradiction_refs=(),
    )
    for forbidden in (
        "authority",
        "order",
        "account",
        "credential",
        "promotion",
        "execute",
        "risk",
    ):
        assert not hasattr(evaluation, forbidden)


def test_dimension_score_rejects_bool() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        EvaluationDimensionScore(
            dimension=EvaluationDimension.EVIDENCE_SUFFICIENCY,
            score=True,
            note="x",
        )


def test_duplicate_dimensions_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CognitiveEvaluation(
            evaluation_id=_EVALUATION,
            evaluated_reference="episode:1",
            dimensions=(
                _score(EvaluationDimension.EVIDENCE_SUFFICIENCY),
                _score(EvaluationDimension.EVIDENCE_SUFFICIENCY),
            ),
            status=CognitiveEvaluationStatus.SUFFICIENT_FOR_EVALUATION,
            evidence_refs=("ev-1",),
            contradiction_refs=(),
        )


def test_inconsistent_status_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CognitiveEvaluation(
            evaluation_id=_EVALUATION,
            evaluated_reference="episode:1",
            dimensions=_dimensions(),
            status=CognitiveEvaluationStatus.SUFFICIENT_FOR_EVALUATION,
            evidence_refs=(),
            contradiction_refs=(),
        )


def test_evaluate_rejects_non_str_reference_without_leaking_exception() -> None:
    bad_reference: Any = 123
    with pytest.raises(CiboCognitiveValidationError):
        evaluate_cognition(
            evaluation_id=_EVALUATION,
            evaluated_reference=bad_reference,
            dimensions=_dimensions(),
            evidence_refs=("ev-1",),
            contradiction_refs=(),
        )


def test_evaluate_rejects_non_score_dimensions_without_leaking_exception() -> None:
    bad_dimensions: Any = ["not-a-score"]
    with pytest.raises(CiboCognitiveValidationError):
        evaluate_cognition(
            evaluation_id=_EVALUATION,
            evaluated_reference="episode:1",
            dimensions=bad_dimensions,
            evidence_refs=("ev-1",),
            contradiction_refs=(),
        )
