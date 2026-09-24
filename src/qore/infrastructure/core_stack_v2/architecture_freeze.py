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
        "vt31_benchmark": {
            "baseline_candidate": "VT31_NAS100_STRUCTURAL_TARGET_V1",
            "baseline_pf": "3.736184576983536",
            "baseline_total_r": "68.4017921123",
            "baseline_observed_dd_r": "3.7089849073",
            "baseline_trade_count_5y": 806,
            "parity_is_only_safety_gate": True,
            "economic_objective_is_material_uplift": True,
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
