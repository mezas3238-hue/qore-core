"""Joint causal-state characterization for QORE Capitalizer.

One-dimensional residual-DD ablations can hide interactions. This diagnostic therefore
characterizes the full consumed-development baseline across the joint causal state available
at decision time:

- Cognitive V2 state family;
- H1 source-age category;
- H1 source-boundary type composition;
- reclaim phase relative to exact H1 departure.

The report includes full-sample and annual cells. It intentionally performs no filtering,
threshold search, candidate selection, costs, holdout claim, or promotion.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
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
    _year,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    summarize_r0,
)
from qore.infrastructure.trader_lab.capitalizer_reclaim_phase_forensics import (
    _episode_reclaim_times,
    _reclaim_phase,
)

IDENTITY = "QORE_CAPITALIZER_JOINT_CAUSAL_STATE_FORENSICS_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerJointStateCell:
    joint_state: str
    state_family: str
    source_age_state: str
    boundary_type_state: str
    reclaim_phase: str
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerJointStateAnnual:
    year: int
    joint_state: str
    trades: int
    total_gross_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int


@dataclass(frozen=True, slots=True)
class CapitalizerJointStateReport:
    identity: str
    symbol: str
    baseline_metrics: CapitalizerR0Metrics
    cells: tuple[CapitalizerJointStateCell, ...]
    annual: tuple[CapitalizerJointStateAnnual, ...]
    distinct_joint_states: int
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    diagnostic_only: bool = True
    causal_annotations_only: bool = True
    full_baseline_characterized: bool = True
    numeric_threshold_optimization_used: bool = False
    filters_applied: bool = False
    costs_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _joint_state_key(
    *,
    state_family: str,
    source_age_state: str,
    boundary_type_state: str,
    reclaim_phase: str,
) -> str:
    return "|".join(
        (
            state_family,
            source_age_state,
            boundary_type_state,
            reclaim_phase,
        )
    )


def _metrics(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Metrics:
    if not trades:
        raise ValueError("joint-state metrics require trades")
    return summarize_r0(trades).metrics


def build_joint_state_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerJointStateReport:
    baseline, state_index, episode_index = _baseline(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    if not baseline:
        raise ValueError("joint-state forensics require baseline trades")

    boundaries = _journey_boundaries(journey_root)
    boundary_types = _episode_boundary_types(journey_root)
    reclaim_times = _episode_reclaim_times(journey_root)

    grouped: dict[
        tuple[str, str, str, str],
        list[CapitalizerR0Trade],
    ] = defaultdict(list)
    annual_grouped: dict[
        tuple[int, str],
        list[CapitalizerR0Trade],
    ] = defaultdict(list)

    for trade in baseline:
        state_family = _state_family(trade, state_index)
        source_age_state = _source_age_state(
            trade,
            episode_index=episode_index,
            boundaries=boundaries,
        )
        boundary_type_state = _boundary_type_state(
            trade,
            episode_index=episode_index,
            boundary_types=boundary_types,
        )
        reclaim_phase = _reclaim_phase(
            trade,
            episode_index=episode_index,
            reclaim_times=reclaim_times,
        )
        key = (
            state_family,
            source_age_state,
            boundary_type_state,
            reclaim_phase,
        )
        grouped[key].append(trade)
        joint_state = _joint_state_key(
            state_family=state_family,
            source_age_state=source_age_state,
            boundary_type_state=boundary_type_state,
            reclaim_phase=reclaim_phase,
        )
        annual_grouped[(_year(trade), joint_state)].append(trade)

    cells = tuple(
        CapitalizerJointStateCell(
            joint_state=_joint_state_key(
                state_family=state_family,
                source_age_state=source_age_state,
                boundary_type_state=boundary_type_state,
                reclaim_phase=reclaim_phase,
            ),
            state_family=state_family,
            source_age_state=source_age_state,
            boundary_type_state=boundary_type_state,
            reclaim_phase=reclaim_phase,
            metrics=_metrics(tuple(raw)),
        )
        for (
            state_family,
            source_age_state,
            boundary_type_state,
            reclaim_phase,
        ), raw in sorted(grouped.items())
    )

    annual_rows: list[CapitalizerJointStateAnnual] = []
    for (year, joint_state), raw in sorted(annual_grouped.items()):
        metrics = _metrics(tuple(raw))
        annual_rows.append(
            CapitalizerJointStateAnnual(
                year=year,
                joint_state=joint_state,
                trades=metrics.trades,
                total_gross_r=metrics.total_gross_r,
                profit_factor=metrics.profit_factor,
                max_drawdown_r=metrics.max_drawdown_r,
                max_losing_streak=metrics.max_losing_streak,
            )
        )

    return CapitalizerJointStateReport(
        identity=IDENTITY,
        symbol=baseline[0].symbol,
        baseline_metrics=_metrics(baseline),
        cells=cells,
        annual=tuple(annual_rows),
        distinct_joint_states=len(cells),
    )


def write_joint_state_report(
    report: CapitalizerJointStateReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-joint-state-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer full-baseline joint causal-state forensics"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_joint_state_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_joint_state_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "baseline": asdict(report.baseline_metrics),
                "distinct_joint_states": report.distinct_joint_states,
                "cells": [
                    {
                        "joint_state": row.joint_state,
                        "trades": row.metrics.trades,
                        "profit_factor": row.metrics.profit_factor,
                        "max_drawdown_r": row.metrics.max_drawdown_r,
                        "max_losing_streak": row.metrics.max_losing_streak,
                    }
                    for row in report.cells
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
