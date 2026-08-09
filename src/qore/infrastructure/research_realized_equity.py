from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from uuid import UUID

from qore.infrastructure.proprietary_accounts import MoneyAmount
from qore.infrastructure.research_economic_evidence import ResearchNetEconomicResult
from qore.infrastructure.research_run import ResearchRunEvidence
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchRealizedEquityError(InfrastructureError):
    """Base error for research realized-equity evidence."""

    __slots__ = ()


class ResearchRealizedEquityValidationError(ResearchRealizedEquityError):
    """Violation of a realized-equity path invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ResearchRealizedEquityValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchRealizedEquityValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchRealizedEquityValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ResearchRealizedEquityPathId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research realized equity path id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _canonical_results(
    results: tuple[ResearchNetEconomicResult, ...],
) -> tuple[ResearchNetEconomicResult, ...]:
    if not isinstance(results, tuple) or not results or any(
        not isinstance(item, ResearchNetEconomicResult) for item in results
    ):
        raise ResearchRealizedEquityValidationError(
            "realized equity requires a non-empty immutable net-result tuple"
        )
    ordered = tuple(
        sorted(
            results,
            key=lambda item: (
                item.valued_at.astimezone(UTC),
                str(item.result_id.value),
            ),
        )
    )
    result_ids = tuple(item.result_id for item in ordered)
    if len(set(result_ids)) != len(result_ids):
        raise ResearchRealizedEquityValidationError(
            "realized equity net result ids must be unique"
        )
    run = ordered[0].run
    if any(item.run != run for item in ordered):
        raise ResearchRealizedEquityValidationError(
            "realized equity net results must belong to one research run"
        )
    currency = ordered[0].net_pnl.currency
    if any(item.net_pnl.currency != currency for item in ordered):
        raise ResearchRealizedEquityValidationError(
            "realized equity net results must use one currency"
        )
    fill_ids = tuple(
        fill.fill_id
        for item in ordered
        for fill in (
            *item.gross_result.entry_fills,
            *item.gross_result.exit_fills,
        )
    )
    if len(set(fill_ids)) != len(fill_ids):
        raise ResearchRealizedEquityValidationError(
            "realized equity results must not reuse fill evidence"
        )
    return ordered


@dataclass(frozen=True, slots=True)
class ResearchRealizedEquityPoint:
    """Realized-only equity after one closed net economic result."""

    source_result: ResearchNetEconomicResult
    equity: MoneyAmount
    running_peak: MoneyAmount
    drawdown_amount: MoneyAmount
    drawdown_rate: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.source_result, ResearchNetEconomicResult):
            raise ResearchRealizedEquityValidationError(
                "equity point requires ResearchNetEconomicResult"
            )
        for field_name, value in (
            ("equity", self.equity),
            ("running_peak", self.running_peak),
            ("drawdown_amount", self.drawdown_amount),
        ):
            if not isinstance(value, MoneyAmount):
                raise ResearchRealizedEquityValidationError(
                    f"{field_name} must be MoneyAmount"
                )
        currencies = {
            self.source_result.net_pnl.currency,
            self.equity.currency,
            self.running_peak.currency,
            self.drawdown_amount.currency,
        }
        if len(currencies) != 1:
            raise ResearchRealizedEquityValidationError(
                "equity point monetary values must use one currency"
            )
        if self.running_peak.amount <= 0:
            raise ResearchRealizedEquityValidationError(
                "equity point running peak must remain positive"
            )
        expected_amount = self.running_peak.amount - self.equity.amount
        if expected_amount < 0:
            raise ResearchRealizedEquityValidationError(
                "equity point running peak cannot be below equity"
            )
        if self.drawdown_amount.amount != expected_amount:
            raise ResearchRealizedEquityValidationError(
                "drawdown amount must equal running peak minus equity"
            )
        if not isinstance(self.drawdown_rate, Decimal) or not self.drawdown_rate.is_finite():
            raise ResearchRealizedEquityValidationError(
                "drawdown_rate must be a finite Decimal"
            )
        with localcontext(_DECIMAL128):
            expected_rate = expected_amount / self.running_peak.amount
        if self.drawdown_rate != expected_rate:
            raise ResearchRealizedEquityValidationError(
                "drawdown_rate must equal drawdown amount divided by running peak"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.source_result.logical_values(),
            self.equity.logical_values(),
            self.running_peak.logical_values(),
            self.drawdown_amount.logical_values(),
            format(self.drawdown_rate, "f"),
        )


@dataclass(frozen=True, slots=True)
class ResearchRealizedEquityPath:
    """Closed-result equity path; not mark-to-market or intratrade drawdown.

    The path starts from explicit positive capital and applies canonical net cash
    P&L from closed research economic results. It therefore supports realized
    drawdown evidence only. It does not infer deposits, withdrawals, open-position
    valuation, intratrade excursions, margin, or broker account equity.
    """

    path_id: ResearchRealizedEquityPathId
    run: ResearchRunEvidence
    initial_capital: MoneyAmount
    results: tuple[ResearchNetEconomicResult, ...]
    points: tuple[ResearchRealizedEquityPoint, ...]
    terminal_equity: MoneyAmount
    maximum_drawdown_amount: MoneyAmount
    maximum_drawdown_rate: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.path_id, ResearchRealizedEquityPathId):
            raise ResearchRealizedEquityValidationError(
                "path_id must be ResearchRealizedEquityPathId"
            )
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchRealizedEquityValidationError(
                "realized equity path requires ResearchRunEvidence"
            )
        if not isinstance(self.initial_capital, MoneyAmount) or self.initial_capital.amount <= 0:
            raise ResearchRealizedEquityValidationError(
                "initial_capital must be positive MoneyAmount"
            )
        ordered = _canonical_results(self.results)
        if self.results != ordered:
            raise ResearchRealizedEquityValidationError(
                "realized equity results must use canonical chronological order"
            )
        if self.run != ordered[0].run:
            raise ResearchRealizedEquityValidationError(
                "realized equity path run must match net results"
            )
        if self.initial_capital.currency != ordered[0].net_pnl.currency:
            raise ResearchRealizedEquityValidationError(
                "initial capital currency must match net results"
            )
        expected_points = _derive_points(self.initial_capital, ordered)
        if self.points != expected_points:
            raise ResearchRealizedEquityValidationError(
                "realized equity points must equal values derived from net results"
            )
        expected_terminal = expected_points[-1].equity
        if self.terminal_equity != expected_terminal:
            raise ResearchRealizedEquityValidationError(
                "terminal equity must match final realized equity point"
            )
        expected_max_point = max(expected_points, key=lambda item: item.drawdown_rate)
        if self.maximum_drawdown_amount != expected_max_point.drawdown_amount:
            raise ResearchRealizedEquityValidationError(
                "maximum drawdown amount must match realized equity path"
            )
        if self.maximum_drawdown_rate != expected_max_point.drawdown_rate:
            raise ResearchRealizedEquityValidationError(
                "maximum drawdown rate must match realized equity path"
            )
        _validate_timestamp(self.observed_at, field_name="realized equity observed_at")
        if self.observed_at < ordered[-1].valued_at:
            raise ResearchRealizedEquityValidationError(
                "realized equity path cannot predate latest net result"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.path_id.logical_values(),
            self.run.logical_values(),
            self.initial_capital.logical_values(),
            tuple(item.logical_values() for item in self.results),
            tuple(item.logical_values() for item in self.points),
            self.terminal_equity.logical_values(),
            self.maximum_drawdown_amount.logical_values(),
            format(self.maximum_drawdown_rate, "f"),
            self.observed_at.isoformat(),
        )


def _derive_points(
    initial_capital: MoneyAmount,
    results: tuple[ResearchNetEconomicResult, ...],
) -> tuple[ResearchRealizedEquityPoint, ...]:
    currency = initial_capital.currency
    equity = initial_capital.amount
    peak = initial_capital.amount
    points: list[ResearchRealizedEquityPoint] = []
    for result in results:
        equity += result.net_pnl.amount
        if equity > peak:
            peak = equity
        drawdown_amount = peak - equity
        with localcontext(_DECIMAL128):
            drawdown_rate = drawdown_amount / peak
        points.append(
            ResearchRealizedEquityPoint(
                source_result=result,
                equity=MoneyAmount(currency=currency, amount=equity),
                running_peak=MoneyAmount(currency=currency, amount=peak),
                drawdown_amount=MoneyAmount(currency=currency, amount=drawdown_amount),
                drawdown_rate=drawdown_rate,
            )
        )
    return tuple(points)


def build_research_realized_equity_path(
    *,
    path_id: ResearchRealizedEquityPathId,
    initial_capital: MoneyAmount,
    results: tuple[ResearchNetEconomicResult, ...],
    observed_at: datetime,
) -> Result[ResearchRealizedEquityPath, ResearchRealizedEquityError]:
    """Build a realized-only equity path from closed net economic evidence."""

    try:
        if not isinstance(initial_capital, MoneyAmount) or initial_capital.amount <= 0:
            raise ResearchRealizedEquityValidationError(
                "initial_capital must be positive MoneyAmount"
            )
        ordered = _canonical_results(results)
        if initial_capital.currency != ordered[0].net_pnl.currency:
            raise ResearchRealizedEquityValidationError(
                "initial capital currency must match net results"
            )
        points = _derive_points(initial_capital, ordered)
        max_point = max(points, key=lambda item: item.drawdown_rate)
        return Success(
            ResearchRealizedEquityPath(
                path_id=path_id,
                run=ordered[0].run,
                initial_capital=initial_capital,
                results=ordered,
                points=points,
                terminal_equity=points[-1].equity,
                maximum_drawdown_amount=max_point.drawdown_amount,
                maximum_drawdown_rate=max_point.drawdown_rate,
                observed_at=observed_at,
            )
        )
    except ResearchRealizedEquityError as error:
        return Failure(error)
