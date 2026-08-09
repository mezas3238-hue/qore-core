from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.execution_reconciliation as execution
import qore.infrastructure.hosting_evidence_governed_failover as governed
import qore.infrastructure.hosting_execution_lease as lease
import qore.infrastructure.hosting_execution_unit as unit
import qore.infrastructure.hosting_failover_reconciliation as failover
import qore.infrastructure.hosting_health_heartbeat as health
import qore.infrastructure.hosting_io_certification as io
import qore.infrastructure.hosting_latency_safety as latency
import qore.infrastructure.hosting_reliability_incident as incident
import qore.infrastructure.hosting_reliability_lab as lab
import qore.infrastructure.hosting_runtime_registry as registry
import qore.kernel.result as result

_T0 = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
_T1 = _T0 + timedelta(minutes=1)
_T2 = _T0 + timedelta(minutes=2)
_IO_START = _T0 - timedelta(minutes=10)
_ACCOUNT = accounts.TradingAccountId(UUID("60000000-0000-0000-0000-000000000003"))
_RUNTIME_A = accounts.ExecutionRuntimeReference(
    UUID("60000000-0000-0000-0000-000000000004")
)
_RUNTIME_B = accounts.ExecutionRuntimeReference(
    UUID("60000000-0000-0000-0000-000000000005")
)
_CLIENT = accounts.ClientId(UUID("60000000-0000-0000-0000-000000000006"))


def _uuid(suffix: int) -> UUID:
    return UUID(f"60000000-0000-0000-0000-{suffix:012d}")


def _unit(
    runtime_ref: accounts.ExecutionRuntimeReference,
    *,
    suffix: int,
) -> unit.HostingExecutionUnit:
    return unit.HostingExecutionUnit(
        unit_id=unit.HostingExecutionUnitId(_uuid(suffix)),
        client_id=_CLIENT,
        account_id=_ACCOUNT,
        mode=unit.HostingMode.QORE_MANAGED,
        runtime_ref=runtime_ref,
        software_version=unit.HostingSoftwareVersion("1.0.0"),
        deployment_ref=unit.HostingDeploymentReference(_uuid(suffix + 100)),
        region_ref=unit.HostingRegionReference("us-east-reliability-test"),
        secret_refs=(),
        state=unit.HostingExecutionUnitState.RUNNING,
        recorded_at=_T0 - timedelta(minutes=20),
    )


def _record(
    runtime_ref: accounts.ExecutionRuntimeReference,
    *,
    suffix: int,
) -> registry.HostingRuntimeRecord:
    return registry.HostingRuntimeRecord(
        unit=_unit(runtime_ref, suffix=suffix),
        desired_state=registry.HostingRuntimeDesiredState.RUNNING,
        observed_state=registry.HostingRuntimeObservedState.RUNNING,
        registered_at=_T0 - timedelta(minutes=19),
        observed_at=_T0 - timedelta(seconds=5),
    )


def _registry() -> registry.HostingRuntimeRegistrySnapshot:
    return registry.HostingRuntimeRegistrySnapshot(
        generation=registry.HostingRuntimeRegistryGeneration(20),
        records=(
            _record(_RUNTIME_A, suffix=10),
            _record(_RUNTIME_B, suffix=11),
        ),
        captured_at=_T2,
    )


def _lease_snapshots() -> tuple[
    lease.HostingExecutionLeaseSnapshot,
    lease.HostingExecutionLeaseSnapshot,
]:
    empty = lease.HostingExecutionLeaseSnapshot(leases=(), captured_at=_T0)
    acquired = lease.acquire_hosting_execution_lease(
        _registry(),
        empty,
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_A,
        lease_id=lease.HostingExecutionLeaseId(_uuid(100)),
        generation=lease.HostingFencingGeneration(7),
        acquired_at=_T0,
        expires_at=_T2 + timedelta(minutes=10),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(101)),
    )
    assert isinstance(acquired, result.Success)
    active = lease.HostingExecutionLeaseSnapshot(
        leases=acquired.value.leases,
        captured_at=_T1,
    )
    revoked = lease.revoke_hosting_execution_lease(
        active,
        lease.HostingExecutionLeaseId(_uuid(100)),
        revoked_at=_T0 + timedelta(seconds=30),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(102)),
    )
    assert isinstance(revoked, result.Success)
    return active, revoked.value


