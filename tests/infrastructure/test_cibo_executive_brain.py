from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveBrain,
    CiboExecutiveBrainValidationError,
    CiboExecutiveDirectiveKind,
    CiboExecutiveSynthesis,
)
from qore.infrastructure.order_intent import OrderIntent
from qore.kernel.result import Failure, Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboFormalRecommendation,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_BRAIN = CiboExecutiveBrain()


def _ref(value: str) -> CiboCognitiveEvidenceRef:
    return CiboCognitiveEvidenceRef(value)


def _bounded_uncertainty() -> CiboUncertainty:
    return CiboUncertainty(
        kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
        confidence=CiboConfidence(
            level=CiboConfidenceLevel.MEDIUM,
            evidence_refs=(_ref("evidence:bounded"),),
        ),
    )


def _insufficient_uncertainty() -> CiboUncertainty:
    return CiboUncertainty(kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE)


def _recommendation() -> CiboFormalRecommendation:
    return CiboFormalRecommendation(
        recommendation_id=UUID("70000000-0000-0000-0000-0000000000aa"),
        recommendation_code="cibo.review-portfolio",
        reasoning_mode=CiboReasoningMode.HIGH,
        summary="Review portfolio exposure",
        evidence_refs=(_ref("evidence:exposure"),),
        uncertainty=_bounded_uncertainty(),
        issued_at=_NOW,
    )


def _synthesize(
    *,
    memory_refs: tuple[UUID, ...] = (),
    deliberation_ref: UUID | None = None,
) -> CiboExecutiveSynthesis:
    result = _BRAIN.synthesize(
        synthesis_id=UUID("70000000-0000-0000-0000-000000000001"),
        directive=CiboExecutiveDirectiveKind.RECOMMEND,
        reasoning_mode=CiboReasoningMode.HIGH,
        subject_code="subject-demo",
        synthesized_at=_NOW,
        evidence_refs=(_ref("evidence:demo"),),
        uncertainty=_bounded_uncertainty(),
        recommendation=_recommendation(),
        memory_refs=memory_refs,
        deliberation_ref=deliberation_ref,
    )
    assert isinstance(result, Success)
    return result.value


class TestDirectiveKinds:
    def test_recommend_requires_recommendation(self) -> None:
        result = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-000000000002"),
            directive=CiboExecutiveDirectiveKind.RECOMMEND,
            reasoning_mode=CiboReasoningMode.HIGH,
            subject_code="subject-demo",
            synthesized_at=_NOW,
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=_bounded_uncertainty(),
        )
        assert isinstance(result, Failure)
        assert isinstance(result.error, CiboExecutiveBrainValidationError)

    def test_question_requires_questions(self) -> None:
        result = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-000000000003"),
            directive=CiboExecutiveDirectiveKind.QUESTION,
            reasoning_mode=CiboReasoningMode.HIGH,
            subject_code="subject-demo",
            synthesized_at=_NOW,
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=_insufficient_uncertainty(),
        )
        assert isinstance(result, Failure)

    def test_request_requires_request_code(self) -> None:
        result = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-000000000004"),
            directive=CiboExecutiveDirectiveKind.REQUEST_EVIDENCE,
            reasoning_mode=CiboReasoningMode.HIGH,
            subject_code="subject-demo",
            synthesized_at=_NOW,
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=_insufficient_uncertainty(),
        )
        assert isinstance(result, Failure)

    def test_defer_and_abstain_paths(self) -> None:
        for directive in (
            CiboExecutiveDirectiveKind.DEFER,
            CiboExecutiveDirectiveKind.ABSTAIN,
        ):
            result = _BRAIN.synthesize(
                synthesis_id=UUID("70000000-0000-0000-0000-000000000005"),
                directive=directive,
                reasoning_mode=CiboReasoningMode.FAST,
                subject_code="subject-demo",
                synthesized_at=_NOW,
                evidence_refs=(_ref("evidence:demo"),),
                uncertainty=_insufficient_uncertainty(),
            )
            assert isinstance(result, Success)
            assert result.value.directive is directive
            assert result.value.recommendation is None


