from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_execution_lease as lease
import qore.infrastructure.hosting_execution_unit as unit
import qore.infrastructure.hosting_health_heartbeat as health
import qore.infrastructure.hosting_runtime_registry as registry
import qore.infrastructure.hosting_telemetry as telemetry

_NOW = datetime(2026, 8, 9, 23, 0, tzinfo=UTC)
_ACCOUNT = accounts.TradingAccountId(UUID("51000000-0000-0000-0000-000000000003"))
_RUNTIME = accounts.ExecutionRuntimeReference(
    UUID("51000000-0000-0000-0000-000000000004")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"51000000-0000-0000-0000-{suffix:012d}")


def _record() -> registry.HostingRuntimeRecord:
    managed = unit.HostingExecutionUnit(
        unit_id=unit.HostingExecutionUnitId(_uuid(1)),
        client_id=accounts.ClientId(_uuid(2)),
        account_id=_ACCOUNT,
        mode=unit.HostingMode.QORE_MANAGED,
        runtime_ref=_RUNTIME,
        software_version=unit.HostingSoftwareVersion("1.0.0"),
        deployment_ref=unit.HostingDeploymentReference(_uuid(5)),
        region_ref=unit.HostingRegionReference("us-east-execution"),
        secret_refs=(),
        state=unit.HostingExecutionUnitState.RUNNING,
        recorded_at=_NOW - timedelta(minutes=5),
    )
    return registry.HostingRuntimeRecord(
        unit=managed,
        desired_state=registry.HostingRuntimeDesiredState.RUNNING,
        observed_state=registry.HostingRuntimeObservedState.RUNNING,
        registered_at=_NOW - timedelta(minutes=4),
        observed_at=_NOW - timedelta(seconds=5),
    )


def _health() -> health.HostingRuntimeHealthAssessment:
    return health.HostingRuntimeHealthAssessment(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        health=health.HostingRuntimeHealth.HEALTHY,
        freshness=health.HostingHeartbeatFreshness.CURRENT,
        containment=health.HostingNewWorkContainment.NONE,
        evaluated_at=_NOW,
        heartbeat_id=health.HostingHeartbeatId(_uuid(10)),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(11)),
    )


def _leases(*, active: bool) -> lease.HostingExecutionLeaseSnapshot:
    if not active:
        return lease.HostingExecutionLeaseSnapshot(leases=(), captured_at=_NOW)
    current = lease.HostingExecutionLease(
        lease_id=lease.HostingExecutionLeaseId(_uuid(20)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        unit_id=unit.HostingExecutionUnitId(_uuid(1)),
        generation=lease.HostingFencingGeneration(3),
        status=lease.HostingExecutionLeaseStatus.ACTIVE,
        acquired_at=_NOW - timedelta(minutes=1),
        expires_at=_NOW + timedelta(minutes=4),
        revoked_at=None,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(21)),
    )
    return lease.HostingExecutionLeaseSnapshot(leases=(current,), captured_at=_NOW)


def _project(*, active: bool = True) -> telemetry.HostingRuntimeTelemetry:
    return telemetry.project_hosting_runtime_telemetry(
        _record(),
        _health(),
        _leases(active=active),
        registry_generation=registry.HostingRuntimeRegistryGeneration(7),
        snapshot_id=telemetry.HostingTelemetrySnapshotId(_uuid(30)),
        evidence_ref=telemetry.HostingTelemetryEvidenceReference(_uuid(31)),
        observed_at=_NOW,
    )


def test_current_writer_is_observed_with_lease_and_fence_evidence() -> None:
    snapshot = _project()

    assert snapshot.writer_observation is telemetry.HostingWriterObservation.CURRENT_WRITER
    assert snapshot.lease_id == lease.HostingExecutionLeaseId(_uuid(20))
    assert snapshot.fencing_generation == lease.HostingFencingGeneration(3)
    assert snapshot.health is health.HostingRuntimeHealth.HEALTHY


def test_no_current_writer_is_observational_and_carries_no_authority_identity() -> None:
    snapshot = _project(active=False)

    assert snapshot.writer_observation is telemetry.HostingWriterObservation.NO_CURRENT_WRITER
    assert snapshot.lease_id is None
    assert snapshot.fencing_generation is None
    assert not hasattr(snapshot, "acquire_lease")
    assert not hasattr(snapshot, "submit_order")


def test_health_must_bind_exact_runtime_and_time() -> None:
    wrong = health.HostingRuntimeHealthAssessment(
        account_id=_ACCOUNT,
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(999)),
        health=health.HostingRuntimeHealth.HEALTHY,
        freshness=health.HostingHeartbeatFreshness.CURRENT,
        containment=health.HostingNewWorkContainment.NONE,
        evaluated_at=_NOW,
        heartbeat_id=health.HostingHeartbeatId(_uuid(40)),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(41)),
    )

    with pytest.raises(telemetry.HostingTelemetryValidationError):
        telemetry.project_hosting_runtime_telemetry(
            _record(),
            wrong,
            _leases(active=False),
            registry_generation=registry.HostingRuntimeRegistryGeneration(7),
            snapshot_id=telemetry.HostingTelemetrySnapshotId(_uuid(42)),
            evidence_ref=telemetry.HostingTelemetryEvidenceReference(_uuid(43)),
            observed_at=_NOW,
        )


def test_stale_lease_snapshot_cannot_be_presented_as_current_telemetry() -> None:
    stale = lease.HostingExecutionLeaseSnapshot(
        leases=(),
        captured_at=_NOW - timedelta(seconds=1),
    )

    with pytest.raises(telemetry.HostingTelemetryValidationError):
        telemetry.project_hosting_runtime_telemetry(
            _record(),
            _health(),
            stale,
            registry_generation=registry.HostingRuntimeRegistryGeneration(7),
            snapshot_id=telemetry.HostingTelemetrySnapshotId(_uuid(44)),
            evidence_ref=telemetry.HostingTelemetryEvidenceReference(_uuid(45)),
            observed_at=_NOW,
        )


def test_telemetry_has_no_strategy_provider_or_mutation_surface() -> None:
    snapshot = _project()
    prohibited = (
        "activate_backup",
        "broker",
        "core_decision",
        "redispatch",
        "retry",
        "set_risk",
        "submit_order",
    )

    for name in prohibited:
        assert not hasattr(snapshot, name)
