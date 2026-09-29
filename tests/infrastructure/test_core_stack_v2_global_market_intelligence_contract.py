from __future__ import annotations

from qore.infrastructure.core_stack_v2.global_market_intelligence_contract import (
    GLOBAL_MARKET_INTELLIGENCE_VERSION,
    global_market_intelligence_contract,
)


def test_global_market_intelligence_owner_law_expands_observation_not_authority() -> None:
    contract = global_market_intelligence_contract()

    assert contract["version"] == GLOBAL_MARKET_INTELLIGENCE_VERSION
    observation = contract["observation_universe_law"]
    assert observation[
        "shared_observation_universe_must_exceed_execution_universe"
    ] is True
    assert observation[
        "current_trader_universe_must_not_define_shared_knowledge_ceiling"
    ] is True
    assert observation["markets_without_qore_traders_may_be_observed"] is True
    assert observation["observing_market_grants_trading_authority"] is False

    sovereignty = contract["sovereignty"]
    assert all(value is False for value in sovereignty.values())


def test_global_graph_and_generalized_smt_are_mandatory() -> None:
    contract = global_market_intelligence_contract()

    graph = contract["global_graph_law"]
    assert graph["qore_global_market_relational_graph_required"] is True
    assert graph["correlation_is_causation"] is False
    assert graph["historical_relationship_is_current_relationship"] is False
    assert "LEAD_LAG" in graph["relation_kinds"]
    assert "RELATIONSHIP_DECAY" in graph["relation_kinds"]
    assert "DECOUPLING" in graph["relation_states"]

    smt = contract["generalized_smt_law"]
    assert smt["cross_market_structural_divergence_required"] is True
    assert smt["fixed_pair_ceiling_forbidden"] is True
    assert smt["automatic_relation_discovery_required"] is True


def test_global_sensor_and_statistics_governance_are_fail_closed() -> None:
    contract = global_market_intelligence_contract()

    sensor = contract["sensor_governance"]
    assert sensor["provider_availability_is_not_admission"] is True
    assert sensor["failed_hypothesis_does_not_imply_useless_sensor"] is True
    assert sensor["pipeline"][0] == "DISCOVER_PROVIDER_SYMBOL"
    assert sensor["pipeline"][-1] == "ADMISSION_DECISION"

    stats = contract["statistical_governance"]
    assert stats["multiple_testing_control_required"] is True
    assert stats["data_snooping_control_required"] is True
    assert stats["lookahead_forbidden"] is True


def test_global_expansion_preserves_latency_split_and_scalability() -> None:
    contract = global_market_intelligence_contract()

    scalability = contract["scalability_law"]
    assert scalability["configuration_driven"] is True
    assert scalability["schema_driven"] is True
    assert scalability["adapter_based"] is True
    assert scalability["one_bespoke_implementation_per_market_forbidden"] is True

    compute = contract["computation_law"]
    assert compute["deep_global_cognition_separate_from_low_latency_support"] is True
    assert compute["runtime_consumes_causal_precomputed_state"] is True
    assert compute["global_perception_may_not_raise_runtime_sla"] is True


def test_gen2_time_integrity_precedes_relational_intelligence() -> None:
    contract = global_market_intelligence_contract()
    law = contract["gen_2_temporal_comparability_law"]

    assert law["time_integrity_before_relational_intelligence"] is True
    assert law["no_relational_claim_without_relational_comparability"] is True
    assert law["future_pairing_forbidden"] is True
    assert law["post_hoc_alignment_forbidden"] is True
    assert law[
        "canonical_market_session_separate_from_provider_availability"
    ] is True
    assert law["provider_degradation_is_not_market_behavior"] is True
    assert law["unknown_calendar_must_abstain"] is True
    assert law["global_observability_matrix_required"] is True
    assert law["single_global_staleness_threshold_forbidden"] is True
    assert "COMPARABLE" in law["comparability_states"]
    assert "STALE_PEER" in law["comparability_states"]
    assert "TRADING_HALT" in law["comparability_states"]
    assert "OPEN_ACTIVE" in law["session_states"]
    assert "HOLIDAY" in law["session_states"]
    assert "DELAYED" in law["provider_states"]
