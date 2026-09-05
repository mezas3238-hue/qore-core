from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCapabilityProfileError,
    CiboCertificationState,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboLabEvidenceStage,
    CiboOperatingAction,
    CiboTraderCapabilityProfile,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class CiboDevelopmentReviewError(InfrastructureError):
    """Base error for the deterministic CIBO Trader Development Director review."""

    __slots__ = ()


class CiboDevelopmentReviewValidationError(CiboDevelopmentReviewError):
    """A development review input violates a deterministic review invariant."""

    __slots__ = ()


class CiboDevelopmentReviewBlockedError(CiboDevelopmentReviewError):
    """Fail-closed result when a review cannot safely produce a recommendation."""

    __slots__ = ()


class CiboDevelopmentRecommendation(StrEnum):
    """Non-authoritative development recommendation; it mutates nothing."""

    CONTINUE_CURRICULUM = "continue-curriculum"
    MORE_EVIDENCE_REQUIRED = "more-evidence-required"
    RETRAIN_RETURN_TO_LAB = "retrain-return-to-lab"
    RECOMMEND_PROMOTION = "recommend-promotion"
    RECOMMEND_REJECTION = "recommend-rejection"
    RECOMMEND_SUSPENSION_REVIEW = "recommend-suspension-review"


class CiboDevelopmentReason(StrEnum):
    CURRICULUM_INCOMPLETE = "curriculum-incomplete"
    EVIDENCE_INSUFFICIENT = "evidence-insufficient"
    EVIDENCE_STALE = "evidence-stale"
    MISSING_LAB_STAGE = "missing-lab-stage"
    IDENTITY_MISMATCH = "identity-mismatch"
    CONFIG_MISMATCH = "config-mismatch"
    CONTRADICTORY_EVIDENCE = "contradictory-evidence"
    UNSUPPORTED_QUANTITATIVE_CLAIM = "unsupported-quantitative-claim"
    REJECTED_STATE = "rejected-state"
    SUSPENDED_OR_DEGRADED = "suspended-or-degraded"
    EVIDENCE_COMPLETE = "evidence-complete"


_REQUIRED_PROMOTION_STAGES = frozenset(
    {
        CiboLabEvidenceStage.REPLAY,
        CiboLabEvidenceStage.FAST_FORWARD,
        CiboLabEvidenceStage.OOS,
        CiboLabEvidenceStage.ECONOMIC,
        CiboLabEvidenceStage.RISK,
    }
)

