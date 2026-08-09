from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from uuid import UUID

from qore.infrastructure.proprietary_accounts import MoneyAmount
from qore.infrastructure.research_periodic_equity import (
    ResearchEquityObservationId,
    ResearchEquityValuationObservation,
    ResearchPeriodicEquityReturnSeries,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchPeriodicDrawdownError(InfrastructureError):
    """Base error for fixed-grid equity drawdown evidence."""

    __slots__ = ()


class ResearchPeriodicDrawdownValidationError(ResearchPeriodicDrawdownError):
    """Violation of a periodic drawdown invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ResearchPeriodicDrawdownSnapshotId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicDrawdownValidationError(
                "periodic drawdown snapshot id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicDrawdownPoint:
    observation_id: ResearchEquityObservationId
    equity: MoneyAmount
    running_peak: MoneyAmount
    drawdown_amount: MoneyAmount
    drawdown_rate: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, ResearchEquityObservationId):
            raise ResearchPeriodicDrawdownValidationError(
                "drawdown point observation_id must be ResearchEquityObservationId"
            )
        for field_name, value in (
            ("equity", self.equity),
            ("running_peak", self.running_peak),
            ("drawdown_amount", self.drawdown_amount),
        ):
            if not isinstance(value, MoneyAmount):
                raise ResearchPeriodicDrawdownValidationError(
                    f"drawdown point {field_name} must be MoneyAmount"
                )
        if len(
            {
                self.equity.currency,
                self.running_peak.currency,
                self.drawdown_amount.currency,
            }
        ) != 1:
            raise ResearchPeriodicDrawdownValidationError(
                "drawdown point monetary values must use one currency"
            )
        if self.equity.amount <= 0 or self.running_peak.amount <= 0:
            raise ResearchPeriodicDrawdownValidationError(
                "drawdown point equity and running peak must remain positive"
            )
        expected_amount = self.running_peak.amount - self.equity.amount
        if expected_amount < 0:
            raise ResearchPeriodicDrawdownValidationError(
                "drawdown point running peak cannot be below equity"
            )
        if self.drawdown_amount.amount != expected_amount:
            raise ResearchPeriodicDrawdownValidationError(
                "drawdown amount must equal running peak minus equity"
            )
        if not isinstance(self.drawdown_rate, Decimal) or not self.drawdown_rate.is_finite():
            raise ResearchPeriodicDrawdownValidationError(
                "drawdown_rate must be a finite Decimal"
            )
        with localcontext(_DECIMAL128):
            expected_rate = expected_amount / self.running_peak.amount
        if self.drawdown_rate != expected_rate:
            raise ResearchPeriodicDrawdownValidationError(
                "drawdown_rate must equal drawdown amount divided by running peak"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.equity.logical_values(),
            self.running_peak.logical_values(),
            self.drawdown_amount.logical_values(),
            format(self.drawdown_rate, "f"),
        )


def _derive_points(
    series: ResearchPeriodicEquityReturnSeries,
) -> tuple[ResearchPeriodicDrawdownPoint, ...]:
    if not isinstance(series, ResearchPeriodicEquityReturnSeries):
        raise ResearchPeriodicDrawdownValidationError(
            "periodic drawdown requires ResearchPeriodicEquityReturnSeries"
        )
    observations = series.observations
    if not observations or any(
        not isinstance(item, ResearchEquityValuationObservation) for item in observations
    ):
        raise ResearchPeriodicDrawdownValidationError(
            "periodic drawdown requires canonical equity valuation observations"
        )
    currency = observations[0].equity.currency
    if any(item.equity.currency != currency for item in observations):
        raise ResearchPeriodicDrawdownValidationError(
            "periodic drawdown observations must use one currency"
        )
    peak = observations[0].equity.amount
    points: list[ResearchPeriodicDrawdownPoint] = []
    for observation in observations:
        equity = observation.equity.amount
        if equity > peak:
            peak = equity
        drawdown_amount = peak - equity
        with localcontext(_DECIMAL128):
            drawdown_rate = drawdown_amount / peak
        points.append(
            ResearchPeriodicDrawdownPoint(
                observation_id=observation.observation_id,
                equity=observation.equity,
                running_peak=MoneyAmount(currency=currency, amount=peak),
                drawdown_amount=MoneyAmount(
                    currency=currency,
                    amount=drawdown_amount,
                ),
                drawdown_rate=drawdown_rate,
            )
        )
    return tuple(points)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicDrawdownSnapshot:
    """Drawdown observed on the exact fixed periodic equity valuation grid.

    This is stronger than closed-trade-only realized drawdown because it can
    reflect open-position valuation whenever the bound valuation model includes
    it. It is still grid-observed drawdown: excursions between valuation points
    are not measured and no intraperiod maximum-drawdown claim is made.
    """

    snapshot_id: ResearchPeriodicDrawdownSnapshotId
    series: ResearchPeriodicEquityReturnSeries
    points: tuple[ResearchPeriodicDrawdownPoint, ...]
    maximum_drawdown_amount: MoneyAmount
    maximum_drawdown_rate: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, ResearchPeriodicDrawdownSnapshotId):
            raise ResearchPeriodicDrawdownValidationError(
                "snapshot_id must be ResearchPeriodicDrawdownSnapshotId"
            )
        if not isinstance(self.series, ResearchPeriodicEquityReturnSeries):
            raise ResearchPeriodicDrawdownValidationError(
                "periodic drawdown snapshot requires ResearchPeriodicEquityReturnSeries"
            )
        expected_points = _derive_points(self.series)
        if self.points != expected_points:
            raise ResearchPeriodicDrawdownValidationError(
                "periodic drawdown points must equal fixed-grid equity evidence"
            )
        expected_max_amount = max(
            (point.drawdown_amount.amount for point in expected_points),
        )
        expected_max_rate = max(point.drawdown_rate for point in expected_points)
        currency = expected_points[0].equity.currency
        if self.maximum_drawdown_amount != MoneyAmount(
            currency=currency,
            amount=expected_max_amount,
        ):
            raise ResearchPeriodicDrawdownValidationError(
                "maximum_drawdown_amount must match periodic drawdown points"
            )
        if self.maximum_drawdown_rate != expected_max_rate:
            raise ResearchPeriodicDrawdownValidationError(
                "maximum_drawdown_rate must match periodic drawdown points"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.series.logical_values(),
            tuple(point.logical_values() for point in self.points),
            self.maximum_drawdown_amount.logical_values(),
            format(self.maximum_drawdown_rate, "f"),
        )


def build_research_periodic_drawdown_snapshot(
    *,
    snapshot_id: ResearchPeriodicDrawdownSnapshotId,
    series: ResearchPeriodicEquityReturnSeries,
) -> Result[ResearchPeriodicDrawdownSnapshot, ResearchPeriodicDrawdownError]:
    """Build fixed-grid drawdown without inferring intraperiod excursions."""

    try:
        points = _derive_points(series)
        currency = points[0].equity.currency
        maximum_drawdown_amount = MoneyAmount(
            currency=currency,
            amount=max(point.drawdown_amount.amount for point in points),
        )
        maximum_drawdown_rate = max(point.drawdown_rate for point in points)
        return Success(
            ResearchPeriodicDrawdownSnapshot(
                snapshot_id=snapshot_id,
                series=series,
                points=points,
                maximum_drawdown_amount=maximum_drawdown_amount,
                maximum_drawdown_rate=maximum_drawdown_rate,
            )
        )
    except ResearchPeriodicDrawdownError as error:
        return Failure(error)
