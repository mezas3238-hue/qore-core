from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_audit_evidence import (
    ExecutiveAuditEvidenceOutcome,
    ExecutiveAuditEvidenceRecord,
    ExecutiveAuditEvidenceRecordId,
    ExecutiveAuditEvidenceStage,
)
from qore.governance.executive_control import ExecutiveAuthorityVersion, ExecutivePrincipalId
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveControlPlaneObservabilityError(DomainError):
    """Base error for executive control-plane observability contracts."""

    __slots__ = ()


class ExecutiveControlPlaneObservabilityValidationError(
    ExecutiveControlPlaneObservabilityError
):
    """An executive observability value violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveControlPlaneObservabilityUnavailableError(
    ExecutiveControlPlaneObservabilityError
):
    """The configured observability sink is unavailable."""

    __slots__ = ()


class ExecutiveControlPlaneObservationStage(StrEnum):
    AUTHENTICATION = "authentication"
    AUTHORITY = "authority"
    AUTHORIZATION = "authorization"
    COMMAND_DISPATCH = "command-dispatch"
    QUERY_DISPATCH = "query-dispatch"
    GOVERNANCE_MUTATION = "governance-mutation"
    AUDIT = "audit"


class ExecutiveControlPlaneObservationOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    NO_ACTION = "no-action"
    BLOCKED = "blocked"
    FAILED = "failed"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveControlPlaneObservabilityValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveControlPlaneObservabilityValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validated_evidence_refs(
    values: tuple[ExecutiveEvidenceRef, ...],
) -> tuple[ExecutiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, ExecutiveEvidenceRef) for item in values
    ):
        raise ExecutiveControlPlaneObservabilityValidationError(
            "control-plane observation evidence refs must be ExecutiveEvidenceRef tuple"
        )
    if len(set(values)) != len(values):
        raise ExecutiveControlPlaneObservabilityValidationError(
            "control-plane observation evidence refs must not contain duplicates"
        )
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ExecutiveControlPlaneObservationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveControlPlaneObservabilityValidationError(
                "control-plane observation id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveControlPlaneObservation:
    """One immutable observable control-plane fact suitable for metric aggregation."""

    observation_id: ExecutiveControlPlaneObservationId
    stage: ExecutiveControlPlaneObservationStage
    outcome: ExecutiveControlPlaneObservationOutcome
    principal_id: ExecutivePrincipalId
    correlation_id: CorrelationId
    observed_at: datetime
    audit_record_id: ExecutiveAuditEvidenceRecordId
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = ()
    authority_version: ExecutiveAuthorityVersion | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, ExecutiveControlPlaneObservationId):
            raise ExecutiveControlPlaneObservabilityValidationError(
                "control-plane observation requires ExecutiveControlPlaneObservationId"
            )
        if not isinstance(self.stage, ExecutiveControlPlaneObservationStage):
            raise ExecutiveControlPlaneObservabilityValidationError(
                "control-plane observation requires explicit stage"
            )
        if not isinstance(self.outcome, ExecutiveControlPlaneObservationOutcome):
            raise ExecutiveControlPlaneObservabilityValidationError(
                "control-plane observation requires explicit outcome"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise ExecutiveControlPlaneObservabilityValidationError(
                "control-plane observation requires ExecutivePrincipalId"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveControlPlaneObservabilityValidationError(
                "control-plane observation requires CorrelationId"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")
        if not isinstance(self.audit_record_id, ExecutiveAuditEvidenceRecordId):
            raise ExecutiveControlPlaneObservabilityValidationError(
                "control-plane observation requires ExecutiveAuditEvidenceRecordId"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(self.evidence_refs),
        )
        if self.authority_version is not None and not isinstance(
            self.authority_version,
            ExecutiveAuthorityVersion,
        ):
            raise ExecutiveControlPlaneObservabilityValidationError(
                "authority version must be ExecutiveAuthorityVersion or None"
            )

    @property
    def metric_name(self) -> str:
        """Stable aggregation key; counters remain outside QORE Core."""

        return f"executive.control-plane.{self.stage.value}.{self.outcome.value}"

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.stage.value,
            self.outcome.value,
            self.metric_name,
            self.principal_id.logical_values(),
            str(self.correlation_id.value),
            self.observed_at.isoformat(),
            self.audit_record_id.logical_values(),
            tuple(item.logical_values() for item in self.evidence_refs),
            (
                self.authority_version.logical_values()
                if self.authority_version is not None
                else None
            ),
        )


class ExecutiveControlPlaneObservabilityPort(Protocol):
    """Transport/backend-neutral sink for one immutable observation at a time."""

    def emit(
        self,
        observation: ExecutiveControlPlaneObservation,
    ) -> Result[ExecutiveControlPlaneObservation, ExecutiveControlPlaneObservabilityError]: ...


_STAGE_MAP: dict[
    ExecutiveAuditEvidenceStage,
    ExecutiveControlPlaneObservationStage,
] = {
    ExecutiveAuditEvidenceStage.AUTHENTICATION: (
        ExecutiveControlPlaneObservationStage.AUTHENTICATION
    ),
    ExecutiveAuditEvidenceStage.AUTHORITY: ExecutiveControlPlaneObservationStage.AUTHORITY,
    ExecutiveAuditEvidenceStage.AUTHORIZATION: (
        ExecutiveControlPlaneObservationStage.AUTHORIZATION
    ),
    ExecutiveAuditEvidenceStage.COMMAND_DISPATCH: (
        ExecutiveControlPlaneObservationStage.COMMAND_DISPATCH
    ),
    ExecutiveAuditEvidenceStage.QUERY_DISPATCH: (
        ExecutiveControlPlaneObservationStage.QUERY_DISPATCH
    ),
    ExecutiveAuditEvidenceStage.GOVERNANCE_MUTATION: (
        ExecutiveControlPlaneObservationStage.GOVERNANCE_MUTATION
    ),
}

_OUTCOME_MAP: dict[
    ExecutiveAuditEvidenceOutcome,
    ExecutiveControlPlaneObservationOutcome,
] = {
    ExecutiveAuditEvidenceOutcome.SUCCEEDED: (
        ExecutiveControlPlaneObservationOutcome.SUCCEEDED
    ),
    ExecutiveAuditEvidenceOutcome.NO_ACTION: (
        ExecutiveControlPlaneObservationOutcome.NO_ACTION
    ),
    ExecutiveAuditEvidenceOutcome.BLOCKED: ExecutiveControlPlaneObservationOutcome.BLOCKED,
    ExecutiveAuditEvidenceOutcome.FAILED: ExecutiveControlPlaneObservationOutcome.FAILED,
}


def build_executive_control_plane_observation(
    record: ExecutiveAuditEvidenceRecord,
    *,
    observation_id: ExecutiveControlPlaneObservationId,
    observed_at: datetime,
) -> Result[ExecutiveControlPlaneObservation, ExecutiveControlPlaneObservabilityError]:
    """Project one durable audit record into one observable metric/evidence signal."""

    if not isinstance(record, ExecutiveAuditEvidenceRecord):
        return Failure(
            ExecutiveControlPlaneObservabilityValidationError(
                "control-plane observation builder requires ExecutiveAuditEvidenceRecord"
            )
        )
    try:
        _validate_timestamp(observed_at, field_name="observed_at")
        if observed_at < record.occurred_at:
            raise ExecutiveControlPlaneObservabilityValidationError(
                "control-plane observation cannot predate audit evidence"
            )
        return Success(
            ExecutiveControlPlaneObservation(
                observation_id=observation_id,
                stage=_STAGE_MAP[record.stage],
                outcome=_OUTCOME_MAP[record.outcome],
                principal_id=record.principal_id,
                correlation_id=record.correlation_id,
                observed_at=observed_at,
                audit_record_id=record.record_id,
                evidence_refs=record.evidence_refs,
                authority_version=record.authority_version,
            )
        )
    except ExecutiveControlPlaneObservabilityError as error:
        return Failure(error)


def build_executive_audit_append_observation(
    record: ExecutiveAuditEvidenceRecord,
    *,
    observation_id: ExecutiveControlPlaneObservationId,
    observed_at: datetime,
) -> Result[ExecutiveControlPlaneObservation, ExecutiveControlPlaneObservabilityError]:
    """Observe successful persistence of one exact durable executive audit record."""

    if not isinstance(record, ExecutiveAuditEvidenceRecord):
        return Failure(
            ExecutiveControlPlaneObservabilityValidationError(
                "audit append observation requires ExecutiveAuditEvidenceRecord"
            )
        )
    try:
        _validate_timestamp(observed_at, field_name="observed_at")
        if observed_at < record.occurred_at:
            raise ExecutiveControlPlaneObservabilityValidationError(
                "audit append observation cannot predate audit evidence"
            )
        return Success(
            ExecutiveControlPlaneObservation(
                observation_id=observation_id,
                stage=ExecutiveControlPlaneObservationStage.AUDIT,
                outcome=ExecutiveControlPlaneObservationOutcome.SUCCEEDED,
                principal_id=record.principal_id,
                correlation_id=record.correlation_id,
                observed_at=observed_at,
                audit_record_id=record.record_id,
                evidence_refs=record.evidence_refs,
                authority_version=record.authority_version,
            )
        )
    except ExecutiveControlPlaneObservabilityError as error:
        return Failure(error)
