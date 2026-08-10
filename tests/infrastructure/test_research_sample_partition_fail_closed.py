from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
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
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.replay_availability import ReplayObservationId
from qore.infrastructure.research_run import ResearchRunId

_NOW = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)


def _uuid(value: int) -> UUID:
    return UUID(f"9d000000-0000-0000-0000-{value:012d}")


def _source(value: int) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(10_000 + value)),
        source_id=SourceId(_uuid(20_000 + value)),
        port_name=PortName(f"market-data.partition-fail-closed-{value}"),
    )


def _run_ref(
    role: partition.SampleRole,
    value: int,
    *,
    index: int = 0,
) -> partition.QualifiedRunRef:
    return partition.QualifiedRunRef(
        role=role,
        canonical_run_index=index,
        run_id=ResearchRunId(_uuid(30_000 + value)),
        qualified_run_fingerprint=IntegrityQualifiedResearchRunFingerprint(
            f"{value % 16:x}" * 64
        ),
    )


def _dataset_ref(
    role: partition.SampleRole,
    value: int,
) -> partition.QualifiedDatasetRef:
    return partition.QualifiedDatasetRef(
        run_ref=_run_ref(role, value),
        qualification_index=0,
        dataset_id=HistoricalDatasetId(_uuid(40_000 + value)),
        revision_id=HistoricalDatasetRevisionId(_uuid(50_000 + value)),
        evidence_digest=HistoricalDatasetDigest(f"{(value + 1) % 16:x}" * 64),
    )


def _observation_ref(
    role: partition.SampleRole,
    value: int,
) -> partition.QualifiedObservationRef:
    return partition.QualifiedObservationRef(
        dataset_ref=_dataset_ref(role, value),
        observation_index=0,
        observation_id=ReplayObservationId(_uuid(60_000 + value)),
        snapshot_id=MarketDataSnapshotId(_uuid(70_000 + value)),
    )


def _run_overlap(value: int = 1) -> partition.RunOverlapEvidence:
    return partition.RunOverlapEvidence(
        run_ref_a=_run_ref(partition.SampleRole.DEVELOPMENT, value),
        run_ref_b=_run_ref(partition.SampleRole.CALIBRATION, value + 1),
        exact_qualified_run_equal=False,
        exact_run_equal=False,
        run_id_equal=True,
        run_input_fingerprint_equal=False,
    )


def _dataset_overlap(
    value: int = 10,
    *,
    role_a: partition.SampleRole = partition.SampleRole.DEVELOPMENT,
    role_b: partition.SampleRole = partition.SampleRole.CALIBRATION,
) -> partition.DatasetOverlapEvidence:
    return partition.DatasetOverlapEvidence(
        dataset_ref_a=_dataset_ref(role_a, value),
        dataset_ref_b=_dataset_ref(role_b, value + 1),
        dataset_id_equal=True,
        revision_id_equal=False,
        evidence_digest_equal=False,
        exact_triple_equal=False,
    )


def _observation_overlap(
    value: int = 20,
    *,
    role_a: partition.SampleRole = partition.SampleRole.DEVELOPMENT,
    role_b: partition.SampleRole = partition.SampleRole.CALIBRATION,
) -> partition.ObservationOverlapEvidence:
    return partition.ObservationOverlapEvidence(
        obs_ref_a=_observation_ref(role_a, value),
        obs_ref_b=_observation_ref(role_b, value + 1),
        observation_id_equal=False,
        snapshot_id_equal=True,
    )


