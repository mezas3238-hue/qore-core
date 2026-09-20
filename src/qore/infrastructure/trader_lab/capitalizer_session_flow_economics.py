"""Economic diagnostics for the QORE Capitalizer session-flow contract.

This consumed-development lab extends the existing chronological MAX2/MAX3 replay with the
evidence explicitly requested by the Owner: ordinal economics, session PnL distributions,
realized-equity giveback, annual positivity, and the behavior of a third execution when the
session was already positive before that candidate arrived.

It does not invent a profit objective, does not apply QORE Risk allocation or costs, does not
select a rule, and does not freeze/promote a candidate.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_portfolio_session_flow_viability import (
    PortfolioFlowMetrics,
    PortfolioFlowTrade,
    _metrics,
    _ordered,
    _prior_realized,
    _select,
    _session_key,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_session_flow_viability import NEW_YORK

IDENTITY = "QORE_CAPITALIZER_SESSION_FLOW_ECONOMICS_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerOrdinalEconomics:
    policy: str
    tie_policy: str
    session: str
    ordinal: int
    trades: int
    wins: int
    losses: int
    flats: int
    win_rate: str
    prior_realized_positive: int
    prior_realized_nonpositive: int
    metrics: PortfolioFlowMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerPolicyEconomics:
    policy: str
    tie_policy: str
    metrics: PortfolioFlowMetrics
    sessions: int
    sessions_reaching_three: int
    max_trades_in_one_session: int
    opportunities_rejected_by_ceiling: int
    positive_sessions: int
    flat_sessions: int
    negative_sessions: int
    positive_years: int
    years_observed: int
    mean_session_r: str
    median_session_r: str
    p25_session_r: str
    p75_session_r: str
    mean_realized_equity_peak_r: str
    mean_realized_equity_giveback_r: str
    max_realized_equity_giveback_r: str
    sessions_positive_before_third: int
    third_wins_after_positive: int
    third_losses_after_positive: int
    third_flats_after_positive: int
    trade2_positive_rate: str | None
    trade3_positive_rate: str | None
    third_giveback_after_positive_rate: str | None


@dataclass(frozen=True, slots=True)
class CapitalizerSessionFlowEconomicsReport:
    identity: str
    symbol_count: int
    symbols: tuple[str, ...]
    baseline_opportunities: int
    policy_economics: tuple[CapitalizerPolicyEconomics, ...]
    ordinal_economics: tuple[CapitalizerOrdinalEconomics, ...]
    same_session_exit_verified: bool = True
    max_executions_per_session: int = 3
    positive_pnl_is_not_stop_condition: bool = True
    governed_profit_objective_not_modeled: bool = True
    realized_equity_peak_is_not_intrabar_mfe: bool = True
    qore_risk_allocator_applied: bool = False
    cross_market_exposure_allocator_applied: bool = False
    costs_applied: bool = False
    development_only: bool = True
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _load_trade_ledgers(root: Path) -> tuple[PortfolioFlowTrade, ...]:
    paths = sorted(root.rglob("capitalizer-*-session-flow-trades-v1.jsonl"))
    if not paths:
        raise ValueError("no Capitalizer session-flow ledgers found")
    trades: list[PortfolioFlowTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                trades.append(
                    PortfolioFlowTrade(
                        symbol=str(row["symbol"]),
                        entry_at=datetime.fromisoformat(str(row["entry_at"])),
                        exit_at=datetime.fromisoformat(str(row["exit_at"])),
                        realized_r=Decimal(str(row["realized_gross_r"])),
                    )
                )
    return tuple(trades)


def _ratio(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return str(Decimal(numerator) / Decimal(denominator))


def _percentile(values: tuple[Decimal, ...], q: Decimal) -> Decimal:
    if not values:
        raise ValueError("percentile requires observations")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = Decimal(len(ordered) - 1) * q
    lower = int(position.to_integral_value(rounding=ROUND_FLOOR))
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - Decimal(lower)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _session_groups(
    selected: tuple[PortfolioFlowTrade, ...],
    *,
    tie_policy: str,
) -> dict[str, tuple[PortfolioFlowTrade, ...]]:
    grouped: dict[str, list[PortfolioFlowTrade]] = defaultdict(list)
    for trade in _ordered(selected, tie_policy=tie_policy):
        grouped[_session_key(trade)].append(trade)
    return {key: tuple(rows) for key, rows in grouped.items()}


def _realized_path(
    rows: tuple[PortfolioFlowTrade, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    equity = Decimal("0")
    peak = Decimal("0")
    for trade in sorted(rows, key=lambda item: (item.exit_at, item.entry_at, item.symbol)):
        equity += trade.realized_r
        peak = max(peak, equity)
    giveback = peak - equity
    return equity, peak, giveback


def _selected_for_policy(
    trades: tuple[PortfolioFlowTrade, ...],
    *,
    policy: str,
    tie_policy: str,
) -> tuple[PortfolioFlowTrade, ...]:
    if policy == "UNCAPPED_RESEARCH":
        return _ordered(trades, tie_policy=tie_policy)
    return _select(trades, mode=policy, tie_policy=tie_policy)


def _policy_economics(
    trades: tuple[PortfolioFlowTrade, ...],
    *,
    policy: str,
    tie_policy: str,
) -> CapitalizerPolicyEconomics:
    selected = _selected_for_policy(trades, policy=policy, tie_policy=tie_policy)
    groups = _session_groups(selected, tie_policy=tie_policy)
    finals: list[Decimal] = []
    peaks: list[Decimal] = []
    givebacks: list[Decimal] = []
    sessions_positive_before_third = 0
    third_wins = 0
    third_losses = 0
    third_flats = 0
    trade2_positive = 0
    trade2_total = 0
    trade3_positive = 0
    trade3_total = 0

    for rows in groups.values():
        final_r, peak_r, giveback_r = _realized_path(rows)
        finals.append(final_r)
        peaks.append(peak_r)
        givebacks.append(giveback_r)
        if len(rows) >= 2:
            trade2_total += 1
            if rows[1].realized_r > 0:
                trade2_positive += 1
        if len(rows) >= 3:
            trade3_total += 1
            if rows[2].realized_r > 0:
                trade3_positive += 1
            prior = _prior_realized(rows[:2], rows[2])
            if prior > 0:
                sessions_positive_before_third += 1
                if rows[2].realized_r > 0:
                    third_wins += 1
                elif rows[2].realized_r < 0:
                    third_losses += 1
                else:
                    third_flats += 1

    by_year: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for trade in selected:
        by_year[trade.entry_at.astimezone(NEW_YORK).year] += trade.realized_r

    final_tuple = tuple(finals)
    peak_tuple = tuple(peaks)
    giveback_tuple = tuple(givebacks)
    sessions = len(final_tuple)
    positive = sum(value > 0 for value in final_tuple)
    negative = sum(value < 0 for value in final_tuple)
    flat = sessions - positive - negative
    mean_final = sum(final_tuple, Decimal("0")) / Decimal(sessions)
    mean_peak = sum(peak_tuple, Decimal("0")) / Decimal(sessions)
    mean_giveback = sum(giveback_tuple, Decimal("0")) / Decimal(sessions)

    return CapitalizerPolicyEconomics(
        policy=policy,
        tie_policy=tie_policy,
        metrics=_metrics(selected),
        sessions=sessions,
        sessions_reaching_three=sum(len(rows) >= 3 for rows in groups.values()),
        max_trades_in_one_session=max(len(rows) for rows in groups.values()),
        opportunities_rejected_by_ceiling=len(trades) - len(selected),
        positive_sessions=positive,
        flat_sessions=flat,
        negative_sessions=negative,
        positive_years=sum(total > 0 for total in by_year.values()),
        years_observed=len(by_year),
        mean_session_r=str(mean_final),
        median_session_r=str(_percentile(final_tuple, Decimal("0.5"))),
        p25_session_r=str(_percentile(final_tuple, Decimal("0.25"))),
        p75_session_r=str(_percentile(final_tuple, Decimal("0.75"))),
        mean_realized_equity_peak_r=str(mean_peak),
        mean_realized_equity_giveback_r=str(mean_giveback),
        max_realized_equity_giveback_r=str(max(giveback_tuple)),
        sessions_positive_before_third=sessions_positive_before_third,
        third_wins_after_positive=third_wins,
        third_losses_after_positive=third_losses,
        third_flats_after_positive=third_flats,
        trade2_positive_rate=_ratio(trade2_positive, trade2_total),
        trade3_positive_rate=_ratio(trade3_positive, trade3_total),
        third_giveback_after_positive_rate=_ratio(
            third_losses,
            sessions_positive_before_third,
        ),
    )


def _ordinal_economics(
    trades: tuple[PortfolioFlowTrade, ...],
    *,
    policy: str,
    tie_policy: str,
) -> tuple[CapitalizerOrdinalEconomics, ...]:
    selected = _selected_for_policy(trades, policy=policy, tie_policy=tie_policy)
    groups = _session_groups(selected, tie_policy=tie_policy)
    cells: list[CapitalizerOrdinalEconomics] = []
    sessions = ("ASIA", "LONDON", "NEW_YORK")

    for session in sessions:
        for ordinal in (1, 2, 3):
            rows: list[PortfolioFlowTrade] = []
            prior_positive = 0
            prior_nonpositive = 0
            for accepted in groups.values():
                if len(accepted) < ordinal:
                    continue
                trade = accepted[ordinal - 1]
                trade_session = capitalizer_session_at(trade.entry_at)
                if trade_session is None or trade_session.value != session:
                    continue
                rows.append(trade)
                prior = _prior_realized(accepted[: ordinal - 1], trade)
                if prior > 0:
                    prior_positive += 1
                else:
                    prior_nonpositive += 1
            if not rows:
                continue
            row_tuple = tuple(rows)
            wins = sum(item.realized_r > 0 for item in row_tuple)
            losses = sum(item.realized_r < 0 for item in row_tuple)
            flats = len(row_tuple) - wins - losses
            cells.append(
                CapitalizerOrdinalEconomics(
                    policy=policy,
                    tie_policy=tie_policy,
                    session=session,
                    ordinal=ordinal,
                    trades=len(row_tuple),
                    wins=wins,
                    losses=losses,
                    flats=flats,
                    win_rate=str(Decimal(wins) / Decimal(len(row_tuple))),
                    prior_realized_positive=prior_positive,
                    prior_realized_nonpositive=prior_nonpositive,
                    metrics=_metrics(row_tuple),
                )
            )
    return tuple(cells)


def _build_report(
    trades: tuple[PortfolioFlowTrade, ...],
) -> CapitalizerSessionFlowEconomicsReport:
    if not trades:
        raise ValueError("session-flow economics requires trades")
    policies = (
        "UNCAPPED_RESEARCH",
        "MAX2",
        "MAX3_ANY_VALID",
        "MAX3_POSITIVE_REALIZED_CONTINUATION",
    )
    policy_rows: list[CapitalizerPolicyEconomics] = []
    ordinal_rows: list[CapitalizerOrdinalEconomics] = []
    for tie_policy in ("SYMBOL_ASC", "SYMBOL_DESC"):
        for policy in policies:
            policy_rows.append(
                _policy_economics(
                    trades,
                    policy=policy,
                    tie_policy=tie_policy,
                )
            )
            ordinal_rows.extend(
                _ordinal_economics(
                    trades,
                    policy=policy,
                    tie_policy=tie_policy,
                )
            )
    symbols = tuple(sorted({trade.symbol for trade in trades}))
    return CapitalizerSessionFlowEconomicsReport(
        identity=IDENTITY,
        symbol_count=len(symbols),
        symbols=symbols,
        baseline_opportunities=len(trades),
        policy_economics=tuple(policy_rows),
        ordinal_economics=tuple(ordinal_rows),
    )


def build_session_flow_economics_report(
    root: Path,
) -> CapitalizerSessionFlowEconomicsReport:
    return _build_report(_load_trade_ledgers(root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer session-flow economic diagnostics"
    )
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_session_flow_economics_report(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-session-flow-economics-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
