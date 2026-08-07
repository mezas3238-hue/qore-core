from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from qore.core.configuration import Configuration
from qore.core.runtime import RuntimeContext
from qore.domain.commands import CommandId
from qore.domain.events import CorrelationId
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
from qore.modules.optimization.contracts import (
    OptimizationAction,
    OptimizationPolicy,
    OptimizationProposalId,
)
from qore.modules.statistics.contracts import StatisticsSnapshotId
from qore.modules.validation.contracts import (
    ValidationAssessmentId,
    ValidationPolicy,
    ValidationVerdict,
)
from qore.specialist.analysis import (
    SpecialistAnalysisId,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistReason,
    SpecialistReasonCode,
)
from qore.specialized_governance.composition import (
    SpecializedGovernanceApplication,
    compose_specialized_governance,
)
from qore.specialized_governance.decision_flow import SpecializedServicesDecisionFlowPlan

_TIMESTAMP = datetime(2026, 8, 8, 1, 0, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("98000000-0000-0000-0000-000000000001"))


def _source_decision() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(UUID("98000000-0000-0000-0000-000000000010")),
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


def _plan() -> SpecializedServicesDecisionFlowPlan:
    return SpecializedServicesDecisionFlowPlan(
        correlation_id=_CORRELATION,
        timestamp=_TIMESTAMP,
        source_decision=_source_decision(),
        trader_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000011")
        ),
        analysis_id=SpecialistAnalysisId(
            UUID("98000000-0000-0000-0000-000000000012")
        ),
        analysis_kind=SpecialistKind("virtual-trader.foundation"),
        analysis_confidence=SpecialistConfidence(0.8),
        analysis_reasons=(
            SpecialistReason(
                code=SpecialistReasonCode("virtual-trader.explicit-input"),
                summary="Explicit specialist input",
            ),
        ),
        validation_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000013")
        ),
        assessment_id=ValidationAssessmentId(
            UUID("98000000-0000-0000-0000-000000000014")
        ),
        validation_policy=ValidationPolicy(SpecialistConfidence(0.6)),
        statistics_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000015")
        ),
        snapshot_id=StatisticsSnapshotId(
            UUID("98000000-0000-0000-0000-000000000016")
        ),
        knowledge_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000017")
        ),
        knowledge_record_id=KnowledgeRecordId(
            UUID("98000000-0000-0000-0000-000000000018")
        ),
        optimization_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000019")
        ),
        proposal_id=OptimizationProposalId(
            UUID("98000000-0000-0000-0000-000000000020")
        ),
        optimization_policy=OptimizationPolicy(
            target_pass_rate=1.0,
            adjustment_step_bps=250,
        ),
    )


def _compose() -> SpecializedGovernanceApplication:
    result = compose_specialized_governance(
        Configuration(application_name="qore-specialized-composition-test")
    )
    assert isinstance(result, Success)
    return result.value


def test_composition_registers_exact_official_module_instances_in_order() -> None:
    application = _compose()
    modules = application.modules.domain_modules()
    catalog_modules = application.core.domain.module_catalog.modules

    assert len(modules) == 5
    assert len(catalog_modules) == 5
    for expected, actual in zip(modules, catalog_modules, strict=True):
        assert actual is expected


def test_composed_application_runs_complete_specialized_flow() -> None:
    application = _compose()
    result = application.decision_flow.execute(_plan())

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.validation.verdict is ValidationVerdict.PASSED
    assert snapshot.statistics.pass_rate == 1.0
    assert snapshot.knowledge.source_snapshot is snapshot.statistics
    assert snapshot.optimization.action is OptimizationAction.KEEP
    assert snapshot.optimization.suggested_delta_bps == 0


def test_specialized_flow_does_not_change_runtime_snapshot_or_health() -> None:
    application = _compose()
    runtime_before = application.core.runtime_snapshot()
    health_before = application.core.runtime_health()

    result = application.decision_flow.execute(_plan())

    assert isinstance(result, Success)
    assert application.core.runtime_snapshot() == runtime_before
    assert application.core.runtime_health() == health_before
    assert len(application.core.runtime_plan.components) == 1
    assert application.core.runtime_plan.components[0].component is application.core.engine


def test_compositions_are_isolated_and_do_not_share_module_instances() -> None:
    first = _compose()
    second = _compose()

    first_modules = first.modules.domain_modules()
    second_modules = second.modules.domain_modules()
    for left, right in zip(first_modules, second_modules, strict=True):
        assert left is not right

    assert first.core.domain.handler_registry is not second.core.domain.handler_registry
    assert first.core.domain.message_bus is not second.core.domain.message_bus


def test_composition_preserves_explicit_runtime_context_and_clock() -> None:
    context = RuntimeContext(
        execution_id=UUID("98000000-0000-0000-0000-000000000030"),
        runtime_version="phase-05-test",
    )

    def clock() -> datetime:
        return _TIMESTAMP

    result = compose_specialized_governance(
        Configuration(application_name="qore-specialized-runtime-context"),
        runtime_context=context,
        clock=clock,
    )

    assert isinstance(result, Success)
    application = result.value
    assert application.core.runtime_context is context
    assert application.core.lifecycle.runtime_context is context


def test_composition_requires_runtime_context_and_clock_together() -> None:
    context = RuntimeContext(
        execution_id=UUID("98000000-0000-0000-0000-000000000031"),
        runtime_version="phase-05-test",
    )

    without_clock = compose_specialized_governance(
        Configuration(application_name="qore-specialized-without-clock"),
        runtime_context=context,
    )
    with_clock_only = compose_specialized_governance(
        Configuration(application_name="qore-specialized-with-clock-only"),
        clock=lambda: _TIMESTAMP,
    )

    assert isinstance(without_clock, Failure)
    assert isinstance(with_clock_only, Failure)
