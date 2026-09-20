"""Daily-loss and cross-session path forensics for QORE Capitalizer.

Consumed-development evidence only. This lab measures daily realized-R behavior for selected
MAX3 routing policies without changing entry/exit logic. It answers a separate question from
total drawdown: how much can the trader lose inside one New York operating date as Asia,
London, and New York sessions accumulate?

No funded-account percentage conversion is performed here because R-to-equity sizing remains
QORE Risk sovereign. No daily stop rule is selected. No outcome-aware runtime gating, numeric
threshold optimization, candidate freeze, fresh holdout claim, or promotion is introduced.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from statistics import median, quantiles

from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
    _load_candidates,
)
from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    _session_key,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_session_compatibility_routing import (
    _select,
)

IDENTITY = "QORE_CAPITALIZER_DAILY_LOSS_FORENSICS_V1"

POLICIES = (
    "MAX3_BASELINE",
    "BLOCK_LONDON_PLUS_NEW_YORK_WEAK_PAIRS_V1",
    "BLOCK_EXTENDED_WEAK_SIDE_PAIRS_V1",
)


@dataclass(frozen=True, slots=True)
class CapitalizerDailyLossDistribution:
    days: int
    positive_days: int
    flat_days: int
    negative_days: int
    total_r: str
    mean_daily_r: str
    median_daily_r: str
    p25_daily_r: str
    p75_daily_r: str
    worst_day_r: str
    best_day_r: str
    days_le_minus_1r: int
    days_le_minus_2r: int
    days_le_minus_3r: int
    days_le_minus_4r: int
    days_le_minus_5r: int
    days_le_minus_6r: int


@dataclass(frozen=True, slots=True)
class CapitalizerDailyLossPolicy:
    policy: str
    tie_policy: str
    selected_trades: int
    distribution: CapitalizerDailyLossDistribution
    max_intraday_realized_drawdown_r: str
    max_intraday_loss_date: str
    worst_day_session_r: dict[str, str]
    worst_day_trade_count: int
    worst_day_losing_trades: int
    worst_day_winning_trades: int


@dataclass(frozen=True, slots=True)
class CapitalizerDailyLossYear:
    policy: str
    tie_policy: str
    year: int
    days: int
    negative_days: int
    worst_day_r: str
    max_intraday_realized_drawdown_r: str


@dataclass(frozen=True, slots=True)
class CapitalizerDailyLossForensicsReport:
    identity: str
    market_count: int
    symbols: tuple[str, ...]
    policies: tuple[CapitalizerDailyLossPolicy, ...]
    annual: tuple[CapitalizerDailyLossYear, ...]
    daily_realized_r_only: bool = True
    cross_session_path_profiled: bool = True
    funded_percent_conversion_applied: bool = False
    qore_risk_sizing_applied: bool = False
    daily_stop_rule_selected: bool = False
    max3_contract_preserved: bool = True
    positive_pnl_is_not_stop_condition: bool = True
    numeric_threshold_optimization_used: bool = False
    outcome_aware_runtime_gating_used: bool = False
    development_only: bool = True
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    promotion_allowed: bool = False


def _operating_date(candidate: CapitalizerExposureCandidate) -> date:
    return date.fromisoformat(_session_key(candidate.as_trade()).split(":", maxsplit=1)[1])


def _daily_groups(
    selected: tuple[CapitalizerExposureCandidate, ...],
) -> dict[date, tuple[CapitalizerExposureCandidate, ...]]:
    grouped: dict[date, list[CapitalizerExposureCandidate]] = defaultdict(list)
    for candidate in selected:
        grouped[_operating_date(candidate)].append(candidate)
    return {
        day: tuple(sorted(rows, key=lambda item: (item.exit_at, item.entry_at, item.symbol)))
        for day, rows in grouped.items()
    }


def _day_total(rows: tuple[CapitalizerExposureCandidate, ...]) -> Decimal:
    return sum((item.realized_r for item in rows), Decimal("0"))


def _intraday_realized_drawdown(
    rows: tuple[CapitalizerExposureCandidate, ...],
) -> Decimal:
    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    for candidate in rows:
        equity += candidate.realized_r
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def _distribution(
    grouped: dict[date, tuple[CapitalizerExposureCandidate, ...]],
) -> CapitalizerDailyLossDistribution:
    totals = sorted(_day_total(rows) for rows in grouped.values())
    if not totals:
        raise ValueError("daily-loss distribution requires observations")
    quartiles = quantiles(totals, n=4) if len(totals) >= 4 else (totals[0], totals[0], totals[-1])
    total = sum(totals, Decimal("0"))
    return CapitalizerDailyLossDistribution(
        days=len(totals),
        positive_days=sum(value > 0 for value in totals),
        flat_days=sum(value == 0 for value in totals),
        negative_days=sum(value < 0 for value in totals),
        total_r=str(total),
        mean_daily_r=str(total / Decimal(len(totals))),
        median_daily_r=str(median(totals)),
        p25_daily_r=str(quartiles[0]),
        p75_daily_r=str(quartiles[2]),
        worst_day_r=str(totals[0]),
        best_day_r=str(totals[-1]),
        days_le_minus_1r=sum(value <= Decimal("-1") for value in totals),
        days_le_minus_2r=sum(value <= Decimal("-2") for value in totals),
        days_le_minus_3r=sum(value <= Decimal("-3") for value in totals),
        days_le_minus_4r=sum(value <= Decimal("-4") for value in totals),
        days_le_minus_5r=sum(value <= Decimal("-5") for value in totals),
        days_le_minus_6r=sum(value <= Decimal("-6") for value in totals),
    )


def _policy_row(
    *,
    policy: str,
    tie_policy: str,
    candidates: tuple[CapitalizerExposureCandidate, ...],
) -> tuple[CapitalizerDailyLossPolicy, tuple[CapitalizerDailyLossYear, ...]]:
    selected, _ = _select(candidates, policy=policy, tie_policy=tie_policy)
    grouped = _daily_groups(selected)
    distribution = _distribution(grouped)

    intraday = {
        day: _intraday_realized_drawdown(rows)
        for day, rows in grouped.items()
    }
    max_day = max(intraday, key=lambda day: (intraday[day], day))
    max_dd = intraday[max_day]

    worst_day = min(grouped, key=lambda day: (_day_total(grouped[day]), day))
    worst_rows = grouped[worst_day]
    session_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for candidate in worst_rows:
        session = capitalizer_session_at(candidate.entry_at)
        if session is None:
            raise ValueError("daily-loss candidate lost Capitalizer session")
        session_totals[session.value] += candidate.realized_r

    annual_rows: list[CapitalizerDailyLossYear] = []
    years = sorted({day.year for day in grouped})
    for year in years:
        year_groups = {day: rows for day, rows in grouped.items() if day.year == year}
        year_totals = [_day_total(rows) for rows in year_groups.values()]
        year_dds = [_intraday_realized_drawdown(rows) for rows in year_groups.values()]
        annual_rows.append(
            CapitalizerDailyLossYear(
                policy=policy,
                tie_policy=tie_policy,
                year=year,
                days=len(year_groups),
                negative_days=sum(value < 0 for value in year_totals),
                worst_day_r=str(min(year_totals)),
                max_intraday_realized_drawdown_r=str(max(year_dds)),
            )
        )

    return (
        CapitalizerDailyLossPolicy(
            policy=policy,
            tie_policy=tie_policy,
            selected_trades=len(selected),
            distribution=distribution,
            max_intraday_realized_drawdown_r=str(max_dd),
            max_intraday_loss_date=max_day.isoformat(),
            worst_day_session_r={
                session: str(value)
                for session, value in sorted(session_totals.items())
            },
            worst_day_trade_count=len(worst_rows),
            worst_day_losing_trades=sum(item.realized_r < 0 for item in worst_rows),
            worst_day_winning_trades=sum(item.realized_r > 0 for item in worst_rows),
        ),
        tuple(annual_rows),
    )


def build_daily_loss_forensics_report(
    root: Path,
) -> CapitalizerDailyLossForensicsReport:
    candidates = _load_candidates(root)
    policies: list[CapitalizerDailyLossPolicy] = []
    annual: list[CapitalizerDailyLossYear] = []

    for tie_policy in ("SYMBOL_ASC", "SYMBOL_DESC"):
        for policy in POLICIES:
            row, year_rows = _policy_row(
                policy=policy,
                tie_policy=tie_policy,
                candidates=candidates,
            )
            policies.append(row)
            annual.extend(year_rows)

    symbols = tuple(sorted({item.symbol for item in candidates}))
    return CapitalizerDailyLossForensicsReport(
        identity=IDENTITY,
        market_count=len(symbols),
        symbols=symbols,
        policies=tuple(policies),
        annual=tuple(annual),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer daily-loss and cross-session path forensics"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_daily_loss_forensics_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-daily-loss-forensics-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
