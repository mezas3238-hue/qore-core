"""Owning-authority adapters for the immutable VT-08 B01 R3.15 evidence.

These adapters are deliberately candidate- and artifact-specific.  They cannot
turn arbitrary JSON into governed Trader Lab evidence.  Robustness, Risk, CIBO,
and Independent Validation each re-enter their own invariant before issuing a
sealed proof.  CIBO projects the B01 portfolio itself (three qualified markets,
M15/H4), never the legacy CRT M5/H4 evaluator identity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import cast
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
from qore.infrastructure.trader_history.contracts import compute_trader_identity_family
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
from qore.infrastructure.trader_lab.vt08_r3_15_artifact_evidence import (
    validate_vt08_r315_candidate,
)
from qore.infrastructure.traders.contracts import DemoTradingTraderCode
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure

_METHOD = "0c3fe8e1353386f7384a8532c7fe71bbbe9fcfdf1da7530be4b53e01bc59de0d"
_SOURCE = "403d54304f241f4a11b1ef847aa2a8b12d5ba6ffa2d9be5bb5cd9c19586943e3"
_R315_HEAD = "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
_R314_HEAD = "266fa60df2654ffcbce3a89569295bb19f791022"
_RISK_POLICY_FINGERPRINT = (
    "dfb3fc8217b9895356ed19f8d7e1ee47fae765d39a9bb2e72e14c4ac41fad1f5"
)
_MARKETS = ("AUDJPY", "GBPJPY", "GBPUSD")
_TIMEFRAMES = ("H4", "M15")
_AUTHORITY = {
    TraderLabGovernedGate.STRESS_REVIEW: (
        TraderLabGovernedAuthorityKind.ROBUSTNESS,
        UUID("77315000-0000-0000-0000-000000000001"),
        "qore-vt08-r315-robustness-authority-v1",
    ),
    TraderLabGovernedGate.RISK_REVIEW: (
        TraderLabGovernedAuthorityKind.RISK,
        UUID("77315000-0000-0000-0000-000000000002"),
        "qore-vt08-r315-risk-authority-v1",
    ),
    TraderLabGovernedGate.CIBO_REVIEW: (
        TraderLabGovernedAuthorityKind.CIBO,
        UUID("77315000-0000-0000-0000-000000000003"),
        "qore-vt08-b01-r315-cibo-authority-v1",
    ),
    TraderLabGovernedGate.INDEPENDENT_VALIDATION: (
        TraderLabGovernedAuthorityKind.INDEPENDENT_VALIDATION,
        UUID("77315000-0000-0000-0000-000000000004"),
        "qore-vt08-r315-independent-authority-v1",
    ),
}


class Vt08R315AuthorityError(InfrastructureError):
    """An immutable R3.15 authority invariant failed closed."""

    __slots__ = ()


def _object(value: object, field: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08R315AuthorityError(f"{field} must be an object")
    return cast(dict[str, object], value)


def _decimal(value: object, field: str) -> Decimal:
    if type(value) is not str:
        raise Vt08R315AuthorityError(f"{field} must be decimal text")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise Vt08R315AuthorityError(f"{field} must be decimal text") from error
    if not result.is_finite():
        raise Vt08R315AuthorityError(f"{field} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class Vt08R315OfficialEvidence:
    """The only payload set accepted by the R3.15 owning authorities."""

    holdout: dict[str, object]
    adaptive_risk_policy: dict[str, object]
    adaptive_monte_carlo_b_combined: dict[str, object]
    two_phase: dict[str, object]

    def __post_init__(self) -> None:
        holdout = _object(self.holdout, "holdout")
        exact = {
            "schema": "qore.vt08.r3.15.final-independent-holdout.v1",
            "holdout_id": "VT08_R3_15_FINAL_INDEPENDENT_2020_2022",
            "software_sha": _R315_HEAD,
            "methodology_fingerprint": _METHOD,
            "portfolio": "B_COMBINED",
            "sample_size": 124,
            "wins": 57,
            "losses": 67,
            "flats": 0,
            "max_losing_streak": 7,
            "independent_validation": True,
            "methodology_mutation_after_holdout": False,
            "live_authorized": False,
        }
        for key, expected in exact.items():
            if holdout.get(key) != expected:
                raise Vt08R315AuthorityError(f"official holdout mismatch: {key}")
        for key, expected in {
            "win_rate": Decimal("0.4596774193548387096774193548"),
            "profit_factor": Decimal("1.196270253543172529737553595"),
            "compounded_return": Decimal("0.015898649288157281707521779"),
            "maximum_drawdown": Decimal("0.01837083102440645070088295985"),
            "population_variance": Decimal("0.000003229064513282220060032071879"),
        }.items():
            if _decimal(holdout.get(key), key) != expected:
                raise Vt08R315AuthorityError(f"official holdout mismatch: {key}")
        risk_gate = _object(holdout.get("risk_policy"), "holdout risk_policy")
        if risk_gate != {
            "approved": True,
            "max_population_variance": "0.01",
            "min_sample_size": 30,
            "policy_id": "vt08-r315-final-demo-v1",
        }:
            raise Vt08R315AuthorityError("official holdout Risk gate mismatch")

        adaptive = _object(self.adaptive_risk_policy, "adaptive Risk policy")
        if adaptive.get("holdout_not_accessed") is not True:
            raise Vt08R315AuthorityError("R3.12 must predate holdout access")
        if adaptive.get("risk_policy_fingerprint") != _RISK_POLICY_FINGERPRINT:
            raise Vt08R315AuthorityError("R3.12 Risk policy fingerprint mismatch")
        primary = _object(adaptive.get("primary_policy"), "R3.12 primary policy")
        if primary.get("name") != "balanced-adaptive-v1":
            raise Vt08R315AuthorityError("R3.12 Risk policy id mismatch")
        if primary.get("a_base_bps") != "25" or primary.get("gbpjpy_base_bps") != "20":
            raise Vt08R315AuthorityError("R3.12 funded sizing policy mismatch")

        monte_carlo = _object(
            self.adaptive_monte_carlo_b_combined,
            "R3.12 B COMBINED Monte Carlo",
        )
        if monte_carlo.get("original_sample") != 229:
            raise Vt08R315AuthorityError("R3.12 Monte Carlo sample mismatch")
        primary_mc = _object(monte_carlo.get("primary_0_50bp"), "R3.12 primary MC")
        if primary_mc.get("any_prop_firm_breach_probability") != 0.0:
            raise Vt08R315AuthorityError("R3.12 Monte Carlo breach gate failed")
        drawdown = _object(primary_mc.get("maximum_drawdown"), "R3.12 drawdown")
        p99 = drawdown.get("p99")
        if type(p99) is not float or p99 > 0.05:
            raise Vt08R315AuthorityError("R3.12 Monte Carlo p99 drawdown failed")

        two_phase = _object(self.two_phase, "R3.14 two-phase evidence")
        if two_phase.get("schema") != "qore.vt08.r3.14.two-phase-funding-qualification.v1":
            raise Vt08R315AuthorityError("R3.14 schema mismatch")
        for key, expected in {
            "git_sha": _R314_HEAD,
            "classification": "CONSUMED-DATA RESEARCH ONLY",
            "selection_status": "SAFE_BUT_LOW_60D_COMPLETION",
            "demo_eligible": False,
            "independent_validation": False,
            "holdout_not_accessed": True,
            "live_authorized": False,
        }.items():
            if two_phase.get(key) != expected:
                raise Vt08R315AuthorityError(f"R3.14 evidence mismatch: {key}")
        if two_phase.get("methodology_fingerprints") != [_METHOD]:
            raise Vt08R315AuthorityError("R3.14 methodology mismatch")
        if two_phase.get("source_contract_fingerprints") != [_SOURCE]:
            raise Vt08R315AuthorityError("R3.14 source contract mismatch")

    def digest(self) -> TraderLabEvidenceDigest:
        payload = {
            "schema": "qore.vt08.r3.15.official-governed-input.v1",
            "holdout": self.holdout,
            "adaptive_risk_policy": self.adaptive_risk_policy,
            "adaptive_monte_carlo_b_combined": self.adaptive_monte_carlo_b_combined,
            "two_phase": self.two_phase,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return TraderLabEvidenceDigest(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class Vt08R315AuthorityIssuance:
    gate: TraderLabGovernedGate
    authority_kind: TraderLabGovernedAuthorityKind
    authority_name: str
    evidence: TraderLabGovernedGateEvidence
    proof: TraderLabGovernedAuthenticityProof
    reference: TraderLabEvidenceReference
    cibo_review: CiboDevelopmentReview | None = None


def _manifest(candidate: TraderLabCandidateBinding) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in candidate.strategy_binding.manifest.parameters:
        if item.name.startswith("trader.") and type(item.value) is str:
            values[item.name] = item.value
    return values


def _issue(
    candidate: TraderLabCandidateBinding,
    official: Vt08R315OfficialEvidence,
    *,
    gate: TraderLabGovernedGate,
    decided_at: datetime,
    extra: object,
    cibo_review: CiboDevelopmentReview | None = None,
) -> Vt08R315AuthorityIssuance:
    validate_vt08_r315_candidate(candidate)
    official.__post_init__()
    if type(decided_at) is not datetime or decided_at.tzinfo is None:
        raise Vt08R315AuthorityError("authority decided_at must be timezone-aware")
    authority_kind, authority_id, authority_name = _AUTHORITY[gate]
    digest = TraderLabEvidenceDigest(
        sha256(
            json.dumps(
                {
                    "schema": "qore.vt08.r3.15.authority-decision.v1",
                    "candidate": candidate.fingerprint.value,
                    "gate": gate.value,
                    "official": official.digest().value,
                    "extra": extra,
                },
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
                default=str,
            ).encode("utf-8")
        ).hexdigest()
    )
    evidence_id = TraderLabGovernedGateEvidenceId(
        uuid5(NAMESPACE_URL, f"qore:vt08:r315:{gate.value}:{digest.value}")
    )
    fingerprint = compute_trader_lab_governed_gate_fingerprint(
        evidence_id=evidence_id,
        gate=gate,
        authority_kind=authority_kind,
        candidate=candidate,
        authority_id=authority_id,
        authority_name=authority_name,
        decision=TraderLabGovernedDecision.APPROVED,
        decided_at=decided_at,
        authority_evidence_digest=digest,
    )
    evidence = TraderLabGovernedGateEvidence(
        evidence_id=evidence_id,
        gate=gate,
        authority_kind=authority_kind,
        candidate=candidate,
        authority_id=authority_id,
        authority_name=authority_name,
        decision=TraderLabGovernedDecision.APPROVED,
        decided_at=decided_at,
        authority_evidence_digest=digest,
        fingerprint=fingerprint,
    )
    proof_fingerprint = compute_trader_lab_governed_authenticity_proof_fingerprint(
        evidence_fingerprint=fingerprint,
        candidate=candidate,
        gate=gate,
        authority_kind=authority_kind,
        issuer_id=authority_id,
        issued_at=decided_at,
    )
    proof = object.__new__(TraderLabGovernedAuthenticityProof)
    object.__setattr__(proof, "evidence_fingerprint", fingerprint)
    object.__setattr__(proof, "candidate", candidate)
    object.__setattr__(proof, "gate", gate)
    object.__setattr__(proof, "authority_kind", authority_kind)
    object.__setattr__(proof, "issuer_id", authority_id)
    object.__setattr__(proof, "issued_at", decided_at)
    object.__setattr__(proof, "proof_fingerprint", proof_fingerprint)
    object.__setattr__(proof, "_issued", True)
    proof.__post_init__()
    verified = verify_governed_gate_evidence(candidate, evidence, proof)
    if isinstance(verified, Failure):
        raise Vt08R315AuthorityError(f"{gate.value} proof verification failed")
    return Vt08R315AuthorityIssuance(
        gate=gate,
        authority_kind=authority_kind,
        authority_name=authority_name,
        evidence=evidence,
        proof=proof,
        reference=verified.value,
        cibo_review=cibo_review,
    )


def issue_vt08_r315_robustness(
    lifecycle: TraderLabLifecycle,
    official: Vt08R315OfficialEvidence,
    *,
    decided_at: datetime,
) -> Vt08R315AuthorityIssuance:
    validate_trader_lab_lifecycle(lifecycle)
    if lifecycle.state is not TraderLabState.OOS_QUALIFIED:
        raise Vt08R315AuthorityError("Robustness requires post-OOS lifecycle")
    primary = _object(
        official.adaptive_monte_carlo_b_combined.get("primary_0_50bp"),
        "R3.12 primary MC",
    )
    return _issue(
        lifecycle.candidate,
        official,
        gate=TraderLabGovernedGate.STRESS_REVIEW,
        decided_at=decided_at,
        extra={
            "policy": "vt08-r315-r312-robustness-v1",
            "breach_probability": primary["any_prop_firm_breach_probability"],
            "maximum_drawdown": primary["maximum_drawdown"],
        },
    )


def issue_vt08_r315_risk(
    lifecycle: TraderLabLifecycle,
    official: Vt08R315OfficialEvidence,
    *,
    decided_at: datetime,
) -> Vt08R315AuthorityIssuance:
    validate_trader_lab_lifecycle(lifecycle)
    if lifecycle.state is not TraderLabState.MONTE_CARLO_QUALIFIED:
        raise Vt08R315AuthorityError("Risk requires post-MONTE_CARLO lifecycle")
    risk_gate = _object(official.holdout.get("risk_policy"), "holdout risk_policy")
    if risk_gate.get("approved") is not True:
        raise Vt08R315AuthorityError("Risk did not approve the frozen policy")
    return _issue(
        lifecycle.candidate,
        official,
        gate=TraderLabGovernedGate.RISK_REVIEW,
        decided_at=decided_at,
        extra={
            "validation_policy": risk_gate,
            "funded_policy_id": "balanced-adaptive-v1",
            "funded_policy_fingerprint": _RISK_POLICY_FINGERPRINT,
        },
    )


_CIBO_STAGE = {
    TraderLabStage.REPLAY: CiboLabEvidenceStage.REPLAY,
    TraderLabStage.FAST_FORWARD: CiboLabEvidenceStage.FAST_FORWARD,
    TraderLabStage.OOS: CiboLabEvidenceStage.OOS,
    TraderLabStage.STRESS: CiboLabEvidenceStage.STRESS,
    TraderLabStage.MONTE_CARLO: CiboLabEvidenceStage.MONTE_CARLO,
    TraderLabStage.RISK_REVIEW: CiboLabEvidenceStage.RISK,
}


def _cibo_ref(reference: TraderLabEvidenceReference, prefix: str) -> CiboEvidenceRef:
    validate_trader_lab_evidence_reference(reference)
    return CiboEvidenceRef(
        f"lab:{prefix}:{reference.reference_id}:{reference.content_digest.value}"
    )


def issue_vt08_b01_r315_cibo(
    lifecycle: TraderLabLifecycle,
    official: Vt08R315OfficialEvidence,
    economic_evidence: TraderLabEvidenceReference,
    *,
    decided_at: datetime,
) -> Vt08R315AuthorityIssuance:
    validate_trader_lab_lifecycle(lifecycle)
    if lifecycle.state is not TraderLabState.RISK_REVIEWED:
        raise Vt08R315AuthorityError("CIBO requires post-Risk lifecycle")
    validate_trader_lab_evidence_reference(economic_evidence)
    if economic_evidence.kind is not TraderLabEvidenceKind.ECONOMIC_EVALUATION:
        raise Vt08R315AuthorityError("CIBO requires B01 economic evidence")
    candidate = lifecycle.candidate
    validate_vt08_r315_candidate(candidate)
    values = _manifest(candidate)
    certified = tuple(
        CiboLabEvidenceRef(
            stage=_CIBO_STAGE[item.stage],
            ref=_cibo_ref(item.evidence.source_reference, item.stage.value),
        )
        for item in lifecycle.qualifications
        if item.stage in _CIBO_STAGE
    ) + (
        CiboLabEvidenceRef(
            stage=CiboLabEvidenceStage.ECONOMIC,
            ref=_cibo_ref(economic_evidence, "economic"),
        ),
    )
    identity = ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(
            compute_trader_identity_family(DemoTradingTraderCode("vt-08"))
        ),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v3.8"),
        software_revision=candidate.strategy_binding.run.software_revision,
    )
    built = build_cibo_trader_capability_profile(
        trader_identity=identity,
        config_fingerprint=CiboTraderConfigFingerprint(
            values["trader.config_fingerprint"]
        ),
        specialty=CiboSpecialtyCode("ttrades-h4-po3-b01"),
        qualified_markets=tuple(CiboTradeableMarketRef(item) for item in _MARKETS),
        qualified_timeframes=tuple(
            CiboTimeframeCode(item.lower()) for item in _TIMEFRAMES
        ),
        certified_lab_evidence=certified,
        certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
        freshness=CiboEvidenceFreshness(
            state=CiboEvidenceFreshnessState.CURRENT,
            as_of=decided_at,
        ),
        limitations=("demo-only", "portfolio-order-composition-pending"),
    )
    if isinstance(built, Failure):
        raise Vt08R315AuthorityError(f"B01 CIBO profile failed: {built.error}")
    reviewed = review_capability_profile(
        built.value,
        reviewed_at=decided_at,
        expected_identity=identity,
        expected_config_fingerprint=values["trader.config_fingerprint"],
    )
    if isinstance(reviewed, Failure):
        raise Vt08R315AuthorityError(f"B01 CIBO review failed: {reviewed.error}")
    if reviewed.value.recommendation is not CiboDevelopmentRecommendation.RECOMMEND_PROMOTION:
        raise Vt08R315AuthorityError("B01 CIBO did not recommend promotion")
    profile = reviewed.value.profile
    if tuple(item.value for item in profile.qualified_markets) != _MARKETS:
        raise Vt08R315AuthorityError("B01 CIBO market binding mismatch")
    if tuple(item.value for item in profile.qualified_timeframes) != ("h4", "m15"):
        raise Vt08R315AuthorityError("B01 CIBO timeframe binding mismatch")
    return _issue(
        candidate,
        official,
        gate=TraderLabGovernedGate.CIBO_REVIEW,
        decided_at=decided_at,
        extra=reviewed.value.logical_values(),
        cibo_review=reviewed.value,
    )


def issue_vt08_r315_independent_validation(
    lifecycle: TraderLabLifecycle,
    official: Vt08R315OfficialEvidence,
    economic_evidence: TraderLabEvidenceReference,
    *,
    decided_at: datetime,
) -> Vt08R315AuthorityIssuance:
    validate_trader_lab_lifecycle(lifecycle)
    if lifecycle.state is not TraderLabState.CIBO_REVIEWED:
        raise Vt08R315AuthorityError("Independent Validation requires post-CIBO lifecycle")
    expected = MANDATORY_STAGES[: MANDATORY_STAGES.index(TraderLabStage.INDEPENDENT_VALIDATION)]
    if lifecycle.completed_stages != expected:
        raise Vt08R315AuthorityError("Independent Validation requires the complete prefix")
    for qualification in lifecycle.qualifications:
        reference = qualification.evidence.source_reference
        if evidence_kind_is_external_authenticated(reference.kind):
            validate_trader_lab_evidence_reference(reference)
            if reference.external_authenticity_proof is None:
                raise Vt08R315AuthorityError("governed prefix lacks authority proof")
    validate_trader_lab_evidence_reference(economic_evidence)
    if economic_evidence.strategy_binding_fingerprint != (
        lifecycle.candidate.strategy_binding.binding_fingerprint.value
    ):
        raise Vt08R315AuthorityError("economic lineage does not bind B01 candidate")
    if official.holdout.get("independent_validation") is not True:
        raise Vt08R315AuthorityError("official holdout is not independently validated")
    return _issue(
        lifecycle.candidate,
        official,
        gate=TraderLabGovernedGate.INDEPENDENT_VALIDATION,
        decided_at=decided_at,
        extra={
            "checks": (
                "candidate_identity",
                "immutable_artifact_lineage",
                "canonical_stage_order",
                "governed_authority_authenticity",
                "holdout_consumed_once",
                "methodology_not_mutated",
                "risk_policy_not_weakened",
                "demo_only",
            ),
            "economic_reference": economic_evidence.logical_values(),
        },
    )
