from __future__ import annotations

from qore.infrastructure.core_stack_v2.architecture_freeze import (
    superintelligence_freeze_contract,
)
from qore.infrastructure.core_stack_v2.shared_brain_architecture_contract import (
    SHARED_BRAIN_ARCHITECTURE_VERSION,
    shared_brain_architecture_contract,
)


def test_shared_brain_architecture_preserves_sovereignty() -> None:
    contract = shared_brain_architecture_contract()

    assert contract["version"] == SHARED_BRAIN_ARCHITECTURE_VERSION
    sovereignty = contract["sovereignty_law"]
    assert sovereignty["shared_is_not_a_trader"] is True
    assert sovereignty["specialist_traders_remain_sovereign"] is True
    assert sovereignty["qore_risk_remains_sovereign"] is True
    assert sovereignty["execution_remains_sovereign"] is True
    assert sovereignty["shared_direct_order_authority"] is False
    assert sovereignty["shared_sizing_authority"] is False


def test_shared_brain_architecture_requires_cognitive_market_os() -> None:
    contract = shared_brain_architecture_contract()

    assert (
        contract["hierarchical_world_model_law"][
            "multiple_temporal_levels_required"
        ]
        is True
    )
    assert (
        contract["multi_world_law"]["multiple_internal_world_models_required"]
        is True
    )
    assert (
        contract["reasoning_law"]["multiple_competing_hypotheses_required"]
        is True
    )
    assert contract["reasoning_law"]["hypothesis_falsification_required"] is True
    assert contract["uncertainty_law"]["epistemic_uncertainty_required"] is True
    assert contract["uncertainty_law"]["aleatoric_uncertainty_required"] is True
    assert contract["autonomous_research_law"]["holdout_required"] is True
    assert contract["autonomous_research_law"]["replication_required"] is True


def test_experimental_knowledge_cannot_self_promote() -> None:
    contract = shared_brain_architecture_contract()

    continual = contract["continual_learning_law"]
    research = contract["autonomous_research_law"]
    assert (
        continual[
            "experimental_knowledge_cannot_replace_certified_knowledge_directly"
        ]
        is True
    )
    assert research["research_may_not_self_promote_to_runtime"] is True
    assert research["validated_to_certified_requires_owner_governed_gate"] is True


def test_owner_cognitive_firewall_forbids_shared_actuation() -> None:
    contract = shared_brain_architecture_contract()
    os_contract = contract["cognitive_os_contract"]
    firewall = os_contract["cognitive_firewall"]

    assert firewall["read_only_by_default"] is True
    assert firewall["shared_may_seize_sovereign_authority"] is False
    assert set(firewall["forbidden_shared_authorities"]) == {
        "order_send",
        "position_close",
        "modify_stop",
        "modify_tp",
        "position_size",
        "capital_allocate",
        "risk_authorize",
        "trade_block",
        "trade_force",
    }
    assert firewall["trader_decides_setup"] is True
    assert firewall["cibo_decides_allocation_and_sizing"] is True
    assert firewall["qore_risk_authorizes_capital_risk"] is True
    assert firewall["execution_mutates_broker_state"] is True


def test_shared_cognitive_os_observes_three_realities_and_can_abstain() -> None:
    contract = shared_brain_architecture_contract()["cognitive_os_contract"]

    assert set(contract["reality_planes"]["required"]) == {
        "MARKET_REALITY",
        "CORE_REALITY",
        "COGNITIVE_REALITY",
    }
    assert contract["digital_twins"]["core_digital_twin_required"] is True
    assert (
        contract["core_infrastructure_and_broker_intelligence"][
            "core_stability_separate_from_market_stability"
        ]
        is True
    )
    assert contract["interfaces_and_blindspots"]["blindspot_engine_required"] is True
    assert (
        contract["trust_and_failure_modes"][
            "anti_hallucination_architecture_required"
        ]
        is True
    )
    assert "NO_SUPPORTED_HYPOTHESIS" in contract["trust_and_failure_modes"][
        "abstention_states"
    ]


