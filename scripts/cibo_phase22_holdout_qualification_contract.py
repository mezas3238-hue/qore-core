"""Emit the preregistered Phase22 economic holdout contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
    phase22_holdout_qualification_plan_sha256,
)


def build_report() -> dict[str, Any]:
    plan = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    economic = FROZEN_PHASE20D_QUALIFICATION_PLAN
    return {
        "schema": "qore.cibo.phase22.holdout-qualification-contract.v1",
        "status": "CONTRACT_READY_FRESH_POST_PHASE21_HOLDOUT_PENDING",
        "plan_id": plan.plan_id,
        "plan_sha256": phase22_holdout_qualification_plan_sha256(),
        "candidate_id": plan.candidate_id,
        "candidate_parameter_sha256": plan.candidate_parameter_sha256,
        "economic_protocol_plan_id": plan.economic_protocol_plan_id,
        "economic_protocol_plan_sha256": plan.economic_protocol_plan_sha256,
        "population_requirements": {
            "minimum_decision_epochs": economic.minimum_decision_epochs,
            "minimum_candidate_outcomes": economic.minimum_candidate_outcomes,
            "minimum_selected_outcomes": economic.minimum_selected_outcomes,
            "minimum_calendar_span_days": economic.minimum_calendar_span_days,
            "minimum_distinct_trading_days": (
                economic.minimum_distinct_trading_days
            ),
            "minimum_fold_candidate_outcomes": (
                economic.minimum_fold_candidate_outcomes
            ),
            "minimum_global_lineages": economic.minimum_global_lineages,
            "minimum_outcomes_per_lineage": (
                economic.minimum_outcomes_per_lineage
            ),
            "minimum_fold_lineages": economic.minimum_fold_lineages,
            "minimum_candidate_outcome_coverage": format(
                economic.minimum_candidate_outcome_coverage,
                "f",
            ),
            "required_selected_outcome_coverage": format(
                economic.required_selected_outcome_coverage,
                "f",
            ),
            "required_baseline_selected_outcome_coverage": format(
                economic.required_baseline_selected_outcome_coverage,
                "f",
            ),
        },
        "economic_hard_gates": list(economic.hard_gates),
        "lineage_requirements": {
            "strictly_post_phase21_freeze": True,
            "disjoint_from_phase20_qualification": True,
            "exact_frozen_policy_identity": True,
            "causal_decision_seals": True,
            "complete_single_collector_git_lineage": True,
            "exact_policy_decision_set": True,
            "outcomes_bound_to_prior_decisions": True,
        },
        "no_refit": True,
        "synthetic_evidence_allowed": False,
        "holdout_mining_allowed": False,
        "economic_holdout_pass_claimed": False,
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
