from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.cibo_trader_manager import (
    CiboConcentrationConclusion,
    CiboConcentrationRecord,
    CiboDemoEligibilityEvidence,
    CiboDemoManagementState,
    CiboExperimentArm,
    CiboManagementAction,
    CiboManagerBlockedError,
    CiboRiskMode,
    CiboTraderManager,
    evaluate_team_concentration,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_MANAGER = CiboTraderManager()


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
    suffix: str = "vt01",
    fingerprint: int = 1,
    markets: tuple[str, ...] = ("EUR/USD",),
    state: CiboCertificationState = CiboCertificationState.EVIDENCE_COLLECTED,
    freshness_state: CiboEvidenceFreshnessState = CiboEvidenceFreshnessState.CURRENT,
    risk_envelope: tuple[CiboEvidenceRef, ...] = (),
) -> CiboTraderCapabilityProfile:
    result = build_cibo_trader_capability_profile(
        trader_identity=_identity(suffix),
        config_fingerprint=_fingerprint(fingerprint),
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=tuple(CiboTradeableMarketRef(m) for m in markets),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        risk_envelope=risk_envelope,
        certification_state=state,
        freshness=CiboEvidenceFreshness(state=freshness_state, as_of=_NOW),
    )
    assert isinstance(result, Success)
    return result.value


def _eligibility(
    profile: CiboTraderCapabilityProfile,
    *,
    arm: CiboExperimentArm = CiboExperimentArm.A,
    risk_mode: CiboRiskMode = CiboRiskMode.TRADERS_RISK_ONLY,
) -> CiboDemoEligibilityEvidence:
    return CiboDemoEligibilityEvidence(
        trader_identity=profile.trader_identity,
        config_fingerprint=profile.config_fingerprint,
        experiment_arm=arm,
        risk_mode=risk_mode,
        evidence_ref=CiboEvidenceRef("evidence:demo-eligible"),
        certified_at=_NOW,
    )


def test_select_exact_eligible_version() -> None:
    profile = _profile()
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    assert isinstance(result, Success)
    decision = result.value
    assert decision.state is CiboDemoManagementState.SELECTED
    assert decision.experiment_arm is CiboExperimentArm.A
    assert decision.risk_mode is CiboRiskMode.TRADERS_RISK_ONLY


def test_select_requires_demo_eligible_evidence() -> None:
    profile = _profile()
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


def test_select_rejects_identity_mismatch() -> None:
    profile = _profile()
    other = _profile(suffix="vt02", fingerprint=2)
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(other),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


def test_select_rejects_config_fingerprint_mismatch() -> None:
    profile = _profile()
    mismatched = CiboDemoEligibilityEvidence(
        trader_identity=profile.trader_identity,
        config_fingerprint=_fingerprint(999),
        experiment_arm=CiboExperimentArm.A,
        risk_mode=CiboRiskMode.TRADERS_RISK_ONLY,
        evidence_ref=CiboEvidenceRef("evidence:demo-eligible"),
        certified_at=_NOW,
    )
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=mismatched,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


def test_suspended_trader_cannot_be_selected() -> None:
    profile = _profile(state=CiboCertificationState.SUSPENDED)
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


def test_stale_evidence_trader_cannot_be_selected() -> None:
    profile = _profile(freshness_state=CiboEvidenceFreshnessState.STALE)
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


def test_managed_risk_requires_risk_envelope() -> None:
    profile = _profile()  # no risk envelope
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(
            profile,
            risk_mode=CiboRiskMode.CIBO_MANAGED_TRADERS_RISK,
        ),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


def test_managed_risk_with_risk_envelope_selects() -> None:
    profile = _profile(risk_envelope=(CiboEvidenceRef("evidence:risk-envelope"),))
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(
            profile,
            arm=CiboExperimentArm.B,
            risk_mode=CiboRiskMode.CIBO_MANAGED_TRADERS_RISK,
        ),
    )
    assert isinstance(result, Success)
    assert result.value.risk_mode is CiboRiskMode.CIBO_MANAGED_TRADERS_RISK
    assert result.value.experiment_arm is CiboExperimentArm.B


def test_suspend_retains_reasons_and_evidence() -> None:
    profile = _profile()
    evidence = CiboEvidenceRef("evidence:suspension")
    result = _MANAGER.decide(
        CiboManagementAction.SUSPEND,
        profile,
        decided_at=_NOW,
        reasons=("evidence-degraded",),
        evidence_refs=(evidence,),
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboDemoManagementState.SUSPENDED
    assert result.value.reasons == ("evidence-degraded",)
    assert result.value.evidence_refs == (evidence,)


def test_reduce_and_block_states() -> None:
    profile = _profile()
    reduced = _MANAGER.decide(
        CiboManagementAction.REDUCE,
        profile,
        decided_at=_NOW,
        reasons=("concentration",),
    )
    assert isinstance(reduced, Success)
    assert reduced.value.state is CiboDemoManagementState.REDUCED
    blocked = _MANAGER.decide(
        CiboManagementAction.BLOCK,
        profile,
        decided_at=_NOW,
        reasons=("policy-violation",),
    )
    assert isinstance(blocked, Success)
    assert blocked.value.state is CiboDemoManagementState.BLOCKED


def test_output_has_no_provider_native_execution_fields() -> None:
    profile = _profile()
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    assert isinstance(result, Success)
    decision = result.value
    assert not hasattr(decision, "order")
    assert not hasattr(decision, "intent")
    assert not hasattr(decision, "provider")
    assert not hasattr(decision, "instrument")
    assert not hasattr(decision, "quantity")


def test_concentration_requires_explicit_evidence() -> None:
    profile = _profile()
    assert evaluate_team_concentration((profile,), correlation_evidence=()) is None


def test_concentration_concludes_from_explicit_evidence() -> None:
    shared = _profile(markets=("EUR/USD", "GBP/USD"))
    other = _profile(suffix="vt02", fingerprint=2, markets=("EUR/USD", "USD/JPY"))
    evidence = (CiboEvidenceRef("evidence:correlation"),)
    conclusion = evaluate_team_concentration(
        (shared, other),
        correlation_evidence=evidence,
    )
    assert isinstance(conclusion, CiboConcentrationRecord)
    assert conclusion.conclusion is CiboConcentrationConclusion.CONCENTRATED
    assert conclusion.evidence_refs == evidence


def test_concentration_diversified_from_explicit_evidence() -> None:
    first = _profile(markets=("EUR/USD",))
    second = _profile(suffix="vt02", fingerprint=2, markets=("USD/JPY",))
    evidence = (CiboEvidenceRef("evidence:correlation"),)
    conclusion = evaluate_team_concentration(
        (first, second),
        correlation_evidence=evidence,
    )
    assert isinstance(conclusion, CiboConcentrationRecord)
    assert conclusion.conclusion is CiboConcentrationConclusion.DIVERSIFIED


def test_ab_arm_bound_to_decision() -> None:
    profile = _profile()
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile, arm=CiboExperimentArm.B),
    )
    assert isinstance(result, Success)
    assert result.value.experiment_arm is CiboExperimentArm.B


def test_deterministic_decision_equality() -> None:
    profile = _profile()
    left = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    right = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()
