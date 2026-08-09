from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.research_periodic_equity import ResearchPeriodicEquityReturnSeries
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchPeriodicHacRiskError(InfrastructureError):
    """Base error for fixed-period HAC long-run variance evidence."""

    __slots__ = ()


class ResearchPeriodicHacRiskValidationError(ResearchPeriodicHacRiskError):
    """Violation of a fixed-period HAC risk invariant."""

    __slots__ = ()


class ResearchPeriodicHacRiskStatus(StrEnum):
    DEFINED = "defined"
    ZERO_LONG_RUN_VARIANCE = "zero_long_run_variance"


@dataclass(frozen=True, slots=True)
class ResearchPeriodicHacRiskSnapshotId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicHacRiskValidationError(
                "periodic HAC risk snapshot id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicHacPolicy:
    """Explicit Bartlett/Newey-West lag truncation for one periodic series."""

    max_lag: int

    def __post_init__(self) -> None:
        if type(self.max_lag) is not int or self.max_lag < 0:
            raise ResearchPeriodicHacRiskValidationError(
                "HAC max_lag must be a non-negative integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.max_lag,)


def _derive_hac(
    series: ResearchPeriodicEquityReturnSeries,
    policy: ResearchPeriodicHacPolicy,
) -> tuple[
    int,
    Decimal,
    tuple[Decimal, ...],
    tuple[Decimal, ...],
    ResearchPeriodicHacRiskStatus,
    Decimal,
    Decimal,
]:
    if not isinstance(series, ResearchPeriodicEquityReturnSeries):
        raise ResearchPeriodicHacRiskValidationError(
            "HAC risk requires ResearchPeriodicEquityReturnSeries"
        )
    if not isinstance(policy, ResearchPeriodicHacPolicy):
        raise ResearchPeriodicHacRiskValidationError(
            "HAC risk requires ResearchPeriodicHacPolicy"
        )
    values = tuple(point.return_rate for point in series.returns)
    sample_size = len(values)
    if sample_size < 2:
        raise ResearchPeriodicHacRiskValidationError(
            "HAC risk requires at least two periodic returns"
        )
    if policy.max_lag >= sample_size:
        raise ResearchPeriodicHacRiskValidationError(
            "HAC max_lag must be smaller than periodic return sample size"
        )
    with localcontext(_DECIMAL128):
        n = Decimal(sample_size)
        mean_return = sum(values, Decimal(0)) / n
        centered = tuple(value - mean_return for value in values)
        autocovariances: list[Decimal] = []
        for lag in range(policy.max_lag + 1):
            products = (
                centered[index] * centered[index - lag]
                for index in range(lag, sample_size)
            )
            autocovariances.append(sum(products, Decimal(0)) / n)
        weights = tuple(
            Decimal(1) - Decimal(lag) / Decimal(policy.max_lag + 1)
            for lag in range(1, policy.max_lag + 1)
        )
        long_run_variance = autocovariances[0] + Decimal(2) * sum(
            (
                weight * autocovariances[lag]
                for lag, weight in enumerate(weights, start=1)
            ),
            Decimal(0),
        )
        if long_run_variance < 0:
            raise ResearchPeriodicHacRiskValidationError(
                "Bartlett long-run variance must not be negative"
            )
        long_run_standard_deviation = long_run_variance.sqrt()
    status = (
        ResearchPeriodicHacRiskStatus.ZERO_LONG_RUN_VARIANCE
        if long_run_variance == 0
        else ResearchPeriodicHacRiskStatus.DEFINED
    )
    return (
        sample_size,
        mean_return,
        tuple(autocovariances),
        weights,
        status,
        long_run_variance,
        long_run_standard_deviation,
    )


@dataclass(frozen=True, slots=True)
class ResearchPeriodicHacRiskSnapshot:
    """Bartlett/Newey-West long-run variance over fixed-period returns.

    Autocovariance gamma_k uses denominator n and centered fixed-period returns.
    Bartlett weights are `1 - k/(q+1)` for k=1..q. The result is dependence-
    aware descriptive volatility evidence conditional on the explicit lag q.
    It does not prove stationarity, select an optimal lag, annualize volatility,
    calculate Sharpe, produce inference, or authorize production.
    """

    snapshot_id: ResearchPeriodicHacRiskSnapshotId
    series: ResearchPeriodicEquityReturnSeries
    policy: ResearchPeriodicHacPolicy
    sample_size: int
    mean_return: Decimal
    autocovariances: tuple[Decimal, ...]
    bartlett_weights: tuple[Decimal, ...]
    status: ResearchPeriodicHacRiskStatus
    long_run_variance: Decimal
    long_run_standard_deviation: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, ResearchPeriodicHacRiskSnapshotId):
            raise ResearchPeriodicHacRiskValidationError(
                "snapshot_id must be ResearchPeriodicHacRiskSnapshotId"
            )
        expected = _derive_hac(self.series, self.policy)
        actual = (
            self.sample_size,
            self.mean_return,
            self.autocovariances,
            self.bartlett_weights,
            self.status,
            self.long_run_variance,
            self.long_run_standard_deviation,
        )
        if actual != expected:
            raise ResearchPeriodicHacRiskValidationError(
                "HAC risk values must match source periodic returns and lag policy"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.series.logical_values(),
            self.policy.logical_values(),
            self.sample_size,
            format(self.mean_return, "f"),
            tuple(format(value, "f") for value in self.autocovariances),
            tuple(format(value, "f") for value in self.bartlett_weights),
            self.status.value,
            format(self.long_run_variance, "f"),
            format(self.long_run_standard_deviation, "f"),
        )


def build_research_periodic_hac_risk_snapshot(
    *,
    snapshot_id: ResearchPeriodicHacRiskSnapshotId,
    series: ResearchPeriodicEquityReturnSeries,
    policy: ResearchPeriodicHacPolicy,
) -> Result[ResearchPeriodicHacRiskSnapshot, ResearchPeriodicHacRiskError]:
    """Build dependence-aware periodic volatility evidence without annualization."""

    try:
        (
            sample_size,
            mean_return,
            autocovariances,
            weights,
            status,
            long_run_variance,
            long_run_standard_deviation,
        ) = _derive_hac(series, policy)
        return Success(
            ResearchPeriodicHacRiskSnapshot(
                snapshot_id=snapshot_id,
                series=series,
                policy=policy,
                sample_size=sample_size,
                mean_return=mean_return,
                autocovariances=autocovariances,
                bartlett_weights=weights,
                status=status,
                long_run_variance=long_run_variance,
                long_run_standard_deviation=long_run_standard_deviation,
            )
        )
    except ResearchPeriodicHacRiskError as error:
        return Failure(error)
