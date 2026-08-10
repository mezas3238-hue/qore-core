from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure.research_sample_partition as partition
from qore.infrastructure.dataset_integrity_qualification import (
    DatasetIntegrityQualification,
    IntegrityQualifiedResearchRun,
    build_dataset_integrity_qualification,
    build_integrity_qualified_research_run,
)
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
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
    MarketDataIntegrityPolicy,
    evaluate_market_data_integrity,
    issue_market_data_integrity_certificate,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
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
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
_TIMEFRAME = Timeframe(60)
_INSTRUMENT = Instrument("EURUSD")
_POLICY = MarketDataIntegrityPolicy(
    max_delivery_delay=HostingLatencyDuration.from_milliseconds(2_000)
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"7b000000-0000-0000-0000-{suffix:012d}")


def _source(suffix: int) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(10_000 + suffix)),
        source_id=SourceId(_uuid(20_000 + suffix)),
        port_name=PortName(f"market-data.sample-partition-{suffix}"),
    )


def _snapshot(
    *,
    start: datetime,
    suffix: int,
    source: ExternalSourceDescriptor,
    instrument: Instrument = _INSTRUMENT,
    timeframe: Timeframe = _TIMEFRAME,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(30_000 + suffix)),
        instrument=instrument,
        source=source,
        timeframe=timeframe,
        opened_at=start,
        closed_at=start + timedelta(seconds=timeframe.seconds),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )


def _record(snapshot: OhlcSnapshot, *, suffix: int) -> MarketDataIngressRecord:
    hosting_received_at = snapshot.closed_at + timedelta(milliseconds=100)
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
    *,
    suffix: int,
    policy: MarketDataIntegrityPolicy = _POLICY,
) -> MarketDataIntegrityCertificate:
    assessment = evaluate_market_data_integrity(
        record=record,
        accepted_history=(),
        policy=policy,
        assessment_id=MarketDataIntegrityAssessmentId(_uuid(50_000 + suffix)),
        assessed_at=record.core_ingress_at + timedelta(milliseconds=1),
    )
    assert isinstance(assessment, Success)
    certificate = issue_market_data_integrity_certificate(
        assessment.value,
        certificate_id=MarketDataIntegrityCertificateId(_uuid(60_000 + suffix)),
        issued_at=assessment.value.assessed_at + timedelta(milliseconds=1),
        evidence_ref=HostingReliabilityEvidenceReference(_uuid(70_000 + suffix)),
    )
    assert isinstance(certificate, Success)
    return certificate.value


def _observation(
    snapshot: OhlcSnapshot,
    record: MarketDataIngressRecord,
    *,
    suffix: int,
    availability_delay: timedelta = timedelta(milliseconds=1),
) -> ReplayMarketDataObservation:
    return ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(80_000 + suffix)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=record.core_ingress_at + availability_delay,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            _uuid(90_000 + suffix)
        ),
    )