def _heartbeat(
    runtime_ref: accounts.ExecutionRuntimeReference,
    *,
    suffix: int,
    runtime_health: health.HostingRuntimeHealth,
) -> health.HostingHeartbeatSample:
    return health.HostingHeartbeatSample(
        heartbeat_id=health.HostingHeartbeatId(_uuid(suffix)),
        account_id=_ACCOUNT,
        runtime_ref=runtime_ref,
        health=runtime_health,
        observed_at=_T1 - timedelta(seconds=1),
        fresh_until=_T1 + timedelta(seconds=30),
        evidence_ref=health.HostingHeartbeatEvidenceReference(_uuid(suffix + 1)),
    )


def _health(
    runtime_ref: accounts.ExecutionRuntimeReference,
    *,
    suffix: int,
    runtime_health: health.HostingRuntimeHealth,
) -> health.HostingRuntimeHealthAssessment:
    return health.assess_hosting_runtime_health(
        _registry(),
        account_id=_ACCOUNT,
        runtime_ref=runtime_ref,
        heartbeat=_heartbeat(
            runtime_ref,
            suffix=suffix,
            runtime_health=runtime_health,
        ),
        evaluated_at=_T1,
    )


def _previous_health() -> health.HostingRuntimeHealthAssessment:
    return _health(
        _RUNTIME_A,
        suffix=200,
        runtime_health=health.HostingRuntimeHealth.UNREACHABLE,
    )


def _candidate_health() -> health.HostingRuntimeHealthAssessment:
    return _health(
        _RUNTIME_B,
        suffix=210,
        runtime_health=health.HostingRuntimeHealth.HEALTHY,
    )


def _account_reconciliation(
    status: failover.HostingExternalAccountReconciliationStatus = (
        failover.HostingExternalAccountReconciliationStatus.MATCHED
    ),
) -> failover.HostingExternalAccountReconciliation:
    return failover.HostingExternalAccountReconciliation(
        account_id=_ACCOUNT,
        status=status,
        reconciled_at=_T1 - timedelta(seconds=3),
        evidence_ref=(
            failover.HostingFailoverEvidenceReference(_uuid(220))
            if status is failover.HostingExternalAccountReconciliationStatus.MATCHED
            else None
        ),
    )


def _execution_reconciliation(
    status: execution.ExecutionReconciliationStatus = (
        execution.ExecutionReconciliationStatus.MATCHED
    ),
) -> tuple[execution.ExecutionReconciliationSnapshot, ...]:
    return (
        execution.ExecutionReconciliationSnapshot(
            status=status,
            reconciled_at=_T1 - timedelta(seconds=2),
            issues=(
                ()
                if status is execution.ExecutionReconciliationStatus.MATCHED
                else ("ambiguous_execution_state",)
            ),
        ),
    )


def _incident_report(
    action: lab.HostingReliabilityInfrastructureAction,
    *,
    suffix: int,
    post_state: incident.HostingReliabilityPostCertificationState = (
        incident.HostingReliabilityPostCertificationState.NOT_CERTIFIED
    ),
) -> incident.HostingReliabilityIncidentReport:
    observation = lab.HostingReliabilityObservation(
        observation_id=lab.HostingReliabilityObservationId(_uuid(suffix)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME_A,
        boundary=lab.HostingReliabilityBoundary.NETWORK_EGRESS,
        condition=lab.HostingReliabilityCondition.ANOMALOUS,
        severity=lab.HostingReliabilitySeverity.CRITICAL,
        observed_at=_T0 + timedelta(seconds=10),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 1)),
    )
    policy = lab.HostingReliabilityPolicySnapshot(
        policy_ref=lab.HostingReliabilityPolicyReference(_uuid(suffix + 2)),
        version=1,
        allowed_actions=(
            lab.HostingReliabilityInfrastructureAction.NO_ACTION,
            action,
        ),
        effective_at=_T0,
        expires_at=None,
    )
    assessed = lab.assess_hosting_reliability_observation(
        observation,
        policy,
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(suffix + 3)),
        authorized_action=action,
        rationale_code=lab.HostingReliabilityRationaleCode(
            "runtime.remains_unsafe_after_recovery"
        ),
        assessed_at=_T0 + timedelta(seconds=11),
        supporting_evidence_refs=(
            lab.HostingReliabilityEvidenceReference(_uuid(suffix + 4)),
        ),
    )
    assert isinstance(assessed, result.Success)
    anomaly = incident.build_hosting_reliability_anomaly_report(
        observation,
        assessed.value,
        report_id=incident.HostingReliabilityAnomalyReportId(_uuid(suffix + 5)),
        metric_name=incident.HostingReliabilityMetricName("network_egress.p99"),
        threshold_evidence_ref=lab.HostingReliabilityEvidenceReference(
            _uuid(suffix + 6)
        ),
        generated_at=_T0 + timedelta(seconds=12),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 7)),
    )
    assert isinstance(anomaly, result.Success)
    opened = incident.open_hosting_reliability_incident(
        anomaly.value,
        incident_id=incident.HostingReliabilityIncidentId(_uuid(suffix + 8)),
        opened_at=_T0 + timedelta(seconds=13),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 9)),
    )
    assert isinstance(opened, result.Success)
    recorded = lab.record_hosting_reliability_action(
        assessed.value,
        action_id=lab.HostingReliabilityActionId(_uuid(suffix + 10)),
        action=action,
        outcome=lab.HostingReliabilityActionOutcome.SUCCEEDED,
        occurred_at=_T0 + timedelta(seconds=14),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 11)),
    )
    assert isinstance(recorded, result.Success)
    post = incident.HostingReliabilityPostActionCertification(
        certification_id=incident.HostingReliabilityPostCertificationId(
            _uuid(suffix + 12)
        ),
        incident_id=opened.value.incident_id,
        state=post_state,
        certified_at=_T0 + timedelta(seconds=15),
        evidence_refs=(
            lab.HostingReliabilityEvidenceReference(_uuid(suffix + 13)),
        ),
    )
    return incident.HostingReliabilityIncidentReport(
        report_id=incident.HostingReliabilityIncidentReportId(_uuid(suffix + 14)),
        incident=opened.value,
        action_record=recorded.value,
        recovery_attempts=(),
        post_certification=post,
        generated_at=_T0 + timedelta(seconds=16),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 15)),
    )


