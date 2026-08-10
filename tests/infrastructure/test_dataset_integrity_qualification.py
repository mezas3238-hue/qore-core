from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure.dataset_integrity_qualification as qualification
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetManifest,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
    HistoricalOhlcReplayDataset,
    build_historical_ohlc_replay_dataset,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.hosting_latency_safety import HostingLatencyDuration
from qore.infrastructure.hosting_reliability_lab import (
    HostingReliabilityEvidenceReference,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.market_data_integrity import (
    MarketDataIngressRecord,
    MarketDataIntegrityAssessmentId,
    MarketDataIntegrityCertificate,
    MarketDataIntegrityCertificateId,
    MarketDataIntegrityError,
    MarketDataIntegrityPolicy,
    MarketDataIntegrityValidationError,
    evaluate_market_data_integrity,
    issue_market_data_integrity_certificate,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunEvidence,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.kernel.result import Failure, Result, Success

_BASE = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
_TIMEFRAME = Timeframe(60)
_INSTRUMENT = Instrument("EURUSD")
_POLICY = MarketDataIntegrityPolicy(
    max_delivery_delay=HostingLatencyDuration.from_milliseconds(2_000)
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"7a000000-0000-0000-0000-{suffix:012d}")


def _source(suffix: int) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(10_000 + suffix)),
        source_id=SourceId(_uuid(20_000 + suffix)),
        port_name=PortName(f"market-data.integrity-qualification-{suffix}"),
    )


def _snapshot(
    index: int,
    *,
    suffix: int,
    source: ExternalSourceDescriptor,
) -> OhlcSnapshot:
    opened_at = _BASE + timedelta(minutes=index)
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(30_000 + suffix)),
        instrument=_INSTRUMENT,
        source=source,
        timeframe=_TIMEFRAME,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )


def _record(
    snapshot: OhlcSnapshot,
    *,
    suffix: int,
    ingress_delay: timedelta = timedelta(milliseconds=100),
) -> MarketDataIngressRecord:
    hosting_received_at = snapshot.closed_at + ingress_delay
    return MarketDataIngressRecord(
        snapshot=snapshot,
        hosting_received_at=hosting_received_at,
        core_ingress_at=hosting_received_at + timedelta(milliseconds=1),
        normalization_evidence_ref=HostingReliabilityEvidenceReference(
            _uuid(40_000 + suffix)
        ),
    )


def _certificate(
    record: MarketDataIngressRecord,
    history: tuple[MarketDataIngressRecord, ...],
    *,
    suffix: int,
    policy: MarketDataIntegrityPolicy = _POLICY,
) -> MarketDataIntegrityCertificate:
    assessed = evaluate_market_data_integrity(
        record=record,
        accepted_history=history,
        policy=policy,
        assessment_id=MarketDataIntegrityAssessmentId(_uuid(50_000 + suffix)),
        assessed_at=record.core_ingress_at + timedelta(milliseconds=1),
    )
    assert isinstance(assessed, Success)
    issued = issue_market_data_integrity_certificate(
        assessed.value,
        certificate_id=MarketDataIntegrityCertificateId(_uuid(60_000 + suffix)),
        issued_at=assessed.value.assessed_at + timedelta(milliseconds=1),
        evidence_ref=HostingReliabilityEvidenceReference(_uuid(70_000 + suffix)),
    )
    assert isinstance(issued, Success)
    return issued.value


def _observation(
    snapshot: OhlcSnapshot,
    *,
    suffix: int,
    visibility_delay: timedelta,
) -> ReplayMarketDataObservation:
    return ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(80_000 + suffix)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at + visibility_delay,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            _uuid(90_000 + suffix)
        ),
    )


