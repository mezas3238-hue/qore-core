from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_trial_licensing as licensing
import qore.infrastructure.execution_reconciliation as execution
import qore.infrastructure.hosting_commercial_suspension as commercial
import qore.infrastructure.hosting_execution_lease as lease
import qore.infrastructure.hosting_execution_unit as unit
import qore.infrastructure.hosting_failover_reconciliation as failover
import qore.infrastructure.hosting_health_heartbeat as health
import qore.infrastructure.hosting_orchestrator as orchestrator
import qore.infrastructure.hosting_runtime_registry as registry
import qore.infrastructure.hosting_telemetry as telemetry
import qore.kernel.result as result

_T0 = datetime(2026, 8, 10, 1, 0, tzinfo=UTC)
_T1 = _T0 + timedelta(minutes=1)
_T2 = _T0 + timedelta(minutes=2)
_T3 = _T0 + timedelta(minutes=3)
_ACCOUNT = accounts.TradingAccountId(UUID("53000000-0000-0000-0000-000000000003"))
_RUNTIME_A = accounts.ExecutionRuntimeReference(
    UUID("53000000-0000-0000-0000-000000000004")
)
_RUNTIME_B = accounts.ExecutionRuntimeReference(
    UUID("53000000-0000-0000-0000-000000000005")
)
_ENTITLEMENT = accounts.ProductEntitlementReference(
    UUID("53000000-0000-0000-0000-000000000006")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"53000000-0000-0000-0000-{suffix:012d}")


def _unit(
    runtime_ref: accounts.ExecutionRuntimeReference,
    *,
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
        recorded_at=_T0 - timedelta(minutes=10),
    )


def _record(
    runtime_ref: accounts.ExecutionRuntimeReference,
    *,
    suffix: int,
    desired: registry.HostingRuntimeDesiredState = (
        registry.HostingRuntimeDesiredState.RUNNING
    ),
    observed: registry.HostingRuntimeObservedState = (
        registry.HostingRuntimeObservedState.RUNNING
    ),
) -> registry.HostingRuntimeRecord:
    return registry.HostingRuntimeRecord(
        unit=_unit(runtime_ref, suffix=suffix),
        desired_state=desired,
        observed_state=observed,
        registered_at=_T0 - timedelta(minutes=9),
        observed_at=_T0 - timedelta(seconds=5),
    )


def _registry() -> registry.HostingRuntimeRegistrySnapshot:
    return registry.HostingRuntimeRegistrySnapshot(
        generation=registry.HostingRuntimeRegistryGeneration(8),
        records=(
            _record(_RUNTIME_A, suffix=10),
            _record(_RUNTIME_B, suffix=11),
        ),
        captured_at=_T3,
    )


def _heartbeat(
    runtime_ref: accounts.ExecutionRuntimeReference,
    *,
    suffix: int,
    runtime_health: health.HostingRuntimeHealth,
    evaluated_at: datetime,
) -> health.HostingHeartbeatSample:
    return health.HostingHeartbeatSample(
        heartbeat_id=health.HostingHeartbeatId(_uuid(suffix)),
        account_id=_ACCOUNT,
        runtime_ref=runtime_ref,
        health=runtime_health,
        observed_at=evaluated_at - timedelta(seconds=1),
        fresh_until=evaluated_at + timedelta(seconds=30),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(suffix + 100)),
    )


def _health(
    runtime_ref: accounts.ExecutionRuntimeReference,
    *,
    suffix: int,
    runtime_health: health.HostingRuntimeHealth,
    evaluated_at: datetime,
) -> health.HostingRuntimeHealthAssessment:
    return health.assess_hosting_runtime_health(
        _registry(),
        account_id=_ACCOUNT,
        runtime_ref=runtime_ref,
        heartbeat=_heartbeat(
            runtime_ref,
            suffix=suffix,
            runtime_health=runtime_health,
            evaluated_at=evaluated_at,
        ),
        evaluated_at=evaluated_at,
    )


