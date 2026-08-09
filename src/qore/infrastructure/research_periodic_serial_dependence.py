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


class ResearchPeriodicSerialDependenceError(InfrastructureError):
    """Base error for fixed-period return serial-dependence evidence."""

    __slots__ = ()


class ResearchPeriodicSerialDependenceValidationError(
    ResearchPeriodicSerialDependenceError
):
    """Violation of a fixed-period serial-dependence invariant."""

    __slots__ = ()


class ResearchPeriodicLagOneStatus(StrEnum):
    DEFINED = "defined"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    UNDEFINED_ZERO_VARIANCE = "undefined_zero_variance"


@dataclass(frozen=True, slots=True)
class ResearchPeriodicSerialDiagnosticId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicSerialDependenceValidationError(
                "periodic serial diagnostic id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _derive_lag_one(
    series: ResearchPeriodicEquityReturnSeries,
) -> tuple[ResearchPeriodicLagOneStatus, int, Decimal | None]:
    if not isinstance(series, ResearchPeriodicEquityReturnSeries):
        raise ResearchPeriodicSerialDependenceValidationError(
            "periodic serial diagnostic requires ResearchPeriodicEquityReturnSeries"
        )
    values = tuple(point.return_rate for point in series.returns)
    if len(values) < 3:
        return (
            ResearchPeriodicLagOneStatus.INSUFFICIENT_SAMPLE,
            max(len(values) - 1, 0),
            None,
        )
    leading = values[:-1]
    trailing = values[1:]
    pair_count = len(leading)
    with localcontext(_DECIMAL128):
        denominator = Decimal(pair_count)
        leading_mean = sum(leading, Decimal(0)) / denominator
        trailing_mean = sum(trailing, Decimal(0)) / denominator
        covariance_sum = sum(
            (
                (left - leading_mean) * (right - trailing_mean)
                for left, right in zip(leading, trailing, strict=True)
            ),
            Decimal(0),
        )
        leading_variance_sum = sum(
            ((value - leading_mean) * (value - leading_mean) for value in leading),
            Decimal(0),
        )
        trailing_variance_sum = sum(
            ((value - trailing_mean) * (value - trailing_mean) for value in trailing),
            Decimal(0),
        )
        variance_product = leading_variance_sum * trailing_variance_sum
        if variance_product == 0:
            return (
                ResearchPeriodicLagOneStatus.UNDEFINED_ZERO_VARIANCE,
                pair_count,
                None,
            )
        correlation = covariance_sum / variance_product.sqrt()
    return ResearchPeriodicLagOneStatus.DEFINED, pair_count, correlation


@dataclass(frozen=True, slots=True)
class ResearchPeriodicSerialDependenceDiagnostic:
    """Descriptive lag-one correlation over fixed-period equity returns.

    This diagnostic is not a proof of independence, IID sampling, stationarity,
    normality, absence of nonlinear/higher-lag dependence, or validity of square-
    root-of-time annualization. It is only first-order linear dependence evidence.
    """

    diagnostic_id: ResearchPeriodicSerialDiagnosticId
    series: ResearchPeriodicEquityReturnSeries
    lag: int
    status: ResearchPeriodicLagOneStatus
    pair_count: int
    correlation: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.diagnostic_id, ResearchPeriodicSerialDiagnosticId):
            raise ResearchPeriodicSerialDependenceValidationError(
                "diagnostic_id must be ResearchPeriodicSerialDiagnosticId"
            )
        if not isinstance(self.series, ResearchPeriodicEquityReturnSeries):
            raise ResearchPeriodicSerialDependenceValidationError(
                "periodic serial diagnostic requires ResearchPeriodicEquityReturnSeries"
            )
        if self.lag != 1:
            raise ResearchPeriodicSerialDependenceValidationError(
                "periodic serial diagnostic currently supports lag one only"
            )
        if not isinstance(self.status, ResearchPeriodicLagOneStatus):
            raise ResearchPeriodicSerialDependenceValidationError(
                "status must be ResearchPeriodicLagOneStatus"
            )
        expected_status, expected_pairs, expected_correlation = _derive_lag_one(
            self.series
        )
        if self.status is not expected_status:
            raise ResearchPeriodicSerialDependenceValidationError(
                "periodic lag-one status must match source returns"
            )
        if self.pair_count != expected_pairs:
            raise ResearchPeriodicSerialDependenceValidationError(
                "periodic lag-one pair_count must match source returns"
            )
        if self.correlation != expected_correlation:
            raise ResearchPeriodicSerialDependenceValidationError(
                "periodic lag-one correlation must match source returns"
            )
        if self.correlation is not None and not -1 <= self.correlation <= 1:
            raise ResearchPeriodicSerialDependenceValidationError(
                "periodic lag-one correlation must remain between -1 and 1"
            )

    @property
    def sample_size(self) -> int:
        return self.series.period_count

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.diagnostic_id.logical_values(),
            self.series.logical_values(),
            self.lag,
            self.status.value,
            self.pair_count,
            format(self.correlation, "f") if self.correlation is not None else None,
        )


def build_research_periodic_serial_dependence_diagnostic(
    *,
    diagnostic_id: ResearchPeriodicSerialDiagnosticId,
    series: ResearchPeriodicEquityReturnSeries,
) -> Result[
    ResearchPeriodicSerialDependenceDiagnostic,
    ResearchPeriodicSerialDependenceError,
]:
    """Derive lag-one periodic correlation without annualization claims."""

    try:
        status, pair_count, correlation = _derive_lag_one(series)
        return Success(
            ResearchPeriodicSerialDependenceDiagnostic(
                diagnostic_id=diagnostic_id,
                series=series,
                lag=1,
                status=status,
                pair_count=pair_count,
                correlation=correlation,
            )
        )
    except ResearchPeriodicSerialDependenceError as error:
        return Failure(error)
