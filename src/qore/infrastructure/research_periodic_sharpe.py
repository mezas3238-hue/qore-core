from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.research_periodic_risk_statistics import (
    ResearchPeriodicDispersionStatus,
    ResearchPeriodicRiskStatisticsSnapshot,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchPeriodicSharpeError(InfrastructureError):
    """Base error for per-period Sharpe evidence."""

    __slots__ = ()


class ResearchPeriodicSharpeValidationError(ResearchPeriodicSharpeError):
    """Violation of a per-period Sharpe invariant."""

    __slots__ = ()


class ResearchPeriodicSharpeStatus(StrEnum):
    DEFINED = "defined"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    ZERO_VARIANCE = "zero_variance"


@dataclass(frozen=True, slots=True)
class ResearchPeriodicSharpeMetricId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicSharpeValidationError(
                "periodic Sharpe metric id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicSharpePolicy:
    """Explicit per-period risk-free return assumption.

    The risk-free rate is expressed on exactly the same interval as the source
    fixed-period equity returns. This policy deliberately contains no annualization
    factor and no implicit conversion from an annual rate.
    """

    risk_free_rate_per_period: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.risk_free_rate_per_period, Decimal)
            or not self.risk_free_rate_per_period.is_finite()
        ):
            raise ResearchPeriodicSharpeValidationError(
                "risk_free_rate_per_period must be a finite Decimal"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (format(self.risk_free_rate_per_period, "f"),)


def _derive_metric(
    statistics: ResearchPeriodicRiskStatisticsSnapshot,
    policy: ResearchPeriodicSharpePolicy,
) -> tuple[ResearchPeriodicSharpeStatus, Decimal, Decimal | None]:
    if not isinstance(statistics, ResearchPeriodicRiskStatisticsSnapshot):
        raise ResearchPeriodicSharpeValidationError(
            "periodic Sharpe requires ResearchPeriodicRiskStatisticsSnapshot"
        )
    if not isinstance(policy, ResearchPeriodicSharpePolicy):
        raise ResearchPeriodicSharpeValidationError(
            "periodic Sharpe requires ResearchPeriodicSharpePolicy"
        )
    with localcontext(_DECIMAL128):
        mean_excess_return = (
            statistics.mean_return - policy.risk_free_rate_per_period
        )
    if statistics.dispersion_status is ResearchPeriodicDispersionStatus.INSUFFICIENT_SAMPLE:
        return ResearchPeriodicSharpeStatus.INSUFFICIENT_SAMPLE, mean_excess_return, None
    if statistics.dispersion_status is ResearchPeriodicDispersionStatus.ZERO_VARIANCE:
        return ResearchPeriodicSharpeStatus.ZERO_VARIANCE, mean_excess_return, None
    if statistics.dispersion_status is not ResearchPeriodicDispersionStatus.DEFINED:
        raise ResearchPeriodicSharpeValidationError(
            "unsupported periodic dispersion status"
        )
    standard_deviation = statistics.sample_standard_deviation
    if standard_deviation is None or standard_deviation <= 0:
        raise ResearchPeriodicSharpeValidationError(
            "defined dispersion requires positive sample standard deviation"
        )
    with localcontext(_DECIMAL128):
        sharpe_ratio = mean_excess_return / standard_deviation
    return ResearchPeriodicSharpeStatus.DEFINED, mean_excess_return, sharpe_ratio


@dataclass(frozen=True, slots=True)
class ResearchPeriodicSharpeMetric:
    """Per-period Sharpe ratio over fixed-period equity-return evidence.

    The ratio is `mean(period_return - risk_free_per_period) / sample_stddev`.
    It is intentionally not annualized. No IID, stationarity, normality,
    significance, predictive validity, or production-readiness claim is implied.
    """

    metric_id: ResearchPeriodicSharpeMetricId
    statistics: ResearchPeriodicRiskStatisticsSnapshot
    policy: ResearchPeriodicSharpePolicy
    status: ResearchPeriodicSharpeStatus
    mean_excess_return: Decimal
    sharpe_ratio: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.metric_id, ResearchPeriodicSharpeMetricId):
            raise ResearchPeriodicSharpeValidationError(
                "metric_id must be ResearchPeriodicSharpeMetricId"
            )
        if not isinstance(self.statistics, ResearchPeriodicRiskStatisticsSnapshot):
            raise ResearchPeriodicSharpeValidationError(
                "periodic Sharpe requires ResearchPeriodicRiskStatisticsSnapshot"
            )
        if not isinstance(self.policy, ResearchPeriodicSharpePolicy):
            raise ResearchPeriodicSharpeValidationError(
                "periodic Sharpe requires ResearchPeriodicSharpePolicy"
            )
        if not isinstance(self.status, ResearchPeriodicSharpeStatus):
            raise ResearchPeriodicSharpeValidationError(
                "status must be ResearchPeriodicSharpeStatus"
            )
        expected_status, expected_excess, expected_ratio = _derive_metric(
            self.statistics,
            self.policy,
        )
        if self.status is not expected_status:
            raise ResearchPeriodicSharpeValidationError(
                "periodic Sharpe status must match source dispersion evidence"
            )
        if self.mean_excess_return != expected_excess:
            raise ResearchPeriodicSharpeValidationError(
                "mean_excess_return must match source statistics and policy"
            )
        if self.sharpe_ratio != expected_ratio:
            raise ResearchPeriodicSharpeValidationError(
                "sharpe_ratio must match source statistics and policy"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metric_id.logical_values(),
            self.statistics.logical_values(),
            self.policy.logical_values(),
            self.status.value,
            format(self.mean_excess_return, "f"),
            format(self.sharpe_ratio, "f") if self.sharpe_ratio is not None else None,
        )


def build_research_periodic_sharpe_metric(
    *,
    metric_id: ResearchPeriodicSharpeMetricId,
    statistics: ResearchPeriodicRiskStatisticsSnapshot,
    policy: ResearchPeriodicSharpePolicy,
) -> Result[ResearchPeriodicSharpeMetric, ResearchPeriodicSharpeError]:
    """Build a non-annualized Sharpe ratio without adding hidden assumptions."""

    try:
        status, mean_excess_return, sharpe_ratio = _derive_metric(statistics, policy)
        return Success(
            ResearchPeriodicSharpeMetric(
                metric_id=metric_id,
                statistics=statistics,
                policy=policy,
                status=status,
                mean_excess_return=mean_excess_return,
                sharpe_ratio=sharpe_ratio,
            )
        )
    except ResearchPeriodicSharpeError as error:
        return Failure(error)
