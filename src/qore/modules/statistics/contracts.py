from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


@dataclass(frozen=True, slots=True)
class StatisticsSnapshot:
    """Immutable descriptive summary over explicit validation assessments."""

    snapshot_id: StatisticsSnapshotId
    timestamp: datetime
    correlation_id: CorrelationId
    source_assessment_ids: tuple[UUID, ...]
    sample_size: int
    passed_count: int
    failed_count: int
    pass_rate: float
    mean_observed_confidence: SpecialistConfidence

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, StatisticsSnapshotId):
            raise StatisticsInvariantError("snapshot_id must be StatisticsSnapshotId")
        if not isinstance(self.timestamp, datetime):
            raise StatisticsInvariantError("statistics timestamp must be datetime")
        if not isinstance(self.correlation_id, CorrelationId):
            raise StatisticsInvariantError("correlation_id must be CorrelationId")
        if not isinstance(self.source_assessment_ids, tuple) or not self.source_assessment_ids:
            raise StatisticsInvariantError("source_assessment_ids must be a non-empty tuple")
        if any(not isinstance(value, UUID) for value in self.source_assessment_ids):
            raise StatisticsInvariantError("source_assessment_ids must contain UUID values")
        if len(set(self.source_assessment_ids)) != len(self.source_assessment_ids):
            raise StatisticsInvariantError("source_assessment_ids must be unique")
        if type(self.sample_size) is not int or self.sample_size <= 0:
            raise StatisticsInvariantError("sample_size must be a positive int")
        if type(self.passed_count) is not int or type(self.failed_count) is not int:
            raise StatisticsInvariantError("statistics counts must be ints")
        if self.passed_count < 0 or self.failed_count < 0:
            raise StatisticsInvariantError("statistics counts must not be negative")
        if self.passed_count + self.failed_count != self.sample_size:
            raise StatisticsInvariantError("statistics counts must equal sample_size")
        if self.sample_size != len(self.source_assessment_ids):
            raise StatisticsInvariantError("sample_size must match source_assessment_ids")
        if type(self.pass_rate) is not float or not 0.0 <= self.pass_rate <= 1.0:
            raise StatisticsInvariantError("pass_rate must be a float between 0 and 1")
        expected_rate = self.passed_count / self.sample_size
        if self.pass_rate != expected_rate:
            raise StatisticsInvariantError("pass_rate must match passed_count/sample_size")
        if not isinstance(self.mean_observed_confidence, SpecialistConfidence):
            raise StatisticsInvariantError(
                "mean_observed_confidence must be SpecialistConfidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.snapshot_id.value),
            self.timestamp.isoformat(),
            str(self.correlation_id.value),
            tuple(str(value) for value in self.source_assessment_ids),
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
        mean = sum(item.observed_confidence.value for item in self.assessments) / sample_size
        return StatisticsSnapshot(
            snapshot_id=self.snapshot_id,
            timestamp=self.timestamp,
            correlation_id=self.metadata.correlation_id,
            source_assessment_ids=tuple(item.assessment_id.value for item in self.assessments),
            sample_size=sample_size,
            passed_count=passed_count,
            failed_count=failed_count,
            pass_rate=passed_count / sample_size,
            mean_observed_confidence=SpecialistConfidence(float(mean)),
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
