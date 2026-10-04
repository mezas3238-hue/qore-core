import pytest

from qore.infrastructure.core_stack_v2.continual_learning_governance import (
    ContinualKnowledgeTier,
    ContinualLearningCandidate,
    KnowledgeCapabilityScore,
    assess_continual_candidate,
)


def _scores(a: int, b: int):
    return (
        KnowledgeCapabilityScore("A", a),
        KnowledgeCapabilityScore("B", b),
    )


def test_experimental_cannot_jump_directly_to_certified() -> None:
    with pytest.raises(ValueError, match="cannot jump"):
        ContinualLearningCandidate(
            candidate_id="jump",
            source_tier=ContinualKnowledgeTier.EXPERIMENTAL,
            target_tier=ContinualKnowledgeTier.STABLE_CERTIFIED,
            baseline=_scores(9000, 9000),
            candidate=_scores(9000, 9000),
            transportability_bps=9000,
            knowledge_half_life_days=30,
            maximum_allowed_regression_bps=500,
            evidence_refs=("test:jump",),
        )


def test_catastrophic_forgetting_blocks_promotion() -> None:
    candidate = ContinualLearningCandidate(
        candidate_id="forgetting",
        source_tier=ContinualKnowledgeTier.EXPERIMENTAL,
        target_tier=ContinualKnowledgeTier.RECENT_VALIDATED_ADAPTATION,
        baseline=_scores(9000, 9000),
        candidate=_scores(8900, 7000),
        transportability_bps=9000,
        knowledge_half_life_days=30,
        maximum_allowed_regression_bps=500,
        evidence_refs=("test:forgetting",),
    )
    result = assess_continual_candidate(candidate)
    assert result.catastrophic_forgetting_detected is True
    assert result.promotion_allowed is False


def test_transportable_nonregressing_candidate_can_advance_one_tier() -> None:
    candidate = ContinualLearningCandidate(
        candidate_id="safe",
        source_tier=ContinualKnowledgeTier.EXPERIMENTAL,
        target_tier=ContinualKnowledgeTier.RECENT_VALIDATED_ADAPTATION,
        baseline=_scores(9000, 9000),
        candidate=_scores(9200, 8900),
        transportability_bps=8500,
        knowledge_half_life_days=30,
        maximum_allowed_regression_bps=500,
        evidence_refs=("test:safe",),
    )
    result = assess_continual_candidate(candidate)
    assert result.catastrophic_forgetting_detected is False
    assert result.promotion_allowed is True
