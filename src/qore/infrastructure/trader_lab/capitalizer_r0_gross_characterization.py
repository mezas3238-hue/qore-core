"""Conservative gross R0 economic characterization for QORE Capitalizer.

R0 is deliberately *not* an economic candidate. It asks one narrow question: if the frozen
CIBO-aligned departure hypothesis is executed at the earliest next-M5 open using only
decision-time structure, what gross R distribution does that geometry produce?

Frozen characterization mechanics:
- signal: directional Capitalizer M5 event + exact aligned H1 CAUSAL_CISD_V1 departure;
- entry proxy: next contiguous M5 open, same Capitalizer session;
- invalidation proxy: directional extreme of the source M5;
- destination: nearest Target V2 candidate that was causal/active at departure and is still
  ahead of the entry proxy;
- lifecycle: stop/target until the broad research session ends;
- same-M5 stop/target ambiguity: STOP_FIRST;
- unresolved at session end: mark-to-market at final same-session M5 close.

No spread/commission/slippage is applied here. No maximum-two portfolio selection is applied.
Those belong to later portfolio/execution layers after the geometry is characterized.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    BAR_DURATION,
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_alignment_forensics import (
    CapitalizerCiboEventKind,
    load_causal_journey_events,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_departure_hypothesis import HYPOTHESIS_ID
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerMicrostructureEvent,
    classify_microstructure_events,
    designated_session,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_target_context import (
    CapitalizerTargetContext,
    load_target_contexts,
)

IDENTITY = "QORE_CAPITALIZER_R0_GROSS_CHARACTERIZATION_V1"

_DIRECTIONAL_EVENTS: dict[CapitalizerMicrostructureEvent, CapitalizerSide] = {
    CapitalizerMicrostructureEvent.HIGH_RAID_REJECTION: CapitalizerSide.SHORT,
    CapitalizerMicrostructureEvent.LOW_RAID_REJECTION: CapitalizerSide.LONG,
    CapitalizerMicrostructureEvent.HIGH_ACCEPTANCE: CapitalizerSide.LONG,
    CapitalizerMicrostructureEvent.LOW_ACCEPTANCE: CapitalizerSide.SHORT,
}


@dataclass(frozen=True, slots=True)
class CapitalizerR0Trade:
    symbol: str
    side: CapitalizerSide
    signal_at: datetime
    entry_at: datetime
    exit_at: datetime
    event_labels: tuple[str, ...]
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    initial_risk_price: Decimal
    planned_reward_r: Decimal
    realized_gross_r: Decimal
    exit_reason: str
    bars_held: int
    same_bar_stop_target_ambiguity: bool

    def __post_init__(self) -> None:
        if self.entry_at < self.signal_at:
            raise ValueError("R0 entry cannot precede signal confirmation")
        if self.exit_at < self.entry_at:
            raise ValueError("R0 exit cannot predate entry")
        if self.initial_risk_price <= 0:
            raise ValueError("R0 initial risk must be positive")
        if self.planned_reward_r <= 0:
            raise ValueError("R0 planned reward must be positive")
        if self.bars_held <= 0:
            raise ValueError("R0 bars_held must be positive")
        if self.exit_reason not in {"STOP", "TARGET", "SESSION_EXIT"}:
            raise ValueError("unsupported R0 exit reason")


@dataclass(frozen=True, slots=True)
class CapitalizerR0Metrics:
    trades: int
    wins: int
    losses: int
    flats: int
    total_gross_r: str
    mean_gross_r: str
    gross_profit_r: str
    gross_loss_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    median_planned_reward_r: str
    median_bars_held: str
    stop_exits: int
    target_exits: int
    session_exits: int
    ambiguous_stop_first_exits: int


@dataclass(frozen=True, slots=True)
class CapitalizerR0Report:
    identity: str
    hypothesis_id: str
    symbol: str
    session: str
    metrics: CapitalizerR0Metrics
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    characterization_only: bool = True
    economic_candidate: bool = False
    execution_costs_applied: bool = False
    portfolio_session_budget_applied: bool = False
    final_stop_contract_defined: bool = False
    final_target_contract_defined: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False


def _target_index(
    contexts: tuple[CapitalizerTargetContext, ...],
) -> dict[tuple[str, CapitalizerSide, datetime], CapitalizerTargetContext]:
    index: dict[tuple[str, CapitalizerSide, datetime], CapitalizerTargetContext] = {}
    for context in contexts:
        key = (context.symbol, context.side, context.departure_at)
        if key in index:
            raise ValueError("duplicate R0 target context key")
        index[key] = context
    return index


def _nearest_target(
    *,
    context: CapitalizerTargetContext,
    side: CapitalizerSide,
    entry: Decimal,
) -> Decimal | None:
    if side is CapitalizerSide.LONG:
        prices = tuple(
            candidate.price
            for candidate in context.candidates
            if candidate.price > entry
        )
        return min(prices) if prices else None
    prices = tuple(candidate.price for candidate in context.candidates if candidate.price < entry)
    return max(prices) if prices else None


def _session_lifecycle(
    bars: tuple[CapitalizerM5Bar, ...],
    *,
    entry_index: int,
    side: CapitalizerSide,
    entry_price: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
) -> tuple[datetime, Decimal, str, int, bool]:
    session = capitalizer_session_at(bars[entry_index].opened_at)
    if session is None:
        raise ValueError("R0 entry must belong to Capitalizer research session")
    risk = abs(entry_price - stop_price)
    last_close = entry_price
    bars_held = 0

    for offset in range(entry_index, len(bars)):
        bar = bars[offset]
        if offset > entry_index:
            previous = bars[offset - 1]
            if bar.opened_at - previous.opened_at != BAR_DURATION:
                break
        if capitalizer_session_at(bar.opened_at) is not session:
            break
        bars_held += 1
        last_close = bar.close

        if side is CapitalizerSide.LONG:
            stop_hit = bar.low <= stop_price
            target_hit = bar.high >= target_price
        else:
            stop_hit = bar.high >= stop_price
            target_hit = bar.low <= target_price

        if stop_hit:
            return bar.closed_at, Decimal("-1"), "STOP", bars_held, target_hit
        if target_hit:
            reward = abs(target_price - entry_price)
            return bar.closed_at, reward / risk, "TARGET", bars_held, False

    final_bar = bars[entry_index + bars_held - 1]
    delta = (
        last_close - entry_price
        if side is CapitalizerSide.LONG
        else entry_price - last_close
    )
    return final_bar.closed_at, delta / risk, "SESSION_EXIT", bars_held, False


def build_r0_trades(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> tuple[CapitalizerR0Trade, ...]:
    bars = tuple(iter_atlas_m5(m5_root))
    if not bars:
        raise ValueError("R0 M5 artifact contained no bars")
    symbol = bars[0].symbol
    session = designated_session(symbol)

    departures = {
        (item.observed_at, item.side)
        for item in load_causal_journey_events(journey_root)
        if item.kind is CapitalizerCiboEventKind.DEPARTURE
        and item.timeframe == "H1"
    }
    contexts = _target_index(load_target_contexts(target_root))
    result: list[CapitalizerR0Trade] = []

    for source_index in range(1, len(bars) - 1):
        source = bars[source_index]
        previous = bars[source_index - 1]
        entry_bar = bars[source_index + 1]
        if source.opened_at - previous.opened_at != BAR_DURATION:
            continue
        if entry_bar.opened_at - source.opened_at != BAR_DURATION:
            continue
        if capitalizer_session_at(source.opened_at) is not session:
            continue
        if capitalizer_session_at(entry_bar.opened_at) is not session:
            continue

        directional = tuple(
            (event, _DIRECTIONAL_EVENTS[event])
            for event in classify_microstructure_events(source, previous)
            if event in _DIRECTIONAL_EVENTS
        )
        if not directional:
            continue
        sides = {side for _, side in directional}
        if len(sides) != 1:
            continue
        side = next(iter(sides))
        if (source.closed_at, side) not in departures:
            continue

        context = contexts.get((symbol, side, source.closed_at))
        if context is None:
            continue

        entry_price = entry_bar.open
        stop_price = source.low if side is CapitalizerSide.LONG else source.high
        if side is CapitalizerSide.LONG and entry_price <= stop_price:
            continue
        if side is CapitalizerSide.SHORT and entry_price >= stop_price:
            continue

        target_price = _nearest_target(context=context, side=side, entry=entry_price)
        if target_price is None:
            continue

        risk = abs(entry_price - stop_price)
        reward = abs(target_price - entry_price)
        if risk <= 0 or reward <= 0:
            continue
        exit_at, realized_r, reason, bars_held, ambiguous = _session_lifecycle(
            bars,
            entry_index=source_index + 1,
            side=side,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
        )
        result.append(
            CapitalizerR0Trade(
                symbol=symbol,
                side=side,
                signal_at=source.closed_at,
                entry_at=entry_bar.opened_at,
                exit_at=exit_at,
                event_labels=tuple(sorted(event.value for event, _ in directional)),
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                initial_risk_price=risk,
                planned_reward_r=reward / risk,
                realized_gross_r=realized_r,
                exit_reason=reason,
                bars_held=bars_held,
                same_bar_stop_target_ambiguity=ambiguous,
            )
        )
    return tuple(result)


def _metrics(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Metrics:
    if not trades:
        raise ValueError("R0 metrics require trades")
    returns = tuple(item.realized_gross_r for item in trades)
    wins = sum(value > 0 for value in returns)
    losses = sum(value < 0 for value in returns)
    flats = len(returns) - wins - losses
    total = sum(returns, Decimal("0"))
    gross_profit = sum((value for value in returns if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in returns if value < 0), Decimal("0"))
    pf = None if gross_loss == 0 else gross_profit / gross_loss

    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return CapitalizerR0Metrics(
        trades=len(trades),
        wins=wins,
        losses=losses,
        flats=flats,
        total_gross_r=str(total),
        mean_gross_r=str(total / Decimal(len(trades))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=None if pf is None else str(pf),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        median_planned_reward_r=str(median(item.planned_reward_r for item in trades)),
        median_bars_held=str(median(item.bars_held for item in trades)),
        stop_exits=sum(item.exit_reason == "STOP" for item in trades),
        target_exits=sum(item.exit_reason == "TARGET" for item in trades),
        session_exits=sum(item.exit_reason == "SESSION_EXIT" for item in trades),
        ambiguous_stop_first_exits=sum(
            item.same_bar_stop_target_ambiguity for item in trades
        ),
    )


def summarize_r0(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Report:
    if not trades:
        raise ValueError("R0 report requires trades")
    symbol = trades[0].symbol
    if any(item.symbol != symbol for item in trades):
        raise ValueError("R0 report requires one symbol")
    return CapitalizerR0Report(
        identity=IDENTITY,
        hypothesis_id=HYPOTHESIS_ID,
        symbol=symbol,
        session=designated_session(symbol).value,
        metrics=_metrics(trades),
    )


def write_r0_report(report: CapitalizerR0Report, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-r0-gross-characterization-v1.json"
    payload: dict[str, Any] = asdict(report)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer conservative R0 characterization")
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    trades = build_r0_trades(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    report = summarize_r0(trades)
    write_r0_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "trades": report.metrics.trades,
                "profit_factor": report.metrics.profit_factor,
                "total_gross_r": report.metrics.total_gross_r,
                "max_drawdown_r": report.metrics.max_drawdown_r,
                "max_losing_streak": report.metrics.max_losing_streak,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
