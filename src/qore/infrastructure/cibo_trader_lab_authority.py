"""CIBO-owned Trader Lab review and authenticity issuance.

The Trader Lab stays consume/verify-only. This module lives outside the Lab,
projects already-qualified Lab evidence into CIBO's provider-neutral capability
profile, obtains the existing deterministic CIBO development review, and issues
a sealed CIBO_REVIEW authenticity proof only for RECOMMEND_PROMOTION.

CIBO remains advisory for trading: this authority can qualify only the CIBO Lab
stage. It creates no Risk authorization, execution submission, provider order,
Production authority, or real-capital permission.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from re import fullmatch
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboLabEvidenceRef,
    CiboLabEvidenceStage,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.cibo_trader_development_review import (
    CiboDevelopmentRecommendation,
    CiboDevelopmentReview,
    review_capability_profile,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
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
    TraderLabLifecycle,
    TraderLabState,
    validate_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceReference,
    TraderLabStage,
    validate_trader_lab_evidence_reference,
)
from qore.infrastructure.traders.evaluators import cohort_evaluators
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_CIBO_AUTHORITY_ID = UUID("76200000-0000-0000-0000-000000000001")
_CIBO_AUTHORITY_NAME = "qore-cibo-trader-lab-authority-v1"

_CIBO_STAGE_BY_LAB_STAGE: dict[TraderLabStage, CiboLabEvidenceStage] = {
    TraderLabStage.REPLAY: CiboLabEvidenceStage.REPLAY,
    TraderLabStage.FAST_FORWARD: CiboLabEvidenceStage.FAST_FORWARD,
    TraderLabStage.OOS: CiboLabEvidenceStage.OOS,
    TraderLabStage.STRESS: CiboLabEvidenceStage.STRESS,
    TraderLabStage.MONTE_CARLO: CiboLabEvidenceStage.MONTE_CARLO,
    TraderLabStage.RISK_REVIEW: CiboLabEvidenceStage.RISK,
}


class CiboTraderLabAuthorityError(InfrastructureError):
    """Base error for the CIBO-owned Trader Lab authority."""

    __slots__ = ()


class CiboTraderLabAuthorityValidationError(CiboTraderLabAuthorityError):
    """CIBO Lab authority inputs violate exact binding invariants."""

    __slots__ = ()


class CiboTraderLabAuthorityBlockedError(CiboTraderLabAuthorityError):
    """CIBO cannot issue a qualifying Lab review for the supplied evidence."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class CiboTraderLabIssuance:
    """CIBO review plus its sealed, Lab-verified qualifying evidence."""

    review: CiboDevelopmentReview
    evidence: TraderLabGovernedGateEvidence
    proof: TraderLabGovernedAuthenticityProof
    reference: TraderLabEvidenceReference

    def __post_init__(self) -> None:
        if self.review.recommendation is not (
            CiboDevelopmentRecommendation.RECOMMEND_PROMOTION
        ):
            raise CiboTraderLabAuthorityValidationError(
                "CIBO issuance requires RECOMMEND_PROMOTION"
            )
        if self.evidence.gate is not TraderLabGovernedGate.CIBO_REVIEW:
            raise CiboTraderLabAuthorityValidationError(
                "CIBO issuance evidence must be the CIBO_REVIEW gate"
            )
        if self.proof.authority_kind is not TraderLabGovernedAuthorityKind.CIBO:
            raise CiboTraderLabAuthorityValidationError(
                "CIBO issuance proof must be owned by CIBO"
            )


def _timestamp(value: datetime, *, field_name: str) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboTraderLabAuthorityValidationError(
            f"{field_name} must be timezone-aware"
        )
    return value.astimezone(UTC)


def _manifest_values(candidate: TraderLabCandidateBinding) -> dict[str, str]:
    values: dict[str, str] = {}
    for parameter in candidate.strategy_binding.manifest.parameters:
        if parameter.name.startswith("trader."):
            if type(parameter.value) is not str:
                raise CiboTraderLabAuthorityValidationError(
                    "CIBO Trader Lab projection requires string trader manifest values"
                )
            values[parameter.name] = parameter.value
    required = {
        "trader.code",
        "trader.config_fingerprint",
        "trader.instrument",
        "trader.methodology_fingerprint",
        "trader.methodology_id",
        "trader.methodology_version",
    }
    if not required.issubset(values):
        raise CiboTraderLabAuthorityValidationError(
            "CIBO Trader Lab projection requires exact trader manifest binding"
        )
    return values


