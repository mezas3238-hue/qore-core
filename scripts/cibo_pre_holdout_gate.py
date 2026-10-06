"""Emit the CIBO pre-holdout lock state without reading holdout data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.cibo_ce2i_pre_holdout_gate import (
    CiboPreHoldoutStatus,
    evaluate_pre_holdout_readiness,
)

# These remain false until an explicit pre-holdout freeze commit seals the
# provider-economics and calibration manifests. Changing them is a governed
# freeze action, not a calibration shortcut.
PROVIDER_ECONOMICS_FROZEN = False
CALIBRATION_FREEZE_MANIFEST_SEALED = False
PHASE20D_CAUSAL_TOOL_GATE_PASSED = False
PHASE21_POLICY_FREEZE_SEALED = False


def build_report() -> dict[str, object]:
    readiness = evaluate_pre_holdout_readiness(
        provider_economics_frozen=PROVIDER_ECONOMICS_FROZEN,
        calibration_freeze_manifest_sealed=(
            CALIBRATION_FREEZE_MANIFEST_SEALED
        ),
        phase20d_causal_gate_passed=PHASE20D_CAUSAL_TOOL_GATE_PASSED,
        phase21_policy_freeze_sealed=PHASE21_POLICY_FREEZE_SEALED,
    )
    authorized = (
        readiness.status
        is CiboPreHoldoutStatus.READY_TO_UNSEAL_ACTIVE_HOLDOUT
    )
    return {
        "schema": "qore.cibo.pre_holdout_gate.v1",
        "status": (
            "READY_TO_UNSEAL_ACTIVE_HOLDOUT"
            if authorized
            else "LOCKED_UNTOUCHED"
        ),
        "authorized": authorized,
        "blockers": list(readiness.blockers),
        "tool_matrix_sha256": readiness.tool_matrix_sha256,
        "holdout_candidate_id": readiness.holdout_candidate_id,
        "holdout_outcomes_inspected": readiness.holdout_outcomes_inspected,
        "holdout_market_data_read": readiness.holdout_market_data_read,
        "provider_economics_frozen": PROVIDER_ECONOMICS_FROZEN,
        "phase20d_causal_tool_gate_passed": (
            PHASE20D_CAUSAL_TOOL_GATE_PASSED
        ),
        "phase21_policy_freeze_sealed": PHASE21_POLICY_FREEZE_SEALED,
        "calibration_freeze_manifest_sealed": (
            CALIBRATION_FREEZE_MANIFEST_SEALED
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
