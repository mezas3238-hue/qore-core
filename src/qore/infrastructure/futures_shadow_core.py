from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.functional.decisions import (
    DecisionOutcome,
    DecisionStatus,
    FunctionalDecision,
)
from qore.infrastructure.futures_cross_provider_certification import (
    FuturesCrossProviderAssessment,
    FuturesCrossProviderState,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class FuturesShadowCoreError(InfrastructureError):
    """Base error for Shadow Futures Core certification."""

    __slots__ = ()


class FuturesShadowCoreValidationError(FuturesShadowCoreError):
    """Violation of a Shadow Futures Core invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise FuturesShadowCoreValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise FuturesShadowCoreValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise FuturesShadowCoreValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class FuturesShadowSessionId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="shadow session id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesShadowDecisionRecordId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="shadow decision record id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesShadowEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="shadow evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class FuturesShadowSessionMode(StrEnum):
    DETERMINISTIC_OFFLINE = "deterministic_offline"
    READ_ONLY_OPERATIONAL = "read_only_operational"


class FuturesShadowSink(StrEnum):
    NULL_SHADOW_SINK = "null_shadow_sink"


@dataclass(frozen=True, slots=True)
class FuturesShadowInputCertification:
    """Cross-provider market-data evidence accepted for Shadow processing."""

    cross_provider_assessment: FuturesCrossProviderAssessment
    accepted_at: datetime
    evidence_ref: FuturesShadowEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.cross_provider_assessment, FuturesCrossProviderAssessment):
            raise FuturesShadowCoreValidationError(
                "cross_provider_assessment must be FuturesCrossProviderAssessment"
            )
        if self.cross_provider_assessment.state not in {
            FuturesCrossProviderState.CERTIFIED,
            FuturesCrossProviderState.DELAY_AWARE_CERTIFIED,
        }:
            raise FuturesShadowCoreValidationError(
                "Shadow input requires certified cross-provider evidence"
            )
        _validate_timestamp(self.accepted_at, field_name="shadow input accepted_at")
        if self.accepted_at < self.cross_provider_assessment.evaluated_at:
            raise FuturesShadowCoreValidationError(
                "shadow input cannot predate cross-provider assessment"
            )
        if not isinstance(self.evidence_ref, FuturesShadowEvidenceReference):
            raise FuturesShadowCoreValidationError(
                "shadow input evidence_ref must be FuturesShadowEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.cross_provider_assessment.logical_values(),
            self.accepted_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FuturesShadowDecisionRecord:
    """A real Core decision terminated at a non-executable Shadow sink."""

    record_id: FuturesShadowDecisionRecordId
    decision: FunctionalDecision
    input_evidence_ref: FuturesShadowEvidenceReference
    sink: FuturesShadowSink
    processed_at: datetime
    evidence_ref: FuturesShadowEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, FuturesShadowDecisionRecordId):
            raise FuturesShadowCoreValidationError(
                "record_id must be FuturesShadowDecisionRecordId"
            )
        if not isinstance(self.decision, FunctionalDecision):
            raise FuturesShadowCoreValidationError(
                "decision must be canonical FunctionalDecision"
            )
        if self.decision.status is not DecisionStatus.RESOLVED:
            raise FuturesShadowCoreValidationError(
                "Shadow certification requires resolved Core decision"
            )
        if self.decision.decision_type.value != "core.trade":
            raise FuturesShadowCoreValidationError(
                "Shadow Futures decision type must be core.trade"
            )
        if not isinstance(self.input_evidence_ref, FuturesShadowEvidenceReference):
            raise FuturesShadowCoreValidationError(
                "input_evidence_ref must be FuturesShadowEvidenceReference"
            )
        if self.sink is not FuturesShadowSink.NULL_SHADOW_SINK:
            raise FuturesShadowCoreValidationError(
                "Shadow Futures output must terminate at NULL_SHADOW_SINK"
            )
        _validate_timestamp(self.processed_at, field_name="shadow decision processed_at")
        if self.processed_at < self.decision.timestamp:
            raise FuturesShadowCoreValidationError(
                "shadow processing cannot predate Core decision"
            )
        if not isinstance(self.evidence_ref, FuturesShadowEvidenceReference):
            raise FuturesShadowCoreValidationError(
                "shadow decision evidence_ref must be FuturesShadowEvidenceReference"
            )

    @property
    def trading_action_emitted(self) -> bool:
        return False

    @property
    def core_outcome(self) -> DecisionOutcome:
        if self.decision.outcome is None:
            raise FuturesShadowCoreValidationError(
                "resolved Shadow decision unexpectedly lacks outcome"
            )
        return self.decision.outcome

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.decision.logical_values(),
            self.input_evidence_ref.logical_values(),
            self.sink.value,
            self.processed_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


class FuturesShadowCertificationStatus(StrEnum):
    CERTIFIED_OFFLINE = "certified_offline"
    CERTIFIED_READ_ONLY_OPERATIONAL = "certified_read_only_operational"


@dataclass(frozen=True, slots=True)
class FuturesShadowSessionReport:
    session_id: FuturesShadowSessionId
    mode: FuturesShadowSessionMode
    input_certification: FuturesShadowInputCertification
    decisions: tuple[FuturesShadowDecisionRecord, ...]
    started_at: datetime
    ended_at: datetime
    reported_at: datetime
    operational_evidence_ref: FuturesShadowEvidenceReference | None
    evidence_ref: FuturesShadowEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, FuturesShadowSessionId):
            raise FuturesShadowCoreValidationError(
                "session_id must be FuturesShadowSessionId"
            )
        if not isinstance(self.mode, FuturesShadowSessionMode):
            raise FuturesShadowCoreValidationError(
                "mode must be FuturesShadowSessionMode"
            )
        if not isinstance(self.input_certification, FuturesShadowInputCertification):
            raise FuturesShadowCoreValidationError(
                "input_certification must be FuturesShadowInputCertification"
            )
        if not isinstance(self.decisions, tuple) or not self.decisions or any(
            not isinstance(item, FuturesShadowDecisionRecord) for item in self.decisions
        ):
            raise FuturesShadowCoreValidationError(
                "Shadow session requires non-empty immutable decision records"
            )
        if any(
            item.input_evidence_ref != self.input_certification.evidence_ref
            for item in self.decisions
        ):
            raise FuturesShadowCoreValidationError(
                "every Shadow decision must bind exact input certification evidence"
            )
        _validate_timestamp(self.started_at, field_name="shadow session started_at")
        _validate_timestamp(self.ended_at, field_name="shadow session ended_at")
        _validate_timestamp(self.reported_at, field_name="shadow session reported_at")
        if self.ended_at <= self.started_at:
            raise FuturesShadowCoreValidationError(
                "shadow session ended_at must be after started_at"
            )
        if self.reported_at < self.ended_at:
            raise FuturesShadowCoreValidationError(
                "shadow report cannot predate session end"
            )
        if any(
            item.decision.timestamp < self.started_at
            or item.processed_at > self.ended_at
            for item in self.decisions
        ):
            raise FuturesShadowCoreValidationError(
                "Shadow decisions must fit entirely inside session window"
            )
        if self.mode is FuturesShadowSessionMode.READ_ONLY_OPERATIONAL:
            if not isinstance(self.operational_evidence_ref, FuturesShadowEvidenceReference):
                raise FuturesShadowCoreValidationError(
                    "operational Shadow mode requires operational evidence reference"
                )
        elif self.operational_evidence_ref is not None:
            raise FuturesShadowCoreValidationError(
                "offline Shadow mode cannot claim operational evidence"
            )
        if not isinstance(self.evidence_ref, FuturesShadowEvidenceReference):
            raise FuturesShadowCoreValidationError(
                "shadow report evidence_ref must be FuturesShadowEvidenceReference"
            )

    @property
    def certification_status(self) -> FuturesShadowCertificationStatus:
        if self.mode is FuturesShadowSessionMode.READ_ONLY_OPERATIONAL:
            return FuturesShadowCertificationStatus.CERTIFIED_READ_ONLY_OPERATIONAL
        return FuturesShadowCertificationStatus.CERTIFIED_OFFLINE

    @property
    def trading_actions_emitted(self) -> int:
        return 0

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.session_id.logical_values(),
            self.mode.value,
            self.input_certification.logical_values(),
            tuple(item.logical_values() for item in self.decisions),
            self.started_at.isoformat(),
            self.ended_at.isoformat(),
            self.reported_at.isoformat(),
            (
                self.operational_evidence_ref.logical_values()
                if self.operational_evidence_ref is not None
                else None
            ),
            self.evidence_ref.logical_values(),
        )


def record_futures_shadow_decision(
    decision: FunctionalDecision,
    input_certification: FuturesShadowInputCertification,
    *,
    record_id: FuturesShadowDecisionRecordId,
    processed_at: datetime,
    evidence_ref: FuturesShadowEvidenceReference,
) -> Result[FuturesShadowDecisionRecord, FuturesShadowCoreError]:
    """Record the Core decision at a NULL sink; performs no execution dispatch."""

    if not isinstance(input_certification, FuturesShadowInputCertification):
        return Failure(
            FuturesShadowCoreValidationError(
                "input_certification must be FuturesShadowInputCertification"
            )
        )
    try:
        record = FuturesShadowDecisionRecord(
            record_id=record_id,
            decision=decision,
            input_evidence_ref=input_certification.evidence_ref,
            sink=FuturesShadowSink.NULL_SHADOW_SINK,
            processed_at=processed_at,
            evidence_ref=evidence_ref,
        )
    except FuturesShadowCoreValidationError as validation_error:
        return Failure(validation_error)
    return Success(record)
