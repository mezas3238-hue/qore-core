"""Freeze and decompose the 1R Capitalizer laboratory candidate.

The source population is the frozen MAX_RECOVERY_FINAL universe. The source
target-sensitivity run already varied only the fixed target multiple. This
module does not search targets again: it selects the predeclared 1.00R
development candidate and measures its stability on the same consumed 2Y
laboratory window.

No trade admission, entry, stop, H1 deadline or MAX3 rule changes here.
No fresh-holdout claim is made.
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
    capitalizer_max_recovery_target_sensitivity_2y_v1 as sensitivity,
)

IDENTITY = "QORE_CAPITALIZER_MAX_RECOVERY_TARGET1_STABILITY_2Y_V1"
CANDIDATE_TARGET_R = Decimal("1.00")
SOURCE_TARGET_RUN_ID = 35941710028
SOURCE_TARGET_SHA = "00dcd48d702d6a0c1c45abb69a3714a8ac66497b"
EXPECTED_RAW_TRADES = 963
EXPECTED_MAX3_TRADES = 948
EXPECTED_PF = Decimal("2.608801712095744666571338155")
EXPECTED_TOTAL_R = Decimal("444.4738316646191578343575863")
EXPECTED_DD_R = Decimal("8.671360188479779752380440576")
EXPECTED_LS = 5

BASELINE_2R_PF = Decimal("1.466020472120789368123727041")
BASELINE_2R_TOTAL_R = Decimal("153.9927998412621697329314877")
BASELINE_2R_DD_R = Decimal("12.93584837435268644582248142")
BASELINE_2R_LS = 7


def _metrics(
    trades: tuple[sensitivity.TargetOutcome, ...],
) -> dict[str, Any]:
    if not trades:
        raise ValueError("stability slice must contain at least one trade")
    return sensitivity._metrics(trades)


def _quarter(value: str) -> str:
    stamp = datetime.fromisoformat(value)
    quarter = ((stamp.month - 1) // 3) + 1
    return f"{stamp.year}-Q{quarter}"


def _group_metrics(
    trades: tuple[sensitivity.TargetOutcome, ...],
    *,
    key_name: str,
    key_fn: Any,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[sensitivity.TargetOutcome]] = defaultdict(list)
    for trade in trades:
        grouped[str(key_fn(trade))].append(trade)

    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        ordered = tuple(
            sorted(
                grouped[key],
                key=lambda item: (
                    datetime.fromisoformat(item.entry_at),
                    item.symbol,
                ),
            )
        )
        rows.append(
            {
                key_name: key,
                "trades": len(ordered),
                "metrics": _metrics(ordered),
            }
        )
    return rows


def _ordinal_rows(
    trades: tuple[sensitivity.TargetOutcome, ...],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[sensitivity.TargetOutcome]] = defaultdict(
        list
    )
    for trade in trades:
        grouped[(trade.operating_date, trade.session)].append(trade)

    ordinals: dict[int, list[sensitivity.TargetOutcome]] = defaultdict(list)
    for values in grouped.values():
        ordered = sorted(
            values,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
        for index, trade in enumerate(ordered, start=1):
            ordinals[index].append(trade)

    rows: list[dict[str, Any]] = []
    for ordinal in sorted(ordinals):
        selected = tuple(
            sorted(
                ordinals[ordinal],
                key=lambda item: (
                    datetime.fromisoformat(item.entry_at),
                    item.symbol,
                ),
            )
        )
        rows.append(
            {
                "ordinal": ordinal,
                "trades": len(selected),
                "metrics": _metrics(selected),
            }
        )
    return rows


def _reproduce_candidate(
    root: Path,
) -> tuple[
    tuple[sensitivity.TargetOutcome, ...],
    tuple[sensitivity.TargetOutcome, ...],
    dict[str, Any],
]:
    outcomes = sensitivity._load_outcomes(root)
    raw = tuple(
        item
        for item in outcomes
        if Decimal(item.target_r) == CANDIDATE_TARGET_R
    )
    selected = sensitivity._max3(raw)
    metrics = _metrics(selected)

    if len(raw) != EXPECTED_RAW_TRADES:
        raise ValueError("1R raw control mismatch")
    if len(selected) != EXPECTED_MAX3_TRADES:
        raise ValueError("1R MAX3 control mismatch")
    if Decimal(str(metrics["profit_factor"])) != EXPECTED_PF:
        raise ValueError("1R PF control mismatch")
    if Decimal(str(metrics["total_r"])) != EXPECTED_TOTAL_R:
        raise ValueError("1R total-R control mismatch")
    if Decimal(str(metrics["max_drawdown_r"])) != EXPECTED_DD_R:
        raise ValueError("1R DD control mismatch")
    if int(metrics["max_losing_streak"]) != EXPECTED_LS:
        raise ValueError("1R losing-streak control mismatch")
    return raw, selected, metrics


def build_report(
    root: Path,
) -> tuple[dict[str, Any], tuple[sensitivity.TargetOutcome, ...]]:
    raw, selected, metrics = _reproduce_candidate(root)

    by_market = _group_metrics(
        selected,
        key_name="market",
        key_fn=lambda trade: trade.symbol,
    )
    by_session = _group_metrics(
        selected,
        key_name="session",
        key_fn=lambda trade: trade.session,
    )
    by_quarter = _group_metrics(
        selected,
        key_name="quarter",
        key_fn=lambda trade: _quarter(trade.entry_at),
    )
    by_provenance = _group_metrics(
        selected,
        key_name="provenance",
        key_fn=lambda trade: trade.provenance,
    )
    by_ordinal = _ordinal_rows(selected)

    market_pfs = [
        Decimal(str(row["metrics"]["profit_factor"])) for row in by_market
    ]
    session_pfs = [
        Decimal(str(row["metrics"]["profit_factor"])) for row in by_session
    ]
    quarter_pfs = [
        Decimal(str(row["metrics"]["profit_factor"])) for row in by_quarter
    ]

    exit_reasons = dict(Counter(item.exit_reason for item in selected))
    ambiguity_count = sum(
        1 for item in selected if item.same_minute_stop_target_ambiguity
    )

    report = {
        "identity": IDENTITY,
        "candidate_target_r": str(CANDIDATE_TARGET_R),
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "raw_trades": len(raw),
        "max3_trades": len(selected),
        "metrics": metrics,
        "baseline_2r": {
            "profit_factor": str(BASELINE_2R_PF),
            "total_r": str(BASELINE_2R_TOTAL_R),
            "max_drawdown_r": str(BASELINE_2R_DD_R),
            "max_losing_streak": BASELINE_2R_LS,
        },
        "delta_vs_2r": {
            "profit_factor": str(EXPECTED_PF - BASELINE_2R_PF),
            "total_r": str(EXPECTED_TOTAL_R - BASELINE_2R_TOTAL_R),
            "max_drawdown_r": str(EXPECTED_DD_R - BASELINE_2R_DD_R),
            "max_losing_streak": EXPECTED_LS - BASELINE_2R_LS,
        },
        "by_market": by_market,
        "by_session": by_session,
        "by_quarter": by_quarter,
        "by_provenance": by_provenance,
        "by_ordinal": by_ordinal,
        "market_count": len(by_market),
        "session_count": len(by_session),
        "quarter_count": len(by_quarter),
        "all_markets_pf_gt_one": all(value > 1 for value in market_pfs),
        "all_sessions_pf_gt_one": all(value > 1 for value in session_pfs),
        "all_quarters_pf_gt_one": all(value > 1 for value in quarter_pfs),
        "minimum_market_pf": str(min(market_pfs)),
        "minimum_session_pf": str(min(session_pfs)),
        "minimum_quarter_pf": str(min(quarter_pfs)),
        "exit_reasons": exit_reasons,
        "same_minute_stop_target_ambiguity": ambiguity_count,
        "selection_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "h1_deadline_changed": False,
        "max3_changed": False,
        "only_target_r_frozen": True,
        "target_reoptimization_allowed": False,
        "selected_from_consumed_grid": True,
        "development_window_role": "CONSUMED_LABORATORY",
        "fresh_holdout_claimed": False,
        "fresh_holdout_required_after_architecture_freeze": True,
        "outcome_used_for_admission": False,
        "automatic_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, selected


def write_report(
    report: dict[str, Any],
    trades: tuple[sensitivity.TargetOutcome, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-max-recovery-target1-stability-2y-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-max-recovery-target1-stability-2y-v1-trades.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, trades = build_report(args.input_root)
    write_report(report, trades, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
