from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from qore.domain.commands import (
    Command,
    CommandId,
    CommandMetadata,
    CommandName,
    CommandValidationError,
)
from qore.domain.events import (
    BusinessDomainEvent,
    CausationId,
    CorrelationId,
    DomainEventCategory,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    DecisionValidationError,
    FunctionalDecision,
)
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import ValidationError
from qore.modules.cibo.contracts import ReviewFunctionalDecisionCommand
from qore.modules.cio.contracts import CreateCioDecisionCommand
from qore.modules.knowledge.contracts import (
    CaptureStatisticsKnowledgeCommand,
    KnowledgeInvariantError,
    KnowledgeRecord,
    KnowledgeRecordId,
)
from qore.modules.optimization.contracts import (
    OptimizationAction,
    OptimizationInvariantError,
    OptimizationPolicy,
    OptimizationProposal,
    OptimizationProposalId,
    ProposeKnowledgeOptimizationCommand,
)
from qore.modules.portfolio.contracts import (
    AllocationIntent,
    AllocationIntentId,
    CreateAllocationIntentCommand,
    PortfolioTarget,
    PortfolioValidationError,
)
from qore.modules.risk.contracts import (
    AssessAllocationRiskCommand,
    RiskPolicy,
    RiskPolicyId,
)
from qore.modules.statistics.contracts import (
    StatisticsInvariantError,
    StatisticsSnapshot,
    StatisticsSnapshotId,
    SummarizeValidationAssessmentsCommand,
)
from qore.modules.trader.contracts import ProduceVirtualTraderAnalysisCommand
from qore.modules.validation.contracts import (
    ValidateSpecialistAnalysisCommand,
    ValidationAssessment,
    ValidationAssessmentId,
    ValidationInvariantError,
    ValidationPolicy,
)
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistReason,
    SpecialistReasonCode,
    SpecialistValidationError,
)

_UTC_TIMESTAMP = datetime(2026, 8, 9, 18, 0, tzinfo=UTC)
_NAIVE_TIMESTAMP = datetime(2026, 8, 9, 18, 0)
_NON_UTC = timezone(timedelta(hours=5, minutes=30))
_NON_UTC_TIMESTAMP = datetime(2026, 8, 9, 23, 30, tzinfo=_NON_UTC)
_CORRELATION_ID = CorrelationId(UUID("71000000-0000-0000-0000-000000000001"))
_EVENT_ID = UUID("71000000-0000-0000-0000-000000000099")


def _uuid(suffix: int) -> UUID:
    return UUID(f"71000000-0000-0000-0000-{suffix:012d}")


def _command_metadata(*, causation: UUID | None = None) -> CommandMetadata:
    return CommandMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=CausationId(causation) if causation is not None else None,
    )


def _reason(code: str) -> DecisionReason:
    return DecisionReason(
        code=DecisionReasonCode(code),
        summary="Temporal invariant test evidence",
    )


def _specialist_reason() -> SpecialistReason:
    return SpecialistReason(
        code=SpecialistReasonCode("virtual-trader.temporal-evidence"),
        summary="Temporal invariant test evidence",
    )


