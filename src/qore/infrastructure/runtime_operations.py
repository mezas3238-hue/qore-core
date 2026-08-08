from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_TEXT_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret=",
    "password=",
    "secret=",
    "token=",
)


class RuntimeOperationsError(ExternalPortError):
    """Base error for operational runtime lifecycle contracts."""

    __slots__ = ()


class RuntimeOperationsValidationError(RuntimeOperationsError):
    """Violation of a runtime operations invariant."""

    __slots__ = ()


class RuntimeOperationsTransitionError(RuntimeOperationsError):
    """Typed error for an invalid lifecycle transition."""

    __slots__ = ()


class RuntimeOperationalState(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    FAILED = "failed"


class RuntimeOperationReason(StrEnum):
    START_REQUESTED = "start_requested"
    READINESS_CONFIRMED = "readiness_confirmed"
    HEALTH_DEGRADED = "health_degraded"
    HEALTH_RECOVERED = "health_recovered"
    STOP_REQUESTED = "stop_requested"
    STOP_CONFIRMED = "stop_confirmed"
    FAILURE_DETECTED = "failure_detected"
    RECOVERY_REQUESTED = "recovery_requested"


@dataclass(frozen=True, slots=True)
class RuntimeOperationActor:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]*", self.value
        ) is None:
            raise RuntimeOperationsValidationError(
                "runtime operation actor must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise RuntimeOperationsValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise RuntimeOperationsValidationError(f"{field_name} must be timezone-aware")


def _validate_message(value: str | None) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise RuntimeOperationsValidationError(
            "runtime operation message must be non-empty or None"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_TEXT_PARTS):
        raise RuntimeOperationsValidationError(
            "runtime operation message must not contain sensitive material"
        )


@dataclass(frozen=True, slots=True)
class RuntimeOperationsSnapshot:
    state: RuntimeOperationalState
    sequence: int
    transitioned_at: datetime
    actor: RuntimeOperationActor
    reason: RuntimeOperationReason
    message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, RuntimeOperationalState):
            raise RuntimeOperationsValidationError(
                "runtime operational state must be RuntimeOperationalState"
            )
        if type(self.sequence) is not int or self.sequence < 0:
            raise RuntimeOperationsValidationError(
                "runtime operation sequence must be a non-negative int"
            )
        _validate_timestamp(self.transitioned_at, field_name="transitioned_at")
        if not isinstance(self.actor, RuntimeOperationActor):
            raise RuntimeOperationsValidationError(
                "runtime operation actor must be RuntimeOperationActor"
            )
        if not isinstance(self.reason, RuntimeOperationReason):
            raise RuntimeOperationsValidationError(
                "runtime operation reason must be RuntimeOperationReason"
            )
        _validate_message(self.message)

    @property
    def is_ready(self) -> bool:
        return self.state is RuntimeOperationalState.READY

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.state.value,
            self.sequence,
            self.transitioned_at.isoformat(),
            self.actor.logical_values(),
            self.reason.value,
            self.message,
        )


@dataclass(frozen=True, slots=True)
class RuntimeOperationTransitionRequest:
    to_state: RuntimeOperationalState
    transitioned_at: datetime
    actor: RuntimeOperationActor
    reason: RuntimeOperationReason
    message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.to_state, RuntimeOperationalState):
            raise RuntimeOperationsValidationError(
                "runtime transition to_state must be RuntimeOperationalState"
            )
        _validate_timestamp(self.transitioned_at, field_name="transitioned_at")
        if not isinstance(self.actor, RuntimeOperationActor):
            raise RuntimeOperationsValidationError(
                "runtime transition actor must be RuntimeOperationActor"
            )
        if not isinstance(self.reason, RuntimeOperationReason):
            raise RuntimeOperationsValidationError(
                "runtime transition reason must be RuntimeOperationReason"
            )
        _validate_message(self.message)


