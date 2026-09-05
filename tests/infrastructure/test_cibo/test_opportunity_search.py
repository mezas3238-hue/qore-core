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
from qore.infrastructure.cibo.opportunity_search import (
    CiboOpportunityHypothesis,
    CiboOpportunitySearch,
    CiboOpportunityState,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_SEARCH = CiboOpportunitySearch()


def _ref(code: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(f"evidence:{code}")


def _evidence(
    status: CiboEvidenceStatus,
    *,
    refs: tuple[CiboEvidenceRef, ...] = (),
    reasons: tuple[str, ...] = ("assessment",),
) -> CiboFunctionalEvidence:
    if status is CiboEvidenceStatus.EVIDENCE_DEPENDENT:
        return dependent_evidence(
            CiboGovernedEvidenceKind.MARKET,
            evidence_refs=refs,
            as_of=_NOW,
            reasons=reasons or ("external.authority.required",),
        )
    return CiboFunctionalEvidence(
        status=status,
        evidence_refs=refs,
        as_of=_NOW,
        reasons=reasons,
    )


def _hypothesis(
    *,
    opportunity_code: str = "carry-arbitrage",
    refs: tuple[CiboEvidenceRef, ...] = (),
    status: CiboEvidenceStatus = CiboEvidenceStatus.INSUFFICIENT,
    state: CiboOpportunityState = CiboOpportunityState.HYPOTHESIS,
    authority: CiboFunctionalAuthority = CiboFunctionalAuthority.OPINION,
) -> CiboOpportunityHypothesis:
    return CiboOpportunityHypothesis(
        opportunity_code=opportunity_code,
        market_refs=refs,
        evidence=_evidence(status, refs=refs),
        state=state,
        authority=authority,
        declared_at=_NOW,
    )


def _corrupt(
    hypothesis: CiboOpportunityHypothesis,
    **overrides: object,
) -> CiboOpportunityHypothesis:
    base: dict[str, object] = {
        "opportunity_code": hypothesis.opportunity_code,
        "market_refs": hypothesis.market_refs,
        "evidence": hypothesis.evidence,
        "state": hypothesis.state,
        "authority": hypothesis.authority,
        "declared_at": hypothesis.declared_at,
    }
    corrupted = object.__new__(CiboOpportunityHypothesis)
    for name, value in base.items():
        object.__setattr__(corrupted, name, overrides.get(name, value))
    return corrupted


def test_validated_opportunity_rejects_dependent_evidence() -> None:
    # Correction 003: VALIDATED/RECOMMENDED require SUFFICIENT (authority-rooted)
    # evidence, which CIBO cannot manufacture; dependent evidence fails closed.
    ref = _ref("eur-usd")
    with pytest.raises(CiboFunctionalValidationError):
        _hypothesis(
            refs=(ref,),
            status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
            state=CiboOpportunityState.VALIDATED,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
        )


def test_hypothesis_stays_hypothesis_with_dependent_evidence() -> None:
    ref = _ref("eur-usd")
    hypothesis = _hypothesis(
        refs=(ref,),
        status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
        state=CiboOpportunityState.HYPOTHESIS,
        authority=CiboFunctionalAuthority.OPINION,
    )
    result = _SEARCH.evaluate(hypothesis)
    assert isinstance(result, Success)
    assert result.value.state is CiboOpportunityState.HYPOTHESIS


def test_validated_with_insufficient_evidence_rejected() -> None:
    ref = _ref("eur-usd")
    with pytest.raises(CiboFunctionalValidationError):
        _hypothesis(
            refs=(ref,),
            status=CiboEvidenceStatus.INSUFFICIENT,
            state=CiboOpportunityState.VALIDATED,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
        )


def test_fabricated_sufficiency_rejected() -> None:
    # A reflectively fabricated SUFFICIENT evidence can never mint a validated
    # hypothesis: the evaluator re-enters evidence validation and rejects it.
    ref = _ref("eur-usd")
    fabricated = object.__new__(CiboFunctionalEvidence)
    object.__setattr__(fabricated, "status", CiboEvidenceStatus.SUFFICIENT)
    object.__setattr__(fabricated, "evidence_refs", ())
    object.__setattr__(fabricated, "as_of", _NOW)
    object.__setattr__(fabricated, "dependency_kind", None)
    object.__setattr__(fabricated, "reasons", ())
    hypothesis = _hypothesis(
        refs=(ref,),
        status=CiboEvidenceStatus.INSUFFICIENT,
        state=CiboOpportunityState.HYPOTHESIS,
        authority=CiboFunctionalAuthority.OPINION,
    )
    result = _SEARCH.evaluate(_corrupt(hypothesis, evidence=fabricated))
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_hypothesis_requires_opinion_authority() -> None:
    ref = _ref("eur-usd")
    with pytest.raises(CiboFunctionalValidationError):
        CiboOpportunityHypothesis(
            opportunity_code="carry-arbitrage",
            market_refs=(ref,),
            evidence=_evidence(CiboEvidenceStatus.INSUFFICIENT, refs=(ref,)),
            state=CiboOpportunityState.HYPOTHESIS,
            authority=CiboFunctionalAuthority.RECOMMENDATION,
            declared_at=_NOW,
        )


def test_rejected_requires_abstention_authority() -> None:
    ref = _ref("eur-usd")
    with pytest.raises(CiboFunctionalValidationError):
        CiboOpportunityHypothesis(
            opportunity_code="carry-arbitrage",
            market_refs=(ref,),
            evidence=_evidence(CiboEvidenceStatus.INSUFFICIENT, refs=(ref,)),
            state=CiboOpportunityState.REJECTED,
            authority=CiboFunctionalAuthority.OPINION,
            declared_at=_NOW,
        )


def test_recommended_requires_recommendation_authority() -> None:
    ref = _ref("eur-usd")
    with pytest.raises(CiboFunctionalValidationError):
        CiboOpportunityHypothesis(
            opportunity_code="carry-arbitrage",
            market_refs=(ref,),
            evidence=_evidence(CiboEvidenceStatus.EVIDENCE_DEPENDENT, refs=(ref,)),
            state=CiboOpportunityState.RECOMMENDED,
            authority=CiboFunctionalAuthority.OPINION,
            declared_at=_NOW,
        )


def test_wrong_type_hypothesis_returns_typed_failure() -> None:
    bad = cast(CiboOpportunityHypothesis, object())
    result = _SEARCH.evaluate(bad)
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_malformed_nested_evidence_returns_typed_failure() -> None:
    ref = _ref("eur-usd")
    valid = _hypothesis(
        refs=(ref,),
        status=CiboEvidenceStatus.INSUFFICIENT,
        state=CiboOpportunityState.HYPOTHESIS,
        authority=CiboFunctionalAuthority.OPINION,
    )
    result = _SEARCH.evaluate(_corrupt(valid, evidence="not-evidence"))
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_repeated_identical_input_equal_logical_values() -> None:
    ref = _ref("eur-usd")
    hypothesis = _hypothesis(
        refs=(ref,),
        status=CiboEvidenceStatus.INSUFFICIENT,
        state=CiboOpportunityState.HYPOTHESIS,
        authority=CiboFunctionalAuthority.OPINION,
    )
    left = _SEARCH.evaluate(hypothesis)
    right = _SEARCH.evaluate(hypothesis)
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()