def _derived_qualified_timeframes(values: dict[str, str]) -> tuple[str, ...]:
    """Derive timeframes from the exact first-cohort evaluator methodology."""

    trader_code = values["trader.code"]
    evaluator = next(
        (item for item in cohort_evaluators() if item.trader_code == trader_code),
        None,
    )
    if evaluator is None:
        raise CiboTraderLabAuthorityValidationError(
            "CIBO first-DEMO review requires an exact first-cohort evaluator"
        )
    methodology_id, methodology_version, methodology_fingerprint = evaluator.methodology()
    if methodology_id.value != values["trader.methodology_id"]:
        raise CiboTraderLabAuthorityValidationError(
            "CIBO methodology id does not match the frozen evaluator"
        )
    if methodology_version.value != values["trader.methodology_version"]:
        raise CiboTraderLabAuthorityValidationError(
            "CIBO methodology version does not match the frozen evaluator"
        )
    if methodology_fingerprint.value != values["trader.methodology_fingerprint"]:
        raise CiboTraderLabAuthorityValidationError(
            "CIBO methodology fingerprint does not match the frozen evaluator"
        )
    if trader_code == "vt-08":
        return (evaluator.timeframe, "H4")
    return (evaluator.timeframe,)


def _identity(
    candidate: TraderLabCandidateBinding,
    *,
    trader_code: str,
) -> ResearchDecisionEvaluatorIdentity:
    normalized_code = trader_code.replace("-", "")
    family = ResearchDecisionEvaluatorFamily(f"qore.trader.{normalized_code}")
    version = candidate.version.value
    if fullmatch(r"v\d+(?:\.\d+)*", version) is None:
        raise CiboTraderLabAuthorityValidationError(
            "CIBO review requires a schema-compatible Trader version"
        )
    return ResearchDecisionEvaluatorIdentity(
        family=family,
        schema_version=ResearchDecisionEvaluatorSchemaVersion(version),
        software_revision=candidate.strategy_binding.run.software_revision,
    )


def _cibo_ref(
    reference: TraderLabEvidenceReference,
    *,
    prefix: str,
) -> CiboEvidenceRef:
    validate_trader_lab_evidence_reference(reference)
    return CiboEvidenceRef(
        f"lab:{prefix}:{reference.reference_id}:{reference.content_digest.value}"
    )