def _dataset(
    *,
    suffix: int = 1,
    delayed_first_visibility: bool = True,
) -> tuple[
    HistoricalOhlcReplayDataset,
    tuple[MarketDataIntegrityCertificate, MarketDataIntegrityCertificate],
]:
    source = _source(suffix)
    first_snapshot = _snapshot(0, suffix=suffix * 10 + 1, source=source)
    second_snapshot = _snapshot(1, suffix=suffix * 10 + 2, source=source)
    first_record = _record(first_snapshot, suffix=suffix * 10 + 1)
    second_record = _record(second_snapshot, suffix=suffix * 10 + 2)
    first_certificate = _certificate(
        first_record,
        (),
        suffix=suffix * 10 + 1,
    )
    second_certificate = _certificate(
        second_record,
        (first_record,),
        suffix=suffix * 10 + 2,
    )
    first_delay = (
        timedelta(minutes=10)
        if delayed_first_visibility
        else timedelta(milliseconds=200)
    )
    first_observation = _observation(
        first_snapshot,
        suffix=suffix * 10 + 1,
        visibility_delay=first_delay,
    )
    second_observation = _observation(
        second_snapshot,
        suffix=suffix * 10 + 2,
        visibility_delay=timedelta(milliseconds=200),
    )
    scope = HistoricalOhlcDatasetScope(
        source=source,
        window=HistoricalOhlcWindow(
            instrument=_INSTRUMENT,
            timeframe=_TIMEFRAME,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=2),
        ),
    )
    built = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(100_000 + suffix)),
        revision_id=HistoricalDatasetRevisionId(_uuid(110_000 + suffix)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion(
            "canonical-ingestion-v1"
        ),
        observations=(first_observation, second_observation),
    )
    assert isinstance(built, Success)
    return built.value, (first_certificate, second_certificate)


def _run(
    manifests: tuple[HistoricalDatasetManifest, ...],
    *,
    suffix: int = 1,
) -> ResearchRunEvidence:
    built = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(120_000 + suffix)),
        created_at=_BASE + timedelta(days=2),
        datasets=manifests,
        replay_policy_version=ResearchReplayPolicyVersion("replay-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=2),
        strategy_configuration_id=ResearchStrategyConfigurationId(
            _uuid(130_000 + suffix)
        ),
        software_revision=ResearchSoftwareRevision("test-revision-1"),
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def test_pairing_uses_chronological_snapshot_identity_not_replay_position() -> None:
    dataset, certificates = _dataset()
    first_payload = dataset.observations[0].payload
    second_payload = dataset.observations[1].payload
    assert isinstance(first_payload, OhlcSnapshot)
    assert isinstance(second_payload, OhlcSnapshot)
    assert first_payload.opened_at > second_payload.opened_at

    built = qualification.build_dataset_integrity_qualification(
        dataset=dataset,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=certificates,
    )

    assert isinstance(built, Success)
    assert built.value.certificates == certificates


def test_wrong_certificate_per_chronological_snapshot_fails() -> None:
    dataset, certificates = _dataset()

    built = qualification.build_dataset_integrity_qualification(
        dataset=dataset,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=tuple(reversed(certificates)),
    )

    assert isinstance(built, Failure)
    assert isinstance(
        built.error,
        qualification.DatasetIntegrityQualificationValidationError,
    )


def test_t2_operates_on_exact_snapshot_pair() -> None:
    source = _source(9)
    snapshot = _snapshot(0, suffix=91, source=source)
    record = _record(
        snapshot,
        suffix=91,
        ingress_delay=timedelta(seconds=1),
    )
    certificate = _certificate(record, (), suffix=91)
    observation = _observation(
        snapshot,
        suffix=91,
        visibility_delay=timedelta(milliseconds=500),
    )
    scope = HistoricalOhlcDatasetScope(
        source=source,
        window=HistoricalOhlcWindow(
            instrument=_INSTRUMENT,
            timeframe=_TIMEFRAME,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=1),
        ),
    )
    dataset_result = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(200_001)),
        revision_id=HistoricalDatasetRevisionId(_uuid(200_002)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion(
            "canonical-ingestion-v1"
        ),
        observations=(observation,),
    )
    assert isinstance(dataset_result, Success)

    built = qualification.build_dataset_integrity_qualification(
        dataset=dataset_result.value,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=(certificate,),
    )

    assert isinstance(built, Failure)
    assert "T2 violation" in str(built.error)


