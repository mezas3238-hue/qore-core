"""Robustness-owned Trader Lab stress review and authenticity issuance.

The Trader Lab remains consume/verify-only for the governed STRESS stage.  This
module lives outside ``qore.infrastructure.trader_lab`` and owns one deterministic
cost-perturbation review over exact research return evidence.  A policy must be
pre-registered before the first retained return observation, and the review
recomputes stressed metrics from the complete evidence tree before any qualifying
proof can be issued.

This authority can qualify only ``STRESS_REVIEW``.  It grants no Risk, CIBO,
independent-validation, execution, Production, LIVE, or real-capital authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceStatisticsSnapshot,
)
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding
from qore.infrastructure.trader_lab.governed_gate import (
    TraderLabGovernedAuthenticityProof,
    TraderLabGovernedAuthorityKind,
    TraderLabGovernedDecision,
    TraderLabGovernedGate,
    TraderLabGovernedGateEvidence,
    TraderLabGovernedGateEvidenceId,
    compute_trader_lab_governed_authenticity_proof_fingerprint,
    compute_trader_lab_governed_gate_fingerprint,
    verify_governed_gate_evidence,
)
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabLifecycle,
    TraderLabState,
    validate_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.robustness import (
    TraderLabRobustnessFamily,
    TraderLabStressEvidence,
    TraderLabStressEvidenceId,
    TraderLabStressStatus,
    build_trader_lab_stress_evidence,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceReference,
    TraderLabStage,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_ROBUSTNESS_AUTHORITY_ID = UUID("76000000-0000-0000-0000-000000000001")
_ROBUSTNESS_AUTHORITY_NAME = "qore-robustness-trader-lab-authority-v1"
_POLICY_RE = r"[a-z][a-z0-9._-]*"
_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)
_REQUIRED_COMPLETED_STAGES = MANDATORY_STAGES[
    : MANDATORY_STAGES.index(TraderLabStage.STRESS)
]


class RobustnessTraderLabAuthorityError(InfrastructureError):
    """Base error for the Robustness-owned Trader Lab authority."""

    __slots__ = ()


class RobustnessTraderLabAuthorityValidationError(RobustnessTraderLabAuthorityError):
    """Stress-review inputs violate exact binding or policy invariants."""

    __slots__ = ()


class RobustnessTraderLabAuthorityBlockedError(RobustnessTraderLabAuthorityError):
    """Robustness cannot issue a qualifying STRESS review."""

    __slots__ = ()


class RobustnessTraderLabReviewDecision(StrEnum):
    """Closed Robustness review outcomes."""

    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class RobustnessTraderLabPolicy:
    """Pre-registered methodology-neutral cost-perturbation policy."""

    policy_id: str
    scenario: str
    return_haircut: Decimal
    min_sample_size: int
    min_stressed_mean_return: Decimal
    max_stressed_population_variance: Decimal
    registered_at: datetime

    def __post_init__(self) -> None:
        if type(self.policy_id) is not str or fullmatch(_POLICY_RE, self.policy_id) is None:
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness policy_id must use canonical lowercase syntax"
            )
        if type(self.scenario) is not str or fullmatch(_POLICY_RE, self.scenario) is None:
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness scenario must use canonical lowercase syntax"
            )
        for field_name, value in (
            ("return_haircut", self.return_haircut),
            ("min_stressed_mean_return", self.min_stressed_mean_return),
            (
                "max_stressed_population_variance",
                self.max_stressed_population_variance,
            ),
        ):
            if type(value) is not Decimal or not value.is_finite():
                raise RobustnessTraderLabAuthorityValidationError(
                    f"robustness {field_name} must be a finite Decimal"
                )
        if self.return_haircut < 0:
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness return_haircut must be non-negative"
            )
        if self.max_stressed_population_variance < 0:
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness max_stressed_population_variance must be non-negative"
            )
        if type(self.min_sample_size) is not int or self.min_sample_size < 2:
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness min_sample_size must be an int of at least two"
            )
        _validate_timestamp(self.registered_at, field_name="registered_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_id,
            self.scenario,
            format(self.return_haircut, "f"),
            self.min_sample_size,
            format(self.min_stressed_mean_return, "f"),
            format(self.max_stressed_population_variance, "f"),
            self.registered_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


def _derive_stressed_metrics(
    performance: ResearchPerformanceStatisticsSnapshot,
    policy: RobustnessTraderLabPolicy,
) -> tuple[Decimal, Decimal]:
    values = tuple(
        observation.return_rate - policy.return_haircut
        for observation in performance.observations
    )
    with localcontext(_DECIMAL128):
        denominator = Decimal(len(values))
        mean = sum(values, Decimal(0)) / denominator
        variance = (
            sum(((value - mean) * (value - mean) for value in values), Decimal(0))
            / denominator
        )
    return mean, variance


def _derive_decision(
    performance: ResearchPerformanceStatisticsSnapshot,
    policy: RobustnessTraderLabPolicy,
) -> tuple[RobustnessTraderLabReviewDecision, tuple[str, ...], Decimal, Decimal]:
    mean, variance = _derive_stressed_metrics(performance, policy)
    reasons: list[str] = []
    if performance.sample_size < policy.min_sample_size:
        reasons.append("sample_size_below_robustness_policy")
    if mean < policy.min_stressed_mean_return:
        reasons.append("stressed_mean_below_robustness_policy")
    if variance > policy.max_stressed_population_variance:
        reasons.append("stressed_variance_above_robustness_policy")
    if any(reason != "sample_size_below_robustness_policy" for reason in reasons):
        decision = RobustnessTraderLabReviewDecision.REJECTED
    elif reasons:
        decision = RobustnessTraderLabReviewDecision.DEFERRED
    else:
        decision = RobustnessTraderLabReviewDecision.APPROVED
    return decision, tuple(reasons), mean, variance


@dataclass(frozen=True, slots=True)
class RobustnessTraderLabReview:
    """Immutable cost-perturbation decision over one exact OOS candidate."""

    candidate: TraderLabCandidateBinding
    lifecycle: TraderLabLifecycle
    performance: ResearchPerformanceStatisticsSnapshot
    policy: RobustnessTraderLabPolicy
    decision: RobustnessTraderLabReviewDecision
    reasons: tuple[str, ...]
    stressed_mean_return: Decimal
    stressed_population_variance: Decimal
    reviewed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, TraderLabCandidateBinding):
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness review requires TraderLabCandidateBinding"
            )
        if not isinstance(self.lifecycle, TraderLabLifecycle):
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness review requires TraderLabLifecycle"
            )
        validate_trader_lab_lifecycle(self.lifecycle)
        if self.lifecycle.candidate != self.candidate:
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness lifecycle must bind the exact candidate"
            )
        if self.lifecycle.state is not TraderLabState.OOS_QUALIFIED:
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness review must consume the exact post-OOS lifecycle state"
            )
        if self.lifecycle.completed_stages != _REQUIRED_COMPLETED_STAGES:
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness review requires RESEARCH through OOS"
            )
        if not isinstance(self.performance, ResearchPerformanceStatisticsSnapshot):
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness review requires performance statistics"
            )
        self.performance.__post_init__()
        if self.performance.run != self.candidate.strategy_binding.run:
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness performance run must match the candidate run"
            )
        if not isinstance(self.policy, RobustnessTraderLabPolicy):
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness review requires RobustnessTraderLabPolicy"
            )
        self.policy.__post_init__()
        first_observed_at = min(
            item.observed_at for item in self.performance.observations
        )
        if self.policy.registered_at > first_observed_at:
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness policy must be registered before outcome evidence"
            )
        _validate_timestamp(self.reviewed_at, field_name="reviewed_at")
        if self.reviewed_at < max(
            self.lifecycle.qualifications[-1].qualified_at,
            self.performance.observed_at,
        ):
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness review cannot predate OOS or performance evidence"
            )
        expected_decision, expected_reasons, expected_mean, expected_variance = (
            _derive_decision(self.performance, self.policy)
        )
        if self.decision is not expected_decision or self.reasons != expected_reasons:
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness decision and reasons must equal the derived policy result"
            )
        if (
            self.stressed_mean_return != expected_mean
            or self.stressed_population_variance != expected_variance
        ):
            raise RobustnessTraderLabAuthorityValidationError(
                "robustness stressed metrics must equal the derived return evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.candidate.fingerprint.value,
            self.lifecycle.logical_values(),
            self.performance.logical_values(),
            self.policy.logical_values(),
            self.decision.value,
            self.reasons,
            format(self.stressed_mean_return, "f"),
            format(self.stressed_population_variance, "f"),
            self.reviewed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class RobustnessTraderLabIssuance:
    """Robustness stress result plus sealed, Lab-verified governed reference."""

    review: RobustnessTraderLabReview
    stress_evidence: TraderLabStressEvidence
    evidence: TraderLabGovernedGateEvidence
    proof: TraderLabGovernedAuthenticityProof
    reference: TraderLabEvidenceReference

    def __post_init__(self) -> None:
        if self.review.decision is not RobustnessTraderLabReviewDecision.APPROVED:
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness issuance requires an approved review"
            )
        if self.stress_evidence.status is not TraderLabStressStatus.QUALIFIED:
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness issuance requires qualified stress evidence"
            )
        if self.evidence.gate is not TraderLabGovernedGate.STRESS_REVIEW:
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness issuance must bind STRESS_REVIEW"
            )
        if self.proof.authority_kind is not TraderLabGovernedAuthorityKind.ROBUSTNESS:
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness issuance proof must be owned by ROBUSTNESS"
            )


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise RobustnessTraderLabAuthorityValidationError(
            f"robustness {field_name} must be timezone-aware"
        )


def review_trader_lab_candidate_robustness(
    lifecycle: TraderLabLifecycle,
    performance: ResearchPerformanceStatisticsSnapshot,
    *,
    policy: RobustnessTraderLabPolicy,
    reviewed_at: datetime,
) -> Result[RobustnessTraderLabReview, RobustnessTraderLabAuthorityError]:
    """Evaluate an exact post-OOS candidate under a pre-registered stress policy."""

    try:
        if not isinstance(lifecycle, TraderLabLifecycle):
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness review requires TraderLabLifecycle"
            )
        validate_trader_lab_lifecycle(lifecycle)
        if lifecycle.state is not TraderLabState.OOS_QUALIFIED:
            raise RobustnessTraderLabAuthorityBlockedError(
                "Robustness review is available only after OOS qualification"
            )
        if lifecycle.completed_stages != _REQUIRED_COMPLETED_STAGES:
            raise RobustnessTraderLabAuthorityBlockedError(
                "Robustness review requires all prior mandatory Lab stages"
            )
        if not isinstance(performance, ResearchPerformanceStatisticsSnapshot):
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness review requires ResearchPerformanceStatisticsSnapshot"
            )
        performance.__post_init__()
        if performance.run != lifecycle.candidate.strategy_binding.run:
            raise RobustnessTraderLabAuthorityBlockedError(
                "Robustness performance evidence does not bind the candidate run"
            )
        if not isinstance(policy, RobustnessTraderLabPolicy):
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness review requires RobustnessTraderLabPolicy"
            )
        policy.__post_init__()
        first_observed_at = min(item.observed_at for item in performance.observations)
        if policy.registered_at > first_observed_at:
            raise RobustnessTraderLabAuthorityBlockedError(
                "Robustness policy was not pre-registered before outcome evidence"
            )
        _validate_timestamp(reviewed_at, field_name="reviewed_at")
        decision, reasons, stressed_mean, stressed_variance = _derive_decision(
            performance,
            policy,
        )
        return Success(
            RobustnessTraderLabReview(
                candidate=lifecycle.candidate,
                lifecycle=lifecycle,
                performance=performance,
                policy=policy,
                decision=decision,
                reasons=reasons,
                stressed_mean_return=stressed_mean,
                stressed_population_variance=stressed_variance,
                reviewed_at=reviewed_at,
            )
        )
    except RobustnessTraderLabAuthorityError as error:
        return Failure(error)


def _authority_digest(
    review: RobustnessTraderLabReview,
    stress_evidence: TraderLabStressEvidence,
) -> TraderLabEvidenceDigest:
    payload = json.dumps(
        {
            "schema": "qore.robustness.trader_lab.authority.v1",
            "review": review.logical_values(),
            "stress_evidence": stress_evidence.logical_values(),
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return TraderLabEvidenceDigest(sha256(payload).hexdigest())


def _issued_proof(
    *,
    evidence: TraderLabGovernedGateEvidence,
    candidate: TraderLabCandidateBinding,
    issued_at: datetime,
) -> TraderLabGovernedAuthenticityProof:
    proof_fingerprint = compute_trader_lab_governed_authenticity_proof_fingerprint(
        evidence_fingerprint=evidence.fingerprint,
        candidate=candidate,
        gate=TraderLabGovernedGate.STRESS_REVIEW,
        authority_kind=TraderLabGovernedAuthorityKind.ROBUSTNESS,
        issuer_id=_ROBUSTNESS_AUTHORITY_ID,
        issued_at=issued_at,
    )
    proof = object.__new__(TraderLabGovernedAuthenticityProof)
    object.__setattr__(proof, "evidence_fingerprint", evidence.fingerprint)
    object.__setattr__(proof, "candidate", candidate)
    object.__setattr__(proof, "gate", TraderLabGovernedGate.STRESS_REVIEW)
    object.__setattr__(
        proof,
        "authority_kind",
        TraderLabGovernedAuthorityKind.ROBUSTNESS,
    )
    object.__setattr__(proof, "issuer_id", _ROBUSTNESS_AUTHORITY_ID)
    object.__setattr__(proof, "issued_at", issued_at)
    object.__setattr__(proof, "proof_fingerprint", proof_fingerprint)
    object.__setattr__(proof, "_issued", True)
    proof.__post_init__()
    return proof


def issue_robustness_trader_lab_approval(
    review: RobustnessTraderLabReview,
) -> Result[RobustnessTraderLabIssuance, RobustnessTraderLabAuthorityError]:
    """Issue and verify the Robustness-owned qualifying STRESS reference."""

    try:
        if not isinstance(review, RobustnessTraderLabReview):
            raise RobustnessTraderLabAuthorityValidationError(
                "Robustness issuance requires RobustnessTraderLabReview"
            )
        review.__post_init__()
        if review.decision is not RobustnessTraderLabReviewDecision.APPROVED:
            raise RobustnessTraderLabAuthorityBlockedError(
                "Robustness cannot issue qualifying evidence for a non-approved review"
            )
        token = sha256(
            json.dumps(
                review.policy.logical_values(),
                ensure_ascii=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        stress_id = TraderLabStressEvidenceId(
            uuid5(
                NAMESPACE_URL,
                f"qore:robustness-stress:{review.candidate.fingerprint.value}:{token}",
            )
        )
        built_stress = build_trader_lab_stress_evidence(
            evidence_id=stress_id,
            candidate=review.candidate,
            family=TraderLabRobustnessFamily.COST_PERTURBATION,
            scenario=review.policy.scenario,
            bounds=(
                review.policy.return_haircut,
                review.policy.min_stressed_mean_return,
                review.policy.max_stressed_population_variance,
            ),
            status=TraderLabStressStatus.QUALIFIED,
            certified_at=review.reviewed_at,
        )
        if isinstance(built_stress, Failure):
            raise RobustnessTraderLabAuthorityValidationError(
                f"Robustness stress evidence construction failed: {built_stress.error}"
            )
        stress_evidence = built_stress.value
        digest = _authority_digest(review, stress_evidence)
        evidence_id = TraderLabGovernedGateEvidenceId(
            uuid5(
                NAMESPACE_URL,
                "qore:robustness-trader-lab:"
                f"{review.candidate.fingerprint.value}:"
                f"{review.reviewed_at.astimezone(UTC).isoformat(timespec='microseconds')}",
            )
        )
        fingerprint = compute_trader_lab_governed_gate_fingerprint(
            evidence_id=evidence_id,
            gate=TraderLabGovernedGate.STRESS_REVIEW,
            authority_kind=TraderLabGovernedAuthorityKind.ROBUSTNESS,
            candidate=review.candidate,
            authority_id=_ROBUSTNESS_AUTHORITY_ID,
            authority_name=_ROBUSTNESS_AUTHORITY_NAME,
            decision=TraderLabGovernedDecision.APPROVED,
            decided_at=review.reviewed_at,
            authority_evidence_digest=digest,
        )
        evidence = TraderLabGovernedGateEvidence(
            evidence_id=evidence_id,
            gate=TraderLabGovernedGate.STRESS_REVIEW,
            authority_kind=TraderLabGovernedAuthorityKind.ROBUSTNESS,
            candidate=review.candidate,
            authority_id=_ROBUSTNESS_AUTHORITY_ID,
            authority_name=_ROBUSTNESS_AUTHORITY_NAME,
            decision=TraderLabGovernedDecision.APPROVED,
            decided_at=review.reviewed_at,
            authority_evidence_digest=digest,
            fingerprint=fingerprint,
        )
        proof = _issued_proof(
            evidence=evidence,
            candidate=review.candidate,
            issued_at=review.reviewed_at,
        )
        verified = verify_governed_gate_evidence(review.candidate, evidence, proof)
        if isinstance(verified, Failure):
            raise RobustnessTraderLabAuthorityBlockedError(
                f"Robustness-issued evidence failed Lab verification: {verified.error}"
            )
        return Success(
            RobustnessTraderLabIssuance(
                review=review,
                stress_evidence=stress_evidence,
                evidence=evidence,
                proof=proof,
                reference=verified.value,
            )
        )
    except RobustnessTraderLabAuthorityError as error:
        return Failure(error)
