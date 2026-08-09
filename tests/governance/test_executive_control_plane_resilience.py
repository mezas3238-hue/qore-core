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
    ExecutiveControlPlaneRecoveryRequirement,
    ExecutiveControlPlaneResiliencePolicy,
    ExecutiveControlPlaneResilienceValidationError,
    ExecutiveControlPlaneTimeout,
    plan_executive_control_plane_recovery,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("51000000-0000-0000-0000-000000000001"))


def test_timeout_is_strict_positive_integer_and_never_executes_time() -> None:
    timeout = ExecutiveControlPlaneTimeout(1500)

    assert timeout.logical_values() == (1500,)
    for invalid in (0, -1, True):
        with pytest.raises(ExecutiveControlPlaneResilienceValidationError):
            ExecutiveControlPlaneTimeout(cast(int, invalid))


def test_policy_pack_is_deterministic_and_has_no_automatic_retry() -> None:
    command = ExecutiveControlPlaneOperationPolicy(
        ExecutiveControlPlaneOperation.COMMAND_DISPATCH,
        ExecutiveControlPlaneTimeout(1000),
    )
    authority = ExecutiveControlPlaneOperationPolicy(
        ExecutiveControlPlaneOperation.AUTHORITY_READ,
        ExecutiveControlPlaneTimeout(500),
    )
    policy = ExecutiveControlPlaneResiliencePolicy((command, authority))

    assert policy.operations[0].operation is ExecutiveControlPlaneOperation.AUTHORITY_READ
    assert policy.timeout_for(ExecutiveControlPlaneOperation.COMMAND_DISPATCH) == (
        ExecutiveControlPlaneTimeout(1000)
    )
    assert policy.timeout_for(ExecutiveControlPlaneOperation.AUDIT_APPEND) is None
    assert all(not item.automatic_retry_allowed for item in policy.operations)
    assert policy.logical_values() == policy.logical_values()


def test_policy_rejects_duplicate_operations() -> None:
    policy = ExecutiveControlPlaneOperationPolicy(
        ExecutiveControlPlaneOperation.REPLAY_CLAIM,
        ExecutiveControlPlaneTimeout(750),
    )

    with pytest.raises(ExecutiveControlPlaneResilienceValidationError):
        ExecutiveControlPlaneResiliencePolicy((policy, policy))


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


def test_recovery_plan_is_immutable_and_deterministic() -> None:
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
    with pytest.raises(FrozenInstanceError):
        plan.__setattr__("failure_kind", ExecutiveControlPlaneFailureKind.TIMEOUT)