def _execution_reconciliation(
    status: execution.ExecutionReconciliationStatus,
    *,
    evaluated_at: datetime,
) -> execution.ExecutionReconciliationSnapshot:
    return execution.ExecutionReconciliationSnapshot(
        status=status,
        reconciled_at=evaluated_at - timedelta(seconds=1),
        issues=(
            ()
            if status is execution.ExecutionReconciliationStatus.MATCHED
            else ("ambiguous_execution_state",)
        ),
    )


def _account_reconciliation(
    status: failover.HostingExternalAccountReconciliationStatus,
    *,
    evaluated_at: datetime,
    suffix: int,
) -> failover.HostingExternalAccountReconciliation:
    return failover.HostingExternalAccountReconciliation(
        account_id=_ACCOUNT,
        status=status,
        reconciled_at=evaluated_at - timedelta(seconds=2),
        evidence_ref=(
            failover.HostingFailoverEvidenceReference(_uuid(suffix))
            if status is failover.HostingExternalAccountReconciliationStatus.MATCHED
            else None
        ),
    )


def _assess_failover(
    leases: lease.HostingExecutionLeaseSnapshot,
    previous_health: health.HostingRuntimeHealthAssessment,
    candidate_health: health.HostingRuntimeHealthAssessment,
    *,
    account_status: failover.HostingExternalAccountReconciliationStatus,
    execution_status: execution.ExecutionReconciliationStatus,
    assessment_suffix: int,
) -> failover.HostingFailoverAssessment:
    return failover.evaluate_hosting_failover_readiness(
        _registry(),
        leases,
        previous_health,
        candidate_health,
        _account_reconciliation(
            account_status,
            evaluated_at=_T1,
            suffix=assessment_suffix + 100,
        ),
        (
            _execution_reconciliation(
                execution_status,
                evaluated_at=_T1,
            ),
        ),
        account_id=_ACCOUNT,
        previous_runtime_ref=_RUNTIME_A,
        candidate_runtime_ref=_RUNTIME_B,
        assessment_id=failover.HostingFailoverAssessmentId(
            _uuid(assessment_suffix)
        ),
        evidence_ref=failover.HostingFailoverEvidenceReference(
            _uuid(assessment_suffix + 1)
        ),
        evaluated_at=_T1,
    )


def _telemetry(
    record: registry.HostingRuntimeRecord,
    health_assessment: health.HostingRuntimeHealthAssessment,
    leases: lease.HostingExecutionLeaseSnapshot,
    *,
    suffix: int,
    observed_at: datetime,
) -> telemetry.HostingRuntimeTelemetry:
    return telemetry.project_hosting_runtime_telemetry(
        record,
        health_assessment,
        leases,
        registry_generation=_registry().generation,
        snapshot_id=telemetry.HostingTelemetrySnapshotId(_uuid(suffix)),
        evidence_ref=telemetry.HostingTelemetryEvidenceReference(_uuid(suffix + 1)),
        observed_at=observed_at,
    )


