"""R0 loss-cluster and stability forensics for QORE Capitalizer.

This module decomposes the already-consumed R0 characterization. It is diagnostic only:
no slice becomes a trading filter, no market/hour/event is promoted or rejected, and no
fresh-holdout claim is created from these observations.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
    build_r0_trades,
)

IDENTITY = "QORE_CAPITALIZER_R0_LOSS_FORENSICS_V1"
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class CapitalizerR0SliceMetrics:
    dimension: str
    key: str
    trades: int
    wins: int
    losses: int
    flats: int
    total_gross_r: str
    mean_gross_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    median_planned_reward_r: str


@dataclass(frozen=True, slots=True)
class CapitalizerR0LossStreak:
    rank: int
    length: int
    start_at: str
    end_at: str
    total_gross_r: str
    dominant_side: str
    dominant_event_signature: str
    dominant_ny_hour: int


@dataclass(frozen=True, slots=True)
class CapitalizerR0ForensicsReport:
    identity: str
    symbol: str
    session: str
    overall: CapitalizerR0SliceMetrics
    by_year: tuple[CapitalizerR0SliceMetrics, ...]
    by_side: tuple[CapitalizerR0SliceMetrics, ...]
    by_event_signature: tuple[CapitalizerR0SliceMetrics, ...]
    by_ny_hour: tuple[CapitalizerR0SliceMetrics, ...]
    longest_loss_streaks: tuple[CapitalizerR0LossStreak, ...]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    diagnostic_only: bool = True
    filter_selected: bool = False
    candidate_revision_defined: bool = False
    execution_costs_applied: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False


def _metrics(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    dimension: str,
    key: str,
) -> CapitalizerR0SliceMetrics:
    if not trades:
        raise ValueError("R0 forensic slice requires trades")
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

    return CapitalizerR0SliceMetrics(
        dimension=dimension,
        key=key,
        trades=len(trades),
        wins=wins,
        losses=losses,
        flats=flats,
        total_gross_r=str(total),
        mean_gross_r=str(total / Decimal(len(trades))),
        profit_factor=None if pf is None else str(pf),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        median_planned_reward_r=str(median(item.planned_reward_r for item in trades)),
    )


def _event_signature(trade: CapitalizerR0Trade) -> str:
    return "+".join(trade.event_labels)


def _group(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    dimension: str,
    key_fn,
) -> tuple[CapitalizerR0SliceMetrics, ...]:
    grouped: dict[str, list[CapitalizerR0Trade]] = defaultdict(list)
    for trade in trades:
        grouped[str(key_fn(trade))].append(trade)
    return tuple(
        _metrics(tuple(grouped[key]), dimension=dimension, key=key)
        for key in sorted(grouped)
    )


def _loss_streaks(
    trades: tuple[CapitalizerR0Trade, ...],
) -> tuple[CapitalizerR0LossStreak, ...]:
    episodes: list[tuple[CapitalizerR0Trade, ...]] = []
    active: list[CapitalizerR0Trade] = []
    for trade in trades:
        if trade.realized_gross_r < 0:
            active.append(trade)
            continue
        if active:
            episodes.append(tuple(active))
            active = []
    if active:
        episodes.append(tuple(active))

    ordered = sorted(
        episodes,
        key=lambda group: (
            len(group),
            -sum((item.realized_gross_r for item in group), Decimal("0")),
        ),
        reverse=True,
    )[:10]

    result: list[CapitalizerR0LossStreak] = []
    for rank, group in enumerate(ordered, start=1):
        side = Counter(item.side.value for item in group).most_common(1)[0][0]
        event = Counter(_event_signature(item) for item in group).most_common(1)[0][0]
        hour = Counter(
            item.entry_at.astimezone(NEW_YORK).hour for item in group
        ).most_common(1)[0][0]
        result.append(
            CapitalizerR0LossStreak(
                rank=rank,
                length=len(group),
                start_at=group[0].entry_at.isoformat(),
                end_at=group[-1].exit_at.isoformat(),
                total_gross_r=str(
                    sum((item.realized_gross_r for item in group), Decimal("0"))
                ),
                dominant_side=side,
                dominant_event_signature=event,
                dominant_ny_hour=hour,
            )
        )
    return tuple(result)


def summarize_r0_forensics(
    trades: tuple[CapitalizerR0Trade, ...],
) -> CapitalizerR0ForensicsReport:
    if not trades:
        raise ValueError("R0 forensics require trades")
    canonical = tuple(sorted(trades, key=lambda item: (item.entry_at, item.exit_at)))
    symbol = canonical[0].symbol
    if any(item.symbol != symbol for item in canonical):
        raise ValueError("R0 forensics require one symbol")

    return CapitalizerR0ForensicsReport(
        identity=IDENTITY,
        symbol=symbol,
        session=(
            "ASIA"
            if symbol in {"USDJPY", "AUDJPY", "AUDUSD", "GBPJPY"}
            else "LONDON"
            if symbol in {"EURUSD", "GBPUSD"}
            else "NEW_YORK"
        ),
        overall=_metrics(canonical, dimension="OVERALL", key="ALL"),
        by_year=_group(
            canonical,
            dimension="YEAR",
            key_fn=lambda item: item.entry_at.astimezone(NEW_YORK).year,
        ),
        by_side=_group(
            canonical,
            dimension="SIDE",
            key_fn=lambda item: item.side.value,
        ),
        by_event_signature=_group(
            canonical,
            dimension="EVENT_SIGNATURE",
            key_fn=_event_signature,
        ),
        by_ny_hour=_group(
            canonical,
            dimension="NY_HOUR",
            key_fn=lambda item: f"{item.entry_at.astimezone(NEW_YORK).hour:02d}",
        ),
        longest_loss_streaks=_loss_streaks(canonical),
    )


def write_r0_forensics(
    report: CapitalizerR0ForensicsReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-r0-loss-forensics-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer R0 loss-cluster forensics")
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
    report = summarize_r0_forensics(trades)
    write_r0_forensics(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "trades": report.overall.trades,
                "profit_factor": report.overall.profit_factor,
                "max_drawdown_r": report.overall.max_drawdown_r,
                "max_losing_streak": report.overall.max_losing_streak,
                "worst_streak": (
                    None
                    if not report.longest_loss_streaks
                    else asdict(report.longest_loss_streaks[0])
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
