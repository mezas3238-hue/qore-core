"""Development-only economic replay for the V49 High-Frequency Scalper.

PREDECLARED before opening V49 development outcomes:
- window: 2025-09-17 -> 2026-09-17;
- decision stack remains H1 -> M15 -> M1 only;
- deterministic trade intent already frozen by V49:
  entry = M1 trigger confirmation close,
  stop = M15 protected swing,
  target = causal H1 structural target witness;
- lifecycle begins after the confirmation-close entry;
- same later M1 bar touching stop and target is adjudicated STOP first (fail-closed);
- unresolved positions exit at the final completed M1 bar of the same Capitalizer session;
- portfolio admits chronological first 3 opportunities per session/day, independent of outcome;
- cost stress is explicit additive R, not a claim about broker-native historical costs.

This replay is DEVELOPMENT ONLY. It does not use or reopen the consumed V49 reserved holdout,
the protected Fresh Holdout, sizing, CIBO capital allocation, LIVE, VPS or production.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    V49TradeDirection,
    V49TradeIntent,
    materialize_trade_intent,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at

IDENTITY = "QORE_CAPITALIZER_V49_DEVELOPMENT_ECONOMIC_REPLAY"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V49_DEVELOPMENT_ECONOMIC_MATRIX"
COST_STRESS_R: tuple[Decimal, ...] = (
    Decimal("0"),
    Decimal("0.01"),
    Decimal("0.025"),
    Decimal("0.05"),
)


@dataclass(frozen=True, slots=True)
class V49EconomicTrade:
    symbol: str
    session: str
    operating_date: str
    ordinal_candidate_at: str
    direction: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    target_price: str
    planned_reward_r: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    trigger_family: str
    h1_state_basis: str
    same_bar_stop_target_ambiguity: bool = False
    outcome_used_for_selection: bool = False
    fresh_holdout_used: bool = False

    def __post_init__(self) -> None:
        if self.outcome_used_for_selection:
            raise ValueError("V49 economic trade selection cannot use outcomes")
        if self.fresh_holdout_used:
            raise ValueError("V49 development economics cannot use Fresh Holdout")


@dataclass(frozen=True, slots=True)
class V49Metrics:
    trades: int
    wins: int
    losses: int
    flats: int
    win_rate: str
    total_r: str
    expectancy_r: str
    gross_profit_r: str
    gross_loss_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    median_planned_reward_r: str
    median_m1_bars_held: str
    stop_exits: int
    target_exits: int
    session_exits: int
    ambiguous_stop_first_exits: int


@dataclass(frozen=True, slots=True)
class V49CostStressMetrics:
    cost_r_per_trade: str
    metrics: V49Metrics


@dataclass(frozen=True, slots=True)
class V49MarketEconomicReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    candidate_opportunities: int
    replayed_trades: int
    rejected_no_session_m1: int
    metrics: V49Metrics | None
    cost_stress: tuple[V49CostStressMetrics, ...]
    outcome_used_for_selection: bool = False
    fresh_holdout_used: bool = False
    daily_used: bool = False
    h4_used: bool = False
    development_only: bool = True
    trader_certified: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V49 economic report identity")
        if self.outcome_used_for_selection or self.fresh_holdout_used:
            raise ValueError("V49 development economics crossed epistemic boundary")
        if self.daily_used or self.h4_used:
            raise ValueError("V49 economics must remain H1/M15/M1 only")
        if not self.development_only or self.trader_certified or self.live_authorized:
            raise ValueError("V49 development report grants no certification/deployment")


def _metrics(
    trades: tuple[V49EconomicTrade, ...],
    *,
    cost_r: Decimal = Decimal("0"),
) -> V49Metrics:
    if not trades:
        raise ValueError("V49 metrics require trades")
    ordered = tuple(
        sorted(
            trades,
            key=lambda item: (
                datetime.fromisoformat(item.exit_at),
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )
    values = tuple(Decimal(item.realized_gross_r) - cost_r for item in ordered)
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
    total = sum(values, Decimal("0"))

    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    planned = tuple(Decimal(item.planned_reward_r) for item in trades)
    held = tuple(item.m1_bars_held for item in trades)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    flats = len(values) - wins - losses
    return V49Metrics(
        trades=len(values),
        wins=wins,
        losses=losses,
        flats=flats,
        win_rate=str(Decimal(wins) / Decimal(len(values))),
        total_r=str(total),
        expectancy_r=str(total / Decimal(len(values))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=None if gross_loss == 0 else str(gross_profit / gross_loss),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        median_planned_reward_r=str(median(planned)),
        median_m1_bars_held=str(median(held)),
        stop_exits=sum(item.exit_reason == "STOP" for item in trades),
        target_exits=sum(item.exit_reason == "TARGET" for item in trades),
        session_exits=sum(item.exit_reason == "SESSION_EXIT" for item in trades),
        ambiguous_stop_first_exits=sum(
            item.same_bar_stop_target_ambiguity for item in trades
        ),
    )


def _load_opportunities(root: Path) -> tuple[V49Opportunity, ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != 1:
        raise ValueError(
            f"market economic replay requires one opportunity ledger, got {len(paths)}"
        )
    rows: list[V49Opportunity] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(V49Opportunity(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                item.m1_trigger_confirmed_at,
                item.symbol,
                item.m1_trigger_family,
            ),
        )
    )


def _session_bars(
    all_bars: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
    *,
    intent: V49TradeIntent,
) -> tuple[CapitalizerM1Bar, ...]:
    index = bisect.bisect_left(opened, intent.entry_at)
    result: list[CapitalizerM1Bar] = []
    expected_session = CapitalizerSession(intent.session)
    for bar in all_bars[index:]:
        observed = capitalizer_session_at(bar.opened_at)
        if observed is not expected_session:
            if result:
                break
            continue
        result.append(bar)
    return tuple(result)


def _replay_one(
    bars: tuple[CapitalizerM1Bar, ...],
    intent: V49TradeIntent,
) -> V49EconomicTrade | None:
    if not bars:
        return None

    entry = intent.entry_price
    stop = intent.stop_price
    target = intent.target_price
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk <= 0 or reward <= 0:
        raise ValueError("V49 trade intent must have positive risk/reward")

    held = 0
    ambiguous = False
    for bar in bars:
        # Entry is at the prior trigger-confirmation close, so only bars opening at or
        # after entry_at can affect the post-entry lifecycle.
        if bar.opened_at < intent.entry_at:
            continue
        held += 1
        stop_hit = (
            bar.low <= stop
            if intent.direction is V49TradeDirection.LONG
            else bar.high >= stop
        )
        target_hit = (
            bar.high >= target
            if intent.direction is V49TradeDirection.LONG
            else bar.low <= target
        )
        if stop_hit:
            ambiguous = target_hit
            realized = Decimal("-1")
            exit_reason = "STOP"
            exit_at = bar.closed_at
            break
        if target_hit:
            realized = reward / risk
            exit_reason = "TARGET"
            exit_at = bar.closed_at
            break
    else:
        last = bars[-1]
        delta = (
            last.close - entry
            if intent.direction is V49TradeDirection.LONG
            else entry - last.close
        )
        realized = delta / risk
        exit_reason = "SESSION_EXIT"
        exit_at = last.closed_at

    return V49EconomicTrade(
        symbol=intent.symbol,
        session=intent.session,
        operating_date=intent.operating_date,
        ordinal_candidate_at=intent.entry_at.isoformat(),
        direction=intent.direction.value,
        entry_at=intent.entry_at.isoformat(),
        exit_at=exit_at.isoformat(),
        entry_price=str(entry),
        stop_price=str(stop),
        target_price=str(target),
        planned_reward_r=str(reward / risk),
        realized_gross_r=str(realized),
        exit_reason=exit_reason,
        m1_bars_held=held,
        trigger_family=intent.trigger_family,
        h1_state_basis=intent.h1_state_basis,
        same_bar_stop_target_ambiguity=ambiguous,
    )


def build_market_economics(
    *,
    capacity_root: Path,
    m1_root: Path,
) -> tuple[V49MarketEconomicReport, tuple[V49EconomicTrade, ...]]:
    opportunities = _load_opportunities(capacity_root)
    if not opportunities:
        raise ValueError("V49 economics requires source-complete opportunities")
    symbol = opportunities[0].symbol
    session = opportunities[0].session
    if any(item.symbol != symbol or item.session != session for item in opportunities):
        raise ValueError("one economic market replay must contain one symbol/session")

    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if DEV_WINDOW_START <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars:
        raise ValueError("V49 economics found no development M1")
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("V49 economics M1 symbol mismatch")
    opened = tuple(item.opened_at for item in bars)

    result: list[V49EconomicTrade] = []
    rejected = 0
    for opportunity in opportunities:
        intent = materialize_trade_intent(opportunity)
        session_window = _session_bars(bars, opened, intent=intent)
        trade = _replay_one(session_window, intent)
        if trade is None:
            rejected += 1
            continue
        result.append(trade)

    ordered = tuple(
        sorted(
            result,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )
    stress = tuple(
        V49CostStressMetrics(
            cost_r_per_trade=str(cost),
            metrics=_metrics(ordered, cost_r=cost),
        )
        for cost in COST_STRESS_R
    ) if ordered else ()
    return (
        V49MarketEconomicReport(
            identity=IDENTITY,
            symbol=symbol,
            session=session,
            window_start=DEV_WINDOW_START.isoformat(),
            window_end_exclusive=DEV_WINDOW_END.isoformat(),
            candidate_opportunities=len(opportunities),
            replayed_trades=len(ordered),
            rejected_no_session_m1=rejected,
            metrics=_metrics(ordered) if ordered else None,
            cost_stress=stress,
        ),
        ordered,
    )


def write_market(
    report: V49MarketEconomicReport,
    trades: tuple[V49EconomicTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-v49-development-economics"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _read_market_reports(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-development-economics.json"))
    if len(paths) != 9:
        raise ValueError(f"V49 economic matrix requires 9 reports, got {len(paths)}")
    return tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths)


def _read_trades(root: Path) -> tuple[V49EconomicTrade, ...]:
    rows: list[V49EconomicTrade] = []
    paths = sorted(root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"V49 economic matrix requires 9 trade ledgers, got {len(paths)}")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V49EconomicTrade(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _portfolio_select(
    trades: tuple[V49EconomicTrade, ...],
) -> tuple[tuple[int, V49EconomicTrade], ...]:
    grouped: dict[tuple[str, str], list[V49EconomicTrade]] = defaultdict(list)
    for trade in trades:
        grouped[(trade.session, trade.operating_date)].append(trade)

    selected: list[tuple[int, V49EconomicTrade]] = []
    for key in sorted(grouped):
        rows = sorted(
            grouped[key],
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
                item.trigger_family,
            ),
        )
        for ordinal, trade in enumerate(rows[:3], start=1):
            selected.append((ordinal, trade))
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item[1].entry_at),
                item[1].symbol,
            ),
        )
    )


def _cell_metrics(
    selected: tuple[tuple[int, V49EconomicTrade], ...],
    *,
    session: str | None = None,
    symbol: str | None = None,
    ordinal: int | None = None,
) -> V49Metrics | None:
    rows = tuple(
        trade
        for order, trade in selected
        if (session is None or trade.session == session)
        and (symbol is None or trade.symbol == symbol)
        and (ordinal is None or order == ordinal)
    )
    return _metrics(rows) if rows else None


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _read_market_reports(root)
    trades = _read_trades(root)
    selected = _portfolio_select(trades)
    selected_trades = tuple(item[1] for item in selected)

    by_session = {
        session: asdict(metrics)
        for session in ("ASIA", "LONDON", "NEW_YORK")
        if (metrics := _cell_metrics(selected, session=session)) is not None
    }
    symbols = sorted({trade.symbol for trade in selected_trades})
    by_market = {
        symbol: asdict(metrics)
        for symbol in symbols
        if (metrics := _cell_metrics(selected, symbol=symbol)) is not None
    }
    by_ordinal = {
        str(ordinal): asdict(metrics)
        for ordinal in (1, 2, 3)
        if (metrics := _cell_metrics(selected, ordinal=ordinal)) is not None
    }
    session_ordinal: dict[str, dict[str, Any]] = {}
    for session in ("ASIA", "LONDON", "NEW_YORK"):
        cells: dict[str, Any] = {}
        for ordinal in (1, 2, 3):
            metrics = _cell_metrics(selected, session=session, ordinal=ordinal)
            if metrics is not None:
                cells[str(ordinal)] = asdict(metrics)
        session_ordinal[session] = cells

    cost_stress = tuple(
        {
            "cost_r_per_trade": str(cost),
            "metrics": asdict(_metrics(selected_trades, cost_r=cost)),
        }
        for cost in COST_STRESS_R
    )

    return {
        "identity": MATRIX_IDENTITY,
        "window_start": DEV_WINDOW_START.isoformat(),
        "window_end_exclusive": DEV_WINDOW_END.isoformat(),
        "development_only": True,
        "reserved_holdout_reopened": False,
        "fresh_holdout_used": False,
        "decision_timeframes": ["H1", "M15", "M1"],
        "daily_used": False,
        "h4_used": False,
        "market_count": len(reports),
        "candidate_trades_before_max3": len(trades),
        "portfolio_max3_selected_trades": len(selected_trades),
        "portfolio_metrics": asdict(_metrics(selected_trades)),
        "cost_stress": cost_stress,
        "by_session": by_session,
        "by_market": by_market,
        "by_ordinal": by_ordinal,
        "by_session_ordinal": session_ordinal,
        "same_bar_stop_target_ambiguities": sum(
            trade.same_bar_stop_target_ambiguity for trade in selected_trades
        ),
        "outcome_aware_selection": False,
        "cibo_sizing_applied": False,
        "risk_allocator_applied": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-v49-development-economic-matrix.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("capacity_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        market_report, trades = build_market_economics(
            capacity_root=args.capacity_root,
            m1_root=args.m1_root,
        )
        write_market(market_report, trades, args.output)
        print(json.dumps(asdict(market_report), sort_keys=True))
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
