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
from qore.modules.statistics.contracts import (
    StatisticsInvariantError,
    StatisticsSnapshot,
    StatisticsSnapshotId,
    StatisticsSnapshotProducedEvent,
    SummarizeValidationAssessmentsCommand,
)
from qore.modules.statistics.module import (
    StatisticsServiceModule,
    SummarizeValidationAssessmentsHandler,
)
from qore.modules.validation.contracts import (
    ValidationAssessment,
    ValidationAssessmentId,
    ValidationPolicy,
    ValidationVerdict,
)
from qore.specialist.analysis import SpecialistAnalysisId, SpecialistConfidence

_TIMESTAMP = datetime(2026, 8, 7, 23, 30, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("94000000-0000-0000-0000-000000000001"))
_COMMAND_ID = CommandId(UUID("94000000-0000-0000-0000-000000000002"))
_SNAPSHOT_ID = StatisticsSnapshotId(UUID("94000000-0000-0000-0000-000000000003"))
_EVENT_ID = DomainEventId(UUID("94000000-0000-0000-0000-000000000004"))


def _assessment(
    index: int,
    confidence: float,
    verdict: ValidationVerdict,
) -> ValidationAssessment:
    source_id = SpecialistAnalysisId(
        UUID(f"94000000-0000-0000-0000-{100 + index:012d}")
    )
    assessment_id = ValidationAssessmentId(
        UUID(f"94000000-0000-0000-0000-{200 + index:012d}")
    )
    threshold = 0.5
    assert (confidence >= threshold) is (verdict is ValidationVerdict.PASSED)
    return ValidationAssessment(
        assessment_id=assessment_id,
        timestamp=_TIMESTAMP,
        source_analysis_id=source_id,
        correlation_id=_CORRELATION,
        causation_id=CausationId(source_id.value),
        policy=ValidationPolicy(SpecialistConfidence(threshold)),
        verdict=verdict,
        observed_confidence=SpecialistConfidence(confidence),
    )


def _command() -> SummarizeValidationAssessmentsCommand:
    assessments = (
        _assessment(1, 0.8, ValidationVerdict.PASSED),
        _assessment(2, 0.4, ValidationVerdict.FAILED),
    )
    return SummarizeValidationAssessmentsCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("statistics.summarize-validations"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION,
            causation_id=CausationId(assessments[-1].assessment_id.value),
        ),
        snapshot_id=_SNAPSHOT_ID,
        assessments=assessments,
    )


def test_command_produces_deterministic_descriptive_snapshot() -> None:
    snapshot = _command().to_snapshot()

    assert snapshot.sample_size == 2
    assert snapshot.passed_count == 1
    assert snapshot.failed_count == 1
    assert snapshot.pass_rate == 0.5
    assert snapshot.mean_observed_confidence == SpecialistConfidence(0.6)
    assert snapshot.correlation_id == _CORRELATION


def test_all_pass_snapshot_has_unit_pass_rate() -> None:
    assessments = (
        _assessment(1, 0.8, ValidationVerdict.PASSED),
        _assessment(2, 0.6, ValidationVerdict.PASSED),
    )
    command = SummarizeValidationAssessmentsCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("statistics.summarize-validations"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION,
            causation_id=CausationId(assessments[-1].assessment_id.value),
        ),
        snapshot_id=_SNAPSHOT_ID,
        assessments=assessments,
    )
    assert command.to_snapshot().pass_rate == 1.0


def test_command_rejects_empty_or_mutable_assessment_collection() -> None:
    with pytest.raises(StatisticsInvariantError, match="non-empty immutable tuple"):
        SummarizeValidationAssessmentsCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("statistics.summarize-validations"),
            metadata=CommandMetadata(correlation_id=_CORRELATION),
            snapshot_id=_SNAPSHOT_ID,
            assessments=(),
        )
    with pytest.raises(StatisticsInvariantError, match="non-empty immutable tuple"):
        SummarizeValidationAssessmentsCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("statistics.summarize-validations"),
            metadata=CommandMetadata(correlation_id=_CORRELATION),
            snapshot_id=_SNAPSHOT_ID,
            assessments=cast(
                tuple[ValidationAssessment, ...],
                [_assessment(1, 0.8, ValidationVerdict.PASSED)],
            ),
        )


