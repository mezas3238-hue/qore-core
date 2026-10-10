"""Outcome-aware forensics for the consumed strict LATE60 continuity candidate.

This module does not create or promote a new admission rule. It reproduces the
already-read strict-continuity development candidate and decomposes only its
selected late trades to explain why density increased while PF/expectancy/DD
failed to improve versus frozen WAIT5.

Admission remains exactly:
- NO_NEW_H1_SWEEP;
- deadline M5 ALIGNED;
- no completed M5 OPPOSED state during carry.

All grouping below is descriptive on the consumed 2Y development window.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_wait5_late60_strict_continuity_2y_v1 as strict,
)

IDENTITY = "QORE_CAPITALIZER_V3_WAIT5_LATE60_STRICT_CONTINUITY_FORENSICS_2Y_V1"
EXPECTED_ATLAS_ROWS = 365
EXPECTED_LATE_RAW = 365
EXPECTED_ELIGIBLE_LATE = 57
EXPECTED_WAIT5_RAW = 1003
EXPECTED_WAIT5_MAX3 = 983
EXPECTED_CANDIDATE_MAX3 = 1038
EXPECTED_SELECTED_LATE = 56


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_atlas_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob(f"{strict.ATLAS_STEM}-rows.jsonl"))
    if len(paths) != 1:
        raise ValueError("strict forensics requires one frozen expiration atlas ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("expiration atlas row must be object")
            rows.append(raw)
    return tuple(rows)


def _load_late60_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-late60-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"strict forensics requires 9 LATE60 ledgers, got {len(paths)}")
    rows: list[v3.V3Trade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _metrics(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any] | None:
    value = v3._metrics(
        tuple(sorted(trades, key=lambda item: (_aware(item.entry_at), item.symbol)))
    )
    return None if value is None else asdict(value)


def _group_metrics(
    trades: tuple[v3.V3Trade, ...],
    key_fn: Any,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[v3.V3Trade]] = defaultdict(list)
    for trade in trades:
        grouped[str(key_fn(trade))].append(trade)
    return {
        key: {"trades": len(values), "metrics": _metrics(tuple(values))}
        for key, values in sorted(grouped.items())
    }


def _delay_minutes(trade: v3.V3Trade) -> int:
    original_deadline = _aware(trade.h1_deadline) - timedelta(minutes=60)
    return int((_aware(trade.entry_at) - original_deadline).total_seconds() // 60)


def _remaining_minutes(trade: v3.V3Trade) -> int:
    return int(
        (_aware(trade.h1_deadline) - _aware(trade.entry_at)).total_seconds() // 60
    )


def _mss_age_minutes(trade: v3.V3Trade) -> int:
    return int(
        (_aware(trade.entry_at) - _aware(trade.m3_mss_at)).total_seconds() // 60
    )


def _band(value: int, cuts: tuple[int, ...]) -> str:
    previous = 0
    for cut in cuts:
        if value <= cut:
            return f"{previous:02d}_{cut:02d}M"
        previous = cut + 1
    return f"{previous:02d}M_PLUS"


def _drawdown_episode(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda item: (_aware(item.exit_at), item.symbol))
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

    if worst_trough_index < 0:
        return {"drawdown_r": "0", "trades": 0}

    start = worst_peak_index + 1
    episode = tuple(ordered[start : worst_trough_index + 1])
    late = tuple(t for t in episode if t.entry_mode.startswith("LATE60_"))
    baseline = tuple(t for t in episode if not t.entry_mode.startswith("LATE60_"))
    return {
        "drawdown_r": str(worst),
        "peak_exit_at": (
            None if worst_peak_index < 0 else ordered[worst_peak_index].exit_at
        ),
        "trough_exit_at": ordered[worst_trough_index].exit_at,
        "trades": len(episode),
        "late_trades": len(late),
        "late_metrics": _metrics(late),
        "wait5_metrics": _metrics(baseline),
        "by_session": _group_metrics(episode, lambda t: t.session),
        "by_market": _group_metrics(episode, lambda t: t.symbol),
    }


def build_report(atlas_root: Path, late60_root: Path) -> dict[str, Any]:
    atlas_rows = _load_atlas_rows(atlas_root)
    if len(atlas_rows) != EXPECTED_ATLAS_ROWS:
        raise ValueError("strict forensics atlas control mismatch")

    atlas_by_key = {strict._atlas_key(row): row for row in atlas_rows}
    if len(atlas_by_key) != len(atlas_rows):
        raise ValueError("duplicate strict-forensics atlas key")

    eligible_keys = {
        key for key, row in atlas_by_key.items() if strict._strict_continuity_admitted(row)
    }
    if len(eligible_keys) != EXPECTED_ELIGIBLE_LATE:
        raise ValueError("strict forensics eligible population mismatch")

    all_trades = _load_late60_trades(late60_root)
    wait5_raw = tuple(
        trade for trade in all_trades if not trade.entry_mode.startswith("LATE60_")
    )
    late_raw = tuple(
        trade for trade in all_trades if trade.entry_mode.startswith("LATE60_")
    )
    if len(wait5_raw) != EXPECTED_WAIT5_RAW:
        raise ValueError("strict forensics WAIT5 raw control mismatch")
    if len(late_raw) != EXPECTED_LATE_RAW:
        raise ValueError("strict forensics LATE60 raw control mismatch")

    late_by_key = {strict._trade_key(trade): trade for trade in late_raw}
    admitted_late = tuple(late_by_key[key] for key in sorted(eligible_keys))
    candidate_raw = tuple(
        sorted(
            (*wait5_raw, *admitted_late),
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
    )

    wait5_max3 = v3._portfolio_max3(wait5_raw)
    candidate_max3 = v3._portfolio_max3(candidate_raw)
    if len(wait5_max3) != EXPECTED_WAIT5_MAX3:
        raise ValueError("strict forensics WAIT5 MAX3 control mismatch")
    if len(candidate_max3) != EXPECTED_CANDIDATE_MAX3:
        raise ValueError("strict forensics candidate MAX3 control mismatch")

    selected_late = tuple(
        trade for trade in candidate_max3 if trade.entry_mode.startswith("LATE60_")
    )
    if len(selected_late) != EXPECTED_SELECTED_LATE:
        raise ValueError("strict forensics selected-late control mismatch")

    candidate_keys = {strict._trade_key(item) for item in candidate_max3}
    displaced_wait5 = tuple(
        item
        for item in wait5_max3
        if strict._trade_key(item) not in candidate_keys
    )

    def atlas_value(trade: v3.V3Trade, field: str) -> Any:
        return atlas_by_key[strict._trade_key(trade)][field]

    return {
        "identity": IDENTITY,
        "diagnostic_window_role": "CONSUMED_DEVELOPMENT_ONLY",
        "atlas_rows": len(atlas_rows),
        "late60_raw": len(late_raw),
        "eligible_late_structural": len(admitted_late),
        "wait5_raw": len(wait5_raw),
        "wait5_max3": len(wait5_max3),
        "candidate_max3": len(candidate_max3),
        "selected_late": len(selected_late),
        "displaced_wait5": len(displaced_wait5),
        "selected_late_metrics": _metrics(selected_late),
        "displaced_wait5_metrics": _metrics(displaced_wait5),
        "entry_m5_state": _group_metrics(
            selected_late, lambda t: atlas_value(t, "entry_m5_state")
        ),
        "m5_state_transition": _group_metrics(
            selected_late, lambda t: atlas_value(t, "m5_state_transition")
        ),
        "any_aligned_since_deadline": _group_metrics(
            selected_late, lambda t: atlas_value(t, "any_aligned_since_deadline")
        ),
        "new_completed_m5_evidence": _group_metrics(
            selected_late, lambda t: atlas_value(t, "new_completed_m5_evidence")
        ),
        "delay_after_deadline": _group_metrics(
            selected_late,
            lambda t: _band(_delay_minutes(t), (5, 15, 30, 45, 59)),
        ),
        "remaining_lifecycle": _group_metrics(
            selected_late,
            lambda t: _band(_remaining_minutes(t), (5, 15, 30, 45, 60)),
        ),
        "mss_to_entry_age": _group_metrics(
            selected_late,
            lambda t: _band(_mss_age_minutes(t), (30, 60, 90, 120)),
        ),
        "entry_mode": _group_metrics(selected_late, lambda t: t.entry_mode),
        "ob_fvg_overlap": _group_metrics(
            selected_late,
            lambda t: "OVERLAP" if t.m1_ob_fvg_overlap else "NO_OVERLAP",
        ),
        "session": _group_metrics(selected_late, lambda t: t.session),
        "market": _group_metrics(selected_late, lambda t: t.symbol),
        "exit_reason": _group_metrics(selected_late, lambda t: t.exit_reason),
        "candidate_max_drawdown_episode": _drawdown_episode(candidate_max3),
        "outcome_aware_descriptive_only": True,
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-wait5-late60-strict-continuity-forensics-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("atlas_root", type=Path)
    parser.add_argument("late60_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.atlas_root, args.late60_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
