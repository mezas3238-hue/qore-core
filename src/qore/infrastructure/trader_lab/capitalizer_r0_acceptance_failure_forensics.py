"""Causal acceptance-failure forensics for QORE Capitalizer R0.

This module compares winners/losses of R0 acceptance trades using only information available
at or before entry. Outcome is used strictly as the label. No diagnostic slice becomes a
trading rule, filter, candidate revision, or promotion decision.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import iter_atlas_m5
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
    build_r0_trades,
)
from qore.infrastructure.trader_lab.capitalizer_target_context import (
    CapitalizerTargetContext,
    load_target_contexts,
)

IDENTITY = "QORE_CAPITALIZER_R0_ACCEPTANCE_FAILURE_FORENSICS_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerAcceptanceFeatureRow:
    event_signature: str
    outcome_label: str
    observations: int
    median_source_body_fraction: str
    median_source_range_ratio: str
    median_aligned_close_location: str
    median_entry_gap_range_units: str
    median_planned_reward_r: str
    median_active_target_candidates: str


@dataclass(frozen=True, slots=True)
class CapitalizerAcceptanceFailureReport:
    identity: str
    symbol: str
    session: str
    acceptance_trades: int
    rows: tuple[CapitalizerAcceptanceFeatureRow, ...]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    causal_features_only: bool = True
    outcome_used_as_label_only: bool = True
    filter_selected: bool = False
    candidate_revision_defined: bool = False
    execution_costs_applied: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False


def _target_index(
    contexts: tuple[CapitalizerTargetContext, ...],
) -> dict[tuple[str, CapitalizerSide, str], CapitalizerTargetContext]:
    result: dict[tuple[str, CapitalizerSide, str], CapitalizerTargetContext] = {}
    for context in contexts:
        key = (context.symbol, context.side, context.departure_at.isoformat())
        if key in result:
            raise ValueError("duplicate acceptance target context")
        result[key] = context
    return result


def _signature(trade: CapitalizerR0Trade) -> str:
    return "+".join(trade.event_labels)


def _is_acceptance(trade: CapitalizerR0Trade) -> bool:
    return any("ACCEPTANCE" in label for label in trade.event_labels)


def _aligned_close_location(
    *,
    low: Decimal,
    high: Decimal,
    close: Decimal,
    side: CapitalizerSide,
) -> Decimal:
    price_range = high - low
    if price_range <= 0:
        return Decimal("0.5")
    raw = (close - low) / price_range
    return raw if side is CapitalizerSide.LONG else Decimal("1") - raw


def summarize_acceptance_failure(
    *,
    m5_root: Path,
    target_root: Path,
    trades: tuple[CapitalizerR0Trade, ...],
) -> CapitalizerAcceptanceFailureReport:
    bars = tuple(iter_atlas_m5(m5_root))
    by_close = {bar.closed_at.isoformat(): index for index, bar in enumerate(bars)}
    targets = _target_index(load_target_contexts(target_root))

    grouped: dict[
        tuple[str, str],
        list[tuple[Decimal, Decimal, Decimal, Decimal, Decimal, int]],
    ] = defaultdict(list)

    acceptance_trades = 0
    for trade in trades:
        if not _is_acceptance(trade):
            continue
        acceptance_trades += 1
        index = by_close.get(trade.signal_at.isoformat())
        if index is None or index <= 0:
            continue
        source = bars[index]
        previous = bars[index - 1]
        if source.range <= 0 or previous.range <= 0:
            continue

        context = targets.get(
            (trade.symbol, trade.side, trade.signal_at.isoformat())
        )
        active_targets = 0 if context is None else context.active_candidate_count
        entry_gap = abs(trade.entry_price - source.close) / source.range
        body_fraction = source.body / source.range
        range_ratio = source.range / previous.range
        close_location = _aligned_close_location(
            low=source.low,
            high=source.high,
            close=source.close,
            side=trade.side,
        )
        outcome_label = "WIN" if trade.realized_gross_r > 0 else "LOSS"
        grouped[(_signature(trade), outcome_label)].append(
            (
                body_fraction,
                range_ratio,
                close_location,
                entry_gap,
                trade.planned_reward_r,
                active_targets,
            )
        )

    rows: list[CapitalizerAcceptanceFeatureRow] = []
    for (signature, outcome), values in sorted(grouped.items()):
        rows.append(
            CapitalizerAcceptanceFeatureRow(
                event_signature=signature,
                outcome_label=outcome,
                observations=len(values),
                median_source_body_fraction=str(median(item[0] for item in values)),
                median_source_range_ratio=str(median(item[1] for item in values)),
                median_aligned_close_location=str(median(item[2] for item in values)),
                median_entry_gap_range_units=str(median(item[3] for item in values)),
                median_planned_reward_r=str(median(item[4] for item in values)),
                median_active_target_candidates=str(median(item[5] for item in values)),
            )
        )

    if not rows:
        raise ValueError("acceptance failure forensics produced no rows")
    symbol = trades[0].symbol
    session = (
        "ASIA"
        if symbol in {"USDJPY", "AUDJPY", "AUDUSD", "GBPJPY"}
        else "LONDON"
        if symbol in {"EURUSD", "GBPUSD"}
        else "NEW_YORK"
    )
    return CapitalizerAcceptanceFailureReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session,
        acceptance_trades=acceptance_trades,
        rows=tuple(rows),
    )


def write_acceptance_failure_report(
    report: CapitalizerAcceptanceFailureReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-r0-acceptance-failure-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer R0 acceptance-failure forensics"
    )
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
    report = summarize_acceptance_failure(
        m5_root=args.m5_root,
        target_root=args.target_root,
        trades=trades,
    )
    write_acceptance_failure_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "acceptance_trades": report.acceptance_trades,
                "rows": len(report.rows),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
