from __future__ import annotations

from qore.infrastructure.core_stack_v2.shared_brain_ceiling_program import (
    FINAL_CERTIFICATION_GATES,
    PROGRAM_ID,
    WORK_CHAIN,
    validate_work_chain,
)


def test_maximum_ceiling_program_is_complete_and_ordered() -> None:
    validate_work_chain()

    assert PROGRAM_ID == "QORE_META_COGNITIVE_SCIENTIFIC_INTELLIGENCE_003"
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
