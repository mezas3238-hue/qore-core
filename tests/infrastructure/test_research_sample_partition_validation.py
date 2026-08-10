from __future__ import annotations

from datetime import UTC, datetime, timedelta, tzinfo
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure.research_sample_partition as partition
from qore.infrastructure.dataset_integrity_qualification import (
    IntegrityQualifiedResearchRunFingerprint,
)
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetDigest,
    HistoricalDatasetId,
    HistoricalDatasetRevisionId,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    Timeframe,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.replay_availability import ReplayObservationId
from qore.infrastructure.research_run import ResearchRunId

_BASE = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"8c000000-0000-0000-0000-{suffix:012d}")


def _source(suffix: int) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(10_000 + suffix)),
        source_id=SourceId(_uuid(20_000 + suffix)),
        port_name=PortName(f"market-data.partition-validation-{suffix}"),
    )


def _run_ref(role: partition.SampleRole, suffix: int) -> partition.QualifiedRunRef:
    return partition.QualifiedRunRef(
        role=role,
        canonical_run_index=0,
        run_id=ResearchRunId(_uuid(30_000 + suffix)),
        qualified_run_fingerprint=IntegrityQualifiedResearchRunFingerprint(
            f"{suffix % 16:x}" * 64
        ),
    )


def _dataset_ref(
    role: partition.SampleRole,
    suffix: int,
) -> partition.QualifiedDatasetRef:
    return partition.QualifiedDatasetRef(
        run_ref=_run_ref(role, suffix),
        qualification_index=0,
        dataset_id=HistoricalDatasetId(_uuid(40_000 + suffix)),
        revision_id=HistoricalDatasetRevisionId(_uuid(50_000 + suffix)),
        evidence_digest=HistoricalDatasetDigest(f"{(suffix + 1) % 16:x}" * 64),
    )


def _observation_ref(
    role: partition.SampleRole,
    suffix: int,
) -> partition.QualifiedObservationRef:
    return partition.QualifiedObservationRef(
        dataset_ref=_dataset_ref(role, suffix),
        observation_index=0,
        observation_id=ReplayObservationId(_uuid(60_000 + suffix)),
        snapshot_id=MarketDataSnapshotId(_uuid(70_000 + suffix)),
    )


def _run_overlap(
    role_a: partition.SampleRole = partition.SampleRole.DEVELOPMENT,
    role_b: partition.SampleRole = partition.SampleRole.CALIBRATION,
    *,
    suffix: int = 1,
) -> partition.RunOverlapEvidence:
    return partition.RunOverlapEvidence(
        run_ref_a=_run_ref(role_a, suffix),
        run_ref_b=_run_ref(role_b, suffix + 1),
        exact_qualified_run_equal=False,
        exact_run_equal=False,
        run_id_equal=True,
        run_input_fingerprint_equal=False,
    )


def _dataset_overlap(
    role_a: partition.SampleRole = partition.SampleRole.DEVELOPMENT,
    role_b: partition.SampleRole = partition.SampleRole.CALIBRATION,
    *,
    suffix: int = 10,
) -> partition.DatasetOverlapEvidence:
    return partition.DatasetOverlapEvidence(
        dataset_ref_a=_dataset_ref(role_a, suffix),
        dataset_ref_b=_dataset_ref(role_b, suffix + 1),
        dataset_id_equal=True,
        revision_id_equal=False,
        evidence_digest_equal=False,
        exact_triple_equal=False,
    )


def _observation_overlap(
    role_a: partition.SampleRole = partition.SampleRole.DEVELOPMENT,
    role_b: partition.SampleRole = partition.SampleRole.CALIBRATION,
    *,
    suffix: int = 20,
) -> partition.ObservationOverlapEvidence:
    return partition.ObservationOverlapEvidence(
        obs_ref_a=_observation_ref(role_a, suffix),
        obs_ref_b=_observation_ref(role_b, suffix + 1),
        observation_id_equal=True,
        snapshot_id_equal=False,
    )


def _market_overlap(
    role_a: partition.SampleRole = partition.SampleRole.DEVELOPMENT,
    role_b: partition.SampleRole = partition.SampleRole.CALIBRATION,
    *,
    suffix: int = 30,
    source_a: ExternalSourceDescriptor | None = None,
    source_b: ExternalSourceDescriptor | None = None,
) -> partition.MarketTimeOverlapEvidence:
    source_a = source_a or _source(suffix)
    source_b = source_b or source_a
    return partition.MarketTimeOverlapEvidence(
        obs_ref_a=_observation_ref(role_a, suffix),
        obs_ref_b=_observation_ref(role_b, suffix + 1),
        source_a=source_a,
        source_b=source_b,
        instrument=Instrument("EURUSD"),
        timeframe=Timeframe(60),
        interval_a_opened=_BASE,
        interval_a_closed=_BASE + timedelta(minutes=1),
        interval_b_opened=_BASE + timedelta(seconds=30),
        interval_b_closed=_BASE + timedelta(seconds=90),
        exact_stream_overlap=source_a == source_b,
        market_coordinate_overlap=True,
    )


