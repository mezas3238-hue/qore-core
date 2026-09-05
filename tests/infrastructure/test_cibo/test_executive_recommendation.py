from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from _governed_evidence_fixtures import dependent_evidence

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.executive_recommendation import (
    CiboExecutiveRecommendation,
    CiboRecommendationDisposition,
    CiboRiskAwareComposer,
    CiboRiskContext,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_COMPOSER = CiboRiskAwareComposer()


def _ref(name: str = "evidence:functional-input") -> CiboEvidenceRef:
    return CiboEvidenceRef(name)


def _dependent_functional_evidence() -> CiboFunctionalEvidence:
    return dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(_ref(),),
        as_of=_NOW,
        reasons=("external.authority.required",),
    )


def _insufficient_functional_evidence() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.INSUFFICIENT,
        evidence_refs=(),
        as_of=_NOW,
        reasons=("not-enough-data",),
    )


def _risk_context() -> CiboRiskContext:
    return CiboRiskContext(
        risk_evidence=dependent_evidence(
            CiboGovernedEvidenceKind.RISK,
            evidence_refs=(_ref("evidence:risk"),),
            as_of=_NOW,
            reasons=("external.risk.authority",),
        ),
        risk_assessment_code="risk.assessment.concentration",
        assessed_at=_NOW,
    )


def test_compose_abstains_with_dependent_evidence_and_risk_context() -> None:
    # Correction 003: RECOMMEND requires SUFFICIENT (authority-rooted) evidence,
    # which CIBO cannot manufacture; dependent evidence fails closed to ABSTAIN.
    result = _COMPOSER.compose(
        recommendation_code="recommendation.volatility",
        functional_evidence=_dependent_functional_evidence(),
        risk_context=_risk_context(),
        composed_at=_NOW,
    )
    assert isinstance(result, Success)
    value = result.value
    assert value.disposition is CiboRecommendationDisposition.ABSTAIN
    assert value.authority is CiboFunctionalAuthority.ABSTENTION
    assert value.risk_context is not None
    assert value.logical_values()


def test_compose_abstains_when_risk_context_absent() -> None:
    # Without an authority root, ESCALATE (which requires SUFFICIENT) is also
    # unreachable; the composer fails closed to ABSTAIN.
    result = _COMPOSER.compose(
        recommendation_code="recommendation.volatility",
        functional_evidence=_dependent_functional_evidence(),
        risk_context=None,
        composed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is CiboRecommendationDisposition.ABSTAIN
    assert result.value.authority is CiboFunctionalAuthority.ABSTENTION


def test_compose_abstain_when_functional_evidence_insufficient() -> None:
    result = _COMPOSER.compose(
        recommendation_code="recommendation.volatility",
        functional_evidence=_insufficient_functional_evidence(),
        risk_context=_risk_context(),
        composed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is CiboRecommendationDisposition.ABSTAIN
    assert result.value.authority is CiboFunctionalAuthority.ABSTENTION


def test_recommend_without_risk_context_never_escalates_with_dependent_evidence() -> None:
    result = _COMPOSER.compose(
        recommendation_code="recommendation.volatility",
        functional_evidence=_dependent_functional_evidence(),
        risk_context=None,
        composed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.disposition is not CiboRecommendationDisposition.RECOMMEND
    assert result.value.disposition is not CiboRecommendationDisposition.ESCALATE
    assert result.value.disposition is CiboRecommendationDisposition.ABSTAIN


def test_output_has_no_risk_decision_field() -> None:
    result = _COMPOSER.compose(
        recommendation_code="recommendation.volatility",
        functional_evidence=_dependent_functional_evidence(),
        risk_context=_risk_context(),
        composed_at=_NOW,
    )
    assert isinstance(result, Success)
    value = result.value
    for forbidden in ("risk_decision", "decision", "outcome", "risk_policy", "approval"):
        assert not hasattr(value, forbidden)
    context = value.risk_context
    assert context is not None
    for forbidden in ("decision", "outcome", "approved", "blocked"):
        assert not hasattr(context, forbidden)


def test_compose_rejects_wrong_risk_context_type() -> None:
    result = _COMPOSER.compose(
        recommendation_code="recommendation.volatility",
        functional_evidence=_dependent_functional_evidence(),
        risk_context=cast(CiboRiskContext | None, object()),
        composed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_compose_rejects_corrupted_nested_risk_context() -> None:
    context = object.__new__(CiboRiskContext)
    object.__setattr__(context, "risk_evidence", ("not-evidence",))
    object.__setattr__(context, "risk_assessment_code", "risk.assessment.concentration")
    object.__setattr__(context, "assessed_at", _NOW)
    result = _COMPOSER.compose(
        recommendation_code="recommendation.volatility",
        functional_evidence=_dependent_functional_evidence(),
        risk_context=context,
        composed_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_risk_context_requires_risk_dependency_kind() -> None:
    # A MARKET-dependent evidence cannot stand in for Risk authority.
    with pytest.raises(CiboFunctionalValidationError):
        CiboRiskContext(
            risk_evidence=dependent_evidence(
                CiboGovernedEvidenceKind.MARKET,
                evidence_refs=(_ref("evidence:market"),),
                as_of=_NOW,
            ),
            risk_assessment_code="risk.assessment.concentration",
            assessed_at=_NOW,
        )


def test_risk_context_requires_dependent_status() -> None:
    # A non-dependent (e.g. INSUFFICIENT) risk assessment cannot become Risk context.
    with pytest.raises(CiboFunctionalValidationError):
        CiboRiskContext(
            risk_evidence=CiboFunctionalEvidence(
                status=CiboEvidenceStatus.INSUFFICIENT,
                evidence_refs=(),
                as_of=_NOW,
                reasons=("insufficient",),
            ),
            risk_assessment_code="risk.assessment.concentration",
            assessed_at=_NOW,
        )


def test_recommend_requires_recommendation_authority() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboExecutiveRecommendation(
            recommendation_code="recommendation.volatility",
            disposition=CiboRecommendationDisposition.RECOMMEND,
            functional_evidence=_dependent_functional_evidence(),
            risk_context=_risk_context(),
            composed_at=_NOW,
            authority=CiboFunctionalAuthority.ABSTENTION,
        )


def test_abstain_requires_abstention_authority() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboExecutiveRecommendation(
            recommendation_code="recommendation.volatility",
            disposition=CiboRecommendationDisposition.ABSTAIN,
            functional_evidence=_insufficient_functional_evidence(),
            risk_context=None,
            composed_at=_NOW,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
        )


def test_repeated_identical_compose_equal_logical_values() -> None:
    left = _COMPOSER.compose(
        recommendation_code="recommendation.volatility",
        functional_evidence=_dependent_functional_evidence(),
        risk_context=_risk_context(),
        composed_at=_NOW,
    )
    right = _COMPOSER.compose(
        recommendation_code="recommendation.volatility",
        functional_evidence=_dependent_functional_evidence(),
        risk_context=_risk_context(),
        composed_at=_NOW,
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


def test_composer_grants_no_risk_decision_authority() -> None:
    assert not hasattr(_COMPOSER, "decide")
    assert not hasattr(_COMPOSER, "approve")
    assert not hasattr(_COMPOSER, "authorize_risk")
    assert not hasattr(_COMPOSER, "execute")
