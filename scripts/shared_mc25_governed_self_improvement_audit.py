#!/usr/bin/env python3
"""MC-25 real-lineage governed self-improvement audit."""

from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.governed_self_improvement import (
    GovernedImprovementProposal,
    ImprovementStage,
    ImprovementStageEvidence,
    ImprovementTarget,
)

IDENTITY = "QORE_SHARED_MC25_GOVERNED_SELF_IMPROVEMENT_AUDIT_001"


def main() -> None:
    stages = (
        ImprovementStageEvidence(
            ImprovementStage.DISCOVERY,
            "run:36244726347",
            True,
            "R8_R6_R5_CONSUMED",
        ),
        ImprovementStageEvidence(
            ImprovementStage.SANDBOX,
            "artifact:10906064254",
            True,
            "R8_R6_R5_CONSUMED",
        ),
        ImprovementStageEvidence(
            ImprovementStage.FALSIFICATION,
            "run:36244726347",
            True,
            "R8_R6_R5_CONSUMED",
        ),
        ImprovementStageEvidence(
            ImprovementStage.REPLICATION,
            "run:36248025384",
            True,
            "REPLICATION_D_2025_07_14_TO_2026_07_13",
        ),
        ImprovementStageEvidence(
            ImprovementStage.HOLDOUT,
            "run:36247407353",
            True,
            "HOLDOUT_E_2026_07_13_TO_2026_09_25",
        ),
    )
    proposal = GovernedImprovementProposal(
        proposal_id="WP04_V3B_REPRESENTATION_SELF_IMPROVEMENT",
        version="001",
        target=ImprovementTarget.REPRESENTATION,
        rollback_ref="WP04_V3_PRE_V3B",
        provenance_refs=(
            "artifact:10906064254",
            "run:36247407353",
            "run:36248025384",
        ),
        reproducibility_ref="representation:e2fc2ca059d5852",
        stages=stages,
    )
    payload = {
        "identity": IDENTITY,
        "status": "MC25_GOVERNED_SELF_IMPROVEMENT_FOUNDATION_PASS",
        "proposal_id": proposal.proposal_id,
        "highest_completed_stage": proposal.highest_completed_stage.name,
        "promotion_allowed": proposal.promotion_allowed,
        "versioning_present": True,
        "rollback_present": True,
        "provenance_present": True,
        "dataset_window_identity_present": True,
        "reproducibility_present": True,
        "direct_experimental_to_certified": False,
        "stress_bound": False,
        "shadow_bound": False,
        "certification_bound": False,
        "mc25_completed_and_proven": False,
        "next_gate": "STRESS_THEN_SHADOW_THEN_CERTIFICATION",
        "protected_certification_holdout_opened": False,
    }
    Path("result").mkdir(exist_ok=True)
    Path("result/mc25-governed-self-improvement-audit.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
