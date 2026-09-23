"""Joint consumed-evidence forensics for the frozen WAIT5 portfolio.

This module extends the WAIT5 DD causal atlas without changing the strategy.
It reports economics and DD-episode representation for pre-entry causal cohorts,
including annual stability. No cohort is promoted, filtered, or ranked for runtime use.

Joint cohort families are predeclared:
- ENTRY_MODE;
- ENTRY_MODE x exact FVG-confirmation-to-entry timing;
- ENTRY_MODE x MSS-to-entry timing;
- ENTRY_MODE x H1 remaining lifecycle;
- ENTRY_MODE x M3 displacement/ATR;
- ENTRY_MODE x stop-distance/ATR.

Outcome is diagnostic only. Any future candidate must be frozen separately from
causal evidence and tested on unconsumed data.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_dd_causal_atlas_2y_v1 as dd,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_DD_JOINT_FORENSICS_2Y_V1"
EXPECTED_MAX3 = 983
EXPECTED_DD = Decimal("11.9420088471277198029814040")


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _exact_timing(later: str, earlier: str) -> str:
    seconds = int((_aware(later) - _aware(earlier)).total_seconds())
    if seconds < 0:
        return "NEGATIVE"
    if seconds == 0:
        return "EXACT_ZERO"
    minutes = seconds // 60
    if minutes <= 5:
        return "GT0_TO_5M"
    if minutes <= 15:
        return "06_TO_15M"
    if minutes <= 30:
        return "16_TO_30M"
    return "GT_30M"


def _ratio_features(trade: v3.V3Trade) -> tuple[str, str]:
    atr = Decimal(trade.m3_atr14)
    if atr <= 0:
        raise ValueError("WAIT5 joint forensics requires positive ATR")
    displacement = Decimal(trade.m3_displacement_range) / atr
    stop_distance = abs(Decimal(trade.entry_price) - Decimal(trade.stop_price)) / atr
    return dd._ratio_bucket(displacement), dd._stop_atr_bucket(stop_distance)


def _cohort_keys(trade: v3.V3Trade) -> tuple[tuple[str, str], ...]:
    displacement_bucket, stop_bucket = _ratio_features(trade)
    fvg_timing = _exact_timing(trade.entry_at, trade.m1_fvg_confirmed_at)
    mss_timing = _exact_timing(trade.entry_at, trade.m3_mss_at)
    h1_remaining = dd._bucket_minutes(dd._minutes(trade.h1_deadline, trade.entry_at))
    mode = trade.entry_mode
    return (
        ("ENTRY_MODE", mode),
        ("ENTRY_MODE_X_FVG_TIMING", f"{mode}|{fvg_timing}"),
        ("ENTRY_MODE_X_MSS_TIMING", f"{mode}|{mss_timing}"),
        ("ENTRY_MODE_X_H1_REMAINING", f"{mode}|{h1_remaining}"),
        ("ENTRY_MODE_X_DISPLACEMENT_ATR", f"{mode}|{displacement_bucket}"),
        ("ENTRY_MODE_X_STOP_ATR", f"{mode}|{stop_bucket}"),
    )


def _metrics(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    result = v3._metrics(trades)
    return None if result is None else asdict(result)


def build_report(root: Path) -> dict[str, Any]:
    raw = dd._load_trades(root)
    baseline = v3._portfolio_max3(raw)
    if len(baseline) != EXPECTED_MAX3:
        raise ValueError("WAIT5 joint forensics MAX3 mismatch")
    metrics = v3._metrics(baseline)
    if metrics is None or Decimal(metrics.max_drawdown_r) != EXPECTED_DD:
        raise ValueError("WAIT5 joint forensics DD mismatch")

    worst, episode = dd._worst_drawdown_episode(baseline)
    if worst != EXPECTED_DD:
        raise ValueError("WAIT5 joint forensics episode mismatch")

    grouped: dict[tuple[str, str], list[v3.V3Trade]] = defaultdict(list)
    episode_grouped: dict[tuple[str, str], list[v3.V3Trade]] = defaultdict(list)
    annual_grouped: dict[tuple[int, str, str], list[v3.V3Trade]] = defaultdict(list)

    for trade in baseline:
        year = _aware(trade.entry_at).year
        for dimension, key in _cohort_keys(trade):
            grouped[(dimension, key)].append(trade)
            annual_grouped[(year, dimension, key)].append(trade)

    for trade in episode:
        for dimension, key in _cohort_keys(trade):
            episode_grouped[(dimension, key)].append(trade)

    cells: list[dict[str, Any]] = []
    baseline_n = Decimal(len(baseline))
    episode_n = Decimal(len(episode))
    for dimension, key in sorted(grouped):
        cohort = tuple(grouped[(dimension, key)])
        episode_cohort = tuple(episode_grouped.get((dimension, key), ()))
        base_share = Decimal(len(cohort)) / baseline_n
        episode_share = Decimal(len(episode_cohort)) / episode_n
        lift = Decimal("0") if base_share == 0 else episode_share / base_share
        annual = []
        years = sorted({_aware(item.entry_at).year for item in cohort})
        for year in years:
            rows = tuple(annual_grouped[(year, dimension, key)])
            annual.append(
                {
                    "year": year,
                    "trades": len(rows),
                    "metrics": _metrics(rows),
                }
            )
        cells.append(
            {
                "dimension": dimension,
                "key": key,
                "trades": len(cohort),
                "metrics": _metrics(cohort),
                "episode_trades": len(episode_cohort),
                "episode_share": str(episode_share),
                "baseline_share": str(base_share),
                "episode_overrepresentation_ratio": str(lift),
                "annual": annual,
            }
        )

    negative_timing = sum(
        1
        for trade in baseline
        if _exact_timing(trade.entry_at, trade.m1_fvg_confirmed_at) == "NEGATIVE"
    )
    zero_timing = sum(
        1
        for trade in baseline
        if _exact_timing(trade.entry_at, trade.m1_fvg_confirmed_at) == "EXACT_ZERO"
    )

    return {
        "identity": IDENTITY,
        "max3_trades": len(baseline),
        "baseline_metrics": asdict(metrics),
        "max_drawdown_r": str(worst),
        "episode_trades": len(episode),
        "negative_fvg_to_entry_timing": negative_timing,
        "exact_zero_fvg_to_entry_timing": zero_timing,
        "cells": cells,
        "predeclared_joint_families": [
            "ENTRY_MODE",
            "ENTRY_MODE_X_FVG_TIMING",
            "ENTRY_MODE_X_MSS_TIMING",
            "ENTRY_MODE_X_H1_REMAINING",
            "ENTRY_MODE_X_DISPLACEMENT_ATR",
            "ENTRY_MODE_X_STOP_ATR",
        ],
        "outcome_aware_diagnostic_only": True,
        "outcome_used_for_admission": False,
        "runtime_filter_selected": False,
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
        "capitalizer-nine-market-v3-source-first-wait5-dd-joint-forensics-2y-v1.json"
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
