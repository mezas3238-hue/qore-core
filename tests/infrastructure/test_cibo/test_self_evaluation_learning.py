from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from _governed_evidence_fixtures import dependent_evidence

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalBlockedError,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.learning import CiboLearning, CiboLesson, CiboLessonState
from qore.infrastructure.cibo.self_evaluation import (
    CiboAbArm,
    CiboAbEvaluation,
    CiboSelfEvaluation,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_SELF = CiboSelfEvaluation()
_LEARNING = CiboLearning()


def _identity(suffix: str = "vt01") -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _dependent_evidence() -> CiboFunctionalEvidence:
    return dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(CiboEvidenceRef("evidence:ab"),),
        as_of=_NOW,
        reasons=("external.authority.required",),
    )


def _insufficient_evidence() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.INSUFFICIENT,
        evidence_refs=(),
        as_of=_NOW,
        reasons=("insufficient",),
    )


def _evaluate(
    *,
    arm_a: CiboAbArm = CiboAbArm.TRADERS_RISK_ONLY,
    arm_b: CiboAbArm = CiboAbArm.CIBO_MANAGED_TRADERS_RISK,
    trader_versions_a: tuple[ResearchDecisionEvaluatorIdentity, ...] = (
        _identity("vt01"),
        _identity("vt02"),
    ),
    trader_versions_b: tuple[ResearchDecisionEvaluatorIdentity, ...] = (
        _identity("vt01"),
        _identity("vt02"),
    ),
    window_start: datetime = _NOW,
    window_end: datetime = _NOW + timedelta(hours=1),
    assessed_at: datetime = _NOW + timedelta(hours=2),
) -> Result[CiboAbEvaluation, CiboFunctionalError]:
    return _SELF.evaluate(
        arm_a=arm_a,
        arm_b=arm_b,
        trader_versions_a=trader_versions_a,
        trader_versions_b=trader_versions_b,
        window_start=window_start,
        window_end=window_end,
        evidence=_dependent_evidence(),
        conclusion_code="conclusion.ab",
        assessed_at=assessed_at,
    )


# --- CF-18: self-evaluation / A-B contribution ---


def test_fair_ab_with_identical_versions_and_window() -> None:
    result = _evaluate()
    assert isinstance(result, Success)
    evaluation = result.value
    assert evaluation.arm_a is CiboAbArm.TRADERS_RISK_ONLY
    assert evaluation.arm_b is CiboAbArm.CIBO_MANAGED_TRADERS_RISK
    assert evaluation.authority is CiboFunctionalAuthority.OPINION
    assert evaluation.trader_versions_a == evaluation.trader_versions_b


def test_ab_rejects_mismatched_versions() -> None:
    result = _evaluate(trader_versions_b=(_identity("vt99"),))
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_ab_rejects_mismatched_windows() -> None:
    result = _evaluate(window_start=_NOW + timedelta(hours=1), window_end=_NOW)
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_ab_rejects_assessment_before_window_end() -> None:
    result = _evaluate(assessed_at=_NOW + timedelta(minutes=30))
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_ab_rejects_non_ab_arm_pairing() -> None:
    result = _evaluate(
        arm_a=CiboAbArm.CIBO_MANAGED_TRADERS_RISK,
        arm_b=CiboAbArm.TRADERS_RISK_ONLY,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_ab_repeated_identical_input_equal_logical_values() -> None:
    left = _evaluate()
    right = _evaluate()
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


# --- CF-19: learning from governed experience ---


def _accept(
    *,
    evidence: CiboFunctionalEvidence | None = None,
    confidence: Decimal = Decimal("0.85"),
) -> Result[CiboLesson, CiboFunctionalError]:
    return _LEARNING.accept(
        _dependent_evidence() if evidence is None else evidence,
        lesson_code="lesson.stop.discipline",
        outcome_ref=CiboEvidenceRef("evidence:outcome"),
        provenance_codes=("provenance.outcome",),
        confidence=confidence,
        evidence_refs=(CiboEvidenceRef("evidence:lesson"),),
        applicability_code="applicability.fx",
        decided_at=_NOW,
    )


def _reject(*, confidence: Decimal = Decimal("0.1")) -> Result[CiboLesson, CiboFunctionalError]:
    return _LEARNING.reject(
        _dependent_evidence(),
        lesson_code="lesson.stop.discipline",
        outcome_ref=CiboEvidenceRef("evidence:outcome"),
        provenance_codes=("provenance.outcome",),
        confidence=confidence,
        evidence_refs=(),
        applicability_code="applicability.fx",
        decided_at=_NOW,
    )


def test_lesson_accept_rejects_dependent_evidence() -> None:
    # Correction 003: an ACCEPTED lesson requires SUFFICIENT (authority-rooted)
    # evidence, which CIBO cannot manufacture; evidence-dependent input fails
    # closed to blocked.
    result = _accept()
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_lesson_accept_rejects_insufficient_evidence() -> None:
    result = _accept(evidence=_insufficient_evidence())
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_lesson_rejected_with_insufficient_evidence() -> None:
    result = _LEARNING.reject(
        _insufficient_evidence(),
        lesson_code="lesson.stop.discipline",
        outcome_ref=CiboEvidenceRef("evidence:outcome"),
        provenance_codes=("provenance.outcome",),
        confidence=Decimal("0.1"),
        evidence_refs=(),
        applicability_code="applicability.fx",
        decided_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboLessonState.REJECTED


def test_lesson_rejects_confidence_out_of_range() -> None:
    result = _reject(confidence=Decimal("1.5"))
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_lesson_has_no_config_rewrite_fields() -> None:
    result = _reject()
    assert isinstance(result, Success)
    lesson = result.value
    assert not hasattr(lesson, "config")
    assert not hasattr(lesson, "code")
    assert not hasattr(lesson, "parameter")
    assert not hasattr(lesson, "mutation")


def test_lesson_repeated_identical_input_equal_logical_values() -> None:
    left = _reject()
    right = _reject()
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


def test_self_evaluation_learning_logical_values_contain_no_secrets() -> None:
    evaluation = _evaluate()
    assert isinstance(evaluation, Success)
    evaluation_projection = repr(evaluation.value.logical_values())
    for secret in ("secret", "token", "password", "private_key", "bearer"):
        assert secret not in evaluation_projection

    lesson = _reject()
    assert isinstance(lesson, Success)
    lesson_projection = repr(lesson.value.logical_values())
    for secret in ("secret", "token", "password", "private_key", "bearer"):
        assert secret not in lesson_projection
