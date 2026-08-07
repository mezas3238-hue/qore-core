from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.commands import (
    CommandHandler,
    CommandId,
    CommandMetadata,
    CommandName,
    CommandResult,
)
from qore.domain.events import (
    CausationId,
    CorrelationId,
    DomainEventCategory,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleName
from qore.kernel.result import Success
from qore.modules.knowledge.contracts import KnowledgeRecord, KnowledgeRecordId
from qore.modules.optimization.contracts import (
    OptimizationAction,
    OptimizationInvariantError,
    OptimizationPolicy,
    OptimizationProposal,
    OptimizationProposalId,
    OptimizationProposalProducedEvent,
    ProposeKnowledgeOptimizationCommand,
)
from qore.modules.optimization.module import (
    OptimizationServiceModule,
    ProposeKnowledgeOptimizationHandler,
)
from qore.modules.statistics.contracts import StatisticsSnapshot, StatisticsSnapshotId
from qore.modules.validation.contracts import (
    ValidationAssessment,
    ValidationAssessmentId,
    ValidationPolicy,
    ValidationVerdict,
)
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistAnalysisStatus,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistMetadata,
    SpecialistReason,
    SpecialistReasonCode,
)

_TIMESTAMP = datetime(2026, 8, 8, 0, 10, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("96000000-0000-0000-0000-000000000001"))
_SNAPSHOT_ID = StatisticsSnapshotId(UUID("96000000-0000-0000-0000-000000000002"))
_RECORD_ID = KnowledgeRecordId(UUID("96000000-0000-0000-0000-000000000003"))
_PROPOSAL_ID = OptimizationProposalId(UUID("96000000-0000-0000-0000-000000000004"))
_COMMAND_ID = CommandId(UUID("96000000-0000-0000-0000-000000000005"))
_EVENT_ID = DomainEventId(UUID("96000000-0000-0000-0000-000000000006"))


def _assessment(index: int, passed: bool) -> ValidationAssessment:
    confidence = 0.8 if passed else 0.6
    source = SpecialistAnalysis(
        analysis_id=SpecialistAnalysisId(
            UUID(f"96000000-0000-0000-0000-{10 + index:012d}")
        ),
        timestamp=_TIMESTAMP,
        kind=SpecialistKind("virtual-trader.optimization-source"),
        status=SpecialistAnalysisStatus.COMPLETED,
        metadata=SpecialistMetadata(correlation_id=_CORRELATION),
        confidence=SpecialistConfidence(confidence),
        reasons=(
            SpecialistReason(
                code=SpecialistReasonCode("virtual-trader.explicit"),
                summary="Explicit optimization evidence",
            ),
        ),
    )
    return ValidationAssessment(
        assessment_id=ValidationAssessmentId(
            UUID(f"96000000-0000-0000-0000-{20 + index:012d}")
        ),
        timestamp=_TIMESTAMP,
        source_analysis=source,
        correlation_id=_CORRELATION,
        causation_id=CausationId(source.analysis_id.value),
        policy=ValidationPolicy(SpecialistConfidence(0.7)),
        verdict=ValidationVerdict.PASSED if passed else ValidationVerdict.FAILED,
        observed_confidence=SpecialistConfidence(confidence),
    )


def _snapshot(pass_rate: float = 0.5) -> StatisticsSnapshot:
    if pass_rate == 1.0:
        assessments = (_assessment(1, True), _assessment(2, True))
        passed_count, failed_count = 2, 0
        mean = SpecialistConfidence(0.8)
    elif pass_rate == 0.5:
        assessments = (_assessment(1, True), _assessment(2, False))
        passed_count, failed_count = 1, 1
        mean = SpecialistConfidence(0.7)
    else:
        raise AssertionError("test helper supports pass_rate 0.5 or 1.0")
    return StatisticsSnapshot(
        snapshot_id=_SNAPSHOT_ID,
        timestamp=_TIMESTAMP,
        correlation_id=_CORRELATION,
        source_assessments=assessments,
        sample_size=2,
        passed_count=passed_count,
        failed_count=failed_count,
        pass_rate=pass_rate,
        mean_observed_confidence=mean,
    )


