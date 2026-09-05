from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalBlockedError,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo.trader_academy import (
    CiboAcademy,
    CiboAcademyStage,
    CiboAcademyTransition,
    CiboExperimentRequest,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.cibo_trader_development_review import (
    CiboDevelopmentReason,
    CiboDevelopmentRecommendation,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_ACADEMY = CiboAcademy()


def _identity(suffix: str = "vt01") -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _fingerprint(n: int = 1) -> CiboTraderConfigFingerprint:
    return CiboTraderConfigFingerprint(f"{n:064x}")


def _evidence() -> CiboEvidenceRef:
    return CiboEvidenceRef("evidence:academy")


# --- NORMAL ---


def test_request_experiment_produces_request_authority() -> None:
    result = _ACADEMY.request_experiment(
        request_code="exp-request-1",
        trader_identity=_identity(),
        config_fingerprint=_fingerprint(),
        hypothesis_code="hyp-1",
        evidence_refs=(_evidence(),),
        requested_at=_NOW,
    )
    assert isinstance(result, Success)
    request: CiboExperimentRequest = result.value
    assert request.authority is CiboFunctionalAuthority.REQUEST
    assert request.request_code == "exp-request-1"
    assert request.hypothesis_code == "hyp-1"
    assert request.evidence_refs == (_evidence(),)


def test_request_experiment_sorts_evidence_refs_deterministically() -> None:
    refs = (CiboEvidenceRef("evidence:z"), CiboEvidenceRef("evidence:a"))
    result = _ACADEMY.request_experiment(
        request_code="exp-request-2",
        trader_identity=_identity(),
        config_fingerprint=_fingerprint(),
        hypothesis_code="hyp-2",
        evidence_refs=refs,
        requested_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.evidence_refs == tuple(sorted(refs, key=lambda r: r.value))


def test_advance_promotion_maps_to_new_exact_version() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.ACCEPT_REJECT_LESSON,
        decision=CiboDevelopmentRecommendation.RECOMMEND_PROMOTION,
        reason=CiboDevelopmentReason.EVIDENCE_COMPLETE,
        new_identity=_identity("vt02"),
        new_fingerprint=_fingerprint(2),
    )
    assert isinstance(result, Success)
    assert result.value is CiboAcademyStage.NEW_EXACT_VERSION


def test_advance_continue_curriculum_advances_forward() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.OBSERVE,
        decision=CiboDevelopmentRecommendation.CONTINUE_CURRICULUM,
        reason=CiboDevelopmentReason.CURRICULUM_INCOMPLETE,
    )
    assert isinstance(result, Success)
    assert result.value is CiboAcademyStage.DIAGNOSE


def test_advance_more_evidence_maps_to_trader_lab() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.HYPOTHESIS,
        decision=CiboDevelopmentRecommendation.MORE_EVIDENCE_REQUIRED,
        reason=CiboDevelopmentReason.EVIDENCE_INSUFFICIENT,
    )
    assert isinstance(result, Success)
    assert result.value is CiboAcademyStage.TRADER_LAB


def test_advance_rejection_maps_to_design_experiment() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.ACCEPT_REJECT_LESSON,
        decision=CiboDevelopmentRecommendation.RECOMMEND_REJECTION,
        reason=CiboDevelopmentReason.REJECTED_STATE,
    )
    assert isinstance(result, Success)
    assert result.value is CiboAcademyStage.DESIGN_EXPERIMENT


def test_advance_retrain_maps_to_trader_lab() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.MEASURE,
        decision=CiboDevelopmentRecommendation.RETRAIN_RETURN_TO_LAB,
        reason=CiboDevelopmentReason.EVIDENCE_STALE,
    )
    assert isinstance(result, Success)
    assert result.value is CiboAcademyStage.TRADER_LAB


def test_advance_suspension_review_maps_to_diagnose() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.MEASURE,
        decision=CiboDevelopmentRecommendation.RECOMMEND_SUSPENSION_REVIEW,
        reason=CiboDevelopmentReason.SUSPENDED_OR_DEGRADED,
    )
    assert isinstance(result, Success)
    assert result.value is CiboAcademyStage.DIAGNOSE


def test_advance_requalify_requires_explicit_new_version() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.NEW_EXACT_VERSION,
        decision=CiboDevelopmentRecommendation.CONTINUE_CURRICULUM,
        reason=CiboDevelopmentReason.CURRICULUM_INCOMPLETE,
        new_identity=_identity("vt02"),
        new_fingerprint=_fingerprint(2),
    )
    assert isinstance(result, Success)
    assert result.value is CiboAcademyStage.REQUALIFY


def test_transition_accepts_forward_move() -> None:
    transition = CiboAcademyTransition(
        from_stage=CiboAcademyStage.DIAGNOSE,
        to_stage=CiboAcademyStage.HYPOTHESIS,
        reason_code="curriculum-incomplete",
        evidence_refs=(_evidence(),),
    )
    assert transition.to_stage is CiboAcademyStage.HYPOTHESIS


