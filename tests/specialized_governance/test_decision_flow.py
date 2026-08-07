from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.commands import CommandId
from qore.domain.events import CorrelationId
from qore.domain.message_bus import HandlerRegistry, MessageBus
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.kernel.result import Failure, Success
from qore.modules.knowledge.contracts import KnowledgeRecordId
from qore.modules.knowledge.module import KnowledgeServiceModule
from qore.modules.optimization.contracts import (
    OptimizationAction,
    OptimizationPolicy,
    OptimizationProposalId,
)
from qore.modules.optimization.module import OptimizationServiceModule
from qore.modules.statistics.contracts import StatisticsSnapshotId
from qore.modules.statistics.module import StatisticsServiceModule
from qore.modules.trader.module import VirtualTraderModule
from qore.modules.validation.contracts import (
    ValidationAssessmentId,
    ValidationPolicy,
    ValidationVerdict,
)
from qore.modules.validation.module import ValidationLabModule
from qore.specialist.analysis import (
    SpecialistAnalysisId,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistReason,
    SpecialistReasonCode,
)
from qore.specialized_governance.decision_flow import (
    SpecializedGovernanceValidationError,
    SpecializedServicesDecisionFlow,
    SpecializedServicesDecisionFlowPlan,
)

_TIMESTAMP = datetime(2026, 8, 8, 0, 30, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("97000000-0000-0000-0000-000000000001"))


def _source_decision() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(UUID("97000000-0000-0000-0000-000000000010")),
        timestamp=_TIMESTAMP,
        decision_type=DecisionType("governance.specialist-input"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=_CORRELATION),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("governance.ready"),
                summary="Ready for specialist evaluation",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _plan(
    *,
    confidence: float,
    minimum: float,
    target_pass_rate: float,
) -> SpecializedServicesDecisionFlowPlan:
    return SpecializedServicesDecisionFlowPlan(
        correlation_id=_CORRELATION,
        timestamp=_TIMESTAMP,
        source_decision=_source_decision(),
        trader_command_id=CommandId(UUID("97000000-0000-0000-0000-000000000011")),
        analysis_id=SpecialistAnalysisId(UUID("97000000-0000-0000-0000-000000000012")),
        analysis_kind=SpecialistKind("virtual-trader.foundation"),
        analysis_confidence=SpecialistConfidence(confidence),
        analysis_reasons=(
            SpecialistReason(
                code=SpecialistReasonCode("virtual-trader.explicit-input"),
                summary="Explicit specialist input",
            ),
        ),
        validation_command_id=CommandId(UUID("97000000-0000-0000-0000-000000000013")),
        assessment_id=ValidationAssessmentId(UUID("97000000-0000-0000-0000-000000000014")),
        validation_policy=ValidationPolicy(SpecialistConfidence(minimum)),
        statistics_command_id=CommandId(UUID("97000000-0000-0000-0000-000000000015")),
        snapshot_id=StatisticsSnapshotId(UUID("97000000-0000-0000-0000-000000000016")),
        knowledge_command_id=CommandId(UUID("97000000-0000-0000-0000-000000000017")),
        knowledge_record_id=KnowledgeRecordId(UUID("97000000-0000-0000-0000-000000000018")),
        optimization_command_id=CommandId(UUID("97000000-0000-0000-0000-000000000019")),
        proposal_id=OptimizationProposalId(UUID("97000000-0000-0000-0000-000000000020")),
        optimization_policy=OptimizationPolicy(
            target_pass_rate=target_pass_rate,
            adjustment_step_bps=250,
        ),
    )


def _flow() -> SpecializedServicesDecisionFlow:
    boot = bootstrap(
        Configuration(application_name="qore-specialized-flow-test"),
        domain_modules=(
            VirtualTraderModule(),
            ValidationLabModule(),
            StatisticsServiceModule(),
            KnowledgeServiceModule(),
            OptimizationServiceModule(),
        ),
    )
    assert isinstance(boot, Success)
    return SpecializedServicesDecisionFlow(message_bus=boot.value.domain.message_bus)