def test_shared_cognitive_os_requires_self_model_and_scientific_memory() -> None:
    contract = shared_brain_architecture_contract()["cognitive_os_contract"]

    assert contract["metacognition"]["self_model_required"] is True
    assert contract["metacognition"]["value_of_computation_required"] is True
    assert contract["memory_and_knowledge"]["cognitive_failure_memory_required"] is True
    assert contract["memory_and_knowledge"]["knowledge_half_life_required"] is True
    assert (
        contract["memory_and_knowledge"]["knowledge_transportability_required"]
        is True
    )
    assert contract["representation_and_ontology"]["ontology_evolution_required"] is True


def test_legacy_freeze_cannot_reintroduce_shared_actuation() -> None:
    freeze = superintelligence_freeze_contract()

    sovereignty = freeze["specialist_sovereignty"]
    assert sovereignty["shared_may_issue_stop_improvement_directive"] is False
    assert sovereignty["shared_may_issue_target_extension_directive"] is False
    assert sovereignty["shared_may_issue_realtime_trade_management_directive"] is False

    position = freeze["position_law"]
    assert position["shared_may_manage_stop"] is False
    assert position["shared_may_manage_target"] is False
    assert position["shared_may_trail_position"] is False
    assert position["shared_may_close_position"] is False
    assert position["shared_may_block_trade"] is False
    assert position["shared_may_force_trade"] is False

    governance = freeze["governance"]
    assert governance["shared_broker_mutation_authority"] is False
    assert governance["shared_position_mutation_authority"] is False
    assert governance["shared_capital_allocation_authority"] is False
    assert governance["shared_trade_block_authority"] is False
    assert governance["shared_trade_force_authority"] is False


def test_maximum_architecture_005_requires_unknown_unknown_discovery() -> None:
    contract = shared_brain_architecture_contract()
    os_contract = contract["cognitive_os_contract"]

    assert contract["version"] == "QORE_META_COGNITIVE_SCIENTIFIC_INTELLIGENCE_005"
    assert (
        os_contract["version"]
        == "QORE_COGNITIVE_SCIENTIFIC_EPISTEMIC_OS_005"
    )
    unknowns = os_contract["unknown_unknown_discovery"]
    assert unknowns["second_order_blindspot_detection_required"] is True
    assert unknowns["must_search_for_uninstrumented_observation_spaces"] is True
    assert unknowns["must_search_for_unmodeled_dependencies"] is True
    assert unknowns["must_not_force_unknown_unknown_into_known_ontology"] is True


def test_maximum_architecture_005_separates_systemic_stability_planes() -> None:
    os_contract = shared_brain_architecture_contract()["cognitive_os_contract"]
    stability = os_contract["systemic_stability"]

    assert stability["market_stability_required"] is True
    assert stability["core_stability_required"] is True
    assert stability["broker_stability_required"] is True
    assert stability["cognitive_stability_required"] is True
    assert stability["systemic_stress_required"] is True
    assert stability["stability_state_is_not_trading_command"] is True
    assert "SYSTEM_DEGRADED" in stability["descriptive_states"]


def test_maximum_cognitive_api_is_read_only_and_non_actuating() -> None:
    os_contract = shared_brain_architecture_contract()["cognitive_os_contract"]
    api = os_contract["maximum_cognitive_api"]

    assert "world" in api["read_only_surface"]
    assert "get_blindspots" in api["read_only_surface"]
    assert "knowledge_status" in api["read_only_surface"]
    assert set(api["forbidden_actuation_surface"]) == {
        "enter",
        "exit",
        "resize",
        "block",
        "send_order",
        "allocate_capital",
        "authorize_risk",
    }
    assert api["api_may_mutate_broker"] is False
    assert api["api_may_allocate_capital"] is False
    assert api["api_may_authorize_risk"] is False
    assert api["api_may_mutate_trader_methodology"] is False


def test_shared_maximum_objective_is_understanding_not_outcome_ownership() -> None:
    os_contract = shared_brain_architecture_contract()["cognitive_os_contract"]
    objective = os_contract["objective_law"]

    assert "WorldUnderstanding" in objective["primary_objectives"]
    assert "UnknownUnknownDiscovery" in objective["primary_objectives"]
    assert objective["profit_factor_is_primary_objective"] is False
    assert objective["drawdown_is_primary_objective"] is False
    assert objective["price_prediction_is_primary_objective"] is False
    assert objective["no_trading_authority"] is True
    assert objective["no_risk_authority"] is True
    assert objective["no_capital_authority"] is True
    assert objective["no_execution_authority"] is True
