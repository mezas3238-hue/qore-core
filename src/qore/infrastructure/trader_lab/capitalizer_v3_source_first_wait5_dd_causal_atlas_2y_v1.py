"""Outcome-aware causal atlas for the frozen WAIT5 maximum drawdown.

This diagnostic consumes the frozen SOURCE_FIRST + WAIT5 2Y trade ledgers and
reproduces the exact MAX3 portfolio used by the economic reference.

It does not alter, filter, score, rank for execution, or re-run the strategy.
Outcome is used only to identify the already-consumed maximum-drawdown episode.

All annotations are available no later than entry:
- market/session/side;
- session ordinal under MAX3;
- liquidity kind/source;
- entry mode and OB/FVG overlap;
- M5 closeback -> M3 MSS delay;
- M3 MSS -> entry delay;
- M1 FVG confirm -> entry delay;
- H1 lifecycle remaining at entry;
- M3 body ratio;
- displacement range / ATR14;
- stop distance / ATR14.

No runtime rule, threshold optimization, promotion, fresh holdout, or execution
authority is created by this module.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_DD_CAUSAL_ATLAS_2Y_V1"
EXPECTED_MAX3 = 983
EXPECTED_DD = Decimal("11.9420088471277198029814040")


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"WAIT5 DD atlas requires 9 trade ledgers, got {len(paths)}")
    rows: list[v3.V3Trade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
    )


def _worst_drawdown_episode(
    trades: tuple[v3.V3Trade, ...],
) -> tuple[Decimal, tuple[v3.V3Trade, ...]]:
    if not trades:
        raise ValueError("WAIT5 DD atlas requires trades")
    ordered = tuple(sorted(trades, key=lambda item: (_aware(item.entry_at), item.symbol)))
    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = -1
    worst = Decimal("0")
    worst_peak_index = -1
    worst_trough_index = -1

    for index, trade in enumerate(ordered):
        equity += Decimal(trade.realized_gross_r)
        if equity > peak:
            peak = equity
            peak_index = index
        drawdown = peak - equity
        if drawdown > worst:
            worst = drawdown
            worst_peak_index = peak_index
            worst_trough_index = index

    start = worst_peak_index + 1
    if worst_trough_index < start:
        raise ValueError("WAIT5 DD episode cannot be empty")
    return worst, ordered[start : worst_trough_index + 1]


def _minutes(later: str, earlier: str) -> int:
    return int((_aware(later) - _aware(earlier)).total_seconds() // 60)


def _bucket_minutes(value: int) -> str:
    if value <= 0:
        return "LE_0M"
    if value <= 5:
        return "01_05M"
    if value <= 15:
        return "06_15M"
    if value <= 30:
        return "16_30M"
    if value <= 60:
        return "31_60M"
    return "GT_60M"


def _body_bucket(value: Decimal) -> str:
    if value < Decimal("0.70"):
        return "0.60_TO_LT_0.70"
    if value < Decimal("0.80"):
        return "0.70_TO_LT_0.80"
    if value < Decimal("0.90"):
        return "0.80_TO_LT_0.90"
    return "GE_0.90"


def _ratio_bucket(value: Decimal) -> str:
    if value < Decimal("1.50"):
        return "1.20_TO_LT_1.50"
    if value < Decimal("2"):
        return "1.50_TO_LT_2.00"
    if value < Decimal("3"):
        return "2.00_TO_LT_3.00"
    return "GE_3.00"


def _stop_atr_bucket(value: Decimal) -> str:
    if value < Decimal("0.75"):
        return "LT_0.75"
    if value < Decimal("1.00"):
        return "0.75_TO_LT_1.00"
    if value < Decimal("1.50"):
        return "1.00_TO_LT_1.50"
    if value < Decimal("2.00"):
        return "1.50_TO_LT_2.00"
    return "GE_2.00"


def _ordinal_index(
    trades: tuple[v3.V3Trade, ...],
) -> dict[tuple[str, str, str, str], int]:
    grouped: dict[tuple[str, str], list[v3.V3Trade]] = defaultdict(list)
    for trade in trades:
        grouped[(trade.session, trade.operating_date)].append(trade)
    result: dict[tuple[str, str, str, str], int] = {}
    for _key, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol))
        for ordinal, trade in enumerate(ordered, start=1):
            result[
                (trade.symbol, trade.session, trade.operating_date, trade.entry_at)
            ] = ordinal
    return result


def _features(
    trade: v3.V3Trade,
    *,
    ordinal: int,
) -> dict[str, str]:
    atr = Decimal(trade.m3_atr14)
    if atr <= 0:
        raise ValueError("WAIT5 DD atlas requires positive M3 ATR")
    displacement_ratio = Decimal(trade.m3_displacement_range) / atr
    stop_distance = abs(Decimal(trade.entry_price) - Decimal(trade.stop_price))
    stop_atr = stop_distance / atr

    return {
        "MARKET": trade.symbol,
        "SESSION": trade.session,
        "SIDE": trade.side,
        "ORDINAL": f"ORDINAL_{ordinal}",
        "LIQUIDITY_KIND": trade.liquidity_kind,
        "LIQUIDITY_SOURCE": trade.liquidity_source,
        "ENTRY_MODE": trade.entry_mode,
        "OB_FVG_OVERLAP": (
            "OVERLAP" if trade.m1_ob_fvg_overlap else "NO_OVERLAP"
        ),
        "CLOSEBACK_TO_MSS": _bucket_minutes(
            _minutes(trade.m3_mss_at, trade.m5_closeback_at)
        ),
        "MSS_TO_ENTRY": _bucket_minutes(
            _minutes(trade.entry_at, trade.m3_mss_at)
        ),
        "FVG_TO_ENTRY": _bucket_minutes(
            _minutes(trade.entry_at, trade.m1_fvg_confirmed_at)
        ),
        "H1_REMAINING_AT_ENTRY": _bucket_minutes(
            _minutes(trade.h1_deadline, trade.entry_at)
        ),
        "M3_BODY_RATIO": _body_bucket(Decimal(trade.m3_body_ratio)),
        "M3_DISPLACEMENT_ATR": _ratio_bucket(displacement_ratio),
        "STOP_DISTANCE_ATR": _stop_atr_bucket(stop_atr),
    }


def _cell_rows(
    baseline: tuple[v3.V3Trade, ...],
    episode: tuple[v3.V3Trade, ...],
) -> tuple[dict[str, Any], ...]:
    ordinals = _ordinal_index(baseline)
    baseline_counts: Counter[tuple[str, str]] = Counter()
    episode_counts: Counter[tuple[str, str]] = Counter()

    def ingest(
        trades: tuple[v3.V3Trade, ...],
        counts: Counter[tuple[str, str]],
    ) -> None:
        for trade in trades:
            key = (trade.symbol, trade.session, trade.operating_date, trade.entry_at)
            ordinal = ordinals[key]
            for dimension, value in _features(trade, ordinal=ordinal).items():
                counts[(dimension, value)] += 1

    ingest(baseline, baseline_counts)
    ingest(episode, episode_counts)

    rows: list[dict[str, Any]] = []
    baseline_n = Decimal(len(baseline))
    episode_n = Decimal(len(episode))
    for dimension, value in sorted(baseline_counts):
        base_count = baseline_counts[(dimension, value)]
        ep_count = episode_counts[(dimension, value)]
        base_share = Decimal(base_count) / baseline_n
        ep_share = Decimal(ep_count) / episode_n
        lift = Decimal("0") if base_share == 0 else ep_share / base_share
        rows.append(
            {
                "dimension": dimension,
                "value": value,
                "baseline_trades": base_count,
                "episode_trades": ep_count,
                "baseline_share": str(base_share),
                "episode_share": str(ep_share),
                "episode_overrepresentation_ratio": str(lift),
            }
        )
    return tuple(rows)


def build_report(root: Path) -> dict[str, Any]:
    raw = _load_trades(root)
    baseline = v3._portfolio_max3(raw)
    if len(baseline) != EXPECTED_MAX3:
        raise ValueError("WAIT5 DD atlas MAX3 control mismatch")
    metrics = v3._metrics(baseline)
    if metrics is None:
        raise ValueError("WAIT5 DD atlas requires metrics")
    dd = Decimal(metrics.max_drawdown_r)
    if dd != EXPECTED_DD:
        raise ValueError("WAIT5 DD atlas drawdown control mismatch")

    worst, episode = _worst_drawdown_episode(baseline)
    if worst != EXPECTED_DD:
        raise ValueError("WAIT5 DD episode does not reproduce frozen DD")

    episode_metrics = v3._metrics(episode)
    if episode_metrics is None:
        raise ValueError("WAIT5 DD episode metrics missing")

    cells = _cell_rows(baseline, episode)
    episode_total = sum(
        (Decimal(item.realized_gross_r) for item in episode),
        Decimal("0"),
    )

    return {
        "identity": IDENTITY,
        "raw_trades": len(raw),
        "max3_trades": len(baseline),
        "baseline_metrics": asdict(metrics),
        "max_drawdown_r": str(worst),
        "episode_start_entry_at": episode[0].entry_at,
        "episode_end_entry_at": episode[-1].entry_at,
        "episode_trades": len(episode),
        "episode_losses": sum(
            Decimal(item.realized_gross_r) < 0 for item in episode
        ),
        "episode_wins": sum(
            Decimal(item.realized_gross_r) > 0 for item in episode
        ),
        "episode_total_r": str(episode_total),
        "episode_metrics": asdict(episode_metrics),
        "cells": cells,
        "annotations_available_by_entry": True,
        "outcome_used_only_to_locate_dd_episode": True,
        "outcome_used_for_admission": False,
        "filters_applied": False,
        "threshold_optimization_used": False,
        "candidate_frozen": False,
        "economic_candidate": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-wait5-dd-causal-atlas-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.input_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
