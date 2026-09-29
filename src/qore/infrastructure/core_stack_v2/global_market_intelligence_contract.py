"""Owner-frozen global market intelligence extension for Shared Brain."""

from __future__ import annotations

from typing import Final

from qore.infrastructure.core_stack_v2.global_market_relational_graph import (
    GlobalRelationHorizon,
    GlobalRelationKind,
    GlobalRelationState,
)
from qore.infrastructure.core_stack_v2.global_sensor_registry import (
    GLOBAL_SENSOR_GOVERNANCE_PIPELINE,
)
from qore.infrastructure.core_stack_v2.global_temporal_comparability import (
    MarketSessionState,
    ProviderObservabilityState,
    RelationalComparabilityState,
)

GLOBAL_MARKET_INTELLIGENCE_VERSION: Final = (
    "QORE_GLOBAL_MARKET_RELATIONAL_INTELLIGENCE_001"
)

_GLOBAL_GENERATIONS: Final = (
    "GEN_0_GOVERNANCE_AND_GLOBAL_CENSUS",
    "GEN_1_GLOBAL_SENSOR_FABRIC",
    "GEN_2_TEMPORAL_SYNCHRONIZATION_AND_MARKET_HOURS_CAUSALITY",
    "GEN_3_RELATION_OBSERVATORY",
    "GEN_4_GENERALIZED_STRUCTURAL_DIVERGENCE",
    "GEN_5_LEAD_LAG_AND_INFORMATION_FLOW",
    "GEN_6_RELATIONSHIP_LIFECYCLE_AND_DYNAMIC_GRAPH",
    "GEN_7_DYNAMIC_TAXONOMY_AND_CROSS_WORLD_FEDERATION",
    "GEN_8_ACTIVE_PERCEPTION_AND_COGNITIVE_ATTENTION",
    "GEN_9_CROSS_MARKET_FOUNDATION_MODEL",
    "GEN_10_AUTONOMOUS_RELATION_AND_UNKNOWN_UNKNOWN_DISCOVERY",
)


def global_market_intelligence_contract() -> dict[str, object]:
    """Return the additive Owner law for global Shared perception."""

    return {
        "version": GLOBAL_MARKET_INTELLIGENCE_VERSION,
        "owner_directive": (
            "docs/shared/QORE_SHARED_GLOBAL_PERCEPTION_OWNER_DIRECTIVE_006.md"
        ),
        "observation_universe_law": {
            "shared_observation_universe_must_exceed_execution_universe": True,
            "current_trader_universe_must_not_define_shared_knowledge_ceiling": True,
            "markets_without_qore_traders_may_be_observed": True,
            "observing_market_grants_trading_authority": False,
            "provider_symbol_discovery_equals_productive_admission": False,
        },
        "global_graph_law": {
            "qore_global_market_relational_graph_required": True,
            "relation_kinds": tuple(item.value for item in GlobalRelationKind),
            "relation_states": tuple(item.value for item in GlobalRelationState),
            "horizons": tuple(item.value for item in GlobalRelationHorizon),
            "historical_relationship_is_current_relationship": False,
            "correlation_is_causation": False,
            "edge_uncertainty_required": True,
            "edge_provenance_required": True,
            "edge_freshness_required": True,
            "relationship_break_is_information": True,
        },
        "generalized_smt_law": {
            "cross_market_structural_divergence_required": True,
            "fixed_pair_ceiling_forbidden": True,
            "manual_pairs_may_seed_hypotheses_only": True,
            "automatic_relation_discovery_required": True,
        },
        "sensor_governance": {
            "pipeline": tuple(
                stage.value for stage in GLOBAL_SENSOR_GOVERNANCE_PIPELINE
            ),
            "provider_availability_is_not_admission": True,
            "failed_hypothesis_does_not_imply_useless_sensor": True,
            "observe_only_is_legal": True,
        },
        "market_hours_and_causality": {
            "market_hours_required": True,
            "session_and_holiday_state_required": True,
            "quote_staleness_required": True,
            "provider_delay_required": True,
            "asynchronous_market_alignment_required": True,
            "false_divergence_from_closed_market_forbidden": True,
        },
        "gen_2_temporal_comparability_law": {
            "time_integrity_before_relational_intelligence": True,
            "no_relational_claim_without_relational_comparability": True,
            "market_time_distinct": True,
            "venue_time_distinct": True,
            "provider_event_time_distinct": True,
            "receipt_time_distinct": True,
            "observation_time_distinct": True,
            "processing_time_distinct": True,
            "decision_time_distinct": True,
            "provider_event_before_receipt_required": True,
            "receipt_before_processing_required": True,
            "future_pairing_forbidden": True,
            "post_hoc_alignment_forbidden": True,
            "canonical_market_session_separate_from_provider_availability": True,
            "session_states": tuple(item.value for item in MarketSessionState),
            "provider_states": tuple(
                item.value for item in ProviderObservabilityState
            ),
            "comparability_states": tuple(
                item.value for item in RelationalComparabilityState
            ),
            "unknown_calendar_must_abstain": True,
            "closed_or_halted_peer_cannot_create_divergence_claim": True,
            "provider_degradation_is_not_market_behavior": True,
            "global_observability_matrix_required": True,
            "expected_update_cadence_is_instrument_provider_session_specific": True,
            "single_global_staleness_threshold_forbidden": True,
        },
        "statistical_governance": {
            "multiple_testing_control_required": True,
            "data_snooping_control_required": True,
            "selection_bias_control_required": True,
            "lookahead_forbidden": True,
            "regime_overfit_control_required": True,
            "unstable_relation_detection_required": True,
            "provider_artifact_control_required": True,
        },
        "active_perception_law": {
            "dynamic_market_selection_required": True,
            "dynamic_relation_selection_required": True,
            "dynamic_horizon_selection_required": True,
            "redundancy_awareness_required": True,
            "expected_uncertainty_reduction_required": True,
            "computation_cost_awareness_required": True,
        },
        "foundation_model_law": {
            "cross_market_training_universe_required": True,
            "trader_market_only_training_ceiling_forbidden": True,
            "market_knowledge_separate_from_trader_methodology": True,
        },
        "scalability_law": {
            "configuration_driven": True,
            "schema_driven": True,
            "adapter_based": True,
            "market_agnostic_where_valid": True,
            "provider_aware": True,
            "one_bespoke_implementation_per_market_forbidden": True,
        },
        "computation_law": {
            "deep_global_cognition_separate_from_low_latency_support": True,
            "offline_science_allowed": True,
            "nearline_graph_updates_allowed": True,
            "runtime_consumes_causal_precomputed_state": True,
            "global_perception_may_not_raise_runtime_sla": True,
        },
        "generations": _GLOBAL_GENERATIONS,
        "sovereignty": {
            "shared_trading_authority": False,
            "shared_execution_authority": False,
            "shared_risk_authority": False,
            "shared_sizing_authority": False,
            "shared_capital_authority": False,
            "shared_strategy_mutation_authority": False,
        },
    }
