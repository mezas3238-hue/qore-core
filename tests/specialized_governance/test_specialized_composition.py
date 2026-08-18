from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from qore.core.configuration import Configuration
from qore.core.lifecycle import EventIdSource
from qore.core.runtime import RuntimeContext
from qore.core.runtime_events import RuntimeStartedEvent
from qore.domain.commands import CommandId
from qore.domain.events import CorrelationId
from qore.functional.decisions import (
    DecisionId,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionType,
    FunctionalDecision,
)
from qore.governance.decision_flow import CrossModuleDecisionFlowPlan
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import ValidationError
from qore.kernel.result import Failure, Success
from qore.modules.knowledge.contracts import KnowledgeRecordId
from qore.modules.optimization.contracts import (
    OptimizationAction,
    OptimizationPolicy,
    OptimizationProposalId,
)
from qore.modules.portfolio.contracts import AllocationIntentId, PortfolioTarget
from qore.modules.risk.contracts import RiskPolicy, RiskPolicyId
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
_SOURCE_ID = UUID("98000000-0000-0000-0000-000000000099")


class SequenceEventIdSource:
    def __init__(self, ids: tuple[UUID, ...]) -> None:
        self._ids = ids
        self.calls = 0

    def __call__(self) -> UUID:
        index = self.calls
        self.calls += 1
        return self._ids[index]


def _functional_plan() -> CrossModuleDecisionFlowPlan:
    return CrossModuleDecisionFlowPlan(
        correlation_id=_CORRELATION,
        timestamp=_TIMESTAMP,
        cio_command_id=CommandId(UUID("98000000-0000-0000-0000-000000000101")),
        cio_decision_id=DecisionId(UUID("98000000-0000-0000-0000-000000000102")),
        cio_decision_type=DecisionType("cio.foundation"),
        cio_priority=DecisionPriority.NORMAL,
        cio_reasons=(
            DecisionReason(
                code=DecisionReasonCode("cio.explicit-input"),
                summary="Explicit CIO input",
            ),
        ),
        cio_outcome=DecisionOutcome.APPROVED,
        cibo_command_id=CommandId(UUID("98000000-0000-0000-0000-000000000103")),
        cibo_decision_id=DecisionId(UUID("98000000-0000-0000-0000-000000000104")),
        cibo_priority=DecisionPriority.NORMAL,
        cibo_reasons=(
            DecisionReason(
                code=DecisionReasonCode("cibo.approved"),
                summary="CIBO approved the functional decision",
            ),
        ),
        cibo_outcome=DecisionOutcome.APPROVED,
        portfolio_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000105")
        ),
        allocation_intent_id=AllocationIntentId(
            UUID("98000000-0000-0000-0000-000000000106")
        ),
        portfolio_targets=(
            PortfolioTarget(name="target-a", weight_bps=5000),
            PortfolioTarget(name="target-b", weight_bps=5000),
        ),
        risk_command_id=CommandId(UUID("98000000-0000-0000-0000-000000000107")),
        risk_decision_id=DecisionId(UUID("98000000-0000-0000-0000-000000000108")),
        risk_policy=RiskPolicy(
            policy_id=RiskPolicyId(UUID("98000000-0000-0000-0000-000000000109")),
            soft_single_target_limit_bps=6000,
            hard_single_target_limit_bps=8000,
        ),
    )