def _qualified_run(
    *,
    suffix: int,
    start: datetime,
    source: ExternalSourceDescriptor | None = None,
    run_id: ResearchRunId | None = None,
    created_at: datetime | None = None,
    strategy_configuration_id: ResearchStrategyConfigurationId | None = None,
    qualification_policy: MarketDataIntegrityPolicy = _POLICY,
    availability_delay: timedelta = timedelta(milliseconds=1),
) -> IntegrityQualifiedResearchRun:
    source = source or _source(suffix)
    snapshot = _snapshot(start=start, suffix=suffix, source=source)
    record = _record(snapshot, suffix=suffix)
    certificate = _certificate(record, suffix=suffix)
    observation = _observation(
        snapshot,
        record,
        suffix=suffix,
        availability_delay=availability_delay,
    )
    scope = HistoricalOhlcDatasetScope(
        source=source,
        window=HistoricalOhlcWindow(
            instrument=snapshot.instrument,
            timeframe=snapshot.timeframe,
            opened_at=snapshot.opened_at,
            closed_at=snapshot.closed_at,
        ),
    )
    dataset_result = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(100_000 + suffix)),
        revision_id=HistoricalDatasetRevisionId(_uuid(110_000 + suffix)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=start + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion(
            "canonical-ingestion-v1"
        ),
        observations=(observation,),
    )
    assert isinstance(dataset_result, Success)
    qualification_result = build_dataset_integrity_qualification(
        dataset=dataset_result.value,
        qualification_policy=qualification_policy,
        predecessor_certificate=None,
        certificates=(certificate,),
    )
    assert isinstance(qualification_result, Success)
    run_result = build_research_run_evidence(
        run_id=run_id or ResearchRunId(_uuid(120_000 + suffix)),
        created_at=created_at or start + timedelta(days=2),
        datasets=(dataset_result.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("replay-v1"),
        simulated_start=start,
        simulated_end=snapshot.closed_at,
        strategy_configuration_id=(
            strategy_configuration_id
            or ResearchStrategyConfigurationId(_uuid(130_000 + suffix))
        ),
        software_revision=ResearchSoftwareRevision("test-revision-1"),
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(run_result, Success)
    qualified_result = build_integrity_qualified_research_run(
        run=run_result.value,
        qualifications=(qualification_result.value,),
    )
    assert isinstance(qualified_result, Success)
    return qualified_result.value


def _requalify(
    qualified_run: IntegrityQualifiedResearchRun,
    *,
    policy: MarketDataIntegrityPolicy,
) -> IntegrityQualifiedResearchRun:
    original = qualified_run.qualifications[0]
    qualification_result = build_dataset_integrity_qualification(
        dataset=original.dataset,
        qualification_policy=policy,
        predecessor_certificate=original.predecessor_certificate,
        certificates=original.certificates,
    )
    assert isinstance(qualification_result, Success)
    qualified_result = build_integrity_qualified_research_run(
        run=qualified_run.run,
        qualifications=(qualification_result.value,),
    )
    assert isinstance(qualified_result, Success)
    return qualified_result.value


def _rerun_same_inputs(
    qualified_run: IntegrityQualifiedResearchRun,
    *,
    suffix: int,
) -> IntegrityQualifiedResearchRun:
    old_run = qualified_run.run
    new_run_result = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(200_000 + suffix)),
        created_at=old_run.created_at + timedelta(seconds=suffix),
        datasets=old_run.datasets,
        replay_policy_version=old_run.replay_policy_version,
        simulated_start=old_run.simulated_start,
        simulated_end=old_run.simulated_end,
        strategy_configuration_id=old_run.strategy_configuration_id,
        software_revision=old_run.software_revision,
        execution_model_id=old_run.execution_model_id,
        transaction_cost_model_id=old_run.transaction_cost_model_id,
        randomness_mode=old_run.randomness_mode,
        random_seed=old_run.random_seed,
    )
    assert isinstance(new_run_result, Success)
    qualified_result = build_integrity_qualified_research_run(
        run=new_run_result.value,
        qualifications=qualified_run.qualifications,
    )
    assert isinstance(qualified_result, Success)
    return qualified_result.value


def _assignment(
    role: partition.SampleRole,
    *runs: IntegrityQualifiedResearchRun,
) -> partition.SampleRoleAssignment:
    result = partition.build_sample_role_assignment(
        role=role,
        qualified_runs=tuple(runs),
    )
    assert isinstance(result, Success)
    return result.value


def _partition(
    development: IntegrityQualifiedResearchRun,
    calibration: IntegrityQualifiedResearchRun,
    external: IntegrityQualifiedResearchRun,
) -> partition.SamplePartitionEvidence:
    result = partition.build_sample_partition_evidence(
        assignments=(
            _assignment(partition.SampleRole.DEVELOPMENT, development),
            _assignment(partition.SampleRole.CALIBRATION, calibration),
            _assignment(partition.SampleRole.EXTERNAL_VALIDATION, external),
        )
    )
    assert isinstance(result, Success)
    return result.value


def test_disjoint_partition_builds_and_disjointness_is_derived() -> None:
    evidence = _partition(
        _qualified_run(suffix=1, start=_BASE),
        _qualified_run(suffix=2, start=_BASE + timedelta(minutes=2)),
        _qualified_run(suffix=3, start=_BASE + timedelta(minutes=4)),
    )
    disjointness = partition.SamplePartitionDisjointnessEvidence(
        source_partition=evidence
    )

    assert all(
        not pair.run_overlaps
        and not pair.dataset_overlaps
        and not pair.observation_overlaps
        and not pair.market_time_overlaps
        for pair in evidence.derived_overlap_report.pairwise
    )
    assert disjointness.exact_qualified_run_disjoint
    assert disjointness.exact_run_evidence_disjoint
    assert disjointness.run_id_disjoint
    assert disjointness.run_input_fingerprint_disjoint
    assert disjointness.dataset_id_disjoint
    assert disjointness.revision_id_disjoint
    assert disjointness.evidence_digest_disjoint
    assert disjointness.observation_id_disjoint
    assert disjointness.snapshot_id_disjoint
    assert disjointness.exact_stream_market_time_disjoint
    assert disjointness.market_coordinate_time_disjoint
    assert not hasattr(disjointness, "independent")