def test_mission08_single_writer_handoff_is_fenced_reconciled_and_offline() -> None:
    runtime_registry = _registry()
    assert len(runtime_registry.candidates_for_account(_ACCOUNT)) == 2

    empty_leases = lease.HostingExecutionLeaseSnapshot(leases=(), captured_at=_T0)
    acquired_a = lease.acquire_hosting_execution_lease(
        runtime_registry,
        empty_leases,
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_A,
        lease_id=lease.HostingExecutionLeaseId(_uuid(200)),
        generation=lease.HostingFencingGeneration(7),
        acquired_at=_T0,
        expires_at=_T3 + timedelta(minutes=5),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(201)),
    )
    assert isinstance(acquired_a, result.Success)

    healthy_a_t0 = _health(
        _RUNTIME_A,
        suffix=210,
        runtime_health=health.HostingRuntimeHealth.HEALTHY,
        evaluated_at=_T0,
    )
    healthy_b_t0 = _health(
        _RUNTIME_B,
        suffix=220,
        runtime_health=health.HostingRuntimeHealth.HEALTHY,
        evaluated_at=_T0,
    )
    telemetry_a_t0 = _telemetry(
        runtime_registry.records[0],
        healthy_a_t0,
        acquired_a.value,
        suffix=230,
        observed_at=_T0,
    )
    telemetry_b_t0 = _telemetry(
        runtime_registry.records[1],
        healthy_b_t0,
        acquired_a.value,
        suffix=240,
        observed_at=_T0,
    )
    assert telemetry_a_t0.writer_observation is (
        telemetry.HostingWriterObservation.CURRENT_WRITER
    )
    assert telemetry_a_t0.fencing_generation == lease.HostingFencingGeneration(7)
    assert telemetry_b_t0.writer_observation is (
        telemetry.HostingWriterObservation.OTHER_RUNTIME_IS_WRITER
    )
    assert telemetry_b_t0.lease_id is None
    assert telemetry_b_t0.fencing_generation is None

    leases_at_t1 = lease.HostingExecutionLeaseSnapshot(
        leases=acquired_a.value.leases,
        captured_at=_T1,
    )
    unhealthy_a_t1 = _health(
        _RUNTIME_A,
        suffix=250,
        runtime_health=health.HostingRuntimeHealth.UNREACHABLE,
        evaluated_at=_T1,
    )
    healthy_b_t1 = _health(
        _RUNTIME_B,
        suffix=260,
        runtime_health=health.HostingRuntimeHealth.HEALTHY,
        evaluated_at=_T1,
    )
    containment = orchestrator.evaluate_hosting_orchestration(
        runtime_registry.records[0],
        unhealthy_a_t1,
        leases_at_t1,
        decision_id=orchestrator.HostingOrchestrationDecisionId(_uuid(270)),
        evidence_ref=orchestrator.HostingOrchestrationEvidenceReference(_uuid(271)),
        evaluated_at=_T1,
    )
    assert containment.action is orchestrator.HostingOrchestrationAction.CONTAIN_NEW_WORK

    blocked_active = _assess_failover(
        leases_at_t1,
        unhealthy_a_t1,
        healthy_b_t1,
        account_status=failover.HostingExternalAccountReconciliationStatus.MATCHED,
        execution_status=execution.ExecutionReconciliationStatus.MATCHED,
        assessment_suffix=280,
    )
    assert blocked_active.readiness is failover.HostingFailoverReadiness.BLOCKED
    assert blocked_active.reason is (
        failover.HostingFailoverReason.PREVIOUS_AUTHORITY_STILL_ACTIVE
    )
    assert blocked_active.next_generation is None

    revoked_a = lease.revoke_hosting_execution_lease(
        leases_at_t1,
        lease.HostingExecutionLeaseId(_uuid(200)),
        revoked_at=_T1,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(290)),
    )
    assert isinstance(revoked_a, result.Success)
    no_authority = revoked_a.value.current_authority(_ACCOUNT, evaluated_at=_T1)
    assert isinstance(no_authority, result.Failure)

    blocked_account = _assess_failover(
        revoked_a.value,
        unhealthy_a_t1,
        healthy_b_t1,
        account_status=failover.HostingExternalAccountReconciliationStatus.AMBIGUOUS,
        execution_status=execution.ExecutionReconciliationStatus.MATCHED,
        assessment_suffix=300,
    )
    assert blocked_account.readiness is failover.HostingFailoverReadiness.BLOCKED
    assert blocked_account.reason is (
        failover.HostingFailoverReason.EXTERNAL_ACCOUNT_AMBIGUOUS
    )

    blocked_execution = _assess_failover(
        revoked_a.value,
        unhealthy_a_t1,
        healthy_b_t1,
        account_status=failover.HostingExternalAccountReconciliationStatus.MATCHED,
        execution_status=execution.ExecutionReconciliationStatus.DIVERGED,
        assessment_suffix=310,
    )
    assert blocked_execution.readiness is failover.HostingFailoverReadiness.BLOCKED
    assert blocked_execution.reason is (
        failover.HostingFailoverReason.EXECUTION_RECONCILIATION_AMBIGUOUS
    )

    ready = _assess_failover(
        revoked_a.value,
        unhealthy_a_t1,
        healthy_b_t1,
        account_status=failover.HostingExternalAccountReconciliationStatus.MATCHED,
        execution_status=execution.ExecutionReconciliationStatus.MATCHED,
        assessment_suffix=320,
    )
    assert ready.readiness is (
        failover.HostingFailoverReadiness.READY_FOR_LEASE_ACQUISITION
    )
    assert ready.next_generation == lease.HostingFencingGeneration(8)
    before_acquisition = revoked_a.value.current_authority(
        _ACCOUNT,
        evaluated_at=_T1,
    )
    assert isinstance(before_acquisition, result.Failure)

    assert ready.next_generation is not None
    acquired_b = lease.acquire_hosting_execution_lease(
        runtime_registry,
        revoked_a.value,
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_B,
        lease_id=lease.HostingExecutionLeaseId(_uuid(330)),
        generation=ready.next_generation,
        acquired_at=_T2,
        expires_at=_T3 + timedelta(minutes=5),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(331)),
    )
    assert isinstance(acquired_b, result.Success)
    current = acquired_b.value.current_authority(_ACCOUNT, evaluated_at=_T2)
    assert isinstance(current, result.Success)
    assert current.value.runtime_ref == _RUNTIME_B
    assert current.value.generation == lease.HostingFencingGeneration(8)
    authoritative = tuple(
        item
        for item in acquired_b.value.leases_for_account(_ACCOUNT)
        if item.is_authoritative_at(_T2)
    )
    assert len(authoritative) == 1
    assert authoritative[0].runtime_ref == _RUNTIME_B

    unhealthy_a_t2 = _health(
        _RUNTIME_A,
        suffix=340,
        runtime_health=health.HostingRuntimeHealth.UNREACHABLE,
        evaluated_at=_T2,
    )
    healthy_b_t2 = _health(
        _RUNTIME_B,
        suffix=350,
        runtime_health=health.HostingRuntimeHealth.HEALTHY,
        evaluated_at=_T2,
    )
    telemetry_a_t2 = _telemetry(
        runtime_registry.records[0],
        unhealthy_a_t2,
        acquired_b.value,
        suffix=360,
        observed_at=_T2,
    )
    telemetry_b_t2 = _telemetry(
        runtime_registry.records[1],
        healthy_b_t2,
        acquired_b.value,
        suffix=370,
        observed_at=_T2,
    )
    assert telemetry_a_t2.writer_observation is (
        telemetry.HostingWriterObservation.OTHER_RUNTIME_IS_WRITER
    )
    assert telemetry_a_t2.lease_id is None
    assert telemetry_a_t2.fencing_generation is None
    assert telemetry_b_t2.writer_observation is (
        telemetry.HostingWriterObservation.CURRENT_WRITER
    )
    assert telemetry_b_t2.lease_id == lease.HostingExecutionLeaseId(_uuid(330))
    assert telemetry_b_t2.fencing_generation == lease.HostingFencingGeneration(8)


