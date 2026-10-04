from qore.infrastructure.core_stack_v2.shared_lab_learning import (
    LearningStabilityReceipt,
    OODReceipt,
)


def test_continual_learning_rejects_catastrophic_forgetting():
    receipt = LearningStabilityReceipt(
        "MC23",
        baseline_skill_score=0.9,
        post_update_skill_score=0.5,
        novel_regime_score_before=0.2,
        novel_regime_score_after=0.6,
        max_allowed_retention_loss=0.1,
        minimum_required_adaptation_gain=0.2,
        update_used_future_outcome=False,
    )
    assert receipt.passed is False


def test_ood_requires_detection_confidence_reduction_and_abstention():
    receipt = OODReceipt(
        "MC23",
        "NOVEL_001",
        novelty_score=0.9,
        novelty_threshold=0.7,
        detected_as_ood=True,
        confidence_reduced=True,
        abstained_when_required=True,
    )
    assert receipt.passed is True