def test_role_builder_canonicalizes_and_rejects_duplicate_exact_run() -> None:
    first = _qualified_run(suffix=10, start=_BASE)
    second = _qualified_run(suffix=11, start=_BASE + timedelta(minutes=2))
    reversed_result = partition.build_sample_role_assignment(
        role=partition.SampleRole.DEVELOPMENT,
        qualified_runs=(second, first),
    )
    duplicate_result = partition.build_sample_role_assignment(
        role=partition.SampleRole.DEVELOPMENT,
        qualified_runs=(first, first),
    )

    assert isinstance(reversed_result, Success)
    expected = tuple(sorted((first, second), key=partition._qualified_run_total_order_key))
    assert reversed_result.value.qualified_runs == expected
    assert isinstance(duplicate_result, Failure)
    assert isinstance(
        duplicate_result.error,
        partition.ResearchSamplePartitionValidationError,
    )


@pytest.mark.parametrize(
    ("role", "runs"),
    [
        ("development", ()),
        (partition.SampleRole.DEVELOPMENT, []),
        (partition.SampleRole.DEVELOPMENT, (object(),)),
    ],
)
def test_role_builder_malformed_inputs_return_failure(
    role: object,
    runs: object,
) -> None:
    result = partition.build_sample_role_assignment(
        role=cast(partition.SampleRole, role),
        qualified_runs=cast(tuple[IntegrityQualifiedResearchRun, ...], runs),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, partition.ResearchSamplePartitionValidationError)


def test_partition_builder_rejects_non_tuple_and_wrong_role_order() -> None:
    development = _assignment(
        partition.SampleRole.DEVELOPMENT,
        _qualified_run(suffix=20, start=_BASE),
    )
    calibration = _assignment(
        partition.SampleRole.CALIBRATION,
        _qualified_run(suffix=21, start=_BASE + timedelta(minutes=2)),
    )
    external = _assignment(
        partition.SampleRole.EXTERNAL_VALIDATION,
        _qualified_run(suffix=22, start=_BASE + timedelta(minutes=4)),
    )
    non_tuple = partition.build_sample_partition_evidence(
        assignments=cast(
            tuple[partition.SampleRoleAssignment, ...],
            [development, calibration, external],
        )
    )
    wrong_order = partition.build_sample_partition_evidence(
        assignments=(calibration, development, external)
    )

    assert isinstance(non_tuple, Failure)
    assert isinstance(wrong_order, Failure)


def test_exact_qualified_run_overlap_sets_all_run_axes() -> None:
    shared = _qualified_run(suffix=30, start=_BASE)
    evidence = _partition(
        shared,
        shared,
        _qualified_run(suffix=31, start=_BASE + timedelta(minutes=3)),
    )
    pair = evidence.derived_overlap_report.pairwise[0]

    assert len(pair.run_overlaps) == 1
    overlap = pair.run_overlaps[0]
    assert overlap.exact_qualified_run_equal
    assert overlap.exact_run_equal
    assert overlap.run_id_equal
    assert overlap.run_input_fingerprint_equal
    disjointness = partition.SamplePartitionDisjointnessEvidence(evidence)
    assert not disjointness.exact_qualified_run_disjoint


def test_same_run_different_qualification_keeps_run_axes_distinct() -> None:
    baseline = _qualified_run(suffix=40, start=_BASE)
    wider_policy = MarketDataIntegrityPolicy(
        max_delivery_delay=HostingLatencyDuration.from_milliseconds(5_000)
    )
    requalified = _requalify(baseline, policy=wider_policy)
    assert baseline != requalified
    assert baseline.run == requalified.run

    evidence = _partition(
        baseline,
        requalified,
        _qualified_run(suffix=41, start=_BASE + timedelta(minutes=3)),
    )
    overlap = evidence.derived_overlap_report.pairwise[0].run_overlaps[0]

    assert not overlap.exact_qualified_run_equal
    assert overlap.exact_run_equal
    assert overlap.run_id_equal
    assert overlap.run_input_fingerprint_equal


