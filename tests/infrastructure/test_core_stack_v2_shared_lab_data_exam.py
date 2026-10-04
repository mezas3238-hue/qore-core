import json

from qore.infrastructure.core_stack_v2.shared_lab_data_assessment import REQUIRED_DATA_REALITY_GATES
from qore.infrastructure.core_stack_v2.shared_lab_data_exam import exam_json, run_engineering_data_reality_exam


def test_full_engineering_exam_requires_all_fourteen_gates() -> None:
    result = run_engineering_data_reality_exam()
    assert result.passed
    assert len(result.evidence) == len(REQUIRED_DATA_REALITY_GATES) == 14
    assert result.assessment.failed_gates == ()
    assert result.assessment.missing_gates == ()
    assert len(result.exam_fingerprint) == 64


def test_exam_receipt_is_serializable_and_authority_free() -> None:
    payload = json.loads(exam_json())
    assert payload["passed"] is True
    assert payload["assessment"]["productive_authority"] is False
    assert payload["assessment"]["certification_authority"] is False