def _duration(milliseconds: int) -> latency.HostingLatencyDuration:
    return latency.HostingLatencyDuration.from_milliseconds(milliseconds)


def _io_samples(
    runtime_ref: accounts.ExecutionRuntimeReference,
    boundary: lab.HostingReliabilityBoundary,
    durations_ms: tuple[int, ...],
    *,
    suffix: int,
) -> tuple[io.HostingIOTimingSample, ...]:
    checkpoints = {
        lab.HostingReliabilityBoundary.NETWORK_INGRESS: (
            io.HostingIOCheckpoint.PROVIDER_EVENT,
            io.HostingIOCheckpoint.HOSTING_INGRESS,
        ),
        lab.HostingReliabilityBoundary.INTERNAL_PIPELINE: (
            io.HostingIOCheckpoint.HOSTING_INGRESS,
            io.HostingIOCheckpoint.CORE_INGRESS,
        ),
        lab.HostingReliabilityBoundary.NETWORK_EGRESS: (
            io.HostingIOCheckpoint.CORE_DECISION,
            io.HostingIOCheckpoint.ADAPTER_RECEIVE,
        ),
    }
    start_checkpoint, end_checkpoint = checkpoints[boundary]
    samples: list[io.HostingIOTimingSample] = []
    for index, milliseconds in enumerate(durations_ms):
        started_at = _IO_START + timedelta(seconds=index)
        samples.append(
            io.HostingIOTimingSample(
                sample_id=io.HostingIOTimingSampleId(_uuid(suffix + index)),
                account_id=_ACCOUNT,
                runtime_ref=runtime_ref,
                boundary=boundary,
                started_checkpoint=start_checkpoint,
                ended_checkpoint=end_checkpoint,
                started_at=started_at,
                ended_at=started_at + timedelta(milliseconds=milliseconds),
                evidence_ref=lab.HostingReliabilityEvidenceReference(
                    _uuid(suffix + 100 + index)
                ),
            )
        )
    return tuple(samples)


