from qore.infrastructure.core_stack_v2.shared_lab_global_exam import (
    run_global_lab_exam,
)


def test_complete_shared_lab_global_exam_passes() -> None:
    result = run_global_lab_exam()
    assert result.core_l10_pass
    assert result.data_exam_pass
    assert result.data_l10_pass
    assert result.global_l10_pass
    assert result.authority_isolation_pass
    assert result.readiness_blockers == ()
    assert result.laboratory_available_for_shared_validation
    assert result.passed
    assert not result.protected_holdout_opened
    assert not result.productive_authority
