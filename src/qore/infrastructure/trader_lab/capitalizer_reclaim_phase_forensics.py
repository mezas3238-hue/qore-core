"""Reclaim-phase forensics for QORE Capitalizer residual drawdown.

The diagnostic preserves the strongest consumed-development baseline and asks whether the
causal reclaim was already established strictly before the exact H1 departure or only became
known at the departure timestamp itself.

For exact aligned H1 episodes the categorical phase is:
- NO_RECLAIM_OBSERVED: no reclaim exists at/before the decision;
- RECLAIM_STRICTLY_BEFORE: all observed reclaims precede the departure;
- RECLAIM_AT_DEPARTURE: all observed reclaims occur exactly at the departure;
- MIXED_RECLAIM_PHASE: exact aligned episodes disagree between those causal phases.

The distinction uses event ordering only. It introduces no optimized time threshold.
Research-only; no rule selection, candidate freeze, costs, holdout, or promotion.
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

IDENTITY = "QORE_CAPITALIZER_RECLAIM_PHASE_FORENSICS_V1"
_JOURNEY_IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
_JOURNEY_SCHEMA = "qore.cibo_market_atlas.market_journey.v1"


@dataclass(frozen=True, slots=True)
class CapitalizerReclaimPhaseCell:
    state_family: str
    reclaim_phase: str
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerReclaimPhaseAblation:
    name: str
    excluded_trades: int
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerReclaimPhaseDrawdown:
    drawdown_r: str
    peak_trade_entry_at: str
    trough_trade_entry_at: str
    trades_in_episode: int
    losing_trades: int
    state_family_counts: dict[str, int]
    reclaim_phase_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class CapitalizerReclaimPhaseReport:
    identity: str
    symbol: str
    baseline_metrics: CapitalizerR0Metrics
    cells: tuple[CapitalizerReclaimPhaseCell, ...]
    ablations: tuple[CapitalizerReclaimPhaseAblation, ...]
    worst_drawdown: CapitalizerReclaimPhaseDrawdown
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    development_only: bool = True
    causal_event_order_only: bool = True
    numeric_threshold_optimization_used: bool = False
    costs_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _episode_reclaim_times(
    journey_root: Path,
) -> dict[str, tuple[datetime, datetime | None]]:
    path = journey_root / "MARKET_JOURNEY_LEDGER.jsonl"
    if not path.exists():
        raise ValueError("MARKET_JOURNEY_LEDGER.jsonl not found")

    result: dict[str, tuple[datetime, datetime | None]] = {}
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
            departure_raw = raw.get("departure_at")
            if not isinstance(departure_raw, str):
                raise ValueError("departure timestamp must be ISO string")
            departure = datetime.fromisoformat(departure_raw)
            if departure.tzinfo is None or departure.utcoffset() is None:
                raise ValueError("departure timestamp must be timezone-aware")

            reclaim_raw = raw.get("reclaim_at")
            reclaim: datetime | None = None
            if reclaim_raw is not None:
                if not isinstance(reclaim_raw, str):
                    raise ValueError("reclaim timestamp must be ISO string")
                reclaim = datetime.fromisoformat(reclaim_raw)
                if reclaim.tzinfo is None or reclaim.utcoffset() is None:
                    raise ValueError("reclaim timestamp must be timezone-aware")

            previous = result.get(episode_id)
            current = (departure, reclaim)
            if previous is not None and previous != current:
                raise ValueError("episode cannot change departure/reclaim timing")
            result[episode_id] = current
    return result


def _reclaim_phase(
    trade: CapitalizerR0Trade,
    *,
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    reclaim_times: Mapping[str, tuple[datetime, datetime | None]],
) -> str:
    episodes = episode_index.get((trade.signal_at.isoformat(), trade.side))
    if not episodes:
        raise ValueError("baseline trade must map to exact H1 departure episodes")

    phases: set[str] = set()
    for episode_id in episodes:
        departure, reclaim = reclaim_times[episode_id]
        if departure != trade.signal_at:
            raise ValueError("exact H1 departure must equal trade signal timestamp")
        if reclaim is None or reclaim > trade.signal_at:
            phases.add("NO_RECLAIM_OBSERVED")
        elif reclaim == trade.signal_at:
            phases.add("RECLAIM_AT_DEPARTURE")
        else:
            phases.add("RECLAIM_STRICTLY_BEFORE")

    if len(phases) == 1:
        return next(iter(phases))
    return "MIXED_RECLAIM_PHASE"


def _metrics(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Metrics:
    if not trades:
        raise ValueError("reclaim-phase metric group cannot be empty")
    return summarize_r0(trades).metrics


def _worst_drawdown(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    state_index: dict[tuple[str, CapitalizerSide], str],
    episode_index: Mapping[tuple[str, CapitalizerSide], tuple[str, ...]],
    reclaim_times: Mapping[str, tuple[datetime, datetime | None]],
) -> CapitalizerReclaimPhaseDrawdown:
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
    phase_counts: Counter[str] = Counter()
    for trade in episode:
        state_counts[_state_family(trade, state_index)] += 1
        phase_counts[
            _reclaim_phase(
                trade,
                episode_index=episode_index,
                reclaim_times=reclaim_times,
            )
        ] += 1

    return CapitalizerReclaimPhaseDrawdown(
        drawdown_r=str(worst),
        peak_trade_entry_at=episode[0].entry_at.isoformat(),
        trough_trade_entry_at=episode[-1].entry_at.isoformat(),
        trades_in_episode=len(episode),
        losing_trades=sum(item.realized_gross_r < 0 for item in episode),
        state_family_counts=dict(sorted(state_counts.items())),
        reclaim_phase_counts=dict(sorted(phase_counts.items())),
    )


def build_reclaim_phase_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerReclaimPhaseReport:
    baseline, state_index, episode_index = _baseline(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    reclaim_times = _episode_reclaim_times(journey_root)

    grouped: dict[tuple[str, str], list[CapitalizerR0Trade]] = defaultdict(list)
    for trade in baseline:
        grouped[
            (
                _state_family(trade, state_index),
                _reclaim_phase(
                    trade,
                    episode_index=episode_index,
                    reclaim_times=reclaim_times,
                ),
            )
        ].append(trade)

    cells = tuple(
        CapitalizerReclaimPhaseCell(
            state_family=state,
            reclaim_phase=phase,
            metrics=_metrics(tuple(raw)),
        )
        for (state, phase), raw in sorted(grouped.items())
    )

    definitions = (
        ("DROP_RECLAIM_AT_DEPARTURE", frozenset({"RECLAIM_AT_DEPARTURE"})),
        ("DROP_RECLAIM_PHASE_MIXED", frozenset({"MIXED_RECLAIM_PHASE"})),
        (
            "DROP_RECLAIM_NOT_STRICTLY_PRIOR",
            frozenset({"RECLAIM_AT_DEPARTURE", "MIXED_RECLAIM_PHASE"}),
        ),
    )
    ablations: list[CapitalizerReclaimPhaseAblation] = []
    for name, blocked_phases in definitions:
        selected: list[CapitalizerR0Trade] = []
        excluded = 0
        for trade in baseline:
            state = _state_family(trade, state_index)
            phase = _reclaim_phase(
                trade,
                episode_index=episode_index,
                reclaim_times=reclaim_times,
            )
            should_drop = (
                state == "RECLAIM_ALL_FRESH"
                and phase in blocked_phases
            )
            if should_drop:
                excluded += 1
            else:
                selected.append(trade)
        ablations.append(
            CapitalizerReclaimPhaseAblation(
                name=name,
                excluded_trades=excluded,
                metrics=_metrics(tuple(selected)),
            )
        )

    return CapitalizerReclaimPhaseReport(
        identity=IDENTITY,
        symbol=baseline[0].symbol,
        baseline_metrics=_metrics(baseline),
        cells=cells,
        ablations=tuple(ablations),
        worst_drawdown=_worst_drawdown(
            baseline,
            state_index=state_index,
            episode_index=episode_index,
            reclaim_times=reclaim_times,
        ),
    )


def write_reclaim_phase_report(
    report: CapitalizerReclaimPhaseReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-reclaim-phase-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer reclaim-phase residual-DD forensics"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_reclaim_phase_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_reclaim_phase_report(report, args.output)
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
