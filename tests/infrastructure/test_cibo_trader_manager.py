from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboOperatingAction,
    CiboOperatingCondition,
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
    CiboManagerValidationError,
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
    operating_conditions: tuple[CiboOperatingCondition, ...] = (),
) -> CiboTraderCapabilityProfile:
    result = build_cibo_trader_capability_profile(
        trader_identity=_identity(suffix),
        config_fingerprint=_fingerprint(fingerprint),
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=tuple(CiboTradeableMarketRef(m) for m in markets),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        risk_envelope=risk_envelope,
        operating_conditions=operating_conditions,
        certification_state=state,
        freshness=CiboEvidenceFreshness(state=freshness_state, as_of=_NOW),
    )
    assert isinstance(result, Success)
    return result.value


def _operating(
    action: CiboOperatingAction,
    reason_code: str = "evidence-degraded",
) -> CiboOperatingCondition:
    return CiboOperatingCondition(action=action, reason_code=reason_code)


def _eligibility(
    profile: CiboTraderCapabilityProfile,
    *,
    arm: CiboExperimentArm = CiboExperimentArm.A,
    risk_mode: CiboRiskMode = CiboRiskMode.TRADERS_RISK_ONLY,
    certified_at: datetime = _NOW,
) -> CiboDemoEligibilityEvidence:
    return CiboDemoEligibilityEvidence(
        trader_identity=profile.trader_identity,
        config_fingerprint=profile.config_fingerprint,
        experiment_arm=arm,
        risk_mode=risk_mode,
        evidence_ref=CiboEvidenceRef("evidence:demo-eligible"),
        certified_at=certified_at,
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


# --- F1: contradictory operating evidence must never reach SELECTED ---

def test_select_rejects_suspend_operating_condition() -> None:
    profile = _profile(operating_conditions=(_operating(CiboOperatingAction.SUSPEND),))
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


def test_select_rejects_return_to_lab_operating_condition() -> None:
    profile = _profile(
        operating_conditions=(_operating(CiboOperatingAction.RETURN_TO_LAB, "retrain"),)
    )
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


@pytest.mark.parametrize(
    "action",
    [CiboOperatingAction.REDUCE, CiboOperatingAction.ABSTAIN],
)
def test_select_allows_non_blocking_operating_condition(
    action: CiboOperatingAction,
) -> None:
    profile = _profile(operating_conditions=(_operating(action),))
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    assert isinstance(result, Success)
    assert result.value.state is CiboDemoManagementState.SELECTED


# --- F2: non-SELECT actions must bind eligibility and never launder attribution ---

@pytest.mark.parametrize(
    "action",
    [
        CiboManagementAction.REDUCE,
        CiboManagementAction.SUSPEND,
        CiboManagementAction.BLOCK,
    ],
)
def test_non_select_rejects_cross_version_eligibility(
    action: CiboManagementAction,
) -> None:
    profile = _profile()
    other = _profile(suffix="vt02", fingerprint=2)
    result = _MANAGER.decide(
        action,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(other),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


@pytest.mark.parametrize(
    "action",
    [
        CiboManagementAction.REDUCE,
        CiboManagementAction.SUSPEND,
        CiboManagementAction.BLOCK,
    ],
)
def test_non_select_rejects_cross_config_eligibility(
    action: CiboManagementAction,
) -> None:
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
        action,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=mismatched,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


@pytest.mark.parametrize(
    "action",
    [
        CiboManagementAction.REDUCE,
        CiboManagementAction.SUSPEND,
        CiboManagementAction.BLOCK,
    ],
)
def test_non_select_retains_bound_eligibility_attribution(
    action: CiboManagementAction,
) -> None:
    profile = _profile()
    result = _MANAGER.decide(
        action,
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
    assert result.value.experiment_arm is CiboExperimentArm.B
    assert result.value.risk_mode is CiboRiskMode.CIBO_MANAGED_TRADERS_RISK


@pytest.mark.parametrize(
    "action",
    [
        CiboManagementAction.REDUCE,
        CiboManagementAction.SUSPEND,
        CiboManagementAction.BLOCK,
    ],
)
def test_non_select_never_fabricates_attribution_without_eligibility(
    action: CiboManagementAction,
) -> None:
    profile = _profile()
    result = _MANAGER.decide(
        action,
        profile,
        decided_at=_NOW,
        reasons=("evidence-degraded",),
    )
    assert isinstance(result, Success)
    assert result.value.experiment_arm is None
    assert result.value.risk_mode is None


# --- F4: wrong-runtime-type eligibility/concentration must fail closed as typed Failure ---

@pytest.mark.parametrize(
    "action",
    [
        CiboManagementAction.SELECT,
        CiboManagementAction.REDUCE,
        CiboManagementAction.SUSPEND,
        CiboManagementAction.BLOCK,
    ],
)
def test_object_eligibility_returns_typed_failure_all_actions(
    action: CiboManagementAction,
) -> None:
    profile = _profile()
    result = _MANAGER.decide(
        action,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=object(),  # type: ignore[arg-type]
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerValidationError)


@pytest.mark.parametrize("bad", [True, "eligibility", 123, []])
def test_wrong_type_eligibility_variants_return_typed_failure(bad: object) -> None:
    profile = _profile()
    result = _MANAGER.decide(
        CiboManagementAction.REDUCE,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=bad,  # type: ignore[arg-type]
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerValidationError)


def test_lookalike_eligibility_cannot_launder_attribution() -> None:
    profile = _profile()
    lookalike = SimpleNamespace(
        trader_identity=profile.trader_identity,
        config_fingerprint=profile.config_fingerprint,
        experiment_arm=CiboExperimentArm.B,
        risk_mode=CiboRiskMode.CIBO_MANAGED_TRADERS_RISK,
    )
    result = _MANAGER.decide(
        CiboManagementAction.SUSPEND,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=lookalike,  # type: ignore[arg-type]
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerValidationError)


def test_reflectively_corrupted_eligibility_returns_typed_failure() -> None:
    profile = _profile()
    valid = _eligibility(profile)
    corrupted = object.__new__(CiboDemoEligibilityEvidence)
    for field in dataclasses.fields(CiboDemoEligibilityEvidence):
        value = getattr(valid, field.name)
        if field.name == "certified_at":
            value = value.replace(tzinfo=None)
        object.__setattr__(corrupted, field.name, value)
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=corrupted,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerValidationError)


def test_wrong_type_concentration_returns_typed_failure() -> None:
    profile = _profile()
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
        concentration=object(),  # type: ignore[arg-type]
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerValidationError)


def test_reflectively_corrupted_concentration_returns_typed_failure() -> None:
    profile = _profile()
    corrupted = object.__new__(CiboConcentrationRecord)
    object.__setattr__(corrupted, "conclusion", CiboConcentrationConclusion.DIVERSIFIED)
    object.__setattr__(corrupted, "evidence_refs", ("not-a-ref",))
    result = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
        concentration=corrupted,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerValidationError)


