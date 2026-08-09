from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_trial_licensing as licensing
import qore.infrastructure.hosting_commercial_suspension as commercial
import qore.infrastructure.hosting_execution_lease as lease
import qore.infrastructure.hosting_execution_unit as unit
import qore.infrastructure.hosting_failover_reconciliation as failover
import qore.infrastructure.hosting_health_heartbeat as health
import qore.infrastructure.hosting_orchestrator as orchestrator
import qore.infrastructure.hosting_runtime_registry as registry
import qore.infrastructure.hosting_telemetry as telemetry

_NOW = datetime(2026, 8, 10, 2, 0, tzinfo=UTC)
_ACCOUNT = accounts.TradingAccountId(UUID("54000000-0000-0000-0000-000000000003"))
_RUNTIME_A = accounts.ExecutionRuntimeReference(
    UUID("54000000-0000-0000-0000-000000000004")
)
_RUNTIME_B = accounts.ExecutionRuntimeReference(
    UUID("54000000-0000-0000-0000-000000000005")
)
_ENTITLEMENT = accounts.ProductEntitlementReference(
    UUID("54000000-0000-0000-0000-000000000006")
)

_MISSION08_DELIVERIES = (
    "QORE-MISSION08-DOCS-001",
    "QORE-HOSTING-EXECUTION-UNIT-001",
    "QORE-HOSTING-RUNTIME-REGISTRY-001",
    "QORE-HOSTING-EXECUTION-LEASE-001",
    "QORE-HOSTING-HEALTH-HEARTBEAT-001",
    "QORE-HOSTING-ORCHESTRATOR-001",
    "QORE-HOSTING-FAILOVER-RECONCILIATION-001",
    "QORE-HOSTING-TELEMETRY-001",
    "QORE-HOSTING-COMMERCIAL-SUSPENSION-001",
    "QORE-MISSION08-E2E-OFFLINE-001",
    "QORE-MISSION08-CLOSURE-001",
)

_MISSION08_ARTIFACTS = (
    "docs/missions/MISSION-08-MANAGED-HOSTING-SINGLE-WRITER.md",
    "docs/architecture/QORE-HOSTING-EXECUTION-UNIT-001.md",
    "docs/architecture/QORE-HOSTING-RUNTIME-REGISTRY-001.md",
    "docs/architecture/QORE-HOSTING-EXECUTION-LEASE-001.md",
    "docs/architecture/QORE-HOSTING-HEALTH-HEARTBEAT-001.md",
    "docs/architecture/QORE-HOSTING-ORCHESTRATOR-001.md",
    "docs/architecture/QORE-HOSTING-FAILOVER-RECONCILIATION-001.md",
    "docs/architecture/QORE-HOSTING-TELEMETRY-001.md",
    "docs/architecture/QORE-HOSTING-COMMERCIAL-SUSPENSION-001.md",
    "docs/architecture/QORE-MISSION08-E2E-OFFLINE-001.md",
    "docs/architecture/QORE-MISSION08-CLOSURE-001.md",
    "docs/missions/MISSION-08-CLOSURE.md",
    "tests/infrastructure/test_mission08_e2e_offline.py",
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"54000000-0000-0000-0000-{suffix:012d}")


def _lease(
    *,
    suffix: int,
    runtime_ref: accounts.ExecutionRuntimeReference,
    unit_suffix: int,
    generation: int,
    acquired_at: datetime,
) -> lease.HostingExecutionLease:
    return lease.HostingExecutionLease(
        lease_id=lease.HostingExecutionLeaseId(_uuid(suffix)),
        account_id=_ACCOUNT,
        runtime_ref=runtime_ref,
        unit_id=unit.HostingExecutionUnitId(_uuid(unit_suffix)),
        generation=lease.HostingFencingGeneration(generation),
        status=lease.HostingExecutionLeaseStatus.ACTIVE,
        acquired_at=acquired_at,
        expires_at=_NOW + timedelta(minutes=10),
        revoked_at=None,
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(suffix + 100)),
    )


def test_mission08_closure_records_all_deliveries_and_artifacts() -> None:
    opening = Path(
        "docs/missions/MISSION-08-MANAGED-HOSTING-SINGLE-WRITER.md"
    ).read_text(encoding="utf-8")
    closure = Path("docs/missions/MISSION-08-CLOSURE.md").read_text(
        encoding="utf-8"
    )

    for delivery in _MISSION08_DELIVERIES:
        assert delivery in opening or delivery in closure
    for artifact in _MISSION08_ARTIFACTS:
        assert Path(artifact).is_file(), artifact

    assert Path(
        "docs/roadmap/QORE-POST-MISSION08-FUTURES-RELIABILITY-ROADMAP.md"
    ).is_file()