def _specialized_plan(
    source_decision: FunctionalDecision,
) -> SpecializedServicesDecisionFlowPlan:
    return SpecializedServicesDecisionFlowPlan(
        correlation_id=_CORRELATION,
        timestamp=_TIMESTAMP,
        source_decision=source_decision,
        trader_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000111")
        ),
        analysis_id=SpecialistAnalysisId(
            UUID("98000000-0000-0000-0000-000000000112")
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
            UUID("98000000-0000-0000-0000-000000000113")
        ),
        assessment_id=ValidationAssessmentId(
            UUID("98000000-0000-0000-0000-000000000114")
        ),
        validation_policy=ValidationPolicy(SpecialistConfidence(0.6)),
        statistics_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000115")
        ),
        snapshot_id=StatisticsSnapshotId(
            UUID("98000000-0000-0000-0000-000000000116")
        ),
        knowledge_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000117")
        ),
        knowledge_record_id=KnowledgeRecordId(
            UUID("98000000-0000-0000-0000-000000000118")
        ),
        optimization_command_id=CommandId(
            UUID("98000000-0000-0000-0000-000000000119")
        ),
        proposal_id=OptimizationProposalId(
            UUID("98000000-0000-0000-0000-000000000120")
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


def _execute_end_to_end(application: SpecializedGovernanceApplication) -> None:
    functional = application.functional_decision_flow.execute(_functional_plan())
    assert isinstance(functional, Success)
    specialized = application.decision_flow.execute(
        _specialized_plan(functional.value.risk_decision)
    )
    assert isinstance(specialized, Success)
    assert specialized.value.validation.verdict is ValidationVerdict.PASSED
    assert specialized.value.statistics.pass_rate == 1.0
    assert specialized.value.optimization.action is OptimizationAction.KEEP


def test_composition_registers_functional_then_specialized_modules_in_one_core() -> None:
    application = _compose()
    expected_modules = (
        application.functional_modules.cio,
        application.functional_modules.cibo,
        application.functional_modules.portfolio,
        application.functional_modules.risk,
        *application.modules.domain_modules(),
    )
    catalog_modules = application.core.domain.module_catalog.modules

    assert len(expected_modules) == 9
    assert len(catalog_modules) == 9
    for expected, actual in zip(expected_modules, catalog_modules, strict=True):
        assert actual is expected


def test_composed_application_runs_functional_then_specialized_end_to_end() -> None:
    application = _compose()
    functional = application.functional_decision_flow.execute(_functional_plan())

    assert isinstance(functional, Success)
    assert functional.value.risk_decision.outcome is DecisionOutcome.APPROVED

    specialized = application.decision_flow.execute(
        _specialized_plan(functional.value.risk_decision)
    )
    assert isinstance(specialized, Success)
    snapshot = specialized.value
    assert snapshot.source_decision is functional.value.risk_decision
    assert snapshot.validation.verdict is ValidationVerdict.PASSED
    assert snapshot.statistics.pass_rate == 1.0
    assert snapshot.knowledge.source_snapshot is snapshot.statistics
    assert snapshot.optimization.action is OptimizationAction.KEEP


def test_end_to_end_flows_do_not_change_runtime_snapshot_or_health() -> None:
    application = _compose()
    runtime_before = application.core.runtime_snapshot()
    health_before = application.core.runtime_health()

    _execute_end_to_end(application)

    assert application.core.runtime_snapshot() == runtime_before
    assert application.core.runtime_health() == health_before
    assert len(application.core.runtime_plan.components) == 1
    assert application.core.runtime_plan.components[0].component is application.core.engine


def test_compositions_are_isolated_across_functional_and_specialized_modules() -> None:
    first = _compose()
    second = _compose()

    first_modules = (
        first.functional_modules.cio,
        first.functional_modules.cibo,
        first.functional_modules.portfolio,
        first.functional_modules.risk,
        *first.modules.domain_modules(),
    )
    second_modules = (
        second.functional_modules.cio,
        second.functional_modules.cibo,
        second.functional_modules.portfolio,
        second.functional_modules.risk,
        *second.modules.domain_modules(),
    )
    for left, right in zip(first_modules, second_modules, strict=True):
        assert left is not right

    assert first.core.domain.handler_registry is not second.core.domain.handler_registry
    assert first.core.domain.message_bus is not second.core.domain.message_bus


def test_composition_preserves_explicit_runtime_context_and_clock() -> None:
    context = RuntimeContext(
        execution_id=UUID("98000000-0000-0000-0000-000000000130"),
        runtime_version="phase-05-test",
    )

    def clock() -> datetime:
        return _TIMESTAMP

    result = compose_specialized_governance(
        Configuration(application_name="qore-specialized-runtime-context"),
        runtime_context=context,
        clock=clock,
        event_id_source=lambda: _SOURCE_ID,
    )

    assert isinstance(result, Success)
    application = result.value
    assert application.core.runtime_context is context
    assert application.core.lifecycle.runtime_context is context
    _execute_end_to_end(application)


def test_composition_requires_runtime_context_and_clock_together() -> None:
    context = RuntimeContext(
        execution_id=UUID("98000000-0000-0000-0000-000000000131"),
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
    with_source_only = compose_specialized_governance(
        Configuration(application_name="qore-specialized-with-source-only"),
        event_id_source=lambda: _SOURCE_ID,
    )

    assert isinstance(without_clock, Failure)
    assert isinstance(with_clock_only, Failure)
    assert isinstance(with_source_only, Failure)


def test_specialized_composition_propagates_event_id_source() -> None:
    source = SequenceEventIdSource((_SOURCE_ID,))
    context = RuntimeContext(
        execution_id=UUID("98000000-0000-0000-0000-000000000132"),
        runtime_version="phase-05-source-test",
    )

    result = compose_specialized_governance(
        Configuration(application_name="qore-specialized-source-propagation"),
        runtime_context=context,
        clock=lambda: _TIMESTAMP,
        event_id_source=source,
    )
    assert isinstance(result, Success)
    application = result.value

    captured: list[RuntimeStartedEvent] = []

    class Handler:
        def handle(self, event: DomainEvent) -> None:
            assert isinstance(event, RuntimeStartedEvent)
            captured.append(event)

    application.core.event_bus.subscribe(RuntimeStartedEvent, Handler())
    assert isinstance(application.core.lifecycle.start(), Success)

    assert source.calls == 1
    assert len(captured) == 1
    assert captured[0].event_id == _SOURCE_ID


def test_specialized_composition_rejects_non_callable_event_id_source() -> None:
    source = cast(EventIdSource, object())
    context = RuntimeContext(
        execution_id=UUID("98000000-0000-0000-0000-000000000133"),
        runtime_version="phase-05-noncallable",
    )

    result = compose_specialized_governance(
        Configuration(application_name="qore-specialized-noncallable"),
        runtime_context=context,
        clock=lambda: _TIMESTAMP,
        event_id_source=source,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ValidationError)
    assert str(result.error) == "event id source must be callable"
