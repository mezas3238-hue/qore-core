#!/usr/bin/env python3
"""Adapter: VT31 COMP006-family report -> generic Trader Lab normalized schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    raw: dict[str, Any] = json.loads(args.input.read_text(encoding="utf-8"))
    if raw.get("schema") != "qore.vt31.nas100.rapid_breaker_conflict_admission_frontier.v1":
        raise ValueError("unexpected VT31 replay schema")
    variants: dict[str, Any] = {}
    for name, row in raw["variants"].items():
        winner = row["winner_preservation_vs_comp006"]
        variants[name] = {
            "trade_count": row["trade_count"],
            "relative_density_vs_control": row["relative_density_vs_comp006"],
            "metrics": row["stress_0_05r"],
            "monte_carlo": row["monte_carlo"],
            "winner_preservation": {
                "count": winner["winner_count_preservation"],
                "r": winner["winner_r_preservation"],
            },
            "temporal_blocks": row["halfyear_stress"],
        }

    normalized = {
        "schema": "qore.github-trader-lab.normalized-replay.v1",
        "adapter": "vt31-comp006-v1",
        "subject": "VT31_NAS100",
        "lane": args.lane,
        "control": "COMP006_CONTROL",
        "variants": variants,
        "source_governance": raw["governance"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(normalized, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
