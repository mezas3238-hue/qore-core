"""Independent authority for the final Trader Lab validation gate.

This authority is deliberately separate from Trader Lab, Risk, and CIBO.  It
re-enters the exact post-CIBO lifecycle, economic evidence, performance lineage,
external-authenticity seams, and temporal ordering before issuing the sealed
``INDEPENDENT_VALIDATION`` proof consumed by Trader Lab.

The authority grants only the final Lab qualification.  It cannot authorize an
order, select a broker account, bypass Risk, enable LIVE/Production, or authorize
real capital.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
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
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    TraderLabStage,
    evidence_kind_is_external_authenticated,
    validate_trader_lab_evidence_reference,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_INDEPENDENT_AUTHORITY_ID = UUID("76300000-0000-0000-0000-000000000001")
_INDEPENDENT_AUTHORITY_NAME = "qore-independent-trader-lab-validator-v1"
_REQUIRED_COMPLETED_STAGES = MANDATORY_STAGES[
    : MANDATORY_STAGES.index(TraderLabStage.INDEPENDENT_VALIDATION)
]


class IndependentTraderLabValidationError(InfrastructureError):
    """Base error for the independent Trader Lab validation authority."""

    __slots__ = ()


class IndependentTraderLabValidationInputError(IndependentTraderLabValidationError):
    """Supplied validation material violates exact structural invariants."""

    __slots__ = ()


class IndependentTraderLabValidationBlockedError(
    IndependentTraderLabValidationError
):
    """Independent validation cannot approve the supplied candidate."""

    __slots__ = ()


class IndependentTraderLabCheck(StrEnum):
    """Closed invariant set re-entered independently before final qualification."""

    EXACT_CANDIDATE_BINDING = "exact_candidate_binding"
    COMPLETE_PREVALIDATION_CHAIN = "complete_prevalidation_chain"
    ECONOMIC_LINEAGE = "economic_lineage"
    PERFORMANCE_LINEAGE = "performance_lineage"
    EXTERNAL_GATE_AUTHENTICITY = "external_gate_authenticity"
    TEMPORAL_ORDERING = "temporal_ordering"


_REQUIRED_CHECKS: tuple[IndependentTraderLabCheck, ...] = tuple(
    IndependentTraderLabCheck
)


@dataclass(frozen=True, slots=True)
class IndependentTraderLabReview:
    """Immutable independent validation over one exact post-CIBO candidate."""

    candidate: TraderLabCandidateBinding
    lifecycle: TraderLabLifecycle
    economic_evidence: TraderLabEvidenceReference
    performance: ResearchPerformanceStatisticsSnapshot
    checks: tuple[IndependentTraderLabCheck, ...]
    validated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, TraderLabCandidateBinding):
            raise IndependentTraderLabValidationInputError(
                "independent review requires TraderLabCandidateBinding"
            )
        if not isinstance(self.lifecycle, TraderLabLifecycle):
            raise IndependentTraderLabValidationInputError(
                "independent review requires TraderLabLifecycle"
            )
        validate_trader_lab_lifecycle(self.lifecycle)
        if self.lifecycle.candidate != self.candidate:
            raise IndependentTraderLabValidationInputError(
                "independent lifecycle must bind the exact candidate"
            )
        if self.lifecycle.state is not TraderLabState.CIBO_REVIEWED:
            raise IndependentTraderLabValidationInputError(
                "independent validation requires the post-CIBO lifecycle state"
            )
        if self.lifecycle.completed_stages != _REQUIRED_COMPLETED_STAGES:
            raise IndependentTraderLabValidationInputError(
                "independent validation requires the complete chain through CIBO"
            )
        validate_trader_lab_evidence_reference(self.economic_evidence)
        if self.economic_evidence.kind is not TraderLabEvidenceKind.ECONOMIC_EVALUATION:
            raise IndependentTraderLabValidationInputError(
                "independent validation requires ECONOMIC_EVALUATION evidence"
            )
        if (
            self.economic_evidence.strategy_binding_fingerprint
            != self.candidate.strategy_binding.binding_fingerprint.value
        ):
            raise IndependentTraderLabValidationInputError(
                "economic evidence must bind the exact candidate strategy"
            )
        if not isinstance(self.performance, ResearchPerformanceStatisticsSnapshot):
            raise IndependentTraderLabValidationInputError(
                "independent validation requires performance statistics"
            )
        self.performance.__post_init__()
        if self.performance.run != self.candidate.strategy_binding.run:
            raise IndependentTraderLabValidationInputError(
                "performance statistics must bind the exact candidate run"
            )
        if type(self.checks) is not tuple or self.checks != _REQUIRED_CHECKS:
            raise IndependentTraderLabValidationInputError(
                "independent review must record every required check exactly once"
            )
        if (
            type(self.validated_at) is not datetime
            or self.validated_at.tzinfo is None
            or self.validated_at.utcoffset() is None
        ):
            raise IndependentTraderLabValidationInputError(
                "independent validated_at must be timezone-aware"
            )
        latest_required = max(
            self.lifecycle.qualifications[-1].qualified_at,
            self.performance.observed_at,
        )
        if self.validated_at < latest_required:
            raise IndependentTraderLabValidationInputError(
                "independent validation cannot predate retained evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.candidate.fingerprint.value,
            self.lifecycle.logical_values(),
            self.economic_evidence.logical_values(),
            self.performance.logical_values(),
            tuple(item.value for item in self.checks),
            self.validated_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class IndependentTraderLabIssuance:
    """Independent review plus sealed, Lab-verified qualifying evidence."""

    review: IndependentTraderLabReview
    evidence: TraderLabGovernedGateEvidence
    proof: TraderLabGovernedAuthenticityProof
    reference: TraderLabEvidenceReference

    def __post_init__(self) -> None:
        self.review.__post_init__()
        if self.evidence.gate is not TraderLabGovernedGate.INDEPENDENT_VALIDATION:
            raise IndependentTraderLabValidationInputError(
                "independent issuance evidence must target INDEPENDENT_VALIDATION"
            )
        if self.proof.authority_kind is not (
            TraderLabGovernedAuthorityKind.INDEPENDENT_VALIDATION
        ):
            raise IndependentTraderLabValidationInputError(
                "independent issuance proof must be owned by independent validation"
            )


def _verify_external_gate_authenticity(lifecycle: TraderLabLifecycle) -> None:
    """Require authenticity proofs on every external-authenticated retained gate."""

    for qualification in lifecycle.qualifications:
        reference = qualification.evidence.source_reference
        if not evidence_kind_is_external_authenticated(reference.kind):
            continue
        validate_trader_lab_evidence_reference(reference)
        if reference.external_authenticity_proof is None:
            raise IndependentTraderLabValidationBlockedError(
                "external-authenticated Lab stage is missing authenticity proof"
            )


def review_trader_lab_candidate_independently(
    lifecycle: TraderLabLifecycle,
    *,
    economic_evidence: TraderLabEvidenceReference,
    performance: ResearchPerformanceStatisticsSnapshot,
    validated_at: datetime,
) -> Result[IndependentTraderLabReview, IndependentTraderLabValidationError]:
    """Re-enter the final independent invariant set without trusting prior conclusions."""

    try:
        if not isinstance(lifecycle, TraderLabLifecycle):
            raise IndependentTraderLabValidationInputError(
                "independent validation requires TraderLabLifecycle"
            )
        validate_trader_lab_lifecycle(lifecycle)
        if lifecycle.state is not TraderLabState.CIBO_REVIEWED:
            raise IndependentTraderLabValidationBlockedError(
                "independent validation is available only after authentic CIBO review"
            )
        if lifecycle.completed_stages != _REQUIRED_COMPLETED_STAGES:
            raise IndependentTraderLabValidationBlockedError(
                "independent validation requires all prior mandatory stages"
            )
        validate_trader_lab_evidence_reference(economic_evidence)
        if economic_evidence.kind is not TraderLabEvidenceKind.ECONOMIC_EVALUATION:
            raise IndependentTraderLabValidationBlockedError(
                "economic evidence kind is not ECONOMIC_EVALUATION"
            )
        candidate = lifecycle.candidate
        if (
            economic_evidence.strategy_binding_fingerprint
            != candidate.strategy_binding.binding_fingerprint.value
        ):
            raise IndependentTraderLabValidationBlockedError(
                "economic evidence lineage does not match the candidate"
            )
        if not isinstance(performance, ResearchPerformanceStatisticsSnapshot):
            raise IndependentTraderLabValidationInputError(
                "performance must be ResearchPerformanceStatisticsSnapshot"
            )
        performance.__post_init__()
        if performance.run != candidate.strategy_binding.run:
            raise IndependentTraderLabValidationBlockedError(
                "performance run does not match the candidate"
            )
        if (
            type(validated_at) is not datetime
            or validated_at.tzinfo is None
            or validated_at.utcoffset() is None
        ):
            raise IndependentTraderLabValidationInputError(
                "validated_at must be timezone-aware"
            )
        latest_required = max(
            lifecycle.qualifications[-1].qualified_at,
            performance.observed_at,
        )
        if validated_at < latest_required:
            raise IndependentTraderLabValidationBlockedError(
                "independent validation cannot predate retained evidence"
            )
        _verify_external_gate_authenticity(lifecycle)
        return Success(
            IndependentTraderLabReview(
                candidate=candidate,
                lifecycle=lifecycle,
                economic_evidence=economic_evidence,
                performance=performance,
                checks=_REQUIRED_CHECKS,
                validated_at=validated_at,
            )
        )
    except IndependentTraderLabValidationError as error:
        return Failure(error)


def _review_digest(review: IndependentTraderLabReview) -> TraderLabEvidenceDigest:
    encoded = json.dumps(
        review.logical_values(),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return TraderLabEvidenceDigest(sha256(encoded).hexdigest())


def _issued_proof(
    *,
    evidence: TraderLabGovernedGateEvidence,
    candidate: TraderLabCandidateBinding,
    issued_at: datetime,
) -> TraderLabGovernedAuthenticityProof:
    proof_fingerprint = compute_trader_lab_governed_authenticity_proof_fingerprint(
        evidence_fingerprint=evidence.fingerprint,
        candidate=candidate,
        gate=TraderLabGovernedGate.INDEPENDENT_VALIDATION,
        authority_kind=TraderLabGovernedAuthorityKind.INDEPENDENT_VALIDATION,
        issuer_id=_INDEPENDENT_AUTHORITY_ID,
        issued_at=issued_at,
    )
    proof = object.__new__(TraderLabGovernedAuthenticityProof)
    object.__setattr__(proof, "evidence_fingerprint", evidence.fingerprint)
    object.__setattr__(proof, "candidate", candidate)
    object.__setattr__(proof, "gate", TraderLabGovernedGate.INDEPENDENT_VALIDATION)
    object.__setattr__(
        proof,
        "authority_kind",
        TraderLabGovernedAuthorityKind.INDEPENDENT_VALIDATION,
    )
    object.__setattr__(proof, "issuer_id", _INDEPENDENT_AUTHORITY_ID)
    object.__setattr__(proof, "issued_at", issued_at)
    object.__setattr__(proof, "proof_fingerprint", proof_fingerprint)
    object.__setattr__(proof, "_issued", True)
    proof.__post_init__()
    return proof


def issue_independent_trader_lab_approval(
    review: IndependentTraderLabReview,
) -> Result[IndependentTraderLabIssuance, IndependentTraderLabValidationError]:
    """Issue and immediately verify the final independent Lab authenticity proof."""

    try:
        if not isinstance(review, IndependentTraderLabReview):
            raise IndependentTraderLabValidationInputError(
                "independent issuance requires IndependentTraderLabReview"
            )
        review.__post_init__()
        candidate = review.candidate
        evidence_id = TraderLabGovernedGateEvidenceId(
            uuid5(
                NAMESPACE_URL,
                "qore:independent-trader-lab:"
                f"{candidate.fingerprint.value}:"
                f"{review.validated_at.astimezone(UTC).isoformat(timespec='microseconds')}",
            )
        )
        digest = _review_digest(review)
        fingerprint = compute_trader_lab_governed_gate_fingerprint(
            evidence_id=evidence_id,
            gate=TraderLabGovernedGate.INDEPENDENT_VALIDATION,
            authority_kind=TraderLabGovernedAuthorityKind.INDEPENDENT_VALIDATION,
            candidate=candidate,
            authority_id=_INDEPENDENT_AUTHORITY_ID,
            authority_name=_INDEPENDENT_AUTHORITY_NAME,
            decision=TraderLabGovernedDecision.APPROVED,
            decided_at=review.validated_at,
            authority_evidence_digest=digest,
        )
        evidence = TraderLabGovernedGateEvidence(
            evidence_id=evidence_id,
            gate=TraderLabGovernedGate.INDEPENDENT_VALIDATION,
            authority_kind=TraderLabGovernedAuthorityKind.INDEPENDENT_VALIDATION,
            candidate=candidate,
            authority_id=_INDEPENDENT_AUTHORITY_ID,
            authority_name=_INDEPENDENT_AUTHORITY_NAME,
            decision=TraderLabGovernedDecision.APPROVED,
            decided_at=review.validated_at,
            authority_evidence_digest=digest,
            fingerprint=fingerprint,
        )
        proof = _issued_proof(
            evidence=evidence,
            candidate=candidate,
            issued_at=review.validated_at,
        )
        verified = verify_governed_gate_evidence(candidate, evidence, proof)
        if isinstance(verified, Failure):
            raise IndependentTraderLabValidationBlockedError(
                "independent evidence failed Trader Lab verification"
            )
        return Success(
            IndependentTraderLabIssuance(
                review=review,
                evidence=evidence,
                proof=proof,
                reference=verified.value,
            )
        )
    except IndependentTraderLabValidationError as error:
        return Failure(error)
