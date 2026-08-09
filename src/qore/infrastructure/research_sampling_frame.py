from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.research_economic_evidence import (
    ResearchGrossEconomicResult,
    ResearchNetEconomicResult,
    ResearchReturnObservation,
    ResearchReturnObservationId,
)
from qore.infrastructure.research_frozen_oos_evidence import ResearchFrozenOosEvidence
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchSamplingFrameError(InfrastructureError):
    """Base error for explicit OOS sampling-frame evidence."""

    __slots__ = ()


class ResearchSamplingFrameValidationError(ResearchSamplingFrameError):
    """Violation of a research sampling-frame invariant."""

    __slots__ = ()


class ResearchSamplingUnit(StrEnum):
    CLOSED_ECONOMIC_RESULT_RETURN = "closed_economic_result_return"


class ResearchHoldingOverlapStatus(StrEnum):
    NON_OVERLAPPING = "non_overlapping"
    OVERLAPPING = "overlapping"


@dataclass(frozen=True, slots=True)
class ResearchSamplingFrameId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchSamplingFrameValidationError(
                "sampling frame id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchHoldingInterval:
    """Half-open exposure interval [opened_at, closed_at) for one return sample."""

    observation_id: ResearchReturnObservationId
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, ResearchReturnObservationId):
            raise ResearchSamplingFrameValidationError(
                "holding interval observation_id must be ResearchReturnObservationId"
            )
        for field_name, value in (
            ("opened_at", self.opened_at),
            ("closed_at", self.closed_at),
        ):
            if not isinstance(value, datetime):
                raise ResearchSamplingFrameValidationError(
                    f"holding interval {field_name} must be datetime"
                )
            if value.tzinfo is None or value.utcoffset() is None:
                raise ResearchSamplingFrameValidationError(
                    f"holding interval {field_name} must be timezone-aware"
                )
        if self.closed_at < self.opened_at:
            raise ResearchSamplingFrameValidationError(
                "holding interval closed_at must not predate opened_at"
            )

    def logical_values(self) -> tuple[str, str, str]:
        return (
            str(self.observation_id.value),
            self.opened_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.closed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


def _gross_result(
    observation: ResearchReturnObservation,
) -> ResearchGrossEconomicResult:
    source = observation.source_result
    if isinstance(source, ResearchNetEconomicResult):
        return source.gross_result
    if not isinstance(source, ResearchGrossEconomicResult):
        raise ResearchSamplingFrameValidationError(
            "sampling return source must be gross or net economic result"
        )
    return source


def _holding_interval(observation: ResearchReturnObservation) -> ResearchHoldingInterval:
    gross = _gross_result(observation)
    if not gross.entry_fills or not gross.exit_fills:
        raise ResearchSamplingFrameValidationError(
            "sampling return requires non-empty entry and exit fill evidence"
        )
    opened_at = min(fill.filled_at for fill in gross.entry_fills)
    closed_at = max(fill.filled_at for fill in gross.exit_fills)
    return ResearchHoldingInterval(
        observation_id=observation.observation_id,
        opened_at=opened_at,
        closed_at=closed_at,
    )


def _canonical_samples(
    frozen_oos: ResearchFrozenOosEvidence,
) -> tuple[tuple[ResearchReturnObservation, ...], tuple[int, ...]]:
    if not isinstance(frozen_oos, ResearchFrozenOosEvidence):
        raise ResearchSamplingFrameValidationError(
            "sampling frame requires ResearchFrozenOosEvidence"
        )
    fold_performance = frozen_oos.oos_performance.fold_performance
    fold_sizes = tuple(len(item.statistics.observations) for item in fold_performance)
    samples = tuple(
        observation
        for item in fold_performance
        for observation in item.statistics.observations
    )
    if not samples or any(not isinstance(item, ResearchReturnObservation) for item in samples):
        raise ResearchSamplingFrameValidationError(
            "sampling frame requires non-empty ResearchReturnObservation evidence"
        )
    observation_ids = tuple(item.observation_id for item in samples)
    if len(set(observation_ids)) != len(observation_ids):
        raise ResearchSamplingFrameValidationError(
            "sampling frame return observation ids must be unique"
        )
    ordered = tuple(
        sorted(
            samples,
            key=lambda item: (
                item.source_result.valued_at.astimezone(UTC),
                str(item.observation_id.value),
            ),
        )
    )
    return ordered, fold_sizes


def _overlapping_pairs(
    intervals: tuple[ResearchHoldingInterval, ...],
) -> tuple[tuple[ResearchReturnObservationId, ResearchReturnObservationId], ...]:
    pairs: list[tuple[ResearchReturnObservationId, ResearchReturnObservationId]] = []
    for index, left in enumerate(intervals):
        for right in intervals[index + 1 :]:
            if max(left.opened_at, right.opened_at) < min(left.closed_at, right.closed_at):
                first, second = sorted(
                    (left.observation_id, right.observation_id),
                    key=lambda item: str(item.value),
                )
                pairs.append((first, second))
    return tuple(
        sorted(
            pairs,
            key=lambda pair: (str(pair[0].value), str(pair[1].value)),
        )
    )


@dataclass(frozen=True, slots=True)
class ResearchSamplingFrame:
    """Explicit sample frame derived only from frozen-strategy OOS return evidence.

    The sampling unit is one closed economic-result return observation. Holding
    overlap is measured from actual entry/exit fill timestamps. NON_OVERLAPPING
    means only that exposure intervals do not overlap; it is not evidence that
    returns are IID, independent, stationary, normally distributed, or free from
    common market/regime dependence.
    """

    frame_id: ResearchSamplingFrameId
    frozen_oos: ResearchFrozenOosEvidence
    sampling_unit: ResearchSamplingUnit
    samples: tuple[ResearchReturnObservation, ...]
    fold_sample_sizes: tuple[int, ...]
    holding_intervals: tuple[ResearchHoldingInterval, ...]
    overlap_status: ResearchHoldingOverlapStatus
    overlapping_pairs: tuple[
        tuple[ResearchReturnObservationId, ResearchReturnObservationId], ...
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.frame_id, ResearchSamplingFrameId):
            raise ResearchSamplingFrameValidationError(
                "frame_id must be ResearchSamplingFrameId"
            )
        if not isinstance(self.frozen_oos, ResearchFrozenOosEvidence):
            raise ResearchSamplingFrameValidationError(
                "sampling frame requires ResearchFrozenOosEvidence"
            )
        if self.sampling_unit is not ResearchSamplingUnit.CLOSED_ECONOMIC_RESULT_RETURN:
            raise ResearchSamplingFrameValidationError(
                "sampling frame unit must be closed economic-result return"
            )
        expected_samples, expected_fold_sizes = _canonical_samples(self.frozen_oos)
        if self.samples != expected_samples:
            raise ResearchSamplingFrameValidationError(
                "sampling frame samples must equal canonical frozen OOS returns"
            )
        if self.fold_sample_sizes != expected_fold_sizes:
            raise ResearchSamplingFrameValidationError(
                "fold sample sizes must equal frozen OOS fold evidence"
            )
        expected_intervals = tuple(_holding_interval(item) for item in self.samples)
        if self.holding_intervals != expected_intervals:
            raise ResearchSamplingFrameValidationError(
                "holding intervals must equal actual fill-derived sample intervals"
            )
        expected_pairs = _overlapping_pairs(expected_intervals)
        if self.overlapping_pairs != expected_pairs:
            raise ResearchSamplingFrameValidationError(
                "overlapping pairs must equal fill-derived overlap evidence"
            )
        expected_status = (
            ResearchHoldingOverlapStatus.OVERLAPPING
            if expected_pairs
            else ResearchHoldingOverlapStatus.NON_OVERLAPPING
        )
        if self.overlap_status is not expected_status:
            raise ResearchSamplingFrameValidationError(
                "overlap status must match fill-derived holding intervals"
            )

    @property
    def sample_size(self) -> int:
        return len(self.samples)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.frame_id.logical_values(),
            self.frozen_oos.logical_values(),
            self.sampling_unit.value,
            tuple(item.logical_values() for item in self.samples),
            self.fold_sample_sizes,
            tuple(item.logical_values() for item in self.holding_intervals),
            self.overlap_status.value,
            tuple(
                (str(first.value), str(second.value))
                for first, second in self.overlapping_pairs
            ),
        )


def build_research_sampling_frame(
    *,
    frame_id: ResearchSamplingFrameId,
    frozen_oos: ResearchFrozenOosEvidence,
) -> Result[ResearchSamplingFrame, ResearchSamplingFrameError]:
    """Derive an explicit OOS sample frame without making inference claims."""

    try:
        samples, fold_sizes = _canonical_samples(frozen_oos)
        intervals = tuple(_holding_interval(item) for item in samples)
        pairs = _overlapping_pairs(intervals)
        status = (
            ResearchHoldingOverlapStatus.OVERLAPPING
            if pairs
            else ResearchHoldingOverlapStatus.NON_OVERLAPPING
        )
        return Success(
            ResearchSamplingFrame(
                frame_id=frame_id,
                frozen_oos=frozen_oos,
                sampling_unit=ResearchSamplingUnit.CLOSED_ECONOMIC_RESULT_RETURN,
                samples=samples,
                fold_sample_sizes=fold_sizes,
                holding_intervals=intervals,
                overlap_status=status,
                overlapping_pairs=pairs,
            )
        )
    except ResearchSamplingFrameError as error:
        return Failure(error)
