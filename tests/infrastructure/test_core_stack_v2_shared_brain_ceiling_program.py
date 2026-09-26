from __future__ import annotations

from qore.infrastructure.core_stack_v2.shared_brain_ceiling_program import (
    FINAL_CERTIFICATION_GATES,
    PROGRAM_ID,
    TRANSVERSAL_ARCHITECTURE_REQUIREMENTS,
    WORK_CHAIN,
    validate_work_chain,
)


def test_maximum_ceiling_program_is_complete_and_ordered() -> None:
    validate_work_chain()

    assert PROGRAM_ID == "QORE_META_COGNITIVE_SCIENTIFIC_INTELLIGENCE_004"
    assert tuple(package.work_id for package in WORK_CHAIN) == tuple(
        f"WP-{index:02d}" for index in range(1, 13)
    )
    assert WORK_CHAIN[0].depends_on == ()
    assert WORK_CHAIN[-1].depends_on == ("WP-11",)


def test_final_certification_remains_economic_and_out_of_sample() -> None:
    required = set(FINAL_CERTIFICATION_GATES)

    assert "profit_factor_increases" in required
    assert "drawdown_reduces" in required
    assert "winner_count_protected" in required
    assert "fresh_holdout_pass" in required
    assert "stress_pass" in required
    assert "no_future_leakage" in required
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
