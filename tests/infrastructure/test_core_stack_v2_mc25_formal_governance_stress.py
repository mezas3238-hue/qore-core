from qore.infrastructure.core_stack_v2.mc25_formal_governance_stress import (
    run_formal_governance_stress,
)


def test_formal_governance_stress_fails_closed_on_all_forbidden_paths() -> None:
    result = run_formal_governance_stress()
    assert result["status"] == "MC25_FORMAL_GOVERNANCE_STRESS_PASS"
    assert result["formal_stress_stage_completed"] is True
    assert result["scenario_count"] == result["rejected_scenario_count"]
    assert result["highest_formal_stage"] == "FORMAL_STRESS"
    assert result["shadow_stage_bound"] is False
    assert result["certification_stage_bound"] is False
    assert result["promotion_allowed"] is False
    assert result["productive_authority"] is False
