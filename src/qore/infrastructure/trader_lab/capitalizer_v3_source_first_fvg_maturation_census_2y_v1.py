"""Outcome-free timing census for SOURCE_FIRST FVG maturation after MSS.

Input is the frozen nine-market FVG_MISSING atlas. No price outcomes, exits,
realized R, stop/target results, or PnL are read.

Purpose:
- quantify how long a same-side M1 FVG takes to mature after SOURCE_FIRST MSS;
- quantify remaining H1 lifecycle when that FVG confirms;
- compare same-side versus opposed FVG confirmation order;
- preserve market/session visibility without creating market-specific rules.

This module is diagnostic only and does not admit trades.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_FVG_MATURATION_CENSUS_2Y_V1"
EXPECTED_ROWS = 322
EXPECTED_SAME_SIDE_BEFORE_DEADLINE = 289
EXPECTED_OPPOSED_BEFORE_DEADLINE = 246


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-fvg-missing-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"maturation census requires 9 ledgers, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("maturation row must be object")
                rows.append(raw)
    return tuple(rows)


def _delay_bucket(minutes: int) -> str:
    if minutes <= 2:
        return "00_02M"
    if minutes <= 5:
        return "03_05M"
    if minutes <= 15:
        return "06_15M"
    if minutes <= 30:
        return "16_30M"
    return "31M_PLUS"


def _remaining_bucket(minutes: int) -> str:
    if minutes <= 5:
        return "00_05M"
    if minutes <= 15:
        return "06_15M"
    if minutes <= 30:
        return "16_30M"
    if minutes <= 45:
        return "31_45M"
    return "46M_PLUS"


def _order(
    same_at: datetime | None,
    opposed_at: datetime | None,
) -> str:
    if same_at is None:
        return "NO_SAME_SIDE_FVG"
    if opposed_at is None:
        return "SAME_SIDE_ONLY"
    if same_at < opposed_at:
        return "SAME_SIDE_FIRST"
    if opposed_at < same_at:
        return "OPPOSED_FIRST"
    return "SIMULTANEOUS"


def build_report(root: Path) -> dict[str, Any]:
    rows = _load_rows(root)
    if len(rows) != EXPECTED_ROWS:
        raise ValueError("maturation census frozen row count mismatch")

    delay: Counter[str] = Counter()
    remaining: Counter[str] = Counter()
    order: Counter[str] = Counter()
    per_session: dict[str, Counter[str]] = defaultdict(Counter)
    per_market: dict[str, Counter[str]] = defaultdict(Counter)

    same_count = 0
    opposed_count = 0
    delay_sum = 0
    remaining_sum = 0

    for row in rows:
        mss_at = _aware(str(row["source_first_mss_at"]))
        deadline = _aware(str(row["h1_deadline"]))
        same_raw = row.get("same_side_fvg_after_mss_before_deadline_at")
        opposed_raw = row.get("opposed_fvg_after_mss_before_deadline_at")
        same_at = None if same_raw is None else _aware(str(same_raw))
        opposed_at = None if opposed_raw is None else _aware(str(opposed_raw))

        relation = _order(same_at, opposed_at)
        order[relation] += 1
        session = str(row["session"])
        market = str(row["symbol"])
        per_session[session]["TOTAL"] += 1
        per_session[session][relation] += 1
        per_market[market]["TOTAL"] += 1
        per_market[market][relation] += 1

        if opposed_at is not None:
            opposed_count += 1

        if same_at is None:
            continue

        same_count += 1
        delay_minutes = int((same_at - mss_at).total_seconds() // 60)
        remaining_minutes = int((deadline - same_at).total_seconds() // 60)
        if delay_minutes < 0:
            raise ValueError("same-side FVG precedes frozen MSS")
        if remaining_minutes < 0:
            raise ValueError("same-side FVG exceeds frozen H1 deadline")

        delay[_delay_bucket(delay_minutes)] += 1
        remaining[_remaining_bucket(remaining_minutes)] += 1
        delay_sum += delay_minutes
        remaining_sum += remaining_minutes

    if same_count != EXPECTED_SAME_SIDE_BEFORE_DEADLINE:
        raise ValueError("same-side maturation control mismatch")
    if opposed_count != EXPECTED_OPPOSED_BEFORE_DEADLINE:
        raise ValueError("opposed maturation control mismatch")

    return {
        "identity": IDENTITY,
        "rows": len(rows),
        "same_side_fvg_before_deadline": same_count,
        "opposed_fvg_before_deadline": opposed_count,
        "delay_from_mss_minutes": dict(sorted(delay.items())),
        "remaining_h1_minutes": dict(sorted(remaining.items())),
        "fvg_order": dict(sorted(order.items())),
        "mean_delay_minutes": str(delay_sum / same_count),
        "mean_remaining_h1_minutes": str(remaining_sum / same_count),
        "per_session": {
            key: dict(sorted(value.items()))
            for key, value in sorted(per_session.items())
        },
        "per_market": {
            key: dict(sorted(value.items()))
            for key, value in sorted(per_market.items())
        },
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-source-first-fvg-maturation-census-2y-v1.json"
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