def test_mission08_single_writer_contract_rejects_split_brain_snapshot() -> None:
    writer_a = _lease(
        suffix=10,
        runtime_ref=_RUNTIME_A,
        unit_suffix=20,
        generation=7,
        acquired_at=_NOW - timedelta(minutes=2),
    )
    writer_b = _lease(
        suffix=11,
        runtime_ref=_RUNTIME_B,
        unit_suffix=21,
        generation=8,
        acquired_at=_NOW - timedelta(minutes=1),
    )

    with pytest.raises(lease.HostingExecutionLeaseValidationError):
        lease.HostingExecutionLeaseSnapshot(
            leases=(writer_a, writer_b),
            captured_at=_NOW,
        )


def test_mission08_hosting_surfaces_preserve_authority_separation() -> None:
    prohibited = {
        "activate_backup",
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

    orchestration_actions = {
        action.value for action in orchestrator.HostingOrchestrationAction
    }
    assert orchestration_actions == {
        "prepare_runtime",
        "request_drain",
        "contain_new_work",
        "stop_runtime",
        "no_action",
    }

    failover_readiness = {state.value for state in failover.HostingFailoverReadiness}
    assert failover_readiness == {"ready_for_lease_acquisition", "blocked"}

    writer_observations = {
        state.value for state in telemetry.HostingWriterObservation
    }
    assert writer_observations == {
        "current_writer",
        "other_runtime_is_writer",
        "no_current_writer",
    }


def test_mission08_secret_boundary_remains_reference_only() -> None:
    execution_unit_fields = {field.name for field in fields(unit.HostingExecutionUnit)}

    assert "secret_refs" in execution_unit_fields
    assert execution_unit_fields.isdisjoint(
        {
            "authorization_header",
            "bearer_token",
            "password",
            "secret",
            "secret_value",
            "token",
        }
    )


def test_mission08_commercial_failure_blocks_new_work_without_forced_close() -> None:
    pending = commercial.evaluate_hosting_commercial_suspension(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_B,
        entitlement_ref=_ENTITLEMENT,
        payment_standing=licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=1,
        evaluated_at=_NOW,
        evidence_ref=commercial.HostingCommercialEvidenceReference(_uuid(30)),
    )
    flat = commercial.evaluate_hosting_commercial_suspension(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_B,
        entitlement_ref=_ENTITLEMENT,
        payment_standing=licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=0,
        evaluated_at=_NOW,
        evidence_ref=commercial.HostingCommercialEvidenceReference(_uuid(31)),
    )

    assert pending.state is commercial.HostingCommercialState.SUSPEND_PENDING_FLAT
    assert pending.allows_new_trades is False
    assert pending.preserve_authorized_position_lifecycle is True
    assert pending.disposition is (
        commercial.HostingRuntimeCommercialDisposition.PRESERVE_POSITION_LIFECYCLE
    )
    assert not hasattr(pending, "close_position")
    assert not hasattr(pending, "liquidate")
    assert not hasattr(pending, "stop_runtime")

    assert flat.state is commercial.HostingCommercialState.SUSPENDED
    assert flat.allows_new_trades is False
    assert flat.disposition is (
        commercial.HostingRuntimeCommercialDisposition.MAY_STOP_WHEN_FLAT
    )
    assert not hasattr(flat, "stop_runtime")


def test_mission08_closure_preserves_external_blocker_and_closed_production() -> None:
    closure = Path("docs/missions/MISSION-08-CLOSURE.md").read_text(
        encoding="utf-8"
    )
    architecture = Path(
        "docs/architecture/QORE-MISSION08-CLOSURE-001.md"
    ).read_text(encoding="utf-8")

    assert "#146" in closure
    assert "OPEN/BLOCKED" in closure
    assert "MISSION-08 = COMPLETED" in closure
    assert "Production = CLOSED" in closure
    assert "Futures Production = CLOSED" in closure
    assert "Native Broker Production = CLOSED" in closure
    assert "Real capital = CLOSED" in closure
    assert "NO CORE DECISION -> NO NEW TRADING ACTION" in architecture
    assert "AMBIGUITY -> CONTAIN -> OBSERVE -> RECONCILE -> RESOLVE" in architecture
    assert "QORE-POST-MISSION08-FUTURES-RELIABILITY-ROADMAP" in architecture
