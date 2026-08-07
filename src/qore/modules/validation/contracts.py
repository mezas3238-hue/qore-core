from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.domain.commands import Command
from qore.domain.events import (
    BusinessDomainEvent,
    CausationId,
    CorrelationId,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.kernel.errors import DomainError
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistAnalysisStatus,
    SpecialistConfidence,
)


class ValidationError(DomainError):
    """Base error for Validation Lab contracts."""

    __slots__ = ()


class ValidationInvariantError(ValidationError):
    """Explicit violation of a Validation Lab invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ValidationAssessmentId:
    """Explicit identity of a Validation Lab assessment."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ValidationInvariantError("validation assessment id must be a UUID")


class ValidationVerdict(StrEnum):
    """Closed verdict produced by deterministic Validation Lab rules."""

    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    """Explicit deterministic policy used to validate a specialist analysis."""

    minimum_confidence: SpecialistConfidence

    def __post_init__(self) -> None:
        if not isinstance(self.minimum_confidence, SpecialistConfidence):
            raise ValidationInvariantError(
                "validation minimum_confidence must be SpecialistConfidence"
            )


@dataclass(frozen=True, slots=True)
class ValidationAssessment:
    """Immutable validation result retaining its complete source analysis."""

    assessment_id: ValidationAssessmentId
    timestamp: datetime
    source_analysis: SpecialistAnalysis
    correlation_id: CorrelationId
    causation_id: CausationId
    policy: ValidationPolicy
    verdict: ValidationVerdict
    observed_confidence: SpecialistConfidence

    def __post_init__(self) -> None:
        if not isinstance(self.assessment_id, ValidationAssessmentId):
            raise ValidationInvariantError(
                "validation assessment_id must be ValidationAssessmentId"
            )
        if not isinstance(self.timestamp, datetime):
            raise ValidationInvariantError("validation timestamp must be a datetime")
        if not isinstance(self.source_analysis, SpecialistAnalysis):
            raise ValidationInvariantError(
                "validation source_analysis must be SpecialistAnalysis"
            )
        if self.source_analysis.status is not SpecialistAnalysisStatus.COMPLETED:
            raise ValidationInvariantError(
                "validation assessment requires a completed source analysis"
            )
        if self.source_analysis.confidence is None:
            raise ValidationInvariantError(
                "validation assessment requires source analysis confidence"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ValidationInvariantError(
                "validation correlation_id must be CorrelationId"
            )
        if self.correlation_id != self.source_analysis.metadata.correlation_id:
            raise ValidationInvariantError(
                "validation correlation must match source analysis"
            )
        if not isinstance(self.causation_id, CausationId):
            raise ValidationInvariantError("validation causation_id must be CausationId")
        if self.causation_id != CausationId(self.source_analysis.analysis_id.value):
            raise ValidationInvariantError(
                "validation causation must match source analysis"
            )
        if self.assessment_id.value == self.source_analysis.analysis_id.value:
            raise ValidationInvariantError(
                "validation assessment identity must differ from source analysis"
            )
        if not isinstance(self.policy, ValidationPolicy):
            raise ValidationInvariantError("validation policy must be ValidationPolicy")
        if not isinstance(self.verdict, ValidationVerdict):
            raise ValidationInvariantError("validation verdict must be ValidationVerdict")
        if not isinstance(self.observed_confidence, SpecialistConfidence):
            raise ValidationInvariantError(
                "validation observed_confidence must be SpecialistConfidence"
            )
        if self.observed_confidence != self.source_analysis.confidence:
            raise ValidationInvariantError(
                "validation observed_confidence must match source analysis confidence"
            )
        expected = (
            ValidationVerdict.PASSED
            if self.observed_confidence.value >= self.policy.minimum_confidence.value
            else ValidationVerdict.FAILED
        )
        if self.verdict is not expected:
            raise ValidationInvariantError(
                "validation verdict must match the deterministic policy evaluation"
            )

    @property
    def source_analysis_id(self) -> SpecialistAnalysisId:
        """Expose the source identity derived from the retained evidence."""
        return self.source_analysis.analysis_id

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.assessment_id.value),
            self.timestamp.isoformat(),
            self.source_analysis.logical_values(),
            str(self.correlation_id.value),
            str(self.causation_id.value),
            self.policy.minimum_confidence.value,
            self.verdict.value,
            self.observed_confidence.value,
        )


