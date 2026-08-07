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
from qore.modules.knowledge.contracts import (
    CaptureStatisticsKnowledgeCommand,
    KnowledgeInvariantError,
    KnowledgeRecord,
    KnowledgeRecordCapturedEvent,
    KnowledgeRecordId,
)
from qore.modules.knowledge.module import (
    CaptureStatisticsKnowledgeHandler,
    KnowledgeServiceModule,
)
from qore.modules.statistics.contracts import StatisticsSnapshot, StatisticsSnapshotId
from qore.specialist.analysis import SpecialistConfidence

_TIMESTAMP = datetime(2026, 8, 7, 23, 50, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("95000000-0000-0000-0000-000000000001"))
_SNAPSHOT_ID = StatisticsSnapshotId(UUID("95000000-0000-0000-0000-000000000002"))
_RECORD_ID = KnowledgeRecordId(UUID("95000000-0000-0000-0000-000000000003"))
_COMMAND_ID = CommandId(UUID("95000000-0000-0000-0000-000000000004"))
_EVENT_ID = DomainEventId(UUID("95000000-0000-0000-0000-000000000005"))


def _snapshot() -> StatisticsSnapshot:
    return StatisticsSnapshot(
        snapshot_id=_SNAPSHOT_ID,
        timestamp=_TIMESTAMP,
        correlation_id=_CORRELATION,
        source_assessment_ids=(
            UUID("95000000-0000-0000-0000-000000000011"),
            UUID("95000000-0000-0000-0000-000000000012"),
        ),
        sample_size=2,
        passed_count=1,
        failed_count=1,
        pass_rate=0.5,
        mean_observed_confidence=SpecialistConfidence(0.6),
    )


def _command() -> CaptureStatisticsKnowledgeCommand:
    snapshot = _snapshot()
    return CaptureStatisticsKnowledgeCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("knowledge.capture-statistics"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION,
            causation_id=CausationId(snapshot.snapshot_id.value),
        ),
        record_id=_RECORD_ID,
        source_snapshot=snapshot,
    )


def test_command_projects_statistics_exactly_into_knowledge() -> None:
    record = _command().to_record()
    snapshot = _snapshot()

    assert record.source_snapshot_id == snapshot.snapshot_id
    assert record.sample_size == snapshot.sample_size
    assert record.passed_count == snapshot.passed_count
    assert record.failed_count == snapshot.failed_count
    assert record.pass_rate == snapshot.pass_rate
    assert record.mean_observed_confidence == snapshot.mean_observed_confidence
    assert record.correlation_id == _CORRELATION
    assert record.causation_id == CausationId(_SNAPSHOT_ID.value)


def test_command_rejects_wrong_correlation_and_causation() -> None:
    snapshot = _snapshot()
    with pytest.raises(KnowledgeInvariantError, match="correlation"):
        CaptureStatisticsKnowledgeCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("knowledge.capture-statistics"),
            metadata=CommandMetadata(
                correlation_id=CorrelationId(
                    UUID("95000000-0000-0000-0000-000000000099")
                ),
                causation_id=CausationId(snapshot.snapshot_id.value),
            ),
            record_id=_RECORD_ID,
            source_snapshot=snapshot,
        )
    with pytest.raises(KnowledgeInvariantError, match="causation"):
        CaptureStatisticsKnowledgeCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("knowledge.capture-statistics"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(
                    UUID("95000000-0000-0000-0000-000000000098")
                ),
            ),
            record_id=_RECORD_ID,
            source_snapshot=snapshot,
        )


def test_command_rejects_record_identity_reuse() -> None:
    snapshot = _snapshot()
    with pytest.raises(KnowledgeInvariantError, match="identity must differ"):
        CaptureStatisticsKnowledgeCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("knowledge.capture-statistics"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(snapshot.snapshot_id.value),
            ),
            record_id=KnowledgeRecordId(snapshot.snapshot_id.value),
            source_snapshot=snapshot,
        )


def test_command_rejects_runtime_type_bypass() -> None:
    with pytest.raises(KnowledgeInvariantError, match="source_snapshot"):
        CaptureStatisticsKnowledgeCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("knowledge.capture-statistics"),
            metadata=CommandMetadata(correlation_id=_CORRELATION),
            record_id=_RECORD_ID,
            source_snapshot=cast(StatisticsSnapshot, object()),
        )


def test_record_rejects_inconsistent_derived_values() -> None:
    with pytest.raises(KnowledgeInvariantError, match="pass_rate"):
        KnowledgeRecord(
            record_id=_RECORD_ID,
            timestamp=_TIMESTAMP,
            source_snapshot_id=_SNAPSHOT_ID,
            correlation_id=_CORRELATION,
            causation_id=CausationId(_SNAPSHOT_ID.value),
            sample_size=2,
            passed_count=1,
            failed_count=1,
            pass_rate=1.0,
            mean_observed_confidence=SpecialistConfidence(0.6),
        )


def test_event_preserves_record_trace() -> None:
    record = _command().to_record()
    event = KnowledgeRecordCapturedEvent(
        event_id=_EVENT_ID,
        timestamp=_TIMESTAMP,
        event_version=DomainEventVersion("1"),
        metadata=DomainEventMetadata(
            category=DomainEventCategory("knowledge"),
            correlation_id=_CORRELATION,
            causation_id=CausationId(_SNAPSHOT_ID.value),
        ),
        record=record,
    )
    assert event.event_name == "knowledge.record-captured"
    assert event.record is record


def test_event_rejects_divergent_trace() -> None:
    record = _command().to_record()
    with pytest.raises(KnowledgeInvariantError, match="causation"):
        KnowledgeRecordCapturedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("knowledge"),
                correlation_id=_CORRELATION,
                causation_id=CausationId(
                    UUID("95000000-0000-0000-0000-000000000097")
                ),
            ),
            record=record,
        )


def test_handler_is_pure_and_deterministic() -> None:
    handler = CaptureStatisticsKnowledgeHandler()
    command = _command()
    first = handler.handle(command)
    second = handler.handle(command)
    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_module_registration_bootstrap_and_runtime_isolation() -> None:
    module = KnowledgeServiceModule()
    registry = HandlerRegistry()
    registration = module.register_handlers(registry)
    registered: CommandHandler[CaptureStatisticsKnowledgeCommand, KnowledgeRecord] | None
    registered = registry.command_handler(CaptureStatisticsKnowledgeCommand)
    assert isinstance(registration, Success)
    assert registered is module.knowledge_handler
    assert module.descriptor.name == ModuleName("knowledge")

    boot = bootstrap(
        Configuration(application_name="qore-knowledge-test"),
        domain_modules=(module,),
    )
    assert isinstance(boot, Success)
    dispatched: CommandResult[KnowledgeRecord]
    dispatched = boot.value.domain.message_bus.dispatch_command(_command())
    assert isinstance(dispatched, Success)
    assert dispatched.value.sample_size == 2
    assert boot.value.domain.module_catalog.get(ModuleName("knowledge")) is module
    assert len(boot.value.runtime_plan.components) == 1
    assert boot.value.runtime_plan.components[0].component is boot.value.engine


def test_knowledge_instances_do_not_share_handler_state() -> None:
    first = KnowledgeServiceModule()
    second = KnowledgeServiceModule()
    assert first.knowledge_handler is not second.knowledge_handler
