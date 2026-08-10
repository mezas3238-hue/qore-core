from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256

from qore.infrastructure.dataset_integrity_qualification import (
    DatasetIntegrityQualification,
    IntegrityQualifiedResearchRun,
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
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.infrastructure.replay_availability import (
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.research_run import ResearchRunId
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_PARTITION_SCHEMA = "qore.sample-partition-evidence.v1"
_MARKET_TIME_SEMANTICS = "half-open-ohlc.v1"


class ResearchSamplePartitionError(InfrastructureError):
    """Base error for exact research sample-partition evidence."""

    __slots__ = ()


class ResearchSamplePartitionValidationError(ResearchSamplePartitionError):
    """Violation of a sample-partition evidence invariant."""

    __slots__ = ()


class SampleRole(Enum):
    DEVELOPMENT = "development"
    CALIBRATION = "calibration"
    EXTERNAL_VALIDATION = "external_validation"


_SAMPLE_ROLE_ORDER: dict[SampleRole, int] = {
    SampleRole.DEVELOPMENT: 0,
    SampleRole.CALIBRATION: 1,
    SampleRole.EXTERNAL_VALIDATION: 2,
}


@dataclass(frozen=True, slots=True)
class SamplePartitionFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or re.fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchSamplePartitionValidationError(
                "fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _require_aware_datetime(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ResearchSamplePartitionValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchSamplePartitionValidationError(
            f"{field_name} must be timezone-aware"
        )
    return value


def _utc_microseconds(value: datetime) -> str:
    return _require_aware_datetime(
        value,
        field_name="canonical timestamp",
    ).astimezone(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True, slots=True)
class QualifiedRunRef:
    role: SampleRole
    canonical_run_index: int
    run_id: ResearchRunId
    qualified_run_fingerprint: IntegrityQualifiedResearchRunFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.role, SampleRole):
            raise ResearchSamplePartitionValidationError("role must be SampleRole")
        if type(self.canonical_run_index) is not int or self.canonical_run_index < 0:
            raise ResearchSamplePartitionValidationError(
                "canonical_run_index must be a non-negative int"
            )
        if not isinstance(self.run_id, ResearchRunId):
            raise ResearchSamplePartitionValidationError(
                "run_id must be ResearchRunId"
            )
        if not isinstance(
            self.qualified_run_fingerprint,
            IntegrityQualifiedResearchRunFingerprint,
        ):
            raise ResearchSamplePartitionValidationError(
                "qualified_run_fingerprint must be "
                "IntegrityQualifiedResearchRunFingerprint"
            )


@dataclass(frozen=True, slots=True)
class QualifiedDatasetRef:
    run_ref: QualifiedRunRef
    qualification_index: int
    dataset_id: HistoricalDatasetId
    revision_id: HistoricalDatasetRevisionId
    evidence_digest: HistoricalDatasetDigest

    def __post_init__(self) -> None:
        if not isinstance(self.run_ref, QualifiedRunRef):
            raise ResearchSamplePartitionValidationError(
                "run_ref must be QualifiedRunRef"
            )
        if type(self.qualification_index) is not int or self.qualification_index < 0:
            raise ResearchSamplePartitionValidationError(
                "qualification_index must be a non-negative int"
            )
        if not isinstance(self.dataset_id, HistoricalDatasetId):
            raise ResearchSamplePartitionValidationError(
                "dataset_id must be HistoricalDatasetId"
            )
        if not isinstance(self.revision_id, HistoricalDatasetRevisionId):
            raise ResearchSamplePartitionValidationError(
                "revision_id must be HistoricalDatasetRevisionId"
            )
        if not isinstance(self.evidence_digest, HistoricalDatasetDigest):
            raise ResearchSamplePartitionValidationError(
                "evidence_digest must be HistoricalDatasetDigest"
            )


@dataclass(frozen=True, slots=True)
class QualifiedObservationRef:
    dataset_ref: QualifiedDatasetRef
    observation_index: int
    observation_id: ReplayObservationId
    snapshot_id: MarketDataSnapshotId

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_ref, QualifiedDatasetRef):
            raise ResearchSamplePartitionValidationError(
                "dataset_ref must be QualifiedDatasetRef"
            )
        if type(self.observation_index) is not int or self.observation_index < 0:
            raise ResearchSamplePartitionValidationError(
                "observation_index must be a non-negative int"
            )
        if not isinstance(self.observation_id, ReplayObservationId):
            raise ResearchSamplePartitionValidationError(
                "observation_id must be ReplayObservationId"
            )
        if not isinstance(self.snapshot_id, MarketDataSnapshotId):
            raise ResearchSamplePartitionValidationError(
                "snapshot_id must be MarketDataSnapshotId"
            )


def _qualified_run_ref_order_key(ref: QualifiedRunRef) -> tuple[int, int, str, str]:
    return (
        _SAMPLE_ROLE_ORDER[ref.role],
        ref.canonical_run_index,
        str(ref.run_id.value),
        ref.qualified_run_fingerprint.value,
    )


def _qualified_dataset_ref_order_key(ref: QualifiedDatasetRef) -> tuple[object, ...]:
    return (
        *_qualified_run_ref_order_key(ref.run_ref),
        ref.qualification_index,
        str(ref.dataset_id.value),
        str(ref.revision_id.value),
        ref.evidence_digest.value,
    )


def _qualified_observation_ref_order_key(
    ref: QualifiedObservationRef,
) -> tuple[object, ...]:
    return (
        *_qualified_dataset_ref_order_key(ref.dataset_ref),
        ref.observation_index,
        str(ref.observation_id.value),
        str(ref.snapshot_id.value),
    )


def _external_source_order_key(
    source: ExternalSourceDescriptor,
) -> tuple[str, str, str]:
    return (
        str(source.adapter_id.value),
        str(source.source_id.value),
        source.port_name.value,
    )


