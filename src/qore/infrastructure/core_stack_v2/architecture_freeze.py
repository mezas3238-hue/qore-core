"""Frozen architecture contract for QORE CORE STACK V2 SUPERINTELLIGENCE."""
from __future__ import annotations

import hashlib
import json
from typing import Final

SUPERINTELLIGENCE_FREEZE_VERSION: Final = "QORE_CORE_STACK_V2_SUPERINTELLIGENCE_001"

_CAPABILITIES: Final = (
    "PERCEPTION_INTEGRITY",
    "HISTORICAL_CAUSAL_MARKET_MEMORY",
    "DEEP_MARKET_WORLD_MODEL",
    "REGIME_AND_TRANSITION_INTELLIGENCE",
    "ATTENTION_AND_CHANGE_DETECTION",
    "HYPOTHESIS_ENSEMBLE",
    "UNCERTAINTY_AND_METACOGNITION",
    "GLOBAL_CROSS_MARKET_INTELLIGENCE",
    "OPPORTUNITY_SUITABILITY_BY_TRADER",
    "FAILURE_AND_COUNTERFACTUAL_MEMORY",
    "POSITION_JOURNEY_AND_ECONOMIC_ATTRIBUTION",
)

_MARKET_UNIVERSE_SOURCES: Final = (
    "ExecutiveMarketsReadModel",
    "InstrumentUniverseRegistrySnapshot",
)

_AUTHORITY_CHAIN: Final = (
    "MARKET_AND_CIBO",
    "SHARED_CORE_V2",
    "COGNITIVE_ADAPTER",
    "TRADER_COGNITION",
    "TRADER_METHODOLOGY",
    "QORE_RISK",
    "EXECUTION",
)


