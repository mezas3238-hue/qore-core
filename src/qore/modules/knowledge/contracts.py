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
from qore.kernel.temporal import canonical_instant, is_timezone_aware_datetime
from qore.modules.statistics.contracts import StatisticsSnapshot, StatisticsSnapshotId
from qore.specialist.analysis import SpecialistConfidence


class KnowledgeError(DomainError):
    """Base error for Knowledge Service contracts."""

    __slots__ = ()


class KnowledgeInvariantError(KnowledgeError):
    """Explicit violation of a Knowledge Service invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class KnowledgeRecordId:
    """Explicit identity of one immutable knowledge record."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise KnowledgeInvariantError("knowledge record id must be a UUID")


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    """Immutable structured projection of one statistics snapshot."""

    record_id: KnowledgeRecordId
    timestamp: datetime
    source_snapshot: StatisticsSnapshot
    correlation_id: CorrelationId
    causation_id: CausationId
    sample_size: int
    passed_count: int
    failed_count: int
    pass_rate: float
    mean_observed_confidence: SpecialistConfidence

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, KnowledgeRecordId):
            raise KnowledgeInvariantError("record_id must be KnowledgeRecordId")
        if not is_timezone_aware_datetime(self.timestamp):
            raise KnowledgeInvariantError(
                "knowledge timestamp must be a timezone-aware datetime"
            )
        if not isinstance(self.source_snapshot, StatisticsSnapshot):
            raise KnowledgeInvariantError(
                "source_snapshot must be StatisticsSnapshot"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise KnowledgeInvariantError("correlation_id must be CorrelationId")
        if not isinstance(self.causation_id, CausationId):
            raise KnowledgeInvariantError("causation_id must be CausationId")
        snapshot = self.source_snapshot
        if self.correlation_id != snapshot.correlation_id:
            raise KnowledgeInvariantError(
                "knowledge correlation must match source snapshot"
            )
        if self.causation_id != CausationId(snapshot.snapshot_id.value):
            raise KnowledgeInvariantError(
                "knowledge causation must match source_snapshot_id"
            )
        if self.record_id.value == snapshot.snapshot_id.value:
            raise KnowledgeInvariantError(
                "knowledge record identity must differ from source snapshot"
            )
        if type(self.sample_size) is not int or self.sample_size <= 0:
            raise KnowledgeInvariantError("sample_size must be a positive int")
        if type(self.passed_count) is not int or type(self.failed_count) is not int:
            raise KnowledgeInvariantError("knowledge counts must be ints")
        if self.passed_count < 0 or self.failed_count < 0:
            raise KnowledgeInvariantError("knowledge counts must not be negative")
        if self.passed_count + self.failed_count != self.sample_size:
            raise KnowledgeInvariantError("knowledge counts must equal sample_size")
        if type(self.pass_rate) is not float or not 0.0 <= self.pass_rate <= 1.0:
            raise KnowledgeInvariantError("pass_rate must be a float between 0 and 1")
        if self.pass_rate != self.passed_count / self.sample_size:
            raise KnowledgeInvariantError(
                "pass_rate must match passed_count/sample_size"
            )
        if not isinstance(self.mean_observed_confidence, SpecialistConfidence):
            raise KnowledgeInvariantError(
                "mean_observed_confidence must be SpecialistConfidence"
            )
        if (
            self.sample_size != snapshot.sample_size
            or self.passed_count != snapshot.passed_count
            or self.failed_count != snapshot.failed_count
            or self.pass_rate != snapshot.pass_rate
            or self.mean_observed_confidence != snapshot.mean_observed_confidence
        ):
            raise KnowledgeInvariantError(
                "knowledge metrics must exactly match source snapshot"
            )

    @property
    def source_snapshot_id(self) -> StatisticsSnapshotId:
        return self.source_snapshot.snapshot_id

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.record_id.value),
            canonical_instant(self.timestamp),
            self.source_snapshot.logical_values(),
            str(self.correlation_id.value),
            str(self.causation_id.value),
            self.sample_size,
            self.passed_count,
            self.failed_count,
            self.pass_rate,
            self.mean_observed_confidence.value,
        )


@dataclass(frozen=True, slots=True)
class CaptureStatisticsKnowledgeCommand(Command):
    """Capture one explicit statistics snapshot as structured knowledge."""

    record_id: KnowledgeRecordId
    source_snapshot: StatisticsSnapshot

    def __post_init__(self) -> None:
        Command.__post_init__(self)
        if not isinstance(self.record_id, KnowledgeRecordId):
            raise KnowledgeInvariantError("record_id must be KnowledgeRecordId")
        if not isinstance(self.source_snapshot, StatisticsSnapshot):
            raise KnowledgeInvariantError(
                "source_snapshot must be StatisticsSnapshot"
            )
        if self.metadata.correlation_id != self.source_snapshot.correlation_id:
            raise KnowledgeInvariantError(
                "knowledge command correlation must match source snapshot"
            )
        expected_causation = CausationId(self.source_snapshot.snapshot_id.value)
        if self.metadata.causation_id != expected_causation:
            raise KnowledgeInvariantError(
                "knowledge command causation must match source snapshot"
            )
        if self.record_id.value == self.source_snapshot.snapshot_id.value:
            raise KnowledgeInvariantError(
                "knowledge record identity must differ from source snapshot"
            )

    def to_record(self) -> KnowledgeRecord:
        causation = self.metadata.causation_id
        if causation is None:
            raise KnowledgeInvariantError(
                "knowledge command causation must match source snapshot"
            )
        snapshot = self.source_snapshot
        return KnowledgeRecord(
            record_id=self.record_id,
            timestamp=self.timestamp,
            source_snapshot=snapshot,
            correlation_id=self.metadata.correlation_id,
            causation_id=causation,
            sample_size=snapshot.sample_size,
            passed_count=snapshot.passed_count,
            failed_count=snapshot.failed_count,
            pass_rate=snapshot.pass_rate,
            mean_observed_confidence=snapshot.mean_observed_confidence,
        )


class KnowledgeRecordCapturedEvent(BusinessDomainEvent):
    """Event representing a structured knowledge record already captured."""

    __slots__ = ("_record",)
    _record: KnowledgeRecord

    def __init__(
        self,
        *,
        event_id: DomainEventId,
        timestamp: datetime,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
        record: KnowledgeRecord,
    ) -> None:
        if not isinstance(record, KnowledgeRecord):
            raise KnowledgeInvariantError(
                "knowledge event record must be KnowledgeRecord"
            )
        if metadata.correlation_id != record.correlation_id:
            raise KnowledgeInvariantError(
                "knowledge event correlation must match record"
            )
        if metadata.causation_id != record.causation_id:
            raise KnowledgeInvariantError(
                "knowledge event causation must match record"
            )
        object.__setattr__(self, "_record", record)
        super().__init__(
            timestamp=timestamp,
            event_name="knowledge.record-captured",
            event_id=event_id,
            event_version=event_version,
            metadata=metadata,
        )

    @property
    def record(self) -> KnowledgeRecord:
        return self._record

    def logical_values(self) -> tuple[object, ...]:
        return (*super().logical_values(), self._record.logical_values())