def test_full_specialized_flow_passes_and_keeps() -> None:
    result = _flow().execute(_plan(confidence=0.8, minimum=0.6, target_pass_rate=1.0))
    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.validation.verdict is ValidationVerdict.PASSED
    assert snapshot.statistics.pass_rate == 1.0
    assert snapshot.knowledge.source_snapshot is snapshot.statistics
    assert snapshot.optimization.action is OptimizationAction.KEEP
    assert snapshot.optimization.suggested_delta_bps == 0
    assert snapshot.analysis.metadata.correlation_id == _CORRELATION
    assert snapshot.optimization.correlation_id == _CORRELATION


def test_failed_validation_is_evidence_and_continues_to_adjust() -> None:
    result = _flow().execute(_plan(confidence=0.4, minimum=0.6, target_pass_rate=0.5))
    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.validation.verdict is ValidationVerdict.FAILED
    assert snapshot.statistics.pass_rate == 0.0
    assert snapshot.statistics.failed_count == 1
    assert snapshot.optimization.action is OptimizationAction.ADJUST
    assert snapshot.optimization.suggested_delta_bps == 250


def test_flow_is_deterministic_for_same_explicit_plan() -> None:
    flow = _flow()
    plan = _plan(confidence=0.8, minimum=0.6, target_pass_rate=1.0)
    first = flow.execute(plan)
    second = flow.execute(plan)
    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_flow_rejects_duplicate_causal_object_identity() -> None:
    plan = _plan(confidence=0.8, minimum=0.6, target_pass_rate=1.0)
    with pytest.raises(SpecializedGovernanceValidationError, match="identities must be unique"):
        SpecializedServicesDecisionFlowPlan(
            correlation_id=plan.correlation_id,
            timestamp=plan.timestamp,
            source_decision=plan.source_decision,
            trader_command_id=plan.trader_command_id,
            analysis_id=plan.analysis_id,
            analysis_kind=plan.analysis_kind,
            analysis_confidence=plan.analysis_confidence,
            analysis_reasons=plan.analysis_reasons,
            validation_command_id=plan.validation_command_id,
            assessment_id=ValidationAssessmentId(plan.analysis_id.value),
            validation_policy=plan.validation_policy,
            statistics_command_id=plan.statistics_command_id,
            snapshot_id=plan.snapshot_id,
            knowledge_command_id=plan.knowledge_command_id,
            knowledge_record_id=plan.knowledge_record_id,
            optimization_command_id=plan.optimization_command_id,
            proposal_id=plan.proposal_id,
            optimization_policy=plan.optimization_policy,
        )


def test_missing_handler_returns_failure_and_stops_pipeline() -> None:
    flow = SpecializedServicesDecisionFlow(message_bus=MessageBus(registry=HandlerRegistry()))
    result = flow.execute(_plan(confidence=0.8, minimum=0.6, target_pass_rate=1.0))
    assert isinstance(result, Failure)


def test_functional_modules_stay_out_of_runtime_plan() -> None:
    modules = (
        VirtualTraderModule(),
        ValidationLabModule(),
        StatisticsServiceModule(),
        KnowledgeServiceModule(),
        OptimizationServiceModule(),
    )
    boot = bootstrap(
        Configuration(application_name="qore-specialized-runtime-isolation"),
        domain_modules=modules,
    )
    assert isinstance(boot, Success)
    before = tuple(boot.value.runtime_plan.components)
    result = SpecializedServicesDecisionFlow(
        message_bus=boot.value.domain.message_bus
    ).execute(_plan(confidence=0.8, minimum=0.6, target_pass_rate=1.0))
    assert isinstance(result, Success)
    assert tuple(boot.value.runtime_plan.components) == before
    assert len(before) == 1
    assert before[0].component is boot.value.engine
