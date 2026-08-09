from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.execution_reconciliation as execution
import qore.infrastructure.hosting_execution_lease as lease
import qore.infrastructure.hosting_execution_unit as unit
import qore.infrastructure.hosting_failover_reconciliation as failover
import qore.infrastructure.hosting_health_heartbeat as health
import qore.infrastructure.hosting_runtime_registry as registry
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 22, 0, tzinfo=UTC)
_ACCOUNT = accounts.TradingAccountId(UUID("50000000-0000-0000-0000-000000000003"))
_PREVIOUS = accounts.ExecutionRuntimeReference(
    UUID("50000000-0000-0000-0000-000000000004")
)
_CANDIDATE = accounts.ExecutionRuntimeReference(
    UUID("50000000-0000-0000-0000-000000000005")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"50000000-0000-0000-0000-{suffix:012d}")


def _unit(
    runtime_ref: accounts.ExecutionRuntimeReference,
    suffix: int,
) -> unit.HostingExecutionUnit:
    return unit.HostingExecutionUnit(
        unit_id=unit.HostingExecutionUnitId(_uuid(suffix)),
        client_id=accounts.ClientId(_uuid(2)),
        account_id=_ACCOUNT,
        mode=unit.HostingMode.QORE_MANAGED,
        runtime_ref=runtime_ref,
        software_version=unit.HostingSoftwareVersion("1.0.0"),
        deployment_ref=unit.HostingDeploymentReference(_uuid(suffix + 100)),
        region_ref=unit.HostingRegionReference("us-east-execution"),
        secret_refs=(),
        state=unit.HostingExecutionUnitState.RUNNING,
        recorded_at=_NOW - timedelta(minutes=10),
    )


def _registry() -> registry.HostingRuntimeRegistrySnapshot:
    previous = registry.HostingRuntimeRecord(
        unit=_unit(_PREVIOUS, 10),
        desired_state=registry.HostingRuntimeDesiredState.DRAINING,
        observed_state=registry.HostingRuntimeObservedState.UNREACHABLE,
        registered_at=_NOW - timedelta(minutes=9),
        observed_at=_NOW - timedelta(seconds=10),
    )
    candidate = registry.HostingRuntimeRecord(
        unit=_unit(_CANDIDATE, 11),
        desired_state=registry.HostingRuntimeDesiredState.RUNNING,
        observed_state=registry.HostingRuntimeObservedState.RUNNING,
        registered_at=_NOW - timedelta(minutes=8),
        observed_at=_NOW - timedelta(seconds=5),
    )
    return registry.HostingRuntimeRegistrySnapshot(
        generation=registry.HostingRuntimeRegistryGeneration(1),
        records=(previous, candidate),
        captured_at=_NOW,
    )


def _previous_health() -> health.HostingRuntimeHealthAssessment:
    return health.HostingRuntimeHealthAssessment(
        account_id=_ACCOUNT,
        runtime_ref=_PREVIOUS,
        health=health.HostingRuntimeHealth.UNREACHABLE,
        freshness=health.HostingHeartbeatFreshness.CURRENT,
        containment=health.HostingNewWorkContainment.STOP_ASSIGNING_NEW_WORK,
        evaluated_at=_NOW,
        heartbeat_id=health.HostingHeartbeatId(_uuid(20)),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(21)),
    )


def _candidate_health(
    runtime_health: health.HostingRuntimeHealth = health.HostingRuntimeHealth.HEALTHY,
) -> health.HostingRuntimeHealthAssessment:
    containment = (
        health.HostingNewWorkContainment.NONE
        if runtime_health is health.HostingRuntimeHealth.HEALTHY
        else health.HostingNewWorkContainment.STOP_ASSIGNING_NEW_WORK
    )
    return health.HostingRuntimeHealthAssessment(
        account_id=_ACCOUNT,
        runtime_ref=_CANDIDATE,
        health=runtime_health,
        freshness=health.HostingHeartbeatFreshness.CURRENT,
        containment=containment,
        evaluated_at=_NOW,
        heartbeat_id=health.HostingHeartbeatId(_uuid(22)),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(23)),
    )


def _lease_snapshot(*, revoked: bool) -> lease.HostingExecutionLeaseSnapshot:
    old = lease.HostingExecutionLease(
        lease_id=lease.HostingExecutionLeaseId(_uuid(30)),
        account_id=_ACCOUNT,
        runtime_ref=_PREVIOUS,
        unit_id=unit.HostingExecutionUnitId(_uuid(10)),
        generation=lease.HostingFencingGeneration(1),
        status=(
            lease.HostingExecutionLeaseStatus.REVOKED
            if revoked
            else lease.HostingExecutionLeaseStatus.ACTIVE
        ),
        acquired_at=_NOW - timedelta(minutes=5),
        expires_at=_NOW + timedelta(minutes=5),
        revoked_at=_NOW - timedelta(seconds=20) if revoked else None,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(31)),
    )
    return lease.HostingExecutionLeaseSnapshot(leases=(old,), captured_at=_NOW)


