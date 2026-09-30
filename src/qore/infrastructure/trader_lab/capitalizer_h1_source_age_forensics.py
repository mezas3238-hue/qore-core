"""Natural H1 source-boundary age forensics for QORE Capitalizer residual drawdown.

The baseline is the strongest consumed-development configuration currently observed:
Structural V2 + NO_RECLAIM CISD-cross-H1 exclusion + PROFITABLE_SWING_LOCK.

Each exact H1 departure episode is classified only by its source-boundary H1 bucket relative
to the decision H1 bucket:
- CURRENT_H1_SOURCE: source created in the same H1 bucket as the decision;
- PRIOR_H1_SOURCE: source created in the immediately preceding H1 bucket;
- OLDER_H1_SOURCE: source is at least two H1 buckets older;
- MIXED_H1_SOURCE_AGE: exact aligned episodes disagree on those categories.

These are structural timeframe relations, not optimized numeric thresholds. Research-only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_h1_episode_multiplicity_forensics import (
    _baseline,
    _journey_boundaries,
)
from qore.infrastructure.trader_lab.capitalizer_position_lifecycle_forensics import (
    _state_family,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    summarize_r0,
)

IDENTITY = "QORE_CAPITALIZER_H1_SOURCE_AGE_FORENSICS_V1"
H1 = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class CapitalizerH1SourceAgeCell:
    state_family: str
    source_age_state: str
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerH1SourceAgeAblation:
    name: str
    excluded_trades: int
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerH1SourceAgeDrawdown:
    drawdown_r: str
    peak_trade_entry_at: str
    trough_trade_entry_at: str
    trades_in_episode: int
    losing_trades: int
    source_age_counts: dict[str, int]
    state_family_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class CapitalizerH1SourceAgeReport:
    identity: str
    symbol: str
    baseline_metrics: CapitalizerR0Metrics
    cells: tuple[CapitalizerH1SourceAgeCell, ...]
    ablations: tuple[CapitalizerH1SourceAgeAblation, ...]
    worst_drawdown: CapitalizerH1SourceAgeDrawdown
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    development_only: bool = True
    structural_timeframe_relation_only: bool = True
    numeric_threshold_optimization_used: bool = False
    costs_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _h1_bucket(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("H1 bucket requires timezone-aware timestamp")
    utc = moment.astimezone(UTC)
    return utc.replace(minute=0, second=0, microsecond=0)


def _episode_age_state(*, decision_at: datetime, created_at: datetime) -> str:
    decision_bucket = _h1_bucket(decision_at)
    created_bucket = _h1_bucket(created_at)
    if created_bucket > decision_bucket:
        raise ValueError("source boundary cannot be created after decision H1")
    distance = (decision_bucket - created_bucket) // H1
    if distance == 0:
        return "CURRENT_H1_SOURCE"
    if distance == 1:
        return "PRIOR_H1_SOURCE"
    return "OLDER_H1_SOURCE"


def _source_age_state(
    trade: CapitalizerR0Trade,
    *,
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    boundaries: Mapping[str, tuple[str, datetime]],
) -> str:
    episodes = episode_index.get((trade.signal_at.isoformat(), trade.side))
    if not episodes:
        raise ValueError("baseline trade must map to exact H1 departure episodes")
    states = {
        _episode_age_state(
            decision_at=trade.signal_at,
            created_at=boundaries[episode_id][1],
        )
        for episode_id in episodes
    }
    if len(states) == 1:
        return next(iter(states))
    return "MIXED_H1_SOURCE_AGE"


def _metrics(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Metrics:
    if not trades:
        raise ValueError("source-age metric group cannot be empty")
    return summarize_r0(trades).metrics


def _worst_drawdown(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    state_index: Mapping[tuple[str, CapitalizerSide], str],
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    boundaries: Mapping[str, tuple[str, datetime]],
) -> CapitalizerH1SourceAgeDrawdown:
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

    age_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    for trade in episode:
        age_counts[
            _source_age_state(
                trade,
                episode_index=episode_index,
                boundaries=boundaries,
            )
        ] += 1
        state_counts[_state_family(trade, dict(state_index))] += 1

    return CapitalizerH1SourceAgeDrawdown(
        drawdown_r=str(worst),
        peak_trade_entry_at=episode[0].entry_at.isoformat(),
        trough_trade_entry_at=episode[-1].entry_at.isoformat(),
        trades_in_episode=len(episode),
        losing_trades=sum(item.realized_gross_r < 0 for item in episode),
        source_age_counts=dict(sorted(age_counts.items())),
        state_family_counts=dict(sorted(state_counts.items())),
    )


def build_h1_source_age_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerH1SourceAgeReport:
    baseline, state_index, episode_index = _baseline(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    boundaries = _journey_boundaries(journey_root)

    grouped: dict[tuple[str, str], list[CapitalizerR0Trade]] = defaultdict(list)
    for trade in baseline:
        grouped[
            (
                _state_family(trade, state_index),
                _source_age_state(
                    trade,
                    episode_index=episode_index,
                    boundaries=boundaries,
                ),
            )
        ].append(trade)

    cells = tuple(
        CapitalizerH1SourceAgeCell(
            state_family=state,
            source_age_state=age_state,
            metrics=_metrics(tuple(raw)),
        )
        for (state, age_state), raw in sorted(grouped.items())
    )

    definitions = (
        ("DROP_OLDER_H1_SOURCE_ALL", None),
        ("DROP_OLDER_H1_SOURCE_RECLAIM_ONLY", "RECLAIM_ALL_FRESH"),
        ("DROP_OLDER_H1_SOURCE_NORECLAIM_ONLY", "NO_RECLAIM_FRESH"),
    )
    ablations: list[CapitalizerH1SourceAgeAblation] = []
    for name, state_scope in definitions:
        selected: list[CapitalizerR0Trade] = []
        excluded = 0
        for trade in baseline:
            state = _state_family(trade, state_index)
            age_state = _source_age_state(
                trade,
                episode_index=episode_index,
                boundaries=boundaries,
            )
            should_drop = (
                age_state == "OLDER_H1_SOURCE"
                and (state_scope is None or state == state_scope)
            )
            if should_drop:
                excluded += 1
            else:
                selected.append(trade)
        ablations.append(
            CapitalizerH1SourceAgeAblation(
                name=name,
                excluded_trades=excluded,
                metrics=_metrics(tuple(selected)),
            )
        )

    return CapitalizerH1SourceAgeReport(
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


def write_h1_source_age_report(
    report: CapitalizerH1SourceAgeReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-h1-source-age-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer natural H1 source-boundary age forensics"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_h1_source_age_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_h1_source_age_report(report, args.output)
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