class TestAuthorityBoundary:
    def test_synthesis_has_no_provider_native_execution_fields(self) -> None:
        synthesis = _synthesize()
        for absent in (
            "order",
            "intent",
            "provider",
            "instrument",
            "quantity",
            "account",
            "authorization",
            "side",
            "limit_price",
            "receipt",
        ):
            assert not hasattr(synthesis, absent)

    def test_synthesis_is_not_an_order_intent(self) -> None:
        synthesis = _synthesize()
        assert not isinstance(synthesis, OrderIntent)

    def test_synthesis_cannot_be_trader_promotion(self) -> None:
        synthesis = _synthesize()
        assert not hasattr(synthesis, "certification_state")
        assert not hasattr(synthesis, "promotion")

    def test_brain_has_no_execution_decision_seam(self) -> None:
        assert not hasattr(_BRAIN, "decide")
        assert not hasattr(_BRAIN, "submit")

    def test_recommendation_is_not_risk_approval(self) -> None:
        synthesis = _synthesize()
        assert synthesis.recommendation is not None
        assert not hasattr(synthesis.recommendation, "risk_policy")
        assert not hasattr(synthesis.recommendation, "approved")

    def test_synthesis_requires_evidence(self) -> None:
        result = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-000000000006"),
            directive=CiboExecutiveDirectiveKind.ABSTAIN,
            reasoning_mode=CiboReasoningMode.FAST,
            subject_code="subject-demo",
            synthesized_at=_NOW,
            evidence_refs=(),
            uncertainty=_insufficient_uncertainty(),
        )
        assert isinstance(result, Failure)


class TestSynthesis:
    def test_synthesis_deterministic(self) -> None:
        assert _synthesize().logical_values() == _synthesize().logical_values()

    def test_synthesis_carries_memory_and_deliberation_refs(self) -> None:
        memory_id = UUID("70000000-0000-0000-0000-0000000000aa")
        deliberation_id = UUID("70000000-0000-0000-0000-0000000000bb")
        synthesis = _synthesize(
            memory_refs=(memory_id,),
            deliberation_ref=deliberation_id,
        )
        assert synthesis.memory_refs == (memory_id,)
        assert synthesis.deliberation_ref == deliberation_id

    def test_revalidate_detects_tampered_recommendation(self) -> None:
        synthesis = _synthesize()
        object.__setattr__(synthesis.recommendation, "summary", "token=leaked")
        with pytest.raises(CiboExecutiveBrainValidationError):
            synthesis.revalidate()


class TestReflectiveCorruptionFailsAtConstruction:
    def test_synthesize_rejects_reflectively_corrupted_uncertainty(self) -> None:
        uncertainty = _insufficient_uncertainty()
        object.__setattr__(uncertainty, "kind", CiboUncertaintyKind.BOUNDED_CONFIDENCE)
        result = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-000000000011"),
            directive=CiboExecutiveDirectiveKind.ABSTAIN,
            reasoning_mode=CiboReasoningMode.FAST,
            subject_code="subject-demo",
            synthesized_at=_NOW,
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=uncertainty,
        )
        assert isinstance(result, Failure)
        assert isinstance(result.error, CiboExecutiveBrainValidationError)

    def test_synthesize_rejects_corrupted_nested_recommendation(self) -> None:
        recommendation = _recommendation()
        object.__setattr__(recommendation, "summary", "token=leaked")
        result = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-000000000012"),
            directive=CiboExecutiveDirectiveKind.RECOMMEND,
            reasoning_mode=CiboReasoningMode.HIGH,
            subject_code="subject-demo",
            synthesized_at=_NOW,
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=_bounded_uncertainty(),
            recommendation=recommendation,
        )
        assert isinstance(result, Failure)
        assert isinstance(result.error, CiboExecutiveBrainValidationError)

    def test_synthesize_rejects_corrupted_nested_evidence_ref(self) -> None:
        ref = _ref("evidence:demo")
        object.__setattr__(ref, "value", "evidence:ghp_abcdefghijklmnopqrstuvwxyz1234")
        result = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-000000000013"),
            directive=CiboExecutiveDirectiveKind.ABSTAIN,
            reasoning_mode=CiboReasoningMode.FAST,
            subject_code="subject-demo",
            synthesized_at=_NOW,
            evidence_refs=(ref,),
            uncertainty=_insufficient_uncertainty(),
        )
        assert isinstance(result, Failure)
        assert isinstance(result.error, CiboExecutiveBrainValidationError)


