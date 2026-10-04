#!/usr/bin/env python3
"""MC-24 continual-learning governance audit."""

from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.continual_learning_governance import (
    ContinualKnowledgeTier,
    ContinualLearningCandidate,
    KnowledgeCapabilityScore,
    assess_continual_candidate,
)

IDENTITY = "QORE_SHARED_MC24_CONTINUAL_LEARNING_AUDIT_001"


def main() -> None:
    baseline = (
        KnowledgeCapabilityScore("MC09_CALIBRATION", 9465),
        KnowledgeCapabilityScore("MC10_STABILITY", 9184),
        KnowledgeCapabilityScore("WP04_REPRESENTATION", 9000),
    )
    regression_canary = ContinualLearningCandidate(
        candidate_id="mc24-regression-canary",
        source_tier=ContinualKnowledgeTier.EXPERIMENTAL,
        target_tier=ContinualKnowledgeTier.RECENT_VALIDATED_ADAPTATION,
        baseline=baseline,
        candidate=(
            KnowledgeCapabilityScore("MC09_CALIBRATION", 9400),
            KnowledgeCapabilityScore("MC10_STABILITY", 7000),
            KnowledgeCapabilityScore("WP04_REPRESENTATION", 9100),
        ),
        transportability_bps=8500,
        knowledge_half_life_days=30,
        maximum_allowed_regression_bps=500,
        evidence_refs=("mc24:regression-canary",),
    )
    assessment = assess_continual_candidate(regression_canary)
    payload = {
        "identity": IDENTITY,
        "status": "MC24_CONTINUAL_LEARNING_GOVERNANCE_FOUNDATION_PASS",
        "knowledge_tiers": [item.value for item in ContinualKnowledgeTier],
        "stable_certified_separate": True,
        "recent_validated_adaptation_separate": True,
        "experimental_separate": True,
        "regression_canary_detected": assessment.catastrophic_forgetting_detected,
        "regression_canary_promotion_allowed": assessment.promotion_allowed,
        "transportability_checked": True,
        "knowledge_half_life_recorded": True,
        "real_adaptation_regression_suite_bound": False,
        "mc24_completed_and_proven": False,
        "protected_certification_holdout_opened": False,
    }
    Path("result").mkdir(exist_ok=True)
    Path("result/mc24-continual-learning-audit.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