def test_mission08_commercial_failure_preserves_lifecycle_and_stop_is_explicit() -> None:
    pending = commercial.evaluate_hosting_commercial_suspension(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_B,
        entitlement_ref=_ENTITLEMENT,
        payment_standing=licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=1,
        evaluated_at=_T3,
        evidence_ref=commercial.HostingCommercialEvidenceReference(_uuid(400)),
    )
    assert pending.state is commercial.HostingCommercialState.SUSPEND_PENDING_FLAT
    assert pending.allows_new_trades is False
    assert pending.preserve_authorized_position_lifecycle is True
    assert pending.disposition is (
        commercial.HostingRuntimeCommercialDisposition.PRESERVE_POSITION_LIFECYCLE
    )
    assert not hasattr(pending, "close_position")
    assert not hasattr(pending, "stop_runtime")

    flat = commercial.evaluate_hosting_commercial_suspension(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_B,
        entitlement_ref=_ENTITLEMENT,
        payment_standing=licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=0,
        evaluated_at=_T3,
        evidence_ref=commercial.HostingCommercialEvidenceReference(_uuid(401)),
    )
    assert flat.state is commercial.HostingCommercialState.SUSPENDED
    assert flat.allows_new_trades is False
    assert flat.disposition is (
        commercial.HostingRuntimeCommercialDisposition.MAY_STOP_WHEN_FLAT
    )
    assert not hasattr(flat, "stop_runtime")

    runtime_registry = _registry()
    previous = lease.HostingExecutionLease(
        lease_id=lease.HostingExecutionLeaseId(_uuid(410)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_A,
        unit_id=unit.HostingExecutionUnitId(_uuid(10)),
        generation=lease.HostingFencingGeneration(7),
        status=lease.HostingExecutionLeaseStatus.REVOKED,
        acquired_at=_T0,
        expires_at=_T3 + timedelta(minutes=5),
        revoked_at=_T1,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(411)),
    )
    current = lease.HostingExecutionLease(
        lease_id=lease.HostingExecutionLeaseId(_uuid(412)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_B,
        unit_id=unit.HostingExecutionUnitId(_uuid(11)),
        generation=lease.HostingFencingGeneration(8),
        status=lease.HostingExecutionLeaseStatus.ACTIVE,
        acquired_at=_T2,
        expires_at=_T3 + timedelta(minutes=5),
        revoked_at=None,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(413)),
    )
    leases_at_t3 = lease.HostingExecutionLeaseSnapshot(
        leases=(previous, current),
        captured_at=_T3,
    )
    stop_record = registry.HostingRuntimeRecord(
        unit=runtime_registry.records[0].unit,
        desired_state=registry.HostingRuntimeDesiredState.STOPPED,
        observed_state=registry.HostingRuntimeObservedState.RUNNING,
        registered_at=runtime_registry.records[0].registered_at,
        observed_at=runtime_registry.records[0].observed_at,
    )
    recovered_a = _health(
        _RUNTIME_A,
        suffix=420,
        runtime_health=health.HostingRuntimeHealth.HEALTHY,
        evaluated_at=_T3,
    )
    stop = orchestrator.evaluate_hosting_orchestration(
        stop_record,
        recovered_a,
        leases_at_t3,
        decision_id=orchestrator.HostingOrchestrationDecisionId(_uuid(430)),
        evidence_ref=orchestrator.HostingOrchestrationEvidenceReference(_uuid(431)),
        evaluated_at=_T3,
    )
    assert stop.action is orchestrator.HostingOrchestrationAction.STOP_RUNTIME
    assert stop.reason is orchestrator.HostingOrchestrationReason.DESIRED_STOP
    assert not hasattr(stop, "provider_mutation")


