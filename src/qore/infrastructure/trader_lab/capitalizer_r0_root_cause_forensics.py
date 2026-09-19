"""Causal root-cause forensics for QORE Capitalizer R0 acceptance losses.

This diagnostic reuses existing CORE evidence rather than inventing a new market lab:
- R0 gross characterization supplies the already-consumed trade labels;
- RAW M5 supplies only bars known at/before the decision;
- CIBO Market Journey supplies exact H1 departure episode identity; and
- PRE_DEPARTURE_SEQUENCE_LEDGER supplies causal raid/reclaim/departure chronology.

The central diagnostic distinction is structural, not threshold-optimized:
- RECLAIM_ALL / RECLAIM_MIXED / NO_RECLAIM are derived from all exact H1 departure
  episodes aligned to the R0 decision instant;
- FRESH / REPEAT asks whether the immediately preceding contiguous M5 bar had already
  confirmed the same directional acceptance before the current signal.

Outcome is used strictly as the label for aggregate forensics. No state becomes a trading
filter, candidate rule, execution permission, or fresh-holdout claim in this module.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    BAR_DURATION,
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_alignment_forensics import (
    CapitalizerCiboEventKind,
    load_causal_journey_events,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerMicrostructureEvent,
    classify_microstructure_events,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
    build_r0_trades,
)

IDENTITY = "QORE_CAPITALIZER_R0_ROOT_CAUSE_FORENSICS_V1"
_PRE_SEQUENCE_SCHEMA = "qore.cibo_market_atlas.pre_departure_sequence.v1"
_PRE_SEQUENCE_IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
_NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class CapitalizerAcceptanceRootCauseRow:
    state: str
    observations: int
    wins: int
    losses: int
    flats: int
    total_gross_r: str
    mean_gross_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    loss_rate: str


@dataclass(frozen=True, slots=True)
class CapitalizerAcceptanceRootCauseAnnual:
    year: int
    state: str
    observations: int
    total_gross_r: str
    mean_gross_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int


@dataclass(frozen=True, slots=True)
class CapitalizerR0RootCauseReport:
    identity: str
    symbol: str
    acceptance_trades: int
    by_state: tuple[CapitalizerAcceptanceRootCauseRow, ...]
    annual: tuple[CapitalizerAcceptanceRootCauseAnnual, ...]
    worst_streak_length: int
    worst_streak_total_gross_r: str
    worst_streak_state_counts: dict[str, int]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    diagnostic_only: bool = True
    causal_features_only: bool = True
    outcome_used_as_label_only: bool = True
    threshold_optimization_used: bool = False
    filter_selected: bool = False
    candidate_revision_defined: bool = False
    execution_costs_applied: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False


def _metrics(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    state: str,
) -> CapitalizerAcceptanceRootCauseRow:
    if not trades:
        raise ValueError("root-cause metrics require trades")
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

    return CapitalizerAcceptanceRootCauseRow(
        state=state,
        observations=len(trades),
        wins=wins,
        losses=losses,
        flats=flats,
        total_gross_r=str(total),
        mean_gross_r=str(total / Decimal(len(trades))),
        profit_factor=None if pf is None else str(pf),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        loss_rate=str(Decimal(losses) / Decimal(len(trades))),
    )


def _annual(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    year: int,
    state: str,
) -> CapitalizerAcceptanceRootCauseAnnual:
    row = _metrics(trades, state=state)
    return CapitalizerAcceptanceRootCauseAnnual(
        year=year,
        state=state,
        observations=row.observations,
        total_gross_r=row.total_gross_r,
        mean_gross_r=row.mean_gross_r,
        profit_factor=row.profit_factor,
        max_drawdown_r=row.max_drawdown_r,
        max_losing_streak=row.max_losing_streak,
    )


def _is_acceptance(trade: CapitalizerR0Trade) -> bool:
    return any("ACCEPTANCE" in label for label in trade.event_labels)


def _same_side_acceptance(side: CapitalizerSide) -> CapitalizerMicrostructureEvent:
    if side is CapitalizerSide.LONG:
        return CapitalizerMicrostructureEvent.HIGH_ACCEPTANCE
    return CapitalizerMicrostructureEvent.LOW_ACCEPTANCE


def _bars_by_close(
    bars: tuple[CapitalizerM5Bar, ...],
) -> dict[str, int]:
    return {bar.closed_at.isoformat(): index for index, bar in enumerate(bars)}


def _departure_episode_index(
    journey_root: Path,
) -> dict[tuple[str, CapitalizerSide], tuple[str, ...]]:
    grouped: dict[tuple[str, CapitalizerSide], set[str]] = defaultdict(set)
    for event in load_causal_journey_events(journey_root):
        if (
            event.kind is CapitalizerCiboEventKind.DEPARTURE
            and event.timeframe == "H1"
        ):
            grouped[(event.observed_at.isoformat(), event.side)].add(event.episode_id)
    return {
        key: tuple(sorted(episode_ids))
        for key, episode_ids in grouped.items()
    }


def _pre_departure_sequences(
    journey_root: Path,
) -> dict[str, tuple[tuple[str, datetime], ...]]:
    path = journey_root / "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl"
    if not path.exists():
        raise ValueError("PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl not found")

    result: dict[str, tuple[tuple[str, datetime], ...]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("pre-departure sequence row must be an object")
            if (
                raw.get("identity") != _PRE_SEQUENCE_IDENTITY
                or raw.get("schema") != _PRE_SEQUENCE_SCHEMA
            ):
                raise ValueError("unexpected pre-departure sequence identity/schema")
            if raw.get("causal_feature") is not True or raw.get("outcome_only") is not False:
                raise ValueError("pre-departure sequence must remain causal/non-outcome")
            episode_id = str(raw.get("episode_id"))
            sequence_raw = raw.get("sequence")
            if not isinstance(sequence_raw, list):
                raise ValueError("pre-departure sequence must be a list")
            sequence: list[tuple[str, datetime]] = []
            for item in sequence_raw:
                if not isinstance(item, dict):
                    raise ValueError("pre-departure sequence item must be an object")
                state = str(item.get("state"))
                raw_timestamp = item.get("timestamp")
                if not isinstance(raw_timestamp, str):
                    raise ValueError("pre-departure timestamp must be ISO string")
                timestamp = datetime.fromisoformat(raw_timestamp)
                if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                    raise ValueError("pre-departure timestamp must be timezone-aware")
                sequence.append((state, timestamp))
            if episode_id in result:
                raise ValueError("duplicate pre-departure sequence episode")
            result[episode_id] = tuple(sequence)
    return result


def _reclaim_tag(
    *,
    trade: CapitalizerR0Trade,
    episode_index: dict[tuple[str, CapitalizerSide], tuple[str, ...]],
    sequences: dict[str, tuple[tuple[str, datetime], ...]],
) -> str:
    episode_ids = episode_index.get((trade.signal_at.isoformat(), trade.side))
    if not episode_ids:
        raise ValueError("acceptance trade must map to exact H1 departure episode")

    reclaim_states: list[bool] = []
    for episode_id in episode_ids:
        sequence = sequences.get(episode_id)
        if sequence is None:
            raise ValueError("acceptance trade departure episode requires causal sequence")
        for _, observed_at in sequence:
            if observed_at > trade.signal_at:
                raise ValueError("future journey state cannot enter root-cause cognition")
        reclaim_states.append(any(state == "RECLAIM" for state, _ in sequence))

    if all(reclaim_states):
        return "RECLAIM_ALL"
    if any(reclaim_states):
        return "RECLAIM_MIXED"
    return "NO_RECLAIM"


def _acceptance_state(
    *,
    trade: CapitalizerR0Trade,
    bars: tuple[CapitalizerM5Bar, ...],
    by_close: dict[str, int],
    episode_index: dict[tuple[str, CapitalizerSide], tuple[str, ...]],
    sequences: dict[str, tuple[tuple[str, datetime], ...]],
) -> str:
    source_index = by_close.get(trade.signal_at.isoformat())
    if source_index is None or source_index < 2:
        raise ValueError("acceptance signal must map to at least three causal M5 bars")
    source = bars[source_index]
    previous = bars[source_index - 1]
    previous_previous = bars[source_index - 2]
    if source.opened_at - previous.opened_at != BAR_DURATION:
        raise ValueError("acceptance source/previous M5 must be contiguous")
    if previous.opened_at - previous_previous.opened_at != BAR_DURATION:
        raise ValueError("acceptance previous M5 context must be contiguous")

    previous_events = classify_microstructure_events(previous, previous_previous)
    repeated = _same_side_acceptance(trade.side) in previous_events
    reclaim_tag = _reclaim_tag(
        trade=trade,
        episode_index=episode_index,
        sequences=sequences,
    )
    freshness_tag = "REPEAT" if repeated else "FRESH"
    return f"{reclaim_tag}_{freshness_tag}"


def _loss_streaks(
    trades: tuple[CapitalizerR0Trade, ...],
) -> tuple[tuple[CapitalizerR0Trade, ...], ...]:
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
    return tuple(
        sorted(
            episodes,
            key=lambda group: (
                len(group),
                -sum((item.realized_gross_r for item in group), Decimal("0")),
            ),
            reverse=True,
        )
    )


def summarize_root_cause(
    *,
    m5_root: Path,
    journey_root: Path,
    trades: tuple[CapitalizerR0Trade, ...],
) -> CapitalizerR0RootCauseReport:
    if not trades:
        raise ValueError("root-cause forensics require R0 trades")
    canonical = tuple(sorted(trades, key=lambda item: (item.entry_at, item.exit_at)))
    symbol = canonical[0].symbol
    if any(item.symbol != symbol for item in canonical):
        raise ValueError("root-cause forensics require one symbol")

    bars = tuple(iter_atlas_m5(m5_root))
    by_close = _bars_by_close(bars)
    episode_index = _departure_episode_index(journey_root)
    sequences = _pre_departure_sequences(journey_root)

    acceptance = tuple(item for item in canonical if _is_acceptance(item))
    if not acceptance:
        raise ValueError("root-cause forensics require acceptance trades")

    state_by_trade: dict[tuple[str, str], str] = {}
    grouped: dict[str, list[CapitalizerR0Trade]] = defaultdict(list)
    annual_grouped: dict[tuple[int, str], list[CapitalizerR0Trade]] = defaultdict(list)
    for trade in acceptance:
        state = _acceptance_state(
            trade=trade,
            bars=bars,
            by_close=by_close,
            episode_index=episode_index,
            sequences=sequences,
        )
        key = (trade.signal_at.isoformat(), trade.side.value)
        state_by_trade[key] = state
        grouped[state].append(trade)
        year = trade.entry_at.astimezone(_NEW_YORK).year
        annual_grouped[(year, state)].append(trade)

    rows = tuple(
        _metrics(tuple(grouped[state]), state=state)
        for state in sorted(grouped)
    )
    annual = tuple(
        _annual(tuple(raw), year=year, state=state)
        for (year, state), raw in sorted(annual_grouped.items())
    )

    streaks = _loss_streaks(canonical)
    if not streaks:
        raise ValueError("root-cause forensics require at least one loss streak")
    worst = streaks[0]
    worst_counts: Counter[str] = Counter()
    for trade in worst:
        if not _is_acceptance(trade):
            worst_counts["REJECTION_ONLY"] += 1
            continue
        key = (trade.signal_at.isoformat(), trade.side.value)
        worst_counts[state_by_trade[key]] += 1

    return CapitalizerR0RootCauseReport(
        identity=IDENTITY,
        symbol=symbol,
        acceptance_trades=len(acceptance),
        by_state=rows,
        annual=annual,
        worst_streak_length=len(worst),
        worst_streak_total_gross_r=str(
            sum((item.realized_gross_r for item in worst), Decimal("0"))
        ),
        worst_streak_state_counts=dict(sorted(worst_counts.items())),
    )


def write_root_cause_report(
    report: CapitalizerR0RootCauseReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-r0-root-cause-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Capitalizer R0 causal root-cause forensics")
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
    report = summarize_root_cause(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        trades=trades,
    )
    write_root_cause_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "acceptance_trades": report.acceptance_trades,
                "states": {row.state: row.observations for row in report.by_state},
                "worst_streak_length": report.worst_streak_length,
                "worst_streak_state_counts": report.worst_streak_state_counts,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