def _io_certificate(
    runtime_ref: accounts.ExecutionRuntimeReference,
    boundary: lab.HostingReliabilityBoundary,
    durations_ms: tuple[int, ...],
    *,
    suffix: int,
) -> io.HostingIOPathCertificate:
    baseline = latency.HostingLatencyBaseline(
        account_id=_ACCOUNT,
        runtime_ref=runtime_ref,
        boundary=boundary,
        reference_p50=_duration(20),
        reference_p95=_duration(30),
        reference_p99=_duration(40),
        certified_at=_IO_START - timedelta(minutes=1),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 200)),
    )
    envelope = latency.HostingLatencyEnvelopePolicy(
        policy_ref=lab.HostingReliabilityPolicyReference(_uuid(suffix + 201)),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 202)),
        absolute_warning=_duration(60),
        absolute_degraded=_duration(120),
        catastrophic_hard_ceiling=_duration(300),
        relative_warning_basis_points=15_000,
        relative_degraded_basis_points=25_000,
        contain_on_degraded=True,
        effective_at=_IO_START - timedelta(minutes=1),
        expires_at=None,
    )
    reliability_policy = lab.HostingReliabilityPolicySnapshot(
        policy_ref=lab.HostingReliabilityPolicyReference(_uuid(suffix + 203)),
        version=1,
        allowed_actions=(
            lab.HostingReliabilityInfrastructureAction.NO_ACTION,
            lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        ),
        effective_at=_IO_START - timedelta(minutes=1),
        expires_at=None,
    )
    certified = io.certify_hosting_io_path(
        _io_samples(
            runtime_ref,
            boundary,
            durations_ms,
            suffix=suffix,
        ),
        baseline,
        envelope,
        reliability_policy,
        distribution_evidence_ref=lab.HostingReliabilityEvidenceReference(
            _uuid(suffix + 204)
        ),
        observation_id=lab.HostingReliabilityObservationId(_uuid(suffix + 205)),
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(suffix + 206)),
        certificate_id=io.HostingIOCertificateId(_uuid(suffix + 207)),
        certificate_evidence_ref=lab.HostingReliabilityEvidenceReference(
            _uuid(suffix + 208)
        ),
        evaluated_at=_IO_START + timedelta(seconds=4),
        issued_at=_IO_START + timedelta(seconds=5),
    )
    assert isinstance(certified, result.Success)
    return certified.value


def _io_report(
    *,
    runtime_ref: accounts.ExecutionRuntimeReference = _RUNTIME_B,
    degraded_egress: bool = False,
    suffix: int = 1000,
) -> io.HostingIOPeriodicReliabilityReport:
    egress = (130, 150, 180) if degraded_egress else (10, 15, 20)
    certificates = (
        _io_certificate(
            runtime_ref,
            lab.HostingReliabilityBoundary.NETWORK_INGRESS,
            (10, 15, 20),
            suffix=suffix,
        ),
        _io_certificate(
            runtime_ref,
            lab.HostingReliabilityBoundary.INTERNAL_PIPELINE,
            (10, 15, 20),
            suffix=suffix + 1000,
        ),
        _io_certificate(
            runtime_ref,
            lab.HostingReliabilityBoundary.NETWORK_EGRESS,
            egress,
            suffix=suffix + 2000,
        ),
    )
    return io.HostingIOPeriodicReliabilityReport(
        report_id=io.HostingIOReportId(_uuid(suffix + 3000)),
        account_id=_ACCOUNT,
        runtime_ref=runtime_ref,
        certificates=certificates,
        window_started_at=_IO_START,
        window_ended_at=_IO_START + timedelta(seconds=4),
        reported_at=_IO_START + timedelta(seconds=6),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 3001)),
    )


def _evaluate(
    leases: lease.HostingExecutionLeaseSnapshot,
    *,
    incident_report: incident.HostingReliabilityIncidentReport | None = None,
    candidate_io_report: io.HostingIOPeriodicReliabilityReport | None = None,
    account_reconciliation: failover.HostingExternalAccountReconciliation | None = None,
    execution_reconciliations: tuple[execution.ExecutionReconciliationSnapshot, ...]
    | None = None,
    suffix: int = 20_000,
) -> result.Result[
    governed.HostingEvidenceGovernedFailoverAssessment,
    governed.HostingEvidenceGovernedFailoverError,
]:
    return governed.evaluate_evidence_governed_failover(
        incident_report
        or _incident_report(
            lab.HostingReliabilityInfrastructureAction.INITIATE_FAILOVER_EVALUATION,
            suffix=400,
        ),
        candidate_io_report or _io_report(),
        _registry(),
        leases,
        _previous_health(),
        _candidate_health(),
        account_reconciliation or _account_reconciliation(),
        execution_reconciliations or _execution_reconciliation(),
        account_id=_ACCOUNT,
        previous_runtime_ref=_RUNTIME_A,
        candidate_runtime_ref=_RUNTIME_B,
        assessment_id=governed.HostingEvidenceGovernedFailoverAssessmentId(
            _uuid(suffix)
        ),
        mission08_assessment_id=failover.HostingFailoverAssessmentId(
            _uuid(suffix + 1)
        ),
        mission08_evidence_ref=failover.HostingFailoverEvidenceReference(
            _uuid(suffix + 2)
        ),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 3)),
        evaluated_at=_T1,
    )