def build_cibo_profile_from_trader_lab(
    lifecycle: TraderLabLifecycle,
    *,
    economic_evidence: TraderLabEvidenceReference,
    qualified_timeframes: tuple[str, ...],
    evidence_as_of: datetime,
) -> Result[CiboTraderCapabilityProfile, CiboTraderLabAuthorityError]:
    """Project exact post-Risk Lab evidence into a CIBO capability profile."""

    try:
        if not isinstance(lifecycle, TraderLabLifecycle):
            raise CiboTraderLabAuthorityValidationError(
                "CIBO projection requires TraderLabLifecycle"
            )
        validate_trader_lab_lifecycle(lifecycle)
        if lifecycle.state is not TraderLabState.RISK_REVIEWED:
            raise CiboTraderLabAuthorityBlockedError(
                "CIBO review is available only after the authentic Risk review"
            )
        candidate = lifecycle.candidate
        values = _manifest_values(candidate)
        expected_timeframes = _derived_qualified_timeframes(values)
        if qualified_timeframes != expected_timeframes:
            raise CiboTraderLabAuthorityValidationError(
                "CIBO qualified timeframes must match the frozen Trader methodology"
            )
        validate_trader_lab_evidence_reference(economic_evidence)
        if (
            economic_evidence.strategy_binding_fingerprint
            != candidate.strategy_binding.binding_fingerprint.value
        ):
            raise CiboTraderLabAuthorityBlockedError(
                "CIBO economic evidence must bind the exact candidate strategy"
            )
        as_of = _timestamp(evidence_as_of, field_name="CIBO evidence_as_of")
        if as_of < lifecycle.qualifications[-1].qualified_at.astimezone(UTC):
            raise CiboTraderLabAuthorityValidationError(
                "CIBO evidence_as_of cannot predate the Risk qualification"
            )

        certified: list[CiboLabEvidenceRef] = []
        for qualification in lifecycle.qualifications:
            mapped = _CIBO_STAGE_BY_LAB_STAGE.get(qualification.stage)
            if mapped is None:
                continue
            certified.append(
                CiboLabEvidenceRef(
                    stage=mapped,
                    ref=_cibo_ref(
                        qualification.evidence.source_reference,
                        prefix=qualification.stage.value,
                    ),
                )
            )
        certified.append(
            CiboLabEvidenceRef(
                stage=CiboLabEvidenceStage.ECONOMIC,
                ref=_cibo_ref(economic_evidence, prefix="economic"),
            )
        )

        built = build_cibo_trader_capability_profile(
            trader_identity=_identity(candidate, trader_code=values["trader.code"]),
            config_fingerprint=CiboTraderConfigFingerprint(
                values["trader.config_fingerprint"]
            ),
            specialty=CiboSpecialtyCode(values["trader.methodology_id"]),
            qualified_markets=(
                CiboTradeableMarketRef(values["trader.instrument"]),
            ),
            qualified_timeframes=tuple(
                CiboTimeframeCode(item.lower()) for item in expected_timeframes
            ),
            certified_lab_evidence=tuple(certified),
            certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
            freshness=CiboEvidenceFreshness(
                state=CiboEvidenceFreshnessState.CURRENT,
                as_of=as_of,
            ),
        )
        if isinstance(built, Failure):
            raise CiboTraderLabAuthorityValidationError(
                f"CIBO profile construction failed: {built.error}"
            )
        return Success(built.value)
    except InfrastructureError as error:
        if isinstance(error, CiboTraderLabAuthorityError):
            return Failure(error)
        return Failure(CiboTraderLabAuthorityValidationError(str(error)))


def review_trader_lab_candidate_cibo(
    lifecycle: TraderLabLifecycle,
    *,
    economic_evidence: TraderLabEvidenceReference,
    qualified_timeframes: tuple[str, ...],
    reviewed_at: datetime,
) -> Result[CiboDevelopmentReview, CiboTraderLabAuthorityError]:
    """Run deterministic CIBO review over exact post-Risk Lab evidence."""

    profile = build_cibo_profile_from_trader_lab(
        lifecycle,
        economic_evidence=economic_evidence,
        qualified_timeframes=qualified_timeframes,
        evidence_as_of=reviewed_at,
    )
    if isinstance(profile, Failure):
        return Failure(profile.error)
    try:
        reviewed = review_capability_profile(
            profile.value,
            reviewed_at=reviewed_at,
            expected_identity=profile.value.trader_identity,
            expected_config_fingerprint=profile.value.config_fingerprint.value,
        )
        if isinstance(reviewed, Failure):
            raise CiboTraderLabAuthorityBlockedError(
                f"CIBO development review blocked: {reviewed.error}"
            )
        return Success(reviewed.value)
    except InfrastructureError as error:
        if isinstance(error, CiboTraderLabAuthorityError):
            return Failure(error)
        return Failure(CiboTraderLabAuthorityBlockedError(str(error)))


def _review_digest(review: CiboDevelopmentReview) -> TraderLabEvidenceDigest:
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
        gate=TraderLabGovernedGate.CIBO_REVIEW,
        authority_kind=TraderLabGovernedAuthorityKind.CIBO,
        issuer_id=_CIBO_AUTHORITY_ID,
        issued_at=issued_at,
    )
    proof = object.__new__(TraderLabGovernedAuthenticityProof)
    object.__setattr__(proof, "evidence_fingerprint", evidence.fingerprint)
    object.__setattr__(proof, "candidate", candidate)
    object.__setattr__(proof, "gate", TraderLabGovernedGate.CIBO_REVIEW)
    object.__setattr__(proof, "authority_kind", TraderLabGovernedAuthorityKind.CIBO)
    object.__setattr__(proof, "issuer_id", _CIBO_AUTHORITY_ID)
    object.__setattr__(proof, "issued_at", issued_at)
    object.__setattr__(proof, "proof_fingerprint", proof_fingerprint)
    object.__setattr__(proof, "_issued", True)
    proof.__post_init__()
    return proof


