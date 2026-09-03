from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboCognitiveValidationError,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboDeliberationRole,
    CiboEpistemicClaim,
    CiboEpistemicState,
    CiboFormalRecommendation,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)


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


def _recommendation(
    *,
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...] = (_ref("evidence:exposure"),),
    issued_at: datetime = _NOW,
    summary: str = "Review portfolio exposure",
) -> CiboFormalRecommendation:
    return CiboFormalRecommendation(
        recommendation_id=UUID("30000000-0000-0000-0000-000000000001"),
        recommendation_code="cibo.review-portfolio",
        reasoning_mode=CiboReasoningMode.HIGH,
        summary=summary,
        evidence_refs=evidence_refs,
        uncertainty=_bounded_uncertainty(),
        issued_at=issued_at,
    )


class TestReasoningModesAndEpistemicStates:
    def test_reasoning_modes_are_policy_semantics_not_models(self) -> None:
        assert {mode.value for mode in CiboReasoningMode} == {
            "fast",
            "high",
            "max",
            "council-adversarial",
        }
        for mode in CiboReasoningMode:
            assert "gpt" not in mode.value
            assert "claude" not in mode.value
            assert "model" not in mode.value

    def test_epistemic_states_exclude_authorized_action(self) -> None:
        assert CiboEpistemicState.FORMAL_RECOMMENDATION.value == "formal-recommendation"
        assert not hasattr(CiboEpistemicState, "AUTHORIZED_ACTION")
        assert not hasattr(CiboEpistemicState, "EXECUTION")


class TestConfidence:
    def test_confidence_rejects_bool_level_laundering(self) -> None:
        with pytest.raises(CiboCognitiveValidationError):
            CiboConfidence(level=True, evidence_refs=(_ref("evidence:x"),))  # type: ignore[arg-type]

    def test_confidence_requires_backing_evidence(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="evidence"):
            CiboConfidence(level=CiboConfidenceLevel.HIGH, evidence_refs=())

    def test_confidence_canonicalizes_evidence_order(self) -> None:
        left = CiboConfidence(
            level=CiboConfidenceLevel.LOW,
            evidence_refs=(_ref("evidence:a"), _ref("evidence:b")),
        )
        right = CiboConfidence(
            level=CiboConfidenceLevel.LOW,
            evidence_refs=(_ref("evidence:b"), _ref("evidence:a")),
        )
        assert left == right
        assert left.logical_values() == right.logical_values()


class TestEvidenceRef:
    def test_evidence_ref_rejects_secret_material(self) -> None:
        for bad in ("evidence:token=abc", "evidence:bearer xyz", "secret=value"):
            with pytest.raises(CiboCognitiveValidationError):
                CiboCognitiveEvidenceRef(bad)

    @pytest.mark.parametrize(
        "witness",
        (
            "evidence:sk-abcdefghijklmnop",
            "evidence:ghp_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:gho_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:ghu_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:ghs_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:ghr_abcdefghijklmnopqrstuvwxyz1234",
            "evidence:xoxb-123456789012-abcdefghijklmnopqrstuvwxyz",
            "evidence:xoxp-123456789012-abcdefghijklmnopqrstuvwxyz",
            "evidence:xoxa-123456789012-abcdefghijklmnopqrstuvwxyz",
            "evidence:xoxr-123456789012-abcdefghijklmnopqrstuvwxyz",
            "evidence:xoxs-123456789012-abcdefghijklmnopqrstuvwxyz",
        ),
    )
    def test_evidence_ref_rejects_structural_secrets(self, witness: str) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            CiboCognitiveEvidenceRef(witness)

    def test_evidence_ref_revalidate_rejects_reflective_secret(self) -> None:
        ref = _ref("evidence:demo")
        object.__setattr__(ref, "value", "evidence:xoxb-123456789012-abcdefghijklmnopqrstuvwxyz")
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            ref.revalidate()

    def test_evidence_ref_accepts_bare_field_name_mention(self) -> None:
        assert _ref("evidence:client_secret_demo").value == "evidence:client_secret_demo"

    def test_evidence_ref_rejects_non_string(self) -> None:
        with pytest.raises(CiboCognitiveValidationError):
            CiboCognitiveEvidenceRef(True)  # type: ignore[arg-type]


class TestUncertainty:
    def test_bounded_confidence_requires_confidence(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="confidence"):
            CiboUncertainty(kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE)

    def test_competing_hypotheses_requires_details(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="detail"):
            CiboUncertainty(kind=CiboUncertaintyKind.COMPETING_HYPOTHESES)

    def test_insufficient_evidence_is_first_class(self) -> None:
        uncertainty = _insufficient_uncertainty()
        assert uncertainty.kind is CiboUncertaintyKind.INSUFFICIENT_EVIDENCE
        assert uncertainty.confidence is None