_ALLOWED_TRANSITIONS: dict[
    RuntimeOperationalState,
    frozenset[RuntimeOperationalState],
] = {
    RuntimeOperationalState.STOPPED: frozenset({RuntimeOperationalState.STARTING}),
    RuntimeOperationalState.STARTING: frozenset(
        {
            RuntimeOperationalState.READY,
            RuntimeOperationalState.DEGRADED,
            RuntimeOperationalState.STOPPING,
            RuntimeOperationalState.FAILED,
        }
    ),
    RuntimeOperationalState.READY: frozenset(
        {
            RuntimeOperationalState.DEGRADED,
            RuntimeOperationalState.STOPPING,
            RuntimeOperationalState.FAILED,
        }
    ),
    RuntimeOperationalState.DEGRADED: frozenset(
        {
            RuntimeOperationalState.READY,
            RuntimeOperationalState.STOPPING,
            RuntimeOperationalState.FAILED,
        }
    ),
    RuntimeOperationalState.STOPPING: frozenset(
        {RuntimeOperationalState.STOPPED, RuntimeOperationalState.FAILED}
    ),
    RuntimeOperationalState.FAILED: frozenset(
        {RuntimeOperationalState.STARTING, RuntimeOperationalState.STOPPING}
    ),
}

_REASON_TRANSITIONS: dict[RuntimeOperationReason, RuntimeOperationalState] = {
    RuntimeOperationReason.START_REQUESTED: RuntimeOperationalState.STARTING,
    RuntimeOperationReason.READINESS_CONFIRMED: RuntimeOperationalState.READY,
    RuntimeOperationReason.HEALTH_DEGRADED: RuntimeOperationalState.DEGRADED,
    RuntimeOperationReason.HEALTH_RECOVERED: RuntimeOperationalState.READY,
    RuntimeOperationReason.STOP_REQUESTED: RuntimeOperationalState.STOPPING,
    RuntimeOperationReason.STOP_CONFIRMED: RuntimeOperationalState.STOPPED,
    RuntimeOperationReason.FAILURE_DETECTED: RuntimeOperationalState.FAILED,
    RuntimeOperationReason.RECOVERY_REQUESTED: RuntimeOperationalState.STARTING,
}


def declare_runtime_operations(
    *,
    declared_at: datetime,
    actor: RuntimeOperationActor,
) -> Result[RuntimeOperationsSnapshot, RuntimeOperationsError]:
    """Declare an initially stopped operational runtime without side effects."""
    try:
        return Success(
            RuntimeOperationsSnapshot(
                state=RuntimeOperationalState.STOPPED,
                sequence=0,
                transitioned_at=declared_at,
                actor=actor,
                reason=RuntimeOperationReason.STOP_CONFIRMED,
                message="runtime declared stopped",
            )
        )
    except RuntimeOperationsError as error:
        return Failure(error)


def apply_runtime_operation_transition(
    snapshot: RuntimeOperationsSnapshot,
    request: RuntimeOperationTransitionRequest,
) -> Result[RuntimeOperationsSnapshot, RuntimeOperationsError]:
    """Apply one pure validated lifecycle transition."""
    if not isinstance(snapshot, RuntimeOperationsSnapshot):
        return Failure(
            RuntimeOperationsValidationError(
                "runtime transition snapshot must be RuntimeOperationsSnapshot"
            )
        )
    if not isinstance(request, RuntimeOperationTransitionRequest):
        return Failure(
            RuntimeOperationsValidationError(
                "runtime transition request must be RuntimeOperationTransitionRequest"
            )
        )
    if request.transitioned_at < snapshot.transitioned_at:
        return Failure(
            RuntimeOperationsTransitionError(
                "runtime transition timestamp must not move backwards"
            )
        )
    if request.to_state not in _ALLOWED_TRANSITIONS[snapshot.state]:
        return Failure(
            RuntimeOperationsTransitionError(
                f"invalid runtime transition: {snapshot.state.value} -> "
                f"{request.to_state.value}"
            )
        )
    if _REASON_TRANSITIONS[request.reason] is not request.to_state:
        return Failure(
            RuntimeOperationsTransitionError(
                "runtime transition reason does not match target state"
            )
        )
    return Success(
        RuntimeOperationsSnapshot(
            state=request.to_state,
            sequence=snapshot.sequence + 1,
            transitioned_at=request.transitioned_at,
            actor=request.actor,
            reason=request.reason,
            message=request.message,
        )
    )
