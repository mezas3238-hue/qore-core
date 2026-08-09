from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_execution_lease as lease
import qore.infrastructure.hosting_execution_unit as unit
import qore.infrastructure.hosting_health_heartbeat as health
import qore.infrastructure.hosting_orchestrator as orchestrator
import qore.infrastructure.hosting_runtime_registry as registry

_NOW = datetime(2026, 8, 9, 21, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"49000000-0000-0000-0000-{suffix:012d}")


def _record(
    *,
    desired: registry.HostingRuntimeDesiredState = registry.HostingRuntimeDesiredState.RUNNING,
    observed: registry.HostingRuntimeObservedState = registry.HostingRuntimeObservedState.RUNNING,
) -> registry.HostingRuntimeRecord:
    managed = unit.HostingExecutionUnit(
        unit_id=unit.HostingExecutionUnitId(_uuid(1)),
        client_id=accounts.ClientId(_uuid(2)),
        account_id=accounts.TradingAccountId(_uuid(3)),
        mode=unit.HostingMode.QORE_MANAGED,
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        software_version=unit.HostingSoftwareVersion("1.0.0"),
        deployment_ref=unit.HostingDeploymentReference(_uuid(5)),
        region_ref=unit.HostingRegionReference("us-east-execution"),
        secret_refs=(),
        state=unit.HostingExecutionUnitState.RUNNING,
        recorded_at=_NOW - timedelta(minutes=5),
    )
    return registry.HostingRuntimeRecord(
        unit=managed,
        desired_state=desired,
        observed_state=observed,
        registered_at=_NOW - timedelta(minutes=4),
        observed_at=_NOW - timedelta(seconds=5),
    )


def _health(
    *,
    containment: health.HostingNewWorkContainment = health.HostingNewWorkContainment.NONE,
    evaluated_at: datetime = _NOW,
) -> health.HostingRuntimeHealthAssessment:
    runtime_health = (
        health.HostingRuntimeHealth.HEALTHY
        if containment is health.HostingNewWorkContainment.NONE
        else health.HostingRuntimeHealth.UNREACHABLE
    )
    return health.HostingRuntimeHealthAssessment(
        account_id=accounts.TradingAccountId(_uuid(3)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        health=runtime_health,
        freshness=health.HostingHeartbeatFreshness.CURRENT,
        containment=containment,
        evaluated_at=evaluated_at,
        heartbeat_id=health.HostingHeartbeatId(_uuid(10)),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(11)),
    )


def _leases(
    *,
    active: bool,
    captured_at: datetime = _NOW,
) -> lease.HostingExecutionLeaseSnapshot:
    if not active:
        return lease.HostingExecutionLeaseSnapshot(
            leases=(),
            captured_at=captured_at,
        )
    current = lease.HostingExecutionLease(
        lease_id=lease.HostingExecutionLeaseId(_uuid(20)),
        account_id=accounts.TradingAccountId(_uuid(3)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        unit_id=unit.HostingExecutionUnitId(_uuid(1)),
        generation=lease.HostingFencingGeneration(1),
        status=lease.HostingExecutionLeaseStatus.ACTIVE,
        acquired_at=_NOW - timedelta(minutes=1),
        expires_at=_NOW + timedelta(minutes=4),
        revoked_at=None,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(21)),
    )
    return lease.HostingExecutionLeaseSnapshot(
        leases=(current,),
        captured_at=captured_at,
    )


def _evaluate(
    record: registry.HostingRuntimeRecord,
    health_assessment: health.HostingRuntimeHealthAssessment,
    lease_snapshot: lease.HostingExecutionLeaseSnapshot,
    *,
    evaluated_at: datetime = _NOW,
) -> orchestrator.HostingOrchestrationDecision:
    return orchestrator.evaluate_hosting_orchestration(
        record,
        health_assessment,
        lease_snapshot,
        decision_id=orchestrator.HostingOrchestrationDecisionId(_uuid(30)),
        evidence_ref=orchestrator.HostingOrchestrationEvidenceReference(_uuid(31)),
        evaluated_at=evaluated_at,
    )


def test_unhealthy_runtime_is_contained_not_failed_over_or_elected() -> None:
    decision = _evaluate(
        _record(),
        _health(containment=health.HostingNewWorkContainment.STOP_ASSIGNING_NEW_WORK),
        _leases(active=True),
    )

    assert decision.action is orchestrator.HostingOrchestrationAction.CONTAIN_NEW_WORK
    assert decision.reason is orchestrator.HostingOrchestrationReason.HEALTH_CONTAINMENT
    assert not hasattr(decision, "activate_backup")
    assert not hasattr(decision, "revoke_lease")
    assert not hasattr(decision, "fence")


