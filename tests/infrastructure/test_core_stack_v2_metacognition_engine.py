# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.metacognition_engine import (
    MetacognitiveEvidence,
    UnderstandingState,
    assess_metacognition,
)


NOW = datetime(2026, 9, 26, 3, 10, tzinfo=UTC)


def test_high_quality_low_novelty_state_is_understood() -> None:
    result = assess_metacognition(
        MetacognitiveEvidence(
            as_of=NOW,
            data_quality_bps=9_000,
            hypothesis_entropy_bps=2_000,
            model_disagreement_bps=1_500,
            novelty_bps=1_000,
            causal_consistency_bps=8_500,
            historical_similarity_bps=8_000,
            calibration_bps=8_000,
            regime_familiarity_bps=8_500,
        )
    )

    assert result.state is UnderstandingState.HIGH
    assert result.confidence_bps >= 7_500
    assert result.execution_authority is False


def test_novel_conflicted_state_reports_low_understanding() -> None:
    result = assess_metacognition(
        MetacognitiveEvidence(
            as_of=NOW,
            data_quality_bps=8_000,
            hypothesis_entropy_bps=8_000,
            model_disagreement_bps=8_000,
            novelty_bps=8_500,
            causal_consistency_bps=3_000,
            historical_similarity_bps=2_000,
            calibration_bps=4_500,
            regime_familiarity_bps=2_500,
        )
    )

    assert result.state is UnderstandingState.LOW
    assert "STATE_NOVEL_OR_OUT_OF_DISTRIBUTION" in result.reasons
    assert "MODEL_DISAGREEMENT_HIGH" in result.reasons


def test_very_low_data_quality_yields_unknown() -> None:
    result = assess_metacognition(
        MetacognitiveEvidence(
            as_of=NOW,
            data_quality_bps=2_000,
            hypothesis_entropy_bps=5_000,
            model_disagreement_bps=5_000,
            novelty_bps=5_000,
            causal_consistency_bps=5_000,
            historical_similarity_bps=5_000,
            calibration_bps=5_000,
            regime_familiarity_bps=5_000,
        )
    )

    assert result.state is UnderstandingState.UNKNOWN
    assert "INSUFFICIENT_OBSERVABILITY" in result.reasons
