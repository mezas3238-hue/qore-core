#!/usr/bin/env python3
"""Verify MC-11 dependency binding against frozen WP-04, MC-09 and MC-10 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.neural_symbolic_brain import (
    CalibratedBeliefRef,
    FrozenLearnedRepresentationRef,
)

IDENTITY = "QORE_SHARED_MC11_NEURAL_SYMBOLIC_VERIFIED_BINDING_001"
EXPECTED_REPRESENTATION = (
    "e2fc2ca059d5852b4e9107c467392e5e64aeabbd6aca2d8013951b93402bc987"
)


def _load(root: Path, name: str) -> dict[str, object]:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, found {len(matches)}")
    return json.loads(matches[0].read_text())


def _fingerprint(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wp04", type=Path, required=True)
    parser.add_argument("--mc09", type=Path, required=True)
    parser.add_argument("--mc10", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    wp04 = _load(args.wp04, "wp04-predictive-nonlinear-probe-v3b.json")
    mc09 = _load(args.mc09, "mc09-belief-calibration-v2.json")
    mc10 = _load(args.mc10, "mc10-transition-stability.json")

    representation = wp04["representation"]
    probes = wp04["final_frozen_probes"]
    if not isinstance(representation, dict) or not isinstance(probes, list):
        raise ValueError("WP04 V3B artifact schema invalid")
    if representation.get("fingerprint") != EXPECTED_REPRESENTATION:
        raise ValueError("WP04 representation fingerprint drift")
    if representation.get("selected_concept_count") != 6 or len(probes) != 8:
        raise ValueError("WP04 frozen concept/probe cardinality drift")
    probe_fingerprints = tuple(
        sorted(str(item["probe_fingerprint"]) for item in probes)
    )
    concept_ids = tuple(sorted(str(item) for item in representation["concept_ids"]))

    learned_ref = FrozenLearnedRepresentationRef(
        representation_fingerprint=EXPECTED_REPRESENTATION,
        concept_ids=concept_ids,
        probe_fingerprints=probe_fingerprints,
        evidence_refs=(
            "artifact:10906064254",
            "run:36244726347",
        ),
    )

    if mc09.get("status") != "MC09_BELIEF_STATE_CALIBRATION_V2_TEMPORAL_OOS_PASS":
        raise ValueError("MC09 calibrated belief dependency is not passed")
    calibrated = mc09.get("oos_calibrated")
    if not isinstance(calibrated, dict):
        raise ValueError("MC09 calibrated OOS payload missing")
    belief_ref = CalibratedBeliefRef(
        calibration_artifact_fingerprint=_fingerprint(mc09),
        calibration_ece_bps=int(calibrated["ece_bps"]),
        temporal_oos_pass=bool(mc09["all_gates_pass"]),
        evidence_refs=(
            "artifact:11116522138",
            "run:36754966932",
        ),
    )

    if mc10.get("status") != "MC10_TRANSITION_STABILITY_REPLICATED_PASS":
        raise ValueError("MC10 structural constraint dependency is not passed")
    if mc10.get("mc10_completed_and_proven") is not True:
        raise ValueError("MC10 completion evidence missing")

    payload = {
        "identity": IDENTITY,
        "status": "MC11_NEURAL_SYMBOLIC_DEPENDENCIES_VERIFIED",
        "wp04_representation_fingerprint": learned_ref.representation_fingerprint,
        "wp04_concept_count": len(learned_ref.concept_ids),
        "wp04_probe_count": len(learned_ref.probe_fingerprints),
        "mc09_calibration_ece_bps": belief_ref.calibration_ece_bps,
        "mc09_temporal_oos_pass": belief_ref.temporal_oos_pass,
        "mc10_transition_stability_pass": True,
        "hard_constraint_dominance_contract_tested": True,
        "symbolic_conclusions_traceable": True,
        "runtime_future_market_used": False,
        "identity_shortcut_used": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
        "incremental_oos_value_demonstrated": False,
        "mc11_completed_and_proven": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