def _market_overlap(
    value: int = 30,
    *,
    role_a: partition.SampleRole = partition.SampleRole.DEVELOPMENT,
    role_b: partition.SampleRole = partition.SampleRole.CALIBRATION,
    same_source: bool = True,
) -> partition.MarketTimeOverlapEvidence:
    source_a = _source(value)
    source_b = source_a if same_source else _source(value + 1)
    return partition.MarketTimeOverlapEvidence(
        obs_ref_a=_observation_ref(role_a, value),
        obs_ref_b=_observation_ref(role_b, value + 1),
        source_a=source_a,
        source_b=source_b,
        instrument=Instrument("EURUSD"),
        timeframe=Timeframe(60),
        interval_a_opened=_NOW,
        interval_a_closed=_NOW + timedelta(seconds=60),
        interval_b_opened=_NOW + timedelta(seconds=30),
        interval_b_closed=_NOW + timedelta(seconds=90),
        exact_stream_overlap=same_source,
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


def test_fingerprint_logical_values_and_wrong_runtime_type() -> None:
    fingerprint = partition.SamplePartitionFingerprint("a" * 64)
    assert fingerprint.logical_values() == ("a" * 64,)
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.SamplePartitionFingerprint(cast(str, 123))


def test_reference_field_runtime_types_fail_closed() -> None:
    valid_run = _run_ref(partition.SampleRole.DEVELOPMENT, 1)
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(valid_run, role=cast(partition.SampleRole, "development"))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(valid_run, run_id=cast(ResearchRunId, _uuid(1)))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            valid_run,
            qualified_run_fingerprint=cast(
                IntegrityQualifiedResearchRunFingerprint,
                "a" * 64,
            ),
        )

    valid_dataset = _dataset_ref(partition.SampleRole.DEVELOPMENT, 2)
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(valid_dataset, run_ref=cast(partition.QualifiedRunRef, object()))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(valid_dataset, dataset_id=cast(HistoricalDatasetId, _uuid(2)))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            valid_dataset,
            revision_id=cast(HistoricalDatasetRevisionId, _uuid(3)),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(valid_dataset, evidence_digest=cast(HistoricalDatasetDigest, "b" * 64))

    valid_observation = _observation_ref(partition.SampleRole.DEVELOPMENT, 3)
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            valid_observation,
            dataset_ref=cast(partition.QualifiedDatasetRef, object()),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            valid_observation,
            observation_id=cast(ReplayObservationId, _uuid(4)),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            valid_observation,
            snapshot_id=cast(MarketDataSnapshotId, _uuid(5)),
        )


@pytest.mark.parametrize(
    ("exact_qualified", "exact_run", "run_id", "input_equal"),
    [
        (True, True, False, True),
        (True, True, True, False),
        (False, True, False, True),
        (False, True, True, False),
        (False, False, False, False),
    ],
)
def test_run_overlap_implications_are_fail_closed(
    exact_qualified: bool,
    exact_run: bool,
    run_id: bool,
    input_equal: bool,
) -> None:
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.RunOverlapEvidence(
            run_ref_a=_run_ref(partition.SampleRole.DEVELOPMENT, 10),
            run_ref_b=_run_ref(partition.SampleRole.CALIBRATION, 11),
            exact_qualified_run_equal=exact_qualified,
            exact_run_equal=exact_run,
            run_id_equal=run_id,
            run_input_fingerprint_equal=input_equal,
        )


def test_overlap_reference_runtime_types_fail_closed() -> None:
    run_overlap = _run_overlap()
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(run_overlap, run_ref_a=cast(partition.QualifiedRunRef, object()))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(run_overlap, run_ref_b=cast(partition.QualifiedRunRef, object()))

    dataset_overlap = _dataset_overlap()
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            dataset_overlap,
            dataset_ref_a=cast(partition.QualifiedDatasetRef, object()),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            dataset_overlap,
            dataset_ref_b=cast(partition.QualifiedDatasetRef, object()),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            dataset_overlap,
            dataset_id_equal=False,
            revision_id_equal=False,
            evidence_digest_equal=False,
            exact_triple_equal=False,
        )

    observation_overlap = _observation_overlap()
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            observation_overlap,
            obs_ref_a=cast(partition.QualifiedObservationRef, object()),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            observation_overlap,
            obs_ref_b=cast(partition.QualifiedObservationRef, object()),
        )


def test_market_overlap_remaining_fail_closed_branches() -> None:
    market = _market_overlap()
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(market, obs_ref_a=cast(partition.QualifiedObservationRef, object()))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(market, obs_ref_b=cast(partition.QualifiedObservationRef, object()))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(market, source_a=cast(ExternalSourceDescriptor, object()))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(market, source_b=cast(ExternalSourceDescriptor, object()))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(market, interval_b_closed=market.interval_b_opened)
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(market, exact_stream_overlap=cast(bool, 1))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(market, market_coordinate_overlap=False)
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            market,
            interval_b_opened=market.interval_a_closed,
            interval_b_closed=market.interval_a_closed + timedelta(seconds=60),
        )


