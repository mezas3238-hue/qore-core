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

from qore.infrastructure.cibo_ce2i_phase20_causal_tool_readiness import (
    assess_phase20_causal_tool_readiness,
)
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
from qore.infrastructure.cibo_ce2i_phase20_t14_path_readiness import (
    assess_phase20_t14_path_readiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t15_option_realization import (
    assess_phase20_t15_option_realization,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    CTraderDemoLiveBehaviorLedger,
)


def _report_json(report: Phase20QualificationReport) -> dict[str, Any]:
    return {
        "schema": "qore.cibo.phase20d.v2-qualification.v5",
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
            "pre_freeze_decisions": (
                report.readiness.pre_freeze_decisions
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
    parser.add_argument("--behavior-ledger", type=Path)
    parser.add_argument("--executed-risk-store", type=Path)
    parser.add_argument("--settlement-store", type=Path)
    parser.add_argument("--t08-oos-shadow-store", type=Path)
    parser.add_argument("--t13-shadow-store", type=Path)
    parser.add_argument("--git-sha")
    args = parser.parse_args()

    git_sha = _resolve_git_sha(args.git_sha)
    evidence_store_sha256 = _sha256_path(args.evidence_store)
    policy_store_sha256 = _sha256_path(args.policy_store)
    executed_risk_store_sha256 = (
        None
        if args.executed_risk_store is None
        else _sha256_path(args.executed_risk_store)
    )
    settlement_store_sha256 = (
        None
        if args.settlement_store is None
        else _sha256_path(args.settlement_store)
    )
    t08_oos_shadow_store_sha256 = (
        None
        if args.t08_oos_shadow_store is None
        else _sha256_path(args.t08_oos_shadow_store)
    )
    t13_shadow_store_sha256 = (
        None
        if args.t13_shadow_store is None
        else _sha256_path(args.t13_shadow_store)
    )
    evidence = DurablePhase20ForwardEvidenceStore(
        args.evidence_store
    ).load()
    policy = DurablePhase20ForwardPolicyStore(args.policy_store).load()
    report = run_phase20d_v2_qualification(
        evidence_book=evidence,
        policy_book=policy,
    )
    t14_path_readiness = None
    behavior_ledger_sha256 = None
    if args.behavior_ledger is not None:
        behavior_ledger_sha256 = _sha256_path(args.behavior_ledger)
        t14_path_readiness = assess_phase20_t14_path_readiness(
            evidence_book=evidence,
            events=CTraderDemoLiveBehaviorLedger(
                args.behavior_ledger
            ).events(),
        )
    t11_execution_population = None
    t11_cost_binding = None
    t11_executed_risk_generation = None
    t11_settlement_generation = None
    if args.executed_risk_store is not None:
        from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
            DurablePhase20ExecutedRiskStore,
        )
        from qore.infrastructure.cibo_ce2i_phase20_t11_execution_population import (
            assess_phase20_t11_execution_population,
        )

        executed_risk_book = DurablePhase20ExecutedRiskStore(
            args.executed_risk_store
        ).load()
        t11_executed_risk_generation = executed_risk_book.generation
        t11_execution_population = assess_phase20_t11_execution_population(
            evidence_book=evidence,
            executed_risk_book=executed_risk_book,
        )
        if args.settlement_store is not None:
            from qore.infrastructure.cibo_ce2i_phase20_t11_cost_binding import (
                assess_phase20_t11_cost_binding,
            )
            from qore.infrastructure.cibo_cma_settlement_store import (
                DurableCmaSettlementStore,
            )

            settlement_book = DurableCmaSettlementStore(
                args.settlement_store
            ).load()
            t11_settlement_generation = settlement_book.generation
            t11_cost_binding = assess_phase20_t11_cost_binding(
                evidence_book=evidence,
                executed_risk_book=executed_risk_book,
                settlement_book=settlement_book,
            )

    t08_oos_ablation = None
    t08_oos_shadow_generation = None
    t08_oos_complete_epochs = 0
    if args.t08_oos_shadow_store is not None:
        from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
            assess_t08_fresh_oos_netting_ablation,
        )
        from qore.infrastructure.cibo_ce2i_phase20_t08_oos_store import (
            DurableT08OosShadowStore,
        )

        t08_oos_book = DurableT08OosShadowStore(
            args.t08_oos_shadow_store
        ).load()
        t08_oos_epochs = t08_oos_book.complete_epochs()
        t08_oos_shadow_generation = t08_oos_book.generation
        t08_oos_complete_epochs = len(t08_oos_epochs)
        t08_oos_ablation = assess_t08_fresh_oos_netting_ablation(
            t08_oos_epochs
        )

    from qore.infrastructure.cibo_ce2i_phase20_t13_reserve_population import (
        assess_phase20_t13_reserve_population,
    )
    from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
        assess_phase20_t13_shadow_policy,
    )

    t13_reserve_population = assess_phase20_t13_reserve_population(
        evidence
    )
    t13_shadow_policy = assess_phase20_t13_shadow_policy(evidence)
    t13_shadow_book = None
    if args.t13_shadow_store is not None:
        from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_store import (
            DurableT13ShadowDecisionStore,
        )

        t13_shadow_book = DurableT13ShadowDecisionStore(
            args.t13_shadow_store
        ).load()
    t15_option_realization = assess_phase20_t15_option_realization(
        evidence
    )
    tool_readiness = assess_phase20_causal_tool_readiness(
        evidence_book=evidence,
        qualification_readiness=report.readiness,
        t08_oos_ablation=t08_oos_ablation,
        t13_reserve_population=t13_reserve_population,
        t14_path_readiness=t14_path_readiness,
        t15_option_realization=t15_option_realization,
    )
    payload = _report_json(report)
    payload["causal_tool_readiness"] = {
        "global_forward_ready": tool_readiness.global_forward_ready,
        "global_forward_blockers": list(
            tool_readiness.global_forward_blockers
        ),
        "decision_epochs": tool_readiness.decision_epochs,
        "usable_forward_epochs": tool_readiness.usable_forward_epochs,
        "candidate_epochs": tool_readiness.candidate_epochs,
        "exact_competition_epochs": (
            tool_readiness.exact_competition_epochs
        ),
        "scarce_competition_epochs": (
            tool_readiness.scarce_competition_epochs
        ),
        "valid_regime_epochs": tool_readiness.valid_regime_epochs,
        "portfolio_netting_epochs": (
            tool_readiness.portfolio_netting_epochs
        ),
        "known_option_epochs": tool_readiness.known_option_epochs,
        "causal_history_epochs": tool_readiness.causal_history_epochs,
        "t08_oos_ablation": (
            None
            if t08_oos_ablation is None
            else {
                "sample_size": t08_oos_ablation.sample_size,
                "minimum_epochs": t08_oos_ablation.minimum_epochs,
                "required_folds": t08_oos_ablation.required_folds,
                "baseline_selected_count": (
                    t08_oos_ablation.baseline_selected_count
                ),
                "treatment_selected_count": (
                    t08_oos_ablation.treatment_selected_count
                ),
                "incremental_selected_count": (
                    t08_oos_ablation.incremental_selected_count
                ),
                "baseline_total_pnl_usd": format(
                    t08_oos_ablation.baseline_total_pnl_usd,
                    "f",
                ),
                "treatment_total_pnl_usd": format(
                    t08_oos_ablation.treatment_total_pnl_usd,
                    "f",
                ),
                "baseline_max_drawdown_usd": format(
                    t08_oos_ablation.baseline_max_drawdown_usd,
                    "f",
                ),
                "treatment_max_drawdown_usd": format(
                    t08_oos_ablation.treatment_max_drawdown_usd,
                    "f",
                ),
                "mapping_evidence_bound": (
                    t08_oos_ablation.mapping_evidence_bound
                ),
                "correlation_evidence_bound": (
                    t08_oos_ablation.correlation_evidence_bound
                ),
                "pathwise_authorization_respected": (
                    t08_oos_ablation.pathwise_authorization_respected
                ),
                "fresh_oos_utility_demonstrated": (
                    t08_oos_ablation.fresh_oos_utility_demonstrated
                ),
                "risk_mapping_verified": (
                    t08_oos_ablation.risk_mapping_verified
                ),
                "correlation_state_verified": (
                    t08_oos_ablation.correlation_state_verified
                ),
                "netting_credit_authorized": (
                    t08_oos_ablation.netting_credit_authorized
                ),
                "blockers": list(t08_oos_ablation.blockers),
            }
        ),
        "t15_option_realization": {
            "stream_bound": t15_option_realization.stream_bound,
            "known_option_instances": (
                t15_option_realization.known_option_instances
            ),
            "signal_bound_option_instances": (
                t15_option_realization.signal_bound_option_instances
            ),
            "matured_option_instances": (
                t15_option_realization.matured_option_instances
            ),
            "materialized_candidate_instances": (
                t15_option_realization.materialized_candidate_instances
            ),
            "reconciled_materialized_outcomes": (
                t15_option_realization.reconciled_materialized_outcomes
            ),
            "expired_before_materialization": (
                t15_option_realization.expired_before_materialization
            ),
            "unresolved_matured_options": (
                t15_option_realization.unresolved_matured_options
            ),
            "distinct_origin_epochs": (
                t15_option_realization.distinct_origin_epochs
            ),
            "blockers": list(t15_option_realization.blockers),
        },
        "t11_execution_population": (
            None
            if t11_execution_population is None
            else {
                "eligible_execution_instances": (
                    t11_execution_population.eligible_execution_instances
                ),
                "adverse_slippage_instances": (
                    t11_execution_population.adverse_slippage_instances
                ),
                "favorable_slippage_instances": (
                    t11_execution_population.favorable_slippage_instances
                ),
                "flat_slippage_instances": (
                    t11_execution_population.flat_slippage_instances
                ),
                "latency_bound_instances": (
                    t11_execution_population.latency_bound_instances
                ),
                "represented_lineages": list(
                    t11_execution_population.represented_lineages
                ),
                "minimum_instances_per_lineage": (
                    t11_execution_population.minimum_instances_per_lineage
                ),
                "mean_signed_slippage_r": (
                    None
                    if t11_execution_population.mean_signed_slippage_r is None
                    else format(
                        t11_execution_population.mean_signed_slippage_r,
                        "f",
                    )
                ),
                "p50_signed_slippage_r": (
                    None
                    if t11_execution_population.p50_signed_slippage_r is None
                    else format(
                        t11_execution_population.p50_signed_slippage_r,
                        "f",
                    )
                ),
                "p95_signed_slippage_r": (
                    None
                    if t11_execution_population.p95_signed_slippage_r is None
                    else format(
                        t11_execution_population.p95_signed_slippage_r,
                        "f",
                    )
                ),
                "mean_decision_to_deployment_ms": (
                    None
                    if (
                        t11_execution_population
                        .mean_decision_to_deployment_ms
                        is None
                    )
                    else format(
                        t11_execution_population
                        .mean_decision_to_deployment_ms,
                        "f",
                    )
                ),
                "p95_decision_to_deployment_ms": (
                    None
                    if (
                        t11_execution_population
                        .p95_decision_to_deployment_ms
                        is None
                    )
                    else format(
                        t11_execution_population
                        .p95_decision_to_deployment_ms,
                        "f",
                    )
                ),
                "minimum_required_executions": (
                    t11_execution_population.minimum_required_executions
                ),
                "minimum_required_lineages": (
                    t11_execution_population.minimum_required_lineages
                ),
                "minimum_required_per_lineage": (
                    t11_execution_population.minimum_required_per_lineage
                ),
                "empirical_execution_population_ready": (
                    t11_execution_population
                    .empirical_execution_population_ready
                ),
                "slippage_empirically_calibrated": (
                    t11_execution_population.slippage_empirically_calibrated
                ),
                "execution_model_ready": (
                    t11_execution_population.execution_model_ready
                ),
                "blockers": list(t11_execution_population.blockers),
            }
        ),
        "t11_cost_binding": (
            None
            if t11_cost_binding is None
            else {
                "execution_instances": t11_cost_binding.execution_instances,
                "provider_spread_bound_instances": (
                    t11_cost_binding.provider_spread_bound_instances
                ),
                "settlement_bound_instances": (
                    t11_cost_binding.settlement_bound_instances
                ),
                "realized_entry_commission_instances": (
                    t11_cost_binding.realized_entry_commission_instances
                ),
                "terminal_settlement_instances": (
                    t11_cost_binding.terminal_settlement_instances
                ),
                "unbound_execution_instances": (
                    t11_cost_binding.unbound_execution_instances
                ),
                "total_predecision_quoted_spread_usd": format(
                    t11_cost_binding.total_predecision_quoted_spread_usd,
                    "f",
                ),
                "mean_predecision_quoted_spread_usd": (
                    None
                    if t11_cost_binding.mean_predecision_quoted_spread_usd
                    is None
                    else format(
                        t11_cost_binding.mean_predecision_quoted_spread_usd,
                        "f",
                    )
                ),
                "total_realized_entry_commission_usd": format(
                    t11_cost_binding.total_realized_entry_commission_usd,
                    "f",
                ),
                "mean_realized_entry_commission_usd": (
                    None
                    if t11_cost_binding.mean_realized_entry_commission_usd
                    is None
                    else format(
                        t11_cost_binding.mean_realized_entry_commission_usd,
                        "f",
                    )
                ),
                "quoted_spread_coverage_complete": (
                    t11_cost_binding.quoted_spread_coverage_complete
                ),
                "realized_entry_commission_coverage_complete": (
                    t11_cost_binding.realized_entry_commission_coverage_complete
                ),
                "realized_spread_component_identified": (
                    t11_cost_binding.realized_spread_component_identified
                ),
                "historical_2017_execution_terms_proven": (
                    t11_cost_binding.historical_2017_execution_terms_proven
                ),
                "execution_cost_model_ready": (
                    t11_cost_binding.execution_cost_model_ready
                ),
                "blockers": list(t11_cost_binding.blockers),
            }
        ),
        "t13_reserve_population": {
            "usable_decision_epochs": (
                t13_reserve_population.usable_decision_epochs
            ),
            "candidate_epochs": t13_reserve_population.candidate_epochs,
            "candidate_instances": (
                t13_reserve_population.candidate_instances
            ),
            "settled_history_epochs": (
                t13_reserve_population.settled_history_epochs
            ),
            "loss_cluster_epochs": (
                t13_reserve_population.loss_cluster_epochs
            ),
            "settlement_drawdown_epochs": (
                t13_reserve_population.settlement_drawdown_epochs
            ),
            "reserve_pressure_epochs": (
                t13_reserve_population.reserve_pressure_epochs
            ),
            "scarce_risk_headroom_epochs": (
                t13_reserve_population.scarce_risk_headroom_epochs
            ),
            "pressure_and_scarcity_epochs": (
                t13_reserve_population.pressure_and_scarcity_epochs
            ),
            "maximum_loss_cluster": (
                t13_reserve_population.maximum_loss_cluster
            ),
            "maximum_settlement_drawdown_usd": format(
                t13_reserve_population.maximum_settlement_drawdown_usd,
                "f",
            ),
            "minimum_decision_epochs": (
                t13_reserve_population.minimum_decision_epochs
            ),
            "decision_threshold_met": (
                t13_reserve_population.decision_threshold_met
            ),
            "reserve_policy_identified": (
                t13_reserve_population.reserve_policy_identified
            ),
            "oos_utility_demonstrated": (
                t13_reserve_population.oos_utility_demonstrated
            ),
            "blockers": list(t13_reserve_population.blockers),
        },
        "t13_shadow_ledger": (
            None
            if t13_shadow_book is None
            else {
                "generation": t13_shadow_book.generation,
                "decision_count": len(t13_shadow_book.decisions),
                "chain_sha256": t13_shadow_book.chain_sha256,
            }
        ),
        "t13_shadow_policy": {
            "policy_id": t13_shadow_policy.policy_id,
            "policy_sha256": t13_shadow_policy.policy_sha256,
            "policy_frozen_at": (
                t13_shadow_policy.policy_frozen_at.isoformat()
            ),
            "post_freeze_decision_epochs": (
                t13_shadow_policy.post_freeze_decision_epochs
            ),
            "candidate_epochs": t13_shadow_policy.candidate_epochs,
            "causal_pressure_epochs": (
                t13_shadow_policy.causal_pressure_epochs
            ),
            "arrival_evidence_epochs": (
                t13_shadow_policy.arrival_evidence_epochs
            ),
            "reserve_trigger_epochs": (
                t13_shadow_policy.reserve_trigger_epochs
            ),
            "full_seed_reserve_epochs": (
                t13_shadow_policy.full_seed_reserve_epochs
            ),
            "partial_headroom_reserve_epochs": (
                t13_shadow_policy.partial_headroom_reserve_epochs
            ),
            "total_shadow_reserved_risk_usd": format(
                t13_shadow_policy.total_shadow_reserved_risk_usd,
                "f",
            ),
            "maximum_shadow_reserved_risk_usd": format(
                t13_shadow_policy.maximum_shadow_reserved_risk_usd,
                "f",
            ),
            "shadow_policy_preregistered": (
                t13_shadow_policy.shadow_policy_preregistered
            ),
            "reserve_policy_empirically_identified": (
                t13_shadow_policy.reserve_policy_empirically_identified
            ),
            "fresh_oos_utility_demonstrated": (
                t13_shadow_policy.fresh_oos_utility_demonstrated
            ),
            "runtime_authority": t13_shadow_policy.runtime_authority,
            "blockers": list(t13_shadow_policy.blockers),
        },
        "t14_path_readiness": (
            None
            if t14_path_readiness is None
            else {
                "stream_bound": t14_path_readiness.stream_bound,
                "observed_path_samples": (
                    t14_path_readiness.observed_path_samples
                ),
                "path_positions": t14_path_readiness.path_positions,
                "longitudinal_path_positions": (
                    t14_path_readiness.longitudinal_path_positions
                ),
                "reconciled_stop_positions": (
                    t14_path_readiness.reconciled_stop_positions
                ),
                "execution_cost_bound_positions": (
                    t14_path_readiness.execution_cost_bound_positions
                ),
                "protection_change_positions": (
                    t14_path_readiness.protection_change_positions
                ),
                "volume_change_positions": (
                    t14_path_readiness.volume_change_positions
                ),
                "qualifying_intervention_positions": (
                    t14_path_readiness.qualifying_intervention_positions
                ),
                "blockers": list(t14_path_readiness.blockers),
            }
        ),
        "tools": [
            {
                "tool_code": item.tool_code,
                "state": item.state.value,
                "stream_bound": item.stream_bound,
                "forward_population_ready": (
                    item.forward_population_ready
                ),
                "observed_epochs": item.observed_epochs,
                "qualifying_epochs": item.qualifying_epochs,
                "blockers": list(item.blockers),
            }
            for item in tool_readiness.tools
        ],
        "governance": {
            "calibration_promoted_by_this_report": False,
            "oos_ready_promoted_by_this_report": False,
            "certification_ready_promoted_by_this_report": False,
            "holdout_2017h1_used": False,
        },
    }
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
        "behavior_ledger_sha256": behavior_ledger_sha256,
        "executed_risk_store_sha256": executed_risk_store_sha256,
        "settlement_store_sha256": settlement_store_sha256,
        "t11_executed_risk_generation": t11_executed_risk_generation,
        "t11_settlement_generation": t11_settlement_generation,
        "t08_oos_shadow_store_sha256": t08_oos_shadow_store_sha256,
        "t13_shadow_store_sha256": t13_shadow_store_sha256,
        "t08_oos_shadow_generation": t08_oos_shadow_generation,
        "t08_oos_complete_epochs": t08_oos_complete_epochs,
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
    payload["phase20d_gate"] = {
        "status": (
            "PASS"
            if not certification_blockers
            else "PENDING_OR_FAIL"
        ),
        "eligible_for_phase21": not certification_blockers,
        "blockers": certification_blockers,
        "requires_exact_evidence_and_policy_digests": True,
        "requires_single_collector_git_sha": True,
    }
    final_blockers = list(certification_blockers)
    final_blockers.extend(
        (
            "PHASE21_POLICY_FREEZE_REQUIRED",
            "PHASE22_SEALED_HOLDOUT_REQUIRED",
        )
    )
    payload["final_certification"] = {
        "status": "PENDING_PHASE21_PHASE22",
        "eligible": False,
        "blockers": final_blockers,
        "phase20d_eligible_for_phase21": not certification_blockers,
        "requires_phase21_policy_freeze": True,
        "requires_phase22_sealed_holdout": True,
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
