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
from qore.modules.validation.contracts import (
    ValidateSpecialistAnalysisCommand,
    ValidationAssessment,
    ValidationAssessmentId,
    ValidationAssessmentProducedEvent,
    ValidationInvariantError,
    ValidationPolicy,
    ValidationVerdict,
)
from qore.modules.validation.module import (
    ValidateSpecialistAnalysisHandler,
    ValidationLabModule,
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

_TIMESTAMP = datetime(2026, 8, 7, 23, 0, tzinfo=UTC)
_SOURCE_ID = SpecialistAnalysisId(UUID("93000000-0000-0000-0000-000000000001"))
_ASSESSMENT_ID = ValidationAssessmentId(UUID("93000000-0000-0000-0000-000000000002"))
_COMMAND_ID = CommandId(UUID("93000000-0000-0000-0000-000000000003"))
_CORRELATION = CorrelationId(UUID("93000000-0000-0000-0000-000000000004"))
_EVENT_ID = DomainEventId(UUID("93000000-0000-0000-0000-000000000005"))


def _reason() -> SpecialistReason:
    return SpecialistReason(
        code=SpecialistReasonCode("virtual-trader.explicit"),
        summary="Explicit internal evidence",
    )


def _analysis(
    *,
    confidence: float = 0.8,
    status: SpecialistAnalysisStatus = SpecialistAnalysisStatus.COMPLETED,
) -> SpecialistAnalysis:
    completed = status is SpecialistAnalysisStatus.COMPLETED
    return SpecialistAnalysis(
        analysis_id=_SOURCE_ID,
        timestamp=_TIMESTAMP,
        kind=SpecialistKind("virtual-trader.structure"),
        status=status,
        metadata=SpecialistMetadata(correlation_id=_CORRELATION),
        confidence=SpecialistConfidence(confidence) if completed else None,
        reasons=(_reason(),) if completed else (),
    )


def _command(
    *, confidence: float = 0.8, minimum: float = 0.7
) -> ValidateSpecialistAnalysisCommand:
    source = _analysis(confidence=confidence)
    return ValidateSpecialistAnalysisCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("validation.validate-specialist-analysis"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION,
            causation_id=CausationId(source.analysis_id.value),
        ),
        assessment_id=_ASSESSMENT_ID,
        source_analysis=source,
        policy=ValidationPolicy(SpecialistConfidence(minimum)),
    )


def test_validation_passes_at_or_above_threshold() -> None:
    above = _command(confidence=0.8, minimum=0.7).to_assessment()
    equal = _command(confidence=0.7, minimum=0.7).to_assessment()
    assert above.verdict is ValidationVerdict.PASSED
    assert equal.verdict is ValidationVerdict.PASSED
    assert above.source_analysis_id == _SOURCE_ID
    assert above.source_analysis.confidence == above.observed_confidence


def test_validation_fails_below_threshold() -> None:
    assessment = _command(confidence=0.69, minimum=0.7).to_assessment()
    assert assessment.verdict is ValidationVerdict.FAILED
    assert assessment.observed_confidence == SpecialistConfidence(0.69)


def test_command_requires_completed_source_analysis() -> None:
    source = _analysis(status=SpecialistAnalysisStatus.PENDING)
    with pytest.raises(ValidationInvariantError, match="completed specialist analysis"):
        ValidateSpecialistAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("validation.validate-specialist-analysis"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(source.analysis_id.value),
            ),
            assessment_id=_ASSESSMENT_ID,
            source_analysis=source,
            policy=ValidationPolicy(SpecialistConfidence(0.7)),
        )


def test_command_rejects_divergent_correlation_and_causation() -> None:
    source = _analysis()
    other = CorrelationId(UUID("93000000-0000-0000-0000-000000000099"))
    with pytest.raises(ValidationInvariantError, match="correlation"):
        ValidateSpecialistAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("validation.validate-specialist-analysis"),
            metadata=CommandMetadata(
                correlation_id=other,
                causation_id=CausationId(source.analysis_id.value),
            ),
            assessment_id=_ASSESSMENT_ID,
            source_analysis=source,
            policy=ValidationPolicy(SpecialistConfidence(0.7)),
        )
    with pytest.raises(ValidationInvariantError, match="causation"):
        ValidateSpecialistAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("validation.validate-specialist-analysis"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(UUID("93000000-0000-0000-0000-000000000098")),
            ),
            assessment_id=_ASSESSMENT_ID,
            source_analysis=source,
            policy=ValidationPolicy(SpecialistConfidence(0.7)),
        )


def test_command_rejects_source_identity_reuse() -> None:
    source = _analysis()
    with pytest.raises(ValidationInvariantError, match="identity must differ"):
        ValidateSpecialistAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("validation.validate-specialist-analysis"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION,
                causation_id=CausationId(source.analysis_id.value),
            ),
            assessment_id=ValidationAssessmentId(source.analysis_id.value),
            source_analysis=source,
            policy=ValidationPolicy(SpecialistConfidence(0.7)),
        )