def test_resolved_incident_cannot_manufacture_failover_readiness() -> None:
    _, revoked = _lease_snapshots()
    resolved = _incident_report(
        lab.HostingReliabilityInfrastructureAction.INITIATE_FAILOVER_EVALUATION,
        suffix=500,
        post_state=incident.HostingReliabilityPostCertificationState.CERTIFIED,
    )

    assessed = _evaluate(revoked, incident_report=resolved, suffix=21_000)

    assert isinstance(assessed, result.Success)
    assert assessed.value.readiness is governed.HostingEvidenceGovernedFailoverReadiness.BLOCKED
    assert assessed.value.reason is (
        governed.HostingEvidenceGovernedFailoverReason.CURRENT_RUNTIME_NOT_PROVEN_UNSAFE
    )
    assert assessed.value.mission08_assessment is None


def test_containment_incident_cannot_escalate_itself_to_failover_evaluation() -> None:
    _, revoked = _lease_snapshots()
    containment = _incident_report(
        lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        suffix=600,
    )

    assessed = _evaluate(revoked, incident_report=containment, suffix=22_000)

    assert isinstance(assessed, result.Success)
    assert assessed.value.readiness is governed.HostingEvidenceGovernedFailoverReadiness.BLOCKED
    assert assessed.value.reason is (
        governed.HostingEvidenceGovernedFailoverReason.FAILOVER_EVALUATION_NOT_AUTHORIZED
    )


def test_candidate_must_be_independently_io_certified_before_mission08_readiness() -> None:
    _, revoked = _lease_snapshots()
    degraded = _io_report(degraded_egress=True, suffix=5000)

    assessed = _evaluate(
        revoked,
        candidate_io_report=degraded,
        suffix=23_000,
    )

    assert degraded.overall_status is io.HostingIOCertificateStatus.NOT_CERTIFIED
    assert isinstance(assessed, result.Success)
    assert assessed.value.reason is (
        governed.HostingEvidenceGovernedFailoverReason.CANDIDATE_IO_NOT_CERTIFIED
    )
    assert assessed.value.mission08_assessment is None


def test_active_previous_authority_remains_canonical_mission08_blocker() -> None:
    active, _ = _lease_snapshots()

    assessed = _evaluate(active, suffix=24_000)

    assert isinstance(assessed, result.Success)
    assert assessed.value.readiness is governed.HostingEvidenceGovernedFailoverReadiness.BLOCKED
    assert assessed.value.reason is (
        governed.HostingEvidenceGovernedFailoverReason.MISSION08_READINESS_BLOCKED
    )
    assert assessed.value.mission08_assessment is not None
    assert assessed.value.mission08_assessment.reason is (
        failover.HostingFailoverReason.PREVIOUS_AUTHORITY_STILL_ACTIVE
    )
    assert assessed.value.next_generation is None


def test_ambiguous_reconciliation_remains_canonical_mission08_blocker() -> None:
    _, revoked = _lease_snapshots()

    assessed = _evaluate(
        revoked,
        account_reconciliation=_account_reconciliation(
            failover.HostingExternalAccountReconciliationStatus.AMBIGUOUS
        ),
        suffix=25_000,
    )

    assert isinstance(assessed, result.Success)
    assert assessed.value.reason is (
        governed.HostingEvidenceGovernedFailoverReason.MISSION08_READINESS_BLOCKED
    )
    assert assessed.value.mission08_assessment is not None
    assert assessed.value.mission08_assessment.reason is (
        failover.HostingFailoverReason.EXTERNAL_ACCOUNT_AMBIGUOUS
    )


def test_evidence_ready_state_still_has_no_writer_until_canonical_lease_acquisition() -> None:
    _, revoked = _lease_snapshots()

    assessed = _evaluate(revoked, suffix=26_000)

    assert isinstance(assessed, result.Success)
    assert assessed.value.readiness is (
        governed.HostingEvidenceGovernedFailoverReadiness.READY_FOR_CANONICAL_LEASE_ACQUISITION
    )
    assert assessed.value.reason is (
        governed.HostingEvidenceGovernedFailoverReason.EVIDENCE_AND_MISSION08_READY
    )
    assert assessed.value.next_generation == lease.HostingFencingGeneration(8)
    no_writer = revoked.current_authority(_ACCOUNT, evaluated_at=_T1)
    assert isinstance(no_writer, result.Failure)


