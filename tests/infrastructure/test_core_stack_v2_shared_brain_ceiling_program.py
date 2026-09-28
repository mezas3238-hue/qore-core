from __future__ import annotations

from qore.infrastructure.core_stack_v2.shared_brain_architecture_contract import (
    SHARED_BRAIN_ARCHITECTURE_VERSION,
)
from qore.infrastructure.core_stack_v2.shared_brain_ceiling_program import (
    FINAL_CERTIFICATION_GATES,
    MAXIMUM_PRECERTIFICATION_CAPABILITIES,
    PRE_CERTIFICATION_GATES,
    PROGRAM_ID,
    TRANSVERSAL_ARCHITECTURE_REQUIREMENTS,
    WORK_CHAIN,
    validate_work_chain,
)


def test_maximum_ceiling_program_is_complete_and_ordered() -> None:
    validate_work_chain()

    assert PROGRAM_ID == "QORE_META_COGNITIVE_SCIENTIFIC_INTELLIGENCE_005"
    assert PROGRAM_ID == SHARED_BRAIN_ARCHITECTURE_VERSION
    assert tuple(package.work_id for package in WORK_CHAIN) == tuple(
        f"WP-{index:02d}" for index in range(1, 13)
    )
    assert WORK_CHAIN[0].depends_on == ()
    assert WORK_CHAIN[-1].depends_on == ("WP-11",)


def test_maximum_ceiling_is_mandatory_before_certification() -> None:
    capabilities = set(MAXIMUM_PRECERTIFICATION_CAPABILITIES)
    gates = set(PRE_CERTIFICATION_GATES)

    assert len(MAXIMUM_PRECERTIFICATION_CAPABILITIES) == 28
    assert "PROBABILISTIC_MARKET_DIGITAL_TWIN" in capabilities
    assert "PREDICTIVE_STATE_MODEL_AND_PREDICTIVE_CODING" in capabilities
    assert "ACTIVE_PERCEPTION_AND_VALUE_OF_INFORMATION" in capabilities
    assert "MARKET_PHYSICS_CONSTRAINT_ENGINE" in capabilities
    assert "NEURAL_SYMBOLIC_BRAIN" in capabilities
    assert "QORE_MARKET_FOUNDATION_MODEL" in capabilities
    assert "DYNAMIC_GRAPH_MARKET_MODEL" in capabilities
    assert "UNCERTAINTY_DECOMPOSITION" in capabilities
    assert "TRAJECTORY_INTELLIGENCE" in capabilities
    assert "AUTONOMOUS_SCIENTIFIC_LABORATORY" in capabilities
    assert "META_LEARNING_RAPID_REGIME_ADAPTATION" in capabilities
    assert "CONTINUAL_LEARNING_WITHOUT_CATASTROPHIC_FORGETTING" in capabilities
    assert "META_COGNITIVE_SCIENTIFIC_INTELLIGENCE" in capabilities

    assert "wp_01_through_wp_12_closed" in gates
    assert "mc_01_through_mc_28_satisfied" in gates
    assert "cognitive_firewall_pass" in gates
    assert "anti_leakage_pass" in gates
    assert "adapter_sovereignty_pass" in gates
    assert "no_hidden_trader_logic" in gates
    assert "certification_inputs_and_thresholds_frozen" in gates


def test_final_certification_is_seven_current_traders_two_years() -> None:
    required = set(FINAL_CERTIFICATION_GATES)

    assert "seven_current_traders_frozen_as_is" in required
    assert "no_pre_exam_trader_improvement" in required
    assert "genuinely_fresh_two_year_holdout" in required
    assert "year_1_superior_for_seven_of_seven" in required
    assert "year_2_superior_for_seven_of_seven" in required
    assert "every_required_oos_fold_pass" in required
    assert "full_current_utc_001_pass_for_seven_of_seven" in required
    assert "material_incremental_value" in required
    assert "monte_carlo_and_tail_stress_pass" in required
    assert "ablation_and_causal_attribution_pass" in required
    assert "failure_engineering_pass" in required
    assert "no_future_leakage" in required
    assert "authority_isolation_pass" in required
    assert "no_production_self_promotion" in required


def test_each_work_package_has_outputs_and_exit_gates() -> None:
    for package in WORK_CHAIN:
        assert package.required_outputs
        assert package.exit_gates


def test_owner_cognitive_os_requirements_are_transversal_not_new_work_packages() -> None:
    required = set(TRANSVERSAL_ARCHITECTURE_REQUIREMENTS)

    assert "COGNITIVE_FIREWALL" in required
    assert "QORE_CORE_DIGITAL_TWIN" in required
    assert "INFRASTRUCTURE_INTELLIGENCE" in required
    assert "BROKER_INTELLIGENCE" in required
    assert "UNKNOWN_WORLD_FIRST_CLASS" in required
    assert "NEGATIVE_EVIDENCE_ENGINE" in required
    assert "VALUE_OF_INFORMATION" in required
    assert "SELF_MODEL" in required
    assert "VALUE_OF_COMPUTATION" in required
    assert "COGNITIVE_FAILURE_MEMORY" in required
    assert "KNOWLEDGE_TRANSPORTABILITY" in required
    assert "ONTOLOGY_EVOLUTION" in required
    assert "BLINDSPOT_ENGINE" in required
    assert "DEGRADED_MODE" in required

    assert tuple(package.work_id for package in WORK_CHAIN) == tuple(
        f"WP-{index:02d}" for index in range(1, 13)
    )
