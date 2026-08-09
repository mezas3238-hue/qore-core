from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveControlPlaneResilienceError(DomainError):
    """Base error for executive control-plane resilience contracts."""

    __slots__ = ()


class ExecutiveControlPlaneResilienceValidationError(
    ExecutiveControlPlaneResilienceError
):
    """A resilience policy or recovery plan violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveControlPlaneOperation(StrEnum):
    AUTHORITY_READ = "authority-read"
    REPLAY_CLAIM = "replay-claim"
    COMMAND_DISPATCH = "command-dispatch"
    READ_DISPATCH = "read-dispatch"
    GOVERNANCE_MUTATION = "governance-mutation"
    AUDIT_APPEND = "audit-append"
    OBSERVABILITY_EMIT = "observability-emit"


class ExecutiveControlPlaneFailureKind(StrEnum):
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    AMBIGUOUS_OUTCOME = "ambiguous-outcome"


class ExecutiveControlPlaneRecoveryRequirement(StrEnum):
    REREAD_AUTHORITY = "reread-authority"
    VERIFY_REPLAY_CLAIM = "verify-replay-claim"
    VERIFY_CONTROL_RECEIPT = "verify-control-receipt"
    ISSUE_NEW_READ_REQUEST = "issue-new-read-request"
    REREAD_GOVERNANCE_STATE = "reread-governance-state"
    VERIFY_AUDIT_RECORD = "verify-audit-record"
    OBSERVABILITY_CAN_DEGRADE = "observability-can-degrade"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveControlPlaneResilienceValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveControlPlaneResilienceValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ExecutiveControlPlaneTimeout:
    milliseconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.milliseconds, int) or isinstance(self.milliseconds, bool):
            raise ExecutiveControlPlaneResilienceValidationError(
                "control-plane timeout milliseconds must be an integer"
            )
        if self.milliseconds <= 0:
            raise ExecutiveControlPlaneResilienceValidationError(
                "control-plane timeout milliseconds must be positive"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.milliseconds,)


@dataclass(frozen=True, slots=True)
class ExecutiveControlPlaneOperationPolicy:
    operation: ExecutiveControlPlaneOperation
    timeout: ExecutiveControlPlaneTimeout

    def __post_init__(self) -> None:
        if not isinstance(self.operation, ExecutiveControlPlaneOperation):
            raise ExecutiveControlPlaneResilienceValidationError(
                "operation policy requires ExecutiveControlPlaneOperation"
            )
        if not isinstance(self.timeout, ExecutiveControlPlaneTimeout):
            raise ExecutiveControlPlaneResilienceValidationError(
                "operation policy requires ExecutiveControlPlaneTimeout"
            )

    @property
    def automatic_retry_allowed(self) -> bool:
        return False

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.operation.value,
            self.timeout.logical_values(),
            self.automatic_retry_allowed,
        )


@dataclass(frozen=True, slots=True)
class ExecutiveControlPlaneResiliencePolicy:
    """Complete explicit timeout policy pack; never executes retries itself."""

    operations: tuple[ExecutiveControlPlaneOperationPolicy, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.operations, tuple) or any(
            not isinstance(item, ExecutiveControlPlaneOperationPolicy)
            for item in self.operations
        ):
            raise ExecutiveControlPlaneResilienceValidationError(
                "resilience policy operations must be operation-policy tuple"
            )
        if not self.operations:
            raise ExecutiveControlPlaneResilienceValidationError(
                "resilience policy must contain at least one operation"
            )
        operation_kinds = tuple(item.operation for item in self.operations)
        if len(set(operation_kinds)) != len(operation_kinds):
            raise ExecutiveControlPlaneResilienceValidationError(
                "resilience policy must not contain duplicate operations"
            )
        object.__setattr__(
            self,
            "operations",
            tuple(sorted(self.operations, key=lambda item: item.operation.value)),
        )

    def timeout_for(
        self,
        operation: ExecutiveControlPlaneOperation,
    ) -> ExecutiveControlPlaneTimeout | None:
        if not isinstance(operation, ExecutiveControlPlaneOperation):
            raise ExecutiveControlPlaneResilienceValidationError(
                "timeout lookup requires ExecutiveControlPlaneOperation"
            )
        for policy in self.operations:
            if policy.operation is operation:
                return policy.timeout
        return None

    def logical_values(self) -> tuple[object, ...]:
        return tuple(item.logical_values() for item in self.operations)


@dataclass(frozen=True, slots=True)
class ExecutiveControlPlaneRecoveryId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveControlPlaneResilienceValidationError(
                "control-plane recovery id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveControlPlaneRecoveryPlan:
    """Contain one failure without retrying or redispatching automatically."""

    recovery_id: ExecutiveControlPlaneRecoveryId
    operation: ExecutiveControlPlaneOperation
    failure_kind: ExecutiveControlPlaneFailureKind
    requirement: ExecutiveControlPlaneRecoveryRequirement
    correlation_id: CorrelationId
    failed_at: datetime
    planned_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.recovery_id, ExecutiveControlPlaneRecoveryId):
            raise ExecutiveControlPlaneResilienceValidationError(
                "recovery plan requires ExecutiveControlPlaneRecoveryId"
            )
        if not isinstance(self.operation, ExecutiveControlPlaneOperation):
            raise ExecutiveControlPlaneResilienceValidationError(
                "recovery plan requires ExecutiveControlPlaneOperation"
            )
        if not isinstance(self.failure_kind, ExecutiveControlPlaneFailureKind):
            raise ExecutiveControlPlaneResilienceValidationError(
                "recovery plan requires ExecutiveControlPlaneFailureKind"
            )
        if not isinstance(self.requirement, ExecutiveControlPlaneRecoveryRequirement):
            raise ExecutiveControlPlaneResilienceValidationError(
                "recovery plan requires ExecutiveControlPlaneRecoveryRequirement"
            )
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveControlPlaneResilienceValidationError(
                "recovery plan requires CorrelationId"
            )
        _validate_timestamp(self.failed_at, field_name="failed_at")
        _validate_timestamp(self.planned_at, field_name="planned_at")
        if self.planned_at < self.failed_at:
            raise ExecutiveControlPlaneResilienceValidationError(
                "recovery plan cannot predate failure"
            )
        expected = _RECOVERY_BY_OPERATION[self.operation]
        if self.requirement is not expected:
            raise ExecutiveControlPlaneResilienceValidationError(
                "recovery requirement must match failed control-plane operation"
            )

    @property
    def automatic_retry_allowed(self) -> bool:
        return False

    @property
    def automatic_redispatch_allowed(self) -> bool:
        return False

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.recovery_id.logical_values(),
            self.operation.value,
            self.failure_kind.value,
            self.requirement.value,
            str(self.correlation_id.value),
            self.failed_at.isoformat(),
            self.planned_at.isoformat(),
            self.automatic_retry_allowed,
            self.automatic_redispatch_allowed,
        )


_RECOVERY_BY_OPERATION: dict[
    ExecutiveControlPlaneOperation,
    ExecutiveControlPlaneRecoveryRequirement,
] = {
    ExecutiveControlPlaneOperation.AUTHORITY_READ: (
        ExecutiveControlPlaneRecoveryRequirement.REREAD_AUTHORITY
    ),
    ExecutiveControlPlaneOperation.REPLAY_CLAIM: (
        ExecutiveControlPlaneRecoveryRequirement.VERIFY_REPLAY_CLAIM
    ),
    ExecutiveControlPlaneOperation.COMMAND_DISPATCH: (
        ExecutiveControlPlaneRecoveryRequirement.VERIFY_CONTROL_RECEIPT
    ),
    ExecutiveControlPlaneOperation.READ_DISPATCH: (
        ExecutiveControlPlaneRecoveryRequirement.ISSUE_NEW_READ_REQUEST
    ),
    ExecutiveControlPlaneOperation.GOVERNANCE_MUTATION: (
        ExecutiveControlPlaneRecoveryRequirement.REREAD_GOVERNANCE_STATE
    ),
    ExecutiveControlPlaneOperation.AUDIT_APPEND: (
        ExecutiveControlPlaneRecoveryRequirement.VERIFY_AUDIT_RECORD
    ),
    ExecutiveControlPlaneOperation.OBSERVABILITY_EMIT: (
        ExecutiveControlPlaneRecoveryRequirement.OBSERVABILITY_CAN_DEGRADE
    ),
}


def plan_executive_control_plane_recovery(
    operation: ExecutiveControlPlaneOperation,
    failure_kind: ExecutiveControlPlaneFailureKind,
    *,
    recovery_id: ExecutiveControlPlaneRecoveryId,
    correlation_id: CorrelationId,
    failed_at: datetime,
    planned_at: datetime,
) -> Result[ExecutiveControlPlaneRecoveryPlan, ExecutiveControlPlaneResilienceError]:
    if not isinstance(operation, ExecutiveControlPlaneOperation):
        return Failure(
            ExecutiveControlPlaneResilienceValidationError(
                "recovery planning requires ExecutiveControlPlaneOperation"
            )
        )
    if not isinstance(failure_kind, ExecutiveControlPlaneFailureKind):
        return Failure(
            ExecutiveControlPlaneResilienceValidationError(
                "recovery planning requires ExecutiveControlPlaneFailureKind"
            )
        )
    try:
        return Success(
            ExecutiveControlPlaneRecoveryPlan(
                recovery_id=recovery_id,
                operation=operation,
                failure_kind=failure_kind,
                requirement=_RECOVERY_BY_OPERATION[operation],
                correlation_id=correlation_id,
                failed_at=failed_at,
                planned_at=planned_at,
            )
        )
    except ExecutiveControlPlaneResilienceError as error:
        return Failure(error)
