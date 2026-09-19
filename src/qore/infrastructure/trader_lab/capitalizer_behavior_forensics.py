"""Density and loss-cluster forensics for Capitalizer Behavior Lab.

These diagnostics answer whether opportunity density is naturally distributed across sessions
and whether losing streaks are repetitions of the same causal failure. They do not authorize
rule selection or promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_behavior_lab import (
    CapitalizerBehaviorEpisode,
    canonical_behavior_episodes,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    MAX_EXECUTIONS_PER_SESSION,
)


@dataclass(frozen=True, slots=True)
class CapitalizerSessionDensityDiagnostic:
    session: CapitalizerSession
    session_days: int
    trades: int
    average_trades_per_session_day: Decimal
    max_trades_in_one_session_day: int
    ceiling_violations: int


@dataclass(frozen=True, slots=True)
class CapitalizerLossCauseDiagnostic:
    tag: str
    losing_trades: int
    appearances_in_losing_streaks: int


@dataclass(frozen=True, slots=True)
class CapitalizerBehaviorForensicsReport:
    calendar_days: int
    trade_days: int
    total_trades: int
    average_trades_per_trade_day: Decimal
    max_trades_in_one_day: int
    session_density: tuple[CapitalizerSessionDensityDiagnostic, ...]
    loss_causes: tuple[CapitalizerLossCauseDiagnostic, ...]
    repeated_same_cause_streaks: int


def _date_key(episode: CapitalizerBehaviorEpisode) -> str:
    return episode.snapshot.decision_at.date().isoformat()


def _session_day_key(episode: CapitalizerBehaviorEpisode) -> tuple[str, CapitalizerSession]:
    return (_date_key(episode), episode.snapshot.session)


def build_behavior_forensics(
    episodes: tuple[CapitalizerBehaviorEpisode, ...],
) -> CapitalizerBehaviorForensicsReport:
    ordered = canonical_behavior_episodes(episodes)
    if not ordered:
        return CapitalizerBehaviorForensicsReport(
            calendar_days=0,
            trade_days=0,
            total_trades=0,
            average_trades_per_trade_day=Decimal("0"),
            max_trades_in_one_day=0,
            session_density=tuple(
                CapitalizerSessionDensityDiagnostic(
                    session=session,
                    session_days=0,
                    trades=0,
                    average_trades_per_session_day=Decimal("0"),
                    max_trades_in_one_session_day=0,
                    ceiling_violations=0,
                )
                for session in CapitalizerSession
            ),
            loss_causes=(),
            repeated_same_cause_streaks=0,
        )

    all_dates = sorted({_date_key(item) for item in ordered})
    per_day: dict[str, int] = {}
    per_session_day: dict[tuple[str, CapitalizerSession], int] = {}
    for episode in ordered:
        date = _date_key(episode)
        key = _session_day_key(episode)
        per_day[date] = per_day.get(date, 0) + 1
        per_session_day[key] = per_session_day.get(key, 0) + 1

    session_density: list[CapitalizerSessionDensityDiagnostic] = []
    for session in CapitalizerSession:
        counts = tuple(
            count
            for (date, observed_session), count in per_session_day.items()
            if observed_session is session and date in all_dates
        )
        trades = sum(counts)
        session_days = len(counts)
        average = (
            Decimal(trades) / Decimal(session_days)
            if session_days
            else Decimal("0")
        )
        session_density.append(
            CapitalizerSessionDensityDiagnostic(
                session=session,
                session_days=session_days,
                trades=trades,
                average_trades_per_session_day=average,
                max_trades_in_one_session_day=max(counts, default=0),
                ceiling_violations=sum(
                    count > MAX_EXECUTIONS_PER_SESSION for count in counts
                ),
            )
        )

    tag_counts: dict[str, int] = {}
    tag_streak_counts: dict[str, int] = {}
    repeated_same_cause_streaks = 0
    active_intersection: frozenset[str] | None = None
    active_length = 0

    for episode in ordered:
        tags = frozenset(episode.outcome.loss_cause_tags)
        if episode.outcome.net_r < 0:
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            if active_length == 0:
                active_intersection = tags
                active_length = 1
            else:
                active_length += 1
                active_intersection = (
                    tags
                    if active_intersection is None
                    else active_intersection & tags
                )

            if active_length >= 2 and active_intersection:
                repeated_same_cause_streaks += 1
                for tag in active_intersection:
                    tag_streak_counts[tag] = tag_streak_counts.get(tag, 0) + 1
        else:
            active_intersection = None
            active_length = 0

    loss_causes = tuple(
        CapitalizerLossCauseDiagnostic(
            tag=tag,
            losing_trades=count,
            appearances_in_losing_streaks=tag_streak_counts.get(tag, 0),
        )
        for tag, count in sorted(tag_counts.items())
    )

    trade_days = len(per_day)
    return CapitalizerBehaviorForensicsReport(
        calendar_days=len(all_dates),
        trade_days=trade_days,
        total_trades=len(ordered),
        average_trades_per_trade_day=(
            Decimal(len(ordered)) / Decimal(trade_days)
            if trade_days
            else Decimal("0")
        ),
        max_trades_in_one_day=max(per_day.values(), default=0),
        session_density=tuple(session_density),
        loss_causes=loss_causes,
        repeated_same_cause_streaks=repeated_same_cause_streaks,
    )
