from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

import qore.infrastructure.adapter_configuration as adapter_configuration
import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_execution_unit as hosting
import qore.infrastructure.secrets as secrets

_NOW = datetime(2026, 8, 9, 17, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"45000000-0000-0000-0000-{suffix:012d}")


def _secret(suffix: int) -> secrets.SecretRef:
    return secrets.SecretRef(
        ref_id=secrets.SecretRefId(_uuid(suffix)),
        name=adapter_configuration.AdapterSecretName("broker-credential-ref"),
        external_reference=secrets.SecretExternalReference(
            f"qore/hosting/account-{suffix}/broker-credential"
        ),
    )


def _managed() -> hosting.HostingExecutionUnit:
    return hosting.HostingExecutionUnit(
        unit_id=hosting.HostingExecutionUnitId(_uuid(1)),
        client_id=accounts.ClientId(_uuid(2)),
        account_id=accounts.TradingAccountId(_uuid(3)),
        mode=hosting.HostingMode.QORE_MANAGED,
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(4)),
        software_version=hosting.HostingSoftwareVersion("1.0.0"),
        deployment_ref=hosting.HostingDeploymentReference(_uuid(5)),
        region_ref=hosting.HostingRegionReference("us-east-execution"),
        secret_refs=(_secret(6),),
        state=hosting.HostingExecutionUnitState.READY,
        recorded_at=_NOW,
    )


def test_qore_managed_unit_binds_account_runtime_placement_and_secret_refs() -> None:
    unit = _managed()

    assert unit.mode is hosting.HostingMode.QORE_MANAGED
    assert unit.is_qore_orchestrated is True
    assert unit.account_id == accounts.TradingAccountId(_uuid(3))
    assert unit.runtime_ref == accounts.ExecutionRuntimeReference(_uuid(4))
    assert unit.region_ref == hosting.HostingRegionReference("us-east-execution")
    assert len(unit.secret_refs) == 1
    assert isinstance(unit.secret_refs[0], secrets.SecretRef)


def test_self_hosted_unit_cannot_claim_qore_deployment_or_region() -> None:
    unit = hosting.HostingExecutionUnit(
        unit_id=hosting.HostingExecutionUnitId(_uuid(10)),
        client_id=accounts.ClientId(_uuid(11)),
        account_id=accounts.TradingAccountId(_uuid(12)),
        mode=hosting.HostingMode.SELF_HOSTED,
        runtime_ref=accounts.ExecutionRuntimeReference(_uuid(13)),
        software_version=hosting.HostingSoftwareVersion("1.2.3"),
        deployment_ref=None,
        region_ref=None,
        secret_refs=(),
        state=hosting.HostingExecutionUnitState.RUNNING,
        recorded_at=_NOW,
    )

    assert unit.is_qore_orchestrated is False
    assert unit.deployment_ref is None
    assert unit.region_ref is None

    with pytest.raises(hosting.HostingExecutionUnitValidationError):
        hosting.HostingExecutionUnit(
            unit_id=hosting.HostingExecutionUnitId(_uuid(20)),
            client_id=unit.client_id,
            account_id=unit.account_id,
            mode=hosting.HostingMode.SELF_HOSTED,
            runtime_ref=unit.runtime_ref,
            software_version=unit.software_version,
            deployment_ref=hosting.HostingDeploymentReference(_uuid(21)),
            region_ref=None,
            secret_refs=(),
            state=unit.state,
            recorded_at=_NOW,
        )


def test_managed_unit_requires_explicit_deployment_and_region() -> None:
    managed = _managed()

    with pytest.raises(hosting.HostingExecutionUnitValidationError):
        hosting.HostingExecutionUnit(
            unit_id=hosting.HostingExecutionUnitId(_uuid(30)),
            client_id=managed.client_id,
            account_id=managed.account_id,
            mode=hosting.HostingMode.QORE_MANAGED,
            runtime_ref=managed.runtime_ref,
            software_version=managed.software_version,
            deployment_ref=None,
            region_ref=managed.region_ref,
            secret_refs=(),
            state=managed.state,
            recorded_at=_NOW,
        )


def test_secret_references_are_unique_and_never_raw_values() -> None:
    secret_ref = _secret(40)
    managed = _managed()

    with pytest.raises(hosting.HostingExecutionUnitValidationError):
        hosting.HostingExecutionUnit(
            unit_id=hosting.HostingExecutionUnitId(_uuid(41)),
            client_id=managed.client_id,
            account_id=managed.account_id,
            mode=managed.mode,
            runtime_ref=managed.runtime_ref,
            software_version=managed.software_version,
            deployment_ref=managed.deployment_ref,
            region_ref=managed.region_ref,
            secret_refs=(secret_ref, secret_ref),
            state=managed.state,
            recorded_at=_NOW,
        )

    fields = vars(hosting.HostingExecutionUnit)
    assert "password" not in fields
    assert "token" not in fields
    assert "api_key" not in fields
    assert "credential" not in fields


def test_unit_lifecycle_state_and_orchestration_do_not_grant_execution_authority() -> None:
    unit = _managed()

    assert unit.state is hosting.HostingExecutionUnitState.READY
    assert unit.is_qore_orchestrated is True
    assert not hasattr(unit, "can_trade")
    assert not hasattr(unit, "submit_order")
    assert not hasattr(unit, "acquire_lease")
    assert not hasattr(unit, "fencing_token")
    assert not hasattr(unit, "broker")


def test_hosting_version_and_region_are_canonical() -> None:
    with pytest.raises(hosting.HostingExecutionUnitValidationError):
        hosting.HostingSoftwareVersion("latest")
    with pytest.raises(hosting.HostingExecutionUnitValidationError):
        hosting.HostingRegionReference("US East")
