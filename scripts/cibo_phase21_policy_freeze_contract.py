"""Emit the Phase21 policy-freeze prerequisite contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21EmpiricalValidationKind,
    phase21_empirical_validation_plan_sha256,
)


def build_report() -> dict[str, Any]:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    return {
        "schema": "qore.cibo.phase21.policy-freeze-contract.v1",
        "status": "CONTRACT_READY_CERTIFICATION_PREREQUISITES_PENDING",
        "candidate_id": candidate.candidate_id,
        "candidate_code_sha": candidate.code_sha,
        "candidate_parameter_sha256": candidate.parameter_sha256(),
        "phase20d_plan_id": plan.plan_id,
        "phase20d_plan_sha256": phase20d_qualification_plan_sha256(),
        "required_phase20d_status": "PASS",
        "required_empirical_validations": sorted(
            item.value for item in Phase21EmpiricalValidationKind
        ),
        "required_empirical_evidence_class": "FORWARD_EMPIRICAL",
        "empirical_validation_lineage_plan_sha256": (
            phase21_empirical_validation_plan_sha256()
        ),
        "empirical_receipt_requires_exact_qualification_population": True,
        "empirical_receipt_requires_canonical_report_digest": True,
        "empirical_receipt_requires_validator_git_sha": True,
        "freeze_requires_exact_policy_surface_digests": True,
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
