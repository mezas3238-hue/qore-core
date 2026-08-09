from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.executive_control_plane_resilience import (
    ExecutiveControlPlaneFailureKind,
    ExecutiveControlPlaneOperation,
    ExecutiveControlPlaneOperationPolicy,
    ExecutiveControlPlaneRecoveryId,
    ExecutiveControlPlaneRecoveryPlan,
    ExecutiveControlPlaneRecoveryRequirement,
    ExecutiveControlPlaneResiliencePolicy,
    ExecutiveControlPlaneResilienceValidationError,
    ExecutiveControlPlaneTimeout,
    plan_executive_control_plane_recovery,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("51000000-0000-0000-0000-000000000001"))


def _complete_policy() -> ExecutiveControlPlaneResiliencePolicy:
    return ExecutiveControlPlaneResiliencePolicy(
        tuple(
            ExecutiveControlPlaneOperationPolicy(
                operation,
                ExecutiveControlPlaneTimeout(index * 500),
            )
            for index, operation in enumerate(ExecutiveControlPlaneOperation, start=1)
        )
    )


def test_timeout_is_strict_positive_integer_and_never_executes_time() -> None:
    timeout = ExecutiveControlPlaneTimeout(1500)

    assert timeout.logical_values() == (1500,)
    for invalid in (0, -1, True):
        with pytest.raises(ExecutiveControlPlaneResilienceValidationError):
            ExecutiveControlPlaneTimeout(invalid)

    with pytest.raises(ExecutiveControlPlaneResilienceValidationError):
        ExecutiveControlPlaneTimeout(cast(int, 1.5))


def test_policy_pack_is_complete_deterministic_and_has_no_automatic_retry() -> None:
    policy = _complete_policy()

    assert tuple(item.operation.value for item in policy.operations) == tuple(
        sorted(operation.value for operation in ExecutiveControlPlaneOperation)
    )
    for operation in ExecutiveControlPlaneOperation:
        matching = next(item for item in policy.operations if item.operation is operation)
        assert policy.timeout_for(operation) == matching.timeout
        assert not matching.automatic_retry_allowed
    assert policy.logical_values() == policy.logical_values()


def test_policy_rejects_partial_and_duplicate_operations() -> None:
    authority = ExecutiveControlPlaneOperationPolicy(
        ExecutiveControlPlaneOperation.AUTHORITY_READ,
        ExecutiveControlPlaneTimeout(500),
    )
    with pytest.raises(ExecutiveControlPlaneResilienceValidationError):
        ExecutiveControlPlaneResiliencePolicy((authority,))

    complete = _complete_policy()
    with pytest.raises(ExecutiveControlPlaneResilienceValidationError):
        ExecutiveControlPlaneResiliencePolicy(complete.operations + (authority,))


def test_policy_lookup_rejects_untyped_operation() -> None:
    with pytest.raises(ExecutiveControlPlaneResilienceValidationError):
        _complete_policy().timeout_for(
            cast(ExecutiveControlPlaneOperation, "command-dispatch")
        )


@pytest.mark.parametrize(
    ("operation", "requirement"),
    [
        (
            ExecutiveControlPlaneOperation.AUTHORITY_READ,
            ExecutiveControlPlaneRecoveryRequirement.REREAD_AUTHORITY,
        ),
        (
            ExecutiveControlPlaneOperation.REPLAY_CLAIM,
            ExecutiveControlPlaneRecoveryRequirement.VERIFY_REPLAY_CLAIM,
        ),
        (
            ExecutiveControlPlaneOperation.COMMAND_DISPATCH,
            ExecutiveControlPlaneRecoveryRequirement.VERIFY_CONTROL_RECEIPT,
        ),
        (
            ExecutiveControlPlaneOperation.READ_DISPATCH,
            ExecutiveControlPlaneRecoveryRequirement.ISSUE_NEW_READ_REQUEST,
        ),
        (
            ExecutiveControlPlaneOperation.GOVERNANCE_MUTATION,
            ExecutiveControlPlaneRecoveryRequirement.REREAD_GOVERNANCE_STATE,
        ),
        (
            ExecutiveControlPlaneOperation.AUDIT_APPEND,
            ExecutiveControlPlaneRecoveryRequirement.VERIFY_AUDIT_RECORD,
        ),
        (
            ExecutiveControlPlaneOperation.OBSERVABILITY_EMIT,
            ExecutiveControlPlaneRecoveryRequirement.OBSERVABILITY_CAN_DEGRADE,
        ),
    ],
)
def test_failure_plan_requires_verification_or_reread_before_new_action(
    operation: ExecutiveControlPlaneOperation,
    requirement: ExecutiveControlPlaneRecoveryRequirement,
) -> None:
    result = plan_executive_control_plane_recovery(
        operation,
        ExecutiveControlPlaneFailureKind.AMBIGUOUS_OUTCOME,
        recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=20)),
        correlation_id=_CORRELATION,
        failed_at=_NOW,
        planned_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    plan = result.value
    assert plan.requirement is requirement
    assert not plan.automatic_retry_allowed
    assert not plan.automatic_redispatch_allowed


