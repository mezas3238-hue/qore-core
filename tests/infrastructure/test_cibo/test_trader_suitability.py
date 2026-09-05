"""D3 closure: Market-Trader Suitability + Development/Degradation loop.

CF-03/CF-04 ownership. The suitability answer is evidence-bound and fails closed
on insufficient/contradictory/stale market evidence; a degraded/suspended exact
version is DEGRADED regardless of market evidence. The individualized development
plan is advisory and can never promote, approve Risk, or grant DEMO eligibility.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.trader_suitability import (
    CiboCurriculumItem,
    CiboCurriculumKind,
    CiboDevelopmentAction,
    CiboDevelopmentPlan,
    CiboSuitabilityAssessment,
    CiboSuitabilityDisposition,
    assess_market_trader_suitability,
    plan_trader_development,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboOperatingAction,
    CiboOperatingCondition,
    CiboRegimeEvidenceRef,
    CiboRegimeKind,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)


def _ref(name: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(f"evidence:{name}")


def _identity(suffix: str = "vt01") -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(f"virtual.trader.{suffix}"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _profile(
    *,
    suffix: str = "vt01",
    fingerprint: int = 1,
    state: CiboCertificationState = CiboCertificationState.EVIDENCE_COLLECTED,
    freshness_state: CiboEvidenceFreshnessState = CiboEvidenceFreshnessState.CURRENT,
    regime_evidence: tuple[CiboRegimeEvidenceRef, ...] = (),
    operating_conditions: tuple[CiboOperatingCondition, ...] = (),
) -> CiboTraderCapabilityProfile:
    result = build_cibo_trader_capability_profile(
        trader_identity=_identity(suffix),
        config_fingerprint=CiboTraderConfigFingerprint(f"{fingerprint:064x}"),
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        regime_evidence=regime_evidence,
        operating_conditions=operating_conditions,
        certification_state=state,
        freshness=CiboEvidenceFreshness(state=freshness_state, as_of=_NOW),
    )
    assert isinstance(result, Success)
    return result.value


def _dependent() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
        evidence_refs=(_ref("market"),),
        as_of=_NOW,
        dependency_kind=CiboGovernedEvidenceKind.MARKET,
        reasons=("external.authority.required",),
    )


def _contradictory() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.CONTRADICTORY,
        evidence_refs=(_ref("market-a"), _ref("market-b")),
        as_of=_NOW,
    )


def _stale() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.STALE,
        evidence_refs=(_ref("market"),),
        as_of=_NOW,
        reasons=("evidence.stale",),
    )


# --- Suitability ---


def test_dependent_market_evidence_fails_closed() -> None:
    result = assess_market_trader_suitability(
        _profile(),
        current_regime=CiboRegimeKind.FAVORABLE,
        market_evidence=_dependent(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is CiboSuitabilityDisposition.INSUFFICIENT_EVIDENCE
    assert result.value.authority is CiboFunctionalAuthority.OBSERVATION
    # exact version binding is preserved verbatim.
    assert result.value.trader_identity == _identity()
    assert result.value.config_fingerprint == CiboTraderConfigFingerprint(f"{1:064x}")


def test_contradictory_market_evidence_fails_closed() -> None:
    result = assess_market_trader_suitability(
        _profile(),
        current_regime=CiboRegimeKind.FAVORABLE,
        market_evidence=_contradictory(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is CiboSuitabilityDisposition.CONTRADICTORY


def test_stale_market_evidence_fails_closed() -> None:
    result = assess_market_trader_suitability(
        _profile(),
        current_regime=CiboRegimeKind.WEAK,
        market_evidence=_stale(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is CiboSuitabilityDisposition.INSUFFICIENT_EVIDENCE


def test_suspended_trader_is_degraded_regardless_of_market() -> None:
    profile = _profile(
        state=CiboCertificationState.SUSPENDED,
        regime_evidence=(CiboRegimeEvidenceRef(CiboRegimeKind.FAVORABLE, _ref("f")),),
    )
    result = assess_market_trader_suitability(
        profile,
        current_regime=CiboRegimeKind.FAVORABLE,
        market_evidence=_dependent(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is CiboSuitabilityDisposition.DEGRADED


def test_blocking_operating_condition_is_degraded() -> None:
    profile = _profile(
        operating_conditions=(
            CiboOperatingCondition(
                action=CiboOperatingAction.RETURN_TO_LAB,
                reason_code="drift",
                evidence_ref=_ref("drift-evidence"),
            ),
        ),
    )
    result = assess_market_trader_suitability(
        profile,
        current_regime=CiboRegimeKind.FAVORABLE,
        market_evidence=_dependent(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is CiboSuitabilityDisposition.DEGRADED


def test_stale_profile_freshness_fails_closed() -> None:
    profile = _profile(freshness_state=CiboEvidenceFreshnessState.STALE)
    result = assess_market_trader_suitability(
        profile,
        current_regime=CiboRegimeKind.FAVORABLE,
        market_evidence=_dependent(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is CiboSuitabilityDisposition.INSUFFICIENT_EVIDENCE


def test_future_market_evidence_rejected() -> None:
    future = CiboFunctionalEvidence(
        status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
        evidence_refs=(_ref("market"),),
        as_of=datetime(2026, 8, 10, 0, 0, tzinfo=UTC),
        dependency_kind=CiboGovernedEvidenceKind.MARKET,
        reasons=("external.authority.required",),
    )
    result = assess_market_trader_suitability(
        _profile(),
        current_regime=CiboRegimeKind.FAVORABLE,
        market_evidence=future,
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_value_equal_regime_enum_laundering_rejected() -> None:
    class FakeRegime(str):
        pass

    result = assess_market_trader_suitability(
        _profile(),
        current_regime=FakeRegime("favorable"),  # type: ignore[arg-type]
        market_evidence=_dependent(),
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_wrong_market_evidence_type_rejected() -> None:
    result = assess_market_trader_suitability(
        _profile(),
        current_regime=CiboRegimeKind.FAVORABLE,
        market_evidence="not-evidence",  # type: ignore[arg-type]
        assessed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_suitability_constructor_rejects_non_observation_authority() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboSuitabilityAssessment(
            trader_identity=_identity(),
            config_fingerprint=CiboTraderConfigFingerprint(f"{1:064x}"),
            current_regime=CiboRegimeKind.FAVORABLE,
            market_evidence=_dependent(),
            disposition=CiboSuitabilityDisposition.INSUFFICIENT_EVIDENCE,
            unsupported_dimensions=(),
            uncertainty_codes=(),
            assessed_at=_NOW,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
        )


def test_suitability_constructor_rejects_positive_disposition_without_sufficient() -> None:
    # Constructor/deriver parity: a positive suitability outcome is reserved for
    # externally injected SUFFICIENT evidence; a dependent (non-sufficient) market
    # assessment must not be able to mint SUITABLE by direct construction.
    with pytest.raises(CiboFunctionalValidationError):
        CiboSuitabilityAssessment(
            trader_identity=_identity(),
            config_fingerprint=CiboTraderConfigFingerprint(f"{1:064x}"),
            current_regime=CiboRegimeKind.FAVORABLE,
            market_evidence=_dependent(),
            disposition=CiboSuitabilityDisposition.SUITABLE,
            unsupported_dimensions=(),
            uncertainty_codes=(),
            assessed_at=_NOW,
            authority=CiboFunctionalAuthority.OBSERVATION,
        )


def test_suitability_constructor_rejects_contradictory_without_contradiction() -> None:
    # A CONTRADICTORY disposition requires contradictory market evidence.
    with pytest.raises(CiboFunctionalValidationError):
        CiboSuitabilityAssessment(
            trader_identity=_identity(),
            config_fingerprint=CiboTraderConfigFingerprint(f"{1:064x}"),
            current_regime=CiboRegimeKind.FAVORABLE,
            market_evidence=_dependent(),
            disposition=CiboSuitabilityDisposition.CONTRADICTORY,
            unsupported_dimensions=(),
            uncertainty_codes=(),
            assessed_at=_NOW,
            authority=CiboFunctionalAuthority.OBSERVATION,
        )


def test_suitability_constructor_rejects_postdating_market_evidence() -> None:
    # No hindsight laundering: the constructor must reject market evidence whose
    # as_of postdates the assessment instant (mirrors the builder boundary).
    future = CiboFunctionalEvidence(
        status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
        evidence_refs=(_ref("market"),),
        as_of=datetime(2026, 8, 10, 0, 0, tzinfo=UTC),
        dependency_kind=CiboGovernedEvidenceKind.MARKET,
        reasons=("external.authority.required",),
    )
    with pytest.raises(CiboFunctionalValidationError):
        CiboSuitabilityAssessment(
            trader_identity=_identity(),
            config_fingerprint=CiboTraderConfigFingerprint(f"{1:064x}"),
            current_regime=CiboRegimeKind.FAVORABLE,
            market_evidence=future,
            disposition=CiboSuitabilityDisposition.INSUFFICIENT_EVIDENCE,
            unsupported_dimensions=(),
            uncertainty_codes=(),
            assessed_at=_NOW,
            authority=CiboFunctionalAuthority.OBSERVATION,
        )


# --- Development plan / degradation loop ---


def _curriculum() -> tuple[CiboCurriculumItem, ...]:
    return (
        CiboCurriculumItem(
            kind=CiboCurriculumKind.REPLAY,
            description_code="replay-baseline",
            evidence_refs=(_ref("replay"),),
        ),
        CiboCurriculumItem(
            kind=CiboCurriculumKind.ERROR_REMEDIATION,
            description_code="error-remediation",
            evidence_refs=(_ref("error"),),
            requalification_evidence=(_ref("requalify"),),
        ),
    )


def test_development_plan_retrain_requires_requalification() -> None:
    result = plan_trader_development(
        _profile(),
        action=CiboDevelopmentAction.RETRAIN,
        curricula=_curriculum(),
        degradation_evidence=_dependent(),
        requalification_evidence=(_ref("requalify"),),
        reasons=("calibration-drift",),
        planned_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.action is CiboDevelopmentAction.RETRAIN
    assert result.value.authority is CiboFunctionalAuthority.RECOMMENDATION


def test_development_plan_retrain_without_requalification_rejected() -> None:
    result = plan_trader_development(
        _profile(),
        action=CiboDevelopmentAction.RETRAIN,
        curricula=_curriculum(),
        degradation_evidence=_dependent(),
        requalification_evidence=(),
        reasons=("calibration-drift",),
        planned_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_reduce_requires_degradation_evidence() -> None:
    result = plan_trader_development(
        _profile(),
        action=CiboDevelopmentAction.REDUCE_PARTICIPATION,
        curricula=_curriculum(),
        degradation_evidence=None,
        requalification_evidence=(),
        reasons=("drawdown",),
        planned_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_return_to_lab_plan_is_advisory_only() -> None:
    result = plan_trader_development(
        _profile(),
        action=CiboDevelopmentAction.RETURN_TO_LAB,
        curricula=_curriculum(),
        degradation_evidence=_dependent(),
        requalification_evidence=(_ref("requalify"),),
        reasons=("unsupported-drift",),
        planned_at=_NOW,
    )
    assert isinstance(result, Success)
    # no promotion/eligibility member exists anywhere on the action catalog.
    assert not hasattr(CiboDevelopmentAction, "PROMOTE")
    assert not hasattr(CiboDevelopmentAction, "DEMO_ELIGIBLE")


def test_plan_cannot_predate_profile_evidence() -> None:
    result = plan_trader_development(
        _profile(),
        action=CiboDevelopmentAction.RETRAIN,
        curricula=_curriculum(),
        degradation_evidence=_dependent(),
        requalification_evidence=(_ref("requalify"),),
        reasons=("calibration-drift",),
        planned_at=datetime(2026, 8, 8, 0, 0, tzinfo=UTC),
    )
    assert isinstance(result, Failure)


def test_plan_preserves_exact_version_binding() -> None:
    result = plan_trader_development(
        _profile(suffix="vt02", fingerprint=7),
        action=CiboDevelopmentAction.RETRAIN,
        curricula=_curriculum(),
        degradation_evidence=_dependent(),
        requalification_evidence=(_ref("requalify"),),
        reasons=("calibration-drift",),
        planned_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.trader_identity == _identity("vt02")
    assert result.value.config_fingerprint == CiboTraderConfigFingerprint(f"{7:064x}")


def test_curriculum_duplicates_rejected() -> None:
    duplicate = (
        CiboCurriculumItem(
            kind=CiboCurriculumKind.REPLAY,
            description_code="replay-baseline",
            evidence_refs=(_ref("replay"),),
        ),
        CiboCurriculumItem(
            kind=CiboCurriculumKind.REPLAY,
            description_code="replay-baseline",
            evidence_refs=(_ref("replay"),),
        ),
    )
    with pytest.raises(CiboFunctionalValidationError):
        CiboDevelopmentPlan(
            trader_identity=_identity(),
            config_fingerprint=CiboTraderConfigFingerprint(f"{1:064x}"),
            action=CiboDevelopmentAction.RETRAIN,
            curricula=duplicate,
            degradation_evidence=_dependent(),
            requalification_evidence=(_ref("requalify"),),
            reasons=("calibration-drift",),
            planned_at=_NOW,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
        )


def test_development_plan_deterministic() -> None:
    def build() -> object:
        return plan_trader_development(
            _profile(),
            action=CiboDevelopmentAction.RETRAIN,
            curricula=_curriculum(),
            degradation_evidence=_dependent(),
            requalification_evidence=(_ref("requalify"),),
            reasons=("calibration-drift",),
            planned_at=_NOW,
        )

    first = build()
    second = build()
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_no_secrets_in_development_plan_logical_values() -> None:
    result = plan_trader_development(
        _profile(),
        action=CiboDevelopmentAction.RETRAIN,
        curricula=_curriculum(),
        degradation_evidence=_dependent(),
        requalification_evidence=(_ref("requalify"),),
        reasons=("calibration-drift",),
        planned_at=_NOW,
    )
    assert isinstance(result, Success)
    material = repr(result.value.logical_values())
    assert "token=" not in material
    assert "bearer " not in material