# Operating actions that block or return a Trader to Lab. A profile carrying any
# of these cannot coherently receive a promotion recommendation.
_BLOCKING_OPERATING_ACTIONS = frozenset(
    {
        CiboOperatingAction.SUSPEND,
        CiboOperatingAction.RETURN_TO_LAB,
    }
)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboDevelopmentReviewValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboDevelopmentReviewValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class CiboDevelopmentReview:
    """Immutable development recommendation with explicit reasons and evidence.

    This value is advisory only: it never mutates the candidate profile and it
    creates no promotion authority.
    """

    profile: CiboTraderCapabilityProfile
    recommendation: CiboDevelopmentRecommendation
    reasons: tuple[CiboDevelopmentReason, ...]
    evidence_refs: tuple[CiboEvidenceRef, ...]
    reviewed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.profile, CiboTraderCapabilityProfile):
            raise CiboDevelopmentReviewValidationError(
                "development review requires CiboTraderCapabilityProfile"
            )
        try:
            CiboTraderCapabilityProfile.__post_init__(self.profile)
        except CiboCapabilityProfileError as error:
            raise CiboDevelopmentReviewValidationError(
                "development review profile failed revalidation"
            ) from error
        if not isinstance(self.recommendation, CiboDevelopmentRecommendation):
            raise CiboDevelopmentReviewValidationError(
                "development review requires CiboDevelopmentRecommendation"
            )
        state = self.profile.certification_state
        if (
            state is CiboCertificationState.REJECTED
            and self.recommendation is not CiboDevelopmentRecommendation.RECOMMEND_REJECTION
        ):
            raise CiboDevelopmentReviewValidationError(
                "rejected profile must carry rejection recommendation"
            )
        if (
            state in (CiboCertificationState.SUSPENDED, CiboCertificationState.DEGRADED)
            and self.recommendation
            is not CiboDevelopmentRecommendation.RECOMMEND_SUSPENSION_REVIEW
        ):
            raise CiboDevelopmentReviewValidationError(
                "suspended/degraded profile must carry suspension-review recommendation"
            )
        if self.recommendation is CiboDevelopmentRecommendation.RECOMMEND_PROMOTION:
            if state not in (
                CiboCertificationState.EVIDENCE_COLLECTED,
                CiboCertificationState.PROMOTION_RECOMMENDED,
            ):
                raise CiboDevelopmentReviewValidationError(
                    "promotion recommendation requires promotion-capable profile state"
                )
            if self.profile.freshness.state is not CiboEvidenceFreshnessState.CURRENT:
                raise CiboDevelopmentReviewValidationError(
                    "promotion recommendation requires current evidence"
                )
            available = {item.stage for item in self.profile.certified_lab_evidence}
            if not _REQUIRED_PROMOTION_STAGES.issubset(available):
                raise CiboDevelopmentReviewValidationError(
                    "promotion recommendation requires the immutable promotion stage floor"
                )
            if any(
                condition.action in _BLOCKING_OPERATING_ACTIONS
                for condition in self.profile.operating_conditions
            ):
                raise CiboDevelopmentReviewValidationError(
                    "promotion recommendation contradicts blocking operating evidence"
                )
        if not isinstance(self.reasons, tuple) or not self.reasons or any(
            not isinstance(reason, CiboDevelopmentReason) for reason in self.reasons
        ):
            raise CiboDevelopmentReviewValidationError(
                "development review requires a non-empty tuple of CiboDevelopmentReason"
            )
        if len(set(self.reasons)) != len(self.reasons):
            raise CiboDevelopmentReviewValidationError(
                "development review reasons must not contain duplicates"
            )
        object.__setattr__(
            self,
            "reasons",
            tuple(sorted(self.reasons, key=lambda reason: reason.value)),
        )
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(item, CiboEvidenceRef) for item in self.evidence_refs
        ):
            raise CiboDevelopmentReviewValidationError(
                "development review evidence refs must be a tuple of CiboEvidenceRef"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise CiboDevelopmentReviewValidationError(
                "development review evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )
        _validate_timestamp(self.reviewed_at, field_name="reviewed_at")
        if self.reviewed_at < self.profile.freshness.as_of:
            raise CiboDevelopmentReviewValidationError(
                "development review cannot predate profile evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.profile.logical_values(),
            self.recommendation.value,
            tuple(reason.value for reason in self.reasons),
            tuple(item.logical_values() for item in self.evidence_refs),
            self.reviewed_at.isoformat(),
        )


def review_capability_profile(
    profile: CiboTraderCapabilityProfile,
    *,
    reviewed_at: datetime,
    required_stages: frozenset[CiboLabEvidenceStage] = _REQUIRED_PROMOTION_STAGES,
    expected_identity: ResearchDecisionEvaluatorIdentity | None = None,
    expected_config_fingerprint: str | None = None,
) -> Result[CiboDevelopmentReview, CiboDevelopmentReviewError]:
    """Produce a deterministic evidence-bound development recommendation.

    The recommendation is advisory and non-authoritative. It never mutates the
    candidate profile and can never grant promotion authority on its own.
    """
    if not isinstance(profile, CiboTraderCapabilityProfile):
        return Failure(
            CiboDevelopmentReviewValidationError(
                "development review requires CiboTraderCapabilityProfile"
            )
        )
    try:
        CiboTraderCapabilityProfile.__post_init__(profile)
    except CiboCapabilityProfileError:
        return Failure(
            CiboDevelopmentReviewBlockedError(
                "retained trader profile failed revalidation; review blocked"
            )
        )
    try:
        _validate_timestamp(reviewed_at, field_name="reviewed_at")
    except CiboDevelopmentReviewError as error:
        return Failure(error)
    if reviewed_at < profile.freshness.as_of:
        return Failure(
            CiboDevelopmentReviewValidationError(
                "development review cannot predate profile evidence"
            )
        )
    if not isinstance(required_stages, frozenset) or any(
        not isinstance(stage, CiboLabEvidenceStage) for stage in required_stages
    ):
        return Failure(
            CiboDevelopmentReviewValidationError(
                "required_stages must be a frozenset of CiboLabEvidenceStage"
            )
        )
    if not _REQUIRED_PROMOTION_STAGES.issubset(required_stages):
        return Failure(
            CiboDevelopmentReviewValidationError(
                "required_stages cannot weaken the immutable promotion stage floor"
            )
        )

    # Fail closed: exact identity/version/config binding.
    if expected_identity is not None:
        if not isinstance(expected_identity, ResearchDecisionEvaluatorIdentity):
            return Failure(
                CiboDevelopmentReviewValidationError(
                    "expected_identity must be ResearchDecisionEvaluatorIdentity"
                )
            )
        if expected_identity != profile.trader_identity:
            return Failure(
                CiboDevelopmentReviewBlockedError(
                    "trader identity/version mismatch; review blocked"
                )
            )
    if expected_config_fingerprint is not None:
        if (
            not isinstance(expected_config_fingerprint, str)
            or fullmatch(r"[0-9a-f]{64}", expected_config_fingerprint) is None
        ):
            return Failure(
                CiboDevelopmentReviewValidationError(
                    "expected_config_fingerprint must be 64 lowercase hex"
                )
            )
        if expected_config_fingerprint != profile.config_fingerprint.value:
            return Failure(
                CiboDevelopmentReviewBlockedError(
                    "trader config fingerprint mismatch; review blocked"
                )
            )

    # Fail closed: unsupported quantitative claims (defense in depth).
    certified_refs = {item.ref.value for item in profile.certified_lab_evidence}
    for metric in profile.economic_metrics:
        if metric.evidence_ref.value not in certified_refs:
            return Failure(
                CiboDevelopmentReviewBlockedError(
                    "economic metric lacks certified evidence; review blocked"
                )
            )

    state = profile.certification_state
    recommendation: CiboDevelopmentRecommendation
    reasons: tuple[CiboDevelopmentReason, ...]
    if state is CiboCertificationState.REJECTED:
        recommendation = CiboDevelopmentRecommendation.RECOMMEND_REJECTION
        reasons = (CiboDevelopmentReason.REJECTED_STATE,)
    elif state in (
        CiboCertificationState.SUSPENDED,
        CiboCertificationState.DEGRADED,
    ):
        recommendation = CiboDevelopmentRecommendation.RECOMMEND_SUSPENSION_REVIEW
        reasons = (CiboDevelopmentReason.SUSPENDED_OR_DEGRADED,)
    elif profile.freshness.state is CiboEvidenceFreshnessState.STALE:
        recommendation = CiboDevelopmentRecommendation.RETRAIN_RETURN_TO_LAB
        reasons = (CiboDevelopmentReason.EVIDENCE_STALE,)
    elif profile.freshness.state in (
        CiboEvidenceFreshnessState.INSUFFICIENT,
        CiboEvidenceFreshnessState.UNKNOWN,
    ):
        recommendation = CiboDevelopmentRecommendation.MORE_EVIDENCE_REQUIRED
        reasons = (CiboDevelopmentReason.EVIDENCE_INSUFFICIENT,)
    else:
        available = {item.stage for item in profile.certified_lab_evidence}
        missing = required_stages - available
        if missing:
            if state in (
                CiboCertificationState.UNQUALIFIED,
                CiboCertificationState.IN_CURRICULUM,
            ):
                recommendation = CiboDevelopmentRecommendation.CONTINUE_CURRICULUM
                reasons = (
                    CiboDevelopmentReason.CURRICULUM_INCOMPLETE,
                    CiboDevelopmentReason.MISSING_LAB_STAGE,
                )
            else:
                recommendation = CiboDevelopmentRecommendation.MORE_EVIDENCE_REQUIRED
                reasons = (CiboDevelopmentReason.MISSING_LAB_STAGE,)
        elif state in (
            CiboCertificationState.UNQUALIFIED,
            CiboCertificationState.IN_CURRICULUM,
        ):
            recommendation = CiboDevelopmentRecommendation.CONTINUE_CURRICULUM
            reasons = (CiboDevelopmentReason.CURRICULUM_INCOMPLETE,)
        elif state in (
            CiboCertificationState.EVIDENCE_COLLECTED,
            CiboCertificationState.PROMOTION_RECOMMENDED,
        ):
            recommendation = CiboDevelopmentRecommendation.RECOMMEND_PROMOTION
            reasons = (CiboDevelopmentReason.EVIDENCE_COMPLETE,)
        else:
            recommendation = CiboDevelopmentRecommendation.MORE_EVIDENCE_REQUIRED
            reasons = (CiboDevelopmentReason.EVIDENCE_INSUFFICIENT,)

    # Fail closed: a blocking operating condition cannot coherently recommend promotion.
    if (
        recommendation is CiboDevelopmentRecommendation.RECOMMEND_PROMOTION
        and any(
            condition.action in _BLOCKING_OPERATING_ACTIONS
            for condition in profile.operating_conditions
        )
    ):
        return Failure(
            CiboDevelopmentReviewBlockedError(
                "contradictory operating/promotion evidence; review blocked"
            )
        )

    evidence_refs = tuple(
        sorted({item.ref for item in profile.certified_lab_evidence}, key=lambda r: r.value)
    )
    try:
        return Success(
            CiboDevelopmentReview(
                profile=profile,
                recommendation=recommendation,
                reasons=reasons,
                evidence_refs=evidence_refs,
                reviewed_at=reviewed_at,
            )
        )
    except CiboDevelopmentReviewError as error:
        return Failure(error)
