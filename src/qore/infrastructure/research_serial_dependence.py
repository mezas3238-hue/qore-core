from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.research_sampling_frame import ResearchSamplingFrame
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchSerialDependenceError(InfrastructureError):
    """Base error for descriptive research return-sequence dependence evidence."""

    __slots__ = ()


class ResearchSerialDependenceValidationError(ResearchSerialDependenceError):
    """Violation of a serial-dependence evidence invariant."""

    __slots__ = ()


class ResearchLagOneCorrelationStatus(StrEnum):
    DEFINED = "defined"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    UNDEFINED_ZERO_VARIANCE = "undefined_zero_variance"


@dataclass(frozen=True, slots=True)
class ResearchSerialDependenceDiagnosticId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchSerialDependenceValidationError(
                "serial dependence diagnostic id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _lag_one_diagnostic(
    frame: ResearchSamplingFrame,
) -> tuple[ResearchLagOneCorrelationStatus, int, Decimal | None]:
    if not isinstance(frame, ResearchSamplingFrame):
        raise ResearchSerialDependenceValidationError(
            "serial dependence requires ResearchSamplingFrame"
        )
    values = tuple(sample.return_rate for sample in frame.samples)
    if len(values) < 3:
        return ResearchLagOneCorrelationStatus.INSUFFICIENT_SAMPLE, max(len(values) - 1, 0), None

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
            return ResearchLagOneCorrelationStatus.UNDEFINED_ZERO_VARIANCE, pair_count, None
        correlation = covariance_sum / variance_product.sqrt()
    return ResearchLagOneCorrelationStatus.DEFINED, pair_count, correlation


@dataclass(frozen=True, slots=True)
class ResearchSerialDependenceDiagnostic:
    """Descriptive lag-one Pearson correlation over canonical OOS trade returns.

    The sequence is inherited exactly from `ResearchSamplingFrame`. A DEFINED
    lag-one correlation is only a first-order linear dependence diagnostic. A
    value near zero does not establish independence, IID sampling, stationarity,
    absence of nonlinear/higher-lag dependence, statistical significance, or
    suitability for an IID bootstrap. Holding-period overlap remains separate
    evidence on the source sampling frame.
    """

    diagnostic_id: ResearchSerialDependenceDiagnosticId
    frame: ResearchSamplingFrame
    lag: int
    status: ResearchLagOneCorrelationStatus
    pair_count: int
    correlation: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.diagnostic_id, ResearchSerialDependenceDiagnosticId):
            raise ResearchSerialDependenceValidationError(
                "diagnostic_id must be ResearchSerialDependenceDiagnosticId"
            )
        if not isinstance(self.frame, ResearchSamplingFrame):
            raise ResearchSerialDependenceValidationError(
                "serial dependence diagnostic requires ResearchSamplingFrame"
            )
        if self.lag != 1:
            raise ResearchSerialDependenceValidationError(
                "serial dependence diagnostic currently supports lag one only"
            )
        if not isinstance(self.status, ResearchLagOneCorrelationStatus):
            raise ResearchSerialDependenceValidationError(
                "status must be ResearchLagOneCorrelationStatus"
            )
        expected_status, expected_pair_count, expected_correlation = _lag_one_diagnostic(
            self.frame
        )
        if self.status is not expected_status:
            raise ResearchSerialDependenceValidationError(
                "serial dependence status must match source return sequence"
            )
        if self.pair_count != expected_pair_count:
            raise ResearchSerialDependenceValidationError(
                "serial dependence pair_count must match lag-one return pairs"
            )
        if self.correlation != expected_correlation:
            raise ResearchSerialDependenceValidationError(
                "serial dependence correlation must match source return sequence"
            )
        if self.correlation is not None and not -1 <= self.correlation <= 1:
            raise ResearchSerialDependenceValidationError(
                "serial dependence correlation must remain between -1 and 1"
            )

    @property
    def sample_size(self) -> int:
        return self.frame.sample_size

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.diagnostic_id.logical_values(),
            self.frame.logical_values(),
            self.lag,
            self.status.value,
            self.pair_count,
            format(self.correlation, "f") if self.correlation is not None else None,
        )


def build_research_serial_dependence_diagnostic(
    *,
    diagnostic_id: ResearchSerialDependenceDiagnosticId,
    frame: ResearchSamplingFrame,
) -> Result[ResearchSerialDependenceDiagnostic, ResearchSerialDependenceError]:
    """Derive lag-one correlation without making inferential independence claims."""

    try:
        status, pair_count, correlation = _lag_one_diagnostic(frame)
        return Success(
            ResearchSerialDependenceDiagnostic(
                diagnostic_id=diagnostic_id,
                frame=frame,
                lag=1,
                status=status,
                pair_count=pair_count,
                correlation=correlation,
            )
        )
    except ResearchSerialDependenceError as error:
        return Failure(error)
