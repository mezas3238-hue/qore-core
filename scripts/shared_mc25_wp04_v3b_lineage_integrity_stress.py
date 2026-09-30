#!/usr/bin/env python3
"""MC-25 WP04 V3B governed lineage-integrity stress.

This stress intentionally does NOT claim performance robustness. It proves that
the governed self-improvement lineage fails closed under provenance, fingerprint,
window, gate, leakage, and promotion drift while keeping the formal promotion
chain stopped at HOLDOUT.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.governed_self_improvement import (
    GovernedImprovementProposal,
    ImprovementStage,
    ImprovementStageEvidence,
    ImprovementTarget,
)

IDENTITY = "QORE_SHARED_MC25_WP04_V3B_LINEAGE_INTEGRITY_STRESS_001"
EXPECTED_REPRESENTATION = (
    "e2fc2ca059d5852b4e9107c467392e5e64aeabbd6aca2d8013951b93402bc987"
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _assert_lineage(
    freeze: dict[str, Any],
    holdout: dict[str, Any],
    replication: dict[str, Any],
) -> None:
    if freeze.get("status") != "WP04_V3B_PROBE_FROZEN_FOR_ONE_SHOT_HOLDOUT":
        raise ValueError("freeze status drift")
    if freeze.get("protocol_pass") is not True:
        raise ValueError("freeze protocol drift")
    if freeze.get("development_gate_pass") is not True:
        raise ValueError("freeze development gate drift")
    if freeze.get("probe_frozen_for_holdout") is not True:
        raise ValueError("freeze probe state drift")

    representation = freeze.get("representation")
    if not isinstance(representation, dict):
        raise ValueError("freeze representation missing")
    rep = str(representation.get("fingerprint", ""))
    if rep != EXPECTED_REPRESENTATION:
        raise ValueError("representation fingerprint drift")

    decoder = freeze.get("decoder")
    if not isinstance(decoder, dict):
        raise ValueError("freeze decoder missing")
    if decoder.get("basis_id") != "SYMMETRIC_SECOND_ORDER_V1":
        raise ValueError("decoder basis drift")
    if decoder.get("target_specific_representation_retune") is not False:
        raise ValueError("target-specific representation retune")

    probes = freeze.get("final_frozen_probes")
    if not isinstance(probes, list) or len(probes) != 8:
        raise ValueError("frozen probe count drift")
    probe_fingerprints = {
        str(item.get("probe_fingerprint", ""))
        for item in probes
        if isinstance(item, dict)
    }
    if len(probe_fingerprints) != 8 or any(len(item) != 64 for item in probe_fingerprints):
        raise ValueError("frozen probe fingerprint drift")
    if any(
        item.get("basis_id") != "SYMMETRIC_SECOND_ORDER_V1"
        or item.get("holdout_used_for_fit") is not False
        or item.get("runtime_future_market_used") is not False
        or item.get("identity_used") is not False
        or item.get("knowledge_promotion_authority") is not False
        for item in probes
        if isinstance(item, dict)
    ):
        raise ValueError("frozen probe governance drift")

    if holdout.get("status") != "WP04_V3B_HOLDOUT_E_PASS_REPLICATION_REQUIRED":
        raise ValueError("holdout status drift")
    if holdout.get("holdout_e_pass") is not True:
        raise ValueError("holdout pass drift")
    if holdout.get("representation_fingerprint") != rep:
        raise ValueError("holdout representation fingerprint drift")
    if set(holdout.get("probe_fingerprints", ())) != probe_fingerprints:
        raise ValueError("holdout probe fingerprint drift")
    he = holdout.get("evaluation")
    if not isinstance(he, dict):
        raise ValueError("holdout evaluation missing")
    if he.get("minimum_pooled_incremental_bps") != 100:
        raise ValueError("holdout pooled gate drift")
    if he.get("minimum_positive_target_count") != 4:
        raise ValueError("holdout positive-target gate drift")
    hg = holdout.get("governance")
    if not isinstance(hg, dict):
        raise ValueError("holdout governance missing")
    if hg.get("consumed_representation_refit_on_holdout") is not False:
        raise ValueError("holdout representation refit drift")
    if hg.get("probe_refit_on_holdout") is not False:
        raise ValueError("holdout probe refit drift")
    if hg.get("threshold_retuning_on_holdout") is not False:
        raise ValueError("holdout threshold retune drift")
    if hg.get("runtime_future_market_used") is not False:
        raise ValueError("holdout runtime future leakage")
    if hg.get("knowledge_auto_promotion", False) is not False:
        raise ValueError("holdout knowledge auto-promotion")

    if replication.get("status") != "WP04_V3B_REPLICATION_D_PASS":
        raise ValueError("replication status drift")
    if replication.get("replication_d_pass") is not True:
        raise ValueError("replication pass drift")
    if replication.get("representation_fingerprint") != rep:
        raise ValueError("replication representation fingerprint drift")
    if set(replication.get("probe_fingerprints", ())) != probe_fingerprints:
        raise ValueError("replication probe fingerprint drift")
    re = replication.get("evaluation")
    if not isinstance(re, dict):
        raise ValueError("replication evaluation missing")
    if re.get("minimum_pooled_incremental_bps") != 100:
        raise ValueError("replication pooled gate drift")
    if re.get("minimum_positive_target_count") != 4:
        raise ValueError("replication positive-target gate drift")
    rr = replication.get("replication")
    if not isinstance(rr, dict):
        raise ValueError("replication window missing")
    if rr.get("preregistered_start_inclusive") != "2025-07-14T00:00:00+00:00":
        raise ValueError("replication start-window drift")
    if rr.get("preregistered_end_exclusive") != "2026-07-13T00:00:00+00:00":
        raise ValueError("replication end-window drift")
    rg = replication.get("governance")
    if not isinstance(rg, dict):
        raise ValueError("replication governance missing")
    if rg.get("consumed_representation_refit_on_replication") is not False:
        raise ValueError("replication representation refit drift")
    if rg.get("probe_refit_on_replication") is not False:
        raise ValueError("replication probe refit drift")
    if rg.get("threshold_retuning_on_replication") is not False:
        raise ValueError("replication threshold retune drift")
    if rg.get("runtime_future_market_used") is not False:
        raise ValueError("replication runtime future leakage")
    if rg.get("knowledge_auto_promotion") is not False:
        raise ValueError("replication knowledge auto-promotion")


def _must_reject(
    freeze: dict[str, Any],
    holdout: dict[str, Any],
    replication: dict[str, Any],
) -> bool:
    try:
        _assert_lineage(freeze, holdout, replication)
    except ValueError:
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--replication", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    freeze = _load(args.freeze)
    holdout = _load(args.holdout)
    replication = _load(args.replication)
    _assert_lineage(freeze, holdout, replication)

    scenarios: dict[str, bool] = {}

    f = copy.deepcopy(freeze)
    f["representation"]["fingerprint"] = "0" * 64
    scenarios["REPRESENTATION_FINGERPRINT_DRIFT"] = _must_reject(f, holdout, replication)

    h = copy.deepcopy(holdout)
    h["probe_fingerprints"][0] = "1" * 64
    scenarios["HOLDOUT_PROBE_FINGERPRINT_DRIFT"] = _must_reject(freeze, h, replication)

    h = copy.deepcopy(holdout)
    h["evaluation"]["minimum_pooled_incremental_bps"] = 99
    scenarios["HOLDOUT_GATE_RELAXATION"] = _must_reject(freeze, h, replication)

    r = copy.deepcopy(replication)
    r["evaluation"]["minimum_positive_target_count"] = 3
    scenarios["REPLICATION_GATE_RELAXATION"] = _must_reject(freeze, holdout, r)

    r = copy.deepcopy(replication)
    r["representation_fingerprint"] = "2" * 64
    scenarios["REPLICATION_REPRESENTATION_DRIFT"] = _must_reject(freeze, holdout, r)

    h = copy.deepcopy(holdout)
    h["governance"]["runtime_future_market_used"] = True
    scenarios["HOLDOUT_RUNTIME_FUTURE_LEAKAGE"] = _must_reject(freeze, h, replication)

    r = copy.deepcopy(replication)
    r["governance"]["probe_refit_on_replication"] = True
    scenarios["REPLICATION_PROBE_REFIT"] = _must_reject(freeze, holdout, r)

    f = copy.deepcopy(freeze)
    f["decoder"]["basis_id"] = "DRIFTED_BASIS"
    scenarios["DECODER_BASIS_DRIFT"] = _must_reject(f, holdout, replication)

    r = copy.deepcopy(replication)
    r["replication"]["preregistered_start_inclusive"] = "2025-07-15T00:00:00+00:00"
    scenarios["REPLICATION_WINDOW_DRIFT"] = _must_reject(freeze, holdout, r)

    r = copy.deepcopy(replication)
    r["governance"]["knowledge_auto_promotion"] = True
    scenarios["KNOWLEDGE_AUTO_PROMOTION"] = _must_reject(freeze, holdout, r)

    proposal = GovernedImprovementProposal(
        proposal_id="WP04_V3B_REPRESENTATION",
        version="V3B",
        target=ImprovementTarget.REPRESENTATION,
        rollback_ref="WP04_V3_TEMPORAL_REPRESENTATION",
        provenance_refs=(
            "artifact:10906064254",
            "artifact:10908077821",
            "artifact:10908500161",
            "run:36244726347",
            "run:36247407353",
            "run:36248025384",
        ),
        reproducibility_ref="representation:e2fc2ca059d5852b4e9107c467392e5e64aeabbd6aca2d8013951b93402bc987",
        stages=(
            ImprovementStageEvidence(ImprovementStage.DISCOVERY, "run:36242978209", True, "R8_R6_R5_CONSUMED"),
            ImprovementStageEvidence(ImprovementStage.SANDBOX, "run:36244726347", True, "R8_R6_R5_CONSUMED"),
            ImprovementStageEvidence(ImprovementStage.FALSIFICATION, "run:36244726347", True, "R8_R6_R5_LOO"),
            ImprovementStageEvidence(ImprovementStage.REPLICATION, "run:36248025384", True, "TEMPORAL_REPLICATION_D"),
            ImprovementStageEvidence(ImprovementStage.HOLDOUT, "run:36247407353", True, "HOLDOUT_E"),
        ),
    )

    integrity_pass = all(scenarios.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC25_WP04_V3B_LINEAGE_INTEGRITY_STRESS_PASS"
            if integrity_pass
            else "MC25_WP04_V3B_LINEAGE_INTEGRITY_STRESS_FAIL"
        ),
        "baseline_lineage_validation_pass": True,
        "stress_scenarios": scenarios,
        "stress_scenario_count": len(scenarios),
        "stress_rejected_count": sum(scenarios.values()),
        "lineage_integrity_stress_pass": integrity_pass,
        "performance_stress_bound": False,
        "formal_stress_stage_completed": False,
        "highest_formal_stage": proposal.highest_completed_stage.name,
        "promotion_allowed": proposal.promotion_allowed,
        "shadow_stage_bound": False,
        "certification_stage_bound": False,
        "mc25_completed_and_proven": False,
        "next_gate": "WP04_V3B_SAME_LINEAGE_PERFORMANCE_STRESS",
        "direct_experimental_to_certified": proposal.direct_experimental_to_certified,
        "productive_authority": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
