from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.hosting_io_certification as io
import qore.infrastructure.hosting_latency_safety as latency
import qore.infrastructure.hosting_reliability_lab as lab
import qore.kernel.result as result

_NOW = datetime(2026, 8, 10, 5, 0, tzinfo=UTC)
_ACCOUNT = accounts.TradingAccountId(UUID("57000000-0000-0000-0000-000000000003"))
_RUNTIME = accounts.ExecutionRuntimeReference(
    UUID("57000000-0000-0000-0000-000000000004")
)

_CHECKPOINTS = {
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
    lab.HostingReliabilityBoundary.ROUND_TRIP: (
        io.HostingIOCheckpoint.CORE_DECISION,
        io.HostingIOCheckpoint.EXTERNAL_ACK,
    ),
}


def _uuid(suffix: int) -> UUID:
    return UUID(f"57000000-0000-0000-0000-{suffix:012d}")


def _duration(milliseconds: int) -> latency.HostingLatencyDuration:
    return latency.HostingLatencyDuration.from_milliseconds(milliseconds)


def _samples(
    boundary: lab.HostingReliabilityBoundary,
    durations_ms: tuple[int, ...],
    *,
    suffix: int,
) -> tuple[io.HostingIOTimingSample, ...]:
    started_checkpoint, ended_checkpoint = _CHECKPOINTS[boundary]
    samples: list[io.HostingIOTimingSample] = []
    for index, duration_ms in enumerate(durations_ms):
        started_at = _NOW + timedelta(seconds=index)
        samples.append(
            io.HostingIOTimingSample(
                sample_id=io.HostingIOTimingSampleId(_uuid(suffix + index)),
                account_id=_ACCOUNT,
                runtime_ref=_RUNTIME,
                boundary=boundary,
                started_checkpoint=started_checkpoint,
                ended_checkpoint=ended_checkpoint,
                started_at=started_at,
                ended_at=started_at + timedelta(milliseconds=duration_ms),
                evidence_ref=lab.HostingReliabilityEvidenceReference(
                    _uuid(suffix + 100 + index)
                ),
            )
        )
    return tuple(samples)


def _baseline(
    boundary: lab.HostingReliabilityBoundary,
    *,
    suffix: int,
) -> latency.HostingLatencyBaseline:
    return latency.HostingLatencyBaseline(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        boundary=boundary,
        reference_p50=_duration(20),
        reference_p95=_duration(30),
        reference_p99=_duration(40),
        certified_at=_NOW - timedelta(minutes=5),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix)),
    )


def _envelope_policy(*, suffix: int) -> latency.HostingLatencyEnvelopePolicy:
    return latency.HostingLatencyEnvelopePolicy(
        policy_ref=lab.HostingReliabilityPolicyReference(_uuid(suffix)),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(suffix + 1)),
        absolute_warning=_duration(60),
        absolute_degraded=_duration(120),
        catastrophic_hard_ceiling=_duration(300),
        relative_warning_basis_points=15_000,
        relative_degraded_basis_points=25_000,
        contain_on_degraded=True,
        effective_at=_NOW - timedelta(minutes=5),
        expires_at=None,
    )


def _lab_policy(*, suffix: int) -> lab.HostingReliabilityPolicySnapshot:
    return lab.HostingReliabilityPolicySnapshot(
        policy_ref=lab.HostingReliabilityPolicyReference(_uuid(suffix)),
        version=1,
        allowed_actions=(
            lab.HostingReliabilityInfrastructureAction.NO_ACTION,
            lab.HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        ),
        effective_at=_NOW - timedelta(minutes=5),
        expires_at=None,
    )


def _certificate(
    boundary: lab.HostingReliabilityBoundary,
    durations_ms: tuple[int, ...],
    *,
    suffix: int,
) -> io.HostingIOPathCertificate:
    certified = io.certify_hosting_io_path(
        _samples(boundary, durations_ms, suffix=suffix),
        _baseline(boundary, suffix=suffix + 200),
        _envelope_policy(suffix=suffix + 300),
        _lab_policy(suffix=suffix + 400),
        distribution_evidence_ref=lab.HostingReliabilityEvidenceReference(
            _uuid(suffix + 500)
        ),
        observation_id=lab.HostingReliabilityObservationId(_uuid(suffix + 501)),
        assessment_id=lab.HostingReliabilityAssessmentId(_uuid(suffix + 502)),
        certificate_id=io.HostingIOCertificateId(_uuid(suffix + 503)),
        certificate_evidence_ref=lab.HostingReliabilityEvidenceReference(
            _uuid(suffix + 504)
        ),
        evaluated_at=_NOW + timedelta(seconds=len(durations_ms) + 1),
        issued_at=_NOW + timedelta(seconds=len(durations_ms) + 2),
    )
    assert isinstance(certified, result.Success)
    return certified.value


def test_timing_sample_preserves_canonical_checkpoint_pair_and_exact_duration() -> None:
    sample = _samples(
        lab.HostingReliabilityBoundary.NETWORK_INGRESS,
        (17,),
        suffix=10,
    )[0]

    assert sample.started_checkpoint is io.HostingIOCheckpoint.PROVIDER_EVENT
    assert sample.ended_checkpoint is io.HostingIOCheckpoint.HOSTING_INGRESS
    assert sample.duration == _duration(17)


