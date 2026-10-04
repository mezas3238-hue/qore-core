#!/usr/bin/env python3
"""MC-27 real meta-cognitive lineage audit."""

from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.meta_cognitive_scientific_intelligence import (
    MetaCognitiveConcern,
    MetaCognitiveObservation,
    assess_meta_cognition,
)

IDENTITY = "QORE_SHARED_MC27_META_COGNITIVE_AUDIT_001"


def main() -> None:
    # MC09 V1 exposed severe absolute calibration error while preserving
    # ordinal discrimination. The observation below binds that failure mode.
    observation = MetaCognitiveObservation(
        prediction_error_bps=4800,
        calibration_error_bps=5977,
        model_disagreement_bps=3200,
        dominant_specialist_share_bps=1800,
        concept_decay_bps=1000,
        regime_novelty_bps=1800,
        information_gap_bps=2500,
        falsification_coverage_bps=9000,
        expected_compute_value_bps=3500,
        evidence_refs=(
            "run:36753425521",
            "run:36754966932",
        ),
    )
    assessment = assess_meta_cognition(observation)
    top = assessment.priorities[0]
    if top.concern is not MetaCognitiveConcern.OVERCONFIDENCE:
        raise AssertionError("MC27 failed to diagnose the known MC09 failure mode")

    payload = {
        "identity": IDENTITY,
        "status": "MC27_META_COGNITIVE_FOUNDATION_PASS",
        "source_failure_run": 36753425521,
        "subsequent_oos_improvement_run": 36754966932,
        "top_research_concern": top.concern.value,
        "top_priority_bps": top.priority_bps,
        "measurable_oos_improvement_observed_in_lineage": True,
        "automatic_priority_generated_before_v2_historically": False,
        "continuous_self_observation_bound": False,
        "self_modification_authority": assessment.self_modification_authority,
        "certified_runtime_mutation": assessment.certified_runtime_mutation,
        "mc27_completed_and_proven": False,
        "next_gate": "LIVE_RESEARCH_LOOP_PRIORITY_TO_PREREGISTERED_OOS_IMPROVEMENT",
        "protected_certification_holdout_opened": False,
    }
    Path("result").mkdir(exist_ok=True)
    Path("result/mc27-meta-cognitive-audit.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