def test_role_pair_each_child_orientation_is_enforced() -> None:
    base = _empty_pair(
        partition.SampleRole.DEVELOPMENT,
        partition.SampleRole.CALIBRATION,
    )
    wrong_dataset = _dataset_overlap(
        role_a=partition.SampleRole.CALIBRATION,
        role_b=partition.SampleRole.EXTERNAL_VALIDATION,
    )
    wrong_observation = _observation_overlap(
        role_a=partition.SampleRole.CALIBRATION,
        role_b=partition.SampleRole.EXTERNAL_VALIDATION,
    )
    wrong_market = _market_overlap(
        role_a=partition.SampleRole.CALIBRATION,
        role_b=partition.SampleRole.EXTERNAL_VALIDATION,
    )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(base, dataset_overlaps=(wrong_dataset,))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(base, observation_overlaps=(wrong_observation,))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(base, market_time_overlaps=(wrong_market,))


def test_role_pair_each_child_collection_rejects_bad_shape_and_duplicates() -> None:
    base = _empty_pair(
        partition.SampleRole.DEVELOPMENT,
        partition.SampleRole.CALIBRATION,
    )
    dataset = _dataset_overlap()
    observation = _observation_overlap()
    market = _market_overlap()

    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            base,
            dataset_overlaps=cast(tuple[partition.DatasetOverlapEvidence, ...], []),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            base,
            observation_overlaps=cast(
                tuple[partition.ObservationOverlapEvidence, ...],
                (object(),),
            ),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(
            base,
            market_time_overlaps=cast(
                tuple[partition.MarketTimeOverlapEvidence, ...],
                (object(),),
            ),
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(base, dataset_overlaps=(dataset, dataset))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(base, observation_overlaps=(observation, observation))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(base, market_time_overlaps=(market, market))


def test_role_pair_each_child_collection_rejects_noncanonical_order() -> None:
    base = _empty_pair(
        partition.SampleRole.DEVELOPMENT,
        partition.SampleRole.CALIBRATION,
    )
    dataset_a = _dataset_overlap(100)
    dataset_b = _dataset_overlap(200)
    observation_a = _observation_overlap(300)
    observation_b = _observation_overlap(400)
    market_a = _market_overlap(500)
    market_b = _market_overlap(600)

    dataset_sorted = tuple(
        sorted((dataset_a, dataset_b), key=partition._dataset_overlap_order_key)
    )
    observation_sorted = tuple(
        sorted(
            (observation_a, observation_b),
            key=partition._observation_overlap_order_key,
        )
    )
    market_sorted = tuple(
        sorted((market_a, market_b), key=partition._market_time_conflict_order_key)
    )

    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(base, dataset_overlaps=tuple(reversed(dataset_sorted)))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(base, observation_overlaps=tuple(reversed(observation_sorted)))
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        replace(base, market_time_overlaps=tuple(reversed(market_sorted)))


def test_overlap_report_rejects_non_tuple_and_wrong_count() -> None:
    pair = _empty_pair(
        partition.SampleRole.DEVELOPMENT,
        partition.SampleRole.CALIBRATION,
    )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.OverlapReport(
            pairwise=cast(tuple[partition.RolePairOverlapEvidence, ...], [])
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition.OverlapReport(pairwise=(pair,))


def test_assignment_tuple_validator_rejects_shape_before_dereference() -> None:
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition._validate_partition_assignments_tuple(
            cast(tuple[partition.SampleRoleAssignment, ...], [])
        )
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition._validate_partition_assignments_tuple(
            cast(
                tuple[partition.SampleRoleAssignment, ...],
                (object(), object(), object()),
            )
        )


def test_fingerprint_computation_rejects_wrong_report_type() -> None:
    with pytest.raises(partition.ResearchSamplePartitionValidationError):
        partition._compute_partition_fingerprint(
            cast(tuple[partition.SampleRoleAssignment, ...], ()),
            cast(partition.OverlapReport, object()),
        )