def test_wrong_checkpoint_pair_is_rejected() -> None:
    with pytest.raises(io.HostingIOCertificationValidationError):
        io.HostingIOTimingSample(
            sample_id=io.HostingIOTimingSampleId(_uuid(20)),
            account_id=_ACCOUNT,
            runtime_ref=_RUNTIME,
            boundary=lab.HostingReliabilityBoundary.NETWORK_INGRESS,
            started_checkpoint=io.HostingIOCheckpoint.CORE_DECISION,
            ended_checkpoint=io.HostingIOCheckpoint.ADAPTER_RECEIVE,
            started_at=_NOW,
            ended_at=_NOW + timedelta(milliseconds=5),
            evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(21)),
        )


def test_distribution_is_deterministic_nearest_rank_and_preserves_spikes() -> None:
    built = io.build_hosting_io_distribution(
        _samples(
            lab.HostingReliabilityBoundary.NETWORK_EGRESS,
            (10, 20, 30, 80),
            suffix=30,
        ),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(40)),
    )

    assert isinstance(built, result.Success)
    assert built.value.sample_count == 4
    assert built.value.minimum == _duration(10)
    assert built.value.p50 == _duration(20)
    assert built.value.p95 == _duration(80)
    assert built.value.p99 == _duration(80)
    assert built.value.maximum == _duration(80)
    assert built.value.jitter == _duration(50)


def test_each_io_path_is_certified_independently() -> None:
    for index, boundary in enumerate(
        (
            lab.HostingReliabilityBoundary.NETWORK_INGRESS,
            lab.HostingReliabilityBoundary.INTERNAL_PIPELINE,
            lab.HostingReliabilityBoundary.NETWORK_EGRESS,
            lab.HostingReliabilityBoundary.ROUND_TRIP,
        )
    ):
        certificate = _certificate(boundary, (10, 20, 30), suffix=1000 + index * 1000)
        assert certificate.boundary is boundary
        assert certificate.status is io.HostingIOCertificateStatus.CERTIFIED


def test_degraded_egress_does_not_invalidate_ingress_measurement_but_report_fails() -> None:
    ingress = _certificate(
        lab.HostingReliabilityBoundary.NETWORK_INGRESS,
        (10, 15, 20),
        suffix=6000,
    )
    internal = _certificate(
        lab.HostingReliabilityBoundary.INTERNAL_PIPELINE,
        (10, 20, 25),
        suffix=7000,
    )
    egress = _certificate(
        lab.HostingReliabilityBoundary.NETWORK_EGRESS,
        (130, 150, 180),
        suffix=8000,
    )

    assert ingress.status is io.HostingIOCertificateStatus.CERTIFIED
    assert egress.status is io.HostingIOCertificateStatus.NOT_CERTIFIED
    assert egress.latency_assessment.state is latency.HostingLatencyEnvelopeState.DEGRADED

    report = io.HostingIOPeriodicReliabilityReport(
        report_id=io.HostingIOReportId(_uuid(9000)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        certificates=(ingress, internal, egress),
        window_started_at=_NOW,
        window_ended_at=_NOW + timedelta(seconds=4),
        reported_at=_NOW + timedelta(seconds=6),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(9001)),
    )
    assert report.overall_status is io.HostingIOCertificateStatus.NOT_CERTIFIED
    assert report.certificate_for(
        lab.HostingReliabilityBoundary.NETWORK_INGRESS
    ) is ingress
    assert report.certificate_for(
        lab.HostingReliabilityBoundary.NETWORK_EGRESS
    ) is egress


def test_periodic_report_requires_ingress_internal_and_egress_separately() -> None:
    ingress = _certificate(
        lab.HostingReliabilityBoundary.NETWORK_INGRESS,
        (10, 15, 20),
        suffix=10000,
    )
    egress = _certificate(
        lab.HostingReliabilityBoundary.NETWORK_EGRESS,
        (10, 15, 20),
        suffix=11000,
    )

    with pytest.raises(io.HostingIOCertificationValidationError):
        io.HostingIOPeriodicReliabilityReport(
            report_id=io.HostingIOReportId(_uuid(12000)),
            account_id=_ACCOUNT,
            runtime_ref=_RUNTIME,
            certificates=(ingress, egress),
            window_started_at=_NOW,
            window_ended_at=_NOW + timedelta(seconds=4),
            reported_at=_NOW + timedelta(seconds=6),
            evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(12001)),
        )


def test_round_trip_is_optional_when_no_external_ack_exists() -> None:
    report = io.HostingIOPeriodicReliabilityReport(
        report_id=io.HostingIOReportId(_uuid(13000)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        certificates=(
            _certificate(
                lab.HostingReliabilityBoundary.NETWORK_INGRESS,
                (10, 15, 20),
                suffix=14000,
            ),
            _certificate(
                lab.HostingReliabilityBoundary.INTERNAL_PIPELINE,
                (10, 15, 20),
                suffix=15000,
            ),
            _certificate(
                lab.HostingReliabilityBoundary.NETWORK_EGRESS,
                (10, 15, 20),
                suffix=16000,
            ),
        ),
        window_started_at=_NOW,
        window_ended_at=_NOW + timedelta(seconds=4),
        reported_at=_NOW + timedelta(seconds=6),
        evidence_ref=lab.HostingReliabilityEvidenceReference(_uuid(17000)),
    )

    assert report.overall_status is io.HostingIOCertificateStatus.CERTIFIED
    assert report.certificate_for(lab.HostingReliabilityBoundary.ROUND_TRIP) is None


def test_certification_exposes_no_provider_trading_or_failover_authority() -> None:
    prohibited = {
        "acquire_lease",
        "buy",
        "core_decision",
        "failover",
        "provider_sdk",
        "redispatch",
        "retry_order",
        "sell",
        "submit_order",
        "switch_server",
    }
    for surface in (
        io.HostingIOTimingSample,
        io.HostingIOPathCertificate,
        io.HostingIOPeriodicReliabilityReport,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