def test_desired_stop_cannot_stop_current_writer_directly() -> None:
    decision = _evaluate(
        _record(desired=registry.HostingRuntimeDesiredState.STOPPED),
        _health(),
        _leases(active=True),
    )

    assert decision.action is orchestrator.HostingOrchestrationAction.REQUEST_DRAIN
    assert decision.reason is (
        orchestrator.HostingOrchestrationReason.CURRENT_WRITER_REQUIRES_DRAIN
    )


def test_desired_stop_can_stop_non_writer_runtime() -> None:
    decision = _evaluate(
        _record(desired=registry.HostingRuntimeDesiredState.STOPPED),
        _health(),
        _leases(active=False),
    )

    assert decision.action is orchestrator.HostingOrchestrationAction.STOP_RUNTIME
    assert decision.reason is orchestrator.HostingOrchestrationReason.DESIRED_STOP


def test_stopped_candidate_can_be_prepared_without_execution_activation() -> None:
    decision = _evaluate(
        _record(observed=registry.HostingRuntimeObservedState.STOPPED),
        _health(),
        _leases(active=False),
    )

    assert decision.action is orchestrator.HostingOrchestrationAction.PREPARE_RUNTIME
    assert decision.reason is orchestrator.HostingOrchestrationReason.RUNTIME_NOT_RUNNING
    actions = {action.value for action in orchestrator.HostingOrchestrationAction}
    assert "activate_execution" not in actions
    assert not hasattr(decision, "execution_authority")


def test_desired_drain_is_explicit_and_does_not_mutate_lease() -> None:
    leases = _leases(active=True)
    before = leases.logical_values()
    decision = _evaluate(
        _record(desired=registry.HostingRuntimeDesiredState.DRAINING),
        _health(),
        leases,
    )

    assert decision.action is orchestrator.HostingOrchestrationAction.REQUEST_DRAIN
    assert leases.logical_values() == before


def test_aligned_running_runtime_requires_no_deployment_action() -> None:
    decision = _evaluate(_record(), _health(), _leases(active=True))

    assert decision.action is orchestrator.HostingOrchestrationAction.NO_ACTION
    assert decision.reason is orchestrator.HostingOrchestrationReason.ALREADY_ALIGNED
    assert not hasattr(decision, "submit_order")
    assert not hasattr(decision, "broker")
    assert not hasattr(decision, "core_decision")


def test_orchestration_uses_canonical_account_and_runtime_types() -> None:
    decision_fields = {field.name: field.type for field in fields(orchestrator.HostingOrchestrationDecision)}

    assert decision_fields["account_id"] == "TradingAccountId"
    assert decision_fields["runtime_ref"] == "ExecutionRuntimeReference"


def test_health_must_bind_exact_runtime_and_evaluation_time() -> None:
    mismatched_health = health.HostingRuntimeHealthAssessment(
        account_id=accounts.TradingAccountId(_uuid(3)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(999)),
        health=health.HostingRuntimeHealth.HEALTHY,
        freshness=health.HostingHeartbeatFreshness.CURRENT,
        containment=health.HostingNewWorkContainment.NONE,
        evaluated_at=_NOW,
        heartbeat_id=health.HostingHeartbeatId(_uuid(12)),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(13)),
    )

    with pytest.raises(orchestrator.HostingOrchestratorValidationError):
        _evaluate(_record(), mismatched_health, _leases(active=False))

    with pytest.raises(orchestrator.HostingOrchestratorValidationError):
        _evaluate(
            _record(),
            _health(evaluated_at=_NOW - timedelta(seconds=1)),
            _leases(active=False),
        )


def test_stale_lease_snapshot_cannot_be_used_to_infer_current_writer() -> None:
    with pytest.raises(orchestrator.HostingOrchestratorValidationError):
        _evaluate(
            _record(desired=registry.HostingRuntimeDesiredState.STOPPED),
            _health(),
            _leases(active=True, captured_at=_NOW - timedelta(seconds=1)),
        )


def test_future_runtime_observation_is_rejected() -> None:
    record = _record()
    future_record = registry.HostingRuntimeRecord(
        unit=record.unit,
        desired_state=record.desired_state,
        observed_state=record.observed_state,
        registered_at=record.registered_at,
        observed_at=_NOW + timedelta(seconds=1),
    )

    with pytest.raises(orchestrator.HostingOrchestratorValidationError):
        _evaluate(future_record, _health(), _leases(active=False))


def test_orchestrator_exposes_no_authority_transfer_or_provider_io() -> None:
    prohibited = {
        "acquire_lease",
        "activate_backup",
        "broker",
        "connect_provider",
        "fence",
        "redispatch",
        "retry",
        "revoke_lease",
        "submit_order",
    }
    decision_fields = {field.name for field in fields(orchestrator.HostingOrchestrationDecision)}

    assert decision_fields.isdisjoint(prohibited)
    assert prohibited.isdisjoint(set(dir(orchestrator.HostingOrchestrationDecision)))
