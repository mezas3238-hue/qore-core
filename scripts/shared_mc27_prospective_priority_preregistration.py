#!/usr/bin/env python3
"""MC-27 prospective meta-cognitive priority and experiment preregistration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.meta_cognitive_scientific_intelligence import (
    MetaCognitiveConcern,
    MetaCognitiveObservation,
    assess_meta_cognition,
)

IDENTITY = "QORE_SHARED_MC27_PROSPECTIVE_PRIORITY_PREREGISTRATION_AUDIT_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc18", type=Path, required=True)
    parser.add_argument("--mc28", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mc18 = _load(args.mc18)
    mc28 = _load(args.mc28)
    prereg = _load(args.preregistration)

    if mc18.get("status") != "MC18_COUNTERFACTUAL_WORLD_ENGINE_REAL_DATA_BOUND_PASS":
        raise AssertionError("MC18 foundation is not real-data-bound")
    if mc18.get("probability_calibration_demonstrated") is not False:
        raise AssertionError("MC18 calibration gap unexpectedly closed")
    if mc18.get("fresh_oos_path_distribution_value_demonstrated") is not False:
        raise AssertionError("MC18 OOS value gap unexpectedly closed")
    if mc28.get("status") != "MC28_STANDARD_006_DIAGNOSTIC_CONTRACT_PASS_OPEN_5":
        raise AssertionError("MC28 current gap inventory missing")
    open_count = int(mc28["open_diagnostic_count"])
    if open_count != 5:
        raise AssertionError("MC28 open diagnostic count drifted")
    if prereg.get("status") != "PREREGISTERED_BEFORE_FUTURE_RESEARCH_OOS":
        raise AssertionError("MC27 prospective experiment is not frozen")
    if prereg["future_research_oos"]["opened"] is not False:
        raise AssertionError("future research OOS must still be unopened")

    information_gap_bps = open_count * 10_000 // 8
    observation = MetaCognitiveObservation(
        prediction_error_bps=0,
        calibration_error_bps=0,
        model_disagreement_bps=0,
        dominant_specialist_share_bps=0,
        concept_decay_bps=0,
        regime_novelty_bps=0,
        information_gap_bps=information_gap_bps,
        falsification_coverage_bps=10_000,
        expected_compute_value_bps=max(2_500, information_gap_bps - 1_000),
        evidence_refs=(
            "artifact:11119876541",
            "artifact:11126275619",
            "run:36764204066",
            "run:36777388801",
        ),
    )
    assessment = assess_meta_cognition(observation)
    if not assessment.priorities:
        raise AssertionError("MC27 emitted no research priority")
    top = assessment.priorities[0]
    expected = MetaCognitiveConcern(
        prereg["detected_weakness"]["expected_top_concern"]
    )
    if top.concern is not expected:
        raise AssertionError(
            f"MC27 top concern drifted: {top.concern.value} != {expected.value}"
        )

    payload = {
        "identity": IDENTITY,
        "status": "MC27_PROSPECTIVE_RESEARCH_PRIORITY_PREREGISTERED",
        "top_concern": top.concern.value,
        "top_priority_bps": top.priority_bps,
        "question": top.question,
        "falsification_requirement": top.falsification_requirement,
        "deeper_compute_justified": top.deeper_compute_justified,
        "research_indices_are_not_calibrated_probabilities": True,
        "current_information_gap_bps": information_gap_bps,
        "mc18_calibration_gap_detected": True,
        "mc18_future_oos_gap_detected": True,
        "mc28_open_diagnostic_count": open_count,
        "prospective_priority_generated": True,
        "future_experiment_preregistered": True,
        "future_oos_window": prereg["future_research_oos"],
        "future_oos_opened": False,
        "future_oos_improvement_demonstrated": False,
        "self_modification_authority": assessment.self_modification_authority,
        "certified_runtime_mutation": assessment.certified_runtime_mutation,
        "productive_authority": False,
        "mc27_completed_and_proven": False,
        "next_gate": (
            "EXECUTE_PREREGISTERED_MC18_CALIBRATION_ON_FUTURE_RESEARCH_OOS"
        ),
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
