"""Natural-H1 departure timing forensics for QORE Capitalizer Structural V2.

This diagnostic reuses CIBO's causal DEPARTURE_TIMING_LEDGER. It does not optimize a numeric
threshold. The only boundary is 60 minutes because the source contract under study is H1:
an episode either completes inside the same H1 duration or it crosses that structural duration.

The report studies source-event->departure and CISD latency separately, including interactions
with Structural V2 state families. It also replays explicit ablations with the already-studied
PROFITABLE_SWING_LOCK so entry cognition and position management remain separately visible.

Research-only: no candidate freeze, promotion, execution authority, costs, or fresh holdout.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import iter_atlas_m5
from qore.infrastructure.trader_lab.capitalizer_cognitive_v2_development import (
    _root_state_index,
    select_development_trades,
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

IDENTITY = "QORE_CAPITALIZER_DEPARTURE_TIMING_FORENSICS_V1"
H1_DURATION_MINUTES = 60
_TIMING_IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
_TIMING_SCHEMA = "qore.cibo_market_atlas.departure_timing.v1"


@dataclass(frozen=True, slots=True)
class CapitalizerDepartureTimingCell:
    dimension: str
    timing_state: str
    structural_state: str
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerDepartureTimingAblation:
    name: str
    excluded_trades: int
    metrics_original_lifecycle: CapitalizerR0Metrics
    metrics_profitable_swing_lock: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerDepartureTimingAnnual:
    name: str
    year: int
    metrics_profitable_swing_lock: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerDepartureTimingReport:
    identity: str
    symbol: str
    h1_duration_minutes: int
    structural_v2_metrics: CapitalizerR0Metrics
    cells: tuple[CapitalizerDepartureTimingCell, ...]
    ablations: tuple[CapitalizerDepartureTimingAblation, ...]
    annual: tuple[CapitalizerDepartureTimingAnnual, ...]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    development_only: bool = True
    timing_features_causal: bool = True
    source_timeframe: str = "H1"
    optimized_numeric_threshold_used: bool = False
    boundary_semantics: str = "SOURCE_TIMEFRAME_DURATION"
    target_changed: bool = False
    candidate_frozen: bool = False
    costs_applied: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _load_timing_rows(root: Path) -> dict[str, dict[str, int | None]]:
    path = root / "DEPARTURE_TIMING_LEDGER.jsonl"
    if not path.exists():
        raise ValueError("DEPARTURE_TIMING_LEDGER.jsonl not found")
    result: dict[str, dict[str, int | None]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row: Any = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("departure timing row must be an object")
            if (
                row.get("identity") != _TIMING_IDENTITY
                or row.get("schema") != _TIMING_SCHEMA
            ):
                raise ValueError("unexpected departure timing identity/schema")
            if row.get("causal_feature") is not True or row.get("outcome_only") is not False:
                raise ValueError("departure timing row must be causal/non-outcome")
            if row.get("departure_at") is None:
                continue
            episode_id = str(row.get("episode_id"))
            source_minutes = row.get("minutes_source_event_to_departure")
            cisd_minutes = row.get("cisd_latency_minutes")
            if not isinstance(source_minutes, int) or source_minutes < 0:
                raise ValueError("resolved departure requires non-negative source latency")
            if not isinstance(cisd_minutes, int) or cisd_minutes < 0:
                raise ValueError("resolved departure requires non-negative CISD latency")
            if episode_id in result:
                raise ValueError("duplicate departure timing episode")
            result[episode_id] = {
                "source": source_minutes,
                "cisd": cisd_minutes,
            }
    return result


def _timing_state(
    trade: CapitalizerR0Trade,
    *,
    dimension: str,
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    timing: Mapping[str, Mapping[str, int | None]],
) -> str:
    episode_ids = episode_index.get((trade.signal_at.isoformat(), trade.side))
    if not episode_ids:
        raise ValueError("Structural V2 trade must map to exact H1 departure episode")
    values: list[int] = []
    for episode_id in episode_ids:
        row = timing.get(episode_id)
        if row is None:
            raise ValueError("H1 departure episode requires causal timing row")
        raw = row.get(dimension)
        if not isinstance(raw, int):
            raise ValueError("resolved timing dimension must be integer")
        values.append(raw)
    return (
        "ALL_WITHIN_H1"
        if all(value < H1_DURATION_MINUTES for value in values)
        else "ANY_CROSS_H1"
    )


def _metrics(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Metrics:
    if not trades:
        raise ValueError("departure timing metric group cannot be empty")
    return summarize_r0(trades).metrics


def _profit_lock(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    m5_root: Path,
) -> tuple[CapitalizerR0Trade, ...]:
    bars = tuple(iter_atlas_m5(m5_root))
    by_open, _ = _bar_indices(bars)
    return tuple(
        _simulate_trade(
            trade,
            bars=bars,
            by_open=by_open,
            mode=CapitalizerLifecycleMode.PROFITABLE_SWING_LOCK,
        )
        for trade in trades
    )


def _select(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    state_index: dict[tuple[str, CapitalizerSide], str],
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    timing: Mapping[str, Mapping[str, int | None]],
    dimension: str,
    scope: str,
) -> tuple[CapitalizerR0Trade, ...]:
    selected: list[CapitalizerR0Trade] = []
    for trade in trades:
        state = _state_family(trade, state_index)
        timing_state = _timing_state(
            trade,
            dimension=dimension,
            episode_index=episode_index,
            timing=timing,
        )
        remove = timing_state == "ANY_CROSS_H1"
        if scope == "NO_RECLAIM_ONLY":
            remove = remove and state == "NO_RECLAIM_FRESH"
        elif scope != "ALL":
            raise ValueError("unknown departure timing ablation scope")
        if not remove:
            selected.append(trade)
    if not selected:
        raise ValueError("departure timing ablation cannot remove all trades")
    return tuple(selected)


def build_departure_timing_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerDepartureTimingReport:
    all_trades = build_r0_trades(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    if not all_trades:
        raise ValueError("departure timing forensics require R0 trades")
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

    grouped: dict[tuple[str, str, str], list[CapitalizerR0Trade]] = defaultdict(list)
    for trade in structural:
        structural_state = _state_family(trade, state_index)
        for dimension in ("source", "cisd"):
            timing_state = _timing_state(
                trade,
                dimension=dimension,
                episode_index=episode_index,
                timing=timing,
            )
            grouped[(dimension, timing_state, structural_state)].append(trade)

    cells = tuple(
        CapitalizerDepartureTimingCell(
            dimension=dimension,
            timing_state=timing_state,
            structural_state=structural_state,
            metrics=_metrics(tuple(raw)),
        )
        for (dimension, timing_state, structural_state), raw in sorted(grouped.items())
    )

    definitions = (
        ("DROP_SOURCE_CROSS_H1", "source", "ALL"),
        ("DROP_CISD_CROSS_H1", "cisd", "ALL"),
        ("DROP_NORECLAIM_SOURCE_CROSS_H1", "source", "NO_RECLAIM_ONLY"),
        ("DROP_NORECLAIM_CISD_CROSS_H1", "cisd", "NO_RECLAIM_ONLY"),
    )
    ablations: list[CapitalizerDepartureTimingAblation] = []
    annual: list[CapitalizerDepartureTimingAnnual] = []
    for name, dimension, scope in definitions:
        selected = _select(
            structural,
            state_index=state_index,
            episode_index=episode_index,
            timing=timing,
            dimension=dimension,
            scope=scope,
        )
        protected = _profit_lock(selected, m5_root=m5_root)
        ablations.append(
            CapitalizerDepartureTimingAblation(
                name=name,
                excluded_trades=len(structural) - len(selected),
                metrics_original_lifecycle=_metrics(selected),
                metrics_profitable_swing_lock=_metrics(protected),
            )
        )
        years = sorted({trade.entry_at.year for trade in protected})
        for year in years:
            subset = tuple(trade for trade in protected if trade.entry_at.year == year)
            if subset:
                annual.append(
                    CapitalizerDepartureTimingAnnual(
                        name=name,
                        year=year,
                        metrics_profitable_swing_lock=_metrics(subset),
                    )
                )

    return CapitalizerDepartureTimingReport(
        identity=IDENTITY,
        symbol=structural[0].symbol,
        h1_duration_minutes=H1_DURATION_MINUTES,
        structural_v2_metrics=_metrics(structural),
        cells=cells,
        ablations=tuple(ablations),
        annual=tuple(annual),
    )


def write_departure_timing_report(
    report: CapitalizerDepartureTimingReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-departure-timing-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer natural-H1 departure timing forensics"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_departure_timing_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_departure_timing_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "h1_duration_minutes": report.h1_duration_minutes,
                "ablations": [
                    {
                        "name": row.name,
                        "excluded_trades": row.excluded_trades,
                        "original": asdict(row.metrics_original_lifecycle),
                        "profit_lock": asdict(row.metrics_profitable_swing_lock),
                    }
                    for row in report.ablations
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
