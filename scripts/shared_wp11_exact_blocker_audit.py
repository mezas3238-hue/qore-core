#!/usr/bin/env python3
"""WP-11 governed self-improvement exact blocker audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IDENTITY = "QORE_SHARED_WP11_EXACT_BLOCKER_AUDIT_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc23", type=Path, required=True)
    parser.add_argument("--mc24", type=Path, required=True)
    parser.add_argument("--mc25", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mc23 = _load(args.mc23)
    mc24 = _load(args.mc24)
    mc25 = _load(args.mc25)

    if mc23.get("status") != "MC23_REAL_NOVELTY_DETECTION_BOUND_PASS":
        raise AssertionError("MC23 real novelty evidence missing")
    if mc24.get("status") != "MC24_REAL_REGRESSION_SUITE_BOUND_PASS":
        raise AssertionError("MC24 real regression evidence missing")
    if mc25.get("status") != "MC25_WP04_V3B_LINEAGE_INTEGRITY_STRESS_PASS":
        raise AssertionError("MC25 lineage-integrity stress evidence missing")

    blockers: list[str] = []
    if mc23.get("real_novel_regime_validated_adaptation") is not True:
        blockers.append("MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION")
    if mc24.get("empirical_half_life_validated") is not True:
        blockers.append("MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE")
    if mc24.get("mc23_real_regime_adaptation_bound") is not True:
        blockers.append("MC24_BIND_REAL_MC23_ADAPTATION")
    if mc25.get("performance_stress_bound") is not True:
        blockers.append("MC25_SAME_LINEAGE_PERFORMANCE_STRESS")
    if mc25.get("formal_stress_stage_completed") is not True:
        blockers.append("MC25_FORMAL_STRESS_STAGE")
    if mc25.get("shadow_stage_bound") is not True:
        blockers.append("MC25_SAME_LINEAGE_SHADOW")
    if mc25.get("certification_stage_bound") is not True:
        blockers.append("MC25_CERTIFICATION")
    if mc25.get("promotion_allowed") is not True:
        blockers.append("MC25_GOVERNED_PROMOTION")

    expected = (
        "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION",
        "MC24_BIND_REAL_MC23_ADAPTATION",
        "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE",
        "MC25_CERTIFICATION",
        "MC25_FORMAL_STRESS_STAGE",
        "MC25_GOVERNED_PROMOTION",
        "MC25_SAME_LINEAGE_PERFORMANCE_STRESS",
        "MC25_SAME_LINEAGE_SHADOW",
    )
    blockers_tuple = tuple(sorted(blockers))
    if blockers_tuple != expected:
        raise AssertionError(f"WP11 blocker inventory drifted: {blockers_tuple}")

    payload = {
        "identity": IDENTITY,
        "status": "WP11_GOVERNED_SELF_IMPROVEMENT_OPEN_EXACT_BLOCKERS",
        "real_novelty_detection_bound": True,
        "real_regression_suite_bound": True,
        "lineage_integrity_stress_pass": True,
        "blocker_count": len(blockers_tuple),
        "blockers": blockers_tuple,
        "zero_open_work": False,
        "wp11_completed_and_proven": False,
        "productive_authority": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
