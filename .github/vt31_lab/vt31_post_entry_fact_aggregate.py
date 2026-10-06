#!/usr/bin/env python3
"""Aggregate observation-only VT31 post-entry causal diagnostics across lanes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

LANES = ("r5", "r6", "r8", "consumed")
MIN_PARTITIONS = 3
MIN_UNHANDLED_LOSSES = 3


def load(path: Path) -> dict[str, Any]:
    raw=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected object: {path}")
    return raw


def qualifies(items: list[dict[str, Any]]) -> bool:
    partitions={str(x["partition"]) for x in items}
    wins=sum(bool(x["winner"]) for x in items)
    losses=len(items)-wins
    return (
        len(partitions) >= MIN_PARTITIONS
        and losses >= MIN_UNHANDLED_LOSSES
        and wins == 0
    )


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args=parser.parse_args()
    payloads={
        lane: load(args.output_root/"lanes"/lane/"normalized.json")
        for lane in LANES
    }
    fact_names=tuple(
        payloads["r5"]["diagnostics"]["geometric_facts"].keys()
    )
    facts: dict[str, Any]={}
    fact_candidates: list[str]=[]
    for fact in fact_names:
        matched=[
            {"partition": lane, **item}
            for lane in LANES
            for item in payloads[lane]["diagnostics"][
                "geometric_facts"
            ][fact]["matched_trades"]
        ]
        unhandled=[
            x for x in matched
            if x["existing_cognitive_exit_authorized"] is not True
        ]
        good=qualifies(unhandled)
        if good:
            fact_candidates.append(fact)
        facts[fact]={
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
            "zero_winner_cross_partition_observation": good,
            "matched_trades": matched,
        }

    keys=sorted({
        key
        for lane in LANES
        for key in payloads[lane]["diagnostics"][
            "single_categorical_conjunctions"
        ]
    })
    conjunctions: dict[str, Any]={}
    candidates: list[str]=[]
    for key in keys:
        matched=[
            {"partition": lane, **item}
            for lane in LANES
            for item in payloads[lane]["diagnostics"][
                "single_categorical_conjunctions"
            ].get(key, {}).get("matched_trades", [])
        ]
        actionable=[
            x for x in matched
            if x["existing_cognitive_exit_authorized"] is not True
        ]
        good=qualifies(actionable)
        if good:
            candidates.append(key)
        conjunctions[key]={
            "actionable_trade_count": len(actionable),
            "winner_count": sum(bool(x["winner"]) for x in actionable),
            "loss_count": sum(not bool(x["winner"]) for x in actionable),
            "partition_support": sorted(
                {str(x["partition"]) for x in actionable}
            ),
            "zero_winner_cross_partition_observation": good,
            "matched_trades": actionable,
        }

    result={
        "schema": (
            "qore.github-trader-lab."
            "vt31-post-entry-fact-audit.aggregate.v3"
        ),
        "baseline": "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR",
        "lanes": list(LANES),
        "geometric_facts": facts,
        "zero_winner_cross_partition_observations": fact_candidates,
        "predeclared_single_categorical_scan": {
            "minimum_partition_support": MIN_PARTITIONS,
            "minimum_unhandled_losses": MIN_UNHANDLED_LOSSES,
            "maximum_categorical_dimensions_per_scan": 1,
            "all_causal_events_scanned": True,
            "numeric_threshold_search_used": False,
            "conjunctions": conjunctions,
            "zero_winner_cross_partition_conjunctions": sorted(candidates),
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
        json.dumps(result, indent=2, sort_keys=True)+"\n",
        encoding="utf-8",
    )
    print(
        "VT31_POST_ENTRY_FACT_AUDIT "
        + json.dumps(
            {
                "schema": result["schema"],
                "zero_winner_cross_partition_observations": fact_candidates,
                "zero_winner_cross_partition_conjunctions": sorted(candidates),
                "governance": result["governance"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
