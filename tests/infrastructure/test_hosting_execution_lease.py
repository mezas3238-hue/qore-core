from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_execution_lease as lease
import qore.infrastructure.hosting_execution_unit as unit
import qore.infrastructure.hosting_runtime_registry as registry
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 19, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"47000000-0000-0000-0000-{suffix:012d}")


def _unit(*, unit_suffix: int, account_suffix: int, runtime_suffix: int) -> unit.HostingExecutionUnit:
    return unit.HostingExecutionUnit(
        unit_id=unit.HostingExecutionUnitId(_uuid(unit_suffix)),
        client_id=accounts.ClientId(_uuid(1)),
        account_id=accounts.TradingAccountId(_uuid(account_suffix)),
        mode=unit.HostingMode.QORE_MANAGED,
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(runtime_suffix)),
        software_version=unit.HostingSoftwareVersion("1.0.0"),
        deployment_ref=unit.HostingDeploymentReference(_uuid(unit_suffix + 100)),
        region_ref=unit.HostingRegionReference("us-east-execution"),
        secret_refs=(),
        state=unit.HostingExecutionUnitState.READY,
        recorded_at=_NOW - timedelta(minutes=5),
    )


def _registry() -> registry.HostingRuntimeRegistrySnapshot:
    first = registry.HostingRuntimeRecord(
        unit=_unit(unit_suffix=10, account_suffix=20, runtime_suffix=30),
        desired_state=registry.HostingRuntimeDesiredState.RUNNING,
        observed_state=registry.HostingRuntimeObservedState.RUNNING,
        registered_at=_NOW - timedelta(minutes=4),
        observed_at=_NOW - timedelta(seconds=5),
    )
    second = registry.HostingRuntimeRecord(
        unit=_unit(unit_suffix=11, account_suffix=20, runtime_suffix=31),
        desired_state=registry.HostingRuntimeDesiredState.RUNNING,
        observed_state=registry.HostingRuntimeObservedState.RUNNING,
        registered_at=_NOW - timedelta(minutes=4),
        observed_at=_NOW - timedelta(seconds=5),
    )
    third = registry.HostingRuntimeRecord(
        unit=_unit(unit_suffix=12, account_suffix=21, runtime_suffix=32),
        desired_state=registry.HostingRuntimeDesiredState.RUNNING,
        observed_state=registry.HostingRuntimeObservedState.RUNNING,
        registered_at=_NOW - timedelta(minutes=4),
        observed_at=_NOW - timedelta(seconds=5),
    )
    return registry.HostingRuntimeRegistrySnapshot(
        generation=registry.HostingRuntimeRegistryGeneration(1),
        records=(first, second, third),
        captured_at=_NOW,
    )


def _empty_snapshot(at: datetime = _NOW) -> lease.HostingExecutionLeaseSnapshot:
    return lease.HostingExecutionLeaseSnapshot(leases=(), captured_at=at)


def _acquire(
    snapshot: lease.HostingExecutionLeaseSnapshot,
    *,
    account_suffix: int = 20,
    runtime_suffix: int = 30,
    lease_suffix: int = 40,
    generation: int = 1,
    acquired_at: datetime = _NOW,
    expires_at: datetime | None = None,
) -> result.Result[lease.HostingExecutionLeaseSnapshot, lease.HostingExecutionLeaseError]:
    return lease.acquire_hosting_execution_lease(
        _registry(),
        snapshot,
        account_id=accounts.TradingAccountId(_uuid(account_suffix)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(runtime_suffix)),
        lease_id=lease.HostingExecutionLeaseId(_uuid(lease_suffix)),
        generation=lease.HostingFencingGeneration(generation),
        acquired_at=acquired_at,
        expires_at=expires_at or acquired_at + timedelta(minutes=5),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(lease_suffix + 1)),
    )


def test_one_account_can_have_exactly_one_current_execution_authority() -> None:
    acquired = _acquire(_empty_snapshot())
    assert isinstance(acquired, result.Success)

    authority = acquired.value.current_authority(
        accounts.TradingAccountId(_uuid(20)),
        evaluated_at=_NOW,
    )
    second = _acquire(
        acquired.value,
        runtime_suffix=31,
        lease_suffix=50,
        generation=2,
        acquired_at=_NOW,
    )

    assert isinstance(authority, result.Success)
    assert authority.value.runtime_ref == accounts.ExecutionRuntimeReference(_uuid(30))
    assert authority.value.generation == lease.HostingFencingGeneration(1)
    assert isinstance(second, result.Failure)
    assert "already has active execution authority" in str(second.error)


def test_different_accounts_keep_independent_writer_authority() -> None:
    first = _acquire(_empty_snapshot())
    assert isinstance(first, result.Success)
    second = _acquire(
        first.value,
        account_suffix=21,
        runtime_suffix=32,
        lease_suffix=60,
        generation=1,
    )
    assert isinstance(second, result.Success)

    a = second.value.current_authority(
        accounts.TradingAccountId(_uuid(20)),
        evaluated_at=_NOW,
    )
    b = second.value.current_authority(
        accounts.TradingAccountId(_uuid(21)),
        evaluated_at=_NOW,
    )
    assert isinstance(a, result.Success)
    assert isinstance(b, result.Success)
    assert a.value.runtime_ref != b.value.runtime_ref