@dataclass(frozen=True, slots=True)
class RunOverlapEvidence:
    run_ref_a: QualifiedRunRef
    run_ref_b: QualifiedRunRef
    exact_qualified_run_equal: bool
    exact_run_equal: bool
    run_id_equal: bool
    run_input_fingerprint_equal: bool

    def __post_init__(self) -> None:
        if not isinstance(self.run_ref_a, QualifiedRunRef):
            raise ResearchSamplePartitionValidationError(
                "run_ref_a must be QualifiedRunRef"
            )
        if not isinstance(self.run_ref_b, QualifiedRunRef):
            raise ResearchSamplePartitionValidationError(
                "run_ref_b must be QualifiedRunRef"
            )
        for field_name in (
            "exact_qualified_run_equal",
            "exact_run_equal",
            "run_id_equal",
            "run_input_fingerprint_equal",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ResearchSamplePartitionValidationError(
                    f"{field_name} must be bool"
                )
        if not (
            self.exact_qualified_run_equal
            or self.exact_run_equal
            or self.run_id_equal
            or self.run_input_fingerprint_equal
        ):
            raise ResearchSamplePartitionValidationError(
                "at least one run overlap axis must be True"
            )
        if self.exact_qualified_run_equal and not self.exact_run_equal:
            raise ResearchSamplePartitionValidationError(
                "exact_qualified_run_equal implies exact_run_equal"
            )
        if self.exact_qualified_run_equal and not self.run_id_equal:
            raise ResearchSamplePartitionValidationError(
                "exact_qualified_run_equal implies run_id_equal"
            )
        if self.exact_qualified_run_equal and not self.run_input_fingerprint_equal:
            raise ResearchSamplePartitionValidationError(
                "exact_qualified_run_equal implies run_input_fingerprint_equal"
            )
        if self.exact_run_equal and not self.run_id_equal:
            raise ResearchSamplePartitionValidationError(
                "exact_run_equal implies run_id_equal"
            )
        if self.exact_run_equal and not self.run_input_fingerprint_equal:
            raise ResearchSamplePartitionValidationError(
                "exact_run_equal implies run_input_fingerprint_equal"
            )


@dataclass(frozen=True, slots=True)
class DatasetOverlapEvidence:
    dataset_ref_a: QualifiedDatasetRef
    dataset_ref_b: QualifiedDatasetRef
    dataset_id_equal: bool
    revision_id_equal: bool
    evidence_digest_equal: bool
    exact_triple_equal: bool

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_ref_a, QualifiedDatasetRef):
            raise ResearchSamplePartitionValidationError(
                "dataset_ref_a must be QualifiedDatasetRef"
            )
        if not isinstance(self.dataset_ref_b, QualifiedDatasetRef):
            raise ResearchSamplePartitionValidationError(
                "dataset_ref_b must be QualifiedDatasetRef"
            )
        for field_name in (
            "dataset_id_equal",
            "revision_id_equal",
            "evidence_digest_equal",
            "exact_triple_equal",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ResearchSamplePartitionValidationError(
                    f"{field_name} must be bool"
                )
        if not (
            self.dataset_id_equal
            or self.revision_id_equal
            or self.evidence_digest_equal
        ):
            raise ResearchSamplePartitionValidationError(
                "at least one dataset overlap axis must be True"
            )
        expected_exact = (
            self.dataset_id_equal
            and self.revision_id_equal
            and self.evidence_digest_equal
        )
        if self.exact_triple_equal != expected_exact:
            raise ResearchSamplePartitionValidationError(
                "exact_triple_equal must equal the conjunction of dataset overlap axes"
            )


@dataclass(frozen=True, slots=True)
class ObservationOverlapEvidence:
    obs_ref_a: QualifiedObservationRef
    obs_ref_b: QualifiedObservationRef
    observation_id_equal: bool
    snapshot_id_equal: bool

    def __post_init__(self) -> None:
        if not isinstance(self.obs_ref_a, QualifiedObservationRef):
            raise ResearchSamplePartitionValidationError(
                "obs_ref_a must be QualifiedObservationRef"
            )
        if not isinstance(self.obs_ref_b, QualifiedObservationRef):
            raise ResearchSamplePartitionValidationError(
                "obs_ref_b must be QualifiedObservationRef"
            )
        if type(self.observation_id_equal) is not bool:
            raise ResearchSamplePartitionValidationError(
                "observation_id_equal must be bool"
            )
        if type(self.snapshot_id_equal) is not bool:
            raise ResearchSamplePartitionValidationError(
                "snapshot_id_equal must be bool"
            )
        if not self.observation_id_equal and not self.snapshot_id_equal:
            raise ResearchSamplePartitionValidationError(
                "at least one observation overlap axis must be True"
            )


@dataclass(frozen=True, slots=True)
class MarketTimeOverlapEvidence:
    obs_ref_a: QualifiedObservationRef
    obs_ref_b: QualifiedObservationRef
    source_a: ExternalSourceDescriptor
    source_b: ExternalSourceDescriptor
    instrument: Instrument
    timeframe: Timeframe
    interval_a_opened: datetime
    interval_a_closed: datetime
    interval_b_opened: datetime
    interval_b_closed: datetime
    exact_stream_overlap: bool
    market_coordinate_overlap: bool

    def __post_init__(self) -> None:
        if not isinstance(self.obs_ref_a, QualifiedObservationRef):
            raise ResearchSamplePartitionValidationError(
                "obs_ref_a must be QualifiedObservationRef"
            )
        if not isinstance(self.obs_ref_b, QualifiedObservationRef):
            raise ResearchSamplePartitionValidationError(
                "obs_ref_b must be QualifiedObservationRef"
            )
        if not isinstance(self.source_a, ExternalSourceDescriptor):
            raise ResearchSamplePartitionValidationError(
                "source_a must be ExternalSourceDescriptor"
            )
        if not isinstance(self.source_b, ExternalSourceDescriptor):
            raise ResearchSamplePartitionValidationError(
                "source_b must be ExternalSourceDescriptor"
            )
        if not isinstance(self.instrument, Instrument):
            raise ResearchSamplePartitionValidationError(
                "instrument must be Instrument"
            )
        if not isinstance(self.timeframe, Timeframe):
            raise ResearchSamplePartitionValidationError("timeframe must be Timeframe")
        _require_aware_datetime(self.interval_a_opened, field_name="interval_a_opened")
        _require_aware_datetime(self.interval_a_closed, field_name="interval_a_closed")
        _require_aware_datetime(self.interval_b_opened, field_name="interval_b_opened")
        _require_aware_datetime(self.interval_b_closed, field_name="interval_b_closed")
        if self.interval_a_closed <= self.interval_a_opened:
            raise ResearchSamplePartitionValidationError(
                "interval_a must have positive duration"
            )
        if self.interval_b_closed <= self.interval_b_opened:
            raise ResearchSamplePartitionValidationError(
                "interval_b must have positive duration"
            )
        if type(self.exact_stream_overlap) is not bool:
            raise ResearchSamplePartitionValidationError(
                "exact_stream_overlap must be bool"
            )
        if type(self.market_coordinate_overlap) is not bool:
            raise ResearchSamplePartitionValidationError(
                "market_coordinate_overlap must be bool"
            )
        if not self.market_coordinate_overlap:
            raise ResearchSamplePartitionValidationError(
                "market_coordinate_overlap must be True for retained market-time overlap"
            )
        if self.exact_stream_overlap != (self.source_a == self.source_b):
            raise ResearchSamplePartitionValidationError(
                "exact_stream_overlap must equal source equality"
            )
        if not (
            self.interval_a_opened < self.interval_b_closed
            and self.interval_b_opened < self.interval_a_closed
        ):
            raise ResearchSamplePartitionValidationError(
                "half-open intervals do not overlap"
            )


def _run_overlap_order_key(
    item: RunOverlapEvidence,
) -> tuple[tuple[int, int, str, str], tuple[int, int, str, str]]:
    return (
        _qualified_run_ref_order_key(item.run_ref_a),
        _qualified_run_ref_order_key(item.run_ref_b),
    )


def _dataset_overlap_order_key(
    item: DatasetOverlapEvidence,
) -> tuple[tuple[object, ...], tuple[object, ...]]:
    return (
        _qualified_dataset_ref_order_key(item.dataset_ref_a),
        _qualified_dataset_ref_order_key(item.dataset_ref_b),
    )


def _observation_overlap_order_key(
    item: ObservationOverlapEvidence,
) -> tuple[tuple[object, ...], tuple[object, ...]]:
    return (
        _qualified_observation_ref_order_key(item.obs_ref_a),
        _qualified_observation_ref_order_key(item.obs_ref_b),
    )


def _market_time_conflict_order_key(
    item: MarketTimeOverlapEvidence,
) -> tuple[object, ...]:
    return (
        item.instrument.symbol,
        item.timeframe.seconds,
        _external_source_order_key(item.source_a),
        _external_source_order_key(item.source_b),
        _utc_microseconds(item.interval_a_opened),
        _utc_microseconds(item.interval_a_closed),
        _utc_microseconds(item.interval_b_opened),
        _utc_microseconds(item.interval_b_closed),
        _qualified_observation_ref_order_key(item.obs_ref_a),
        _qualified_observation_ref_order_key(item.obs_ref_b),
    )


def _has_equal_duplicate(items: tuple[object, ...]) -> bool:
    for index, item in enumerate(items):
        if any(item == prior for prior in items[:index]):
            return True
    return False


@dataclass(frozen=True, slots=True)
class RolePairOverlapEvidence:
    role_a: SampleRole
    role_b: SampleRole
    run_overlaps: tuple[RunOverlapEvidence, ...]
    dataset_overlaps: tuple[DatasetOverlapEvidence, ...]
    observation_overlaps: tuple[ObservationOverlapEvidence, ...]
    market_time_overlaps: tuple[MarketTimeOverlapEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.role_a, SampleRole):
            raise ResearchSamplePartitionValidationError("role_a must be SampleRole")
        if not isinstance(self.role_b, SampleRole):
            raise ResearchSamplePartitionValidationError("role_b must be SampleRole")
        if _SAMPLE_ROLE_ORDER[self.role_a] >= _SAMPLE_ROLE_ORDER[self.role_b]:
            raise ResearchSamplePartitionValidationError(
                "role_a must precede role_b canonically"
            )
        self._validate_run_overlaps()
        self._validate_dataset_overlaps()
        self._validate_observation_overlaps()
        self._validate_market_time_overlaps()

    def _validate_run_overlaps(self) -> None:
        if not isinstance(self.run_overlaps, tuple):
            raise ResearchSamplePartitionValidationError("run_overlaps must be tuple")
        for index, item in enumerate(self.run_overlaps):
            if not isinstance(item, RunOverlapEvidence):
                raise ResearchSamplePartitionValidationError(
                    f"run_overlaps[{index}] must be RunOverlapEvidence"
                )
            if item.run_ref_a.role != self.role_a or item.run_ref_b.role != self.role_b:
                raise ResearchSamplePartitionValidationError(
                    "run overlap ref roles must match pair roles"
                )
        if self.run_overlaps != tuple(sorted(self.run_overlaps, key=_run_overlap_order_key)):
            raise ResearchSamplePartitionValidationError(
                "run_overlaps must be in canonical order"
            )
        if _has_equal_duplicate(tuple(self.run_overlaps)):
            raise ResearchSamplePartitionValidationError(
                "duplicate records in run_overlaps"
            )

    def _validate_dataset_overlaps(self) -> None:
        if not isinstance(self.dataset_overlaps, tuple):
            raise ResearchSamplePartitionValidationError("dataset_overlaps must be tuple")
        for index, item in enumerate(self.dataset_overlaps):
            if not isinstance(item, DatasetOverlapEvidence):
                raise ResearchSamplePartitionValidationError(
                    f"dataset_overlaps[{index}] must be DatasetOverlapEvidence"
                )
            if (
                item.dataset_ref_a.run_ref.role != self.role_a
                or item.dataset_ref_b.run_ref.role != self.role_b
            ):
                raise ResearchSamplePartitionValidationError(
                    "dataset overlap ref roles must match pair roles"
                )
        if self.dataset_overlaps != tuple(
            sorted(self.dataset_overlaps, key=_dataset_overlap_order_key)
        ):
            raise ResearchSamplePartitionValidationError(
                "dataset_overlaps must be in canonical order"
            )
        if _has_equal_duplicate(tuple(self.dataset_overlaps)):
            raise ResearchSamplePartitionValidationError(
                "duplicate records in dataset_overlaps"
            )

    def _validate_observation_overlaps(self) -> None:
        if not isinstance(self.observation_overlaps, tuple):
            raise ResearchSamplePartitionValidationError(
                "observation_overlaps must be tuple"
            )
        for index, item in enumerate(self.observation_overlaps):
            if not isinstance(item, ObservationOverlapEvidence):
                raise ResearchSamplePartitionValidationError(
                    f"observation_overlaps[{index}] must be ObservationOverlapEvidence"
                )
            if (
                item.obs_ref_a.dataset_ref.run_ref.role != self.role_a
                or item.obs_ref_b.dataset_ref.run_ref.role != self.role_b
            ):
                raise ResearchSamplePartitionValidationError(
                    "observation overlap ref roles must match pair roles"
                )
        if self.observation_overlaps != tuple(
            sorted(self.observation_overlaps, key=_observation_overlap_order_key)
        ):
            raise ResearchSamplePartitionValidationError(
                "observation_overlaps must be in canonical order"
            )
        if _has_equal_duplicate(tuple(self.observation_overlaps)):
            raise ResearchSamplePartitionValidationError(
                "duplicate records in observation_overlaps"
            )

    def _validate_market_time_overlaps(self) -> None:
        if not isinstance(self.market_time_overlaps, tuple):
            raise ResearchSamplePartitionValidationError(
                "market_time_overlaps must be tuple"
            )
        for index, item in enumerate(self.market_time_overlaps):
            if not isinstance(item, MarketTimeOverlapEvidence):
                raise ResearchSamplePartitionValidationError(
                    f"market_time_overlaps[{index}] must be MarketTimeOverlapEvidence"
                )
            if (
                item.obs_ref_a.dataset_ref.run_ref.role != self.role_a
                or item.obs_ref_b.dataset_ref.run_ref.role != self.role_b
            ):
                raise ResearchSamplePartitionValidationError(
                    "market-time overlap ref roles must match pair roles"
                )
        if self.market_time_overlaps != tuple(
            sorted(self.market_time_overlaps, key=_market_time_conflict_order_key)
        ):
            raise ResearchSamplePartitionValidationError(
                "market_time_overlaps must be in canonical order"
            )
        if _has_equal_duplicate(tuple(self.market_time_overlaps)):
            raise ResearchSamplePartitionValidationError(
                "duplicate records in market_time_overlaps"
            )


@dataclass(frozen=True, slots=True)
class OverlapReport:
    pairwise: tuple[RolePairOverlapEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.pairwise, tuple):
            raise ResearchSamplePartitionValidationError("pairwise must be tuple")
        if len(self.pairwise) != 3:
            raise ResearchSamplePartitionValidationError(
                "pairwise must contain exactly three role pairs"
            )
        for index, pair in enumerate(self.pairwise):
            if not isinstance(pair, RolePairOverlapEvidence):
                raise ResearchSamplePartitionValidationError(
                    f"pairwise[{index}] must be RolePairOverlapEvidence"
                )
        expected = (
            (SampleRole.DEVELOPMENT, SampleRole.CALIBRATION),
            (SampleRole.DEVELOPMENT, SampleRole.EXTERNAL_VALIDATION),
            (SampleRole.CALIBRATION, SampleRole.EXTERNAL_VALIDATION),
        )
        actual = tuple((pair.role_a, pair.role_b) for pair in self.pairwise)
        if actual != expected:
            raise ResearchSamplePartitionValidationError(
                "pairwise role pairs must use exact canonical order"
            )


def _qualified_run_total_order_key(
    run: IntegrityQualifiedResearchRun,
) -> tuple[str, str, str, str]:
    if not isinstance(run, IntegrityQualifiedResearchRun):
        raise ResearchSamplePartitionValidationError(
            "qualified run must be IntegrityQualifiedResearchRun"
        )
    return (
        str(run.run.run_id.value),
        _utc_microseconds(run.run.created_at),
        run.run.input_fingerprint.value,
        run.fingerprint.value,
    )


@dataclass(frozen=True, slots=True)
class SampleRoleAssignment:
    role: SampleRole
    qualified_runs: tuple[IntegrityQualifiedResearchRun, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.role, SampleRole):
            raise ResearchSamplePartitionValidationError("role must be SampleRole")
        if not isinstance(self.qualified_runs, tuple) or not self.qualified_runs:
            raise ResearchSamplePartitionValidationError(
                "qualified_runs must be a non-empty tuple"
            )
        for index, run in enumerate(self.qualified_runs):
            if not isinstance(run, IntegrityQualifiedResearchRun):
                raise ResearchSamplePartitionValidationError(
                    f"qualified_runs[{index}] must be IntegrityQualifiedResearchRun"
                )
        if _has_equal_duplicate(tuple(self.qualified_runs)):
            raise ResearchSamplePartitionValidationError("duplicate exact qualified run")
        canonical = tuple(sorted(self.qualified_runs, key=_qualified_run_total_order_key))
        if self.qualified_runs != canonical:
            raise ResearchSamplePartitionValidationError(
                "qualified_runs must be in canonical total order"
            )


def _validate_partition_assignments_tuple(
    assignments: tuple[SampleRoleAssignment, ...],
) -> tuple[SampleRoleAssignment, ...]:
    if not isinstance(assignments, tuple):
        raise ResearchSamplePartitionValidationError("assignments must be tuple")
    if len(assignments) != 3:
        raise ResearchSamplePartitionValidationError(
            "assignments must contain exactly three role assignments"
        )
    for index, assignment in enumerate(assignments):
        if not isinstance(assignment, SampleRoleAssignment):
            raise ResearchSamplePartitionValidationError(
                f"assignments[{index}] must be SampleRoleAssignment"
            )
    expected_roles = (
        SampleRole.DEVELOPMENT,
        SampleRole.CALRATION if False else SampleRole.CALIBRATION,
        SampleRole.EXTERNAL_VALIDATION,
    )
    actual_roles = tuple(assignment.role for assignment in assignments)
    if actual_roles != expected_roles:
        raise ResearchSamplePartitionValidationError(
            "assignments must use canonical role order"
        )
    return assignments


def _resolve_qualified_run(
    assignments: tuple[SampleRoleAssignment, ...],
    ref: QualifiedRunRef,
) -> IntegrityQualifiedResearchRun:
    _validate_partition_assignments_tuple(assignments)
    if not isinstance(ref, QualifiedRunRef):
        raise ResearchSamplePartitionValidationError("ref must be QualifiedRunRef")
    slot = _SAMPLE_ROLE_ORDER[ref.role]
    assignment = assignments[slot]
    if assignment.role != ref.role:
        raise ResearchSamplePartitionValidationError(
            "reference role does not match assignment slot"
        )
    if ref.canonical_run_index >= len(assignment.qualified_runs):
        raise ResearchSamplePartitionValidationError("run index out of range")
    run = assignment.qualified_runs[ref.canonical_run_index]
    if run.run.run_id != ref.run_id:
        raise ResearchSamplePartitionValidationError("run_id mismatch")
    if run.fingerprint != ref.qualified_run_fingerprint:
        raise ResearchSamplePartitionValidationError("qualified_run_fingerprint mismatch")
    return run


def _resolve_qualified_dataset(
    assignments: tuple[SampleRoleAssignment, ...],
    ref: QualifiedDatasetRef,
) -> DatasetIntegrityQualification:
    if not isinstance(ref, QualifiedDatasetRef):
        raise ResearchSamplePartitionValidationError("ref must be QualifiedDatasetRef")
    run = _resolve_qualified_run(assignments, ref.run_ref)
    if ref.qualification_index >= len(run.qualifications):
        raise ResearchSamplePartitionValidationError("qualification index out of range")
    qualification = run.qualifications[ref.qualification_index]
    manifest = qualification.dataset.manifest
    if manifest.dataset_id != ref.dataset_id:
        raise ResearchSamplePartitionValidationError("dataset_id mismatch")
    if manifest.revision_id != ref.revision_id:
        raise ResearchSamplePartitionValidationError("revision_id mismatch")
    if manifest.evidence_digest != ref.evidence_digest:
        raise ResearchSamplePartitionValidationError("evidence_digest mismatch")
    return qualification


def _resolve_observation(
    assignments: tuple[SampleRoleAssignment, ...],
    ref: QualifiedObservationRef,
) -> ReplayMarketDataObservation:
    if not isinstance(ref, QualifiedObservationRef):
        raise ResearchSamplePartitionValidationError("ref must be QualifiedObservationRef")
    qualification = _resolve_qualified_dataset(assignments, ref.dataset_ref)
    observations = qualification.dataset.observations
    if ref.observation_index >= len(observations):
        raise ResearchSamplePartitionValidationError("observation index out of range")
    observation = observations[ref.observation_index]
    if observation.observation_id != ref.observation_id:
        raise ResearchSamplePartitionValidationError("observation_id mismatch")
    if not isinstance(observation.payload, OhlcSnapshot):
        raise ResearchSamplePartitionValidationError("payload must be OhlcSnapshot")
    if observation.payload.snapshot_id != ref.snapshot_id:
        raise ResearchSamplePartitionValidationError("snapshot_id mismatch")
    return observation


def _run_ref(
    role: SampleRole,
    index: int,
    run: IntegrityQualifiedResearchRun,
) -> QualifiedRunRef:
    return QualifiedRunRef(
        role=role,
        canonical_run_index=index,
        run_id=run.run.run_id,
        qualified_run_fingerprint=run.fingerprint,
    )


def _dataset_ref(
    run_ref: QualifiedRunRef,
    qualification_index: int,
    qualification: DatasetIntegrityQualification,
) -> QualifiedDatasetRef:
    manifest = qualification.dataset.manifest
    return QualifiedDatasetRef(
        run_ref=run_ref,
        qualification_index=qualification_index,
        dataset_id=manifest.dataset_id,
        revision_id=manifest.revision_id,
        evidence_digest=manifest.evidence_digest,
    )


def _observation_ref(
    dataset_ref: QualifiedDatasetRef,
    observation_index: int,
    observation: ReplayMarketDataObservation,
) -> QualifiedObservationRef:
    if not isinstance(observation.payload, OhlcSnapshot):
        raise ResearchSamplePartitionValidationError(
            "sample partition requires OhlcSnapshot observations"
        )
    return QualifiedObservationRef(
        dataset_ref=dataset_ref,
        observation_index=observation_index,
        observation_id=observation.observation_id,
        snapshot_id=observation.payload.snapshot_id,
    )


def _qualified_datasets(
    role: SampleRole,
    assignment: SampleRoleAssignment,
) -> tuple[tuple[QualifiedDatasetRef, DatasetIntegrityQualification], ...]:
    items: list[tuple[QualifiedDatasetRef, DatasetIntegrityQualification]] = []
    for run_index, run in enumerate(assignment.qualified_runs):
        run_ref = _run_ref(role, run_index, run)
        for qualification_index, qualification in enumerate(run.qualifications):
            items.append(
                (
                    _dataset_ref(run_ref, qualification_index, qualification),
                    qualification,
                )
            )
    return tuple(items)


def _qualified_observations(
    role: SampleRole,
    assignment: SampleRoleAssignment,
) -> tuple[tuple[QualifiedObservationRef, ReplayMarketDataObservation], ...]:
    items: list[tuple[QualifiedObservationRef, ReplayMarketDataObservation]] = []
    for dataset_ref, qualification in _qualified_datasets(role, assignment):
        for observation_index, observation in enumerate(
            qualification.dataset.observations
        ):
            items.append(
                (
                    _observation_ref(dataset_ref, observation_index, observation),
                    observation,
                )
            )
    return tuple(items)


def _derive_role_pair(
    role_a: SampleRole,
    assignment_a: SampleRoleAssignment,
    role_b: SampleRole,
    assignment_b: SampleRoleAssignment,
) -> RolePairOverlapEvidence:
    run_overlaps: list[RunOverlapEvidence] = []
    for run_index_a, run_a in enumerate(assignment_a.qualified_runs):
        run_ref_a = _run_ref(role_a, run_index_a, run_a)
        for run_index_b, run_b in enumerate(assignment_b.qualified_runs):
            run_ref_b = _run_ref(role_b, run_index_b, run_b)
            exact_qualified = run_a == run_b
            exact_run = run_a.run == run_b.run
            run_id_equal = run_a.run.run_id == run_b.run.run_id
            input_equal = run_a.run.input_fingerprint == run_b.run.input_fingerprint
            if exact_qualified or exact_run or run_id_equal or input_equal:
                run_overlaps.append(
                    RunOverlapEvidence(
                        run_ref_a=run_ref_a,
                        run_ref_b=run_ref_b,
                        exact_qualified_run_equal=exact_qualified,
                        exact_run_equal=exact_run,
                        run_id_equal=run_id_equal,
                        run_input_fingerprint_equal=input_equal,
                    )
                )

    datasets_a = _qualified_datasets(role_a, assignment_a)
    datasets_b = _qualified_datasets(role_b, assignment_b)
    dataset_overlaps: list[DatasetOverlapEvidence] = []
    for dataset_ref_a, qualification_a in datasets_a:
        manifest_a = qualification_a.dataset.manifest
        for dataset_ref_b, qualification_b in datasets_b:
            manifest_b = qualification_b.dataset.manifest
            dataset_id_equal = manifest_a.dataset_id == manifest_b.dataset_id
            revision_id_equal = manifest_a.revision_id == manifest_b.revision_id
            digest_equal = manifest_a.evidence_digest == manifest_b.evidence_digest
            if dataset_id_equal or revision_id_equal or digest_equal:
                dataset_overlaps.append(
                    DatasetOverlapEvidence(
                        dataset_ref_a=dataset_ref_a,
                        dataset_ref_b=dataset_ref_b,
                        dataset_id_equal=dataset_id_equal,
                        revision_id_equal=revision_id_equal,
                        evidence_digest_equal=digest_equal,
                        exact_triple_equal=(
                            dataset_id_equal and revision_id_equal and digest_equal
                        ),
                    )
                )

    observations_a = _qualified_observations(role_a, assignment_a)
    observations_b = _qualified_observations(role_b, assignment_b)
    observation_overlaps: list[ObservationOverlapEvidence] = []
    market_time_overlaps: list[MarketTimeOverlapEvidence] = []
    for observation_ref_a, observation_a in observations_a:
        payload_a = observation_a.payload
        if not isinstance(payload_a, OhlcSnapshot):
            raise ResearchSamplePartitionValidationError(
                "sample partition requires OhlcSnapshot observations"
            )
        for observation_ref_b, observation_b in observations_b:
            payload_b = observation_b.payload
            if not isinstance(payload_b, OhlcSnapshot):
                raise ResearchSamplePartitionValidationError(
                    "sample partition requires OhlcSnapshot observations"
                )
            observation_id_equal = (
                observation_a.observation_id == observation_b.observation_id
            )
            snapshot_id_equal = payload_a.snapshot_id == payload_b.snapshot_id
            if observation_id_equal or snapshot_id_equal:
                observation_overlaps.append(
                    ObservationOverlapEvidence(
                        obs_ref_a=observation_ref_a,
                        obs_ref_b=observation_ref_b,
                        observation_id_equal=observation_id_equal,
                        snapshot_id_equal=snapshot_id_equal,
                    )
                )
            if (
                payload_a.instrument == payload_b.instrument
                and payload_a.timeframe == payload_b.timeframe
                and payload_a.opened_at < payload_b.closed_at
                and payload_b.opened_at < payload_a.closed_at
            ):
                market_time_overlaps.append(
                    MarketTimeOverlapEvidence(
                        obs_ref_a=observation_ref_a,
                        obs_ref_b=observation_ref_b,
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
                )

    return RolePairOverlapEvidence(
        role_a=role_a,
        role_b=role_b,
        run_overlaps=tuple(sorted(run_overlaps, key=_run_overlap_order_key)),
        dataset_overlaps=tuple(
            sorted(dataset_overlaps, key=_dataset_overlap_order_key)
        ),
        observation_overlaps=tuple(
            sorted(observation_overlaps, key=_observation_overlap_order_key)
        ),
        market_time_overlaps=tuple(
            sorted(market_time_overlaps, key=_market_time_conflict_order_key)
        ),
    )


def _derive_overlap_report(
    assignments: tuple[SampleRoleAssignment, ...],
) -> OverlapReport:
    validated = _validate_partition_assignments_tuple(assignments)
    development, calibration, external_validation = validated
    return OverlapReport(
        pairwise=(
            _derive_role_pair(
                SampleRole.DEVELOPMENT,
                development,
                SampleRole.CALIBRATION,
                calibration,
            ),
            _derive_role_pair(
                SampleRole.DEVELOPMENT,
                development,
                SampleRole.EXTERNAL_VALIDATION,
                external_validation,
            ),
            _derive_role_pair(
                SampleRole.CALIBRATION,
                calibration,
                SampleRole.EXTERNAL_VALIDATION,
                external_validation,
            ),
        )
    )


def _canonical_qualified_run_ref(ref: QualifiedRunRef) -> dict[str, object]:
    return {
        "role": ref.role.value,
        "canonical_run_index": ref.canonical_run_index,
        "run_id": str(ref.run_id.value),
        "qualified_run_fingerprint": ref.qualified_run_fingerprint.value,
    }


def _canonical_dataset_ref(ref: QualifiedDatasetRef) -> dict[str, object]:
    return {
        "run_ref": _canonical_qualified_run_ref(ref.run_ref),
        "qualification_index": ref.qualification_index,
        "dataset_id": str(ref.dataset_id.value),
        "revision_id": str(ref.revision_id.value),
        "evidence_digest": ref.evidence_digest.value,
    }


def _canonical_observation_ref(ref: QualifiedObservationRef) -> dict[str, object]:
    return {
        "dataset_ref": _canonical_dataset_ref(ref.dataset_ref),
        "observation_index": ref.observation_index,
        "observation_id": str(ref.observation_id.value),
        "snapshot_id": str(ref.snapshot_id.value),
    }


def _canonical_external_source(source: ExternalSourceDescriptor) -> dict[str, object]:
    return {
        "adapter_id": str(source.adapter_id.value),
        "source_id": str(source.source_id.value),
        "port_name": source.port_name.value,
    }


def _canonical_run_commitment(
    run: IntegrityQualifiedResearchRun,
) -> dict[str, object]:
    return {
        "run_id": str(run.run.run_id.value),
        "created_at": _utc_microseconds(run.run.created_at),
        "input_fingerprint": run.run.input_fingerprint.value,
        "qualified_run_fingerprint": run.fingerprint.value,
    }


def _canonical_run_overlap(item: RunOverlapEvidence) -> dict[str, object]:
    return {
        "run_ref_a": _canonical_qualified_run_ref(item.run_ref_a),
        "run_ref_b": _canonical_qualified_run_ref(item.run_ref_b),
        "exact_qualified_run_equal": item.exact_qualified_run_equal,
        "exact_run_equal": item.exact_run_equal,
        "run_id_equal": item.run_id_equal,
        "run_input_fingerprint_equal": item.run_input_fingerprint_equal,
    }


def _canonical_dataset_overlap(item: DatasetOverlapEvidence) -> dict[str, object]:
    return {
        "dataset_ref_a": _canonical_dataset_ref(item.dataset_ref_a),
        "dataset_ref_b": _canonical_dataset_ref(item.dataset_ref_b),
        "dataset_id_equal": item.dataset_id_equal,
        "revision_id_equal": item.revision_id_equal,
        "evidence_digest_equal": item.evidence_digest_equal,
        "exact_triple_equal": item.exact_triple_equal,
    }


def _canonical_observation_overlap(
    item: ObservationOverlapEvidence,
) -> dict[str, object]:
    return {
        "obs_ref_a": _canonical_observation_ref(item.obs_ref_a),
        "obs_ref_b": _canonical_observation_ref(item.obs_ref_b),
        "observation_id_equal": item.observation_id_equal,
        "snapshot_id_equal": item.snapshot_id_equal,
    }


def _canonical_market_time_overlap(
    item: MarketTimeOverlapEvidence,
) -> dict[str, object]:
    return {
        "obs_ref_a": _canonical_observation_ref(item.obs_ref_a),
        "obs_ref_b": _canonical_observation_ref(item.obs_ref_b),
        "source_a": _canonical_external_source(item.source_a),
        "source_b": _canonical_external_source(item.source_b),
        "instrument": item.instrument.symbol,
        "timeframe_seconds": item.timeframe.seconds,
        "interval_a_opened": _utc_microseconds(item.interval_a_opened),
        "interval_a_closed": _utc_microseconds(item.interval_a_closed),
        "interval_b_opened": _utc_microseconds(item.interval_b_opened),
        "interval_b_closed": _utc_microseconds(item.interval_b_closed),
        "exact_stream_overlap": item.exact_stream_overlap,
        "market_coordinate_overlap": item.market_coordinate_overlap,
    }


def _canonical_role_pair_overlap(
    pair: RolePairOverlapEvidence,
) -> dict[str, object]:
    return {
        "role_a": pair.role_a.value,
        "role_b": pair.role_b.value,
        "run_overlaps": [_canonical_run_overlap(item) for item in pair.run_overlaps],
        "dataset_overlaps": [
            _canonical_dataset_overlap(item) for item in pair.dataset_overlaps
        ],
        "observation_overlaps": [
            _canonical_observation_overlap(item) for item in pair.observation_overlaps
        ],
        "market_time_overlaps": [
            _canonical_market_time_overlap(item) for item in pair.market_time_overlaps
        ],
    }


def _canonical_overlap_report(report: OverlapReport) -> dict[str, object]:
    return {
        "pairwise": [_canonical_role_pair_overlap(pair) for pair in report.pairwise]
    }


def _canonical_role_assignment(
    assignment: SampleRoleAssignment,
) -> dict[str, object]:
    return {
        "role": assignment.role.value,
        "qualified_runs": [
            _canonical_run_commitment(run) for run in assignment.qualified_runs
        ],
    }


def _compute_partition_fingerprint(
    assignments: tuple[SampleRoleAssignment, ...],
    overlap_report: OverlapReport,
) -> SamplePartitionFingerprint:
    _validate_partition_assignments_tuple(assignments)
    if not isinstance(overlap_report, OverlapReport):
        raise ResearchSamplePartitionValidationError(
            "overlap_report must be OverlapReport"
        )
    canonical: dict[str, object] = {
        "schema": _PARTITION_SCHEMA,
        "market_time_semantics": _MARKET_TIME_SEMANTICS,
        "assignments": [
            _canonical_role_assignment(assignment) for assignment in assignments
        ],
        "overlap_report": _canonical_overlap_report(overlap_report),
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return SamplePartitionFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class SamplePartitionEvidence:
    assignments: tuple[SampleRoleAssignment, ...]
    derived_overlap_report: OverlapReport
    fingerprint: SamplePartitionFingerprint

    def __post_init__(self) -> None:
        _validate_partition_assignments_tuple(self.assignments)
        if not isinstance(self.derived_overlap_report, OverlapReport):
            raise ResearchSamplePartitionValidationError(
                "derived_overlap_report must be OverlapReport"
            )
        recomputed_report = _derive_overlap_report(self.assignments)
        if recomputed_report != self.derived_overlap_report:
            raise ResearchSamplePartitionValidationError(
                "overlap report does not match derived report"
            )
        if not isinstance(self.fingerprint, SamplePartitionFingerprint):
            raise ResearchSamplePartitionValidationError(
                "fingerprint must be SamplePartitionFingerprint"
            )
        recomputed_fingerprint = _compute_partition_fingerprint(
            self.assignments,
            self.derived_overlap_report,
        )
        if recomputed_fingerprint != self.fingerprint:
            raise ResearchSamplePartitionValidationError("fingerprint mismatch")


@dataclass(frozen=True, slots=True)
class SamplePartitionDisjointnessEvidence:
    source_partition: SamplePartitionEvidence
    exact_qualified_run_disjoint: bool = field(init=False)
    exact_run_evidence_disjoint: bool = field(init=False)
    run_id_disjoint: bool = field(init=False)
    run_input_fingerprint_disjoint: bool = field(init=False)
    dataset_id_disjoint: bool = field(init=False)
    revision_id_disjoint: bool = field(init=False)
    evidence_digest_disjoint: bool = field(init=False)
    observation_id_disjoint: bool = field(init=False)
    snapshot_id_disjoint: bool = field(init=False)
    exact_stream_market_time_disjoint: bool = field(init=False)
    market_coordinate_time_disjoint: bool = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source_partition, SamplePartitionEvidence):
            raise ResearchSamplePartitionValidationError(
                "source_partition must be SamplePartitionEvidence"
            )
        report = self.source_partition.derived_overlap_report
        run_items = tuple(item for pair in report.pairwise for item in pair.run_overlaps)
        dataset_items = tuple(
            item for pair in report.pairwise for item in pair.dataset_overlaps
        )
        observation_items = tuple(
            item for pair in report.pairwise for item in pair.observation_overlaps
        )
        market_items = tuple(
            item for pair in report.pairwise for item in pair.market_time_overlaps
        )
        object.__setattr__(
            self,
            "exact_qualified_run_disjoint",
            not any(item.exact_qualified_run_equal for item in run_items),
        )
        object.__setattr__(
            self,
            "exact_run_evidence_disjoint",
            not any(item.exact_run_equal for item in run_items),
        )
        object.__setattr__(
            self,
            "run_id_disjoint",
            not any(item.run_id_equal for item in run_items),
        )
        object.__setattr__(
            self,
            "run_input_fingerprint_disjoint",
            not any(item.run_input_fingerprint_equal for item in run_items),
        )
        object.__setattr__(
            self,
            "dataset_id_disjoint",
            not any(item.dataset_id_equal for item in dataset_items),
        )
        object.__setattr__(
            self,
            "revision_id_disjoint",
            not any(item.revision_id_equal for item in dataset_items),
        )
        object.__setattr__(
            self,
            "evidence_digest_disjoint",
            not any(item.evidence_digest_equal for item in dataset_items),
        )
        object.__setattr__(
            self,
            "observation_id_disjoint",
            not any(item.observation_id_equal for item in observation_items),
        )
        object.__setattr__(
            self,
            "snapshot_id_disjoint",
            not any(item.snapshot_id_equal for item in observation_items),
        )
        object.__setattr__(
            self,
            "exact_stream_market_time_disjoint",
            not any(item.exact_stream_overlap for item in market_items),
        )
        object.__setattr__(
            self,
            "market_coordinate_time_disjoint",
            not any(item.market_coordinate_overlap for item in market_items),
        )


def build_sample_role_assignment(
    *,
    role: SampleRole,
    qualified_runs: tuple[IntegrityQualifiedResearchRun, ...],
) -> Result[SampleRoleAssignment, ResearchSamplePartitionError]:
    try:
        if not isinstance(role, SampleRole):
            raise ResearchSamplePartitionValidationError("role must be SampleRole")
        if not isinstance(qualified_runs, tuple) or not qualified_runs:
            raise ResearchSamplePartitionValidationError(
                "qualified_runs must be a non-empty tuple"
            )
        for index, run in enumerate(qualified_runs):
            if not isinstance(run, IntegrityQualifiedResearchRun):
                raise ResearchSamplePartitionValidationError(
                    f"qualified_runs[{index}] must be IntegrityQualifiedResearchRun"
                )
        if _has_equal_duplicate(tuple(qualified_runs)):
            raise ResearchSamplePartitionValidationError("duplicate exact qualified run")
        canonical_runs = tuple(sorted(qualified_runs, key=_qualified_run_total_order_key))
        return Success(
            SampleRoleAssignment(
                role=role,
                qualified_runs=canonical_runs,
            )
        )
    except ResearchSamplePartitionError as error:
        return Failure(error)


def build_sample_partition_evidence(
    *,
    assignments: tuple[SampleRoleAssignment, ...],
) -> Result[SamplePartitionEvidence, ResearchSamplePartitionError]:
    try:
        validated = _validate_partition_assignments_tuple(assignments)
        report = _derive_overlap_report(validated)
        fingerprint = _compute_partition_fingerprint(validated, report)
        return Success(
            SamplePartitionEvidence(
                assignments=validated,
                derived_overlap_report=report,
                fingerprint=fingerprint,
            )
        )
    except ResearchSamplePartitionError as error:
        return Failure(error)