def _account_reconciliation(
    status: failover.HostingExternalAccountReconciliationStatus = (
        failover.HostingExternalAccountReconciliationStatus.MATCHED
    ),
) -> failover.HostingExternalAccountReconciliation:
    return failover.HostingExternalAccountReconciliation(
        account_id=_ACCOUNT,
        status=status,
        reconciled_at=_NOW - timedelta(seconds=2),
        evidence_ref=(
            failover.HostingFailoverEvidenceReference(_uuid(40))
            if status is failover.HostingExternalAccountReconciliationStatus.MATCHED
            else None
        ),
    )


def _execution_reconciliation(
    status: execution.ExecutionReconciliationStatus = (
        execution.ExecutionReconciliationStatus.MATCHED
    ),
) -> execution.ExecutionReconciliationSnapshot:
    issues = (
        ()
        if status is execution.ExecutionReconciliationStatus.MATCHED
        else ("ambiguous",)
    )
    return execution.ExecutionReconciliationSnapshot(
        status=status,
        reconciled_at=_NOW - timedelta(seconds=1),
        issues=issues,
    )


def _evaluate(
    *,
    leases: lease.HostingExecutionLeaseSnapshot | None = None,
    candidate_health: health.HostingRuntimeHealthAssessment | None = None,
    account_reconciliation: failover.HostingExternalAccountReconciliation | None = None,
    executions: tuple[execution.ExecutionReconciliationSnapshot, ...] | None = None,
) -> failover.HostingFailoverAssessment:
    return failover.evaluate_hosting_failover_readiness(
        _registry(),
        leases or _lease_snapshot(revoked=True),
        _previous_health(),
        candidate_health or _candidate_health(),
        account_reconciliation or _account_reconciliation(),
        executions if executions is not None else (_execution_reconciliation(),),
        account_id=_ACCOUNT,
        previous_runtime_ref=_PREVIOUS,
        candidate_runtime_ref=_CANDIDATE,
        assessment_id=failover.HostingFailoverAssessmentId(_uuid(50)),
        evidence_ref=failover.HostingFailoverEvidenceReference(_uuid(51)),
        evaluated_at=_NOW,
    )


def test_reconciled_revoked_writer_is_ready_for_next_fenced_lease() -> None:
    assessed = _evaluate()

    assert assessed.readiness is (
        failover.HostingFailoverReadiness.READY_FOR_LEASE_ACQUISITION
    )
    assert assessed.reason is failover.HostingFailoverReason.RECONCILED_AND_FENCED
    assert assessed.next_generation == lease.HostingFencingGeneration(2)
    assert not hasattr(assessed, "activate_backup")
    assert not hasattr(assessed, "submit_order")


def test_previous_authority_must_be_revoked_or_expired_before_transfer() -> None:
    assessed = _evaluate(leases=_lease_snapshot(revoked=False))

    assert assessed.readiness is failover.HostingFailoverReadiness.BLOCKED
    assert assessed.reason is (
        failover.HostingFailoverReason.PREVIOUS_AUTHORITY_STILL_ACTIVE
    )
    assert assessed.next_generation is None


def test_ambiguous_external_account_state_blocks_failover() -> None:
    assessed = _evaluate(
        account_reconciliation=_account_reconciliation(
            failover.HostingExternalAccountReconciliationStatus.AMBIGUOUS
        )
    )

    assert assessed.readiness is failover.HostingFailoverReadiness.BLOCKED
    assert assessed.reason is failover.HostingFailoverReason.EXTERNAL_ACCOUNT_AMBIGUOUS


def test_diverged_execution_reconciliation_blocks_failover() -> None:
    assessed = _evaluate(
        executions=(
            _execution_reconciliation(execution.ExecutionReconciliationStatus.DIVERGED),
        )
    )

    assert assessed.readiness is failover.HostingFailoverReadiness.BLOCKED
    assert assessed.reason is (
        failover.HostingFailoverReason.EXECUTION_RECONCILIATION_AMBIGUOUS
    )


def test_candidate_must_be_current_and_healthy() -> None:
    assessed = _evaluate(
        candidate_health=_candidate_health(health.HostingRuntimeHealth.DEGRADED)
    )

    assert assessed.readiness is failover.HostingFailoverReadiness.BLOCKED
    assert assessed.reason is failover.HostingFailoverReason.CANDIDATE_NOT_HEALTHY


def test_ready_assessment_can_feed_existing_atomic_lease_acquisition() -> None:
    assessed = _evaluate()
    snapshot = _lease_snapshot(revoked=True)
    assert assessed.next_generation is not None

    acquired = lease.acquire_hosting_execution_lease(
        _registry(),
        snapshot,
        account_id=_ACCOUNT,
        runtime_ref=_CANDIDATE,
        lease_id=lease.HostingExecutionLeaseId(_uuid(60)),
        generation=assessed.next_generation,
        acquired_at=_NOW,
        expires_at=_NOW + timedelta(minutes=5),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(61)),
    )

    assert isinstance(acquired, result.Success)
    authority = acquired.value.current_authority(_ACCOUNT, evaluated_at=_NOW)
    assert isinstance(authority, result.Success)
    assert authority.value.runtime_ref == _CANDIDATE
    assert authority.value.generation == lease.HostingFencingGeneration(2)


def test_failover_contract_has_no_retry_redispatch_or_provider_surface() -> None:
    assessed = _evaluate()

    for name in (
        "activate_backup",
        "broker",
        "connect_provider",
        "redispatch",
        "retry",
        "submit_order",
    ):
        assert not hasattr(assessed, name)
