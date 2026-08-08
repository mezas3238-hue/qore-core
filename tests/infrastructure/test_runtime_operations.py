from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.runtime_operations import (
    RuntimeOperationActor,
    RuntimeOperationalState,
    RuntimeOperationReason,
    RuntimeOperationsError,
    RuntimeOperationsSnapshot,
    RuntimeOperationsTransitionError,
    RuntimeOperationsValidationError,
    RuntimeOperationTransitionRequest,
    apply_runtime_operation_transition,
    declare_runtime_operations,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 6, 0, tzinfo=UTC)
_ACTOR = RuntimeOperationActor("operations.supervisor")


def _transition(
    snapshot: RuntimeOperationsSnapshot,
    *,
    state: RuntimeOperationalState,
    reason: RuntimeOperationReason,
    offset: int,
) -> Result[RuntimeOperationsSnapshot, RuntimeOperationsError]:
    return apply_runtime_operation_transition(
        snapshot,
        RuntimeOperationTransitionRequest(
            to_state=state,
            transitioned_at=_NOW + timedelta(seconds=offset),
            actor=_ACTOR,
            reason=reason,
        ),
    )


def test_runtime_lifecycle_reaches_ready_without_side_effects() -> None:
    declared = declare_runtime_operations(declared_at=_NOW, actor=_ACTOR)
    assert isinstance(declared, Success)

    starting = _transition(
        declared.value,
        state=RuntimeOperationalState.STARTING,
        reason=RuntimeOperationReason.START_REQUESTED,
        offset=1,
    )
    assert isinstance(starting, Success)
    ready = _transition(
        starting.value,
        state=RuntimeOperationalState.READY,
        reason=RuntimeOperationReason.READINESS_CONFIRMED,
        offset=2,
    )

    assert isinstance(ready, Success)
    assert ready.value.is_ready is True
    assert ready.value.sequence == 2


def test_ready_can_degrade_and_recover() -> None:
    declared = declare_runtime_operations(declared_at=_NOW, actor=_ACTOR)
    assert isinstance(declared, Success)
    starting = _transition(
        declared.value,
        state=RuntimeOperationalState.STARTING,
        reason=RuntimeOperationReason.START_REQUESTED,
        offset=1,
    )
    assert isinstance(starting, Success)
    ready = _transition(
        starting.value,
        state=RuntimeOperationalState.READY,
        reason=RuntimeOperationReason.READINESS_CONFIRMED,
        offset=2,
    )
    assert isinstance(ready, Success)
    degraded = _transition(
        ready.value,
        state=RuntimeOperationalState.DEGRADED,
        reason=RuntimeOperationReason.HEALTH_DEGRADED,
        offset=3,
    )
    assert isinstance(degraded, Success)
    recovered = _transition(
        degraded.value,
        state=RuntimeOperationalState.READY,
        reason=RuntimeOperationReason.HEALTH_RECOVERED,
        offset=4,
    )

    assert isinstance(recovered, Success)
    assert recovered.value.state is RuntimeOperationalState.READY


def test_invalid_direct_stopped_to_ready_transition_fails() -> None:
    declared = declare_runtime_operations(declared_at=_NOW, actor=_ACTOR)
    assert isinstance(declared, Success)

    result = _transition(
        declared.value,
        state=RuntimeOperationalState.READY,
        reason=RuntimeOperationReason.READINESS_CONFIRMED,
        offset=1,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, RuntimeOperationsTransitionError)


def test_transition_reason_must_match_target_state() -> None:
    declared = declare_runtime_operations(declared_at=_NOW, actor=_ACTOR)
    assert isinstance(declared, Success)

    result = _transition(
        declared.value,
        state=RuntimeOperationalState.STARTING,
        reason=RuntimeOperationReason.FAILURE_DETECTED,
        offset=1,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, RuntimeOperationsTransitionError)


def test_timestamp_cannot_move_backwards() -> None:
    declared = declare_runtime_operations(declared_at=_NOW, actor=_ACTOR)
    assert isinstance(declared, Success)
    result = apply_runtime_operation_transition(
        declared.value,
        RuntimeOperationTransitionRequest(
            to_state=RuntimeOperationalState.STARTING,
            transitioned_at=_NOW - timedelta(seconds=1),
            actor=_ACTOR,
            reason=RuntimeOperationReason.START_REQUESTED,
        ),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, RuntimeOperationsTransitionError)


def test_actor_and_message_reject_sensitive_or_invalid_text() -> None:
    with pytest.raises(RuntimeOperationsValidationError):
        RuntimeOperationActor("Operations Supervisor")
    with pytest.raises(RuntimeOperationsValidationError):
        RuntimeOperationTransitionRequest(
            to_state=RuntimeOperationalState.STARTING,
            transitioned_at=_NOW,
            actor=_ACTOR,
            reason=RuntimeOperationReason.START_REQUESTED,
            message="Bearer must-not-appear",
        )


def test_sequence_rejects_bool() -> None:
    declared = declare_runtime_operations(declared_at=_NOW, actor=_ACTOR)
    assert isinstance(declared, Success)
    with pytest.raises(RuntimeOperationsValidationError):
        RuntimeOperationsSnapshot(
            state=declared.value.state,
            sequence=True,
            transitioned_at=_NOW,
            actor=_ACTOR,
            reason=RuntimeOperationReason.STOP_CONFIRMED,
        )


def test_failed_runtime_can_enter_explicit_recovery_starting() -> None:
    declared = declare_runtime_operations(declared_at=_NOW, actor=_ACTOR)
    assert isinstance(declared, Success)
    starting = _transition(
        declared.value,
        state=RuntimeOperationalState.STARTING,
        reason=RuntimeOperationReason.START_REQUESTED,
        offset=1,
    )
    assert isinstance(starting, Success)
    failed = _transition(
        starting.value,
        state=RuntimeOperationalState.FAILED,
        reason=RuntimeOperationReason.FAILURE_DETECTED,
        offset=2,
    )
    assert isinstance(failed, Success)
    recovery = _transition(
        failed.value,
        state=RuntimeOperationalState.STARTING,
        reason=RuntimeOperationReason.RECOVERY_REQUESTED,
        offset=3,
    )

    assert isinstance(recovery, Success)
    assert recovery.value.state is RuntimeOperationalState.STARTING
