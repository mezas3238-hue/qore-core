from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_execution_unit as unit
import qore.infrastructure.hosting_health_heartbeat as health
import qore.infrastructure.hosting_runtime_registry as registry

_NOW = datetime(2026, 8, 9, 20, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"48000000-0000-0000-0000-{suffix:012d}")


def _registry() -> registry.HostingRuntimeRegistrySnapshot:
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
    record = registry.HostingRuntimeRecord(
        unit=managed,
        desired_state=registry.HostingRuntimeDesiredState.RUNNING,
        observed_state=registry.HostingRuntimeObservedState.RUNNING,
        registered_at=_NOW - timedelta(minutes=4),
        observed_at=_NOW - timedelta(seconds=5),
    )
    return registry.HostingRuntimeRegistrySnapshot(
        generation=registry.HostingRuntimeRegistryGeneration(1),
        records=(record,),
        captured_at=_NOW,
    )


def _heartbeat(
    *,
    runtime_health: health.HostingRuntimeHealth = health.HostingRuntimeHealth.HEALTHY,
    fresh_until: datetime | None = None,
) -> health.HostingHeartbeatSample:
    return health.HostingHeartbeatSample(
        heartbeat_id=health.HostingHeartbeatId(_uuid(10)),
        account_id=accounts.TradingAccountId(_uuid(3)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        health=runtime_health,
        observed_at=_NOW - timedelta(seconds=10),
        fresh_until=fresh_until or _NOW + timedelta(seconds=20),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(11)),
    )


def test_current_healthy_heartbeat_is_observation_not_execution_authority() -> None:
    assessment = health.assess_hosting_runtime_health(
        _registry(),
        account_id=accounts.TradingAccountId(_uuid(3)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        heartbeat=_heartbeat(),
        evaluated_at=_NOW,
    )

    assert assessment.health is health.HostingRuntimeHealth.HEALTHY
    assert assessment.freshness is health.HostingHeartbeatFreshness.CURRENT
    assert assessment.containment is health.HostingNewWorkContainment.NONE
    assert assessment.requires_new_work_containment is False
    assert not hasattr(assessment, "can_execute")
    assert not hasattr(assessment, "lease")
    assert not hasattr(assessment, "activate_backup")


def test_stale_heartbeat_stops_new_work_but_does_not_activate_backup() -> None:
    assessment = health.assess_hosting_runtime_health(
        _registry(),
        account_id=accounts.TradingAccountId(_uuid(3)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        heartbeat=_heartbeat(fresh_until=_NOW - timedelta(seconds=1)),
        evaluated_at=_NOW,
    )

    assert assessment.freshness is health.HostingHeartbeatFreshness.STALE
    assert assessment.containment is (
        health.HostingNewWorkContainment.STOP_ASSIGNING_NEW_WORK
    )
    assert assessment.requires_new_work_containment is True
    assert not hasattr(assessment, "activate_backup")


def test_unreachable_current_heartbeat_stops_new_work_only() -> None:
    assessment = health.assess_hosting_runtime_health(
        _registry(),
        account_id=accounts.TradingAccountId(_uuid(3)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        heartbeat=_heartbeat(runtime_health=health.HostingRuntimeHealth.UNREACHABLE),
        evaluated_at=_NOW,
    )

    assert assessment.health is health.HostingRuntimeHealth.UNREACHABLE
    assert assessment.containment is (
        health.HostingNewWorkContainment.STOP_ASSIGNING_NEW_WORK
    )
    assert not hasattr(assessment, "revoke_lease")
    assert not hasattr(assessment, "fence")


def test_missing_heartbeat_fails_closed_without_fabricating_evidence() -> None:
    assessment = health.assess_hosting_runtime_health(
        _registry(),
        account_id=accounts.TradingAccountId(_uuid(3)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        heartbeat=None,
        evaluated_at=_NOW,
    )

    assert assessment.health is health.HostingRuntimeHealth.UNKNOWN
    assert assessment.freshness is health.HostingHeartbeatFreshness.UNKNOWN
    assert assessment.containment is health.HostingNewWorkContainment.FAIL_CLOSED
    assert assessment.heartbeat_id is None
    assert assessment.evidence_ref is None


def test_heartbeat_must_bind_registered_account_runtime() -> None:
    sample = _heartbeat()
    with pytest.raises(health.HostingHealthHeartbeatValidationError):
        health.assess_hosting_runtime_health(
            _registry(),
            account_id=accounts.TradingAccountId(_uuid(999)),
            runtime_ref=sample.runtime_ref,
            heartbeat=sample,
            evaluated_at=_NOW,
        )

    with pytest.raises(health.HostingHealthHeartbeatValidationError):
        health.assess_hosting_runtime_health(
            _registry(),
            account_id=sample.account_id,
            runtime_ref=accounts.ExecutionRuntimeReference(_uuid(998)),
            heartbeat=sample,
            evaluated_at=_NOW,
        )


def test_future_heartbeat_and_invalid_freshness_interval_are_rejected() -> None:
    with pytest.raises(health.HostingHealthHeartbeatValidationError):
        health.HostingHeartbeatSample(
            heartbeat_id=health.HostingHeartbeatId(_uuid(20)),
            account_id=accounts.TradingAccountId(_uuid(3)),
            runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
            health=health.HostingRuntimeHealth.HEALTHY,
            observed_at=_NOW,
            fresh_until=_NOW,
            evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(21)),
        )

    future = health.HostingHeartbeatSample(
        heartbeat_id=health.HostingHeartbeatId(_uuid(22)),
        account_id=accounts.TradingAccountId(_uuid(3)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        health=health.HostingRuntimeHealth.HEALTHY,
        observed_at=_NOW + timedelta(seconds=1),
        fresh_until=_NOW + timedelta(seconds=30),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(23)),
    )
    with pytest.raises(health.HostingHealthHeartbeatValidationError):
        health.assess_hosting_runtime_health(
            _registry(),
            account_id=future.account_id,
            runtime_ref=future.runtime_ref,
            heartbeat=future,
            evaluated_at=_NOW,
        )
