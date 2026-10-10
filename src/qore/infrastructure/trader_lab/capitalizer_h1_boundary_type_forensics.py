"""H1 source-boundary type forensics for QORE Capitalizer residual drawdown.

This diagnostic starts from the strongest consumed-development baseline:
Structural V2 + NO_RECLAIM CISD-cross-H1 exclusion + PROFITABLE_SWING_LOCK.

Exact aligned H1 departure episodes already carry a frozen categorical source-boundary type
from CIBO Market Journey. The diagnostic distinguishes:
- PRIOR_HIGH_LOW_ONLY;
- SWING_HIGH_LOW_ONLY; and
- MIXED_BOUNDARY_TYPE when exact aligned episodes disagree.

No numeric threshold is introduced. Outcome is used only for aggregate characterization.
Research-only: no rule selection, candidate freeze, holdout, costs, or promotion.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_h1_episode_multiplicity_forensics import (
    _baseline,
)
from qore.infrastructure.trader_lab.capitalizer_position_lifecycle_forensics import (
    _state_family,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    summarize_r0,
)

IDENTITY = "QORE_CAPITALIZER_H1_BOUNDARY_TYPE_FORENSICS_V1"
_JOURNEY_IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
_JOURNEY_SCHEMA = "qore.cibo_market_atlas.market_journey.v1"
_SUPPORTED_TYPES = frozenset({"PRIOR_HIGH_LOW", "SWING_HIGH_LOW"})


@dataclass(frozen=True, slots=True)
class CapitalizerH1BoundaryTypeCell:
    state_family: str
    boundary_type_state: str
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerH1BoundaryTypeAblation:
    name: str
    excluded_trades: int
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerH1BoundaryTypeDrawdown:
    drawdown_r: str
    peak_trade_entry_at: str
    trough_trade_entry_at: str
    trades_in_episode: int
    losing_trades: int
    state_family_counts: dict[str, int]
    boundary_type_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class CapitalizerH1BoundaryTypeReport:
    identity: str
    symbol: str
    baseline_metrics: CapitalizerR0Metrics
    cells: tuple[CapitalizerH1BoundaryTypeCell, ...]
    ablations: tuple[CapitalizerH1BoundaryTypeAblation, ...]
    worst_drawdown: CapitalizerH1BoundaryTypeDrawdown
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    development_only: bool = True
    categorical_causal_feature_only: bool = True
    numeric_threshold_optimization_used: bool = False
    costs_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _episode_boundary_types(journey_root: Path) -> dict[str, str]:
    path = journey_root / "MARKET_JOURNEY_LEDGER.jsonl"
    if not path.exists():
        raise ValueError("MARKET_JOURNEY_LEDGER.jsonl not found")

    result: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw: Any = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("Market Journey row must be an object")
            if (
                raw.get("identity") != _JOURNEY_IDENTITY
                or raw.get("schema") != _JOURNEY_SCHEMA
            ):
                raise ValueError("unexpected Market Journey identity/schema")
            if raw.get("causal_feature") is not True or raw.get("outcome_only") is not False:
                raise ValueError("Market Journey row must be causal/non-outcome")
            if raw.get("source_timeframe") != "H1" or raw.get("departure_at") is None:
                continue
            episode_id = str(raw.get("episode_id"))
            boundary_type = str(raw.get("source_boundary_type"))
            if boundary_type not in _SUPPORTED_TYPES:
                raise ValueError("unsupported H1 source boundary type")
            previous = result.get(episode_id)
            if previous is not None and previous != boundary_type:
                raise ValueError("episode cannot change source boundary type")
            result[episode_id] = boundary_type
    return result


def _boundary_type_state(
    trade: CapitalizerR0Trade,
    *,
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    boundary_types: Mapping[str, str],
) -> str:
    episodes = episode_index.get((trade.signal_at.isoformat(), trade.side))
    if not episodes:
        raise ValueError("baseline trade must map to exact H1 departure episodes")
    types = {boundary_types[episode_id] for episode_id in episodes}
    if types == {"PRIOR_HIGH_LOW"}:
        return "PRIOR_HIGH_LOW_ONLY"
    if types == {"SWING_HIGH_LOW"}:
        return "SWING_HIGH_LOW_ONLY"
    if types == _SUPPORTED_TYPES:
        return "MIXED_BOUNDARY_TYPE"
    raise ValueError("unexpected exact H1 boundary-type composition")


def _metrics(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Metrics:
    if not trades:
        raise ValueError("boundary-type metric group cannot be empty")
    return summarize_r0(trades).metrics


def _worst_drawdown(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    state_index: dict[tuple[str, CapitalizerSide], str],
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    boundary_types: Mapping[str, str],
) -> CapitalizerH1BoundaryTypeDrawdown:
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
    type_counts: Counter[str] = Counter()
    for trade in episode:
        state_counts[_state_family(trade, state_index)] += 1
        type_counts[
            _boundary_type_state(
                trade,
                episode_index=episode_index,
                boundary_types=boundary_types,
            )
        ] += 1

    return CapitalizerH1BoundaryTypeDrawdown(
        drawdown_r=str(worst),
        peak_trade_entry_at=episode[0].entry_at.isoformat(),
        trough_trade_entry_at=episode[-1].entry_at.isoformat(),
        trades_in_episode=len(episode),
        losing_trades=sum(item.realized_gross_r < 0 for item in episode),
        state_family_counts=dict(sorted(state_counts.items())),
        boundary_type_counts=dict(sorted(type_counts.items())),
    )


def build_h1_boundary_type_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerH1BoundaryTypeReport:
    baseline, state_index, episode_index = _baseline(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    boundary_types = _episode_boundary_types(journey_root)

    grouped: dict[tuple[str, str], list[CapitalizerR0Trade]] = defaultdict(list)
    for trade in baseline:
        grouped[
            (
                _state_family(trade, state_index),
                _boundary_type_state(
                    trade,
                    episode_index=episode_index,
                    boundary_types=boundary_types,
                ),
            )
        ].append(trade)

    cells = tuple(
        CapitalizerH1BoundaryTypeCell(
            state_family=state,
            boundary_type_state=boundary_state,
            metrics=_metrics(tuple(raw)),
        )
        for (state, boundary_state), raw in sorted(grouped.items())
    )

    definitions = (
        ("DROP_RECLAIM_SWING_ONLY", frozenset({"SWING_HIGH_LOW_ONLY"})),
        ("DROP_RECLAIM_MIXED_ONLY", frozenset({"MIXED_BOUNDARY_TYPE"})),
        (
            "DROP_RECLAIM_ANY_SWING_SOURCE",
            frozenset({"SWING_HIGH_LOW_ONLY", "MIXED_BOUNDARY_TYPE"}),
        ),
        ("DROP_RECLAIM_PRIOR_ONLY", frozenset({"PRIOR_HIGH_LOW_ONLY"})),
    )
    ablations: list[CapitalizerH1BoundaryTypeAblation] = []
    for name, blocked_states in definitions:
        selected: list[CapitalizerR0Trade] = []
        excluded = 0
        for trade in baseline:
            state = _state_family(trade, state_index)
            boundary_state = _boundary_type_state(
                trade,
                episode_index=episode_index,
                boundary_types=boundary_types,
            )
            should_drop = (
                state == "RECLAIM_ALL_FRESH"
                and boundary_state in blocked_states
            )
            if should_drop:
                excluded += 1
            else:
                selected.append(trade)
        ablations.append(
            CapitalizerH1BoundaryTypeAblation(
                name=name,
                excluded_trades=excluded,
                metrics=_metrics(tuple(selected)),
            )
        )

    return CapitalizerH1BoundaryTypeReport(
        identity=IDENTITY,
        symbol=baseline[0].symbol,
        baseline_metrics=_metrics(baseline),
        cells=cells,
        ablations=tuple(ablations),
        worst_drawdown=_worst_drawdown(
            baseline,
            state_index=state_index,
            episode_index=episode_index,
            boundary_types=boundary_types,
        ),
    )


def write_h1_boundary_type_report(
    report: CapitalizerH1BoundaryTypeReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-h1-boundary-type-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer H1 source-boundary type residual-DD forensics"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_h1_boundary_type_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_h1_boundary_type_report(report, args.output)
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
