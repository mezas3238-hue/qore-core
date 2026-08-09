from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from qore.infrastructure.research_economic_evidence import (
    ResearchReturnBasis,
    ResearchReturnObservation,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceSnapshotId,
    ResearchPerformanceStatisticsSnapshot,
    build_research_performance_statistics,
)
from qore.infrastructure.research_temporal_evaluation import (
    ResearchTemporalEvaluationPlan,
    ResearchWalkForwardFold,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchOosPerformanceError(InfrastructureError):
    """Base error for out-of-sample performance evidence."""

    __slots__ = ()


class ResearchOosPerformanceValidationError(ResearchOosPerformanceError):
    """Violation of an out-of-sample performance invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchOosPerformanceValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchOosPerformanceValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ResearchOosPerformanceEvidenceId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchOosPerformanceValidationError(
                "OOS performance evidence id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchOosFoldPerformance:
    """Performance statistics sourced only from one fold's OOS interval."""

    fold: ResearchWalkForwardFold
    statistics: ResearchPerformanceStatisticsSnapshot

    def __post_init__(self) -> None:
        if not isinstance(self.fold, ResearchWalkForwardFold):
            raise ResearchOosPerformanceValidationError(
                "OOS fold performance requires ResearchWalkForwardFold"
            )
        if not isinstance(self.statistics, ResearchPerformanceStatisticsSnapshot):
            raise ResearchOosPerformanceValidationError(
                "OOS fold performance requires performance statistics"
            )
        window = self.fold.out_of_sample
        for observation in self.statistics.observations:
            valued_at = observation.source_result.valued_at
            if not window.opened_at <= valued_at < window.closed_at:
                raise ResearchOosPerformanceValidationError(
                    "every OOS return must be valued inside its fold window"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (self.fold.logical_values(), self.statistics.logical_values())


def _validate_observations(
    plan: ResearchTemporalEvaluationPlan,
    observations: tuple[ResearchReturnObservation, ...],
) -> ResearchReturnBasis:
    if not isinstance(plan, ResearchTemporalEvaluationPlan):
        raise ResearchOosPerformanceValidationError(
            "OOS performance requires ResearchTemporalEvaluationPlan"
        )
    if not isinstance(observations, tuple) or not observations or any(
        not isinstance(item, ResearchReturnObservation) for item in observations
    ):
        raise ResearchOosPerformanceValidationError(
            "OOS performance requires a non-empty immutable return tuple"
        )
    if any(item.run != plan.run for item in observations):
        raise ResearchOosPerformanceValidationError(
            "all OOS returns must belong to the temporal plan research run"
        )
    basis = observations[0].basis
    if any(item.basis is not basis for item in observations):
        raise ResearchOosPerformanceValidationError(
            "all OOS returns must use one gross-or-net return basis"
        )
    observation_ids = tuple(item.observation_id for item in observations)
    if len(set(observation_ids)) != len(observation_ids):
        raise ResearchOosPerformanceValidationError(
            "OOS return observation ids must be unique"
        )
    result_ids = tuple(item.source_result.result_id for item in observations)
    if len(set(result_ids)) != len(result_ids):
        raise ResearchOosPerformanceValidationError(
            "OOS source economic result ids must be unique"
        )
    return basis


def _partition_observations(
    plan: ResearchTemporalEvaluationPlan,
    observations: tuple[ResearchReturnObservation, ...],
) -> tuple[tuple[ResearchReturnObservation, ...], ...]:
    buckets: list[tuple[ResearchReturnObservation, ...]] = []
    assigned_ids: set[object] = set()
    for fold in plan.folds:
        window = fold.out_of_sample
        bucket = tuple(
            item
            for item in observations
            if window.opened_at <= item.source_result.valued_at < window.closed_at
        )
        if not bucket:
            raise ResearchOosPerformanceValidationError(
                "every walk-forward fold requires at least one OOS return observation"
            )
        for item in bucket:
            if item.observation_id in assigned_ids:
                raise ResearchOosPerformanceValidationError(
                    "an OOS return observation cannot be assigned to multiple folds"
                )
            assigned_ids.add(item.observation_id)
        buckets.append(bucket)
    if len(assigned_ids) != len(observations):
        raise ResearchOosPerformanceValidationError(
            "every supplied return observation must fall inside exactly one OOS window"
        )
    return tuple(buckets)


@dataclass(frozen=True, slots=True)
class ResearchOosPerformanceEvidence:
    """Fold-scoped OOS performance evidence with preserved source returns.

    This contract proves that the measured return evidence is temporally located
    inside declared out-of-sample windows. It does not prove analyst blindness,
    strategy pre-registration, parameter freezing, statistical significance, or
    absence of repeated-research selection bias.
    """

    evidence_id: ResearchOosPerformanceEvidenceId
    plan: ResearchTemporalEvaluationPlan
    basis: ResearchReturnBasis
    fold_performance: tuple[ResearchOosFoldPerformance, ...]
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, ResearchOosPerformanceEvidenceId):
            raise ResearchOosPerformanceValidationError(
                "evidence_id must be ResearchOosPerformanceEvidenceId"
            )
        if not isinstance(self.plan, ResearchTemporalEvaluationPlan):
            raise ResearchOosPerformanceValidationError(
                "OOS evidence requires ResearchTemporalEvaluationPlan"
            )
        if not isinstance(self.basis, ResearchReturnBasis):
            raise ResearchOosPerformanceValidationError(
                "OOS evidence basis must be ResearchReturnBasis"
            )
        if (
            not isinstance(self.fold_performance, tuple)
            or len(self.fold_performance) != len(self.plan.folds)
            or any(
                not isinstance(item, ResearchOosFoldPerformance)
                for item in self.fold_performance
            )
        ):
            raise ResearchOosPerformanceValidationError(
                "OOS evidence requires exactly one performance record per fold"
            )
        if tuple(item.fold for item in self.fold_performance) != self.plan.folds:
            raise ResearchOosPerformanceValidationError(
                "OOS performance records must follow the temporal plan folds exactly"
            )
        all_observations = tuple(
            observation
            for item in self.fold_performance
            for observation in item.statistics.observations
        )
        _validate_observations(self.plan, all_observations)
        if any(item.statistics.basis is not self.basis for item in self.fold_performance):
            raise ResearchOosPerformanceValidationError(
                "every OOS fold statistic must use the evidence return basis"
            )
        if any(item.statistics.run != self.plan.run for item in self.fold_performance):
            raise ResearchOosPerformanceValidationError(
                "every OOS fold statistic must bind the temporal plan research run"
            )
        _validate_timestamp(self.observed_at, field_name="OOS performance observed_at")
        if self.observed_at < max(
            item.statistics.observed_at for item in self.fold_performance
        ):
            raise ResearchOosPerformanceValidationError(
                "OOS performance evidence cannot predate fold statistics"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_id.logical_values(),
            self.plan.logical_values(),
            self.basis.value,
            tuple(item.logical_values() for item in self.fold_performance),
            self.observed_at.isoformat(),
        )


def build_research_oos_performance_evidence(
    *,
    evidence_id: ResearchOosPerformanceEvidenceId,
    plan: ResearchTemporalEvaluationPlan,
    observations: tuple[ResearchReturnObservation, ...],
    statistics_snapshot_ids: tuple[ResearchPerformanceSnapshotId, ...],
    observed_at: datetime,
) -> Result[ResearchOosPerformanceEvidence, ResearchOosPerformanceError]:
    """Partition actual returns into OOS windows and derive fold statistics."""

    try:
        basis = _validate_observations(plan, observations)
        if (
            not isinstance(statistics_snapshot_ids, tuple)
            or len(statistics_snapshot_ids) != len(plan.folds)
            or any(
                not isinstance(item, ResearchPerformanceSnapshotId)
                for item in statistics_snapshot_ids
            )
        ):
            raise ResearchOosPerformanceValidationError(
                "exactly one performance snapshot id is required per OOS fold"
            )
        if len(set(statistics_snapshot_ids)) != len(statistics_snapshot_ids):
            raise ResearchOosPerformanceValidationError(
                "OOS performance snapshot ids must be unique"
            )
        buckets = _partition_observations(plan, observations)
        fold_performance: list[ResearchOosFoldPerformance] = []
        for fold, bucket, snapshot_id in zip(
            plan.folds,
            buckets,
            statistics_snapshot_ids,
            strict=True,
        ):
            built = build_research_performance_statistics(
                snapshot_id=snapshot_id,
                observations=bucket,
                observed_at=observed_at,
            )
            if isinstance(built, Failure):
                raise ResearchOosPerformanceValidationError(
                    f"OOS fold statistics invalid: {built.error}"
                )
            fold_performance.append(
                ResearchOosFoldPerformance(fold=fold, statistics=built.value)
            )
        return Success(
            ResearchOosPerformanceEvidence(
                evidence_id=evidence_id,
                plan=plan,
                basis=basis,
                fold_performance=tuple(fold_performance),
                observed_at=observed_at,
            )
        )
    except ResearchOosPerformanceError as error:
        return Failure(error)
