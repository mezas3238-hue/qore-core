from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_execution_unit as unit
import qore.infrastructure.hosting_runtime_registry as registry
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 18, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"46000000-0000-0000-0000-{suffix:012d}")


def _managed(
    *,
    unit_suffix: int,
    account_suffix: int,
    runtime_suffix: int,
) -> unit.HostingExecutionUnit:
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
        recorded_at=_NOW - timedelta(minutes=2),
    )


def _record(
    managed: unit.HostingExecutionUnit,
    *,
    observed: registry.HostingRuntimeObservedState = (
        registry.HostingRuntimeObservedState.RUNNING
    ),
) -> registry.HostingRuntimeRecord:
    return registry.HostingRuntimeRecord(
        unit=managed,
        desired_state=registry.HostingRuntimeDesiredState.RUNNING,
        observed_state=observed,
        registered_at=_NOW - timedelta(minutes=1),
        observed_at=_NOW - timedelta(seconds=5),
    )


def test_registry_allows_multiple_runtime_candidates_for_one_account() -> None:
    first = _record(_managed(unit_suffix=10, account_suffix=20, runtime_suffix=30))
    second = _record(_managed(unit_suffix=11, account_suffix=20, runtime_suffix=31))
    snapshot = registry.HostingRuntimeRegistrySnapshot(
        generation=registry.HostingRuntimeRegistryGeneration(1),
        records=(second, first),
        captured_at=_NOW,
    )

    candidates = snapshot.candidates_for_account(accounts.TradingAccountId(_uuid(20)))

    assert len(candidates) == 2
    assert {candidate.runtime_ref for candidate in candidates} == {
        accounts.ExecutionRuntimeReference(_uuid(30)),
        accounts.ExecutionRuntimeReference(_uuid(31)),
    }
    assert not hasattr(snapshot, "active_runtime")
    assert not hasattr(snapshot, "writer")


def test_registry_rejects_duplicate_runtime_or_unit_identity() -> None:
    first = _record(_managed(unit_suffix=40, account_suffix=41, runtime_suffix=42))
    duplicate_runtime = _record(
        _managed(unit_suffix=43, account_suffix=44, runtime_suffix=42)
    )

    with pytest.raises(registry.HostingRuntimeRegistryValidationError):
        registry.HostingRuntimeRegistrySnapshot(
            generation=registry.HostingRuntimeRegistryGeneration(1),
            records=(first, duplicate_runtime),
            captured_at=_NOW,
        )


def test_registry_rejects_self_hosted_unit() -> None:
    self_hosted = unit.HostingExecutionUnit(
        unit_id=unit.HostingExecutionUnitId(_uuid(50)),
        client_id=accounts.ClientId(_uuid(1)),
        account_id=accounts.TradingAccountId(_uuid(51)),
        mode=unit.HostingMode.SELF_HOSTED,
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(52)),
        software_version=unit.HostingSoftwareVersion("1.0.0"),
        deployment_ref=None,
        region_ref=None,
        secret_refs=(),
        state=unit.HostingExecutionUnitState.RUNNING,
        recorded_at=_NOW - timedelta(minutes=2),
    )

    with pytest.raises(registry.HostingRuntimeRegistryValidationError):
        _record(self_hosted)


def test_registry_exact_runtime_resolution_is_fail_closed() -> None:
    record = _record(_managed(unit_suffix=60, account_suffix=61, runtime_suffix=62))
    snapshot = registry.HostingRuntimeRegistrySnapshot(
        generation=registry.HostingRuntimeRegistryGeneration(2),
        records=(record,),
        captured_at=_NOW,
    )

    resolved = snapshot.resolve_runtime(accounts.ExecutionRuntimeReference(_uuid(62)))
    missing = snapshot.resolve_runtime(accounts.ExecutionRuntimeReference(_uuid(999)))

    assert isinstance(resolved, result.Success)
    assert resolved.value == record
    assert isinstance(missing, result.Failure)


def test_runtime_observation_cannot_predate_registration_or_snapshot() -> None:
    managed = _managed(unit_suffix=70, account_suffix=71, runtime_suffix=72)
    with pytest.raises(registry.HostingRuntimeRegistryValidationError):
        registry.HostingRuntimeRecord(
            unit=managed,
            desired_state=registry.HostingRuntimeDesiredState.RUNNING,
            observed_state=registry.HostingRuntimeObservedState.RUNNING,
            registered_at=_NOW,
            observed_at=_NOW - timedelta(seconds=1),
        )


def test_registry_state_does_not_grant_execution_authority() -> None:
    record = _record(_managed(unit_suffix=80, account_suffix=81, runtime_suffix=82))
    snapshot = registry.HostingRuntimeRegistrySnapshot(
        generation=registry.HostingRuntimeRegistryGeneration(3),
        records=(record,),
        captured_at=_NOW,
    )

    assert record.observed_state is registry.HostingRuntimeObservedState.RUNNING
    assert record.desired_state is registry.HostingRuntimeDesiredState.RUNNING
    assert not hasattr(record, "can_execute")
    assert not hasattr(record, "lease")
    assert not hasattr(record, "fencing_token")
    assert not hasattr(snapshot, "elect")
    assert not hasattr(snapshot, "submit_order")
