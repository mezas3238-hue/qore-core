"""Consumed-window development A/B for strict causal LATE60 continuity.

Frozen before reading this composite rule's economics:
- keep SOURCE_FIRST + WAIT5 unchanged through the original H1 deadline;
- only a NORMAL_FILL_MISSING setup may carry beyond the deadline;
- deadline M5 state must be ALIGNED with the original side;
- no new H1 sweep may occur before the late fill;
- no completed M5 OPPOSED state may occur during the carry;
- same original FVG, entry mode, stop, target and +60 minute hard cap.

Admission uses only the outcome-free hypothesis-expiration atlas. This consumed 2Y
window is development-only. Prior component dimensions have already been described
economically, so no result from this module may be promoted without fresh holdout.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)

IDENTITY = "QORE_CAPITALIZER_V3_WAIT5_LATE60_STRICT_CONTINUITY_2Y_V1"
EXPECTED_ATLAS_ROWS = 365
EXPECTED_LATE_RAW = 365
EXPECTED_ELIGIBLE_LATE = 57
EXPECTED_WAIT5_RAW = 1003
EXPECTED_WAIT5_MAX3 = 983

ATLAS_STEM = (
    "capitalizer-nine-market-v3-wait5-late60-"
    "hypothesis-expiration-atlas-2y-v1"
)


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_atlas_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob(f"{ATLAS_STEM}-rows.jsonl"))
    if len(paths) != 1:
        raise ValueError("strict continuity requires one frozen expiration atlas ledger")
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
        raise ValueError(f"strict continuity requires 9 LATE60 ledgers, got {len(paths)}")
    rows: list[v3.V3Trade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _trade_key(trade: v3.V3Trade) -> tuple[str, str, str, str, str]:
    return (
        trade.symbol,
        trade.session,
        trade.operating_date,
        trade.side,
        trade.entry_at,
    )


def _atlas_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["symbol"]),
        str(row["session"]),
        str(row["operating_date"]),
        str(row["side"]),
        str(row["entry_at"]),
    )


def _strict_continuity_admitted(row: dict[str, Any]) -> bool:
    return (
        row["continuity_state"] == "NO_NEW_H1_SWEEP"
        and row["deadline_m5_state"] == "ALIGNED"
        and not bool(row["any_opposed_since_deadline"])
    )


def _metrics(trades: tuple[v3.V3Trade, ...]) -> dict[str, Any]:
    ordered = tuple(sorted(trades, key=lambda item: (_aware(item.entry_at), item.symbol)))
    metrics = v3._metrics(ordered)
    if metrics is None:
        raise ValueError("strict continuity produced empty metrics")
    return asdict(metrics)


def _decimal(value: Any) -> Decimal:
    if value is None:
        raise ValueError("strict continuity metric unexpectedly null")
    return Decimal(str(value))


def build_report(
    atlas_root: Path,
    late60_root: Path,
) -> dict[str, Any]:
    atlas_rows = _load_atlas_rows(atlas_root)
    if len(atlas_rows) != EXPECTED_ATLAS_ROWS:
        raise ValueError("expiration atlas control mismatch")

    atlas_by_key = {_atlas_key(row): row for row in atlas_rows}
    if len(atlas_by_key) != len(atlas_rows):
        raise ValueError("duplicate expiration atlas key")

    eligible_keys = {
        key for key, row in atlas_by_key.items() if _strict_continuity_admitted(row)
    }
    if len(eligible_keys) != EXPECTED_ELIGIBLE_LATE:
        raise ValueError("strict continuity structural population mismatch")

    all_trades = _load_late60_trades(late60_root)
    wait5_raw = tuple(
        trade for trade in all_trades if not trade.entry_mode.startswith("LATE60_")
    )
    late_raw = tuple(
        trade for trade in all_trades if trade.entry_mode.startswith("LATE60_")
    )
    if len(wait5_raw) != EXPECTED_WAIT5_RAW:
        raise ValueError("WAIT5 raw control mismatch")
    if len(late_raw) != EXPECTED_LATE_RAW:
        raise ValueError("LATE60 raw control mismatch")

    late_by_key = {_trade_key(trade): trade for trade in late_raw}
    if len(late_by_key) != len(late_raw):
        raise ValueError("duplicate LATE60 trade key")
    if set(late_by_key) != set(atlas_by_key):
        raise ValueError("LATE60 and expiration atlas provenance mismatch")

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
        raise ValueError("WAIT5 MAX3 control mismatch")

    selected_late = tuple(
        trade for trade in candidate_max3 if trade.entry_mode.startswith("LATE60_")
    )
    selected_wait5 = tuple(
        trade for trade in candidate_max3 if not trade.entry_mode.startswith("LATE60_")
    )

    baseline_metrics = _metrics(wait5_max3)
    candidate_metrics = _metrics(candidate_max3)

    return {
        "identity": IDENTITY,
        "diagnostic_window_role": "CONSUMED_DEVELOPMENT_ONLY",
        "variant_only_change": (
            "LATE60_REQUIRES_DEADLINE_M5_ALIGNED__NO_NEW_H1_SWEEP__"
            "NO_OPPOSED_M5_DURING_CARRY"
        ),
        "atlas_rows": len(atlas_rows),
        "late60_raw": len(late_raw),
        "eligible_late_structural": len(admitted_late),
        "wait5_raw": len(wait5_raw),
        "candidate_raw": len(candidate_raw),
        "wait5_max3": len(wait5_max3),
        "candidate_max3": len(candidate_max3),
        "candidate_selected_late": len(selected_late),
        "candidate_selected_wait5": len(selected_wait5),
        "wait5_metrics": baseline_metrics,
        "candidate_metrics": candidate_metrics,
        "delta_vs_wait5": {
            "trades": len(candidate_max3) - len(wait5_max3),
            "profit_factor": str(
                _decimal(candidate_metrics["profit_factor"])
                - _decimal(baseline_metrics["profit_factor"])
            ),
            "total_r": str(
                _decimal(candidate_metrics["total_r"])
                - _decimal(baseline_metrics["total_r"])
            ),
            "mean_r": str(
                _decimal(candidate_metrics["mean_r"])
                - _decimal(baseline_metrics["mean_r"])
            ),
            "max_drawdown_r": str(
                _decimal(candidate_metrics["max_drawdown_r"])
                - _decimal(baseline_metrics["max_drawdown_r"])
            ),
            "losing_streak": (
                int(candidate_metrics["max_losing_streak"])
                - int(baseline_metrics["max_losing_streak"])
            ),
        },
        "same_source_first_mss_preserved": True,
        "same_fvg_preserved": True,
        "same_fill_modes_preserved": True,
        "same_stop_preserved": True,
        "same_target_preserved": True,
        "same_wait5_preserved": True,
        "same_late60_hard_cap_preserved": True,
        "admission_source": (
            "QORE_CAPITALIZER_V3_WAIT5_LATE60_HYPOTHESIS_EXPIRATION_ATLAS_2Y_V1"
        ),
        "outcome_used_for_admission": False,
        "component_dimensions_previously_outcome_described": True,
        "composite_rule_economics_previously_unread": True,
        "fresh_holdout_required": True,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": True,
        "strategy_mutated": True,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-wait5-late60-strict-continuity-2y-v1.json"
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