def issue_cibo_trader_lab_approval(
    lifecycle: TraderLabLifecycle,
    review: CiboDevelopmentReview,
) -> Result[CiboTraderLabIssuance, CiboTraderLabAuthorityError]:
    """Issue a CIBO_REVIEW proof only from a valid promotion recommendation."""

    try:
        if not isinstance(lifecycle, TraderLabLifecycle):
            raise CiboTraderLabAuthorityValidationError(
                "CIBO issuance requires TraderLabLifecycle"
            )
        validate_trader_lab_lifecycle(lifecycle)
        if lifecycle.state is not TraderLabState.RISK_REVIEWED:
            raise CiboTraderLabAuthorityBlockedError(
                "CIBO issuance requires the post-Risk lifecycle state"
            )
        if not isinstance(review, CiboDevelopmentReview):
            raise CiboTraderLabAuthorityValidationError(
                "CIBO issuance requires CiboDevelopmentReview"
            )
        review.__post_init__()
        candidate = lifecycle.candidate
        values = _manifest_values(candidate)
        expected_timeframes = tuple(
            CiboTimeframeCode(item.lower())
            for item in _derived_qualified_timeframes(values)
        )
        expected_identity = _identity(candidate, trader_code=values["trader.code"])
        if review.profile.trader_identity != expected_identity:
            raise CiboTraderLabAuthorityBlockedError(
                "CIBO review identity does not match the exact Lab candidate"
            )
        if (
            review.profile.config_fingerprint.value
            != values["trader.config_fingerprint"]
        ):
            raise CiboTraderLabAuthorityBlockedError(
                "CIBO review config does not match the exact Lab candidate"
            )
        if review.profile.qualified_timeframes != expected_timeframes:
            raise CiboTraderLabAuthorityBlockedError(
                "CIBO review timeframes do not match the frozen Trader methodology"
            )
        if review.recommendation is not (
            CiboDevelopmentRecommendation.RECOMMEND_PROMOTION
        ):
            raise CiboTraderLabAuthorityBlockedError(
                "CIBO cannot issue qualifying evidence without RECOMMEND_PROMOTION"
            )

        decided_at = review.reviewed_at
        digest = _review_digest(review)
        evidence_id = TraderLabGovernedGateEvidenceId(
            uuid5(
                NAMESPACE_URL,
                "qore:cibo-trader-lab:"
                f"{candidate.fingerprint.value}:"
                f"{decided_at.astimezone(UTC).isoformat(timespec='microseconds')}",
            )
        )
        fingerprint = compute_trader_lab_governed_gate_fingerprint(
            evidence_id=evidence_id,
            gate=TraderLabGovernedGate.CIBO_REVIEW,
            authority_kind=TraderLabGovernedAuthorityKind.CIBO,
            candidate=candidate,
            authority_id=_CIBO_AUTHORITY_ID,
            authority_name=_CIBO_AUTHORITY_NAME,
            decision=TraderLabGovernedDecision.APPROVED,
            decided_at=decided_at,
            authority_evidence_digest=digest,
        )
        evidence = TraderLabGovernedGateEvidence(
            evidence_id=evidence_id,
            gate=TraderLabGovernedGate.CIBO_REVIEW,
            authority_kind=TraderLabGovernedAuthorityKind.CIBO,
            candidate=candidate,
            authority_id=_CIBO_AUTHORITY_ID,
            authority_name=_CIBO_AUTHORITY_NAME,
            decision=TraderLabGovernedDecision.APPROVED,
            decided_at=decided_at,
            authority_evidence_digest=digest,
            fingerprint=fingerprint,
        )
        proof = _issued_proof(
            evidence=evidence,
            candidate=candidate,
            issued_at=decided_at,
        )
        verified = verify_governed_gate_evidence(candidate, evidence, proof)
        if isinstance(verified, Failure):
            raise CiboTraderLabAuthorityBlockedError(
                f"CIBO-issued evidence failed Lab verification: {verified.error}"
            )
        return Success(
            CiboTraderLabIssuance(
                review=review,
                evidence=evidence,
                proof=proof,
                reference=verified.value,
            )
        )
    except InfrastructureError as error:
        if isinstance(error, CiboTraderLabAuthorityError):
            return Failure(error)
        return Failure(CiboTraderLabAuthorityValidationError(str(error)))