def test_ready_handoff_delegates_to_canonical_n_plus_one_lease_and_certifies_it() -> None:
    _, revoked = _lease_snapshots()
    candidate_io = _io_report(suffix=8000)
    assessed = _evaluate(
        revoked,
        candidate_io_report=candidate_io,
        suffix=27_000,
    )
    assert isinstance(assessed, result.Success)

    acquired = governed.acquire_evidence_governed_failover_lease(
        assessed.value,
        _registry(),
        revoked,
        lease_id=lease.HostingExecutionLeaseId(_uuid(27_100)),
        acquired_at=_T2,
        expires_at=_T2 + timedelta(minutes=10),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(27_101)),
    )
    assert isinstance(acquired, result.Success)
    current = acquired.value.current_authority(_ACCOUNT, evaluated_at=_T2)
    assert isinstance(current, result.Success)
    assert current.value.runtime_ref == _RUNTIME_B
    assert current.value.generation == lease.HostingFencingGeneration(8)
    authoritative = tuple(
        item
        for item in acquired.value.leases_for_account(_ACCOUNT)
        if item.is_authoritative_at(_T2)
    )
    assert len(authoritative) == 1
    assert authoritative[0].runtime_ref == _RUNTIME_B

    certified = governed.certify_availability_failover_handoff(
        assessed.value,
        candidate_io,
        acquired.value,
        certificate_id=governed.HostingAvailabilityFailoverCertificateId(
            _uuid(27_102)
        ),
        certified_at=_T2,
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(27_103)),
    )
    assert isinstance(certified, result.Success)
    assert certified.value.status is (
        governed.HostingAvailabilityFailoverCertificateStatus.CERTIFIED
    )


def test_blocked_assessment_cannot_use_canonical_acquisition_wrapper() -> None:
    active, _ = _lease_snapshots()
    assessed = _evaluate(active, suffix=28_000)
    assert isinstance(assessed, result.Success)

    acquired = governed.acquire_evidence_governed_failover_lease(
        assessed.value,
        _registry(),
        active,
        lease_id=lease.HostingExecutionLeaseId(_uuid(28_100)),
        acquired_at=_T2,
        expires_at=_T2 + timedelta(minutes=10),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(28_101)),
    )
    assert isinstance(acquired, result.Failure)
    assert isinstance(
        acquired.error,
        governed.HostingEvidenceGovernedFailoverExecutionError,
    )


def test_availability_certificate_requires_exact_candidate_io_report_identity() -> None:
    _, revoked = _lease_snapshots()
    candidate_io = _io_report(suffix=11_000)
    assessed = _evaluate(
        revoked,
        candidate_io_report=candidate_io,
        suffix=29_000,
    )
    assert isinstance(assessed, result.Success)
    acquired = governed.acquire_evidence_governed_failover_lease(
        assessed.value,
        _registry(),
        revoked,
        lease_id=lease.HostingExecutionLeaseId(_uuid(29_100)),
        acquired_at=_T2,
        expires_at=_T2 + timedelta(minutes=10),
        evidence_ref=lease.HostingLeaseEvidenceReference(_uuid(29_101)),
    )
    assert isinstance(acquired, result.Success)
    different_report = _io_report(suffix=14_000)

    certified = governed.certify_availability_failover_handoff(
        assessed.value,
        different_report,
        acquired.value,
        certificate_id=governed.HostingAvailabilityFailoverCertificateId(
            _uuid(29_102)
        ),
        certified_at=_T2,
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(29_103)),
    )
    assert isinstance(certified, result.Failure)
    assert isinstance(
        certified.error,
        governed.HostingEvidenceGovernedFailoverValidationError,
    )


def test_evidence_governed_surface_exposes_no_trading_retry_or_direct_server_switch() -> None:
    readiness = {
        state.value for state in governed.HostingEvidenceGovernedFailoverReadiness
    }
    assert readiness == {"ready_for_canonical_lease_acquisition", "blocked"}
    assert "failover" not in readiness
    assert "switch_server" not in readiness

    prohibited = {
        "buy",
        "sell",
        "submit_order",
        "retry_order",
        "redispatch",
        "switch_server",
        "core_decision",
        "provider_sdk",
    }
    for surface in (
        governed.HostingEvidenceGovernedFailoverAssessment,
        governed.HostingAvailabilityFailoverCertificate,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
