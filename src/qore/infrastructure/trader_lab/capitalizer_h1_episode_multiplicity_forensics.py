"""H1 episode-multiplicity forensics for QORE Capitalizer residual drawdown.

This diagnostic starts from the strongest consumed-development baseline currently observed:
- Structural V2 entry cognition;
- block NO_RECLAIM_FRESH when any exact H1 departure episode has CISD latency crossing the
  natural H1 duration;
- apply causal PROFITABLE_SWING_LOCK position intelligence.

It then asks whether exact H1 departure multiplicity is explanatory. Multiple simultaneously
aligned H1 episodes normally represent distinct source boundaries. The count is categorical
and fully causal at decision time; no numeric optimization threshold is introduced.

The module is research-only. It does not freeze or promote a candidate, apply costs, claim
fresh holdout evidence, or authorize execution.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import iter_atlas_m5
from qore.infrastructure.trader_lab.capitalizer_cognitive_v2_development import (
    _root_state_index,
    select_development_trades,
)
from qore.infrastructure.trader_lab.capitalizer_departure_timing_forensics import (
    _load_timing_rows,
    _timing_state,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_position_lifecycle_forensics import (
    CapitalizerLifecycleMode,
    _bar_indices,
    _simulate_trade,
    _state_family,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    build_r0_trades,
    summarize_r0,
)
from qore.infrastructure.trader_lab.capitalizer_r0_root_cause_forensics import (
    _departure_episode_index,
)

IDENTITY = "QORE_CAPITALIZER_H1_EPISODE_MULTIPLICITY_FORENSICS_V1"
_JOURNEY_IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
_JOURNEY_SCHEMA = "qore.cibo_market_atlas.market_journey.v1"


@dataclass(frozen=True, slots=True)
class CapitalizerH1MultiplicityCell:
    state_family: str
    episode_multiplicity: str
    source_boundary_multiplicity: str
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerH1MultiplicityAblation:
    name: str
    excluded_trades: int
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerH1MultiplicityDrawdown:
    peak_trade_entry_at: str
    trough_trade_entry_at: str
    drawdown_r: str
    trades_in_episode: int
    losing_trades: int
    state_family_counts: dict[str, int]
    episode_multiplicity_counts: dict[str, int]
    boundary_multiplicity_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class CapitalizerH1MultiplicityReport:
    identity: str
    symbol: str
    baseline_metrics: CapitalizerR0Metrics
    cells: tuple[CapitalizerH1MultiplicityCell, ...]
    ablations: tuple[CapitalizerH1MultiplicityAblation, ...]
    worst_drawdown: CapitalizerH1MultiplicityDrawdown
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    development_only: bool = True
    categorical_causal_feature_only: bool = True
    numeric_threshold_optimization_used: bool = False
    costs_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _journey_boundaries(
    journey_root: Path,
) -> dict[str, tuple[str, datetime]]:
    path = journey_root / "MARKET_JOURNEY_LEDGER.jsonl"
    if not path.exists():
        raise ValueError("MARKET_JOURNEY_LEDGER.jsonl not found")
    result: dict[str, tuple[str, datetime]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row: Any = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("Market Journey row must be an object")
            if (
                row.get("identity") != _JOURNEY_IDENTITY
                or row.get("schema") != _JOURNEY_SCHEMA
            ):
                raise ValueError("unexpected Market Journey identity/schema")
            if row.get("causal_feature") is not True or row.get("outcome_only") is not False:
                raise ValueError("Market Journey row must be causal/non-outcome")
            if row.get("source_timeframe") != "H1" or row.get("departure_at") is None:
                continue
            episode_id = str(row.get("episode_id"))
            boundary = str(row.get("source_boundary"))
            raw_created = row.get("source_boundary_created_at")
            if not isinstance(raw_created, str):
                raise ValueError("source boundary creation timestamp must be ISO string")
            created_at = datetime.fromisoformat(raw_created)
            if created_at.tzinfo is None or created_at.utcoffset() is None:
                raise ValueError("source boundary creation timestamp must be aware")
            if episode_id in result:
                raise ValueError("duplicate H1 Journey episode")
            result[episode_id] = (boundary, created_at)
    return result


def _multiplicity_tags(
    trade: CapitalizerR0Trade,
    *,
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    boundaries: Mapping[str, tuple[str, datetime]],
) -> tuple[str, str]:
    episodes = episode_index.get((trade.signal_at.isoformat(), trade.side))
    if not episodes:
        raise ValueError("baseline trade must map to exact H1 departure episodes")
    episode_tag = "SINGLE_EPISODE" if len(episodes) == 1 else "MULTI_EPISODE"
    distinct_boundaries: set[tuple[str, datetime]] = set()
    for episode_id in episodes:
        boundary = boundaries.get(episode_id)
        if boundary is None:
            raise ValueError("exact H1 departure episode requires source boundary")
        distinct_boundaries.add(boundary)
    boundary_tag = (
        "SINGLE_SOURCE_BOUNDARY"
        if len(distinct_boundaries) == 1
        else "MULTI_SOURCE_BOUNDARY"
    )
    return episode_tag, boundary_tag


def _baseline(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> tuple[
    tuple[CapitalizerR0Trade, ...],
    dict[tuple[str, CapitalizerSide], str],
    dict[tuple[str, CapitalizerSide], tuple[str, ...]],
]:
    all_trades = build_r0_trades(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    if not all_trades:
        raise ValueError("H1 multiplicity forensics require R0 trades")
    state_index = _root_state_index(
        m5_root=m5_root,
        journey_root=journey_root,
        trades=all_trades,
    )
    structural, _, _, _ = select_development_trades(
        trades=all_trades,
        state_index=state_index,
        block_late_acceptance_repeat=True,
        block_journey_conflict=True,
        apply_session_ceiling=False,
    )
    episode_index = _departure_episode_index(journey_root)
    timing = _load_timing_rows(journey_root)
    timing_filtered = tuple(
        trade
        for trade in structural
        if not (
            _state_family(trade, state_index) == "NO_RECLAIM_FRESH"
            and _timing_state(
                trade,
                dimension="cisd",
                episode_index=episode_index,
                timing=timing,
            )
            == "ANY_CROSS_H1"
        )
    )
    bars = tuple(iter_atlas_m5(m5_root))
    by_open, _ = _bar_indices(bars)
    protected = tuple(
        _simulate_trade(
            trade,
            bars=bars,
            by_open=by_open,
            mode=CapitalizerLifecycleMode.PROFITABLE_SWING_LOCK,
        )
        for trade in timing_filtered
    )
    return protected, state_index, episode_index


def _metrics(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Metrics:
    if not trades:
        raise ValueError("H1 multiplicity metric group cannot be empty")
    return summarize_r0(trades).metrics


def _worst_drawdown(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    state_index: dict[tuple[str, CapitalizerSide], str],
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    boundaries: Mapping[str, tuple[str, datetime]],
) -> CapitalizerH1MultiplicityDrawdown:
    ordered = tuple(sorted(trades, key=lambda item: (item.entry_at, item.exit_at)))
    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = 0
    worst = Decimal("0")
    worst_peak_index = 0
    worst_trough_index = 0
    for index, trade in enumerate(ordered):
        equity += trade.realized_gross_r
        if equity > peak:
            peak = equity
            peak_index = index + 1
        drawdown = peak - equity
        if drawdown > worst:
            worst = drawdown
            worst_peak_index = peak_index
            worst_trough_index = index

    start = max(0, min(worst_peak_index, len(ordered) - 1))
    episode = ordered[start : worst_trough_index + 1]
    if not episode:
        episode = (ordered[worst_trough_index],)

    state_counts: Counter[str] = Counter()
    episode_counts: Counter[str] = Counter()
    boundary_counts: Counter[str] = Counter()
    for trade in episode:
        state_counts[_state_family(trade, state_index)] += 1
        episode_tag, boundary_tag = _multiplicity_tags(
            trade,
            episode_index=episode_index,
            boundaries=boundaries,
        )
        episode_counts[episode_tag] += 1
        boundary_counts[boundary_tag] += 1

    return CapitalizerH1MultiplicityDrawdown(
        peak_trade_entry_at=episode[0].entry_at.isoformat(),
        trough_trade_entry_at=episode[-1].entry_at.isoformat(),
        drawdown_r=str(worst),
        trades_in_episode=len(episode),
        losing_trades=sum(item.realized_gross_r < 0 for item in episode),
        state_family_counts=dict(sorted(state_counts.items())),
        episode_multiplicity_counts=dict(sorted(episode_counts.items())),
        boundary_multiplicity_counts=dict(sorted(boundary_counts.items())),
    )


def build_h1_multiplicity_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerH1MultiplicityReport:
    baseline, state_index, episode_index = _baseline(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    boundaries = _journey_boundaries(journey_root)

    grouped: dict[tuple[str, str, str], list[CapitalizerR0Trade]] = defaultdict(list)
    for trade in baseline:
        episode_tag, boundary_tag = _multiplicity_tags(
            trade,
            episode_index=episode_index,
            boundaries=boundaries,
        )
        grouped[
            (_state_family(trade, state_index), episode_tag, boundary_tag)
        ].append(trade)

    cells = tuple(
        CapitalizerH1MultiplicityCell(
            state_family=state,
            episode_multiplicity=episode_tag,
            source_boundary_multiplicity=boundary_tag,
            metrics=_metrics(tuple(raw)),
        )
        for (state, episode_tag, boundary_tag), raw in sorted(grouped.items())
    )

    definitions = (
        ("DROP_MULTI_EPISODE_ALL", None),
        ("DROP_MULTI_EPISODE_RECLAIM_ONLY", "RECLAIM_ALL_FRESH"),
        ("DROP_MULTI_EPISODE_NORECLAIM_ONLY", "NO_RECLAIM_FRESH"),
    )
    ablations: list[CapitalizerH1MultiplicityAblation] = []
    for name, state_scope in definitions:
        selected: list[CapitalizerR0Trade] = []
        excluded = 0
        for trade in baseline:
            episode_tag, _ = _multiplicity_tags(
                trade,
                episode_index=episode_index,
                boundaries=boundaries,
            )
            state = _state_family(trade, state_index)
            should_drop = (
                episode_tag == "MULTI_EPISODE"
                and (state_scope is None or state == state_scope)
            )
            if should_drop:
                excluded += 1
            else:
                selected.append(trade)
        ablations.append(
            CapitalizerH1MultiplicityAblation(
                name=name,
                excluded_trades=excluded,
                metrics=_metrics(tuple(selected)),
            )
        )

    return CapitalizerH1MultiplicityReport(
        identity=IDENTITY,
        symbol=baseline[0].symbol,
        baseline_metrics=_metrics(baseline),
        cells=cells,
        ablations=tuple(ablations),
        worst_drawdown=_worst_drawdown(
            baseline,
            state_index=state_index,
            episode_index=episode_index,
            boundaries=boundaries,
        ),
    )


def write_h1_multiplicity_report(
    report: CapitalizerH1MultiplicityReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-h1-multiplicity-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer H1 episode multiplicity residual-DD forensics"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_h1_multiplicity_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_h1_multiplicity_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "baseline": asdict(report.baseline_metrics),
                "worst_drawdown": asdict(report.worst_drawdown),
                "ablations": [
                    {
                        "name": item.name,
                        "excluded_trades": item.excluded_trades,
                        "metrics": asdict(item.metrics),
                    }
                    for item in report.ablations
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
