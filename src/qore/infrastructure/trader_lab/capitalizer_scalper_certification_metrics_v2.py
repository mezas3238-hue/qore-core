"""Edge-first certification metrics for QORE Capitalizer Cognitive Scalper V1.

The report is descriptive evidence. It never promotes a trader or changes strategy
logic. Metrics are computed from one explicit realized-R ledger and one explicit
window. Daily Sharpe/Sortino use New-York operating dates, include zero-return
weekdays with no trades, conservatively count weekday holidays as zero when no
provider calendar is supplied, use 252 periods/year, zero risk-free return and
zero MAR, and never fabricate infinite ratios.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)

IDENTITY = "QORE_CAPITALIZER_SCALPER_CERTIFICATION_METRICS_V2"
_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)
_ANNUALIZATION_PERIODS = Decimal("252")
_SQRT_252 = _ANNUALIZATION_PERIODS.sqrt()


@dataclass(frozen=True, slots=True)
class TradeEconomics:
    trades: int
    wins: int
    losses: int
    flats: int
    win_rate: str
    total_r: str
    expectancy_r_per_trade: str
    gross_profit_r: str
    gross_loss_r: str
    profit_factor: str | None
    average_winner_r: str | None
    average_loser_r_abs: str | None
    payoff_ratio: str | None
    max_drawdown_r: str
    max_losing_streak: int


@dataclass(frozen=True, slots=True)
class DailyRiskAdjustedMetrics:
    window_start: str
    window_end_exclusive: str
    return_unit: str
    zero_trade_weekdays_included: bool
    weekday_holidays_without_provider_calendar_count_as_zero: bool
    business_day_observations: int
    active_trade_days: int
    zero_trade_days: int
    risk_free_rate_per_day: str
    minimum_acceptable_return_per_day: str
    annualization_periods_per_year: int
    standard_deviation_uses_sample_denominator_n_minus_1: bool
    downside_deviation_uses_all_periods_denominator: bool
    mean_daily_r: str
    sample_standard_deviation_r: str | None
    downside_deviation_r: str | None
    sharpe_daily: str | None
    sharpe_annualized: str | None
    sortino_daily: str | None
    sortino_annualized: str | None


@dataclass(frozen=True, slots=True)
class LossCluster:
    cluster_id: int
    start_entry_at: str
    end_entry_at: str
    trade_count: int
    total_r: str
    duration_minutes: int
    symbols: tuple[str, ...]
    sessions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LossClusterMetrics:
    cluster_count: int
    losing_trade_count: int
    max_cluster_length: int
    mean_cluster_length: str
    worst_cluster_total_r: str
    clusters: tuple[LossCluster, ...]


@dataclass(frozen=True, slots=True)
class SegmentMetrics:
    dimension: str
    value: str
    economics: TradeEconomics


@dataclass(frozen=True, slots=True)
class CertificationMetricsReport:
    identity: str
    population_role: str
    window_start: str
    window_end_exclusive: str
    economics: TradeEconomics
    daily_risk_adjusted: DailyRiskAdjustedMetrics
    loss_clustering: LossClusterMetrics
    by_year: tuple[SegmentMetrics, ...]
    by_session: tuple[SegmentMetrics, ...]
    by_symbol: tuple[SegmentMetrics, ...]
    by_side: tuple[SegmentMetrics, ...]
    entrant_identity_count: int
    density_trades_per_eligible_weekday: str
    density_is_descriptive_not_primary_gate: bool = True
    future_outcomes_used_as_decision_features: bool = False
    classification_performed: bool = False
    trader_certified: bool = False


@dataclass(frozen=True, slots=True)
class WinnerPreservationReport:
    control_trades: int
    candidate_trades: int
    same_entrant_identities: bool
    control_winners: int
    preserved_control_winners: int
    winner_count_preservation: str | None
    control_winner_r: str
    candidate_r_on_control_winners: str
    winner_r_preservation: str | None
    control_losers: int
    recalled_control_losses: int
    loss_recall: str | None
    density_retention: str
    profit_factor_delta: str | None
    expectancy_delta_r_per_trade: str
    sharpe_annualized_delta: str | None
    max_drawdown_delta_r: str


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("trade timestamp must be timezone-aware")
    return parsed


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _canonical(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[milestone.SimulatedTrade, ...]:
    ordered = tuple(
        sorted(rows, key=lambda row: (_aware(row.entry_at), row.symbol))
    )
    keys = tuple((row.symbol, row.entry_at) for row in ordered)
    if len(set(keys)) != len(keys):
        raise ValueError("certification metrics require unique entrant identities")
    return ordered


def _returns(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[Decimal, ...]:
    return tuple(Decimal(row.realized_gross_r) for row in _canonical(rows))


def _economics(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> TradeEconomics:
    values = _returns(rows)
    trades = len(values)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flats = trades - wins - losses
    total = sum(values, Decimal("0"))
    expectancy = total / Decimal(trades) if trades else Decimal("0")
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
    profit_factor = (
        gross_profit / gross_loss if gross_loss > 0 else None
    )
    average_winner = (
        gross_profit / Decimal(wins) if wins else None
    )
    average_loser = (
        gross_loss / Decimal(losses) if losses else None
    )
    payoff = (
        average_winner / average_loser
        if average_winner is not None
        and average_loser is not None
        and average_loser > 0
        else None
    )
    win_rate = Decimal(wins) / Decimal(trades) if trades else Decimal("0")

    equity = Decimal("0")
    peak = Decimal("0")
    max_drawdown = Decimal("0")
    current_streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if value < 0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return TradeEconomics(
        trades=trades,
        wins=wins,
        losses=losses,
        flats=flats,
        win_rate=str(win_rate),
        total_r=str(total),
        expectancy_r_per_trade=str(expectancy),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=None if profit_factor is None else str(profit_factor),
        average_winner_r=(
            None if average_winner is None else str(average_winner)
        ),
        average_loser_r_abs=(
            None if average_loser is None else str(average_loser)
        ),
        payoff_ratio=None if payoff is None else str(payoff),
        max_drawdown_r=str(max_drawdown),
        max_losing_streak=max_streak,
    )


def _eligible_operating_dates(
    *,
    window_start: date,
    window_end_exclusive: date,
    observed_dates: set[date],
) -> tuple[date, ...]:
    if window_end_exclusive <= window_start:
        raise ValueError("certification metrics window must be positive")
    days: list[date] = []
    current = window_start
    while current < window_end_exclusive:
        if current.weekday() < 5 or current in observed_dates:
            days.append(current)
        current += timedelta(days=1)
    if not days:
        raise ValueError("certification metrics window has no eligible dates")
    if not observed_dates.issubset(set(days)):
        raise ValueError("trade operating date outside certification window")
    return tuple(days)


def _daily_metrics(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    window_start: date,
    window_end_exclusive: date,
) -> DailyRiskAdjustedMetrics:
    ordered = _canonical(rows)
    by_day: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in ordered:
        operating_date = _parse_date(row.operating_date)
        if not window_start <= operating_date < window_end_exclusive:
            raise ValueError("trade operating date outside declared window")
        by_day[operating_date] += Decimal(row.realized_gross_r)

    eligible = _eligible_operating_dates(
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
        observed_dates=set(by_day),
    )
    values = tuple(by_day.get(day, Decimal("0")) for day in eligible)
    with localcontext(_DECIMAL128):
        mean = sum(values, Decimal("0")) / Decimal(len(values))

    sample_std: Decimal | None = None
    sharpe_daily: Decimal | None = None
    sharpe_annualized: Decimal | None = None
    if len(values) >= 2:
        with localcontext(_DECIMAL128):
            variance = (
                sum(
                    ((value - mean) * (value - mean) for value in values),
                    Decimal("0"),
                )
                / Decimal(len(values) - 1)
            )
            if variance > 0:
                sample_std = variance.sqrt()
                sharpe_daily = mean / sample_std
                sharpe_annualized = sharpe_daily * _SQRT_252

    with localcontext(_DECIMAL128):
        downside_variance = (
            sum(
                (
                    min(Decimal("0"), value)
                    * min(Decimal("0"), value)
                    for value in values
                ),
                Decimal("0"),
            )
            / Decimal(len(values))
        )
        downside = downside_variance.sqrt()

    sortino_daily: Decimal | None = None
    sortino_annualized: Decimal | None = None
    if downside > 0:
        with localcontext(_DECIMAL128):
            sortino_daily = mean / downside
            sortino_annualized = sortino_daily * _SQRT_252

    return DailyRiskAdjustedMetrics(
        window_start=window_start.isoformat(),
        window_end_exclusive=window_end_exclusive.isoformat(),
        return_unit="NEW_YORK_OPERATING_DATE_REALIZED_R",
        zero_trade_weekdays_included=True,
        weekday_holidays_without_provider_calendar_count_as_zero=True,
        business_day_observations=len(values),
        active_trade_days=sum(value != 0 for value in values),
        zero_trade_days=sum(value == 0 for value in values),
        risk_free_rate_per_day="0",
        minimum_acceptable_return_per_day="0",
        annualization_periods_per_year=252,
        standard_deviation_uses_sample_denominator_n_minus_1=True,
        downside_deviation_uses_all_periods_denominator=True,
        mean_daily_r=str(mean),
        sample_standard_deviation_r=(
            None if sample_std is None else str(sample_std)
        ),
        downside_deviation_r=str(downside),
        sharpe_daily=None if sharpe_daily is None else str(sharpe_daily),
        sharpe_annualized=(
            None
            if sharpe_annualized is None
            else str(sharpe_annualized)
        ),
        sortino_daily=None if sortino_daily is None else str(sortino_daily),
        sortino_annualized=(
            None
            if sortino_annualized is None
            else str(sortino_annualized)
        ),
    )


def _loss_clusters(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> LossClusterMetrics:
    ordered = _canonical(rows)
    clusters: list[LossCluster] = []
    active: list[milestone.SimulatedTrade] = []

    def flush() -> None:
        if not active:
            return
        start = _aware(active[0].entry_at)
        end = _aware(active[-1].entry_at)
        clusters.append(
            LossCluster(
                cluster_id=len(clusters) + 1,
                start_entry_at=active[0].entry_at,
                end_entry_at=active[-1].entry_at,
                trade_count=len(active),
                total_r=str(
                    sum(
                        (
                            Decimal(row.realized_gross_r)
                            for row in active
                        ),
                        Decimal("0"),
                    )
                ),
                duration_minutes=int((end - start).total_seconds() // 60),
                symbols=tuple(sorted({row.symbol for row in active})),
                sessions=tuple(sorted({row.session for row in active})),
            )
        )
        active.clear()

    for row in ordered:
        if Decimal(row.realized_gross_r) < 0:
            active.append(row)
        else:
            flush()
    flush()

    losing_trade_count = sum(cluster.trade_count for cluster in clusters)
    if clusters:
        worst = min(Decimal(cluster.total_r) for cluster in clusters)
        mean_length = (
            Decimal(losing_trade_count) / Decimal(len(clusters))
        )
        max_length = max(cluster.trade_count for cluster in clusters)
    else:
        worst = Decimal("0")
        mean_length = Decimal("0")
        max_length = 0

    return LossClusterMetrics(
        cluster_count=len(clusters),
        losing_trade_count=losing_trade_count,
        max_cluster_length=max_length,
        mean_cluster_length=str(mean_length),
        worst_cluster_total_r=str(worst),
        clusters=tuple(clusters),
    )


def _segments(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    dimension: str,
) -> tuple[SegmentMetrics, ...]:
    grouped: dict[str, list[milestone.SimulatedTrade]] = defaultdict(list)
    for row in _canonical(rows):
        if dimension == "year":
            value = str(_parse_date(row.operating_date).year)
        elif dimension == "session":
            value = row.session
        elif dimension == "symbol":
            value = row.symbol
        elif dimension == "side":
            value = row.side
        else:
            raise ValueError(f"unknown segment dimension {dimension}")
        grouped[value].append(row)
    return tuple(
        SegmentMetrics(
            dimension=dimension,
            value=value,
            economics=_economics(tuple(grouped[value])),
        )
        for value in sorted(grouped)
    )


def build_certification_metrics_report(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    population_role: str,
    window_start: date,
    window_end_exclusive: date,
) -> CertificationMetricsReport:
    if not population_role:
        raise ValueError("population_role must be non-empty")
    ordered = _canonical(rows)
    daily = _daily_metrics(
        ordered,
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
    )
    economics = _economics(ordered)
    return CertificationMetricsReport(
        identity=IDENTITY,
        population_role=population_role,
        window_start=window_start.isoformat(),
        window_end_exclusive=window_end_exclusive.isoformat(),
        economics=economics,
        daily_risk_adjusted=daily,
        loss_clustering=_loss_clusters(ordered),
        by_year=_segments(ordered, dimension="year"),
        by_session=_segments(ordered, dimension="session"),
        by_symbol=_segments(ordered, dimension="symbol"),
        by_side=_segments(ordered, dimension="side"),
        entrant_identity_count=len(ordered),
        density_trades_per_eligible_weekday=str(
            Decimal(len(ordered))
            / Decimal(daily.business_day_observations)
        ),
    )


def compare_winner_preservation(
    control_rows: tuple[milestone.SimulatedTrade, ...],
    candidate_rows: tuple[milestone.SimulatedTrade, ...],
    *,
    window_start: date,
    window_end_exclusive: date,
) -> WinnerPreservationReport:
    control = _canonical(control_rows)
    candidate = _canonical(candidate_rows)
    control_by_key = {
        (row.symbol, row.entry_at): row for row in control
    }
    candidate_by_key = {
        (row.symbol, row.entry_at): row for row in candidate
    }
    control_keys = set(control_by_key)
    candidate_keys = set(candidate_by_key)

    winner_keys = {
        key
        for key, row in control_by_key.items()
        if Decimal(row.realized_gross_r) > 0
    }
    loser_keys = {
        key
        for key, row in control_by_key.items()
        if Decimal(row.realized_gross_r) < 0
    }
    preserved_winner_keys = {
        key
        for key in winner_keys
        if key in candidate_by_key
        and Decimal(candidate_by_key[key].realized_gross_r) > 0
    }
    recalled_losses = {
        key
        for key in loser_keys
        if key not in candidate_by_key
        or Decimal(candidate_by_key[key].realized_gross_r) >= 0
    }

    control_winner_r = sum(
        (
            Decimal(control_by_key[key].realized_gross_r)
            for key in winner_keys
        ),
        Decimal("0"),
    )
    candidate_r_on_control_winners = sum(
        (
            max(
                Decimal("0"),
                Decimal(candidate_by_key[key].realized_gross_r),
            )
            for key in winner_keys
            if key in candidate_by_key
        ),
        Decimal("0"),
    )
    winner_count_preservation = (
        Decimal(len(preserved_winner_keys)) / Decimal(len(winner_keys))
        if winner_keys
        else None
    )
    winner_r_preservation = (
        candidate_r_on_control_winners / control_winner_r
        if control_winner_r > 0
        else None
    )
    loss_recall = (
        Decimal(len(recalled_losses)) / Decimal(len(loser_keys))
        if loser_keys
        else None
    )
    density_retention = (
        Decimal(len(candidate)) / Decimal(len(control))
        if control
        else Decimal("0")
    )

    control_economics = _economics(control)
    candidate_economics = _economics(candidate)
    control_daily = _daily_metrics(
        control,
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
    )
    candidate_daily = _daily_metrics(
        candidate,
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
    )
    pf_delta: Decimal | None = None
    if (
        control_economics.profit_factor is not None
        and candidate_economics.profit_factor is not None
    ):
        pf_delta = (
            Decimal(candidate_economics.profit_factor)
            - Decimal(control_economics.profit_factor)
        )
    sharpe_delta: Decimal | None = None
    if (
        control_daily.sharpe_annualized is not None
        and candidate_daily.sharpe_annualized is not None
    ):
        sharpe_delta = (
            Decimal(candidate_daily.sharpe_annualized)
            - Decimal(control_daily.sharpe_annualized)
        )

    return WinnerPreservationReport(
        control_trades=len(control),
        candidate_trades=len(candidate),
        same_entrant_identities=control_keys == candidate_keys,
        control_winners=len(winner_keys),
        preserved_control_winners=len(preserved_winner_keys),
        winner_count_preservation=(
            None
            if winner_count_preservation is None
            else str(winner_count_preservation)
        ),
        control_winner_r=str(control_winner_r),
        candidate_r_on_control_winners=str(
            candidate_r_on_control_winners
        ),
        winner_r_preservation=(
            None if winner_r_preservation is None else str(winner_r_preservation)
        ),
        control_losers=len(loser_keys),
        recalled_control_losses=len(recalled_losses),
        loss_recall=None if loss_recall is None else str(loss_recall),
        density_retention=str(density_retention),
        profit_factor_delta=None if pf_delta is None else str(pf_delta),
        expectancy_delta_r_per_trade=str(
            Decimal(candidate_economics.expectancy_r_per_trade)
            - Decimal(control_economics.expectancy_r_per_trade)
        ),
        sharpe_annualized_delta=(
            None if sharpe_delta is None else str(sharpe_delta)
        ),
        max_drawdown_delta_r=str(
            Decimal(candidate_economics.max_drawdown_r)
            - Decimal(control_economics.max_drawdown_r)
        ),
    )


def _load_rows(path: Path) -> tuple[milestone.SimulatedTrade, ...]:
    rows: list[milestone.SimulatedTrade] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            if raw.strip():
                item: Any = json.loads(raw)
                if not isinstance(item, dict):
                    raise ValueError("trade ledger row must be object")
                rows.append(milestone.SimulatedTrade(**item))
    return tuple(rows)


def write_report(
    report: CertificationMetricsReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-scalper-certification-metrics-v2.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--population-role", required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end-exclusive", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_certification_metrics_report(
        _load_rows(args.ledger),
        population_role=args.population_role,
        window_start=_parse_date(args.window_start),
        window_end_exclusive=_parse_date(args.window_end_exclusive),
    )
    write_report(report, args.output)
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
