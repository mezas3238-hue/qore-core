from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from _governed_evidence_fixtures import dependent_evidence

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalBlockedError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.research_director import (
    CiboResearchDirector,
    CiboResearchPlan,
    CiboResearchStage,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_DIRECTOR = CiboResearchDirector()


def _ref(name: str = "evidence:research-input") -> CiboEvidenceRef:
    return CiboEvidenceRef(name)


def _dependent_evidence() -> CiboFunctionalEvidence:
    return dependent_evidence(
        CiboGovernedEvidenceKind.MARKET,
        evidence_refs=(_ref(),),
        as_of=_NOW,
        reasons=("external.authority.required",),
    )


def _insufficient_evidence() -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.INSUFFICIENT,
        evidence_refs=(),
        as_of=_NOW,
        reasons=("not-enough-data",),
    )


def _plan(
    *,
    stage: CiboResearchStage = CiboResearchStage.OBSERVATION,
    evidence: CiboFunctionalEvidence | None = None,
    updated_at: datetime = _NOW,
) -> CiboResearchPlan:
    return CiboResearchPlan(
        plan_code="research.plan.volatility",
        question_code="research.question.volatility-regime",
        hypothesis_code="research.hypothesis.mean-reversion",
        data_requirements=(_ref("evidence:research-data"),),
        stage=stage,
        evidence=_dependent_evidence() if evidence is None else evidence,
        updated_at=updated_at,
    )


def test_research_stage_lineage_order() -> None:
    expected = [
        "observation",
        "hypothesis",
        "formalization",
        "data",
        "experiment",
        "replay-backtest",
        "adversarial",
        "oos",
        "stress",
        "monte-carlo",
        "economic",
        "trader-lab",
        "demo",
    ]
    assert [stage.value for stage in CiboResearchStage] == expected


def test_advance_forward_one_stage() -> None:
    plan = _plan(stage=CiboResearchStage.OBSERVATION)
    result = _DIRECTOR.advance(
        plan,
        to_stage=CiboResearchStage.HYPOTHESIS,
        evidence=_dependent_evidence(),
        updated_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.stage is CiboResearchStage.HYPOTHESIS


def test_advance_to_demo_rejects_dependent_evidence() -> None:
    # Correction 003: terminal trader-lab/demo stages require SUFFICIENT
    # (authority-rooted) evidence; evidence-dependent backing fails closed.
    plan = _plan(stage=CiboResearchStage.ECONOMIC)
    result = _DIRECTOR.advance(
        plan,
        to_stage=CiboResearchStage.DEMO,
        evidence=_dependent_evidence(),
        updated_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_advance_rejects_backward_stage() -> None:
    plan = _plan(stage=CiboResearchStage.EXPERIMENT)
    result = _DIRECTOR.advance(
        plan,
        to_stage=CiboResearchStage.HYPOTHESIS,
        evidence=_dependent_evidence(),
        updated_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_advance_rejects_backward_time() -> None:
    plan = _plan(stage=CiboResearchStage.OBSERVATION, updated_at=_NOW)
    result = _DIRECTOR.advance(
        plan,
        to_stage=CiboResearchStage.HYPOTHESIS,
        evidence=_dependent_evidence(),
        updated_at=_NOW - timedelta(seconds=1),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


@pytest.mark.parametrize("stage", [CiboResearchStage.TRADER_LAB, CiboResearchStage.DEMO])
def test_advance_rejects_terminal_stage_without_authority_root(
    stage: CiboResearchStage,
) -> None:
    plan = _plan(stage=CiboResearchStage.ECONOMIC)
    result = _DIRECTOR.advance(
        plan,
        to_stage=stage,
        evidence=_dependent_evidence(),
        updated_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_research_has_no_demo_eligible_state() -> None:
    assert not hasattr(CiboResearchStage, "DEMO_ELIGIBLE")
    assert "demo-eligible" not in {stage.value for stage in CiboResearchStage}


def test_plan_rejects_demo_stage_without_authority_root() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboResearchPlan(
            plan_code="research.plan.volatility",
            question_code="research.question.volatility-regime",
            hypothesis_code="research.hypothesis.mean-reversion",
            data_requirements=(),
            stage=CiboResearchStage.DEMO,
            evidence=_dependent_evidence(),
            updated_at=_NOW,
        )


def test_advance_rejects_wrong_plan_type() -> None:
    result = _DIRECTOR.advance(
        cast(CiboResearchPlan, object()),
        to_stage=CiboResearchStage.HYPOTHESIS,
        evidence=_dependent_evidence(),
        updated_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_advance_rejects_corrupted_nested_data_requirements() -> None:
    plan = object.__new__(CiboResearchPlan)
    object.__setattr__(plan, "plan_code", "research.plan.volatility")
    object.__setattr__(plan, "question_code", "research.question.volatility-regime")
    object.__setattr__(plan, "hypothesis_code", "research.hypothesis.mean-reversion")
    object.__setattr__(plan, "data_requirements", ("not-a-ref",))
    object.__setattr__(plan, "stage", CiboResearchStage.OBSERVATION)
    object.__setattr__(plan, "evidence", _dependent_evidence())
    object.__setattr__(plan, "updated_at", _NOW)
    result = _DIRECTOR.advance(
        plan,
        to_stage=CiboResearchStage.HYPOTHESIS,
        evidence=_dependent_evidence(),
        updated_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_repeated_identical_advance_equal_logical_values() -> None:
    plan = _plan(stage=CiboResearchStage.OBSERVATION)
    left = _DIRECTOR.advance(
        plan,
        to_stage=CiboResearchStage.HYPOTHESIS,
        evidence=_dependent_evidence(),
        updated_at=_NOW,
    )
    right = _DIRECTOR.advance(
        plan,
        to_stage=CiboResearchStage.HYPOTHESIS,
        evidence=_dependent_evidence(),
        updated_at=_NOW,
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


def test_director_grants_no_promotion_or_eligibility_authority() -> None:
    assert not hasattr(_DIRECTOR, "promote")
    assert not hasattr(_DIRECTOR, "grant_demo")
    assert not hasattr(_DIRECTOR, "authorize")
