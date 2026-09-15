"""Consumed-evidence Monte Carlo tail forensics for rejected VT-31 R7.

This module never opens fresh evidence and never changes the rejected R7
identity.  It tests the already-predeclared raid-resolution neighborhood to
understand why the fixed R7 witness misses the p95 drawdown gate.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5
import vt31_r7_candidate as r7
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _metrics,
)

DURATIONS = (3, 4, 5, 6, 7, 8)


def _run_partition(paths: dict[str, Path]) -> dict[str, object]:
    r5.CANDIDATE_ID = r7.CANDIDATE_ID
    r5.MAX_SIGNAL_MINUTE = r7.MAX_SIGNAL_MINUTE
    r5.MAX_RISK_TO_REFERENCE = r7.MAX_RISK_TO_REFERENCE
    r5.MIN_CONFIRMATION_BODY_FRACTION = r7.MIN_CONFIRMATION_BODY_FRACTION
    r5.TARGET_R = r7.TARGET_R
    r5._quality = r7._r7_quality
    return r5.replay(paths)


def _key(trade: dict[str, object]) -> tuple[str, str, str]:
    return (
        cast(str, trade["market"]),
        cast(str, trade["signal_at"]),
        cast(str, trade["side"]),
    )


def _worst_drawdown(trades: list[dict[str, object]]) -> dict[str, object]:
    equity = Decimal(0)
    peak = Decimal(0)
    peak_index = -1
    worst = Decimal(0)
    worst_start = 0
    worst_end = -1
    for index, trade in enumerate(trades):
        equity += Decimal(cast(str, trade["r_multiple"])) - r7.FRICTION
        if equity > peak:
            peak = equity
            peak_index = index
        drawdown = peak - equity
        if drawdown > worst:
            worst = drawdown
            worst_start = peak_index + 1
            worst_end = index
    episode = trades[worst_start : worst_end + 1]
    return {
        "drawdown_r": format(worst, "f"),
        "trade_count": len(episode),
        "start_signal_at": episode[0]["signal_at"] if episode else None,
        "end_signal_at": episode[-1]["signal_at"] if episode else None,
        "markets": dict(Counter(cast(str, x["market"]) for x in episode)),
        "sides": dict(Counter(cast(str, x["side"]) for x in episode)),
        "months": dict(Counter(cast(str, x["local_date"])[:7] for x in episode)),
        "exit_reasons": dict(Counter(cast(str, x["exit_reason"]) for x in episode)),
        "total_r_after_friction": format(
            sum(
                (
                    Decimal(cast(str, x["r_multiple"])) - r7.FRICTION
                    for x in episode
                ),
                Decimal(0),
            ),
            "f",
        ),
    }


def _worst_blocks(trades: list[dict[str, object]], width: int = 5) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for start in range(max(0, len(trades) - width + 1)):
        block = trades[start : start + width]
        total = sum(
            (
                Decimal(cast(str, x["r_multiple"])) - r7.FRICTION
                for x in block
            ),
            Decimal(0),
        )
        rows.append(
            {
                "start": block[0]["signal_at"],
                "end": block[-1]["signal_at"],
                "total_r_after_friction": format(total, "f"),
                "markets": [x["market"] for x in block],
                "sides": [x["side"] for x in block],
                "dates": [x["local_date"] for x in block],
                "r": [x["r_multiple"] for x in block],
            }
        )
    rows.sort(key=lambda row: Decimal(cast(str, row["total_r_after_friction"])))
    return rows[:12]


def _same_day_clusters(trades: list[dict[str, object]]) -> dict[str, object]:
    by_day: dict[str, list[dict[str, object]]] = defaultdict(list)
    for trade in trades:
        by_day[cast(str, trade["local_date"])].append(trade)
    multi = []
    for day, items in by_day.items():
        if len(items) < 2:
            continue
        total = sum(
            (
                Decimal(cast(str, x["r_multiple"])) - r7.FRICTION
                for x in items
            ),
            Decimal(0),
        )
        multi.append(
            {
                "day": day,
                "n": len(items),
                "total_r_after_friction": format(total, "f"),
                "markets": [x["market"] for x in items],
                "sides": [x["side"] for x in items],
            }
        )
    multi.sort(key=lambda row: Decimal(cast(str, row["total_r_after_friction"])))
    return {
        "multi_trade_day_count": len(multi),
        "worst_multi_trade_days": multi[:15],
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 6:
        print(
            "usage: vt31_r7_tail_forensics.py "
            "R5_NAS100 R5_SP500 R5_US30 R6_NAS100 R6_SP500 R6_US30"
        )
        return 2
    tranches = {
        "r5": {market: Path(path) for market, path in zip(r7.MARKETS, args[:3], strict=True)},
        "r6": {market: Path(path) for market, path in zip(r7.MARKETS, args[3:], strict=True)},
    }
    original_duration = r7.MAX_RAID_TO_EXTREME_BARS
    results: dict[str, object] = {}
    trade_sets: dict[int, list[dict[str, object]]] = {}
    try:
        for duration in DURATIONS:
            r7.MAX_RAID_TO_EXTREME_BARS = duration
            parts = [_run_partition(paths) for paths in tranches.values()]
            trades = [
                trade
                for part in parts
                for trade in cast(list[dict[str, object]], part["trades"])
            ]
            trades.sort(key=lambda item: (item["signal_at"], item["market"]))
            trade_sets[duration] = trades
            stress = _metrics(trades, friction=r7.FRICTION)
            mc, mc_gates = r7._monte_carlo(trades)
            markets = {
                market: _metrics(
                    [x for x in trades if x["market"] == market],
                    friction=r7.FRICTION,
                )
                for market in r7.MARKETS
            }
            sides = {
                side: _metrics(
                    [x for x in trades if x["side"] == side],
                    friction=r7.FRICTION,
                )
                for side in ("long", "short")
            }
            results[str(duration)] = {
                "stress": stress,
                "monte_carlo": mc,
                "monte_carlo_gates": mc_gates,
                "markets": markets,
                "sides": sides,
                "worst_realized_drawdown": _worst_drawdown(trades),
            }
    finally:
        r7.MAX_RAID_TO_EXTREME_BARS = original_duration

    baseline = trade_sets[6]
    baseline_keys = {_key(x) for x in baseline}
    fast = trade_sets[4]
    fast_keys = {_key(x) for x in fast}
    excluded_by_fast = [x for x in baseline if _key(x) not in fast_keys]
    added_vs_baseline = [x for x in fast if _key(x) not in baseline_keys]

    def subset_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
        return _metrics(rows, friction=r7.FRICTION) if rows else {"sample": 0}

    report = {
        "schema": "qore.trader_lab.vt31_r7_tail_forensics.v1",
        "candidate": r7.CANDIDATE_ID,
        "candidate_status": "REJECTED_PRE_FREEZE_CONSUMED_MONTE_CARLO",
        "fresh_evidence_opened": False,
        "fixed_body_fraction": format(r7.MIN_RAID_BODY_FRACTION, "f"),
        "duration_neighborhood": list(DURATIONS),
        "results": results,
        "baseline_duration_6": {
            "worst_five_trade_blocks": _worst_blocks(baseline),
            "same_day_clusters": _same_day_clusters(baseline),
        },
        "duration_4_vs_6": {
            "excluded_from_6_by_4": subset_metrics(excluded_by_fast),
            "added_in_4_not_6": subset_metrics(added_vs_baseline),
            "excluded_trade_count": len(excluded_by_fast),
            "added_trade_count": len(added_vs_baseline),
        },
        "adjudication_rule": (
            "Do not select a replacement threshold from a single best cell. "
            "A tighter duration may justify a new identity only if MC tail risk "
            "improves across an adjacent threshold neighborhood while market, "
            "side and sample gates remain stable."
        ),
    }
    Path("vt31-r7-tail-forensics.json").write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    )
    summary = {
        duration: {
            "sample": cast(dict[str, object], result)["stress"]["sample"],
            "mean_r": cast(dict[str, object], result)["stress"]["mean_r"],
            "pf": cast(dict[str, object], result)["stress"]["profit_factor"],
            "realized_dd": cast(dict[str, object], result)["stress"]["max_drawdown_r"],
            "mc_p95_dd": cast(dict[str, object], result)["monte_carlo"]["p95_max_drawdown_r"],
            "mc_positive_terminal": cast(dict[str, object], result)["monte_carlo"]["positive_terminal_probability"],
            "mc_pass": all(cast(dict[str, bool], cast(dict[str, object], result)["monte_carlo_gates"]).values()),
        }
        for duration, result in results.items()
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