def test_mission08_hosting_surfaces_have_no_trading_retry_or_secret_value_authority() -> None:
    prohibited = {
        "buy",
        "close_position",
        "core_decision",
        "liquidate",
        "provider_sdk",
        "redispatch",
        "retry",
        "retry_order",
        "sell",
        "set_risk",
        "submit_order",
    }
    surfaces = (
        unit.HostingExecutionUnit,
        registry.HostingRuntimeRegistrySnapshot,
        lease.HostingExecutionLeaseSnapshot,
        health.HostingRuntimeHealthAssessment,
        orchestrator.HostingOrchestrationDecision,
        failover.HostingFailoverAssessment,
        telemetry.HostingRuntimeTelemetry,
        commercial.HostingCommercialSuspensionSnapshot,
    )
    for surface in surfaces:
        assert prohibited.isdisjoint(set(dir(surface)))

    actions = {action.value for action in orchestrator.HostingOrchestrationAction}
    assert actions.isdisjoint({"buy", "sell", "submit_order", "redispatch"})

    execution_unit_fields = {field.name for field in fields(unit.HostingExecutionUnit)}
    assert "secret_refs" in execution_unit_fields
    assert execution_unit_fields.isdisjoint(
        {"secret", "secret_value", "password", "token", "authorization_header"}
    )
