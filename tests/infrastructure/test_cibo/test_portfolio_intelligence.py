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
from qore.infrastructure.cibo.portfolio_intelligence import (
    CiboAllocationConclusion,
    CiboAllocationRecommendation,
    CiboPortfolioIntelligence,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_PORTFOLIO = CiboPortfolioIntelligence()


def _dependent_evidence() -> CiboFunctionalEvidence:
    return dependent_evidence(
        CiboGovernedEvidenceKind.ECONOMIC,
        evidence_refs=(CiboEvidenceRef("evidence:allocation"),),
        as_of=_NOW,
        reasons=("external.authority.required",),
    )


def _insufficient_evidence() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.INSUFFICIENT,
        evidence_refs=(),
        as_of=_NOW,
        reasons=("insufficient",),
    )


def test_recommend_dependent_evidence_abstains() -> None:
    # Correction 003: without an authority-rooted receipt CIBO cannot conclude a
    # diversified allocation; evidence-dependent inputs abstain rather than
    # certifying an unauthenticated allocation.
    result = _PORTFOLIO.recommend(
        _dependent_evidence(),
        participation_refs=(CiboEvidenceRef("evidence:participant"),),
        allocation_code="portfolio.alloc.v1",
        recommended_at=_NOW,
    )
    assert isinstance(result, Success)
    recommendation = result.value
    assert recommendation.conclusion is CiboAllocationConclusion.INSUFFICIENT_EVIDENCE
    assert recommendation.authority is CiboFunctionalAuthority.ABSTENTION
    assert not hasattr(recommendation, "order")
    assert not hasattr(recommendation, "intent")


def test_recommend_insufficient_evidence_abstains() -> None:
    result = _PORTFOLIO.recommend(
        _insufficient_evidence(),
        participation_refs=(),
        allocation_code="portfolio.alloc.v1",
        recommended_at=_NOW,
    )
    assert isinstance(result, Success)
    recommendation = result.value
    assert recommendation.conclusion is CiboAllocationConclusion.INSUFFICIENT_EVIDENCE
    assert recommendation.authority is CiboFunctionalAuthority.ABSTENTION


def test_recommend_rejects_wrong_type_evidence() -> None:
    result = _PORTFOLIO.recommend(
        cast(CiboFunctionalEvidence, object()),
        participation_refs=(),
        allocation_code="portfolio.alloc.v1",
        recommended_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_recommend_rejects_reflectively_corrupted_evidence() -> None:
    corrupted = object.__new__(CiboFunctionalEvidence)
    object.__setattr__(corrupted, "status", CiboEvidenceStatus.SUFFICIENT)
    object.__setattr__(corrupted, "evidence_refs", ("not-a-ref",))
    object.__setattr__(corrupted, "as_of", _NOW)
    object.__setattr__(corrupted, "dependency_kind", None)
    object.__setattr__(corrupted, "reasons", ())
    result = _PORTFOLIO.recommend(
        corrupted,
        participation_refs=(),
        allocation_code="portfolio.alloc.v1",
        recommended_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_concentrated_direct_construction_requires_sufficient_evidence() -> None:
    # A CONCENTRATED conclusion requires SUFFICIENT (authority-rooted) evidence,
    # which CIBO cannot manufacture; evidence-dependent backing fails closed.
    with pytest.raises(CiboFunctionalValidationError):
        CiboAllocationRecommendation(
            allocation_code="portfolio.concentrated",
            participation_refs=(CiboEvidenceRef("evidence:participant"),),
            conclusion=CiboAllocationConclusion.CONCENTRATED,
            evidence=_dependent_evidence(),
            authority=CiboFunctionalAuthority.RECOMMENDATION,
            recommended_at=_NOW,
        )


def test_repeated_identical_input_equal_logical_values() -> None:
    left = _PORTFOLIO.recommend(
        _dependent_evidence(),
        participation_refs=(CiboEvidenceRef("evidence:participant"),),
        allocation_code="portfolio.alloc.v1",
        recommended_at=_NOW,
    )
    right = _PORTFOLIO.recommend(
        _dependent_evidence(),
        participation_refs=(CiboEvidenceRef("evidence:participant"),),
        allocation_code="portfolio.alloc.v1",
        recommended_at=_NOW,
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


def test_logical_values_contain_no_secrets() -> None:
    result = _PORTFOLIO.recommend(
        _dependent_evidence(),
        participation_refs=(CiboEvidenceRef("evidence:participant"),),
        allocation_code="portfolio.alloc.v1",
        recommended_at=_NOW,
    )
    assert isinstance(result, Success)
    projection = repr(result.value.logical_values())
    for secret in ("secret", "token", "password", "private_key", "bearer"):
        assert secret not in projection
