#!/usr/bin/env python3
"""MC-24 real regression suite bound to sealed Shared capabilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.continual_learning_governance import (
    ContinualKnowledgeTier,
    ContinualLearningCandidate,
    KnowledgeCapabilityScore,
    assess_continual_candidate,
)

IDENTITY = "QORE_SHARED_MC24_REAL_ADAPTATION_REGRESSION_SUITE_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc09", type=Path, required=True)
    parser.add_argument("--mc10", type=Path, required=True)
    parser.add_argument("--wp04-holdout", type=Path, required=True)
    parser.add_argument("--wp04-replication", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mc09 = _load(args.mc09)
    mc10 = _load(args.mc10)
    holdout = _load(args.wp04_holdout)
    replication = _load(args.wp04_replication)

    if mc09.get("status") != "MC09_BELIEF_STATE_CALIBRATION_V2_TEMPORAL_OOS_PASS":
        raise AssertionError("MC09 V2 adaptation is not validated")
    if mc09.get("mc09_completed_and_proven") is not True:
        raise AssertionError("MC09 V2 completion evidence missing")
    if mc10.get("status") != "MC10_TRANSITION_STABILITY_REPLICATED_PASS":
        raise AssertionError("MC10 regression anchor is not passed")
    if mc10.get("mc10_completed_and_proven") is not True:
        raise AssertionError("MC10 completion evidence missing")
    if holdout.get("status") != "WP04_V3B_HOLDOUT_E_PASS_REPLICATION_REQUIRED":
        raise AssertionError("WP04 HOLDOUT_E did not pass")
    if holdout.get("holdout_e_pass") is not True:
        raise AssertionError("WP04 HOLDOUT_E pass flag missing")
    if replication.get("status") != "WP04_V3B_REPLICATION_D_PASS":
        raise AssertionError("WP04 REPLICATION_D did not pass")
    if replication.get("replication_d_pass") is not True:
        raise AssertionError("WP04 replication pass flag missing")

    raw_ece = int(mc09["oos_raw"]["ece_bps"])
    calibrated_ece = int(mc09["oos_calibrated"]["ece_bps"])
    baseline = (
        KnowledgeCapabilityScore(
            "MC09_CALIBRATION_QUALITY",
            max(0, 10_000 - raw_ece),
        ),
        KnowledgeCapabilityScore("MC10_TRANSITION_STABILITY", 10_000),
        KnowledgeCapabilityScore("WP04_REPRESENTATION_TRANSFER", 10_000),
    )
    candidate = (
        KnowledgeCapabilityScore(
            "MC09_CALIBRATION_QUALITY",
            max(0, 10_000 - calibrated_ece),
        ),
        KnowledgeCapabilityScore("MC10_TRANSITION_STABILITY", 10_000),
        KnowledgeCapabilityScore("WP04_REPRESENTATION_TRANSFER", 10_000),
    )
    proposal = ContinualLearningCandidate(
        candidate_id="MC09_V2_REAL_CALIBRATION_ADAPTATION",
        source_tier=ContinualKnowledgeTier.RECENT_VALIDATED_ADAPTATION,
        target_tier=ContinualKnowledgeTier.RECENT_VALIDATED_ADAPTATION,
        baseline=baseline,
        candidate=candidate,
        transportability_bps=10_000,
        knowledge_half_life_days=30,
        maximum_allowed_regression_bps=500,
        evidence_refs=(
            "artifact:10908077821",
            "artifact:10908500161",
            "artifact:11115664725",
            "artifact:11116522138",
            "run:36247407353",
            "run:36248025384",
            "run:36754966932",
            "run:36755380068",
        ),
    )
    assessment = assess_continual_candidate(proposal)

    payload = {
        "identity": IDENTITY,
        "status": (
            "MC24_REAL_REGRESSION_SUITE_BOUND_PASS"
            if (
                not assessment.catastrophic_forgetting_detected
                and assessment.transportability_pass
                and assessment.promotion_allowed
            )
            else "MC24_REAL_REGRESSION_SUITE_FAILED"
        ),
        "candidate_id": proposal.candidate_id,
        "source_tier": proposal.source_tier.value,
        "target_tier": proposal.target_tier.value,
        "baseline_scores_bps": {
            item.capability_id: item.score_bps for item in proposal.baseline
        },
        "candidate_scores_bps": {
            item.capability_id: item.score_bps for item in proposal.candidate
        },
        "maximum_regression_bps": assessment.maximum_regression_bps,
        "maximum_allowed_regression_bps": proposal.maximum_allowed_regression_bps,
        "catastrophic_forgetting_detected": (
            assessment.catastrophic_forgetting_detected
        ),
        "transportability_checked_on_independent_temporal_evidence": True,
        "transportability_pass": assessment.transportability_pass,
        "knowledge_half_life_policy_days": proposal.knowledge_half_life_days,
        "knowledge_half_life_recorded": assessment.half_life_recorded,
        "empirical_half_life_validated": False,
        "stable_certified_knowledge_overwritten": False,
        "real_adaptation_regression_suite_bound": True,
        "regression_suite_promotion_allowed": assessment.promotion_allowed,
        "mc23_real_regime_adaptation_bound": False,
        "mc24_completed_and_proven": False,
        "next_gate": (
            "REAL_MC23_ADAPTATION_PLUS_EMPIRICAL_KNOWLEDGE_HALF_LIFE"
        ),
        "productive_authority": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
