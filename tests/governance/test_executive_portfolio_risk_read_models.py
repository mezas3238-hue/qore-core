from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_portfolio_risk_read_models import (
    ExecutivePortfolioAllocationRef,
    ExecutivePortfolioAllocationSummary,
    ExecutivePortfolioGovernanceState,
    ExecutivePortfolioReadModel,
    ExecutivePortfolioSourceDecisionRef,
    ExecutivePortfolioTargetSummary,
    ExecutiveRiskAssessmentOutcome,
    ExecutiveRiskConcentrationAssessment,
    ExecutiveRiskDecisionRef,
    ExecutiveRiskPolicyRef,
    ExecutiveRiskReadModel,
    ExecutiveRiskState,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveReadModelValidationError,
    ExecutiveSourceFreshness,
)

_NOW = datetime(2026, 8, 8, 22, 0, tzinfo=UTC)


def _metadata(scope: ExecutiveReadScope) -> ExecutiveProjectionMetadata:
    return ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("2c000000-0000-0000-0000-000000000001")
        ),
        projection_version=ExecutiveProjectionVersion("executive-portfolio-risk.v1"),
        scope=scope,
        source_observed_at=_NOW,
        projected_at=_NOW + timedelta(seconds=1),
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(ExecutiveEvidenceRef("evidence:portfolio-risk/root-001"),),
    )