def _knowledge(pass_rate: float = 0.5) -> KnowledgeRecord:
    snapshot = _snapshot(pass_rate)
    return KnowledgeRecord(
        record_id=_RECORD_ID,
        timestamp=_TIMESTAMP,
        source_snapshot=snapshot,
        correlation_id=_CORRELATION,
        causation_id=CausationId(snapshot.snapshot_id.value),
        sample_size=snapshot.sample_size,
        passed_count=snapshot.passed_count,
        failed_count=snapshot.failed_count,
        pass_rate=snapshot.pass_rate,
        mean_observed_confidence=snapshot.mean_observed_confidence,
    )


def _command(
    *, pass_rate: float = 0.5, target_pass_rate: float = 0.75, step_bps: int = 250
) -> ProposeKnowledgeOptimizationCommand:
    knowledge = _knowledge(pass_rate)
    return ProposeKnowledgeOptimizationCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("optimization.propose-from-knowledge"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION,
            causation_id=CausationId(knowledge.record_id.value),
        ),
        proposal_id=_PROPOSAL_ID,
        source_knowledge=knowledge,
        policy=OptimizationPolicy(target_pass_rate, step_bps),
    )


def test_command_produces_adjust_when_target_is_not_met() -> None:
    proposal = _command().to_proposal()
    assert proposal.action is OptimizationAction.ADJUST
    assert proposal.suggested_delta_bps == 250
    assert proposal.source_knowledge_id == _RECORD_ID
    assert proposal.correlation_id == _CORRELATION
    assert proposal.causation_id == CausationId(_RECORD_ID.value)


def test_command_produces_keep_when_target_is_met_or_equal() -> None:
    above = _command(pass_rate=1.0, target_pass_rate=0.75).to_proposal()
    equal = _command(pass_rate=0.5, target_pass_rate=0.5).to_proposal()
    assert above.action is OptimizationAction.KEEP
    assert above.suggested_delta_bps == 0
    assert equal.action is OptimizationAction.KEEP
    assert equal.suggested_delta_bps == 0


def test_policy_rejects_invalid_runtime_values() -> None:
    for target in (float("nan"), float("inf"), -0.1, 1.1):
        with pytest.raises(OptimizationInvariantError, match="target_pass_rate"):
            OptimizationPolicy(target, 100)
    with pytest.raises(OptimizationInvariantError, match="target_pass_rate"):
        OptimizationPolicy(cast(float, True), 100)
    with pytest.raises(OptimizationInvariantError, match="adjustment_step_bps"):
        OptimizationPolicy(0.5, cast(int, True))
    with pytest.raises(OptimizationInvariantError, match="adjustment_step_bps"):
        OptimizationPolicy(0.5, 0)
    with pytest.raises(OptimizationInvariantError, match="adjustment_step_bps"):
        OptimizationPolicy(0.5, 10_001)


def test_command_rejects_wrong_trace_and_identity_reuse() -> None:
    knowledge = _knowledge()
    with pytest.raises(OptimizationInvariantError, match="correlation"):
        ProposeKnowledgeOptimizationCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("optimization.propose-from-knowledge"),
            metadata=CommandMetadata(
                correlation_id=CorrelationId(UUID("96000000-0000-0000-0000-000000000099")),
                causation_id=CausationId(knowledge.record_id.value),
            ),
            proposal_id=_PROPOSAL_ID,
            source_knowledge=knowledge,
            policy=OptimizationPolicy(0.75, 250),
        )
    with pytest.raises(OptimizationInvariantError, match="causation"):
        ProposeKnowledgeOptimizationCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("optimization.propose-from-knowledge"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(UUID("96000000-0000-0000-0000-000000000098")),
            ),
            proposal_id=_PROPOSAL_ID,
            source_knowledge=knowledge,
            policy=OptimizationPolicy(0.75, 250),
        )
    with pytest.raises(OptimizationInvariantError, match="identity must differ"):
        ProposeKnowledgeOptimizationCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("optimization.propose-from-knowledge"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(knowledge.record_id.value),
            ),
            proposal_id=OptimizationProposalId(knowledge.record_id.value),
            source_knowledge=knowledge,
            policy=OptimizationPolicy(0.75, 250),
        )


