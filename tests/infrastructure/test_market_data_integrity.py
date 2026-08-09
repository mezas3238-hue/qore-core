from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.market_data as market_data
import qore.infrastructure.market_data_integrity as integrity
import qore.infrastructure.ports as ports
from qore.infrastructure.hosting_latency_safety import HostingLatencyDuration
from qore.infrastructure.hosting_reliability_lab import (
    HostingReliabilityEvidenceReference,
)
import qore.kernel.result as result

_T0 = datetime(2026, 8, 10, 6, 0, tzinfo=UTC)
_INSTRUMENT = market_data.Instrument("ESZ6")
_TIMEFRAME = market_data.Timeframe(60)
_SOURCE = ports.ExternalSourceDescriptor(
    adapter_id=ports.AdapterId(UUID("58000000-0000-0000-0000-000000000001")),
    source_id=ports.SourceId(UUID("58000000-0000-0000-0000-000000000002")),
    port_name=ports.PortName("market-data.futures-test"),
)
_OTHER_SOURCE = ports.ExternalSourceDescriptor(
    adapter_id=ports.AdapterId(UUID("58000000-0000-0000-0000-000000000003")),
    source_id=ports.SourceId(UUID("58000000-0000-0000-0000-000000000004")),
    port_name=ports.PortName("market-data.other-test"),
)
_POLICY = integrity.MarketDataIntegrityPolicy(
    max_delivery_delay=HostingLatencyDuration.from_milliseconds(2_000)
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"58000000-0000-0000-0000-{suffix:012d}")


def _snapshot(
    index: int,
    *,
    suffix: int,
    source: ports.ExternalSourceDescriptor = _SOURCE,
    close: float = 5001.0,
) -> market_data.OhlcSnapshot:
    opened_at = _T0 + timedelta(minutes=index)
    return market_data.OhlcSnapshot(
        snapshot_id=market_data.MarketDataSnapshotId(_uuid(suffix)),
        instrument=_INSTRUMENT,
        source=source,
        timeframe=_TIMEFRAME,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=5000.0,
        high=5005.0,
        low=4995.0,
        close=close,
    )


def _record(
    index: int,
    *,
    suffix: int,
    delay_ms: int = 500,
    source: ports.ExternalSourceDescriptor = _SOURCE,
    close: float = 5001.0,
) -> integrity.MarketDataIngressRecord:
    snapshot = _snapshot(index, suffix=suffix, source=source, close=close)
    hosting_received_at = snapshot.closed_at + timedelta(milliseconds=delay_ms)
    return integrity.MarketDataIngressRecord(
        snapshot=snapshot,
        hosting_received_at=hosting_received_at,
        core_ingress_at=hosting_received_at + timedelta(milliseconds=2),
        normalization_evidence_ref=HostingReliabilityEvidenceReference(
            _uuid(suffix + 10_000)
        ),
    )


def _assess(
    record: integrity.MarketDataIngressRecord,
    history: tuple[integrity.MarketDataIngressRecord, ...],
    *,
    suffix: int,
) -> integrity.MarketDataIntegrityAssessment:
    assessed = integrity.evaluate_market_data_integrity(
        record,
        history,
        _POLICY,
        assessment_id=integrity.MarketDataIntegrityAssessmentId(_uuid(suffix)),
        assessed_at=record.core_ingress_at + timedelta(milliseconds=1),
    )
    assert isinstance(assessed, result.Success)
    return assessed.value


def test_canonical_bar_preserves_source_normalization_and_core_ingress_evidence() -> None:
    record = _record(0, suffix=10)

    assert record.snapshot.instrument == _INSTRUMENT
    assert record.snapshot.timeframe == _TIMEFRAME
    assert record.snapshot.source == _SOURCE
    assert record.delivery_delay == HostingLatencyDuration.from_milliseconds(500)
    assert record.core_ingress_at > record.hosting_received_at
    assert record.normalization_evidence_ref == HostingReliabilityEvidenceReference(
        _uuid(10_010)
    )


