from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.cibo_trader_manager import (
    CiboManagerMode,
    CiboManagerPolicy,
    CiboPerformanceEvidence,
    CiboRiskClassification,
    CiboRiskEvidence,
    CiboTraderCandidate,
    CiboTraderId,
    CiboTraderManager,
    CiboTraderParticipation,
    CiboTraderRecommendation,
    CiboTraderVersionBinding,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_run import ResearchSoftwareRevision

_EVAL = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


def _binding(
    trader_id: str,
    *,
    family: str = "qore.trader.trend",
    fingerprint: str = "a" * 64,
) -> CiboTraderVersionBinding:
    return CiboTraderVersionBinding(
        trader_id=CiboTraderId(trader_id),
        evaluator_family=ResearchDecisionEvaluatorFamily(family),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("qore.trader.trend.v1"),
        config_fingerprint=fingerprint,
    )


def _performance(
    *,
    metric_value: str = "1.0",
    sample_count: int = 100,
    as_of: datetime = _EVAL,
    metric_code: str = "sharpe",
) -> CiboPerformanceEvidence:
    return CiboPerformanceEvidence(
        metric_code=metric_code,
        metric_value=Decimal(metric_value),
        sample_count=sample_count,
        as_of=as_of,
        evidence_ref=UUID("b0000000-0000-0000-0000-000000000001"),
    )


def _risk(
    *,
    classification: CiboRiskClassification = CiboRiskClassification.CLEAR,
    violation_count: int = 0,
    as_of: datetime = _EVAL,
) -> CiboRiskEvidence:
    return CiboRiskEvidence(
        classification=classification,
        violation_count=violation_count,
        as_of=as_of,
        evidence_ref=UUID("b0000000-0000-0000-0000-000000000002"),
    )


def _candidate(
    trader_id: str,
    *,
    family: str = "qore.trader.trend",
    metric_value: str = "1.0",
    classification: CiboRiskClassification = CiboRiskClassification.CLEAR,
) -> CiboTraderCandidate:
    return CiboTraderCandidate(
        version_binding=_binding(trader_id, family=family),
        performance=_performance(metric_value=metric_value),
        risk=_risk(classification=classification),
    )


def _policy(
    *,
    mode: CiboManagerMode = CiboManagerMode.CIBO_MANAGED_TRADERS_RISK,
    selection_count: int = 1,
    ranking_metric_code: str = "sharpe",
    freshness_bound: timedelta = timedelta(days=1),
    minimum_samples: int = 10,
    violation_floor: int = 1,
    selection_threshold: Decimal = Decimal("0.0"),
    reduced_weight: Decimal = Decimal("0.5"),
) -> CiboManagerPolicy:
    return CiboManagerPolicy(
        mode=mode,
        selection_count=selection_count,
        ranking_metric_code=ranking_metric_code,
        freshness_bound=freshness_bound,
        minimum_samples=minimum_samples,
        violation_floor=violation_floor,
        selection_threshold=selection_threshold,
        reduced_weight=reduced_weight,
    )


def _participation(
    manager: CiboTraderManager,
    policy: CiboManagerPolicy,
    candidates: tuple[CiboTraderCandidate, ...],
) -> dict[str, CiboTraderParticipation]:
    result = manager.evaluate(policy=policy, candidates=candidates, evaluated_at=_EVAL)
    return {r.trader_id.value: r.participation for r in result.recommendations}


def test_policy_rejects_invalid_invariants() -> None:
    with pytest.raises(ResearchLineageValidationError):
        _policy(selection_count=0)
    with pytest.raises(ResearchLineageValidationError):
        _policy(reduced_weight=Decimal("0"))
    with pytest.raises(ResearchLineageValidationError):
        _policy(reduced_weight=Decimal("1"))
    with pytest.raises(ResearchLineageValidationError):
        _policy(freshness_bound=timedelta(0))
    with pytest.raises(ResearchLineageValidationError):
        _policy(minimum_samples=0)
    with pytest.raises(ResearchLineageValidationError):
        _policy(violation_floor=0)


def test_version_binding_requires_exact_fingerprint() -> None:
    with pytest.raises(ResearchLineageValidationError):
        _binding("trader-001", fingerprint="not-hex")


def test_violation_risk_is_blocked() -> None:
    candidate = CiboTraderCandidate(
        version_binding=_binding("trader-001"),
        performance=_performance(),
        risk=_risk(classification=CiboRiskClassification.VIOLATION),
    )
    assert (
        _participation(CiboTraderManager(), _policy(), (candidate,))["trader-001"]
        is CiboTraderParticipation.BLOCKED
    )


def test_violation_floor_blocks() -> None:
    candidate = CiboTraderCandidate(
        version_binding=_binding("trader-001"),
        performance=_performance(),
        risk=_risk(violation_count=1),
    )
    assert (
        _participation(CiboTraderManager(), _policy(), (candidate,))["trader-001"]
        is CiboTraderParticipation.BLOCKED
    )


def test_flagged_risk_is_suspended_and_never_selected() -> None:
    flagged = CiboTraderCandidate(
        version_binding=_binding("trader-001"),
        performance=_performance(metric_value="99.0"),
        risk=_risk(classification=CiboRiskClassification.FLAGGED),
    )
    assert (
        _participation(CiboTraderManager(), _policy(), (flagged,))["trader-001"]
        is CiboTraderParticipation.SUSPENDED
    )


def test_stale_performance_is_blocked() -> None:
    stale = _EVAL - timedelta(days=2)
    candidate = CiboTraderCandidate(
        version_binding=_binding("trader-001"),
        performance=_performance(as_of=stale),
        risk=_risk(),
    )
    assert (
        _participation(CiboTraderManager(), _policy(), (candidate,))["trader-001"]
        is CiboTraderParticipation.BLOCKED
    )


def test_contradictory_future_evidence_is_blocked() -> None:
    future = _EVAL + timedelta(seconds=1)
    candidate = CiboTraderCandidate(
        version_binding=_binding("trader-001"),
        performance=_performance(as_of=future),
        risk=_risk(),
    )
    assert (
        _participation(CiboTraderManager(), _policy(), (candidate,))["trader-001"]
        is CiboTraderParticipation.BLOCKED
    )


def test_insufficient_samples_is_blocked() -> None:
    candidate = CiboTraderCandidate(
        version_binding=_binding("trader-001"),
        performance=_performance(sample_count=5),
        risk=_risk(),
    )
    assert (
        _participation(CiboTraderManager(), _policy(), (candidate,))["trader-001"]
        is CiboTraderParticipation.BLOCKED
    )


def test_metric_code_mismatch_is_blocked() -> None:
    candidate = CiboTraderCandidate(
        version_binding=_binding("trader-001"),
        performance=_performance(metric_code="profit-factor"),
        risk=_risk(),
    )
    assert (
        _participation(CiboTraderManager(), _policy(), (candidate,))["trader-001"]
        is CiboTraderParticipation.BLOCKED
    )


def test_below_threshold_is_reduced() -> None:
    candidate = _candidate("trader-001", metric_value="-0.5")
    assert (
        _participation(CiboTraderManager(), _policy(), (candidate,))["trader-001"]
        is CiboTraderParticipation.REDUCED
    )


def test_top_candidate_is_selected() -> None:
    candidates = (
        _candidate("trader-001", metric_value="1.0"),
        _candidate("trader-002", metric_value="2.0"),
    )
    states = _participation(CiboTraderManager(), _policy(), candidates)
    assert states["trader-002"] is CiboTraderParticipation.SELECTED
    assert states["trader-001"] is CiboTraderParticipation.ELIGIBLE


def test_deterministic_tie_break_by_family() -> None:
    candidates = (
        _candidate("trader-trend", family="qore.trader.trend", metric_value="1.0"),
        _candidate("trader-mean", family="qore.trader.meanreversion", metric_value="1.0"),
    )
    states = _participation(CiboTraderManager(), _policy(), candidates)
    # "qore.trader.meanreversion" < "qore.trader.trend" -> ranks first -> SELECTED.
    assert states["trader-mean"] is CiboTraderParticipation.SELECTED
    assert states["trader-trend"] is CiboTraderParticipation.ELIGIBLE


def test_ab_mode_identity_retained_exactly() -> None:
    candidate = _candidate("trader-001", metric_value="1.0")
    manager = CiboTraderManager()
    risk_only = _policy(mode=CiboManagerMode.TRADERS_RISK_ONLY)
    managed = _policy(mode=CiboManagerMode.CIBO_MANAGED_TRADERS_RISK)
    result_risk = manager.evaluate(policy=risk_only, candidates=(candidate,), evaluated_at=_EVAL)
    result_managed = manager.evaluate(policy=managed, candidates=(candidate,), evaluated_at=_EVAL)
    assert result_risk.provenance.mode is CiboManagerMode.TRADERS_RISK_ONLY
    assert result_managed.provenance.mode is CiboManagerMode.CIBO_MANAGED_TRADERS_RISK
    assert result_risk.provenance.policy_fingerprint != result_managed.provenance.policy_fingerprint
    assert [r.trader_id.value for r in result_risk.recommendations] == [
        r.trader_id.value for r in result_managed.recommendations
    ]


def test_recommendation_never_emits_execution_authority() -> None:
    candidate = _candidate("trader-001", metric_value="1.0")
    result = CiboTraderManager().evaluate(
        policy=_policy(),
        candidates=(candidate,),
        evaluated_at=_EVAL,
    )
    recommendation = result.recommendations[0]
    assert isinstance(recommendation, CiboTraderRecommendation)
    assert recommendation.weight in (Decimal("0"), Decimal("0.5"), Decimal("1"))


def test_secret_like_material_rejected() -> None:
    with pytest.raises(ResearchLineageValidationError):
        CiboTraderId("client_secret")
    with pytest.raises(ResearchLineageValidationError):
        _policy(ranking_metric_code="client_secret")
