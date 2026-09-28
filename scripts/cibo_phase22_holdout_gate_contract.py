"""Emit the Phase22 fresh sealed-holdout lineage contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_report() -> dict[str, Any]:
    return {
        "schema": "qore.cibo.phase22.holdout-lineage-contract.v1",
        "status": "CONTRACT_READY_PHASE21_FREEZE_AND_HOLDOUT_PENDING",
        "requirements": [
            "HOLDOUT_DECISIONS_STRICTLY_POST_PHASE21_FREEZE",
            "NO_PHASE20_QUALIFICATION_DECISION_REUSE",
            "EXACT_FROZEN_CANDIDATE_IDENTITY",
            "EXACT_FROZEN_POLICY_CODE_SHA",
            "EXACT_FROZEN_PARAMETER_DIGEST",
            "CAUSAL_DECISION_SEALS_WITHIN_DEADLINE",
            "COMPLETE_SINGLE_COLLECTOR_GIT_LINEAGE",
            "ONE_POLICY_RECORD_PER_DECISION",
            "OUTCOMES_BOUND_TO_PREVIOUSLY_SEALED_DECISIONS",
        ],
        "economic_thresholds_invented_by_contract": False,
        "economic_holdout_pass_claimed": False,
        "separate_preregistered_holdout_evaluation_required": True,
        "governance": {
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
