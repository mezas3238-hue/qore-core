"""Forensics on the permanently consumed VT31_NAS100_R5 final holdout.

This module is diagnostic only. It replays the frozen candidate on the already
consumed 2022-07-18..2024-07-18 evidence and attributes expectancy / drawdown
by causal fields already present before or at the trade decision.

Nothing in this file can certify a trader or reopen the holdout as fresh.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_r5_certification_candidate as candidate

SCHEMA = "qore.vt31.nas100.r5.consumed_holdout_forensics.v1"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return candidate.engine._capital_metrics(rows)


def _group(
    rows: list[dict[str, object]],
    field: str,
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(field))].append(row)
    return {
        key: _metrics(items)
        for key, items in sorted(grouped.items())
    }


def _quarter(local_day: date) -> str:
    quarter = (local_day.month - 1) // 3 + 1
    return f"{local_day.year}-Q{quarter}"


def _month(local_day: date) -> str:
    return f"{local_day.year:04d}-{local_day.month:02d}"


def _time_groups(
    rows: list[dict[str, object]],
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
]:
    months: dict[str, list[dict[str, object]]] = defaultdict(list)
    quarters: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        months[_month(local_day)].append(row)
        quarters[_quarter(local_day)].append(row)
    return (
        {key: _metrics(items) for key, items in sorted(months.items())},
        {key: _metrics(items) for key, items in sorted(quarters.items())},
    )


def _drawdown_episode(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    equity = Decimal(0)
    peak = Decimal(0)
    peak_index = -1
    max_dd = Decimal(0)
    trough_index = -1
    dd_start_index = -1

    for index, row in enumerate(rows):
        equity += _d(row["capital_weighted_net_r"])
        if equity > peak:
            peak = equity
            peak_index = index
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            trough_index = index
            dd_start_index = peak_index + 1

    if trough_index < 0:
        return {
            "max_drawdown_r": "0",
            "trade_count": 0,
            "rows": [],
        }

    start = max(dd_start_index, 0)
    episode = rows[start : trough_index + 1]
    tier_counts: dict[str, int] = defaultdict(int)
    side_counts: dict[str, int] = defaultdict(int)
    entry_family_counts: dict[str, int] = defaultdict(int)
    for row in episode:
        tier_counts[str(row.get("tier"))] += 1
        side_counts[str(row.get("side"))] += 1
        entry_family_counts[str(row.get("entry_family"))] += 1

    return {
        "max_drawdown_r": format(max_dd, "f"),
        "start_signal_at": (
            None if not episode else episode[0].get("signal_at")
        ),
        "end_signal_at": (
            None if not episode else episode[-1].get("signal_at")
        ),
        "trade_count": len(episode),
        "metrics": _metrics(episode),
        "tier_counts": dict(sorted(tier_counts.items())),
        "side_counts": dict(sorted(side_counts.items())),
        "entry_family_counts": dict(sorted(entry_family_counts.items())),
        "rows": episode,
    }


def _loss_runs(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    runs: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    for row in rows:
        if _d(row["capital_weighted_net_r"]) < 0:
            current.append(row)
            continue
        if current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)

    ranked = sorted(
        runs,
        key=lambda items: (
            sum((_d(row["capital_weighted_net_r"]) for row in items), Decimal(0)),
            -len(items),
        ),
    )
    result: list[dict[str, object]] = []
    for items in ranked[:10]:
        result.append(
            {
                "trade_count": len(items),
                "total_r": format(
                    sum(
                        (
                            _d(row["capital_weighted_net_r"])
                            for row in items
                        ),
                        Decimal(0),
                    ),
                    "f",
                ),
                "start_signal_at": items[0].get("signal_at"),
                "end_signal_at": items[-1].get("signal_at"),
                "tier_counts": {
                    tier: sum(
                        1 for row in items if str(row.get("tier")) == tier
                    )
                    for tier in sorted(
                        {str(row.get("tier")) for row in items}
                    )
                },
                "side_counts": {
                    side: sum(
                        1 for row in items if str(row.get("side")) == side
                    )
                    for side in sorted(
                        {str(row.get("side")) for row in items}
                    )
                },
            }
        )
    return result


def analyze(evidence_path: Path) -> dict[str, object]:
    replay = candidate.replay(evidence_path)
    result = cast(dict[str, object], replay["result"])
    rows = cast(list[dict[str, object]], result["trade_rows"])
    rows.sort(key=lambda row: cast(str, row["signal_at"]))

    months, quarters = _time_groups(rows)
    dimensions = (
        "tier",
        "side",
        "entry_family",
        "exit_reason",
        "requested_risk_r",
        "first_tier",
        "first_exit_reason",
        "rearm_quality_score",
        "rearm_risk_class",
        "rearm_management_mode",
    )
    by_dimension = {
        field: _group(rows, field)
        for field in dimensions
        if any(field in row for row in rows)
    }

    year1 = [
        row
        for row in rows
        if date.fromisoformat(cast(str, row["local_date"]))
        < date(2023, 7, 18)
    ]
    year2 = [
        row
        for row in rows
        if date.fromisoformat(cast(str, row["local_date"]))
        >= date(2023, 7, 18)
    ]

    return {
        "schema": SCHEMA,
        "candidate_id": candidate.CANDIDATE_ID,
        "holdout_id": candidate.FINAL_HOLDOUT_ID,
        "holdout_status": "PERMANENTLY_CONSUMED_FOR_FORENSICS",
        "fresh_reuse_allowed": False,
        "overall": _metrics(rows),
        "year_blocks": {
            "year1": _metrics(year1),
            "year2": _metrics(year2),
        },
        "by_dimension": by_dimension,
        "by_month": months,
        "by_quarter": quarters,
        "max_drawdown_episode": _drawdown_episode(rows),
        "worst_loss_runs": _loss_runs(rows),
        "governance": {
            "diagnostic_only": True,
            "uses_consumed_holdout": True,
            "may_retune_against_this_interval_for_development": True,
            "may_call_interval_fresh_again": False,
            "may_certify_on_this_interval_again": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = analyze(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "overall": payload["overall"],
                "year_blocks": payload["year_blocks"],
                "by_dimension": payload["by_dimension"],
                "by_quarter": payload["by_quarter"],
                "max_drawdown_episode": payload[
                    "max_drawdown_episode"
                ],
                "worst_loss_runs": payload["worst_loss_runs"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