def test_valid_contiguous_bar_is_certified_and_eligible_for_core_use() -> None:
    previous = _record(0, suffix=20)
    candidate = _record(1, suffix=21)
    assessment = _assess(candidate, (previous,), suffix=22)

    assert assessment.state is integrity.MarketDataIntegrityState.VALID
    assert assessment.disposition is integrity.MarketDataIntegrityDisposition.ACCEPT
    assert assessment.allows_core_ingress is True
    assert assessment.expected_opened_at == previous.snapshot.closed_at

    issued = integrity.issue_market_data_integrity_certificate(
        assessment,
        certificate_id=integrity.MarketDataIntegrityCertificateId(_uuid(23)),
        issued_at=assessment.assessed_at + timedelta(milliseconds=1),
        evidence_ref=HostingReliabilityEvidenceReference(_uuid(24)),
    )
    assert isinstance(issued, result.Success)
    assert issued.value.status is (
        integrity.MarketDataIntegrityCertificateStatus.CERTIFIED
    )


def test_delayed_bar_is_degraded_not_certified_and_not_silently_accepted() -> None:
    previous = _record(0, suffix=30)
    delayed = _record(1, suffix=31, delay_ms=3_000)
    assessment = _assess(delayed, (previous,), suffix=32)

    assert assessment.state is integrity.MarketDataIntegrityState.DELAYED
    assert assessment.disposition is integrity.MarketDataIntegrityDisposition.DEGRADE
    assert assessment.allows_core_ingress is False

    issued = integrity.issue_market_data_integrity_certificate(
        assessment,
        certificate_id=integrity.MarketDataIntegrityCertificateId(_uuid(33)),
        issued_at=assessment.assessed_at + timedelta(milliseconds=1),
        evidence_ref=HostingReliabilityEvidenceReference(_uuid(34)),
    )
    assert isinstance(issued, result.Success)
    assert issued.value.status is (
        integrity.MarketDataIntegrityCertificateStatus.NOT_CERTIFIED
    )


def test_gap_is_detected_against_exact_expected_next_open() -> None:
    previous = _record(0, suffix=40)
    gapped = _record(2, suffix=41)
    assessment = _assess(gapped, (previous,), suffix=42)

    assert assessment.state is integrity.MarketDataIntegrityState.GAP_DETECTED
    assert assessment.disposition is integrity.MarketDataIntegrityDisposition.DEGRADE
    assert assessment.expected_opened_at == _T0 + timedelta(minutes=1)
    assert assessment.record.snapshot.opened_at == _T0 + timedelta(minutes=2)
    assert assessment.allows_core_ingress is False


def test_exact_semantic_duplicate_is_quarantined_not_redistributed() -> None:
    previous = _record(0, suffix=50)
    duplicate = _record(0, suffix=51)
    assessment = _assess(duplicate, (previous,), suffix=52)

    assert assessment.state is integrity.MarketDataIntegrityState.DUPLICATE
    assert assessment.disposition is integrity.MarketDataIntegrityDisposition.QUARANTINE
    assert assessment.allows_core_ingress is False

    quarantined = integrity.quarantine_market_data_assessment(
        assessment,
        quarantine_id=integrity.MarketDataQuarantineId(_uuid(53)),
        quarantined_at=assessment.assessed_at + timedelta(milliseconds=1),
        evidence_ref=HostingReliabilityEvidenceReference(_uuid(54)),
    )
    assert isinstance(quarantined, result.Success)
    assert quarantined.value.state is integrity.MarketDataIntegrityState.QUARANTINED
    assert quarantined.value.origin_state is integrity.MarketDataIntegrityState.DUPLICATE
    assert quarantined.value.snapshot == duplicate.snapshot


def test_conflicting_values_for_same_interval_are_corrupted_and_quarantined() -> None:
    previous = _record(0, suffix=60, close=5001.0)
    conflicting = _record(0, suffix=61, close=5003.0)
    assessment = _assess(conflicting, (previous,), suffix=62)

    assert assessment.state is integrity.MarketDataIntegrityState.CORRUPTED
    assert assessment.disposition is integrity.MarketDataIntegrityDisposition.QUARANTINE
    assert assessment.rationale_code == integrity.MarketDataIntegrityRationaleCode(
        "market_data.conflicting_interval"
    )


def test_out_of_order_bar_is_quarantined() -> None:
    first = _record(0, suffix=70)
    second = _record(1, suffix=71)
    older = _record(0, suffix=72)
    assessment = _assess(older, (first, second), suffix=73)

    assert assessment.state is integrity.MarketDataIntegrityState.OUT_OF_ORDER
    assert assessment.disposition is integrity.MarketDataIntegrityDisposition.QUARANTINE
    assert assessment.previous_snapshot_id == second.snapshot.snapshot_id


