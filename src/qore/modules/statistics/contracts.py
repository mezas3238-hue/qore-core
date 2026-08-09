from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
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
from qore.kernel.temporal import is_timezone_aware_datetime
from qore.modules.validation.contracts import ValidationAssessment, ValidationVerdict
from qore.specialist.analysis import SpecialistConfidence


class StatisticsError(DomainError):
    """Base error for Statistics Service contracts."""

    __slots__ = ()


class StatisticsInvariantError(StatisticsError):
    """Explicit violation of a Statistics Service invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class StatisticsSnapshotId:
    """Explicit identity of one descriptive statistics snapshot."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise StatisticsInvariantError("statistics snapshot id must be a UUID")


def _mean_confidence(assessments: tuple[ValidationAssessment, ...]) -> SpecialistConfidence:
    confidence_total = sum(
        (Decimal(str(item.observed_confidence.value)) for item in assessments),
        Decimal(0),
    )
    return SpecialistConfidence(float(confidence_total / Decimal(len(assessments))))


@dataclass(frozen=True, slots=True)
class StatisticsSnapshot:
    """Immutable descriptive summary retaining all source assessments."""

    snapshot_id: StatisticsSnapshotId
    timestamp: datetime
    correlation_id: CorrelationId
    source_assessments: tuple[ValidationAssessment, ...]
    sample_size: int
    passed_count: int
    failed_count: int
    pass_rate: float
    mean_observed_confidence: SpecialistConfidence

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, StatisticsSnapshotId):
            raise StatisticsInvariantError("snapshot_id must be StatisticsSnapshotId")
        if not is_timezone_aware_datetime(self.timestamp):
            raise StatisticsInvariantError(
                "statistics timestamp must be a timezone-aware datetime"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise StatisticsInvariantError("correlation_id must be CorrelationId")
        if not isinstance(self.source_assessments, tuple) or not self.source_assessments:
            raise StatisticsInvariantError("source_assessments must be a non-empty tuple")
        if any(
            not isinstance(value, ValidationAssessment)
            for value in self.source_assessments
        ):
            raise StatisticsInvariantError(
                "source_assessments must contain ValidationAssessment values"
            )
        source_ids = self.source_assessment_ids
        if len(set(source_ids)) != len(source_ids):
            raise StatisticsInvariantError("source assessments must be unique")
        if self.snapshot_id.value in source_ids:
            raise StatisticsInvariantError(
                "statistics snapshot identity must differ from source assessments"
            )
        if any(
            assessment.correlation_id != self.correlation_id
            for assessment in self.source_assessments
        ):
            raise StatisticsInvariantError(
                "statistics correlation must match all source assessments"
            )
        if type(self.sample_size) is not int or self.sample_size <= 0:
            raise StatisticsInvariantError("sample_size must be a positive int")
        if type(self.passed_count) is not int or type(self.failed_count) is not int:
            raise StatisticsInvariantError("statistics counts must be ints")
        if self.passed_count < 0 or self.failed_count < 0:
            raise StatisticsInvariantError("statistics counts must not be negative")
        if self.sample_size != len(self.source_assessments):
            raise StatisticsInvariantError("sample_size must match source assessments")
        expected_passed = sum(
            1
            for item in self.source_assessments
            if item.verdict is ValidationVerdict.PASSED
        )
        expected_failed = self.sample_size - expected_passed
        if self.passed_count != expected_passed or self.failed_count != expected_failed:
            raise StatisticsInvariantError(
                "statistics counts must match source assessment verdicts"
            )
        if type(self.pass_rate) is not float or not 0.0 <= self.pass_rate <= 1.0:
            raise StatisticsInvariantError("pass_rate must be a float between 0 and 1")
        expected_rate = expected_passed / self.sample_size
        if self.pass_rate != expected_rate:
            raise StatisticsInvariantError(
                "pass_rate must match source assessment verdicts"
            )
        if not isinstance(self.mean_observed_confidence, SpecialistConfidence):
            raise StatisticsInvariantError(
                "mean_observed_confidence must be SpecialistConfidence"
            )
        if self.mean_observed_confidence != _mean_confidence(self.source_assessments):
            raise StatisticsInvariantError(
                "mean_observed_confidence must match source assessments"
            )

    @property
    def source_assessment_ids(self) -> tuple[UUID, ...]:
        """Expose source identities derived from retained evidence."""
        return tuple(item.assessment_id.value for item in self.source_assessments)

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.snapshot_id.value),
            self.timestamp.isoformat(),
            str(self.correlation_id.value),
            tuple(item.logical_values() for item in self.source_assessments),
            self.sample_size,
            self.passed_count,
            self.failed_count,
            self.pass_rate,
            self.mean_observed_confidence.value,
        )


