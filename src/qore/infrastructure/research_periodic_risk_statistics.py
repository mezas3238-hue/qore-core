from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.research_periodic_equity import (
    ResearchPeriodicEquityReturnSeries,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchPeriodicRiskStatisticsError(InfrastructureError):
    """Base error for descriptive fixed-period return risk statistics."""

    __slots__ = ()


class ResearchPeriodicRiskStatisticsValidationError(
    ResearchPeriodicRiskStatisticsError
):
    """Violation of a fixed-period risk-statistics invariant."""

    __slots__ = ()


class ResearchPeriodicDispersionStatus(StrEnum):
    DEFINED = "defined"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    ZERO_VARIANCE = "zero_variance"


@dataclass(frozen=True, slots=True)
class ResearchPeriodicRiskSnapshotId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicRiskStatisticsValidationError(
                "periodic risk snapshot id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _derive_statistics(
    series: ResearchPeriodicEquityReturnSeries,
) -> tuple[
    int,
    int,
    int,
    int,
    Decimal,
    Decimal,
    Decimal,
    ResearchPeriodicDispersionStatus,
    Decimal | None,
    Decimal | None,
]:
    if not isinstance(series, ResearchPeriodicEquityReturnSeries):
        raise ResearchPeriodicRiskStatisticsValidationError(
            "periodic risk statistics require ResearchPeriodicEquityReturnSeries"
        )
    values = tuple(point.return_rate for point in series.returns)
    if not values:
        raise ResearchPeriodicRiskStatisticsValidationError(
            "periodic risk statistics require non-empty periodic returns"
        )
    sample_size = len(values)
    positive_count = sum(value > 0 for value in values)
    negative_count = sum(value < 0 for value in values)
    flat_count = sample_size - positive_count - negative_count
    with localcontext(_DECIMAL128):
        mean_return = sum(values, Decimal(0)) / Decimal(sample_size)
    minimum_return = min(values)
    maximum_return = max(values)
    if sample_size < 2:
        return (
            sample_size,
            positive_count,
            negative_count,
            flat_count,
            mean_return,
            minimum_return,
            maximum_return,
            ResearchPeriodicDispersionStatus.INSUFFICIENT_SAMPLE,
            None,
            None,
        )
    with localcontext(_DECIMAL128):
        sample_variance = sum(
            ((value - mean_return) * (value - mean_return) for value in values),
            Decimal(0),
        ) / Decimal(sample_size - 1)
        sample_standard_deviation = sample_variance.sqrt()
    status = (
        ResearchPeriodicDispersionStatus.ZERO_VARIANCE
        if sample_variance == 0
        else ResearchPeriodicDispersionStatus.DEFINED
    )
    return (
        sample_size,
        positive_count,
        negative_count,
        flat_count,
        mean_return,
        minimum_return,
        maximum_return,
        status,
        sample_variance,
        sample_standard_deviation,
    )


@dataclass(frozen=True, slots=True)
class ResearchPeriodicRiskStatisticsSnapshot:
    """Descriptive statistics over fixed-period equity returns.

    Dispersion uses the unbiased sample-variance denominator n-1. The snapshot
    deliberately does not annualize, introduce a risk-free rate, calculate
    Sharpe/Sortino, infer normality/stationarity, or make significance claims.
    """

    snapshot_id: ResearchPeriodicRiskSnapshotId
    series: ResearchPeriodicEquityReturnSeries
    sample_size: int
    positive_count: int
    negative_count: int
    flat_count: int
    mean_return: Decimal
    minimum_return: Decimal
    maximum_return: Decimal
    dispersion_status: ResearchPeriodicDispersionStatus
    sample_variance: Decimal | None
    sample_standard_deviation: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, ResearchPeriodicRiskSnapshotId):
            raise ResearchPeriodicRiskStatisticsValidationError(
                "snapshot_id must be ResearchPeriodicRiskSnapshotId"
            )
        if not isinstance(self.series, ResearchPeriodicEquityReturnSeries):
            raise ResearchPeriodicRiskStatisticsValidationError(
                "periodic risk snapshot requires ResearchPeriodicEquityReturnSeries"
            )
        expected = _derive_statistics(self.series)
        actual = (
            self.sample_size,
            self.positive_count,
            self.negative_count,
            self.flat_count,
            self.mean_return,
            self.minimum_return,
            self.maximum_return,
            self.dispersion_status,
            self.sample_variance,
            self.sample_standard_deviation,
        )
        if actual != expected:
            raise ResearchPeriodicRiskStatisticsValidationError(
                "periodic risk statistics must equal source fixed-period returns"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.series.logical_values(),
            self.sample_size,
            self.positive_count,
            self.negative_count,
            self.flat_count,
            format(self.mean_return, "f"),
            format(self.minimum_return, "f"),
            format(self.maximum_return, "f"),
            self.dispersion_status.value,
            (
                format(self.sample_variance, "f")
                if self.sample_variance is not None
                else None
            ),
            (
                format(self.sample_standard_deviation, "f")
                if self.sample_standard_deviation is not None
                else None
            ),
        )


def build_research_periodic_risk_statistics(
    *,
    snapshot_id: ResearchPeriodicRiskSnapshotId,
    series: ResearchPeriodicEquityReturnSeries,
) -> Result[
    ResearchPeriodicRiskStatisticsSnapshot,
    ResearchPeriodicRiskStatisticsError,
]:
    """Build descriptive fixed-period return statistics without annualization."""

    try:
        (
            sample_size,
            positive_count,
            negative_count,
            flat_count,
            mean_return,
            minimum_return,
            maximum_return,
            dispersion_status,
            sample_variance,
            sample_standard_deviation,
        ) = _derive_statistics(series)
        return Success(
            ResearchPeriodicRiskStatisticsSnapshot(
                snapshot_id=snapshot_id,
                series=series,
                sample_size=sample_size,
                positive_count=positive_count,
                negative_count=negative_count,
                flat_count=flat_count,
                mean_return=mean_return,
                minimum_return=minimum_return,
                maximum_return=maximum_return,
                dispersion_status=dispersion_status,
                sample_variance=sample_variance,
                sample_standard_deviation=sample_standard_deviation,
            )
        )
    except ResearchPeriodicRiskStatisticsError as error:
        return Failure(error)
