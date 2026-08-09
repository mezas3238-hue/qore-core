from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from uuid import UUID

from qore.infrastructure.research_economic_evidence import (
    ResearchGrossEconomicResult,
    ResearchNetEconomicResult,
    ResearchReturnBasis,
    ResearchReturnObservation,
)
from qore.infrastructure.research_run import ResearchRunEvidence
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchPerformanceStatisticsError(InfrastructureError):
    """Base error for evidence-backed research performance statistics."""

    __slots__ = ()


class ResearchPerformanceStatisticsValidationError(ResearchPerformanceStatisticsError):
    """Violation of a research performance-statistics invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ResearchPerformanceStatisticsValidationError(
            f"{field_name} must be UUID"
        )


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchPerformanceStatisticsValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchPerformanceStatisticsValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ResearchPerformanceSnapshotId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research performance snapshot id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _gross_result(
    observation: ResearchReturnObservation,
) -> ResearchGrossEconomicResult:
    source = observation.source_result
    if isinstance(source, ResearchNetEconomicResult):
        return source.gross_result
    return source


def _canonical_observations(
    observations: tuple[ResearchReturnObservation, ...],
) -> tuple[ResearchReturnObservation, ...]:
    if not isinstance(observations, tuple) or not observations or any(
        not isinstance(item, ResearchReturnObservation) for item in observations
    ):
        raise ResearchPerformanceStatisticsValidationError(
            "performance observations must be a non-empty immutable return tuple"
        )
    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.observed_at.astimezone(UTC),
                str(item.observation_id.value),
            ),
        )
    )
    observation_ids = tuple(item.observation_id for item in ordered)
    if len(set(observation_ids)) != len(observation_ids):
        raise ResearchPerformanceStatisticsValidationError(
            "performance return observation ids must be unique"
        )
    result_ids = tuple(item.source_result.result_id for item in ordered)
    if len(set(result_ids)) != len(result_ids):
        raise ResearchPerformanceStatisticsValidationError(
            "performance source economic result ids must be unique"
        )
    fill_ids = tuple(
        fill.fill_id
        for item in ordered
        for fill in (
            *_gross_result(item).entry_fills,
            *_gross_result(item).exit_fills,
        )
    )
    if len(set(fill_ids)) != len(fill_ids):
        raise ResearchPerformanceStatisticsValidationError(
            "performance observations must not reuse economic fill evidence"
        )
    run = ordered[0].run
    if any(item.run != run for item in ordered):
        raise ResearchPerformanceStatisticsValidationError(
            "performance observations must belong to one research run"
        )
    basis = ordered[0].basis
    if any(item.basis is not basis for item in ordered):
        raise ResearchPerformanceStatisticsValidationError(
            "performance observations must use one gross-or-net return basis"
        )
    return ordered


def _derive_metrics(
    observations: tuple[ResearchReturnObservation, ...],
) -> tuple[int, int, int, int, Decimal, Decimal, Decimal, Decimal, Decimal]:
    values = tuple(item.return_rate for item in observations)
    sample_size = len(values)
    positive_count = sum(value > 0 for value in values)
    negative_count = sum(value < 0 for value in values)
    flat_count = sample_size - positive_count - negative_count
    with localcontext(_DECIMAL128):
        denominator = Decimal(sample_size)
        mean_return = sum(values, Decimal(0)) / denominator
        win_rate = Decimal(positive_count) / denominator
        population_variance = (
            sum(
                ((value - mean_return) * (value - mean_return) for value in values),
                Decimal(0),
            )
            / denominator
        )
    return (
        sample_size,
        positive_count,
        negative_count,
        flat_count,
        mean_return,
        min(values),
        max(values),
        win_rate,
        population_variance,
    )


@dataclass(frozen=True, slots=True)
class ResearchPerformanceStatisticsSnapshot:
    """Descriptive trading-return statistics with complete source preservation.

    Metrics are computed only from `ResearchReturnObservation` evidence from one
    research run and one explicit gross/net basis. Decimal divisions use a fixed
    decimal128-style context (34 digits, ROUND_HALF_EVEN) for deterministic
    cross-environment arithmetic. This contract deliberately does not annualize,
    compound, infer an equity curve, calculate Sharpe/Sortino, or claim statistical
    significance.
    """

    snapshot_id: ResearchPerformanceSnapshotId
    run: ResearchRunEvidence
    basis: ResearchReturnBasis
    observations: tuple[ResearchReturnObservation, ...]
    sample_size: int
    positive_count: int
    negative_count: int
    flat_count: int
    mean_return: Decimal
    minimum_return: Decimal
    maximum_return: Decimal
    win_rate: Decimal
    population_variance: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, ResearchPerformanceSnapshotId):
            raise ResearchPerformanceStatisticsValidationError(
                "snapshot_id must be ResearchPerformanceSnapshotId"
            )
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchPerformanceStatisticsValidationError(
                "performance snapshot requires ResearchRunEvidence"
            )
        if not isinstance(self.basis, ResearchReturnBasis):
            raise ResearchPerformanceStatisticsValidationError(
                "performance basis must be ResearchReturnBasis"
            )
        ordered = _canonical_observations(self.observations)
        if self.observations != ordered:
            raise ResearchPerformanceStatisticsValidationError(
                "performance observations must use canonical chronological order"
            )
        if self.run != ordered[0].run:
            raise ResearchPerformanceStatisticsValidationError(
                "performance snapshot run must match source observations"
            )
        if self.basis is not ordered[0].basis:
            raise ResearchPerformanceStatisticsValidationError(
                "performance snapshot basis must match source observations"
            )
        expected = _derive_metrics(ordered)
        actual = (
            self.sample_size,
            self.positive_count,
            self.negative_count,
            self.flat_count,
            self.mean_return,
            self.minimum_return,
            self.maximum_return,
            self.win_rate,
            self.population_variance,
        )
        if actual != expected:
            raise ResearchPerformanceStatisticsValidationError(
                "performance statistics must equal metrics derived from return evidence"
            )
        _validate_timestamp(self.observed_at, field_name="performance observed_at")
        if self.observed_at < max(item.observed_at for item in ordered):
            raise ResearchPerformanceStatisticsValidationError(
                "performance snapshot cannot predate source return evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.run.logical_values(),
            self.basis.value,
            tuple(item.logical_values() for item in self.observations),
            self.sample_size,
            self.positive_count,
            self.negative_count,
            self.flat_count,
            format(self.mean_return, "f"),
            format(self.minimum_return, "f"),
            format(self.maximum_return, "f"),
            format(self.win_rate, "f"),
            format(self.population_variance, "f"),
            self.observed_at.isoformat(),
        )


def build_research_performance_statistics(
    *,
    snapshot_id: ResearchPerformanceSnapshotId,
    observations: tuple[ResearchReturnObservation, ...],
    observed_at: datetime,
) -> Result[ResearchPerformanceStatisticsSnapshot, ResearchPerformanceStatisticsError]:
    """Build descriptive return statistics without inventing an equity curve."""

    try:
        ordered = _canonical_observations(observations)
        (
            sample_size,
            positive_count,
            negative_count,
            flat_count,
            mean_return,
            minimum_return,
            maximum_return,
            win_rate,
            population_variance,
        ) = _derive_metrics(ordered)
        return Success(
            ResearchPerformanceStatisticsSnapshot(
                snapshot_id=snapshot_id,
                run=ordered[0].run,
                basis=ordered[0].basis,
                observations=ordered,
                sample_size=sample_size,
                positive_count=positive_count,
                negative_count=negative_count,
                flat_count=flat_count,
                mean_return=mean_return,
                minimum_return=minimum_return,
                maximum_return=maximum_return,
                win_rate=win_rate,
                population_variance=population_variance,
                observed_at=observed_at,
            )
        )
    except ResearchPerformanceStatisticsError as error:
        return Failure(error)
