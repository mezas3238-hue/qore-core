#!/usr/bin/env python3
"""WP-12 cognitive arbitration/meta-cognition exact blocker audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IDENTITY = "QORE_SHARED_WP12_EXACT_BLOCKER_AUDIT_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc26", type=Path, required=True)
    parser.add_argument("--mc27", type=Path, required=True)
    parser.add_argument("--mc28", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mc26 = _load(args.mc26)
    mc27 = _load(args.mc27)
    mc28 = _load(args.mc28)

    if mc26.get("status") != "MC26_COGNITIVE_ARBITRATION_COMPLETED_AND_PROVEN":
        raise AssertionError("MC26 completed arbitration evidence missing")
    if mc26.get("mc26_completed_and_proven") is not True:
        raise AssertionError("MC26 completion flag missing")
    if mc27.get("status") != "MC27_PROSPECTIVE_RESEARCH_PRIORITY_PREREGISTERED":
        raise AssertionError("MC27 prospective evidence missing")
    if mc28.get("status") != "MC28_STANDARD_006_DIAGNOSTIC_CONTRACT_PASS_OPEN_5":
        raise AssertionError("MC28 diagnostic evidence missing")

    blockers: list[str] = []
    if mc27.get("future_oos_improvement_demonstrated") is not True:
        blockers.append("MC27_PROSPECTIVE_FUTURE_OOS_IMPROVEMENT")
    if mc27.get("mc27_completed_and_proven") is not True:
        blockers.append("MC27_COMPLETED_AND_PROVEN")

    open_diagnostics = tuple(sorted(str(x) for x in mc28["open_diagnostics"]))
    for diagnostic in open_diagnostics:
        blockers.append(f"MC28_DIAGNOSTIC_{diagnostic}")
    if mc28.get("mc28_completed_and_proven") is not True:
        blockers.append("MC28_COMPLETED_AND_PROVEN")

    expected = (
        "MC27_COMPLETED_AND_PROVEN",
        "MC27_PROSPECTIVE_FUTURE_OOS_IMPROVEMENT",
        "MC28_COMPLETED_AND_PROVEN",
        "MC28_DIAGNOSTIC_BROKER_PROVIDER_MISMATCH",
        "MC28_DIAGNOSTIC_CLOCK_DRIFT",
        "MC28_DIAGNOSTIC_EXECUTION_QUALITY_DETERIORATION",
        "MC28_DIAGNOSTIC_MAPPING_ERRORS",
        "MC28_DIAGNOSTIC_MODEL_RUNTIME_INSTABILITY",
    )
    blockers_tuple = tuple(sorted(blockers))
    if blockers_tuple != expected:
        raise AssertionError(f"WP12 blocker inventory drifted: {blockers_tuple}")

    payload = {
        "identity": IDENTITY,
        "status": "WP12_COGNITIVE_ARBITRATION_META_COGNITION_OPEN_EXACT_BLOCKERS",
        "mc26_real_all_facet_arbitration_complete": True,
        "mc27_prospective_cycle_preregistered": True,
        "mc28_runtime_inventory_old_blockers_satisfied": True,
        "mc28_open_diagnostics": open_diagnostics,
        "blocker_count": len(blockers_tuple),
        "blockers": blockers_tuple,
        "zero_open_work": False,
        "wp12_completed_and_proven": False,
        "trading_authority": False,
        "sizing_authority": False,
        "capital_authority": False,
        "risk_authority": False,
        "broker_authority": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