def test_two_policy_ambiguity_is_revalidation_not_issuance_provenance() -> None:
    dataset, certificates = _dataset(delayed_first_visibility=False)
    wider_policy = MarketDataIntegrityPolicy(
        max_delivery_delay=HostingLatencyDuration.from_milliseconds(5_000)
    )

    under_original = qualification.build_dataset_integrity_qualification(
        dataset=dataset,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=certificates,
    )
    under_wider = qualification.build_dataset_integrity_qualification(
        dataset=dataset,
        qualification_policy=wider_policy,
        predecessor_certificate=None,
        certificates=certificates,
    )

    assert isinstance(under_original, Success)
    assert isinstance(under_wider, Success)
    assert under_original.value.fingerprint != under_wider.value.fingerprint


def test_predecessor_is_bounded_anchor_and_is_required_for_non_root_assessment() -> None:
    source = _source(12)
    predecessor_snapshot = _snapshot(-1, suffix=121, source=source)
    current_snapshot = _snapshot(0, suffix=122, source=source)
    predecessor_record = _record(predecessor_snapshot, suffix=121)
    current_record = _record(current_snapshot, suffix=122)
    predecessor_certificate = _certificate(
        predecessor_record,
        (),
        suffix=121,
    )
    current_certificate = _certificate(
        current_record,
        (predecessor_record,),
        suffix=122,
    )
    observation = _observation(
        current_snapshot,
        suffix=122,
        visibility_delay=timedelta(milliseconds=200),
    )
    scope = HistoricalOhlcDatasetScope(
        source=source,
        window=HistoricalOhlcWindow(
            instrument=_INSTRUMENT,
            timeframe=_TIMEFRAME,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=1),
        ),
    )
    dataset_result = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(210_001)),
        revision_id=HistoricalDatasetRevisionId(_uuid(210_002)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion(
            "canonical-ingestion-v1"
        ),
        observations=(observation,),
    )
    assert isinstance(dataset_result, Success)

    missing_anchor = qualification.build_dataset_integrity_qualification(
        dataset=dataset_result.value,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=(current_certificate,),
    )
    anchored = qualification.build_dataset_integrity_qualification(
        dataset=dataset_result.value,
        qualification_policy=_POLICY,
        predecessor_certificate=predecessor_certificate,
        certificates=(current_certificate,),
    )

    assert isinstance(missing_anchor, Failure)
    assert isinstance(anchored, Success)


def test_projectors_use_exact_primitives_microseconds_uuid_and_float_hex() -> None:
    dataset, certificates = _dataset(delayed_first_visibility=False)
    observation = dataset.observations[0]
    assert isinstance(observation.payload, OhlcSnapshot)
    projected_observation = qualification._canonical_replay_observation(observation)
    projected_manifest = qualification._canonical_dataset_manifest(dataset.manifest)
    projected_certificate = qualification._canonical_integrity_certificate(
        certificates[0]
    )
    payload_projection = cast(
        dict[str, object],
        projected_observation["payload"],
    )
    available_at = cast(str, projected_observation["available_at"])
    scope_projection = cast(dict[str, object], projected_manifest["scope"])
    window_projection = cast(dict[str, object], scope_projection["window"])
    assessment_projection = cast(
        dict[str, object],
        projected_certificate["assessment"],
    )
    record_projection = cast(
        dict[str, object],
        assessment_projection["record"],
    )

    assert payload_projection["open"] == observation.payload.open.hex()
    assert projected_observation["observation_id"] == str(observation.observation_id.value)
    assert available_at.endswith("+00:00")
    assert "." in available_at
    assert len(projected_manifest) == 14
    assert window_projection["interval_count"] == 2
    assert record_projection["delivery_delay_microseconds"] == (
        certificates[0].assessment.record.delivery_delay.microseconds
    )


def test_exact_certificate_envelope_mutation_changes_fingerprint() -> None:
    dataset, certificates = _dataset(delayed_first_visibility=False)
    baseline = qualification.build_dataset_integrity_qualification(
        dataset=dataset,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=certificates,
    )
    assert isinstance(baseline, Success)

    first = certificates[0]
    changed_certificate = MarketDataIntegrityCertificate(
        certificate_id=MarketDataIntegrityCertificateId(_uuid(220_001)),
        status=first.status,
        assessment=first.assessment,
        issued_at=first.issued_at,
        evidence_ref=first.evidence_ref,
    )
    changed = qualification.build_dataset_integrity_qualification(
        dataset=dataset,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=(changed_certificate, certificates[1]),
    )

    assert isinstance(changed, Success)
    assert baseline.value.fingerprint != changed.value.fingerprint