def test_different_run_ids_same_input_fingerprint_are_not_disjoint_inputs() -> None:
    baseline = _qualified_run(suffix=50, start=_BASE)
    rerun = _rerun_same_inputs(baseline, suffix=1)
    assert baseline.run.run_id != rerun.run.run_id
    assert baseline.run.input_fingerprint == rerun.run.input_fingerprint
    assert baseline.run != rerun.run

    evidence = _partition(
        baseline,
        rerun,
        _qualified_run(suffix=51, start=_BASE + timedelta(minutes=3)),
    )
    overlap = evidence.derived_overlap_report.pairwise[0].run_overlaps[0]

    assert not overlap.exact_qualified_run_equal
    assert not overlap.exact_run_equal
    assert not overlap.run_id_equal
    assert overlap.run_input_fingerprint_equal


def test_same_dataset_and_observation_axes_are_reported_independently() -> None:
    baseline = _qualified_run(suffix=60, start=_BASE)
    rerun = _rerun_same_inputs(baseline, suffix=2)
    evidence = _partition(
        baseline,
        rerun,
        _qualified_run(suffix=61, start=_BASE + timedelta(minutes=3)),
    )
    pair = evidence.derived_overlap_report.pairwise[0]

    assert len(pair.dataset_overlaps) == 1
    dataset_overlap = pair.dataset_overlaps[0]
    assert dataset_overlap.dataset_id_equal
    assert dataset_overlap.revision_id_equal
    assert dataset_overlap.evidence_digest_equal
    assert dataset_overlap.exact_triple_equal
    assert len(pair.observation_overlaps) == 1
    observation_overlap = pair.observation_overlaps[0]
    assert observation_overlap.observation_id_equal
    assert observation_overlap.snapshot_id_equal


def test_same_source_market_time_overlap_is_one_exact_pair_record() -> None:
    shared_source = _source(70)
    development = _qualified_run(
        suffix=70,
        start=_BASE,
        source=shared_source,
    )
    calibration = _qualified_run(
        suffix=71,
        start=_BASE,
        source=shared_source,
    )
    evidence = _partition(
        development,
        calibration,
        _qualified_run(suffix=72, start=_BASE + timedelta(minutes=3)),
    )
    market = evidence.derived_overlap_report.pairwise[0].market_time_overlaps

    assert len(market) == 1
    assert market[0].exact_stream_overlap
    assert market[0].market_coordinate_overlap


def test_cross_source_market_time_overlap_is_coordinate_only() -> None:
    evidence = _partition(
        _qualified_run(suffix=80, start=_BASE, source=_source(80)),
        _qualified_run(suffix=81, start=_BASE, source=_source(81)),
        _qualified_run(suffix=82, start=_BASE + timedelta(minutes=3)),
    )
    market = evidence.derived_overlap_report.pairwise[0].market_time_overlaps

    assert len(market) == 1
    assert not market[0].exact_stream_overlap
    assert market[0].market_coordinate_overlap
    disjointness = partition.SamplePartitionDisjointnessEvidence(evidence)
    assert disjointness.exact_stream_market_time_disjoint
    assert not disjointness.market_coordinate_time_disjoint


def test_contiguous_boundary_is_not_market_time_overlap() -> None:
    development = _qualified_run(suffix=90, start=_BASE)
    calibration = _qualified_run(
        suffix=91,
        start=_BASE + timedelta(minutes=1),
    )
    evidence = _partition(
        development,
        calibration,
        _qualified_run(suffix=92, start=_BASE + timedelta(minutes=3)),
    )

    assert evidence.derived_overlap_report.pairwise[0].market_time_overlaps == ()


def test_available_at_change_does_not_change_market_time_classification() -> None:
    shared_source = _source(100)
    slow = _qualified_run(
        suffix=100,
        start=_BASE,
        source=shared_source,
        availability_delay=timedelta(seconds=5),
    )
    fast = _qualified_run(
        suffix=101,
        start=_BASE,
        source=shared_source,
        availability_delay=timedelta(milliseconds=1),
    )
    evidence = _partition(
        slow,
        fast,
        _qualified_run(suffix=102, start=_BASE + timedelta(minutes=3)),
    )

    market = evidence.derived_overlap_report.pairwise[0].market_time_overlaps
    assert len(market) == 1
    assert market[0].interval_a_opened == market[0].interval_b_opened
    assert market[0].interval_a_closed == market[0].interval_b_closed