def _functional_commands() -> tuple[Command, ...]:
    cio = CreateCioDecisionCommand(
        command_id=CommandId(_uuid(10)),
        timestamp=_UTC_TIMESTAMP,
        name=CommandName("cio.temporal-test"),
        metadata=_command_metadata(),
        decision_id=DecisionId(_uuid(11)),
        decision_type=DecisionType("cio.temporal-test"),
        priority=DecisionPriority.HIGH,
        reasons=(_reason("cio.temporal-test"),),
        requested_outcome=DecisionOutcome.APPROVED,
    )
    cio_decision = cio.to_decision()

    cibo = ReviewFunctionalDecisionCommand(
        command_id=CommandId(_uuid(20)),
        timestamp=_UTC_TIMESTAMP,
        name=CommandName("cibo.temporal-test"),
        metadata=_command_metadata(causation=cio_decision.decision_id.value),
        decision_id=DecisionId(_uuid(21)),
        source_decision=cio_decision,
        priority=DecisionPriority.HIGH,
        reasons=(_reason("cibo.temporal-test"),),
        requested_outcome=DecisionOutcome.APPROVED,
    )
    cibo_decision = cibo.to_decision()

    portfolio = CreateAllocationIntentCommand(
        command_id=CommandId(_uuid(30)),
        timestamp=_UTC_TIMESTAMP,
        name=CommandName("portfolio.temporal-test"),
        metadata=_command_metadata(causation=cibo_decision.decision_id.value),
        intent_id=AllocationIntentId(_uuid(31)),
        source_decision=cibo_decision,
        targets=(PortfolioTarget("virtual-trader.primary", 10_000),),
    )
    intent = portfolio.to_intent()

    risk = AssessAllocationRiskCommand(
        command_id=CommandId(_uuid(40)),
        timestamp=_UTC_TIMESTAMP,
        name=CommandName("risk.temporal-test"),
        metadata=_command_metadata(causation=intent.intent_id.value),
        decision_id=DecisionId(_uuid(41)),
        allocation_intent=intent,
        policy=RiskPolicy(
            policy_id=RiskPolicyId(_uuid(42)),
            soft_single_target_limit_bps=10_000,
            hard_single_target_limit_bps=10_000,
        ),
    )
    risk_decision = risk.to_decision()

    trader = ProduceVirtualTraderAnalysisCommand(
        command_id=CommandId(_uuid(50)),
        timestamp=_UTC_TIMESTAMP,
        name=CommandName("virtual-trader.temporal-test"),
        metadata=_command_metadata(causation=risk_decision.decision_id.value),
        analysis_id=SpecialistAnalysisId(_uuid(51)),
        source_decision=risk_decision,
        kind=SpecialistKind("virtual-trader.temporal-test"),
        confidence=SpecialistConfidence(0.8),
        reasons=(_specialist_reason(),),
    )
    analysis = trader.to_analysis()

    validation = ValidateSpecialistAnalysisCommand(
        command_id=CommandId(_uuid(60)),
        timestamp=_UTC_TIMESTAMP,
        name=CommandName("validation.temporal-test"),
        metadata=_command_metadata(causation=analysis.analysis_id.value),
        assessment_id=ValidationAssessmentId(_uuid(61)),
        source_analysis=analysis,
        policy=ValidationPolicy(minimum_confidence=SpecialistConfidence(0.5)),
    )
    assessment = validation.to_assessment()

    statistics = SummarizeValidationAssessmentsCommand(
        command_id=CommandId(_uuid(70)),
        timestamp=_UTC_TIMESTAMP,
        name=CommandName("statistics.temporal-test"),
        metadata=_command_metadata(causation=assessment.assessment_id.value),
        snapshot_id=StatisticsSnapshotId(_uuid(71)),
        assessments=(assessment,),
    )
    snapshot = statistics.to_snapshot()

    knowledge = CaptureStatisticsKnowledgeCommand(
        command_id=CommandId(_uuid(80)),
        timestamp=_UTC_TIMESTAMP,
        name=CommandName("knowledge.temporal-test"),
        metadata=_command_metadata(causation=snapshot.snapshot_id.value),
        record_id=KnowledgeRecordId(_uuid(81)),
        source_snapshot=snapshot,
    )
    record = knowledge.to_record()

    optimization = ProposeKnowledgeOptimizationCommand(
        command_id=CommandId(_uuid(90)),
        timestamp=_UTC_TIMESTAMP,
        name=CommandName("optimization.temporal-test"),
        metadata=_command_metadata(causation=record.record_id.value),
        proposal_id=OptimizationProposalId(_uuid(91)),
        source_knowledge=record,
        policy=OptimizationPolicy(target_pass_rate=0.9, adjustment_step_bps=25),
    )

    return (
        cio,
        cibo,
        portfolio,
        risk,
        trader,
        validation,
        statistics,
        knowledge,
        optimization,
    )