class TestEpistemicClaim:
    def test_claim_rejects_formal_recommendation_state(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="CiboFormalRecommendation"):
            CiboEpistemicClaim(
                claim_id=UUID("30000000-0000-0000-0000-000000000010"),
                epistemic_state=CiboEpistemicState.FORMAL_RECOMMENDATION,
                reasoning_mode=CiboReasoningMode.FAST,
                content_code="cibo.claim",
                evidence_refs=(_ref("evidence:x"),),
                uncertainty=_insufficient_uncertainty(),
            )

    def test_claim_requires_exact_uuid(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="UUID"):
            CiboEpistemicClaim(
                claim_id="not-a-uuid",  # type: ignore[arg-type]
                epistemic_state=CiboEpistemicState.OBSERVATION,
                reasoning_mode=CiboReasoningMode.FAST,
                content_code="cibo.claim",
                evidence_refs=(_ref("evidence:x"),),
                uncertainty=_insufficient_uncertainty(),
            )

    def test_claim_rejects_bool_epistemic_state(self) -> None:
        with pytest.raises(CiboCognitiveValidationError):
            CiboEpistemicClaim(
                claim_id=UUID("30000000-0000-0000-0000-000000000010"),
                epistemic_state=True,  # type: ignore[arg-type]
                reasoning_mode=CiboReasoningMode.FAST,
                content_code="cibo.claim",
                evidence_refs=(_ref("evidence:x"),),
                uncertainty=_insufficient_uncertainty(),
            )


class TestFormalRecommendation:
    def test_recommendation_requires_evidence(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="evidence"):
            _recommendation(evidence_refs=())

    def test_recommendation_rejects_naive_datetime(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="timezone"):
            _recommendation(issued_at=datetime(2026, 8, 9, 0, 0))

    def test_recommendation_rejects_secret_summary(self) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            _recommendation(summary="token=abc123 leaked")

    @pytest.mark.parametrize(
        "witness",
        (
            "sk-proj-abcdefghijklmnopqrstuvwxyz123456",
            "AKIAIOSFODNN7EXAMPLE",
            "ghp_abcdefghijklmnopqrstuvwxyz1234",
            "gho_abcdefghijklmnopqrstuvwxyz1234",
            "ghu_abcdefghijklmnopqrstuvwxyz1234",
            "ghs_abcdefghijklmnopqrstuvwxyz1234",
            "ghr_abcdefghijklmnopqrstuvwxyz1234",
            "xoxb-123456789012-abcdefghijklmnopqrstuvwxyz",
            "xoxp-123456789012-abcdefghijklmnopqrstuvwxyz",
            "xoxa-123456789012-abcdefghijklmnopqrstuvwxyz",
            "xoxr-123456789012-abcdefghijklmnopqrstuvwxyz",
            "xoxs-123456789012-abcdefghijklmnopqrstuvwxyz",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature",
            "https://alice:correcthorsebatterystaple@example.com/x",
            "client_secret=abcdefghijklmnopqrstuvwxyz123456",
            "Authorization: Bearer abcdef1234567890",
            "-----BEGIN PRIVATE KEY-----",
        ),
    )
    def test_recommendation_rejects_structural_secret_summary(self, witness: str) -> None:
        with pytest.raises(CiboCognitiveValidationError, match="sensitive"):
            _recommendation(summary=witness)

    def test_revalidate_rejects_injected_structural_secret(self) -> None:
        recommendation = _recommendation()
        object.__setattr__(
            recommendation, "summary", "sk-proj-abcdefghijklmnopqrstuvwxyz123456"
        )
        with pytest.raises(CiboCognitiveValidationError):
            recommendation.revalidate()

    def test_recommendation_has_no_authority_fields(self) -> None:
        recommendation = _recommendation()
        for absent in (
            "order",
            "intent",
            "provider",
            "instrument",
            "quantity",
            "account",
            "authorization",
            "promotion",
        ):
            assert not hasattr(recommendation, absent)

    def test_recommendation_epistemic_state_is_never_an_action(self) -> None:
        assert _recommendation().epistemic_state is CiboEpistemicState.FORMAL_RECOMMENDATION

    def test_recommendation_deterministic(self) -> None:
        assert _recommendation().logical_values() == _recommendation().logical_values()

    def test_revalidate_detects_tampered_nested_confidence(self) -> None:
        recommendation = _recommendation()
        object.__setattr__(recommendation.uncertainty, "confidence", object())
        with pytest.raises(CiboCognitiveValidationError):
            recommendation.revalidate()

    def test_revalidate_detects_tampered_evidence_ref(self) -> None:
        recommendation = _recommendation()
        object.__setattr__(recommendation.evidence_refs[0], "value", "secret=injected")
        with pytest.raises(CiboCognitiveValidationError):
            recommendation.revalidate()


class TestDeliberationRole:
    def test_role_is_generic_faculty_identity(self) -> None:
        role = CiboDeliberationRole("market-strategist")
        assert role.value == "market-strategist"
        assert CiboDeliberationRole("risk-aware-critic").value == "risk-aware-critic"

    def test_role_rejects_non_canonical_code(self) -> None:
        with pytest.raises(CiboCognitiveValidationError):
            CiboDeliberationRole("Market Strategist")