class TestSynthesisRevalidationEquivalence:
    def test_revalidate_rejects_directive_mutated_to_question(self) -> None:
        synthesis = _synthesize()
        object.__setattr__(synthesis, "directive", CiboExecutiveDirectiveKind.QUESTION)
        with pytest.raises(CiboExecutiveBrainValidationError):
            synthesis.revalidate()

    def test_revalidate_rejects_recommend_without_recommendation(self) -> None:
        synthesis = _synthesize()
        object.__setattr__(synthesis, "recommendation", None)
        with pytest.raises(CiboExecutiveBrainValidationError):
            synthesis.revalidate()

    def test_secret_subject_code_rejected(self) -> None:
        result = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-0000000000cc"),
            directive=CiboExecutiveDirectiveKind.DEFER,
            reasoning_mode=CiboReasoningMode.HIGH,
            subject_code="sk-abcdefghijklmnop",
            synthesized_at=_NOW,
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=_insufficient_uncertainty(),
        )
        assert isinstance(result, Failure)
        assert isinstance(result.error, CiboExecutiveBrainValidationError)


class TestTimezoneMetamorphism:
    def test_synthesis_logical_values_identical_across_offsets(self) -> None:
        utc = datetime(2026, 8, 9, 5, 0, tzinfo=UTC)
        est = datetime(2026, 8, 9, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        left = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-0000000000dd"),
            directive=CiboExecutiveDirectiveKind.DEFER,
            reasoning_mode=CiboReasoningMode.HIGH,
            subject_code="subject-demo",
            synthesized_at=utc,
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=_insufficient_uncertainty(),
        )
        right = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-0000000000dd"),
            directive=CiboExecutiveDirectiveKind.DEFER,
            reasoning_mode=CiboReasoningMode.HIGH,
            subject_code="subject-demo",
            synthesized_at=est,
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=_insufficient_uncertainty(),
        )
        assert isinstance(left, Success) and isinstance(right, Success)
        assert left.value.logical_values() == right.value.logical_values()

    def test_synthesis_distinct_instants_stay_distinct(self) -> None:
        left = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-0000000000ee"),
            directive=CiboExecutiveDirectiveKind.DEFER,
            reasoning_mode=CiboReasoningMode.HIGH,
            subject_code="subject-demo",
            synthesized_at=datetime(2026, 8, 9, 5, 0, tzinfo=UTC),
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=_insufficient_uncertainty(),
        )
        right = _BRAIN.synthesize(
            synthesis_id=UUID("70000000-0000-0000-0000-0000000000ee"),
            directive=CiboExecutiveDirectiveKind.DEFER,
            reasoning_mode=CiboReasoningMode.HIGH,
            subject_code="subject-demo",
            synthesized_at=datetime(2026, 8, 9, 5, 1, tzinfo=UTC),
            evidence_refs=(_ref("evidence:demo"),),
            uncertainty=_insufficient_uncertainty(),
        )
        assert isinstance(left, Success) and isinstance(right, Success)
        assert left.value.logical_values() != right.value.logical_values()