@dataclass(frozen=True, slots=True)
class ValidateSpecialistAnalysisCommand(Command):
    """Request deterministic validation of one completed specialist analysis."""

    assessment_id: ValidationAssessmentId
    source_analysis: SpecialistAnalysis
    policy: ValidationPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.assessment_id, ValidationAssessmentId):
            raise ValidationInvariantError(
                "validation assessment_id must be ValidationAssessmentId"
            )
        if not isinstance(self.source_analysis, SpecialistAnalysis):
            raise ValidationInvariantError(
                "validation source_analysis must be SpecialistAnalysis"
            )
        if not isinstance(self.policy, ValidationPolicy):
            raise ValidationInvariantError("validation policy must be ValidationPolicy")
        if self.source_analysis.status is not SpecialistAnalysisStatus.COMPLETED:
            raise ValidationInvariantError(
                "validation requires a completed specialist analysis"
            )
        if self.source_analysis.confidence is None:
            raise ValidationInvariantError(
                "validation requires source analysis confidence"
            )
        if self.metadata.correlation_id != self.source_analysis.metadata.correlation_id:
            raise ValidationInvariantError(
                "validation command correlation must match source analysis"
            )
        expected_causation = CausationId(self.source_analysis.analysis_id.value)
        if self.metadata.causation_id != expected_causation:
            raise ValidationInvariantError(
                "validation command causation must match source analysis"
            )
        if self.assessment_id.value == self.source_analysis.analysis_id.value:
            raise ValidationInvariantError(
                "validation assessment identity must differ from source analysis"
            )

    def to_assessment(self) -> ValidationAssessment:
        confidence = self.source_analysis.confidence
        if confidence is None:
            raise ValidationInvariantError(
                "validation requires source analysis confidence"
            )
        verdict = (
            ValidationVerdict.PASSED
            if confidence.value >= self.policy.minimum_confidence.value
            else ValidationVerdict.FAILED
        )
        causation = self.metadata.causation_id
        if causation is None:
            raise ValidationInvariantError(
                "validation command causation must match source analysis"
            )
        return ValidationAssessment(
            assessment_id=self.assessment_id,
            timestamp=self.timestamp,
            source_analysis=self.source_analysis,
            correlation_id=self.metadata.correlation_id,
            causation_id=causation,
            policy=self.policy,
            verdict=verdict,
            observed_confidence=confidence,
        )


class ValidationAssessmentProducedEvent(BusinessDomainEvent):
    """Event representing a Validation Lab assessment already produced."""

    __slots__ = ("_assessment",)
    _assessment: ValidationAssessment

    def __init__(
        self,
        *,
        event_id: DomainEventId,
        timestamp: datetime,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
        assessment: ValidationAssessment,
    ) -> None:
        if not isinstance(assessment, ValidationAssessment):
            raise ValidationInvariantError(
                "validation event assessment must be ValidationAssessment"
            )
        if metadata.correlation_id != assessment.correlation_id:
            raise ValidationInvariantError(
                "validation event correlation must match assessment"
            )
        if metadata.causation_id != assessment.causation_id:
            raise ValidationInvariantError(
                "validation event causation must match assessment"
            )
        object.__setattr__(self, "_assessment", assessment)
        super().__init__(
            timestamp=timestamp,
            event_name="validation.assessment-produced",
            event_id=event_id,
            event_version=event_version,
            metadata=metadata,
        )

    @property
    def assessment(self) -> ValidationAssessment:
        return self._assessment

    def logical_values(self) -> tuple[object, ...]:
        return (*super().logical_values(), self._assessment.logical_values())