def _allocation(
    allocation_id: str = "2c000000-0000-0000-0000-000000000010",
) -> ExecutivePortfolioAllocationSummary:
    return ExecutivePortfolioAllocationSummary(
        allocation_ref=ExecutivePortfolioAllocationRef(UUID(allocation_id)),
        source_decision_ref=ExecutivePortfolioSourceDecisionRef(
            UUID("2c000000-0000-0000-0000-000000000020")
        ),
        state=ExecutivePortfolioGovernanceState.APPROVED,
        targets=(
            ExecutivePortfolioTargetSummary("trader.beta", 4000),
            ExecutivePortfolioTargetSummary("trader.alpha", 6000),
        ),
        reason_codes=("portfolio.allocation-approved",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:portfolio/allocation-001"),),
    )


def _assessment(
    *,
    decision_id: str = "2c000000-0000-0000-0000-000000000030",
    peak_bps: int = 6000,
    outcome: ExecutiveRiskAssessmentOutcome = ExecutiveRiskAssessmentOutcome.APPROVED,
) -> ExecutiveRiskConcentrationAssessment:
    return ExecutiveRiskConcentrationAssessment(
        decision_ref=ExecutiveRiskDecisionRef(UUID(decision_id)),
        allocation_ref=ExecutivePortfolioAllocationRef(
            UUID("2c000000-0000-0000-0000-000000000010")
        ),
        policy_ref=ExecutiveRiskPolicyRef(
            UUID("2c000000-0000-0000-0000-000000000040")
        ),
        soft_single_target_limit_bps=6000,
        hard_single_target_limit_bps=7500,
        observed_peak_weight_bps=peak_bps,
        outcome=outcome,
        reason_codes=("risk.within-concentration-limits",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:risk/decision-001"),),
    )


def test_portfolio_projection_is_scope_bound_and_deterministic() -> None:
    second = _allocation("2c000000-0000-0000-0000-000000000011")
    first = _allocation("2c000000-0000-0000-0000-000000000010")
    model = ExecutivePortfolioReadModel(
        metadata=_metadata(ExecutiveReadScope.PORTFOLIO),
        attention=ExecutiveAttentionLevel.INFORMATION,
        allocations=(second, first),
    )

    assert model.allocations == (first, second)
    assert tuple(item.target_code for item in first.targets) == (
        "trader.alpha",
        "trader.beta",
    )
    assert model.logical_values() == model.logical_values()
    assert not hasattr(first, "positions")
    assert not hasattr(first, "broker_exposure")
    assert not hasattr(first, "balance")


def test_portfolio_projection_rejects_wrong_scope() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutivePortfolioReadModel(
            metadata=_metadata(ExecutiveReadScope.RISK),
            attention=ExecutiveAttentionLevel.ATTENTION,
            allocations=(_allocation(),),
        )


def test_portfolio_allocation_requires_full_unique_basis_point_allocation() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutivePortfolioAllocationSummary(
            allocation_ref=ExecutivePortfolioAllocationRef(
                UUID("2c000000-0000-0000-0000-000000000012")
            ),
            source_decision_ref=ExecutivePortfolioSourceDecisionRef(
                UUID("2c000000-0000-0000-0000-000000000021")
            ),
            state=ExecutivePortfolioGovernanceState.PENDING_RISK,
            targets=(
                ExecutivePortfolioTargetSummary("trader.alpha", 5000),
                ExecutivePortfolioTargetSummary("trader.beta", 4000),
            ),
            reason_codes=("portfolio.pending-risk",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:portfolio/pending-001"),),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutivePortfolioAllocationSummary(
            allocation_ref=ExecutivePortfolioAllocationRef(
                UUID("2c000000-0000-0000-0000-000000000013")
            ),
            source_decision_ref=ExecutivePortfolioSourceDecisionRef(
                UUID("2c000000-0000-0000-0000-000000000022")
            ),
            state=ExecutivePortfolioGovernanceState.APPROVED,
            targets=(
                ExecutivePortfolioTargetSummary("trader.alpha", 5000),
                ExecutivePortfolioTargetSummary("trader.alpha", 5000),
            ),
            reason_codes=("portfolio.invalid-duplicate",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:portfolio/duplicate-001"),),
        )


def test_portfolio_allocation_requires_reasons_and_evidence() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutivePortfolioAllocationSummary(
            allocation_ref=ExecutivePortfolioAllocationRef(
                UUID("2c000000-0000-0000-0000-000000000014")
            ),
            source_decision_ref=ExecutivePortfolioSourceDecisionRef(
                UUID("2c000000-0000-0000-0000-000000000023")
            ),
            state=ExecutivePortfolioGovernanceState.UNKNOWN,
            targets=(ExecutivePortfolioTargetSummary("trader.alpha", 10_000),),
            reason_codes=(),
            evidence_refs=(ExecutiveEvidenceRef("evidence:portfolio/unknown-001"),),
        )


def test_risk_assessment_matches_repository_concentration_policy() -> None:
    approved = _assessment()
    degraded = _assessment(
        decision_id="2c000000-0000-0000-0000-000000000031",
        peak_bps=7000,
        outcome=ExecutiveRiskAssessmentOutcome.DEGRADED,
    )
    blocked = _assessment(
        decision_id="2c000000-0000-0000-0000-000000000032",
        peak_bps=8000,
        outcome=ExecutiveRiskAssessmentOutcome.BLOCKED,
    )

    assert approved.outcome is ExecutiveRiskAssessmentOutcome.APPROVED
    assert degraded.outcome is ExecutiveRiskAssessmentOutcome.DEGRADED
    assert blocked.outcome is ExecutiveRiskAssessmentOutcome.BLOCKED


def test_risk_assessment_rejects_policy_outcome_mismatch() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        _assessment(
            peak_bps=8000,
            outcome=ExecutiveRiskAssessmentOutcome.APPROVED,
        )


def test_risk_projection_is_scope_bound_and_requires_consistent_clear_state() -> None:
    blocked = _assessment(
        peak_bps=8000,
        outcome=ExecutiveRiskAssessmentOutcome.BLOCKED,
    )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveRiskReadModel(
            metadata=_metadata(ExecutiveReadScope.PORTFOLIO),
            attention=ExecutiveAttentionLevel.CRITICAL,
            state=ExecutiveRiskState.BLOCKED,
            assessments=(blocked,),
            reason_codes=("risk.blocked",),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveRiskReadModel(
            metadata=_metadata(ExecutiveReadScope.RISK),
            attention=ExecutiveAttentionLevel.INFORMATION,
            state=ExecutiveRiskState.CLEAR,
            assessments=(blocked,),
            reason_codes=("risk.clear",),
        )


def test_blocked_risk_state_requires_blocked_evidence() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveRiskReadModel(
            metadata=_metadata(ExecutiveReadScope.RISK),
            attention=ExecutiveAttentionLevel.CRITICAL,
            state=ExecutiveRiskState.BLOCKED,
            assessments=(_assessment(),),
            reason_codes=("risk.blocked",),
        )


def test_risk_projection_is_not_capital_or_execution_authority() -> None:
    model = ExecutiveRiskReadModel(
        metadata=_metadata(ExecutiveReadScope.RISK),
        attention=ExecutiveAttentionLevel.INFORMATION,
        state=ExecutiveRiskState.CLEAR,
        assessments=(_assessment(),),
        reason_codes=("risk.clear",),
    )

    assert not hasattr(model, "balance")
    assert not hasattr(model, "equity")
    assert not hasattr(model, "submit_order")
    assert not hasattr(model, "client_profit_share")