def test_command_rejects_runtime_type_bypass() -> None:
    with pytest.raises(OptimizationInvariantError, match="source_knowledge"):
        ProposeKnowledgeOptimizationCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("optimization.propose-from-knowledge"),
            metadata=CommandMetadata(correlation_id=_CORRELATION),
            proposal_id=_PROPOSAL_ID,
            source_knowledge=cast(KnowledgeRecord, object()),
            policy=OptimizationPolicy(0.75, 250),
        )


def test_proposal_rejects_action_or_delta_inconsistent_with_evidence() -> None:
    knowledge = _knowledge()
    policy = OptimizationPolicy(0.75, 250)
    with pytest.raises(OptimizationInvariantError, match="action"):
        OptimizationProposal(
            proposal_id=_PROPOSAL_ID,
            timestamp=_TIMESTAMP,
            source_knowledge=knowledge,
            correlation_id=_CORRELATION,
            causation_id=CausationId(_RECORD_ID.value),
            policy=policy,
            action=OptimizationAction.KEEP,
            suggested_delta_bps=0,
        )
    with pytest.raises(OptimizationInvariantError, match="suggested_delta_bps"):
        OptimizationProposal(
            proposal_id=_PROPOSAL_ID,
            timestamp=_TIMESTAMP,
            source_knowledge=knowledge,
            correlation_id=_CORRELATION,
            causation_id=CausationId(_RECORD_ID.value),
            policy=policy,
            action=OptimizationAction.ADJUST,
            suggested_delta_bps=500,
        )


def test_event_preserves_proposal_trace() -> None:
    proposal = _command().to_proposal()
    event = OptimizationProposalProducedEvent(
        event_id=_EVENT_ID,
        timestamp=_TIMESTAMP,
        event_version=DomainEventVersion("1"),
        metadata=DomainEventMetadata(
            category=DomainEventCategory("optimization"),
            correlation_id=_CORRELATION,
            causation_id=CausationId(_RECORD_ID.value),
        ),
        proposal=proposal,
    )
    assert event.event_name == "optimization.proposal-produced"
    assert event.proposal is proposal


def test_event_rejects_divergent_trace() -> None:
    proposal = _command().to_proposal()
    with pytest.raises(OptimizationInvariantError, match="causation"):
        OptimizationProposalProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("optimization"),
                correlation_id=_CORRELATION,
                causation_id=CausationId(UUID("96000000-0000-0000-0000-000000000097")),
            ),
            proposal=proposal,
        )


def test_handler_is_pure_and_deterministic_and_does_not_mutate_source() -> None:
    handler = ProposeKnowledgeOptimizationHandler()
    command = _command()
    before = command.source_knowledge.logical_values()
    first = handler.handle(command)
    second = handler.handle(command)
    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()
    assert command.source_knowledge.logical_values() == before


def test_module_registration_bootstrap_and_runtime_isolation() -> None:
    module = OptimizationServiceModule()
    registry = HandlerRegistry()
    registration = module.register_handlers(registry)
    registered: CommandHandler[
        ProposeKnowledgeOptimizationCommand,
        OptimizationProposal,
    ] | None = registry.command_handler(ProposeKnowledgeOptimizationCommand)
    assert isinstance(registration, Success)
    assert registered is module.optimization_handler
    assert module.descriptor.name == ModuleName("optimization")
    boot = bootstrap(
        Configuration(application_name="qore-optimization-test"),
        domain_modules=(module,),
    )
    assert isinstance(boot, Success)
    dispatched: CommandResult[OptimizationProposal]
    dispatched = boot.value.domain.message_bus.dispatch_command(_command())
    assert isinstance(dispatched, Success)
    assert dispatched.value.action is OptimizationAction.ADJUST
    assert boot.value.domain.module_catalog.get(ModuleName("optimization")) is module
    assert len(boot.value.runtime_plan.components) == 1
    assert boot.value.runtime_plan.components[0].component is boot.value.engine


def test_optimization_instances_do_not_share_handler_state() -> None:
    first = OptimizationServiceModule()
    second = OptimizationServiceModule()
    assert first.optimization_handler is not second.optimization_handler