def test_direct_constructor_rejects_wrong_fingerprint() -> None:
    dataset, certificates = _dataset(delayed_first_visibility=False)
    built = qualification.build_dataset_integrity_qualification(
        dataset=dataset,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=certificates,
    )
    assert isinstance(built, Success)

    with pytest.raises(
        qualification.DatasetIntegrityQualificationValidationError,
        match="fingerprint mismatch",
    ):
        qualification.DatasetIntegrityQualification(
            dataset=dataset,
            qualification_policy=_POLICY,
            predecessor_certificate=None,
            certificates=certificates,
            fingerprint=qualification.DatasetIntegrityQualificationFingerprint(
                "0" * 64
            ),
        )


def test_evaluator_failure_is_translated_to_qualification_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, certificates = _dataset(delayed_first_visibility=False)

    def _failure(**_: object) -> Result[object, MarketDataIntegrityError]:
        return Failure(MarketDataIntegrityValidationError("forced failure"))

    monkeypatch.setattr(
        qualification,
        "evaluate_market_data_integrity",
        _failure,
    )
    built = qualification.build_dataset_integrity_qualification(
        dataset=dataset,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=certificates,
    )

    assert isinstance(built, Failure)
    assert isinstance(
        built.error,
        qualification.DatasetIntegrityQualificationValidationError,
    )
    assert "assessment reproduction failed" in str(built.error)


def test_integrity_qualified_run_requires_exact_run_order_bijection() -> None:
    dataset_a, certificates_a = _dataset(
        suffix=21,
        delayed_first_visibility=False,
    )
    dataset_b, certificates_b = _dataset(
        suffix=22,
        delayed_first_visibility=False,
    )
    qual_a = qualification.build_dataset_integrity_qualification(
        dataset=dataset_a,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=certificates_a,
    )
    qual_b = qualification.build_dataset_integrity_qualification(
        dataset=dataset_b,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=certificates_b,
    )
    assert isinstance(qual_a, Success)
    assert isinstance(qual_b, Success)
    run = _run((dataset_a.manifest, dataset_b.manifest), suffix=22)

    ordered = tuple(
        qual_a.value
        if manifest == dataset_a.manifest
        else qual_b.value
        for manifest in run.datasets
    )
    built = qualification.build_integrity_qualified_research_run(
        run=run,
        qualifications=ordered,
    )
    reversed_built = qualification.build_integrity_qualified_research_run(
        run=run,
        qualifications=tuple(reversed(ordered)),
    )

    assert isinstance(built, Success)
    assert isinstance(reversed_built, Failure)


def test_run_wrapper_fingerprint_binds_exact_run_identity() -> None:
    dataset, certificates = _dataset(suffix=31, delayed_first_visibility=False)
    qualified = qualification.build_dataset_integrity_qualification(
        dataset=dataset,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=certificates,
    )
    assert isinstance(qualified, Success)
    run_a = _run((dataset.manifest,), suffix=31)
    run_b = _run((dataset.manifest,), suffix=32)
    wrapped_a = qualification.build_integrity_qualified_research_run(
        run=run_a,
        qualifications=(qualified.value,),
    )
    wrapped_b = qualification.build_integrity_qualified_research_run(
        run=run_b,
        qualifications=(qualified.value,),
    )

    assert isinstance(wrapped_a, Success)
    assert isinstance(wrapped_b, Success)
    assert wrapped_a.value.fingerprint != wrapped_b.value.fingerprint


def test_objects_expose_no_trading_execution_risk_or_capital_authority() -> None:
    forbidden = {
        "allocate_capital",
        "buy",
        "dispatch",
        "execute",
        "place_order",
        "publish",
        "sell",
        "submit_order",
    }
    for surface in (
        qualification.DatasetIntegrityQualification,
        qualification.IntegrityQualifiedResearchRun,
    ):
        assert forbidden.isdisjoint(set(dir(surface)))