@pytest.mark.parametrize(
    "failure_kind",
    [
        ExecutiveControlPlaneFailureKind.TIMEOUT,
        ExecutiveControlPlaneFailureKind.UNAVAILABLE,
        ExecutiveControlPlaneFailureKind.AMBIGUOUS_OUTCOME,
    ],
)
def test_all_failure_kinds_fail_closed_to_same_operation_specific_recovery(
    failure_kind: ExecutiveControlPlaneFailureKind,
) -> None:
    result = plan_executive_control_plane_recovery(
        ExecutiveControlPlaneOperation.GOVERNANCE_MUTATION,
        failure_kind,
        recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=21)),
        correlation_id=_CORRELATION,
        failed_at=_NOW,
        planned_at=_NOW,
    )

    assert isinstance(result, Success)
    assert (
        result.value.requirement
        is ExecutiveControlPlaneRecoveryRequirement.REREAD_GOVERNANCE_STATE
    )
    assert not result.value.automatic_retry_allowed
    assert not result.value.automatic_redispatch_allowed


def test_command_ambiguity_never_becomes_automatic_redispatch() -> None:
    result = plan_executive_control_plane_recovery(
        ExecutiveControlPlaneOperation.COMMAND_DISPATCH,
        ExecutiveControlPlaneFailureKind.TIMEOUT,
        recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=22)),
        correlation_id=_CORRELATION,
        failed_at=_NOW,
        planned_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert (
        result.value.requirement
        is ExecutiveControlPlaneRecoveryRequirement.VERIFY_CONTROL_RECEIPT
    )
    assert not result.value.automatic_redispatch_allowed


def test_recovery_plan_rejects_wrong_requirement() -> None:
    with pytest.raises(ExecutiveControlPlaneResilienceValidationError):
        ExecutiveControlPlaneRecoveryPlan(
            recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=26)),
            operation=ExecutiveControlPlaneOperation.GOVERNANCE_MUTATION,
            failure_kind=ExecutiveControlPlaneFailureKind.AMBIGUOUS_OUTCOME,
            requirement=ExecutiveControlPlaneRecoveryRequirement.ISSUE_NEW_READ_REQUEST,
            correlation_id=_CORRELATION,
            failed_at=_NOW,
            planned_at=_NOW,
        )


def test_recovery_plan_requires_explicit_identity_and_aware_chronology() -> None:
    with pytest.raises(ExecutiveControlPlaneResilienceValidationError):
        ExecutiveControlPlaneRecoveryId(cast(UUID, "recovery"))

    naive = datetime(2026, 8, 9, 9, 0)
    naive_result = plan_executive_control_plane_recovery(
        ExecutiveControlPlaneOperation.AUDIT_APPEND,
        ExecutiveControlPlaneFailureKind.UNAVAILABLE,
        recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=23)),
        correlation_id=_CORRELATION,
        failed_at=naive,
        planned_at=naive,
    )
    backwards = plan_executive_control_plane_recovery(
        ExecutiveControlPlaneOperation.AUDIT_APPEND,
        ExecutiveControlPlaneFailureKind.UNAVAILABLE,
        recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=24)),
        correlation_id=_CORRELATION,
        failed_at=_NOW,
        planned_at=_NOW - timedelta(microseconds=1),
    )

    assert isinstance(naive_result, Failure)
    assert isinstance(backwards, Failure)


def test_recovery_planner_rejects_untyped_inputs() -> None:
    bad_operation = plan_executive_control_plane_recovery(
        cast(ExecutiveControlPlaneOperation, "command-dispatch"),
        ExecutiveControlPlaneFailureKind.TIMEOUT,
        recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=27)),
        correlation_id=_CORRELATION,
        failed_at=_NOW,
        planned_at=_NOW,
    )
    bad_failure = plan_executive_control_plane_recovery(
        ExecutiveControlPlaneOperation.COMMAND_DISPATCH,
        cast(ExecutiveControlPlaneFailureKind, "timeout"),
        recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=28)),
        correlation_id=_CORRELATION,
        failed_at=_NOW,
        planned_at=_NOW,
    )

    assert isinstance(bad_operation, Failure)
    assert isinstance(bad_failure, Failure)


def test_recovery_plan_is_immutable_deterministic_and_secret_free() -> None:
    result = plan_executive_control_plane_recovery(
        ExecutiveControlPlaneOperation.REPLAY_CLAIM,
        ExecutiveControlPlaneFailureKind.AMBIGUOUS_OUTCOME,
        recovery_id=ExecutiveControlPlaneRecoveryId(UUID(int=25)),
        correlation_id=_CORRELATION,
        failed_at=_NOW,
        planned_at=_NOW,
    )
    assert isinstance(result, Success)
    plan = result.value

    assert plan.logical_values() == plan.logical_values()
    rendered = repr(plan.logical_values()).lower()
    for forbidden in ("password", "bearer ", "client_secret", "token"):
        assert forbidden not in rendered

    with pytest.raises(FrozenInstanceError):
        plan.__setattr__("failure_kind", ExecutiveControlPlaneFailureKind.TIMEOUT)

    assert not hasattr(plan, "retry_count")
    assert not hasattr(plan, "sleep")
    assert not hasattr(plan, "error_text")