def test_transition_accepts_accept_path() -> None:
    transition = CiboAcademyTransition(
        from_stage=CiboAcademyStage.ACCEPT_REJECT_LESSON,
        to_stage=CiboAcademyStage.NEW_EXACT_VERSION,
        reason_code="lesson-accepted",
        evidence_refs=(),
    )
    assert transition.to_stage is CiboAcademyStage.NEW_EXACT_VERSION


def test_transition_accepts_reject_redesign_loop() -> None:
    transition = CiboAcademyTransition(
        from_stage=CiboAcademyStage.ACCEPT_REJECT_LESSON,
        to_stage=CiboAcademyStage.DESIGN_EXPERIMENT,
        reason_code="lesson-rejected-redesign",
        evidence_refs=(),
    )
    assert transition.to_stage is CiboAcademyStage.DESIGN_EXPERIMENT


# --- ADVERSARIAL ---


def test_experiment_request_rejects_non_request_authority() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboExperimentRequest(
            request_code="exp-request-1",
            trader_identity=_identity(),
            config_fingerprint=_fingerprint(),
            hypothesis_code="hyp-1",
            evidence_refs=(_evidence(),),
            requested_at=_NOW,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
        )


def test_request_experiment_rejects_malformed_nested_type() -> None:
    bad_refs = cast(tuple[CiboEvidenceRef, ...], ("evidence:not-a-ref",))
    result = _ACADEMY.request_experiment(
        request_code="exp-request-1",
        trader_identity=_identity(),
        config_fingerprint=_fingerprint(),
        hypothesis_code="hyp-1",
        evidence_refs=bad_refs,
        requested_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_request_experiment_rejects_naive_timestamp() -> None:
    result = _ACADEMY.request_experiment(
        request_code="exp-request-1",
        trader_identity=_identity(),
        config_fingerprint=_fingerprint(),
        hypothesis_code="hyp-1",
        evidence_refs=(_evidence(),),
        requested_at=datetime(2026, 8, 9, 0, 0),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_advance_rejects_silent_new_exact_version() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.ACCEPT_REJECT_LESSON,
        decision=CiboDevelopmentRecommendation.RECOMMEND_PROMOTION,
        reason=CiboDevelopmentReason.EVIDENCE_COMPLETE,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_advance_rejects_silent_requalify() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.NEW_EXACT_VERSION,
        decision=CiboDevelopmentRecommendation.CONTINUE_CURRICULUM,
        reason=CiboDevelopmentReason.CURRICULUM_INCOMPLETE,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_advance_rejects_inconsistent_reason() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.OBSERVE,
        decision=CiboDevelopmentRecommendation.CONTINUE_CURRICULUM,
        reason=CiboDevelopmentReason.EVIDENCE_STALE,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_advance_rejects_wrong_type_decision() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.OBSERVE,
        decision=cast(CiboDevelopmentRecommendation, "recommend-promotion"),
        reason=CiboDevelopmentReason.CURRICULUM_INCOMPLETE,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_advance_rejects_new_identity_for_non_version_stage() -> None:
    result = _ACADEMY.advance(
        CiboAcademyStage.OBSERVE,
        decision=CiboDevelopmentRecommendation.CONTINUE_CURRICULUM,
        reason=CiboDevelopmentReason.CURRICULUM_INCOMPLETE,
        new_identity=_identity("vt02"),
        new_fingerprint=_fingerprint(2),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_transition_rejects_backwards_move() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboAcademyTransition(
            from_stage=CiboAcademyStage.HYPOTHESIS,
            to_stage=CiboAcademyStage.DIAGNOSE,
            reason_code="curriculum-incomplete",
            evidence_refs=(),
        )


def test_transition_rejects_reject_loop_without_reject_reason() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboAcademyTransition(
            from_stage=CiboAcademyStage.ACCEPT_REJECT_LESSON,
            to_stage=CiboAcademyStage.DESIGN_EXPERIMENT,
            reason_code="lesson-accepted",
            evidence_refs=(),
        )


def test_transition_rejects_self_loop() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboAcademyTransition(
            from_stage=CiboAcademyStage.DIAGNOSE,
            to_stage=CiboAcademyStage.DIAGNOSE,
            reason_code="curriculum-incomplete",
            evidence_refs=(),
        )


# --- DETERMINISM / NO EXECUTION AUTHORITY ---


def test_repeated_identical_request_equal_logical_values() -> None:
    left = _ACADEMY.request_experiment(
        request_code="exp-request-1",
        trader_identity=_identity(),
        config_fingerprint=_fingerprint(),
        hypothesis_code="hyp-1",
        evidence_refs=(_evidence(),),
        requested_at=_NOW,
    )
    right = _ACADEMY.request_experiment(
        request_code="exp-request-1",
        trader_identity=_identity(),
        config_fingerprint=_fingerprint(),
        hypothesis_code="hyp-1",
        evidence_refs=(_evidence(),),
        requested_at=_NOW,
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


def test_academy_grants_no_execution_or_promotion_authority() -> None:
    assert not hasattr(_ACADEMY, "execute")
    assert not hasattr(_ACADEMY, "place_order")
    assert not hasattr(_ACADEMY, "promote")
    assert not hasattr(_ACADEMY, "authorize_risk")
