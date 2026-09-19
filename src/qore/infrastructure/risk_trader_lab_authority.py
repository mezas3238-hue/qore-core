"""Risk-owned Trader Lab review and authenticity issuance.

This module sits OUTSIDE ``qore.infrastructure.trader_lab`` deliberately.  The
Lab remains consume/verify-only for the Risk gate; only this Risk authority may
turn a Risk review into the sealed authenticity proof consumed by the Lab.

The review is candidate/run-bound, requires the exact lifecycle state after
MONTE_CARLO, applies an explicit immutable Risk policy, and never grants
execution, CIBO, independent-validation, Production, or real-capital authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
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
    TraderLabGovernedGateFingerprint,
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
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceReference,
    TraderLabStage,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_RISK_AUTHORITY_ID = UUID("76100000-0000-0000-0000-000000000001")
_RISK_AUTHORITY_NAME = "qore-risk-trader-lab-authority-v1"
_POLICY_RE = r"[a-z][a-z0-9._-]*"
_REQUIRED_COMPLETED_STAGES = MANDATORY_STAGES[: MANDATORY_STAGES.index(TraderLabStage.RISK_REVIEW)]


class RiskTraderLabAuthorityError(InfrastructureError):
    """Base error for the Risk-owned Trader Lab review authority."""

    __slots__ = ()


class RiskTraderLabAuthorityValidationError(RiskTraderLabAuthorityError):
    """Risk review inputs violate exact candidate/policy invariants."""

    __slots__ = ()


class RiskTraderLabAuthorityBlockedError(RiskTraderLabAuthorityError):
    """Risk cannot issue a qualifying Lab review for the supplied evidence."""

    __slots__ = ()


class RiskTraderLabReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class RiskTraderLabPolicy:
    """Explicit Risk policy for one Trader Lab candidate review."""

    policy_id: str
    min_sample_size: int
    max_population_variance: Decimal

    def __post_init__(self) -> None:
        if type(self.policy_id) is not str or fullmatch(_POLICY_RE, self.policy_id) is None:
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab policy_id must use canonical lowercase syntax"
            )
        if type(self.min_sample_size) is not int or self.min_sample_size <= 0:
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab min_sample_size must be a positive int"
            )
        if (
            type(self.max_population_variance) is not Decimal
            or not self.max_population_variance.is_finite()
            or self.max_population_variance < 0
        ):
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab max_population_variance must be a finite non-negative Decimal"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_id,
            self.min_sample_size,
            format(self.max_population_variance, "f"),
        )


@dataclass(frozen=True, slots=True)
class RiskTraderLabReview:
    """Immutable Risk decision over one exact candidate/run and Lab prefix."""

    candidate: TraderLabCandidateBinding
    lifecycle: TraderLabLifecycle
    performance: ResearchPerformanceStatisticsSnapshot
    policy: RiskTraderLabPolicy
    decision: RiskTraderLabReviewDecision
    reasons: tuple[str, ...]
    reviewed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, TraderLabCandidateBinding):
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab review requires TraderLabCandidateBinding"
            )
        if not isinstance(self.lifecycle, TraderLabLifecycle):
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab review requires TraderLabLifecycle"
            )
        validate_trader_lab_lifecycle(self.lifecycle)
        if self.lifecycle.candidate != self.candidate:
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab lifecycle must bind the exact candidate"
            )
        if self.lifecycle.state is not TraderLabState.MONTE_CARLO_QUALIFIED:
            raise RiskTraderLabAuthorityValidationError(
                "Risk review must consume the exact post-MONTE_CARLO lifecycle state"
            )
        if self.lifecycle.completed_stages != _REQUIRED_COMPLETED_STAGES:
            raise RiskTraderLabAuthorityValidationError(
                "Risk review requires the complete RESEARCH through MONTE_CARLO chain"
            )
        if not isinstance(self.performance, ResearchPerformanceStatisticsSnapshot):
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab review requires performance statistics"
            )
        self.performance.__post_init__()
        if self.performance.run != self.candidate.strategy_binding.run:
            raise RiskTraderLabAuthorityValidationError(
                "risk review performance run must match the exact candidate run"
            )
        if not isinstance(self.policy, RiskTraderLabPolicy):
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab review requires RiskTraderLabPolicy"
            )
        self.policy.__post_init__()
        if type(self.decision) is not RiskTraderLabReviewDecision:
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab decision must be RiskTraderLabReviewDecision"
            )
        if type(self.reasons) is not tuple or any(type(item) is not str for item in self.reasons):
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab reasons must be an immutable str tuple"
            )
        if len(set(self.reasons)) != len(self.reasons):
            raise RiskTraderLabAuthorityValidationError(
                "risk Trader Lab reasons must not contain duplicates"
            )
        if self.decision is RiskTraderLabReviewDecision.APPROVED and self.reasons:
            raise RiskTraderLabAuthorityValidationError(
                "approved Risk review must not carry blocking reasons"
            )
        if self.decision is not RiskTraderLabReviewDecision.APPROVED and not self.reasons:
            raise RiskTraderLabAuthorityValidationError(
                "non-approved Risk review must carry at least one reason"
            )
        _validate_timestamp(self.reviewed_at)
        last_qualified_at = self.lifecycle.qualifications[-1].qualified_at
        if self.reviewed_at < last_qualified_at:
            raise RiskTraderLabAuthorityValidationError(
                "Risk review cannot predate MONTE_CARLO qualification"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.candidate.fingerprint.value,
            self.lifecycle.logical_values(),
            self.performance.logical_values(),
            self.policy.logical_values(),
            self.decision.value,
            self.reasons,
            self.reviewed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class RiskTraderLabIssuance:
    """Risk-issued carrier, sealed proof and verified Lab reference."""

    review: RiskTraderLabReview
    evidence: TraderLabGovernedGateEvidence
    proof: TraderLabGovernedAuthenticityProof
    reference: TraderLabEvidenceReference

    def __post_init__(self) -> None:
        if self.review.decision is not RiskTraderLabReviewDecision.APPROVED:
            raise RiskTraderLabAuthorityValidationError(
                "Risk issuance requires an approved Risk review"
            )
        if self.evidence.gate is not TraderLabGovernedGate.RISK_REVIEW:
            raise RiskTraderLabAuthorityValidationError(
                "Risk issuance evidence must be the RISK_REVIEW gate"
            )
        if self.proof.authority_kind is not TraderLabGovernedAuthorityKind.RISK:
            raise RiskTraderLabAuthorityValidationError(
                "Risk issuance proof must be owned by Risk"
            )


def _validate_timestamp(value: datetime) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise RiskTraderLabAuthorityValidationError(
            "risk Trader Lab reviewed_at must be timezone-aware"
        )


def review_trader_lab_candidate_risk(
    lifecycle: TraderLabLifecycle,
    performance: ResearchPerformanceStatisticsSnapshot,
    *,
    policy: RiskTraderLabPolicy,
    reviewed_at: datetime,
) -> Result[RiskTraderLabReview, RiskTraderLabAuthorityError]:
    """Evaluate one exact post-Monte-Carlo candidate under explicit Risk policy."""

    try:
        if not isinstance(lifecycle, TraderLabLifecycle):
            raise RiskTraderLabAuthorityValidationError(
                "Risk review requires TraderLabLifecycle"
            )
        validate_trader_lab_lifecycle(lifecycle)
        if lifecycle.state is not TraderLabState.MONTE_CARLO_QUALIFIED:
            raise RiskTraderLabAuthorityBlockedError(
                "Risk review is available only after MONTE_CARLO qualification"
            )
        if lifecycle.completed_stages != _REQUIRED_COMPLETED_STAGES:
            raise RiskTraderLabAuthorityBlockedError(
                "Risk review requires all prior mandatory Lab stages"
            )
        if not isinstance(performance, ResearchPerformanceStatisticsSnapshot):
            raise RiskTraderLabAuthorityValidationError(
                "Risk review requires ResearchPerformanceStatisticsSnapshot"
            )
        performance.__post_init__()
        if performance.run != lifecycle.candidate.strategy_binding.run:
            raise RiskTraderLabAuthorityBlockedError(
                "Risk performance evidence does not bind the candidate run"
            )
        if not isinstance(policy, RiskTraderLabPolicy):
            raise RiskTraderLabAuthorityValidationError(
                "Risk review requires RiskTraderLabPolicy"
            )
        policy.__post_init__()
        _validate_timestamp(reviewed_at)

        reasons: list[str] = []
        decision = RiskTraderLabReviewDecision.APPROVED
        if performance.sample_size < policy.min_sample_size:
            decision = RiskTraderLabReviewDecision.DEFERRED
            reasons.append("sample_size_below_risk_policy")
        if performance.population_variance > policy.max_population_variance:
            decision = RiskTraderLabReviewDecision.REJECTED
            reasons.append("population_variance_above_risk_policy")
        return Success(
            RiskTraderLabReview(
                candidate=lifecycle.candidate,
                lifecycle=lifecycle,
                performance=performance,
                policy=policy,
                decision=decision,
                reasons=tuple(reasons),
                reviewed_at=reviewed_at,
            )
        )
    except RiskTraderLabAuthorityError as error:
        return Failure(error)


def _review_digest(review: RiskTraderLabReview) -> TraderLabEvidenceDigest:
    payload = json.dumps(
        review.logical_values(),
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
        gate=TraderLabGovernedGate.RISK_REVIEW,
        authority_kind=TraderLabGovernedAuthorityKind.RISK,
        issuer_id=_RISK_AUTHORITY_ID,
        issued_at=issued_at,
    )
    proof = object.__new__(TraderLabGovernedAuthenticityProof)
    object.__setattr__(proof, "evidence_fingerprint", evidence.fingerprint)
    object.__setattr__(proof, "candidate", candidate)
    object.__setattr__(proof, "gate", TraderLabGovernedGate.RISK_REVIEW)
    object.__setattr__(proof, "authority_kind", TraderLabGovernedAuthorityKind.RISK)
    object.__setattr__(proof, "issuer_id", _RISK_AUTHORITY_ID)
    object.__setattr__(proof, "issued_at", issued_at)
    object.__setattr__(proof, "proof_fingerprint", proof_fingerprint)
    object.__setattr__(proof, "_issued", True)
    proof.__post_init__()
    return proof


def issue_risk_trader_lab_approval(
    review: RiskTraderLabReview,
) -> Result[RiskTraderLabIssuance, RiskTraderLabAuthorityError]:
    """Issue and immediately verify the Risk-owned qualifying Lab reference."""

    try:
        if not isinstance(review, RiskTraderLabReview):
            raise RiskTraderLabAuthorityValidationError(
                "Risk issuance requires RiskTraderLabReview"
            )
        review.__post_init__()
        if review.decision is not RiskTraderLabReviewDecision.APPROVED:
            raise RiskTraderLabAuthorityBlockedError(
                "Risk cannot issue qualifying evidence for a non-approved review"
            )
        evidence_id = TraderLabGovernedGateEvidenceId(
            uuid5(
                NAMESPACE_URL,
                "qore:risk-trader-lab:"
                f"{review.candidate.fingerprint.value}:"
                f"{review.reviewed_at.astimezone(UTC).isoformat(timespec='microseconds')}",
            )
        )
        digest = _review_digest(review)
        fingerprint: TraderLabGovernedGateFingerprint = (
            compute_trader_lab_governed_gate_fingerprint(
                evidence_id=evidence_id,
                gate=TraderLabGovernedGate.RISK_REVIEW,
                authority_kind=TraderLabGovernedAuthorityKind.RISK,
                candidate=review.candidate,
                authority_id=_RISK_AUTHORITY_ID,
                authority_name=_RISK_AUTHORITY_NAME,
                decision=TraderLabGovernedDecision.APPROVED,
                decided_at=review.reviewed_at,
                authority_evidence_digest=digest,
            )
        )
        evidence = TraderLabGovernedGateEvidence(
            evidence_id=evidence_id,
            gate=TraderLabGovernedGate.RISK_REVIEW,
            authority_kind=TraderLabGovernedAuthorityKind.RISK,
            candidate=review.candidate,
            authority_id=_RISK_AUTHORITY_ID,
            authority_name=_RISK_AUTHORITY_NAME,
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
            raise RiskTraderLabAuthorityBlockedError(
                f"Risk-issued governed evidence failed Lab verification: {verified.error}"
            )
        return Success(
            RiskTraderLabIssuance(
                review=review,
                evidence=evidence,
                proof=proof,
                reference=verified.value,
            )
        )
    except RiskTraderLabAuthorityError as error:
        return Failure(error)
