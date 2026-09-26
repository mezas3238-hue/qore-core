"""Deterministic diagnostic metrics for Capitalizer Behavior Lab episodes.

Metrics are descriptive research outputs, never promotion decisions. Profit factor is undefined
when there are no losing observations rather than represented by a fabricated infinity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_behavior_lab import (
    CapitalizerBehaviorEpisode,
    canonical_behavior_episodes,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession


@dataclass(frozen=True, slots=True)
class CapitalizerBehaviorMetrics:
    trades: int
    wins: int
    losses: int
    flats: int
    total_r: Decimal
    mean_r: Decimal
    gross_profit_r: Decimal
    gross_loss_r: Decimal
    profit_factor: Decimal | None
    max_drawdown_r: Decimal
    max_losing_streak: int

    def __post_init__(self) -> None:
        if self.trades < 0 or self.wins < 0 or self.losses < 0 or self.flats < 0:
            raise ValueError("metric counts must be non-negative")
        if self.wins + self.losses + self.flats != self.trades:
            raise ValueError("win/loss/flat counts must sum to trades")
        if self.max_drawdown_r < 0:
            raise ValueError("max_drawdown_r must be non-negative")
        if self.max_losing_streak < 0:
            raise ValueError("max_losing_streak must be non-negative")


@dataclass(frozen=True, slots=True)
class CapitalizerBehaviorSegment:
    session: CapitalizerSession
    symbol: str | None
    metrics: CapitalizerBehaviorMetrics


@dataclass(frozen=True, slots=True)
class CapitalizerBehaviorReport:
    """Portfolio + session + session-market diagnostic views from one chronology."""

    total: CapitalizerBehaviorMetrics
    by_session: tuple[CapitalizerBehaviorSegment, ...]
    by_session_market: tuple[CapitalizerBehaviorSegment, ...]


def compute_behavior_metrics(
    episodes: tuple[CapitalizerBehaviorEpisode, ...],
) -> CapitalizerBehaviorMetrics:
    ordered = canonical_behavior_episodes(episodes)
    returns = tuple(item.outcome.net_r for item in ordered)
    trades = len(returns)
    wins = sum(value > 0 for value in returns)
    losses = sum(value < 0 for value in returns)
    flats = trades - wins - losses
    total_r = sum(returns, Decimal("0"))
    mean_r = total_r / Decimal(trades) if trades else Decimal("0")
    gross_profit_r = sum((value for value in returns if value > 0), Decimal("0"))
    gross_loss_r = -sum((value for value in returns if value < 0), Decimal("0"))
    profit_factor = (
        gross_profit_r / gross_loss_r if gross_loss_r > 0 else None
    )

    equity = Decimal("0")
    peak = Decimal("0")
    max_drawdown = Decimal("0")
    current_losing_streak = 0
    max_losing_streak = 0
    for value in returns:
        equity += value
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        if value < 0:
            current_losing_streak += 1
            if current_losing_streak > max_losing_streak:
                max_losing_streak = current_losing_streak
        else:
            current_losing_streak = 0

    return CapitalizerBehaviorMetrics(
        trades=trades,
        wins=wins,
        losses=losses,
        flats=flats,
        total_r=total_r,
        mean_r=mean_r,
        gross_profit_r=gross_profit_r,
        gross_loss_r=gross_loss_r,
        profit_factor=profit_factor,
        max_drawdown_r=max_drawdown,
        max_losing_streak=max_losing_streak,
    )


def build_behavior_report(
    episodes: tuple[CapitalizerBehaviorEpisode, ...],
) -> CapitalizerBehaviorReport:
    ordered = canonical_behavior_episodes(episodes)

    by_session: list[CapitalizerBehaviorSegment] = []
    by_session_market: list[CapitalizerBehaviorSegment] = []
    for session in CapitalizerSession:
        session_episodes = tuple(
            item for item in ordered if item.snapshot.session is session
        )
        by_session.append(
            CapitalizerBehaviorSegment(
                session=session,
                symbol=None,
                metrics=compute_behavior_metrics(session_episodes),
            )
        )
        symbols = sorted({item.snapshot.symbol for item in session_episodes})
        for symbol in symbols:
            market_episodes = tuple(
                item
                for item in session_episodes
                if item.snapshot.symbol == symbol
            )
            by_session_market.append(
                CapitalizerBehaviorSegment(
                    session=session,
                    symbol=symbol,
                    metrics=compute_behavior_metrics(market_episodes),
                )
            )

    return CapitalizerBehaviorReport(
        total=compute_behavior_metrics(ordered),
        by_session=tuple(by_session),
        by_session_market=tuple(by_session_market),
    )