def superintelligence_freeze_contract() -> dict[str, object]:
    """Return the Owner-approved immutable architecture direction."""
    return {
        "schema": "qore.core_stack_v2.superintelligence_freeze.v1",
        "freeze_version": SUPERINTELLIGENCE_FREEZE_VERSION,
        "objective": (
            "shared causal market intelligence that materially improves specialist "
            "trader quality without owning specialist methodology"
        ),
        "authority_chain": _AUTHORITY_CHAIN,
        "capabilities": _CAPABILITIES,
        "global_market_universe": {
            "required": True,
            "dynamic_not_hardcoded": True,
            "sources": _MARKET_UNIVERSE_SOURCES,
            "retain_restricted_markets_as_context": True,
            "retain_unavailable_markets_as_context": True,
            "future_market_additions_require_core_rewrite": False,
            "market_knowledge_implies_trade_authority": False,
        },
        "memory_law": {
            "shared_facts_separate_interpretation": True,
            "historical_closed_episodes_allowed": True,
            "current_episode_future_outcome_forbidden": True,
            "runtime_self_training_from_current_pnl_forbidden": True,
        },
        "specialist_sovereignty": {
            "adapter_contextualizes_only": True,
            "shared_core_may_rewrite_setup": False,
            "shared_core_may_rewrite_entry": False,
            "shared_core_may_rewrite_stop": False,
            "shared_core_may_rewrite_target": False,
            "shared_core_may_authorize_order": False,
            "shared_core_may_authorize_risk": False,
            "qore_risk_sovereign": True,
            "execution_single_authority": True,
        },
        "position_law": {
            "stop_can_improve_or_hold": True,
            "stop_can_widen": False,
            "future_information_allowed": False,
        },
        "shared_essential_intelligence": {
            "profit_factor": {
                "required": True,
                "meaning": (
                    "Shared must improve opportunity selection and journey quality "
                    "enough to create materially higher Profit Factor."
                ),
                "cannot_be_achieved_by_risk_weighting_only": True,
            },
            "drawdown": {
                "required": True,
                "meaning": (
                    "Shared must identify bad situations, deterioration, anomaly "
                    "and failed continuation/reversal early enough to reduce DD."
                ),
                "stop_may_improve_or_hold_only": True,
                "stop_widening_forbidden": True,
            },
            "adaptive_journey": {
                "required": True,
                "extend_target_when_market_capacity_supports_it": True,
                "hold_original_target_when_extension_is_unproven": True,
                "defend_or_reduce_loss_when_market_deteriorates": True,
                "decision_must_be_causal_as_of_each_observation": True,
                "future_path_or_terminal_outcome_forbidden": True,
                "shared_has_no_execution_authority": True,
            },
            "market_situation_dimensions": (
                "anomaly",
                "volatility",
                "trend",
                "range",
                "regime",
                "regime_transition",
                "liquidity",
                "structure",
                "displacement",
                "compression",
                "expansion",
                "exhaustion",
                "cross_market_confirmation",
                "cross_market_divergence",
                "historical_analogs",
                "failure_patterns",
                "uncertainty",
            ),
            "success_requires_all_three": True,
        },
        "shared_research_sequence": {
            "phase_a_shared_intelligence": {
                "status": "ACTIVE_PRIMARY_RESEARCH",
                "scope": "DECISION_PLUS_POSITION_JOURNEY_INTELLIGENCE",
                "capital_potentiation_forbidden_in_phase": True,
                "risk_weighting_forbidden_in_phase": True,
                "journey_intelligence_required_in_phase": True,
                "target_extension_intelligence_required_in_phase": True,
                "loss_defense_intelligence_required_in_phase": True,
                "must_be_formally_accepted_before_phase_b": True,
                "formal_acceptance_requires_temporal_falsification_pass": True,
                "formal_acceptance_requires_material_pf_uplift": True,
                "formal_acceptance_requires_material_dd_reduction": True,
                "formal_acceptance_requires_loss_rejection_quality": True,
                "formal_acceptance_requires_winner_preservation": True,
                "formal_acceptance_requires_density_preservation": True,
                "formal_acceptance_requires_target_extension_quality": True,
                "formal_acceptance_requires_loss_defense_quality": True,
            },
            "phase_b_capital_potentiation": {
                "status": "DEFERRED_BLOCKED",
                "blocked_until_phase_a_formally_accepted": True,
                "shared_intelligence_model_must_be_frozen_first": True,
                "may_not_influence_phase_a_selection": True,
                "capital_or_risk_weighting_belongs_here": True,
            },
        },
        "shared_dual_mission": {
            "mission_1_decision_support": {
                "purpose": (
                    "improve the original trader methodology decision quality "
                    "without rewriting the methodology"
                ),
                "decision_must_precede_entry": True,
                "methodology_rules_unchanged": True,
                "profit_factor_must_increase": True,
                "observed_drawdown_must_decrease": True,
                "protect_winner_retention": True,
                "measure_losses_avoided": True,
                "measure_winners_sacrificed": True,
                "measure_density_retained": True,
            },
            "mission_2_trade_potentiation": {
                "purpose": (
                    "increase the economic quality of trades the trader actually "
                    "takes, reproducing the beneficial economic role of legacy "
                    "Core Stack without owning execution or risk authority"
                ),
                "trader_trade_identity_preserved": True,
                "shared_order_authority": False,
                "shared_risk_authority": False,
                "qore_risk_remains_sovereign": True,
                "profit_factor_must_increase": True,
                "observed_drawdown_may_increase": False,
                "measure_position_journey_uplift": True,
                "measure_capital_efficiency_uplift": True,
                "measure_pf_before_and_after_weighting": True,
            },
            "success_requires_both_missions": True,
        },
        "vt31_benchmark": {
            "owner_raw_methodology": {
                "role": "PRIMARY_FALSIFICATION_BASELINE",
                "core_stack_assistance": False,
                "shared_core_assistance": False,
                "owner_stated_profit_factor": "<1",
                "exact_identity_must_be_recovered_before_numeric_claim": True,
                "shared_must_create_material_positive_edge": True,
            },
            "source_only_r22_formalization": {
                "role": "SECONDARY_UNASSISTED_FORMALIZATION_CONTROL",
                "identity": "ttrades-am-silver-bullet-nq-r2.2",
                "core_stack_assistance": False,
                "shared_core_assistance": False,
                "trade_count_5y": 822,
                "profit_factor_5y": "1.227987023050540462303028923",
                "total_r_5y": "144.2131914306193694297809449",
                "observed_dd_r_5y": "54.78233819598703031487108534",
                "max_losing_streak_5y": 27,
                "evidence_run_id": 35979485763,
                "artifact_id": 10799064861,
                "not_equivalent_to_owner_raw_methodology": True,
            },
            "legacy_core_stack_certified": {
                "role": "SECONDARY_ASSISTED_CEILING",
                "candidate": "VT31_NAS100_STRUCTURAL_TARGET_V1",
                "core_stack_assistance": True,
                "profit_factor_5y": "3.736184576983536",
                "total_r_5y": "68.4017921123",
                "observed_dd_r_5y": "3.7089849073",
                "trade_count_5y": 806,
                "winner_count_5y": 241,
                "certification_loser_count_5y": 565,
                "owner_observed_loser_count": 546,
                "loser_count_requires_reconciliation": True,
                "win_rate_5y_from_certification": "0.2990074441687344913151364764",
                "weighted_pf_uses_capital_weighted_net_r": True,
                "weighted_pf_is_not_signal_quality_pf": True,
                "signal_quality_must_be_measured_unweighted": True,
                "loss_count_imbalance_is_diagnostic_not_pf_proof": True,
            },
            "parity_is_only_safety_gate": True,
            "economic_objective_is_material_uplift": True,
            "shared_success_order": (
                "beat-owner-raw-methodology",
                "beat-source-only-r22-control",
                "challenge-legacy-core-stack-certified",
            ),
            "evaluate_pf": True,
            "evaluate_total_r": True,
            "evaluate_mean_r": True,
            "evaluate_observed_dd": True,
            "evaluate_losing_streak": True,
            "evaluate_mc_dd": True,
            "evaluate_temporal_stability": True,
            "evaluate_wait_abstain_quality": True,
            "evaluate_losses_avoided_vs_winners_sacrificed": True,
            "no_future_features": True,
            "no_calendar_or_fold_identity_edge": True,
        },
        "operational_falsification": {
            "required": True,
            "same_realized_market_path_required": True,
            "same_opportunity_universe_required": True,
            "shared_decision_must_precede_outcome": True,
            "shared_shadow_decision_must_be_immutable": True,
            "actual_costs_and_slippage_preferred": True,
            "compare_against_real_vt31_operations": True,
            "poor_real_vt31_period_is_primary_challenge_set": True,
            "shared_must_materially_outperform_on_poor_period": True,
            "shared_failure_to_improve_materially_is_falsification": True,
            "hindsight_reclassification_forbidden": True,
            "post_trade_label_as_runtime_input_forbidden": True,
            "minimum_required_outputs": (
                "profit_factor",
                "total_r",
                "mean_r",
                "observed_drawdown_r",
                "max_losing_streak",
                "monte_carlo_drawdown",
                "density_retained",
                "losses_avoided",
                "winners_sacrificed",
            ),
        },
        "governance": {
            "research_authorized": True,
            "shadow_first": True,
            "vt08_forex_integration": False,
            "vt08_forex_excluded": True,
            "capitalizer_deferred_until_frozen": True,
            "live_deployment_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def superintelligence_freeze_fingerprint() -> str:
    raw = json.dumps(
        superintelligence_freeze_contract(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()
