"""Emit the pre-registered Phase20D V2 forward qualification protocol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)


def build_report() -> dict[str, Any]:
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    return {
        "schema": "qore.cibo.phase20d.qualification_plan.v1",
        "identity": plan.plan_id,
        "status": "PRE_REGISTERED_BEFORE_FRESH_FORWARD_OUTCOMES",
        "candidate_id": plan.candidate_id,
        "candidate_parameter_sha256": plan.candidate_parameter_sha256,
        "frozen_at": plan.frozen_at.isoformat(),
        "plan_sha256": phase20d_qualification_plan_sha256(),
        "baseline_policy_id": plan.baseline_policy_id,
        "population": {
            "fold_count": plan.fold_count,
            "minimum_decision_epochs": plan.minimum_decision_epochs,
            "minimum_candidate_outcomes": plan.minimum_candidate_outcomes,
            "minimum_selected_outcomes": plan.minimum_selected_outcomes,
            "minimum_calendar_span_days": plan.minimum_calendar_span_days,
            "minimum_distinct_trading_days": (
                plan.minimum_distinct_trading_days
            ),
            "minimum_fold_candidate_outcomes": (
                plan.minimum_fold_candidate_outcomes
            ),
            "minimum_global_lineages": plan.minimum_global_lineages,
            "minimum_outcomes_per_lineage": (
                plan.minimum_outcomes_per_lineage
            ),
            "minimum_fold_lineages": plan.minimum_fold_lineages,
            "minimum_candidate_outcome_coverage": format(
                plan.minimum_candidate_outcome_coverage,
                "f",
            ),
            "required_selected_outcome_coverage": format(
                plan.required_selected_outcome_coverage,
                "f",
            ),
            "required_baseline_selected_outcome_coverage": format(
                plan.required_baseline_selected_outcome_coverage,
                "f",
            ),
        },
        "metrics": list(plan.metrics),
        "hard_gates": list(plan.hard_gates),
        "governance": {
            "no_refit_between_folds": plan.no_refit_between_folds,
            "burned_phase19j_reuse_allowed": (
                plan.burned_phase19j_reuse_allowed
            ),
            "synthetic_evidence_allowed": plan.synthetic_evidence_allowed,
            "decision_time_provider_cost_proxy_only": (
                plan.decision_time_provider_cost_proxy_only
            ),
            "realized_execution_economics_required": (
                plan.realized_execution_economics_required
            ),
            "fresh_forward_outcomes_consumed_when_frozen": 0,
            "policy_certified": False,
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