def _empty_pair(
    role_a: partition.SampleRole,
    role_b: partition.SampleRole,
) -> partition.RolePairOverlapEvidence:
    return partition.RolePairOverlapEvidence(
        role_a=role_a,
        role_b=role_b,
        run_overlaps=(),
        dataset_overlaps=(),
        observation_overlaps=(),
        market_time_overlaps=(),
    )


def test_fingerprint_and_reference_types_fail_closed() -> None:
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.SamplePartitionFingerprint("A" * 64)
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.SamplePartitionFingerprint("0" * 63)
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.QualifiedRunRef(
            role=partition.SampleRole.DEVELOPMENT,
            canonical_run_index=cast(int, True),
            run_id=ResearchRunId(_uuid(1)),
            qualified_run_fingerprint=IntegrityQualifiedResearchRunFingerprint("0" * 64),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.QualifiedDatasetRef(
            run_ref=_run_ref(partition.SampleRole.DEVELOPMENT, 2),
            qualification_index=cast(int, True),
            dataset_id=HistoricalDatasetId(_uuid(2)),
            revision_id=HistoricalDatasetRevisionId(_uuid(3)),
            evidence_digest=HistoricalDatasetDigest("1" * 64),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.QualifiedObservationRef(
            dataset_ref=_dataset_ref(partition.SampleRole.DEVELOPMENT, 3),
            observation_index=cast(int, True),
            observation_id=ReplayObservationId(_uuid(4)),
            snapshot_id=MarketDataSnapshotId(_uuid(5)),
        )


def test_overlap_boolean_types_are_strict() -> None:
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.RunOverlapEvidence(
            run_ref_a=_run_ref(partition.SampleRole.DEVELOPMENT, 1),
            run_ref_b=_run_ref(partition.SampleRole.CALIBRATION, 2),
            exact_qualified_run_equal=False,
            exact_run_equal=False,
            run_id_equal=cast(bool, 1),
            run_input_fingerprint_equal=False,
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.DatasetOverlapEvidence(
            dataset_ref_a=_dataset_ref(partition.SampleRole.DEVELOPMENT, 3),
            dataset_ref_b=_dataset_ref(partition.SampleRole.CALIBRATION, 4),
            dataset_id_equal=cast(bool, 1),
            revision_id_equal=False,
            evidence_digest_equal=False,
            exact_triple_equal=False,
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.ObservationOverlapEvidence(
            obs_ref_a=_observation_ref(partition.SampleRole.DEVELOPMENT, 5),
            obs_ref_b=_observation_ref(partition.SampleRole.CALIBRATION, 6),
            observation_id_equal=cast(bool, 1),
            snapshot_id_equal=False,
        )


class _NoOffsetTz(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> str:
        return "NO-OFFSET"


def test_datetime_validation_rejects_tzinfo_without_offset() -> None:
    invalid = datetime(2026, 8, 10, 15, 0, tzinfo=_NoOffsetTz())
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition._utc_microseconds(invalid)


def test_market_time_record_rejects_wrong_types_and_durations() -> None:
    valid = _market_overlap()
    kwargs = {
        "obs_ref_a": valid.obs_ref_a,
        "obs_ref_b": valid.obs_ref_b,
        "source_a": valid.source_a,
        "source_b": valid.source_b,
        "instrument": valid.instrument,
        "timeframe": valid.timeframe,
        "interval_a_opened": valid.interval_a_opened,
        "interval_a_closed": valid.interval_a_closed,
        "interval_b_opened": valid.interval_b_opened,
        "interval_b_closed": valid.interval_b_closed,
        "exact_stream_overlap": valid.exact_stream_overlap,
        "market_coordinate_overlap": valid.market_coordinate_overlap,
    }
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.MarketTimeOverlapEvidence(**{**kwargs, "instrument": cast(Instrument, "EURUSD")})
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.MarketTimeOverlapEvidence(**{**kwargs, "timeframe": cast(Timeframe, 60)})
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.MarketTimeOverlapEvidence(
            **{**kwargs, "interval_a_closed": valid.interval_a_opened}
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.MarketTimeOverlapEvidence(
            **{**kwargs, "market_coordinate_overlap": cast(bool, 1)}
        )


def test_role_pair_rejects_wrong_direction_and_child_orientation() -> None:
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        _empty_pair(
            partition.SampleRole.CALIBRATION,
            partition.SampleRole.DEVELOPMENT,
        )
    wrong_child = _run_overlap(
        partition.SampleRole.CALIBRATION,
        partition.SampleRole.EXTERNAL_VALIDATION,
    )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.RolePairOverlapEvidence(
            role_a=partition.SampleRole.DEVELOPMENT,
            role_b=partition.SampleRole.CALIBRATION,
            run_overlaps=(wrong_child,),
            dataset_overlaps=(),
            observation_overlaps=(),
            market_time_overlaps=(),
        )


def test_role_pair_rejects_wrong_collection_types() -> None:
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.RolePairOverlapEvidence(
            role_a=partition.SampleRole.DEVELOPMENT,
            role_b=partition.SampleRole.CALIBRATION,
            run_overlaps=cast(tuple[partition.RunOverlapEvidence, ...], []),
            dataset_overlaps=(),
            observation_overlaps=(),
            market_time_overlaps=(),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.RolePairOverlapEvidence(
            role_a=partition.SampleRole.DEVELOPMENT,
            role_b=partition.SampleRole.CALIBRATION,
            run_overlaps=cast(tuple[partition.RunOverlapEvidence, ...], (object(),)),
            dataset_overlaps=(),
            observation_overlaps=(),
            market_time_overlaps=(),
        )


def test_role_pair_rejects_duplicates_and_noncanonical_order() -> None:
    first = _run_overlap(suffix=100)
    second = _run_overlap(suffix=200)
    canonical = tuple(sorted((first, second), key=partition._run_overlap_order_key))
    reversed_items = tuple(reversed(canonical))
    if reversed_items != canonical:
        with pytest.raises(partition.ResearchSamplePartitionValidationError):
            partition.RolePairOverlapEvidence(
                role_a=partition.SampleRole.DEVELOPMENT,
                role_b=partition.SampleRole.CALIBRATION,
                run_overlaps=reversed_items,
                dataset_overlaps=(),
                observation_overlaps=(),
                market_time_overlaps=(),
            )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.RolePairOverlapEvidence(
            role_a=partition.SampleRole.DEVELOPMENT,
            role_b=partition.SampleRole.CALIBRATION,
            run_overlaps=(first, first),
            dataset_overlaps=(),
            observation_overlaps=(),
            market_time_overlaps=(),
        )


def test_each_role_pair_child_collection_accepts_canonical_valid_record() -> None:
    pair = partition.RolePairOverlapEvidence(
        role_a=partition.SampleRole.DEVELOPMENT,
        role_b=partition.SampleRole.CALIBRATION,
        run_overlaps=(_run_overlap(),),
        dataset_overlaps=(_dataset_overlap(),),
        observation_overlaps=(_observation_overlap(),),
        market_time_overlaps=(_market_overlap(),),
    )
    assert len(pair.run_overlaps) == 1
    assert len(pair.dataset_overlaps) == 1
    assert len(pair.observation_overlaps) == 1
    assert len(pair.market_time_overlaps) == 1


def test_overlap_report_rejects_shape_and_order_errors() -> None:
    dev_cal = _empty_pair(partition.SampleRole.DEVELOPMENT, partition.SampleRole.CALIBRATION)
    dev_ext = _empty_pair(
        partition.SampleRole.DEVELOPMENT,
        partition.SampleRole.EXTERNAL_VALIDATION,
    )
    cal_ext = _empty_pair(
        partition.SampleRole.CALIBRATION,
        partition.SampleRole.EXTERNAL_VALIDATION,
    )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.OverlapReport(pairwise=cast(tuple[partition.RolePairOverlapEvidence, ...], []))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.OverlapReport(pairwise=cast(tuple[partition.RolePairOverlapEvidence, ...], (dev_cal, object(), cal_ext)))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.OverlapReport(pairwise=(dev_ext, dev_cal, cal_ext))


def test_disjointness_rejects_non_partition_input() -> None:
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.SamplePartitionDisjointnessEvidence(
            source_partition=cast(partition.SamplePartitionEvidence, object())
        )


def test_canonical_projectors_preserve_all_overlap_fields() -> None:
    run = _run_overlap()
    dataset = _dataset_overlap()
    observation = _observation_overlap()
    market = _market_overlap()

    assert tuple(partition._canonical_run_overlap(run)) == (
        "run_ref_a",
        "run_ref_b",
        "exact_qualified_run_equal",
        "exact_run_equal",
        "run_id_equal",
        "run_input_fingerprint_equal",
    )
    assert tuple(partition._canonical_dataset_overlap(dataset)) == (
        "dataset_ref_a",
        "dataset_ref_b",
        "dataset_id_equal",
        "revision_id_equal",
        "evidence_digest_equal",
        "exact_triple_equal",
    )
    assert tuple(partition._canonical_observation_overlap(observation)) == (
        "obs_ref_a",
        "obs_ref_b",
        "observation_id_equal",
        "snapshot_id_equal",
    )
    assert tuple(partition._canonical_market_time_overlap(market)) == (
        "obs_ref_a",
        "obs_ref_b",
        "source_a",
        "source_b",
        "instrument",
        "timeframe_seconds",
        "interval_a_opened",
        "interval_a_closed",
        "interval_b_opened",
        "interval_b_closed",
        "exact_stream_overlap",
        "market_coordinate_overlap",
    )
