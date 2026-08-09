from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.research_periodic_equity import ResearchPeriodicEquityReturnSeries
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchPeriodicAutocorrelationError(InfrastructureError):
    """Base error for fixed-period multi-lag autocorrelation evidence."""

    __slots__ = ()


class ResearchPeriodicAutocorrelationValidationError(
    ResearchPeriodicAutocorrelationError
):
    """Violation of a periodic autocorrelation-profile invariant."""

    __slots__ = ()


class ResearchPeriodicAutocorrelationStatus(StrEnum):
    DEFINED = "defined"
    UNDEFINED_ZERO_VARIANCE = "undefined_zero_variance"


@dataclass(frozen=True, slots=True)
class ResearchPeriodicAutocorrelationProfileId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicAutocorrelationValidationError(
                "autocorrelation profile id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicAutocorrelationPolicy:
    max_lag: int

    def __post_init__(self) -> None:
        if type(self.max_lag) is not int or self.max_lag <= 0:
            raise ResearchPeriodicAutocorrelationValidationError(
                "max_lag must be a positive integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.max_lag,)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicAutocorrelationPoint:
    lag: int
    pair_count: int
    status: ResearchPeriodicAutocorrelationStatus
    correlation: Decimal | None

    def __post_init__(self) -> None:
        if type(self.lag) is not int or self.lag <= 0:
            raise ResearchPeriodicAutocorrelationValidationError(
                "autocorrelation lag must be a positive integer"
            )
        if type(self.pair_count) is not int or self.pair_count < 2:
            raise ResearchPeriodicAutocorrelationValidationError(
                "autocorrelation point requires at least two return pairs"
            )
        if not isinstance(self.status, ResearchPeriodicAutocorrelationStatus):
            raise ResearchPeriodicAutocorrelationValidationError(
                "autocorrelation status must be ResearchPeriodicAutocorrelationStatus"
            )
        if self.status is ResearchPeriodicAutocorrelationStatus.DEFINED:
            if (
                not isinstance(self.correlation, Decimal)
                or not self.correlation.is_finite()
                or not -1 <= self.correlation <= 1
            ):
                raise ResearchPeriodicAutocorrelationValidationError(
                    "defined autocorrelation must be a finite Decimal between -1 and 1"
                )
        elif self.correlation is not None:
            raise ResearchPeriodicAutocorrelationValidationError(
                "undefined autocorrelation must not carry a numeric value"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.lag,
            self.pair_count,
            self.status.value,
            format(self.correlation, "f") if self.correlation is not None else None,
        )


def _correlation_at_lag(
    values: tuple[Decimal, ...],
    lag: int,
) -> ResearchPeriodicAutocorrelationPoint:
    leading = values[:-lag]
    trailing = values[lag:]
    pair_count = len(leading)
    if pair_count < 2:
        raise ResearchPeriodicAutocorrelationValidationError(
            "every requested autocorrelation lag requires at least two return pairs"
        )
    with localcontext(_DECIMAL128):
        denominator = Decimal(pair_count)
        left_mean = sum(leading, Decimal(0)) / denominator
        right_mean = sum(trailing, Decimal(0)) / denominator
        covariance_sum = sum(
            (
                (left - left_mean) * (right - right_mean)
                for left, right in zip(leading, trailing, strict=True)
            ),
            Decimal(0),
        )
        left_variance_sum = sum(
            ((value - left_mean) * (value - left_mean) for value in leading),
            Decimal(0),
        )
        right_variance_sum = sum(
            ((value - right_mean) * (value - right_mean) for value in trailing),
            Decimal(0),
        )
        variance_product = left_variance_sum * right_variance_sum
        if variance_product == 0:
            return ResearchPeriodicAutocorrelationPoint(
                lag=lag,
                pair_count=pair_count,
                status=ResearchPeriodicAutocorrelationStatus.UNDEFINED_ZERO_VARIANCE,
                correlation=None,
            )
        correlation = covariance_sum / variance_product.sqrt()
    return ResearchPeriodicAutocorrelationPoint(
        lag=lag,
        pair_count=pair_count,
        status=ResearchPeriodicAutocorrelationStatus.DEFINED,
        correlation=correlation,
    )


def _derive_profile(
    series: ResearchPeriodicEquityReturnSeries,
    policy: ResearchPeriodicAutocorrelationPolicy,
) -> tuple[ResearchPeriodicAutocorrelationPoint, ...]:
    if not isinstance(series, ResearchPeriodicEquityReturnSeries):
        raise ResearchPeriodicAutocorrelationValidationError(
            "autocorrelation profile requires ResearchPeriodicEquityReturnSeries"
        )
    if not isinstance(policy, ResearchPeriodicAutocorrelationPolicy):
        raise ResearchPeriodicAutocorrelationValidationError(
            "autocorrelation profile requires ResearchPeriodicAutocorrelationPolicy"
        )
    values = tuple(point.return_rate for point in series.returns)
    if len(values) < 3:
        raise ResearchPeriodicAutocorrelationValidationError(
            "autocorrelation profile requires at least three periodic returns"
        )
    if policy.max_lag > len(values) - 2:
        raise ResearchPeriodicAutocorrelationValidationError(
            "max_lag must leave at least two return pairs at every requested lag"
        )
    return tuple(
        _correlation_at_lag(values, lag)
        for lag in range(1, policy.max_lag + 1)
    )


@dataclass(frozen=True, slots=True)
class ResearchPeriodicAutocorrelationProfile:
    """Descriptive Pearson autocorrelation profile for fixed-period returns.

    The profile makes first-through-max-lag linear dependence visible. Even a
    profile whose defined correlations are near zero does not prove independence,
    IID sampling, stationarity, absence of nonlinear dependence, or validity of
    square-root-of-time annualization.
    """

    profile_id: ResearchPeriodicAutocorrelationProfileId
    series: ResearchPeriodicEquityReturnSeries
    policy: ResearchPeriodicAutocorrelationPolicy
    points: tuple[ResearchPeriodicAutocorrelationPoint, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, ResearchPeriodicAutocorrelationProfileId):
            raise ResearchPeriodicAutocorrelationValidationError(
                "profile_id must be ResearchPeriodicAutocorrelationProfileId"
            )
        expected = _derive_profile(self.series, self.policy)
        if self.points != expected:
            raise ResearchPeriodicAutocorrelationValidationError(
                "autocorrelation points must match source fixed-period returns"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.profile_id.logical_values(),
            self.series.logical_values(),
            self.policy.logical_values(),
            tuple(point.logical_values() for point in self.points),
        )


def build_research_periodic_autocorrelation_profile(
    *,
    profile_id: ResearchPeriodicAutocorrelationProfileId,
    series: ResearchPeriodicEquityReturnSeries,
    policy: ResearchPeriodicAutocorrelationPolicy,
) -> Result[
    ResearchPeriodicAutocorrelationProfile,
    ResearchPeriodicAutocorrelationError,
]:
    """Build multi-lag descriptive dependence evidence without time scaling."""

    try:
        points = _derive_profile(series, policy)
        return Success(
            ResearchPeriodicAutocorrelationProfile(
                profile_id=profile_id,
                series=series,
                policy=policy,
                points=points,
            )
        )
    except ResearchPeriodicAutocorrelationError as error:
        return Failure(error)