# --- F3: temporal binding ---

@pytest.mark.parametrize(
    "action",
    [
        CiboManagementAction.SELECT,
        CiboManagementAction.REDUCE,
        CiboManagementAction.SUSPEND,
        CiboManagementAction.BLOCK,
    ],
)
def test_decision_cannot_predate_profile_evidence(
    action: CiboManagementAction,
) -> None:
    profile = _profile()
    past = _NOW - timedelta(microseconds=1)
    kwargs: dict[str, object] = {"decided_at": past, "reasons": ("demo-eligible",)}
    if action is CiboManagementAction.SELECT:
        kwargs["eligibility"] = _eligibility(profile)
    result = _MANAGER.decide(action, profile, **kwargs)  # type: ignore[arg-type]
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerValidationError)


@pytest.mark.parametrize(
    "action",
    [
        CiboManagementAction.REDUCE,
        CiboManagementAction.SUSPEND,
        CiboManagementAction.BLOCK,
    ],
)
def test_non_select_decision_cannot_predate_eligibility_certification(
    action: CiboManagementAction,
) -> None:
    profile = _profile()
    eligibility = _eligibility(profile, certified_at=_NOW + timedelta(hours=1))
    result = _MANAGER.decide(
        action,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=eligibility,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboManagerBlockedError)


def test_equality_timestamp_boundaries_pass() -> None:
    profile = _profile()
    selected = _MANAGER.decide(
        CiboManagementAction.SELECT,
        profile,
        decided_at=_NOW,
        reasons=("demo-eligible",),
        eligibility=_eligibility(profile),
    )
    assert isinstance(selected, Success)
    reduced = _MANAGER.decide(
        CiboManagementAction.REDUCE,
        profile,
        decided_at=_NOW,
        reasons=("concentration",),
    )
    assert isinstance(reduced, Success)


def test_manager_grants_no_execution_or_promotion_authority() -> None:
    assert not hasattr(_MANAGER, "execute")
    assert not hasattr(_MANAGER, "place_order")
    assert not hasattr(_MANAGER, "promote")
    assert not hasattr(_MANAGER, "authorize_risk")
