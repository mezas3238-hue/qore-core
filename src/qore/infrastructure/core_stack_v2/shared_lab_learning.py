"""Meta-learning, continual-learning and OOD receipts for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LearningStabilityReceipt:
    capability_id: str
    baseline_skill_score: float
    post_update_skill_score: float
    novel_regime_score_before: float
    novel_regime_score_after: float
    max_allowed_retention_loss: float
    minimum_required_adaptation_gain: float
    update_used_future_outcome: bool

    @property
    def retention_loss(self) -> float:
        return self.baseline_skill_score - self.post_update_skill_score

    @property
    def adaptation_gain(self) -> float:
        return self.novel_regime_score_after - self.novel_regime_score_before

    @property
    def passed(self) -> bool:
        return (
            not self.update_used_future_outcome
            and self.retention_loss <= self.max_allowed_retention_loss
            and self.adaptation_gain >= self.minimum_required_adaptation_gain
        )


@dataclass(frozen=True, slots=True)
class OODReceipt:
    capability_id: str
    case_id: str
    novelty_score: float
    novelty_threshold: float
    detected_as_ood: bool
    confidence_reduced: bool
    abstained_when_required: bool

    @property
    def actually_ood(self) -> bool:
        return self.novelty_score >= self.novelty_threshold

    @property
    def passed(self) -> bool:
        if not self.actually_ood:
            return True
        return (
            self.detected_as_ood
            and self.confidence_reduced
            and self.abstained_when_required
        )
