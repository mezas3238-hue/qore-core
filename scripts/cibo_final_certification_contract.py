"""Emit the final CIBO economic-certification contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
    phase22_holdout_qualification_plan_sha256,
)


def build_report() -> dict[str, Any]:
    plan = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    return {
        "schema": "qore.cibo.final-economic-certification-contract.v1",
        "status": "PENDING_EMPIRICAL_PHASE20D_PHASE21_PHASE22",
        "phase22_plan_id": plan.plan_id,
        "phase22_plan_sha256": phase22_holdout_qualification_plan_sha256(),
        "required_chain": [
            "PHASE20D_FRESH_FORWARD_PASS",
            "PHASE21_EMPIRICAL_MC_PROVIDER_STRESS_ABLATION_PASS",
            "PHASE21_POLICY_FREEZE_MANIFEST",
            "PHASE22_FRESH_DISJOINT_HOLDOUT_LINEAGE_PASS",
            "PHASE22_ECONOMIC_HOLDOUT_PASS",
            "PHASE22_QUALIFICATION_RECEIPT",
        ],
        "receipt_bindings": [
            "PHASE21_MANIFEST_SHA256",
            "PHASE22_PLAN_SHA256",
            "HOLDOUT_EVIDENCE_STORE_SHA256",
            "HOLDOUT_POLICY_STORE_SHA256",
            "QUALIFICATION_ARTIFACT_SHA256",
            "QUALIFICATION_ARTIFACT_CANONICAL_JSON",
            "PHASE22_VALIDATOR_GIT_SHA",
        ],
        "phase22_receipt_requires_artifact_digest_match": True,
        "phase22_receipt_requires_economic_pass_in_artifact": True,
        "phase22_receipt_requires_zero_holdout_governance_contamination": True,
        "self_certification_allowed": False,
        "historical_or_burned_evidence_allowed": False,
        "synthetic_evidence_allowed": False,
        "pre_freeze_evidence_allowed": False,
        "governance": {
            "economic_certification_grants_demo_execution": False,
            "economic_certification_grants_live": False,
            "economic_certification_grants_real_capital": False,
            "economic_certification_grants_merge": False,
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