def test_utc_projection_is_timezone_representation_invariant() -> None:
    utc_value = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)
    paraguay_value = datetime(
        2026,
        8,
        10,
        12,
        0,
        tzinfo=timezone(timedelta(hours=-3)),
    )

    assert partition._utc_microseconds(utc_value) == partition._utc_microseconds(
        paraguay_value
    )


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 8, 10, 12, 0),
        cast(datetime, "not-a-datetime"),
    ],
)
def test_utc_projection_rejects_invalid_datetime(value: datetime) -> None:
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition._utc_microseconds(value)


def test_local_overlap_records_reject_impossible_boolean_claims() -> None:
    run = _qualified_run(suffix=110, start=_BASE)
    dev = _assignment(partition.SampleRole.DEVELOPMENT, run)
    cal = _assignment(partition.SampleRole.CALIBRATION, run)
    refs = (
        partition._run_ref(partition.SampleRole.DEVELOPMENT, 0, dev.qualified_runs[0]),
        partition._run_ref(partition.SampleRole.CALIBRATION, 0, cal.qualified_runs[0]),
    )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.RunOverlapEvidence(
            run_ref_a=refs[0],
            run_ref_b=refs[1],
            exact_qualified_run_equal=True,
            exact_run_equal=False,
            run_id_equal=True,
            run_input_fingerprint_equal=True,
        )

    dataset_refs = (
        partition._qualified_datasets(partition.SampleRole.DEVELOPMENT, dev)[0][0],
        partition._qualified_datasets(partition.SampleRole.CALIBRATION, cal)[0][0],
    )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.DatasetOverlapEvidence(
            dataset_ref_a=dataset_refs[0],
            dataset_ref_b=dataset_refs[1],
            dataset_id_equal=True,
            revision_id_equal=True,
            evidence_digest_equal=True,
            exact_triple_equal=False,
        )

    observation_refs = (
        partition._qualified_observations(partition.SampleRole.DEVELOPMENT, dev)[0][0],
        partition._qualified_observations(partition.SampleRole.CALIBRATION, cal)[0][0],
    )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.ObservationOverlapEvidence(
            obs_ref_a=observation_refs[0],
            obs_ref_b=observation_refs[1],
            observation_id_equal=False,
            snapshot_id_equal=False,
        )


def test_market_time_record_rejects_non_overlap_and_wrong_stream_flag() -> None:
    run_a = _qualified_run(suffix=120, start=_BASE)
    run_b = _qualified_run(suffix=121, start=_BASE + timedelta(minutes=2))
    dev = _assignment(partition.SampleRole.DEVELOPMENT, run_a)
    cal = _assignment(partition.SampleRole.CALIBRATION, run_b)
    ref_a, obs_a = partition._qualified_observations(
        partition.SampleRole.DEVELOPMENT,
        dev,
    )[0]
    ref_b, obs_b = partition._qualified_observations(
        partition.SampleRole.CALIBRATION,
        cal,
    )[0]
    payload_a = cast(OhlcSnapshot, obs_a.payload)
    payload_b = cast(OhlcSnapshot, obs_b.payload)

    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.MarketTimeOverlapEvidence(
            obs_ref_a=ref_a,
            obs_ref_b=ref_b,
            source_a=payload_a.source,
            source_b=payload_b.source,
            instrument=payload_a.instrument,
            timeframe=payload_a.timeframe,
            interval_a_opened=payload_a.opened_at,
            interval_a_closed=payload_a.closed_at,
            interval_b_opened=payload_b.opened_at,
            interval_b_closed=payload_b.closed_at,
            exact_stream_overlap=payload_a.source == payload_b.source,
            market_coordinate_overlap=True,
        )

    overlapping = _qualified_run(suffix=122, start=_BASE, source=payload_a.source)
    cal2 = _assignment(partition.SampleRole.CALIBRATION, overlapping)
    ref_c, obs_c = partition._qualified_observations(
        partition.SampleRole.CALIBRATION,
        cal2,
    )[0]
    payload_c = cast(OhlcSnapshot, obs_c.payload)
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.MarketTimeOverlapEvidence(
            obs_ref_a=ref_a,
            obs_ref_b=ref_c,
            source_a=payload_a.source,
            source_b=payload_c.source,
            instrument=payload_a.instrument,
            timeframe=payload_a.timeframe,
            interval_a_opened=payload_a.opened_at,
            interval_a_closed=payload_a.closed_at,
            interval_b_opened=payload_c.opened_at,
            interval_b_closed=payload_c.closed_at,
            exact_stream_overlap=False,
            market_coordinate_overlap=True,
        )


