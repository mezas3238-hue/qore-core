"""Structural Cognitive V2 development replay for QORE Capitalizer.

This is consumed-development evidence, not a candidate freeze. It tests whether two causal
state semantics discovered by R0 forensics reduce repeated loss clusters without inventing
numeric optimization thresholds:

- repeated directional acceptance on the immediately preceding contiguous M5 is treated as
  a late/chasing hypothesis;
- disagreement among exact H1 Journey episodes about reclaim state is treated as causal
  conflict, not as confidence.

The module also applies the already-frozen maximum-three-executions-per-session ceiling as a
separate ablation. Gross R0 lifecycle is intentionally retained so cognition and position
management are not conflated. Costs, provider portability, holdout, and certification remain
future stages.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import iter_atlas_m5
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    build_r0_trades,
    summarize_r0,
)
from qore.infrastructure.trader_lab.capitalizer_r0_root_cause_forensics import (
    _acceptance_state,
    _bars_by_close,
    _departure_episode_index,
    _is_acceptance,
    _pre_departure_sequences,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_V2_DEVELOPMENT_REPLAY_V1"
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveV2Ablation:
    name: str
    metrics: CapitalizerR0Metrics
    excluded_late_acceptance_repeat: int
    excluded_journey_conflict: int
    excluded_session_budget: int


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveV2DevelopmentReport:
    identity: str
    symbol: str
    baseline: CapitalizerR0Metrics
    ablations: tuple[CapitalizerCognitiveV2Ablation, ...]
    structural_hypothesis: tuple[str, ...]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    development_only: bool = True
    causal_features_only: bool = True
    numeric_threshold_optimization_used: bool = False
    position_intelligence_changed: bool = False
    execution_costs_applied: bool = False
    portfolio_cross_market_allocator_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False


def _root_state_index(
    *,
    m5_root: Path,
    journey_root: Path,
    trades: tuple[CapitalizerR0Trade, ...],
) -> dict[tuple[str, CapitalizerSide], str]:
    bars = tuple(iter_atlas_m5(m5_root))
    by_close = _bars_by_close(bars)
    episode_index = _departure_episode_index(journey_root)
    sequences = _pre_departure_sequences(journey_root)
    result: dict[tuple[str, CapitalizerSide], str] = {}
    for trade in trades:
        if not _is_acceptance(trade):
            continue
        key = (trade.signal_at.isoformat(), trade.side)
        result[key] = _acceptance_state(
            trade=trade,
            bars=bars,
            by_close=by_close,
            episode_index=episode_index,
            sequences=sequences,
        )
    return result


def _asia_session_day(trade: CapitalizerR0Trade) -> str:
    local = trade.entry_at.astimezone(NEW_YORK)
    operating_date = local.date()
    if local.hour < 2:
        operating_date -= timedelta(days=1)
    return operating_date.isoformat()


def select_development_trades(
    *,
    trades: tuple[CapitalizerR0Trade, ...],
    state_index: dict[tuple[str, CapitalizerSide], str],
    block_late_acceptance_repeat: bool,
    block_journey_conflict: bool,
    apply_session_ceiling: bool,
) -> tuple[
    tuple[CapitalizerR0Trade, ...],
    int,
    int,
    int,
]:
    """Apply only explicit structural ablations in chronological order."""

    selected: list[CapitalizerR0Trade] = []
    session_counts: dict[str, int] = defaultdict(int)
    late_repeat = 0
    journey_conflict = 0
    session_budget = 0

    canonical = tuple(sorted(trades, key=lambda item: (item.entry_at, item.exit_at)))
    for trade in canonical:
        state: str | None = None
        if _is_acceptance(trade):
            key = (trade.signal_at.isoformat(), trade.side)
            state = state_index.get(key)
            if state is None:
                raise ValueError("acceptance trade requires causal root-cause state")

        if (
            block_late_acceptance_repeat
            and state is not None
            and state.endswith("_REPEAT")
        ):
            late_repeat += 1
            continue
        if (
            block_journey_conflict
            and state is not None
            and state.startswith("RECLAIM_MIXED_")
        ):
            journey_conflict += 1
            continue

        if apply_session_ceiling:
            session_day = _asia_session_day(trade)
            if session_counts[session_day] >= MAX_EXECUTIONS_PER_SESSION:
                session_budget += 1
                continue
            session_counts[session_day] += 1

        selected.append(trade)

    return tuple(selected), late_repeat, journey_conflict, session_budget


def _ablation(
    *,
    name: str,
    trades: tuple[CapitalizerR0Trade, ...],
    state_index: dict[tuple[str, CapitalizerSide], str],
    block_late_acceptance_repeat: bool,
    block_journey_conflict: bool,
    apply_session_ceiling: bool,
) -> CapitalizerCognitiveV2Ablation:
    selected, late_repeat, journey_conflict, session_budget = select_development_trades(
        trades=trades,
        state_index=state_index,
        block_late_acceptance_repeat=block_late_acceptance_repeat,
        block_journey_conflict=block_journey_conflict,
        apply_session_ceiling=apply_session_ceiling,
    )
    if not selected:
        raise ValueError("Cognitive V2 development ablation cannot remove all trades")
    return CapitalizerCognitiveV2Ablation(
        name=name,
        metrics=summarize_r0(selected).metrics,
        excluded_late_acceptance_repeat=late_repeat,
        excluded_journey_conflict=journey_conflict,
        excluded_session_budget=session_budget,
    )


def build_cognitive_v2_development_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerCognitiveV2DevelopmentReport:
    trades = build_r0_trades(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    if not trades:
        raise ValueError("Cognitive V2 development requires R0 trades")
    state_index = _root_state_index(
        m5_root=m5_root,
        journey_root=journey_root,
        trades=trades,
    )
    ablations = (
        _ablation(
            name="FRESHNESS_ONLY",
            trades=trades,
            state_index=state_index,
            block_late_acceptance_repeat=True,
            block_journey_conflict=False,
            apply_session_ceiling=False,
        ),
        _ablation(
            name="JOURNEY_CONFLICT_ONLY",
            trades=trades,
            state_index=state_index,
            block_late_acceptance_repeat=False,
            block_journey_conflict=True,
            apply_session_ceiling=False,
        ),
        _ablation(
            name="STRUCTURAL_V2",
            trades=trades,
            state_index=state_index,
            block_late_acceptance_repeat=True,
            block_journey_conflict=True,
            apply_session_ceiling=False,
        ),
        _ablation(
            name="STRUCTURAL_V2_MAX3_SESSION",
            trades=trades,
            state_index=state_index,
            block_late_acceptance_repeat=True,
            block_journey_conflict=True,
            apply_session_ceiling=True,
        ),
    )
    return CapitalizerCognitiveV2DevelopmentReport(
        identity=IDENTITY,
        symbol=trades[0].symbol,
        baseline=summarize_r0(trades).metrics,
        ablations=ablations,
        structural_hypothesis=(
            "IMMEDIATE_PRIOR_SAME_SIDE_ACCEPTANCE_IS_LATE_CHASE_DIAGNOSTIC",
            "MIXED_EXACT_H1_RECLAIM_STATE_IS_JOURNEY_CONFLICT",
            "NO_RECLAIM_FRESH_REMAINS_ELIGIBLE_FOR_CONTINUATION_RESEARCH",
            "REJECTION_ROUTE_REMAINS_SEPARATE",
        ),
    )


def write_cognitive_v2_development_report(
    report: CapitalizerCognitiveV2DevelopmentReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-cognitive-v2-development-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer structural Cognitive V2 development replay"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_cognitive_v2_development_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_cognitive_v2_development_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "baseline": asdict(report.baseline),
                "ablations": [
                    {
                        "name": row.name,
                        "trades": row.metrics.trades,
                        "profit_factor": row.metrics.profit_factor,
                        "max_drawdown_r": row.metrics.max_drawdown_r,
                        "max_losing_streak": row.metrics.max_losing_streak,
                    }
                    for row in report.ablations
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
