from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.hosting_execution_lease import (
    HostingExecutionLeaseId,
    HostingExecutionLeaseSnapshot,
    HostingFencingGeneration,
)
from qore.infrastructure.hosting_failover_reconciliation import (
    HostingFailoverAssessment,
    HostingFailoverReadiness,
)
from qore.infrastructure.hosting_health_heartbeat import (
    HostingHeartbeatFreshness,
    HostingNewWorkContainment,
    HostingRuntimeHealth,
    HostingRuntimeHealthAssessment,
)
from qore.infrastructure.hosting_runtime_registry import (
    HostingRuntimeDesiredState,
    HostingRuntimeObservedState,
    HostingRuntimeRecord,
    HostingRuntimeRegistryGeneration,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Success


class HostingTelemetryError(InfrastructureError):
    """Base error for observational Managed Hosting telemetry."""

    __slots__ = ()


class HostingTelemetryValidationError(HostingTelemetryError):
    """Violation of a hosting telemetry invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingTelemetryValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingTelemetryValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class HostingTelemetrySnapshotId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise HostingTelemetryValidationError(
                "hosting telemetry snapshot id must be UUID"
            )


@dataclass(frozen=True, slots=True)
class HostingTelemetryEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise HostingTelemetryValidationError(
                "hosting telemetry evidence reference must be UUID"
            )


class HostingWriterObservation(StrEnum):
    CURRENT_WRITER = "current_writer"
    OTHER_RUNTIME_IS_WRITER = "other_runtime_is_writer"
    NO_CURRENT_WRITER = "no_current_writer"


@dataclass(frozen=True, slots=True)
class HostingRuntimeTelemetry:
    """Read-only runtime telemetry; fields never constitute authority."""

    snapshot_id: HostingTelemetrySnapshotId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    registry_generation: HostingRuntimeRegistryGeneration
    desired_state: HostingRuntimeDesiredState
    observed_state: HostingRuntimeObservedState
    health: HostingRuntimeHealth
    freshness: HostingHeartbeatFreshness
    containment: HostingNewWorkContainment
    writer_observation: HostingWriterObservation
    lease_id: HostingExecutionLeaseId | None
    fencing_generation: HostingFencingGeneration | None
    failover_readiness: HostingFailoverReadiness | None
    observed_at: datetime
    evidence_ref: HostingTelemetryEvidenceReference

    def __post_init__(self) -> None:
        _validate_timestamp(self.observed_at, field_name="telemetry observed_at")
        current = self.writer_observation is HostingWriterObservation.CURRENT_WRITER
        if current != (
            isinstance(self.lease_id, HostingExecutionLeaseId)
            and isinstance(self.fencing_generation, HostingFencingGeneration)
        ):
            raise HostingTelemetryValidationError(
                "only CURRENT_WRITER telemetry may carry lease/fencing identity"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.snapshot_id.value),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.registry_generation.logical_values(),
            self.desired_state.value,
            self.observed_state.value,
            self.health.value,
            self.freshness.value,
            self.containment.value,
            self.writer_observation.value,
            self.lease_id.logical_values() if self.lease_id else None,
            self.fencing_generation.logical_values()
            if self.fencing_generation
            else None,
            self.failover_readiness.value if self.failover_readiness else None,
            self.observed_at.isoformat(),
            str(self.evidence_ref.value),
        )


def project_hosting_runtime_telemetry(
    record: HostingRuntimeRecord,
    health: HostingRuntimeHealthAssessment,
    leases: HostingExecutionLeaseSnapshot,
    *,
    registry_generation: HostingRuntimeRegistryGeneration,
    snapshot_id: HostingTelemetrySnapshotId,
    evidence_ref: HostingTelemetryEvidenceReference,
    observed_at: datetime,
    failover: HostingFailoverAssessment | None = None,
) -> HostingRuntimeTelemetry:
    """Project existing hosting facts without changing any authority state."""

    _validate_timestamp(observed_at, field_name="telemetry observed_at")
    if record.observed_at > observed_at:
        raise HostingTelemetryValidationError(
            "runtime observation cannot be newer than telemetry"
        )
    if health.evaluated_at != observed_at:
        raise HostingTelemetryValidationError(
            "health assessment must bind exact telemetry time"
        )
    if health.account_id != record.account_id or health.runtime_ref != record.runtime_ref:
        raise HostingTelemetryValidationError(
            "health assessment must bind exact telemetry runtime"
        )
    if observed_at > leases.captured_at:
        raise HostingTelemetryValidationError(
            "lease snapshot must cover telemetry observation time"
        )
    if failover is not None:
        if failover.account_id != record.account_id:
            raise HostingTelemetryValidationError(
                "failover assessment account binding mismatch"
            )
        if failover.evaluated_at != observed_at:
            raise HostingTelemetryValidationError(
                "failover assessment must bind exact telemetry time"
            )
        if record.runtime_ref not in (
            failover.previous_runtime_ref,
            failover.candidate_runtime_ref,
        ):
            raise HostingTelemetryValidationError(
                "failover assessment does not reference telemetry runtime"
            )

    authority = leases.current_authority(
        record.account_id,
        evaluated_at=observed_at,
    )
    lease_id: HostingExecutionLeaseId | None = None
    generation: HostingFencingGeneration | None = None
    if isinstance(authority, Success):
        if authority.value.runtime_ref == record.runtime_ref:
            writer = HostingWriterObservation.CURRENT_WRITER
            lease_id = authority.value.lease_id
            generation = authority.value.generation
        else:
            writer = HostingWriterObservation.OTHER_RUNTIME_IS_WRITER
    else:
        writer = HostingWriterObservation.NO_CURRENT_WRITER

    return HostingRuntimeTelemetry(
        snapshot_id=snapshot_id,
        account_id=record.account_id,
        runtime_ref=record.runtime_ref,
        registry_generation=registry_generation,
        desired_state=record.desired_state,
        observed_state=record.observed_state,
        health=health.health,
        freshness=health.freshness,
        containment=health.containment,
        writer_observation=writer,
        lease_id=lease_id,
        fencing_generation=generation,
        failover_readiness=failover.readiness if failover else None,
        observed_at=observed_at,
        evidence_ref=evidence_ref,
    )