def test_reference_resolvers_reject_tampered_identity() -> None:
    development = _qualified_run(suffix=130, start=_BASE)
    assignments = (
        _assignment(partition.SampleRole.DEVELOPMENT, development),
        _assignment(
            partition.SampleRole.CALIBRATION,
            _qualified_run(suffix=131, start=_BASE + timedelta(minutes=2)),
        ),
        _assignment(
            partition.SampleRole.EXTERNAL_VALIDATION,
            _qualified_run(suffix=132, start=_BASE + timedelta(minutes=4)),
        ),
    )
    valid_ref = partition._run_ref(
        partition.SampleRole.DEVELOPMENT,
        0,
        development,
    )
    assert partition._resolve_qualified_run(assignments, valid_ref) == development

    tampered_run = replace(valid_ref, run_id=ResearchRunId(_uuid(999_001)))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition._resolve_qualified_run(assignments, tampered_run)

    dataset_ref = partition._qualified_datasets(
        partition.SampleRole.DEVELOPMENT,
        assignments[0],
    )[0][0]
    tampered_dataset = replace(
        dataset_ref,
        revision_id=HistoricalDatasetRevisionId(_uuid(999_002)),
    )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition._resolve_qualified_dataset(assignments, tampered_dataset)

    observation_ref = partition._qualified_observations(
        partition.SampleRole.DEVELOPMENT,
        assignments[0],
    )[0][0]
    tampered_observation = replace(
        observation_ref,
        snapshot_id=MarketDataSnapshotId(_uuid(999_003)),
    )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition._resolve_observation(assignments, tampered_observation)


def test_forged_report_and_fingerprint_are_rejected() -> None:
    shared = _qualified_run(suffix=140, start=_BASE)
    evidence = _partition(
        shared,
        shared,
        _qualified_run(suffix=141, start=_BASE + timedelta(minutes=4)),
    )
    forged_pair = partition.RolePairOverlapEvidence(
        role_a=partition.SampleRole.DEVELOPMENT,
        role_b=partition.SampleRole.CALIBRATION,
        run_overlaps=(),
        dataset_overlaps=(),
        observation_overlaps=(),
        market_time_overlaps=(),
    )
    forged_report = partition.OverlapReport(
        pairwise=(
            forged_pair,
            evidence.derived_overlap_report.pairwise[1],
            evidence.derived_overlap_report.pairwise[2],
        )
    )
    forged_fingerprint = partition._compute_partition_fingerprint(
        evidence.assignments,
        forged_report,
    )

    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.SamplePartitionEvidence(
            assignments=evidence.assignments,
            derived_overlap_report=forged_report,
            fingerprint=forged_fingerprint,
        )


def test_partition_fingerprint_is_reproducible_and_materially_bound() -> None:
    evidence_a = _partition(
        _qualified_run(suffix=150, start=_BASE),
        _qualified_run(suffix=151, start=_BASE + timedelta(minutes=2)),
        _qualified_run(suffix=152, start=_BASE + timedelta(minutes=4)),
    )
    evidence_b = partition.SamplePartitionEvidence(
        assignments=evidence_a.assignments,
        derived_overlap_report=evidence_a.derived_overlap_report,
        fingerprint=partition._compute_partition_fingerprint(
            evidence_a.assignments,
            evidence_a.derived_overlap_report,
        ),
    )
    changed = _partition(
        _qualified_run(suffix=153, start=_BASE),
        _qualified_run(suffix=151, start=_BASE + timedelta(minutes=2)),
        _qualified_run(suffix=152, start=_BASE + timedelta(minutes=4)),
    )

    assert evidence_a.fingerprint == evidence_b.fingerprint
    assert evidence_a.fingerprint != changed.fingerprint


def test_builder_signatures_do_not_accept_derived_claims() -> None:
    parameters = inspect.signature(
        partition.build_sample_partition_evidence
    ).parameters

    assert "derived_overlap_report" not in parameters
    assert "fingerprint" not in parameters


def test_authority_boundary_has_no_operational_imports_or_surfaces() -> None:
    source = inspect.getsource(partition)
    forbidden = (
        "MessageBus",
        "EventBus",
        "place_order",
        "execute_order",
        "allocate_capital",
        "broker",
        "provider_write",
        "production_activation",
    )

    assert all(token not in source for token in forbidden)
    assert not hasattr(partition.SamplePartitionEvidence, "dispatch")
    assert not hasattr(partition.SamplePartitionEvidence, "trading_signal")
