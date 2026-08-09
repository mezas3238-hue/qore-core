from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.research_periodic_risk_statistics import (
    ResearchPeriodicRiskStatisticsSnapshot,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchPeriodicSortinoError(InfrastructureError):
    """Base error for per-period Sortino evidence."""

    __slots__ = ()


class ResearchPeriodicSortinoValidationError(ResearchPeriodicSortinoError):
    """Violation of a per-period Sortino invariant."""

    __slots__ = ()


class ResearchPeriodicSortinoStatus(StrEnum):
    DEFINED = "defined"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    NO_DOWNSIDE_DEVIATION = "no_downside_deviation"


@dataclass(frozen=True, slots=True)
class ResearchPeriodicSortinoMetricId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicSortinoValidationError(
                "periodic Sortino metric id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicSortinoPolicy:
    """Explicit minimum acceptable return (MAR) on the source return interval."""

    minimum_acceptable_return_per_period: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.minimum_acceptable_return_per_period, Decimal)
            or not self.minimum_acceptable_return_per_period.is_finite()
        ):
            raise ResearchPeriodicSortinoValidationError(
                "minimum_acceptable_return_per_period must be a finite Decimal"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (format(self.minimum_acceptable_return_per_period, "f"),)


def _derive_metric(
    statistics: ResearchPeriodicRiskStatisticsSnapshot,
    policy: ResearchPeriodicSortinoPolicy,
) -> tuple[
    ResearchPeriodicSortinoStatus,
    Decimal,
    int,
    Decimal | None,
    Decimal | None,
]:
    if not isinstance(statistics, ResearchPeriodicRiskStatisticsSnapshot):
        raise ResearchPeriodicSortinoValidationError(
            "periodic Sortino requires ResearchPeriodicRiskStatisticsSnapshot"
        )
    if not isinstance(policy, ResearchPeriodicSortinoPolicy):
        raise ResearchPeriodicSortinoValidationError(
            "periodic Sortino requires ResearchPeriodicSortinoPolicy"
        )
    values = tuple(point.return_rate for point in statistics.series.returns)
    if len(values) != statistics.sample_size or not values:
        raise ResearchPeriodicSortinoValidationError(
            "periodic Sortino source returns must match risk-statistics sample size"
        )
    target = policy.minimum_acceptable_return_per_period
    with localcontext(_DECIMAL128):
        mean_excess_return = statistics.mean_return - target
    downside_values = tuple(min(Decimal(0), value - target) for value in values)
    downside_count = sum(value < 0 for value in downside_values)
    if len(values) < 2:
        return (
            ResearchPeriodicSortinoStatus.INSUFFICIENT_SAMPLE,
            mean_excess_return,
            downside_count,
            None,
            None,
        )
    with localcontext(_DECIMAL128):
        downside_variance = sum(
            (value * value for value in downside_values),
            Decimal(0),
        ) / Decimal(len(values))
        downside_deviation = downside_variance.sqrt()
    if downside_deviation == 0:
        return (
            ResearchPeriodicSortinoStatus.NO_DOWNSIDE_DEVIATION,
            mean_excess_return,
            downside_count,
            Decimal(0),
            None,
        )
    with localcontext(_DECIMAL128):
        sortino_ratio = mean_excess_return / downside_deviation
    return (
        ResearchPeriodicSortinoStatus.DEFINED,
        mean_excess_return,
        downside_count,
        downside_deviation,
        sortino_ratio,
    )


@dataclass(frozen=True, slots=True)
class ResearchPeriodicSortinoMetric:
    """Non-annualized Sortino ratio over exact fixed-period equity returns.

    Downside deviation is the square root of the mean squared negative deviation
    from the explicit per-period MAR, using all source periods in the denominator.
    No annualization, IID/stationarity assumption, significance claim, predictive
    interpretation, or production-readiness claim is implied.
    """

    metric_id: ResearchPeriodicSortinoMetricId
    statistics: ResearchPeriodicRiskStatisticsSnapshot
    policy: ResearchPeriodicSortinoPolicy
    status: ResearchPeriodicSortinoStatus
    mean_excess_return: Decimal
    downside_observation_count: int
    downside_deviation: Decimal | None
    sortino_ratio: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.metric_id, ResearchPeriodicSortinoMetricId):
            raise ResearchPeriodicSortinoValidationError(
                "metric_id must be ResearchPeriodicSortinoMetricId"
            )
        if not isinstance(self.statistics, ResearchPeriodicRiskStatisticsSnapshot):
            raise ResearchPeriodicSortinoValidationError(
                "periodic Sortino requires ResearchPeriodicRiskStatisticsSnapshot"
            )
        if not isinstance(self.policy, ResearchPeriodicSortinoPolicy):
            raise ResearchPeriodicSortinoValidationError(
                "periodic Sortino requires ResearchPeriodicSortinoPolicy"
            )
        if not isinstance(self.status, ResearchPeriodicSortinoStatus):
            raise ResearchPeriodicSortinoValidationError(
                "status must be ResearchPeriodicSortinoStatus"
            )
        expected = _derive_metric(self.statistics, self.policy)
        actual = (
            self.status,
            self.mean_excess_return,
            self.downside_observation_count,
            self.downside_deviation,
            self.sortino_ratio,
        )
        if actual != expected:
            raise ResearchPeriodicSortinoValidationError(
                "periodic Sortino values must match source statistics and MAR policy"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metric_id.logical_values(),
            self.statistics.logical_values(),
            self.policy.logical_values(),
            self.status.value,
            format(self.mean_excess_return, "f"),
            self.downside_observation_count,
            (
                format(self.downside_deviation, "f")
                if self.downside_deviation is not None
                else None
            ),
            format(self.sortino_ratio, "f") if self.sortino_ratio is not None else None,
        )


def build_research_periodic_sortino_metric(
    *,
    metric_id: ResearchPeriodicSortinoMetricId,
    statistics: ResearchPeriodicRiskStatisticsSnapshot,
    policy: ResearchPeriodicSortinoPolicy,
) -> Result[ResearchPeriodicSortinoMetric, ResearchPeriodicSortinoError]:
    """Build a non-annualized Sortino ratio without hidden MAR assumptions."""

    try:
        (
            status,
            mean_excess_return,
            downside_observation_count,
            downside_deviation,
            sortino_ratio,
        ) = _derive_metric(statistics, policy)
        return Success(
            ResearchPeriodicSortinoMetric(
                metric_id=metric_id,
                statistics=statistics,
                policy=policy,
                status=status,
                mean_excess_return=mean_excess_return,
                downside_observation_count=downside_observation_count,
                downside_deviation=downside_deviation,
                sortino_ratio=sortino_ratio,
            )
        )
    except ResearchPeriodicSortinoError as error:
        return Failure(error)