@dataclass(frozen=True, slots=True)
class SummarizeValidationAssessmentsCommand(Command):
    """Request a deterministic descriptive summary of validation assessments."""

    snapshot_id: StatisticsSnapshotId
    assessments: tuple[ValidationAssessment, ...]

    def __post_init__(self) -> None:
        Command.__post_init__(self)
        if not isinstance(self.snapshot_id, StatisticsSnapshotId):
            raise StatisticsInvariantError("snapshot_id must be StatisticsSnapshotId")
        if not isinstance(self.assessments, tuple) or not self.assessments:
            raise StatisticsInvariantError("assessments must be a non-empty immutable tuple")
        if any(not isinstance(item, ValidationAssessment) for item in self.assessments):
            raise StatisticsInvariantError("assessments must contain ValidationAssessment values")
        ids = tuple(item.assessment_id.value for item in self.assessments)
        if len(set(ids)) != len(ids):
            raise StatisticsInvariantError("statistics source assessments must be unique")
        correlations = {item.correlation_id for item in self.assessments}
        if len(correlations) != 1 or self.metadata.correlation_id not in correlations:
            raise StatisticsInvariantError(
                "statistics command correlation must match all source assessments"
            )
        if self.snapshot_id.value in ids:
            raise StatisticsInvariantError(
                "statistics snapshot identity must differ from source assessments"
            )
        expected_causation = CausationId(ids[-1])
        if self.metadata.causation_id != expected_causation:
            raise StatisticsInvariantError(
                "statistics command causation must match the last source assessment"
            )

    def to_snapshot(self) -> StatisticsSnapshot:
        sample_size = len(self.assessments)
        passed_count = sum(
            1 for item in self.assessments if item.verdict is ValidationVerdict.PASSED
        )
        failed_count = sample_size - passed_count
        return StatisticsSnapshot(
            snapshot_id=self.snapshot_id,
            timestamp=self.timestamp,
            correlation_id=self.metadata.correlation_id,
            source_assessments=self.assessments,
            sample_size=sample_size,
            passed_count=passed_count,
            failed_count=failed_count,
            pass_rate=passed_count / sample_size,
            mean_observed_confidence=_mean_confidence(self.assessments),
        )


class StatisticsSnapshotProducedEvent(BusinessDomainEvent):
    """Event representing a descriptive statistics snapshot already produced."""

    __slots__ = ("_snapshot",)
    _snapshot: StatisticsSnapshot

    def __init__(
        self,
        *,
        event_id: DomainEventId,
        timestamp: datetime,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
        snapshot: StatisticsSnapshot,
    ) -> None:
        if not isinstance(snapshot, StatisticsSnapshot):
            raise StatisticsInvariantError("statistics event snapshot must be StatisticsSnapshot")
        if metadata.correlation_id != snapshot.correlation_id:
            raise StatisticsInvariantError("statistics event correlation must match snapshot")
        if metadata.causation_id is None:
            raise StatisticsInvariantError("statistics event causation must be explicit")
        if metadata.causation_id.value != snapshot.source_assessment_ids[-1]:
            raise StatisticsInvariantError(
                "statistics event causation must match last source assessment"
            )
        object.__setattr__(self, "_snapshot", snapshot)
        super().__init__(
            timestamp=timestamp,
            event_name="statistics.snapshot-produced",
            event_id=event_id,
            event_version=event_version,
            metadata=metadata,
        )

    @property
    def snapshot(self) -> StatisticsSnapshot:
        return self._snapshot

    def logical_values(self) -> tuple[object, ...]:
        return (*super().logical_values(), self._snapshot.logical_values())