def test_history_must_be_one_source_instrument_timeframe_and_contiguous() -> None:
    candidate = _record(2, suffix=80)
    other_source = _record(0, suffix=81, source=_OTHER_SOURCE)

    rejected_source = integrity.evaluate_market_data_integrity(
        candidate,
        (other_source,),
        _POLICY,
        assessment_id=integrity.MarketDataIntegrityAssessmentId(_uuid(82)),
        assessed_at=candidate.core_ingress_at + timedelta(milliseconds=1),
    )
    assert isinstance(rejected_source, result.Failure)
    assert isinstance(
        rejected_source.error,
        integrity.MarketDataIntegrityValidationError,
    )

    first = _record(0, suffix=83)
    third = _record(2, suffix=84)
    rejected_gap_history = integrity.evaluate_market_data_integrity(
        candidate,
        (first, third),
        _POLICY,
        assessment_id=integrity.MarketDataIntegrityAssessmentId(_uuid(85)),
        assessed_at=candidate.core_ingress_at + timedelta(milliseconds=1),
    )
    assert isinstance(rejected_gap_history, result.Failure)


def test_canonical_ohlc_invariants_are_reused_not_duplicated() -> None:
    with pytest.raises(market_data.MarketDataValidationError):
        market_data.OhlcSnapshot(
            snapshot_id=market_data.MarketDataSnapshotId(_uuid(90)),
            instrument=_INSTRUMENT,
            source=_SOURCE,
            timeframe=_TIMEFRAME,
            opened_at=_T0,
            closed_at=_T0 + timedelta(minutes=1),
            open=5000.0,
            high=4990.0,
            low=4995.0,
            close=5001.0,
        )


def test_closed_bar_cannot_claim_arrival_before_close_or_core_before_hosting() -> None:
    snapshot = _snapshot(0, suffix=100)

    with pytest.raises(integrity.MarketDataIntegrityValidationError):
        integrity.MarketDataIngressRecord(
            snapshot=snapshot,
            hosting_received_at=snapshot.closed_at - timedelta(milliseconds=1),
            core_ingress_at=snapshot.closed_at,
            normalization_evidence_ref=HostingReliabilityEvidenceReference(_uuid(101)),
        )

    with pytest.raises(integrity.MarketDataIntegrityValidationError):
        integrity.MarketDataIngressRecord(
            snapshot=snapshot,
            hosting_received_at=snapshot.closed_at,
            core_ingress_at=snapshot.closed_at - timedelta(milliseconds=1),
            normalization_evidence_ref=HostingReliabilityEvidenceReference(_uuid(102)),
        )


def test_valid_or_degraded_assessment_cannot_be_falsely_quarantined() -> None:
    assessment = _assess(_record(0, suffix=110), (), suffix=111)

    rejected = integrity.quarantine_market_data_assessment(
        assessment,
        quarantine_id=integrity.MarketDataQuarantineId(_uuid(112)),
        quarantined_at=assessment.assessed_at + timedelta(milliseconds=1),
        evidence_ref=HostingReliabilityEvidenceReference(_uuid(113)),
    )
    assert isinstance(rejected, result.Failure)
    assert isinstance(rejected.error, integrity.MarketDataIntegrityQuarantineError)


def test_quarantine_preserves_original_snapshot_without_repair_or_rewrite() -> None:
    previous = _record(0, suffix=120, close=5001.0)
    conflicting = _record(0, suffix=121, close=5004.0)
    assessment = _assess(conflicting, (previous,), suffix=122)
    before = conflicting.snapshot.logical_values()

    quarantined = integrity.quarantine_market_data_assessment(
        assessment,
        quarantine_id=integrity.MarketDataQuarantineId(_uuid(123)),
        quarantined_at=assessment.assessed_at + timedelta(milliseconds=1),
        evidence_ref=HostingReliabilityEvidenceReference(_uuid(124)),
    )
    assert isinstance(quarantined, result.Success)
    assert quarantined.value.snapshot.logical_values() == before
    assert not hasattr(quarantined.value, "replacement_snapshot")
    assert not hasattr(quarantined.value, "repair")


def test_integrity_contracts_expose_no_trading_provider_or_failover_authority() -> None:
    states = {state.value for state in integrity.MarketDataIntegrityState}
    assert states == {
        "valid",
        "delayed",
        "gap_detected",
        "duplicate",
        "out_of_order",
        "corrupted",
        "quarantined",
    }

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
        integrity.MarketDataIngressRecord,
        integrity.MarketDataIntegrityAssessment,
        integrity.MarketDataIntegrityCertificate,
        integrity.MarketDataQuarantineRecord,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
