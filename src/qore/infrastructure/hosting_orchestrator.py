from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.hosting_execution_lease import (
    HostingExecutionLeaseSnapshot,
)
from qore.infrastructure.hosting_health_heartbeat import (
    HostingNewWorkContainment,
    HostingRuntimeHealthAssessment,
)
from qore.infrastructure.hosting_runtime_registry import (
    HostingRuntimeDesiredState,
    HostingRuntimeObservedState,
    HostingRuntimeRecord,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Success


class HostingOrchestratorError(InfrastructureError):
    """Base error for Managed Hosting orchestration contracts."""

    __slots__ = ()


class HostingOrchestratorValidationError(HostingOrchestratorError):
    """Violation of a hosting orchestration invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingOrchestratorValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingOrchestratorValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class HostingOrchestrationDecisionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise HostingOrchestratorValidationError(
                "hosting orchestration decision id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingOrchestrationEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise HostingOrchestratorValidationError(
                "hosting orchestration evidence reference must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class HostingOrchestrationAction(StrEnum):
    PREPARE_RUNTIME = "prepare_runtime"
    REQUEST_DRAIN = "request_drain"
    CONTAIN_NEW_WORK = "contain_new_work"
    STOP_RUNTIME = "stop_runtime"
    NO_ACTION = "no_action"


class HostingOrchestrationReason(StrEnum):
    RUNTIME_NOT_RUNNING = "runtime_not_running"
    DESIRED_DRAIN = "desired_drain"
    DESIRED_STOP = "desired_stop"
    HEALTH_CONTAINMENT = "health_containment"
    CURRENT_WRITER_REQUIRES_DRAIN = "current_writer_requires_drain"
    ALREADY_ALIGNED = "already_aligned"


@dataclass(frozen=True, slots=True)
class HostingOrchestrationDecision:
    decision_id: HostingOrchestrationDecisionId
    account_id: object
    runtime_ref: object
    action: HostingOrchestrationAction
    reason: HostingOrchestrationReason
    evaluated_at: datetime
    evidence_ref: HostingOrchestrationEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, HostingOrchestrationDecisionId):
            raise HostingOrchestratorValidationError(
                "decision_id must be HostingOrchestrationDecisionId"
            )
        if not isinstance(self.action, HostingOrchestrationAction):
            raise HostingOrchestratorValidationError(
                "action must be HostingOrchestrationAction"
            )
        if not isinstance(self.reason, HostingOrchestrationReason):
            raise HostingOrchestratorValidationError(
                "reason must be HostingOrchestrationReason"
            )
        _validate_timestamp(self.evaluated_at, field_name="orchestration evaluated_at")
        if not isinstance(self.evidence_ref, HostingOrchestrationEvidenceReference):
            raise HostingOrchestratorValidationError(
                "evidence_ref must be HostingOrchestrationEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.decision_id.logical_values(),
            self.account_id,
            self.runtime_ref,
            self.action.value,
            self.reason.value,
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def evaluate_hosting_orchestration(
    record: HostingRuntimeRecord,
    health: HostingRuntimeHealthAssessment,
    leases: HostingExecutionLeaseSnapshot,
    *,
    decision_id: HostingOrchestrationDecisionId,
    evidence_ref: HostingOrchestrationEvidenceReference,
    evaluated_at: datetime,
) -> HostingOrchestrationDecision:
    """Evaluate deployment control without acquiring/revoking execution authority."""

    if not isinstance(record, HostingRuntimeRecord):
        raise HostingOrchestratorValidationError(
            "HostingRuntimeRecord is required"
        )
    if not isinstance(health, HostingRuntimeHealthAssessment):
        raise HostingOrchestratorValidationError(
            "HostingRuntimeHealthAssessment is required"
        )
    if not isinstance(leases, HostingExecutionLeaseSnapshot):
        raise HostingOrchestratorValidationError(
            "HostingExecutionLeaseSnapshot is required"
        )
    _validate_timestamp(evaluated_at, field_name="orchestration evaluated_at")
    if health.account_id != record.account_id or health.runtime_ref != record.runtime_ref:
        raise HostingOrchestratorValidationError(
            "orchestration health must bind exact runtime record"
        )
    authority = leases.current_authority(
        record.account_id,
        evaluated_at=min(evaluated_at, leases.captured_at),
    )
    is_current_writer = (
        isinstance(authority, Success)
        and authority.value.runtime_ref == record.runtime_ref
    )
    action: HostingOrchestrationAction
    reason: HostingOrchestrationReason
    if health.containment is not HostingNewWorkContainment.NONE:
        action = HostingOrchestrationAction.CONTAIN_NEW_WORK
        reason = HostingOrchestrationReason.HEALTH_CONTAINMENT
    elif record.desired_state is HostingRuntimeDesiredState.DRAINING:
        action = HostingOrchestrationAction.REQUEST_DRAIN
        reason = HostingOrchestrationReason.DESIRED_DRAIN
    elif record.desired_state is HostingRuntimeDesiredState.STOPPED:
        if is_current_writer:
            action = HostingOrchestrationAction.REQUEST_DRAIN
            reason = HostingOrchestrationReason.CURRENT_WRITER_REQUIRES_DRAIN
        elif record.observed_state is HostingRuntimeObservedState.STOPPED:
            action = HostingOrchestrationAction.NO_ACTION
            reason = HostingOrchestrationReason.ALREADY_ALIGNED
        else:
            action = HostingOrchestrationAction.STOP_RUNTIME
            reason = HostingOrchestrationReason.DESIRED_STOP
    elif record.observed_state in (
        HostingRuntimeObservedState.STOPPED,
        HostingRuntimeObservedState.UNKNOWN,
    ):
        action = HostingOrchestrationAction.PREPARE_RUNTIME
        reason = HostingOrchestrationReason.RUNTIME_NOT_RUNNING
    else:
        action = HostingOrchestrationAction.NO_ACTION
        reason = HostingOrchestrationReason.ALREADY_ALIGNED
    return HostingOrchestrationDecision(
        decision_id=decision_id,
        account_id=record.account_id,
        runtime_ref=record.runtime_ref,
        action=action,
        reason=reason,
        evaluated_at=evaluated_at,
        evidence_ref=evidence_ref,
    )
