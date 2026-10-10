"""Exact causal trace for QORE Capitalizer's residual maximum drawdown.

The trace does not select or test a new trading rule. It reconstructs the exact maximum
drawdown episode of the strongest consumed-development baseline and annotates each trade with
already-available causal state:
- Cognitive V2 state family;
- exact H1 boundary-type composition;
- exact H1 source-age state;
- reclaim phase relative to the departure;
- side, lifecycle result, and exit reason.

This is intended to expose joint causal patterns that one-dimensional ablations can hide.
No future outcome is consumed by cognition; outcome is only the diagnostic label.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_h1_boundary_type_forensics import (
    _boundary_type_state,
    _episode_boundary_types,
)
from qore.infrastructure.trader_lab.capitalizer_h1_episode_multiplicity_forensics import (
    _baseline,
    _journey_boundaries,
)
from qore.infrastructure.trader_lab.capitalizer_h1_source_age_forensics import (
    _source_age_state,
)
from qore.infrastructure.trader_lab.capitalizer_position_lifecycle_forensics import (
    _state_family,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
)
from qore.infrastructure.trader_lab.capitalizer_reclaim_phase_forensics import (
    _episode_reclaim_times,
    _reclaim_phase,
)

IDENTITY = "QORE_CAPITALIZER_RESIDUAL_DD_CAUSAL_TRACE_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerResidualDDTraceRow:
    signal_at: str
    entry_at: str
    exit_at: str
    side: str
    realized_gross_r: str
    planned_reward_r: str
    exit_reason: str
    bars_held: int
    state_family: str
    source_age_state: str
    boundary_type_state: str
    reclaim_phase: str


@dataclass(frozen=True, slots=True)
class CapitalizerResidualDDTraceReport:
    identity: str
    symbol: str
    baseline_trades: int
    baseline_max_drawdown_r: str
    trace_start_entry_at: str
    trace_end_entry_at: str
    trace_trades: int
    trace_losses: int
    trace_total_r: str
    rows: tuple[CapitalizerResidualDDTraceRow, ...]
    joint_state_counts: dict[str, int]
    side_counts: dict[str, int]
    exit_reason_counts: dict[str, int]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    diagnostic_only: bool = True
    causal_annotations_only: bool = True
    outcome_used_as_label_only: bool = True
    numeric_threshold_optimization_used: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _worst_drawdown_episode(
    trades: tuple[CapitalizerR0Trade, ...],
) -> tuple[Decimal, tuple[CapitalizerR0Trade, ...]]:
    if not trades:
        raise ValueError("residual DD trace requires trades")
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
    return worst, episode


def build_residual_dd_trace(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerResidualDDTraceReport:
    baseline, state_index, episode_index = _baseline(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    worst, episode = _worst_drawdown_episode(baseline)
    boundaries = _journey_boundaries(journey_root)
    boundary_types = _episode_boundary_types(journey_root)
    reclaim_times = _episode_reclaim_times(journey_root)

    rows: list[CapitalizerResidualDDTraceRow] = []
    joint_counts: Counter[str] = Counter()
    side_counts: Counter[str] = Counter()
    exit_counts: Counter[str] = Counter()

    for trade in episode:
        state = _state_family(trade, state_index)
        source_age = _source_age_state(
            trade,
            episode_index=episode_index,
            boundaries=boundaries,
        )
        boundary_type = _boundary_type_state(
            trade,
            episode_index=episode_index,
            boundary_types=boundary_types,
        )
        reclaim_phase = _reclaim_phase(
            trade,
            episode_index=episode_index,
            reclaim_times=reclaim_times,
        )
        row = CapitalizerResidualDDTraceRow(
            signal_at=trade.signal_at.isoformat(),
            entry_at=trade.entry_at.isoformat(),
            exit_at=trade.exit_at.isoformat(),
            side=trade.side.value,
            realized_gross_r=str(trade.realized_gross_r),
            planned_reward_r=str(trade.planned_reward_r),
            exit_reason=trade.exit_reason,
            bars_held=trade.bars_held,
            state_family=state,
            source_age_state=source_age,
            boundary_type_state=boundary_type,
            reclaim_phase=reclaim_phase,
        )
        rows.append(row)
        joint_counts[
            "|".join((state, source_age, boundary_type, reclaim_phase))
        ] += 1
        side_counts[trade.side.value] += 1
        exit_counts[trade.exit_reason] += 1

    return CapitalizerResidualDDTraceReport(
        identity=IDENTITY,
        symbol=baseline[0].symbol,
        baseline_trades=len(baseline),
        baseline_max_drawdown_r=str(worst),
        trace_start_entry_at=episode[0].entry_at.isoformat(),
        trace_end_entry_at=episode[-1].entry_at.isoformat(),
        trace_trades=len(episode),
        trace_losses=sum(item.realized_gross_r < 0 for item in episode),
        trace_total_r=str(
            sum((item.realized_gross_r for item in episode), Decimal("0"))
        ),
        rows=tuple(rows),
        joint_state_counts=dict(sorted(joint_counts.items())),
        side_counts=dict(sorted(side_counts.items())),
        exit_reason_counts=dict(sorted(exit_counts.items())),
    )


def write_residual_dd_trace(
    report: CapitalizerResidualDDTraceReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-residual-dd-trace-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer residual maximum-drawdown causal trace"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_residual_dd_trace(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_residual_dd_trace(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "baseline_trades": report.baseline_trades,
                "baseline_max_drawdown_r": report.baseline_max_drawdown_r,
                "trace_trades": report.trace_trades,
                "trace_losses": report.trace_losses,
                "trace_total_r": report.trace_total_r,
                "joint_state_counts": report.joint_state_counts,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
