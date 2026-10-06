#!/usr/bin/env python3
"""Aggregate observation-only VT31 post-entry causal diagnostics across lanes.

Predeclared scan: one geometric fact crossed with exactly one existing
categorical state. No numeric search and no multi-field conjunction search.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

LANES = ("r5", "r6", "r8", "consumed")
CATEGORICAL_FIELDS = (
    "side",
    "entry_family",
    "current_reasoning_action",
    "h4_state",
    "h1_state",
    "m15_state",
    "management_context",
    "protection_urgency",
    "destination_state",
    "reclaim_bucket",
    "last_causal_event_family",
    "last_causal_event_source",
)
MIN_PARTITIONS = 3
MIN_UNHANDLED_LOSSES = 3


def load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected object: {path}")
    return raw


def qualifies(items: list[dict[str, Any]]) -> bool:
    partitions = {str(item["partition"]) for item in items}
    wins = sum(bool(item["winner"]) for item in items)
    losses = len(items) - wins
    return (
        len(partitions) >= MIN_PARTITIONS
        and losses >= MIN_UNHANDLED_LOSSES
        and wins == 0
    )


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
    fact_candidates: list[str] = []
    for fact in fact_names:
        matched: list[dict[str, Any]] = []
        for lane in LANES:
            row = payloads[lane]["diagnostics"]["geometric_facts"][fact]
            matched.extend(
                {"partition": lane, **item}
                for item in row["matched_trades"]
            )
        unhandled = [
            item
            for item in matched
            if item["existing_cognitive_exit_authorized"] is not True
        ]
        fact_qualifies = qualifies(unhandled)
        if fact_qualifies:
            fact_candidates.append(fact)
        facts[fact] = {
            "trade_count": len(matched),
            "winner_count": sum(bool(x["winner"]) for x in matched),
            "loss_count": sum(not bool(x["winner"]) for x in matched),
            "already_exit_authorized_count": sum(
                x["existing_cognitive_exit_authorized"] is True
                for x in matched
            ),
            "unhandled_trade_count": len(unhandled),
            "unhandled_winner_count": sum(
                bool(x["winner"]) for x in unhandled
            ),
            "unhandled_loss_count": sum(
                not bool(x["winner"]) for x in unhandled
            ),
            "unhandled_partition_support": sorted(
                {str(x["partition"]) for x in unhandled}
            ),
            "zero_winner_cross_partition_observation": fact_qualifies,
            "matched_trades": matched,
        }

    conjunctions: dict[str, Any] = {}
    conjunction_candidates: list[str] = []
    for fact, row in sorted(facts.items()):
        matched = row["matched_trades"]
        for field in CATEGORICAL_FIELDS:
            for value in sorted({str(x.get(field)) for x in matched}):
                actionable = [
                    x for x in matched
                    if str(x.get(field)) == value
                    and x["existing_cognitive_exit_authorized"] is not True
                ]
                if not actionable:
                    continue
                key = f"{fact} && {field}={value}"
                good = qualifies(actionable)
                if good:
                    conjunction_candidates.append(key)
                conjunctions[key] = {
                    "geometric_fact": fact,
                    "categorical_field": field,
                    "categorical_value": value,
                    "actionable_trade_count": len(actionable),
                    "winner_count": sum(bool(x["winner"]) for x in actionable),
                    "loss_count": sum(not bool(x["winner"]) for x in actionable),
                    "partition_support": sorted(
                        {str(x["partition"]) for x in actionable}
                    ),
                    "zero_winner_cross_partition_observation": good,
                    "matched_trades": actionable,
                }

    result = {
        "schema": (
            "qore.github-trader-lab."
            "vt31-post-entry-fact-audit.aggregate.v2"
        ),
        "baseline": "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR",
        "lanes": list(LANES),
        "geometric_facts": facts,
        "zero_winner_cross_partition_observations": fact_candidates,
        "predeclared_single_categorical_scan": {
            "categorical_fields": list(CATEGORICAL_FIELDS),
            "minimum_partition_support": MIN_PARTITIONS,
            "minimum_unhandled_losses": MIN_UNHANDLED_LOSSES,
            "maximum_categorical_dimensions_per_scan": 1,
            "numeric_threshold_search_used": False,
            "conjunctions": conjunctions,
            "zero_winner_cross_partition_conjunctions": (
                sorted(conjunction_candidates)
            ),
        },
        "governance": {
            "observation_only": True,
            "candidate_runtime_authority": False,
            "terminal_outcome_used_for_runtime": False,
            "new_numeric_threshold_added": False,
            "multi_categorical_search_used": False,
            "fresh_holdout_opened": False,
            "certification_claimed": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "VT31_POST_ENTRY_FACT_AUDIT "
        + json.dumps(
            {
                "schema": result["schema"],
                "zero_winner_cross_partition_observations": fact_candidates,
                "zero_winner_cross_partition_conjunctions": sorted(
                    conjunction_candidates
                ),
                "governance": result["governance"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
