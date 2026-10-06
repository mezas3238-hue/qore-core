#!/usr/bin/env python3
"""Aggregate observation-only VT31 post-entry fact diagnostics across lanes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

LANES = ("r5", "r6", "r8", "consumed")


def load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected object: {path}")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payloads = {
        lane: load(args.output_root / "lanes" / lane / "normalized.json")
        for lane in LANES
    }
    fact_names = tuple(
        payloads["r5"]["diagnostics"]["geometric_facts"].keys()
    )
    facts: dict[str, Any] = {}
    candidates: list[str] = []

    for fact in fact_names:
        matched: list[dict[str, Any]] = []
        partitions: list[str] = []
        for lane in LANES:
            row = payloads[lane]["diagnostics"]["geometric_facts"][fact]
            if int(row["trade_count"]) > 0:
                partitions.append(lane)
            for item in row["matched_trades"]:
                matched.append({"partition": lane, **item})

        wins = sum(bool(item["winner"]) for item in matched)
        losses = len(matched) - wins
        already = sum(
            item["existing_cognitive_exit_authorized"] is True
            for item in matched
        )
        unhandled_losses = sum(
            not bool(item["winner"])
            and item["existing_cognitive_exit_authorized"] is not True
            for item in matched
        )
        qualifies_observation = (
            len(partitions) >= 3
            and losses >= 3
            and wins == 0
            and unhandled_losses >= 3
        )
        if qualifies_observation:
            candidates.append(fact)
        facts[fact] = {
            "trade_count": len(matched),
            "winner_count": wins,
            "loss_count": losses,
            "partition_support": partitions,
            "partition_count": len(partitions),
            "already_exit_authorized_count": already,
            "unhandled_loss_count": unhandled_losses,
            "zero_winner_cross_partition_observation": (
                qualifies_observation
            ),
            "matched_trades": matched,
        }

    result = {
        "schema": "qore.github-trader-lab.vt31-post-entry-fact-audit.aggregate.v1",
        "baseline": "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR",
        "lanes": list(LANES),
        "geometric_facts": facts,
        "zero_winner_cross_partition_observations": candidates,
        "governance": {
            "observation_only": True,
            "candidate_runtime_authority": False,
            "terminal_outcome_used_for_runtime": False,
            "new_numeric_threshold_added": False,
            "fresh_holdout_opened": False,
            "certification_claimed": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("VT31_POST_ENTRY_FACT_AUDIT " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
