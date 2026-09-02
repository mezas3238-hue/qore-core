from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEconomicMetric,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboLabEvidenceRef,
    CiboLabEvidenceStage,
    CiboOperatingAction,
    CiboOperatingCondition,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.cibo_trader_development_review import (
    CiboDevelopmentReason,
    CiboDevelopmentRecommendation,
    CiboDevelopmentReview,
    CiboDevelopmentReviewBlockedError,
    review_capability_profile,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)

_PROMOTION_STAGES = (
    CiboLabEvidenceRef(CiboLabEvidenceStage.REPLAY, CiboEvidenceRef("evidence:replay")),
    CiboLabEvidenceRef(
        CiboLabEvidenceStage.FAST_FORWARD,
        CiboEvidenceRef("evidence:fast-forward"),
    ),
    CiboLabEvidenceRef(CiboLabEvidenceStage.OOS, CiboEvidenceRef("evidence:oos")),
    CiboLabEvidenceRef(
        CiboLabEvidenceStage.ECONOMIC,
        CiboEvidenceRef("evidence:economic"),
    ),
    CiboLabEvidenceRef(CiboLabEvidenceStage.RISK, CiboEvidenceRef("evidence:risk")),
)


def _identity(suffix: str = "vt01") -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _fingerprint(n: int = 1) -> CiboTraderConfigFingerprint:
    return CiboTraderConfigFingerprint(f"{n:064x}")


def _profile(
    *,
    state: CiboCertificationState = CiboCertificationState.EVIDENCE_COLLECTED,
    freshness_state: CiboEvidenceFreshnessState = CiboEvidenceFreshnessState.CURRENT,
    stages: tuple[CiboLabEvidenceRef, ...] = _PROMOTION_STAGES,
    operating_conditions: tuple[CiboOperatingCondition, ...] = (),
    suffix: str = "vt01",
    fingerprint: int = 1,
) -> CiboTraderCapabilityProfile:
    result = build_cibo_trader_capability_profile(
        trader_identity=_identity(suffix),
        config_fingerprint=_fingerprint(fingerprint),
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        certified_lab_evidence=stages,
        economic_metrics=(
            CiboEconomicMetric(
                metric_code="net-sharpe",
                value=Decimal("1.5"),
                evidence_ref=CiboEvidenceRef("evidence:economic"),
            ),
        )
        if any(s.stage is CiboLabEvidenceStage.ECONOMIC for s in stages)
        else (),
        operating_conditions=operating_conditions,
        certification_state=state,
        freshness=CiboEvidenceFreshness(state=freshness_state, as_of=_NOW),
    )
    assert isinstance(result, Success)
    return result.value


def test_recommend_promotion_with_complete_evidence() -> None:
    profile = _profile()
    result = review_capability_profile(profile, reviewed_at=_NOW)
    assert isinstance(result, Success)
    review: CiboDevelopmentReview = result.value
    assert review.recommendation is CiboDevelopmentRecommendation.RECOMMEND_PROMOTION
    assert CiboDevelopmentReason.EVIDENCE_COMPLETE in review.reasons


def test_continue_curriculum_when_incomplete() -> None:
    profile = _profile(
        state=CiboCertificationState.IN_CURRICULUM,
        stages=(),
    )
    result = review_capability_profile(profile, reviewed_at=_NOW)
    assert isinstance(result, Success)
    assert result.value.recommendation is CiboDevelopmentRecommendation.CONTINUE_CURRICULUM


def test_more_evidence_required_when_missing_stage() -> None:
    profile = _profile(
        stages=(_PROMOTION_STAGES[0], _PROMOTION_STAGES[1]),
    )
    result = review_capability_profile(profile, reviewed_at=_NOW)
    assert isinstance(result, Success)
    assert (
        result.value.recommendation
        is CiboDevelopmentRecommendation.MORE_EVIDENCE_REQUIRED
    )
    assert CiboDevelopmentReason.MISSING_LAB_STAGE in result.value.reasons


def test_stale_evidence_returns_to_lab() -> None:
    profile = _profile(freshness_state=CiboEvidenceFreshnessState.STALE)
    result = review_capability_profile(profile, reviewed_at=_NOW)
    assert isinstance(result, Success)
    assert (
        result.value.recommendation is CiboDevelopmentRecommendation.RETRAIN_RETURN_TO_LAB
    )


def test_rejected_state_returns_rejection() -> None:
    profile = _profile(state=CiboCertificationState.REJECTED)
    result = review_capability_profile(profile, reviewed_at=_NOW)
    assert isinstance(result, Success)
    assert result.value.recommendation is CiboDevelopmentRecommendation.RECOMMEND_REJECTION


def test_suspended_state_returns_suspension_review() -> None:
    profile = _profile(state=CiboCertificationState.SUSPENDED)
    result = review_capability_profile(profile, reviewed_at=_NOW)
    assert isinstance(result, Success)
    assert (
        result.value.recommendation
        is CiboDevelopmentRecommendation.RECOMMEND_SUSPENSION_REVIEW
    )


def test_identity_mismatch_blocked() -> None:
    profile = _profile()
    result = review_capability_profile(
        profile,
        reviewed_at=_NOW,
        expected_identity=_identity("vt02"),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboDevelopmentReviewBlockedError)


def test_config_fingerprint_mismatch_blocked() -> None:
    profile = _profile()
    result = review_capability_profile(
        profile,
        reviewed_at=_NOW,
        expected_config_fingerprint=f"{2:064x}",
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboDevelopmentReviewBlockedError)


def test_contradictory_suspend_promotion_blocked() -> None:
    profile = _profile(
        state=CiboCertificationState.PROMOTION_RECOMMENDED,
        operating_conditions=(
            CiboOperatingCondition(
                action=CiboOperatingAction.SUSPEND,
                reason_code="evidence-degraded",
            ),
        ),
    )
    result = review_capability_profile(profile, reviewed_at=_NOW)
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboDevelopmentReviewBlockedError)


def test_promotion_laundering_impossible_for_suspended() -> None:
    profile = _profile(state=CiboCertificationState.SUSPENDED)
    result = review_capability_profile(profile, reviewed_at=_NOW)
    assert isinstance(result, Success)
    assert result.value.recommendation is not CiboDevelopmentRecommendation.RECOMMEND_PROMOTION


def test_review_never_mutates_profile() -> None:
    profile = _profile()
    before = profile.logical_values()
    result = review_capability_profile(profile, reviewed_at=_NOW)
    assert isinstance(result, Success)
    assert profile.logical_values() == before
    assert result.value.profile == profile


def test_review_blocks_unsupported_quantitative_claim() -> None:
    profile = _profile()
    corrupted = object.__new__(CiboTraderCapabilityProfile)
    for field in dataclasses.fields(CiboTraderCapabilityProfile):
        if field.name == "economic_metrics":
            object.__setattr__(
                corrupted,
                field.name,
                (
                    CiboEconomicMetric(
                        metric_code="net-sharpe",
                        value=Decimal("9.9"),
                        evidence_ref=CiboEvidenceRef("evidence:not-certified"),
                    ),
                ),
            )
        else:
            object.__setattr__(corrupted, field.name, getattr(profile, field.name))
    result = review_capability_profile(corrupted, reviewed_at=_NOW)
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboDevelopmentReviewBlockedError)


def test_review_cannot_predate_evidence() -> None:
    profile = _profile()
    result = review_capability_profile(
        profile,
        reviewed_at=datetime(2026, 8, 8, 0, 0, tzinfo=UTC),
    )
    assert isinstance(result, Failure)