def test_assessment_rejects_verdict_inconsistent_with_policy() -> None:
    source = _analysis(confidence=0.8)
    with pytest.raises(ValidationInvariantError, match="verdict must match"):
        ValidationAssessment(
            assessment_id=_ASSESSMENT_ID,
            timestamp=_TIMESTAMP,
            source_analysis=source,
            correlation_id=_CORRELATION,
            causation_id=CausationId(_SOURCE_ID.value),
            policy=ValidationPolicy(SpecialistConfidence(0.7)),
            verdict=ValidationVerdict.FAILED,
            observed_confidence=SpecialistConfidence(0.8),
        )


def test_assessment_rejects_confidence_divergent_from_source_evidence() -> None:
    source = _analysis(confidence=0.8)
    with pytest.raises(ValidationInvariantError, match="must match source analysis confidence"):
        ValidationAssessment(
            assessment_id=_ASSESSMENT_ID,
            timestamp=_TIMESTAMP,
            source_analysis=source,
            correlation_id=_CORRELATION,
            causation_id=CausationId(_SOURCE_ID.value),
            policy=ValidationPolicy(SpecialistConfidence(0.7)),
            verdict=ValidationVerdict.PASSED,
            observed_confidence=SpecialistConfidence(0.9),
        )


def test_assessment_rejects_runtime_type_bypass() -> None:
    source = _analysis()
    with pytest.raises(ValidationInvariantError, match="verdict"):
        ValidationAssessment(
            assessment_id=_ASSESSMENT_ID,
            timestamp=_TIMESTAMP,
            source_analysis=source,
            correlation_id=_CORRELATION,
            causation_id=CausationId(_SOURCE_ID.value),
            policy=ValidationPolicy(SpecialistConfidence(0.7)),
            verdict=cast(ValidationVerdict, "passed"),
            observed_confidence=SpecialistConfidence(0.8),
        )


def test_assessment_logical_values_are_deterministic() -> None:
    first = _command().to_assessment()
    second = _command().to_assessment()
    assert first.logical_values() == second.logical_values()


def test_event_preserves_assessment_trace() -> None:
    assessment = _command().to_assessment()
    event = ValidationAssessmentProducedEvent(
        event_id=_EVENT_ID,
        timestamp=_TIMESTAMP,
        event_version=DomainEventVersion("1"),
        metadata=DomainEventMetadata(
            category=DomainEventCategory("validation"),
            correlation_id=_CORRELATION,
            causation_id=CausationId(_SOURCE_ID.value),
        ),
        assessment=assessment,
    )
    assert event.assessment is assessment


def test_event_rejects_divergent_trace() -> None:
    assessment = _command().to_assessment()
    other = CorrelationId(UUID("93000000-0000-0000-0000-000000000097"))
    with pytest.raises(ValidationInvariantError, match="correlation"):
        ValidationAssessmentProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("validation"),
                correlation_id=other,
                causation_id=CausationId(_SOURCE_ID.value),
            ),
            assessment=assessment,
        )


def test_handler_is_pure_and_deterministic() -> None:
    handler = ValidateSpecialistAnalysisHandler()
    command = _command()
    first = handler.handle(command)
    second = handler.handle(command)
    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_module_descriptor_and_handler_registration() -> None:
    module = ValidationLabModule()
    registry = HandlerRegistry()
    registration = module.register_handlers(registry)
    registered: CommandHandler[
        ValidateSpecialistAnalysisCommand, ValidationAssessment
    ] | None = registry.command_handler(ValidateSpecialistAnalysisCommand)
    assert isinstance(registration, Success)
    assert module.descriptor.name == ModuleName("validation-lab")
    assert registered is module.validation_handler


def test_bootstrap_composes_and_dispatches_validation_lab() -> None:
    module = ValidationLabModule()
    boot = bootstrap(
        Configuration(application_name="qore-validation-lab-test"),
        domain_modules=(module,),
    )
    assert isinstance(boot, Success)
    dispatched: CommandResult[ValidationAssessment] = (
        boot.value.domain.message_bus.dispatch_command(_command())
    )
    assert isinstance(dispatched, Success)
    assert dispatched.value.verdict is ValidationVerdict.PASSED
    assert boot.value.domain.module_catalog.get(ModuleName("validation-lab")) is module


def test_validation_lab_does_not_enter_runtime_plan() -> None:
    boot = bootstrap(
        Configuration(application_name="qore-validation-lab-test"),
        domain_modules=(ValidationLabModule(),),
    )
    assert isinstance(boot, Success)
    assert len(boot.value.runtime_plan.components) == 1
    assert boot.value.runtime_plan.components[0].component is boot.value.engine


def test_validation_lab_instances_do_not_share_handler_state() -> None:
    first = ValidationLabModule()
    second = ValidationLabModule()
    assert first.validation_handler is not second.validation_handler