def test_command_rejects_duplicate_sources_and_wrong_causation() -> None:
    item = _assessment(1, 0.8, ValidationVerdict.PASSED)
    with pytest.raises(StatisticsInvariantError, match="must be unique"):
        SummarizeValidationAssessmentsCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("statistics.summarize-validations"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(item.assessment_id.value),
            ),
            snapshot_id=_SNAPSHOT_ID,
            assessments=(item, item),
        )

    with pytest.raises(StatisticsInvariantError, match="causation"):
        SummarizeValidationAssessmentsCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("statistics.summarize-validations"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(
                    UUID("94000000-0000-0000-0000-000000000099")
                ),
            ),
            snapshot_id=_SNAPSHOT_ID,
            assessments=(item,),
        )


def test_command_rejects_snapshot_identity_reuse() -> None:
    item = _assessment(1, 0.8, ValidationVerdict.PASSED)
    with pytest.raises(StatisticsInvariantError, match="identity must differ"):
        SummarizeValidationAssessmentsCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("statistics.summarize-validations"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(item.assessment_id.value),
            ),
            snapshot_id=StatisticsSnapshotId(item.assessment_id.value),
            assessments=(item,),
        )


def test_snapshot_rejects_inconsistent_derived_values_runtime_bypass() -> None:
    item = _assessment(1, 0.8, ValidationVerdict.PASSED)
    with pytest.raises(StatisticsInvariantError, match="pass_rate"):
        StatisticsSnapshot(
            snapshot_id=_SNAPSHOT_ID,
            timestamp=_TIMESTAMP,
            correlation_id=_CORRELATION,
            source_assessment_ids=(item.assessment_id.value,),
            sample_size=1,
            passed_count=1,
            failed_count=0,
            pass_rate=0.0,
            mean_observed_confidence=SpecialistConfidence(0.8),
        )


def test_event_preserves_snapshot_trace() -> None:
    snapshot = _command().to_snapshot()
    event = StatisticsSnapshotProducedEvent(
        event_id=_EVENT_ID,
        timestamp=_TIMESTAMP,
        event_version=DomainEventVersion("1"),
        metadata=DomainEventMetadata(
            category=DomainEventCategory("statistics"),
            correlation_id=_CORRELATION,
            causation_id=CausationId(snapshot.source_assessment_ids[-1]),
        ),
        snapshot=snapshot,
    )
    assert event.event_name == "statistics.snapshot-produced"
    assert event.snapshot is snapshot


def test_handler_is_pure_and_deterministic() -> None:
    handler = SummarizeValidationAssessmentsHandler()
    command = _command()
    first = handler.handle(command)
    second = handler.handle(command)
    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_module_registration_bootstrap_and_runtime_isolation() -> None:
    module = StatisticsServiceModule()
    registry = HandlerRegistry()
    registration = module.register_handlers(registry)
    registered: CommandHandler[
        SummarizeValidationAssessmentsCommand,
        StatisticsSnapshot,
    ] | None = registry.command_handler(SummarizeValidationAssessmentsCommand)
    assert isinstance(registration, Success)
    assert registered is module.statistics_handler
    assert module.descriptor.name == ModuleName("statistics")

    boot = bootstrap(
        Configuration(application_name="qore-statistics-test"),
        domain_modules=(module,),
    )
    assert isinstance(boot, Success)
    dispatched: CommandResult[StatisticsSnapshot] = (
        boot.value.domain.message_bus.dispatch_command(_command())
    )
    assert isinstance(dispatched, Success)
    assert dispatched.value.sample_size == 2
    assert boot.value.domain.module_catalog.get(ModuleName("statistics")) is module
    assert len(boot.value.runtime_plan.components) == 1
    assert boot.value.runtime_plan.components[0].component is boot.value.engine


def test_statistics_instances_do_not_share_handler_state() -> None:
    first = StatisticsServiceModule()
    second = StatisticsServiceModule()
    assert first.statistics_handler is not second.statistics_handler