def test_revocation_removes_authority_and_does_not_auto_acquire_backup() -> None:
    acquired = _acquire(_empty_snapshot())
    assert isinstance(acquired, result.Success)
    revoked = lease.revoke_hosting_execution_lease(
        acquired.value,
        lease.HostingExecutionLeaseId(_uuid(40)),
        revoked_at=_NOW + timedelta(seconds=10),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(70)),
    )
    assert isinstance(revoked, result.Success)

    current = revoked.value.current_authority(
        accounts.TradingAccountId(_uuid(20)),
        evaluated_at=_NOW + timedelta(seconds=10),
    )
    assert isinstance(current, result.Failure)
    assert not hasattr(revoked.value, "activate_backup")
    assert not hasattr(revoked.value, "redispatch")


def test_new_writer_requires_monotonic_fencing_generation_after_revocation() -> None:
    acquired = _acquire(_empty_snapshot())
    assert isinstance(acquired, result.Success)
    revoked = lease.revoke_hosting_execution_lease(
        acquired.value,
        lease.HostingExecutionLeaseId(_uuid(40)),
        revoked_at=_NOW + timedelta(seconds=10),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(71)),
    )
    assert isinstance(revoked, result.Success)

    stale_generation = _acquire(
        revoked.value,
        runtime_suffix=31,
        lease_suffix=72,
        generation=1,
        acquired_at=_NOW + timedelta(seconds=10),
    )
    new_generation = _acquire(
        revoked.value,
        runtime_suffix=31,
        lease_suffix=73,
        generation=2,
        acquired_at=_NOW + timedelta(seconds=10),
    )

    assert isinstance(stale_generation, result.Failure)
    assert "must exceed account history" in str(stale_generation.error)
    assert isinstance(new_generation, result.Success)
    authority = new_generation.value.current_authority(
        accounts.TradingAccountId(_uuid(20)),
        evaluated_at=_NOW + timedelta(seconds=10),
    )
    assert isinstance(authority, result.Success)
    assert authority.value.runtime_ref == accounts.ExecutionRuntimeReference(_uuid(31))
    assert authority.value.generation == lease.HostingFencingGeneration(2)


def test_expired_active_lease_is_not_authoritative_and_old_generation_is_fenced() -> None:
    old = lease.HostingExecutionLease(
        lease_id=lease.HostingExecutionLeaseId(_uuid(80)),
        account_id=accounts.TradingAccountId(_uuid(20)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(30)),
        unit_id=unit.HostingExecutionUnitId(_uuid(10)),
        generation=lease.HostingFencingGeneration(1),
        status=lease.HostingExecutionLeaseStatus.ACTIVE,
        acquired_at=_NOW - timedelta(minutes=10),
        expires_at=_NOW - timedelta(minutes=5),
        revoked_at=None,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(81)),
    )
    snapshot = lease.HostingExecutionLeaseSnapshot(leases=(old,), captured_at=_NOW)

    current = snapshot.current_authority(
        accounts.TradingAccountId(_uuid(20)),
        evaluated_at=_NOW,
    )
    new = _acquire(
        snapshot,
        runtime_suffix=31,
        lease_suffix=82,
        generation=2,
        acquired_at=_NOW,
    )

    assert isinstance(current, result.Failure)
    assert isinstance(new, result.Success)
    assert old.is_authoritative_at(_NOW) is False


def test_runtime_must_be_registered_for_exact_account() -> None:
    wrong_account = _acquire(
        _empty_snapshot(),
        account_suffix=21,
        runtime_suffix=30,
        lease_suffix=90,
        generation=1,
    )
    missing_runtime = _acquire(
        _empty_snapshot(),
        runtime_suffix=999,
        lease_suffix=91,
        generation=1,
    )

    assert isinstance(wrong_account, result.Failure)
    assert "binding mismatch" in str(wrong_account.error)
    assert isinstance(missing_runtime, result.Failure)
    assert "must exist in Runtime Registry" in str(missing_runtime.error)


def test_authority_attestation_is_writer_gate_not_core_or_broker_authority() -> None:
    acquired = _acquire(_empty_snapshot())
    assert isinstance(acquired, result.Success)
    authority = acquired.value.current_authority(
        accounts.TradingAccountId(_uuid(20)),
        evaluated_at=_NOW,
    )
    assert isinstance(authority, result.Success)

    assert not hasattr(authority.value, "core_decision")
    assert not hasattr(authority.value, "submit_order")
    assert not hasattr(authority.value, "broker")
    assert not hasattr(authority.value, "retry")


def test_snapshot_rejects_two_simultaneous_active_writers() -> None:
    first = lease.HostingExecutionLease(
        lease_id=lease.HostingExecutionLeaseId(_uuid(100)),
        account_id=accounts.TradingAccountId(_uuid(20)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(30)),
        unit_id=unit.HostingExecutionUnitId(_uuid(10)),
        generation=lease.HostingFencingGeneration(1),
        status=lease.HostingExecutionLeaseStatus.ACTIVE,
        acquired_at=_NOW - timedelta(seconds=20),
        expires_at=_NOW + timedelta(minutes=5),
        revoked_at=None,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(101)),
    )
    second = lease.HostingExecutionLease(
        lease_id=lease.HostingExecutionLeaseId(_uuid(102)),
        account_id=accounts.TradingAccountId(_uuid(20)),
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(31)),
        unit_id=unit.HostingExecutionUnitId(_uuid(11)),
        generation=lease.HostingFencingGeneration(2),
        status=lease.HostingExecutionLeaseStatus.ACTIVE,
        acquired_at=_NOW - timedelta(seconds=10),
        expires_at=_NOW + timedelta(minutes=5),
        revoked_at=None,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(103)),
    )

    with pytest.raises(lease.HostingExecutionLeaseValidationError):
        lease.HostingExecutionLeaseSnapshot(
            leases=(first, second),
            captured_at=_NOW,
        )