def _direct_artifacts() -> tuple[
    FunctionalDecision,
    SpecialistAnalysis,
    ValidationAssessment,
    StatisticsSnapshot,
    AllocationIntent,
    KnowledgeRecord,
    OptimizationProposal,
]:
    commands = _functional_commands()
    cio = commands[0]
    portfolio = commands[2]
    trader = commands[4]
    validation = commands[5]
    statistics = commands[6]
    knowledge = commands[7]
    optimization = commands[8]

    assert isinstance(cio, CreateCioDecisionCommand)
    assert isinstance(portfolio, CreateAllocationIntentCommand)
    assert isinstance(trader, ProduceVirtualTraderAnalysisCommand)
    assert isinstance(validation, ValidateSpecialistAnalysisCommand)
    assert isinstance(statistics, SummarizeValidationAssessmentsCommand)
    assert isinstance(knowledge, CaptureStatisticsKnowledgeCommand)
    assert isinstance(optimization, ProposeKnowledgeOptimizationCommand)

    decision = cio.to_decision()
    intent = portfolio.to_intent()
    analysis = trader.to_analysis()
    assessment = validation.to_assessment()
    snapshot = statistics.to_snapshot()
    record = knowledge.to_record()
    proposal = optimization.to_proposal()

    return decision, analysis, assessment, snapshot, intent, record, proposal


def test_base_command_rejects_naive_and_accepts_non_utc_aware_timestamp() -> None:
    with pytest.raises(CommandValidationError, match="timezone-aware"):
        Command(
            command_id=CommandId(_uuid(100)),
            timestamp=_NAIVE_TIMESTAMP,
            name=CommandName("qore.temporal-test"),
            metadata=_command_metadata(),
        )

    value = Command(
        command_id=CommandId(_uuid(100)),
        timestamp=_NON_UTC_TIMESTAMP,
        name=CommandName("qore.temporal-test"),
        metadata=_command_metadata(),
    )
    assert value.timestamp == _NON_UTC_TIMESTAMP
    assert value.timestamp.utcoffset() == timedelta(hours=5, minutes=30)


def test_domain_event_rejects_naive_and_accepts_non_utc_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        DomainEvent(
            timestamp=_NAIVE_TIMESTAMP,
            event_name="qore.temporal-test",
            event_id=_EVENT_ID,
        )

    value = DomainEvent(
        timestamp=_NON_UTC_TIMESTAMP,
        event_name="qore.temporal-test",
        event_id=_EVENT_ID,
    )
    assert value.timestamp == _NON_UTC_TIMESTAMP


def test_business_event_path_inherits_timezone_awareness_enforcement() -> None:
    metadata = DomainEventMetadata(
        category=DomainEventCategory("temporal"),
        correlation_id=_CORRELATION_ID,
    )

    with pytest.raises(ValidationError, match="timezone-aware"):
        BusinessDomainEvent(
            timestamp=_NAIVE_TIMESTAMP,
            event_name="qore.temporal-test",
            event_id=DomainEventId(_uuid(101)),
            event_version=DomainEventVersion("1"),
            metadata=metadata,
        )

    value = BusinessDomainEvent(
        timestamp=_NON_UTC_TIMESTAMP,
        event_name="qore.temporal-test",
        event_id=DomainEventId(_uuid(102)),
        event_version=DomainEventVersion("1"),
        metadata=metadata,
    )
    assert value.timestamp == _NON_UTC_TIMESTAMP


def test_all_functional_commands_reject_naive_timestamps() -> None:
    for command in _functional_commands():
        with pytest.raises(CommandValidationError, match="timezone-aware"):
            replace(command, timestamp=_NAIVE_TIMESTAMP)


def test_all_functional_commands_accept_non_utc_aware_offsets() -> None:
    for command in _functional_commands():
        value = replace(command, timestamp=_NON_UTC_TIMESTAMP)
        assert value.timestamp == _NON_UTC_TIMESTAMP
        assert value.timestamp.utcoffset() == timedelta(hours=5, minutes=30)


def test_direct_functional_decision_rejects_naive_timestamp() -> None:
    decision = _direct_artifacts()[0]
    with pytest.raises(DecisionValidationError, match="timezone-aware"):
        replace(decision, timestamp=_NAIVE_TIMESTAMP)


