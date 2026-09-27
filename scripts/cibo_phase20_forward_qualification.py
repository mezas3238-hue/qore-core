"""Run the frozen Phase20D V2 qualification from durable forward books."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
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
        "schema": "qore.cibo.phase20d.v2-qualification.v4",
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
            "policy_settlement_cash_drawdown_usd": format(
                report.policy_settlement_cash_drawdown_usd,
                "f",
            ),
            "baseline_settlement_cash_drawdown_usd": format(
                report.baseline_settlement_cash_drawdown_usd,
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
                "realized_net_pnl_usd": (
                    None
                    if item.realized_net_pnl_usd is None
                    else format(item.realized_net_pnl_usd, "f")
                ),
                "executed_initial_stop_risk_usd": (
                    None
                    if item.executed_initial_stop_risk_usd is None
                    else format(
                        item.executed_initial_stop_risk_usd,
                        "f",
                    )
                ),
                "realized_structural_outcome_r": (
                    None
                    if item.realized_structural_outcome_r is None
                    else format(
                        item.realized_structural_outcome_r,
                        "f",
                    )
                ),
                "capital_minutes": (
                    None
                    if item.capital_minutes is None
                    else format(item.capital_minutes, "f")
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
            "realized_execution_economics_required": True,
            "provider_cost_proxy_subtracted_after_settlement": False,
            "drawdown_metric_is_terminal_settlement_cash_path": True,
            "drawdown_metric_is_mark_to_market_equity_mdd": False,
            "capital_productivity_uses_realized_risk_minutes": True,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _resolve_git_sha(explicit: str | None) -> str:
    value = explicit or os.getenv("GITHUB_SHA")
    if value is None:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
        ).strip()
    normalized = value.strip().lower()
    if _GIT_SHA_RE.fullmatch(normalized) is None:
        raise ValueError("qualification git SHA must be 40 lowercase hex")
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-store", type=Path, required=True)
    parser.add_argument("--policy-store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--git-sha")
    args = parser.parse_args()

    git_sha = _resolve_git_sha(args.git_sha)
    evidence_store_sha256 = _sha256_path(args.evidence_store)
    policy_store_sha256 = _sha256_path(args.policy_store)
    evidence = DurablePhase20ForwardEvidenceStore(
        args.evidence_store
    ).load()
    policy = DurablePhase20ForwardPolicyStore(args.policy_store).load()
    report = run_phase20d_v2_qualification(
        evidence_book=evidence,
        policy_book=policy,
    )
    payload = _report_json(report)
    collector_git_shas: set[str] = set()
    missing_collector_git_sha = 0
    for decision in evidence.decisions:
        if decision.collector_git_sha is None:
            missing_collector_git_sha += 1
        else:
            collector_git_shas.add(decision.collector_git_sha)
    payload["provenance"] = {
        "git_sha": git_sha,
        "evidence_store_sha256": evidence_store_sha256,
        "policy_store_sha256": policy_store_sha256,
        "evidence_generation": evidence.generation,
        "policy_generation": policy.generation,
        "decision_count": len(evidence.decisions),
        "outcome_count": len(evidence.outcomes),
        "policy_decision_count": len(policy.decisions),
        "collector_git_shas": sorted(collector_git_shas),
        "missing_collector_git_sha_decisions": missing_collector_git_sha,
    }
    certification_blockers: list[str] = []
    if report.status.value != "PASS":
        certification_blockers.append("QUALIFICATION_NOT_PASS")
    if report.failures:
        certification_blockers.append("QUALIFICATION_HAS_FAILURES")
    if not report.readiness.ready:
        certification_blockers.append("FORWARD_READINESS_INCOMPLETE")
    if missing_collector_git_sha:
        certification_blockers.append("COLLECTOR_GIT_LINEAGE_INCOMPLETE")
    if len(collector_git_shas) != 1:
        certification_blockers.append("COLLECTOR_GIT_LINEAGE_NOT_SINGLE_SHA")
    payload["final_certification"] = {
        "status": (
            "CIBO_CERTIFIED"
            if not certification_blockers
            else "PENDING"
        ),
        "eligible": not certification_blockers,
        "blockers": certification_blockers,
        "requires_exact_evidence_and_policy_digests": True,
        "requires_single_collector_git_sha": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
