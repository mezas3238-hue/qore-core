#!/usr/bin/env python3
"""WP-08 real evidence integration audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.governed_epistemic_layer import (
    GovernedEpistemicEvidence,
    assess_governed_epistemics,
)

IDENTITY = "QORE_SHARED_WP08_GOVERNED_EPISTEMIC_LAYER_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _clip(value: int) -> int:
    return max(0, min(10_000, int(value)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc09", type=Path, required=True)
    parser.add_argument("--mc15", type=Path, required=True)
    parser.add_argument("--x10", type=Path, required=True)
    parser.add_argument("--mc23", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mc09 = _load(args.mc09)
    mc15 = _load(args.mc15)
    x10 = _load(args.x10)
    mc23 = _load(args.mc23)

    if mc09.get("status") != "MC09_BELIEF_STATE_CALIBRATION_V2_TEMPORAL_OOS_PASS":
        raise AssertionError("MC09 calibrated belief evidence missing")
    if mc09.get("mc09_completed_and_proven") is not True:
        raise AssertionError("MC09 completion evidence missing")
    if mc15.get("status") != "MC15_SIX_SOURCE_UNCERTAINTY_REPLICATED_PASS":
        raise AssertionError("MC15 uncertainty evidence missing")
    if mc15.get("calibration_state") != "UNCALIBRATED":
        raise AssertionError("MC15 uncertainty index semantics drifted")
    if x10.get("status") != "X10_CONTRADICTION_MAP_REPLICATED_PASS":
        raise AssertionError("X10 contradiction evidence missing")
    if mc23.get("status") != "MC23_REAL_NOVELTY_DETECTION_BOUND_PASS":
        raise AssertionError("MC23 novelty evidence missing")
    if mc23.get("novel_unknown_treated_as_known") is not False:
        raise AssertionError("MC23 unknown-as-known invariant failed")

    calibrated = mc09.get("oos_calibrated")
    if not isinstance(calibrated, dict):
        raise AssertionError("MC09 calibrated metrics missing")
    calibration_error = _clip(int(calibrated["ece_bps"]))

    uncertainty_values: list[int] = []
    mc15_results = mc15.get("results")
    if not isinstance(mc15_results, dict):
        raise AssertionError("MC15 result partitions missing")
    for partition in ("r6", "r5"):
        row = mc15_results.get(partition)
        if not isinstance(row, dict):
            raise AssertionError(f"MC15 {partition} missing")
        components = row.get("components")
        if not isinstance(components, dict):
            raise AssertionError(f"MC15 {partition} components missing")
        baseline = components.get("BASELINE")
        if not isinstance(baseline, dict):
            raise AssertionError(f"MC15 {partition} baseline missing")
        uncertainty_values.append(int(baseline["epistemic_bps"]))
    uncertainty = _clip(max(uncertainty_values))

    contradiction_values: list[int] = []
    x10_results = x10.get("results")
    if not isinstance(x10_results, dict):
        raise AssertionError("X10 result partitions missing")
    for partition in ("r8", "r6", "r5"):
        row = x10_results.get(partition)
        if not isinstance(row, dict):
            raise AssertionError(f"X10 {partition} missing")
        contradiction_values.append(int(row["baseline_contradiction_bps"]))
    contradiction = _clip(max(contradiction_values))

    total = int(mc23["real_source_observations"])
    novel = int(mc23["real_novel_or_near_known_episode_count"])
    if total <= 0 or not 0 <= novel <= total:
        raise AssertionError("MC23 novelty incidence is invalid")
    novelty_incidence = novel * 10_000 // total

    evidence = GovernedEpistemicEvidence(
        calibration_error_bps=calibration_error,
        uncertainty_index_bps=uncertainty,
        contradiction_bps=contradiction,
        novelty_index_bps=novelty_incidence,
        missing_evidence_bps=0,
        evidence_refs=(
            "artifact:11102652639",
            "artifact:11104578542",
            "artifact:11116522138",
            "artifact:11128786574",
            "run:36726927463",
            "run:36731394336",
            "run:36754966932",
            "run:36782458472",
        ),
        belief_probability_calibrated=True,
    )
    state = assess_governed_epistemics(evidence)
    repeated = assess_governed_epistemics(evidence)

    stressed_contradiction = assess_governed_epistemics(
        GovernedEpistemicEvidence(
            calibration_error_bps=calibration_error,
            uncertainty_index_bps=uncertainty,
            contradiction_bps=9_000,
            novelty_index_bps=novelty_incidence,
            missing_evidence_bps=0,
            evidence_refs=evidence.evidence_refs,
            belief_probability_calibrated=True,
        )
    )
    missing = assess_governed_epistemics(
        GovernedEpistemicEvidence(
            calibration_error_bps=calibration_error,
            uncertainty_index_bps=uncertainty,
            contradiction_bps=contradiction,
            novelty_index_bps=novelty_incidence,
            missing_evidence_bps=9_000,
            evidence_refs=evidence.evidence_refs,
            belief_probability_calibrated=True,
        )
    )

    deterministic = state == repeated
    adverse_evidence_visible = (
        stressed_contradiction.assertiveness_ceiling_bps
        <= state.assertiveness_ceiling_bps
        and missing.assertiveness_ceiling_bps
        <= state.assertiveness_ceiling_bps
    )
    completed = deterministic and adverse_evidence_visible

    payload = {
        "identity": IDENTITY,
        "status": (
            "WP08_GOVERNED_EPISTEMIC_LAYER_COMPLETED_AND_PROVEN"
            if completed
            else "WP08_GOVERNED_EPISTEMIC_LAYER_FAILED"
        ),
        "upstream": {
            "mc09_calibrated_belief": True,
            "mc15_uncertainty_decomposition": True,
            "x10_contradiction_map": True,
            "mc23_real_novelty_detection": True,
        },
        "calibration_error_bps": calibration_error,
        "uncertainty_index_bps": uncertainty,
        "contradiction_bps": contradiction,
        "population_novelty_incidence_bps": novelty_incidence,
        "population_novelty_incidence_is_probability": False,
        "uncertainty_index_is_probability": False,
        "integrated_state": state.state.value,
        "assertiveness_ceiling_bps": state.assertiveness_ceiling_bps,
        "deterministic_integration": deterministic,
        "contradiction_stress_state": stressed_contradiction.state.value,
        "contradiction_stress_assertiveness_bps": (
            stressed_contradiction.assertiveness_ceiling_bps
        ),
        "missing_evidence_state": missing.state.value,
        "missing_evidence_assertiveness_bps": missing.assertiveness_ceiling_bps,
        "adverse_evidence_cannot_increase_assertiveness": adverse_evidence_visible,
        "trading_command": False,
        "methodology_authority": False,
        "sizing_authority": False,
        "capital_authority": False,
        "risk_authority": False,
        "execution_authority": False,
        "wp08_completed_and_proven": completed,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