def test_direct_specialist_analysis_rejects_naive_timestamp() -> None:
    analysis = _direct_artifacts()[1]
    with pytest.raises(SpecialistValidationError, match="timezone-aware"):
        replace(analysis, timestamp=_NAIVE_TIMESTAMP)


def test_direct_validation_assessment_rejects_naive_timestamp() -> None:
    assessment = _direct_artifacts()[2]
    with pytest.raises(ValidationInvariantError, match="timezone-aware"):
        replace(assessment, timestamp=_NAIVE_TIMESTAMP)


def test_direct_statistics_snapshot_rejects_naive_timestamp() -> None:
    snapshot = _direct_artifacts()[3]
    with pytest.raises(StatisticsInvariantError, match="timezone-aware"):
        replace(snapshot, timestamp=_NAIVE_TIMESTAMP)


def test_direct_allocation_intent_rejects_naive_timestamp() -> None:
    intent = _direct_artifacts()[4]
    with pytest.raises(PortfolioValidationError, match="timezone-aware"):
        replace(intent, timestamp=_NAIVE_TIMESTAMP)


def test_direct_knowledge_record_rejects_naive_timestamp() -> None:
    record = _direct_artifacts()[5]
    with pytest.raises(KnowledgeInvariantError, match="timezone-aware"):
        replace(record, timestamp=_NAIVE_TIMESTAMP)


def test_direct_optimization_proposal_rejects_naive_timestamp() -> None:
    proposal = _direct_artifacts()[6]
    with pytest.raises(OptimizationInvariantError, match="timezone-aware"):
        replace(proposal, timestamp=_NAIVE_TIMESTAMP)


def test_direct_artifacts_accept_non_utc_aware_offsets() -> None:
    decision, analysis, assessment, snapshot, intent, record, proposal = _direct_artifacts()

    adjusted_decision = replace(decision, timestamp=_NON_UTC_TIMESTAMP)
    adjusted_analysis = replace(analysis, timestamp=_NON_UTC_TIMESTAMP)
    adjusted_assessment = replace(assessment, timestamp=_NON_UTC_TIMESTAMP)
    adjusted_snapshot = replace(snapshot, timestamp=_NON_UTC_TIMESTAMP)
    adjusted_intent = replace(intent, timestamp=_NON_UTC_TIMESTAMP)
    adjusted_record = replace(record, timestamp=_NON_UTC_TIMESTAMP)
    adjusted_proposal = replace(proposal, timestamp=_NON_UTC_TIMESTAMP)

    assert adjusted_decision.timestamp == _NON_UTC_TIMESTAMP
    assert adjusted_analysis.timestamp == _NON_UTC_TIMESTAMP
    assert adjusted_assessment.timestamp == _NON_UTC_TIMESTAMP
    assert adjusted_snapshot.timestamp == _NON_UTC_TIMESTAMP
    assert adjusted_intent.timestamp == _NON_UTC_TIMESTAMP
    assert adjusted_record.timestamp == _NON_UTC_TIMESTAMP
    assert adjusted_proposal.timestamp == _NON_UTC_TIMESTAMP
    assert adjusted_proposal.action in {
        OptimizationAction.KEEP,
        OptimizationAction.ADJUST,
    }


def test_logical_values_preserve_explicit_offset() -> None:
    decision = replace(_direct_artifacts()[0], timestamp=_NON_UTC_TIMESTAMP)
    serialized_timestamp = decision.logical_values()[1]

    assert serialized_timestamp == _NON_UTC_TIMESTAMP.isoformat()
    assert isinstance(serialized_timestamp, str)
    assert serialized_timestamp.endswith("+05:30")


def test_functional_decision_constructor_remains_resolved_and_explicit() -> None:
    decision = FunctionalDecision(
        decision_id=DecisionId(_uuid(110)),
        timestamp=_NON_UTC_TIMESTAMP,
        decision_type=DecisionType("temporal.direct"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=_CORRELATION_ID),
        reasons=(_reason("temporal.direct"),),
        outcome=DecisionOutcome.APPROVED,
    )
    assert decision.timestamp.utcoffset() == timedelta(hours=5, minutes=30)
