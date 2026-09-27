"""Run the frozen Phase20D V2 qualification from durable forward books."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationReport,
    run_phase20d_v2_qualification,
)


def _report_json(report: Phase20QualificationReport) -> dict[str, Any]:
    return {
        "schema": "qore.cibo.phase20d.v2-qualification.v1",
        "status": report.status.value,
        "plan_id": report.plan_id,
        "plan_sha256": report.plan_sha256,
        "candidate_id": report.candidate_id,
        "failures_or_pending_reasons": list(report.failures),
        "readiness": {
            "ready": report.readiness.ready,
            "reasons": list(report.readiness.reasons),
            "decision_epochs": report.readiness.decision_epochs,
            "candidate_instances": report.readiness.candidate_instances,
            "candidate_outcomes": report.readiness.candidate_outcomes,
            "selected_instances": report.readiness.selected_instances,
            "selected_outcomes": report.readiness.selected_outcomes,
            "candidate_outcome_coverage": format(
                report.readiness.candidate_outcome_coverage,
                "f",
            ),
            "selected_outcome_coverage": format(
                report.readiness.selected_outcome_coverage,
                "f",
            ),
            "calendar_span_days": report.readiness.calendar_span_days,
            "distinct_trading_days": report.readiness.distinct_trading_days,
            "represented_lineages": report.readiness.represented_lineages,
            "minimum_outcomes_any_lineage": (
                report.readiness.minimum_outcomes_any_lineage
            ),
            "minimum_fold_candidate_outcomes": (
                report.readiness.minimum_fold_candidate_outcomes
            ),
            "minimum_fold_lineages": (
                report.readiness.minimum_fold_lineages
            ),
            "missing_policy_decisions": (
                report.readiness.missing_policy_decisions
            ),
        },
        "economics": {
            "policy_net_delta_usd": format(
                report.policy_net_delta_usd,
                "f",
            ),
            "baseline_net_delta_usd": format(
                report.baseline_net_delta_usd,
                "f",
            ),
            "policy_max_drawdown_usd": format(
                report.policy_max_drawdown_usd,
                "f",
            ),
            "baseline_max_drawdown_usd": format(
                report.baseline_max_drawdown_usd,
                "f",
            ),
            "policy_capital_productivity": format(
                report.policy_capital_productivity,
                "f",
            ),
            "baseline_capital_productivity": format(
                report.baseline_capital_productivity,
                "f",
            ),
            "policy_acceptance_rate": format(
                report.policy_acceptance_rate,
                "f",
            ),
            "baseline_acceptance_rate": format(
                report.baseline_acceptance_rate,
                "f",
            ),
            "policy_selected_outcome_coverage": format(
                report.policy_selected_outcome_coverage,
                "f",
            ),
            "baseline_selected_outcome_coverage": format(
                report.baseline_selected_outcome_coverage,
                "f",
            ),
            "candidate_outcome_coverage": format(
                report.candidate_outcome_coverage,
                "f",
            ),
            "capital_utilization": format(
                report.capital_utilization,
                "f",
            ),
            "capital_starvation_rate": format(
                report.capital_starvation_rate,
                "f",
            ),
            "mpc_reserve_efficiency": format(
                report.mpc_reserve_efficiency,
                "f",
            ),
            "optionality_preserved_rate": format(
                report.optionality_preserved_rate,
                "f",
            ),
            "concentration_utilization": format(
                report.concentration_utilization,
                "f",
            ),
            "provider_failure_incidence": format(
                report.provider_failure_incidence,
                "f",
            ),
            "evidence_missingness": format(
                report.evidence_missingness,
                "f",
            ),
        },
        "folds": [
            {
                "fold_id": item.fold_id,
                "decision_epoch_count": item.decision_epoch_count,
                "candidate_count": item.candidate_count,
                "policy_selected_count": item.policy_selected_count,
                "baseline_selected_count": item.baseline_selected_count,
                "policy_net_delta_usd": format(
                    item.policy_net_delta_usd,
                    "f",
                ),
                "baseline_net_delta_usd": format(
                    item.baseline_net_delta_usd,
                    "f",
                ),
            }
            for item in report.folds
        ],
        "dataset": [
            {
                "decision_epoch_id": item.decision_epoch_id,
                "decision_evidence_sha256": item.decision_evidence_sha256,
                "decision_at": item.decision_at.isoformat(),
                "signal_fingerprint": item.signal_fingerprint,
                "trader_id": item.trader_id,
                "stop_risk_usd": format(item.stop_risk_usd, "f"),
                "margin_usd": format(item.margin_usd, "f"),
                "concentration_group": item.concentration_group,
                "concentration_risk_usd": format(
                    item.concentration_risk_usd,
                    "f",
                ),
                "expected_capital_minutes": format(
                    item.expected_capital_minutes,
                    "f",
                ),
                "provider_cost_proxy_usd": format(
                    item.provider_cost_proxy_usd,
                    "f",
                ),
                "policy_selected": item.policy_selected,
                "baseline_selected": item.baseline_selected,
                "realized_structural_outcome_r": (
                    None
                    if item.realized_structural_outcome_r is None
                    else format(
                        item.realized_structural_outcome_r,
                        "f",
                    )
                ),
                "outcome_observed_at": (
                    None
                    if item.outcome_observed_at is None
                    else item.outcome_observed_at.isoformat()
                ),
            }
            for item in report.rows
        ],
        "governance": {
            "no_refit_between_folds": True,
            "phase19j_burned_validation_reused": False,
            "decision_time_provider_cost_proxy_only": True,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-store", type=Path, required=True)
    parser.add_argument("--policy-store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence = DurablePhase20ForwardEvidenceStore(
        args.evidence_store
    ).load()
    policy = DurablePhase20ForwardPolicyStore(args.policy_store).load()
    report = run_phase20d_v2_qualification(
        evidence_book=evidence,
        policy_book=policy,
    )
    payload = _report_json(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
