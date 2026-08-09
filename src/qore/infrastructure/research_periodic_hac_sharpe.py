from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.research_periodic_hac_risk import (
    ResearchPeriodicHacRiskSnapshot,
    ResearchPeriodicHacRiskStatus,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchPeriodicHacSharpeError(InfrastructureError):
    """Base error for dependence-aware per-period Sharpe evidence."""

    __slots__ = ()


class ResearchPeriodicHacSharpeValidationError(ResearchPeriodicHacSharpeError):
    """Violation of a dependence-aware Sharpe invariant."""

    __slots__ = ()


class ResearchPeriodicHacSharpeStatus(StrEnum):
    DEFINED = "defined"
    ZERO_LONG_RUN_VARIANCE = "zero_long_run_variance"


@dataclass(frozen=True, slots=True)
class ResearchPeriodicHacSharpeMetricId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicHacSharpeValidationError(
                "periodic HAC Sharpe metric id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicHacSharpePolicy:
    risk_free_rate_per_period: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.risk_free_rate_per_period, Decimal)
            or not self.risk_free_rate_per_period.is_finite()
        ):
            raise ResearchPeriodicHacSharpeValidationError(
                "risk_free_rate_per_period must be a finite Decimal"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (format(self.risk_free_rate_per_period, "f"),)


def _derive_metric(
    risk: ResearchPeriodicHacRiskSnapshot,
    policy: ResearchPeriodicHacSharpePolicy,
) -> tuple[ResearchPeriodicHacSharpeStatus, Decimal, Decimal | None]:
    if not isinstance(risk, ResearchPeriodicHacRiskSnapshot):
        raise ResearchPeriodicHacSharpeValidationError(
            "periodic HAC Sharpe requires ResearchPeriodicHacRiskSnapshot"
        )
    if not isinstance(policy, ResearchPeriodicHacSharpePolicy):
        raise ResearchPeriodicHacSharpeValidationError(
            "periodic HAC Sharpe requires ResearchPeriodicHacSharpePolicy"
        )
    with localcontext(_DECIMAL128):
        mean_excess_return = risk.mean_return - policy.risk_free_rate_per_period
    if risk.status is ResearchPeriodicHacRiskStatus.ZERO_LONG_RUN_VARIANCE:
        return (
            ResearchPeriodicHacSharpeStatus.ZERO_LONG_RUN_VARIANCE,
            mean_excess_return,
            None,
        )
    if risk.status is not ResearchPeriodicHacRiskStatus.DEFINED:
        raise ResearchPeriodicHacSharpeValidationError(
            "unsupported HAC risk status"
        )
    if risk.long_run_standard_deviation <= 0:
        raise ResearchPeriodicHacSharpeValidationError(
            "defined HAC risk requires positive long-run standard deviation"
        )
    with localcontext(_DECIMAL128):
        ratio = mean_excess_return / risk.long_run_standard_deviation
    return ResearchPeriodicHacSharpeStatus.DEFINED, mean_excess_return, ratio


@dataclass(frozen=True, slots=True)
class ResearchPeriodicHacSharpeMetric:
    """Non-annualized Sharpe-like ratio using HAC long-run standard deviation.

    The numerator is the fixed-period mean excess return and the denominator is
    the Bartlett/Newey-West long-run standard deviation from the exact source
    series and explicit lag policy. This is dependence-aware descriptive evidence,
    not proof of stationarity, asymptotic validity, statistical significance,
    predictive performance, annualized Sharpe, or production readiness.
    """

    metric_id: ResearchPeriodicHacSharpeMetricId
    risk: ResearchPeriodicHacRiskSnapshot
    policy: ResearchPeriodicHacSharpePolicy
    status: ResearchPeriodicHacSharpeStatus
    mean_excess_return: Decimal
    hac_sharpe_ratio: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.metric_id, ResearchPeriodicHacSharpeMetricId):
            raise ResearchPeriodicHacSharpeValidationError(
                "metric_id must be ResearchPeriodicHacSharpeMetricId"
            )
        expected = _derive_metric(self.risk, self.policy)
        actual = (self.status, self.mean_excess_return, self.hac_sharpe_ratio)
        if actual != expected:
            raise ResearchPeriodicHacSharpeValidationError(
                "HAC Sharpe values must match source long-run risk and policy"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metric_id.logical_values(),
            self.risk.logical_values(),
            self.policy.logical_values(),
            self.status.value,
            format(self.mean_excess_return, "f"),
            (
                format(self.hac_sharpe_ratio, "f")
                if self.hac_sharpe_ratio is not None
                else None
            ),
        )


def build_research_periodic_hac_sharpe_metric(
    *,
    metric_id: ResearchPeriodicHacSharpeMetricId,
    risk: ResearchPeriodicHacRiskSnapshot,
    policy: ResearchPeriodicHacSharpePolicy,
) -> Result[ResearchPeriodicHacSharpeMetric, ResearchPeriodicHacSharpeError]:
    """Build dependence-aware per-period Sharpe evidence without annualization."""

    try:
        status, mean_excess_return, ratio = _derive_metric(risk, policy)
        return Success(
            ResearchPeriodicHacSharpeMetric(
                metric_id=metric_id,
                risk=risk,
                policy=policy,
                status=status,
                mean_excess_return=mean_excess_return,
                hac_sharpe_ratio=ratio,
            )
        )
    except ResearchPeriodicHacSharpeError as error:
        return Failure(error)
