#!/usr/bin/env python3
"""Fast VT31 COMP006-family adapter for the independent GitHub Trader Lab.

Consumes a prepared COMP003 ledger and applies the current subject's downstream
admission/recovery/frontier logic. It does not reconstruct M1 and it defers
Monte Carlo to the generic Trader Lab scientific engine.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_breaker_rotation_recovery_exception_frontier_v1 as recovery
import vt31_nas100_rapid_breaker_conflict_admission_frontier_v1 as rapid
import vt31_nas100_specialist_r1_candidate as specialist


def net_values(rows: list[dict[str, object]]) -> list[str]:
    return [
        format(Decimal(str(row["r_multiple"])) - specialist.FRICTION, "f")
        for row in rows
    ]


def variant_row(
    *,
    comparator: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> dict[str, Any]:
    winner = admission._winner_preservation(comparator, rows)
    return {
        "trade_count": len(rows),
        "relative_density_vs_control": (
            "0"
            if not comparator
            else format(Decimal(len(rows)) / Decimal(len(comparator)), "f")
        ),
        "metrics": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "winner_preservation": {
            "count": winner["winner_count_preservation"],
            "r": winner["winner_r_preservation"],
        },
        "temporal_blocks": specialist._block_metrics(
            rows,
            halfyear=True,
        ),
        "net_r_values": net_values(rows),
    }


def run(prepared_path: Path, lane: str) -> dict[str, Any]:
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    if prepared.get("schema") != "qore.github-trader-lab.vt31-comp003-prepared.v1":
        raise ValueError("unexpected prepared ledger schema")

    comp003 = cast(list[dict[str, object]], prepared["comp003_rows"])
    admitted = [
        row
        for row in comp003
        if not admission._is_abstained(row, rapid.ADMISSION_BASE)
    ]
    recovery_filtered = [
        row for row in admitted if not recovery._should_abstain(row)
    ]
    fvg_filtered = [
        row
        for row in recovery_filtered
        if not recovery._fvg_short_compressed_fresh_fast(row)
    ]
    comp006 = [
        row
        for row in fvg_filtered
        if not recovery._episode_breaker_bearish_compressed_bullish(row)
    ]
    variant_rows = {
        "COMP006_CONTROL": comp006,
        "COMP006_PLUS_H4_BULLISH_CONFLICT": [
            row for row in comp006 if not rapid._conflict_a(row)
        ],
        "COMP006_PLUS_FRESH_MID_NORMAL_BREAKER": [
            row for row in comp006 if not rapid._conflict_b(row)
        ],
        "COMP006_PLUS_RAPID_BREAKER_UNION": [
            row
            for row in comp006
            if not (rapid._conflict_a(row) or rapid._conflict_b(row))
        ],
    }
    return {
        "schema": "qore.github-trader-lab.normalized-replay.v2",
        "adapter": "vt31-comp006-fast-prepared-v1",
        "subject": "VT31_NAS100",
        "lane": lane,
        "control": "COMP006_CONTROL",
        "variants": {
            name: variant_row(comparator=comp006, rows=rows)
            for name, rows in variant_rows.items()
        },
        "governance": {
            "prepared_upstream_reused": True,
            "current_subject_downstream_logic_loaded": True,
            "m1_reconstructed_this_iteration": False,
            "monte_carlo_deferred_to_lab": True,
            "fresh_holdout_opened": False,
            "certification_claimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run(args.prepared, args.lane)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
