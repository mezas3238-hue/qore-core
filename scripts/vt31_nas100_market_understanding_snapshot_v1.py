"""Compose the causal VT31_NAS100 Market Understanding Snapshot.

The snapshot is the deterministic "working memory" presented to the specialist
at a decision timestamp.  It merges:
- Market State V2,
- corrected Market Context V3,
- CIBO historical-memory/runtime-observation bridge.

No new outcomes are calculated and no trading policy is selected here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

SCHEMA = "qore.vt31.nas100.market_understanding_snapshot.v1"
BRIDGE_SCHEMA = "qore.vt31.nas100.cibo_intelligence_bridge.v1"
CONTEXT_SCHEMA = "qore.vt31.nas100.market_context_lab.v3"


def _key(row: dict[str, Any]) -> tuple[str, str]:
    timestamp = row.get("decision_at", row.get("signal_at"))
    if timestamp is None:
        raise ValueError("row missing decision/signal timestamp")
    return str(row["local_date"]), str(timestamp)


def build(bridge_path: Path, context_path: Path) -> dict[str, object]:
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    context = json.loads(context_path.read_text(encoding="utf-8"))
    if bridge.get("schema") != BRIDGE_SCHEMA:
        raise ValueError("unexpected bridge schema")
    if context.get("schema") != CONTEXT_SCHEMA:
        raise ValueError("unexpected context schema")
    if bridge.get("partition") != context.get("partition"):
        raise ValueError("partition mismatch")
    if bridge.get("research_only") is not True:
        raise ValueError("bridge governance mismatch")
    if context.get("research_only") is not True:
        raise ValueError("context governance mismatch")

    context_index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in cast(list[dict[str, Any]], context["state_matrix"]):
        key = _key(row)
        if key in context_index:
            raise ValueError(f"duplicate context key {key}")
        context_index[key] = row

    snapshots: list[dict[str, object]] = []
    missing_context = 0
    for observation in cast(
        list[dict[str, Any]],
        bridge["runtime_observations"],
    ):
        key = (str(observation["local_date"]), str(observation["decision_at"]))
        context_row = context_index.get(key)
        if context_row is None:
            missing_context += 1
            continue

        cibo_structure = cast(
            dict[str, object],
            observation["cibo_structure_state"],
        )
        cross_index = cast(
            dict[str, object],
            observation["cibo_cross_index_state"],
        )
        market_state = cast(dict[str, object], observation["market_state"])
        research_labels = cast(
            dict[str, object],
            observation["research_labels"],
        )

        stale_sequence = (
            context_row.get("reclaim_latency_bin") == "8-14"
        )
        reference_liquidity_support = (
            cibo_structure.get("last_event_family")
            == "reference-liquidity-sweep"
        )
        peer_same_support = (
            cross_index.get("state") == "both-peers-same-breach"
        )
        peer_conflict = (
            cross_index.get("state") == "both-peers-opposite-breach"
        )

        snapshots.append(
            {
                "partition": observation["partition"],
                "local_date": observation["local_date"],
                "decision_at": observation["decision_at"],
                "side": observation["side"],
                "market_state": market_state,
                "market_context": {
                    "previous_day_direction": context_row.get(
                        "previous_day_direction"
                    ),
                    "previous_day_strength": context_row.get(
                        "previous_day_strength"
                    ),
                    "previous_day_trade_alignment": context_row.get(
                        "previous_day_trade_alignment"
                    ),
                    "premarket_direction": context_row.get(
                        "premarket_direction"
                    ),
                    "premarket_strength": context_row.get(
                        "premarket_strength"
                    ),
                    "premarket_trade_alignment": context_row.get(
                        "premarket_trade_alignment"
                    ),
                    "reference_direction": context_row.get(
                        "reference_direction"
                    ),
                    "reference_strength": context_row.get(
                        "reference_strength"
                    ),
                    "reference_trade_alignment": context_row.get(
                        "reference_trade_alignment"
                    ),
                    "cash_open_direction": context_row.get(
                        "cash_open_direction"
                    ),
                    "cash_open_strength": context_row.get(
                        "cash_open_strength"
                    ),
                    "cash_open_trade_alignment": context_row.get(
                        "cash_open_trade_alignment"
                    ),
                    "reference_volatility_state": context_row.get(
                        "reference_volatility_state"
                    ),
                    "current_path_volatility_state": context_row.get(
                        "current_path_volatility_state"
                    ),
                    "decision_position_in_previous_range": context_row.get(
                        "decision_position_in_previous_range"
                    ),
                    "reference_width_vs_prior5_median": context_row.get(
                        "reference_width_vs_prior5_median"
                    ),
                    "current_path_range_vs_previous_day": context_row.get(
                        "current_path_range_vs_previous_day"
                    ),
                },
                "cibo_structure_state": cibo_structure,
                "cibo_peer_state": observation["cibo_peer_state"],
                "cibo_cross_index_state": cross_index,
                "reasoning_primitives": {
                    "sequence_stale_8_14": stale_sequence,
                    "reference_liquidity_support": (
                        reference_liquidity_support
                    ),
                    "both_peers_same_breach_support": peer_same_support,
                    "both_peers_opposite_breach_conflict": peer_conflict,
                    "support_count": int(reference_liquidity_support)
                    + int(peer_same_support),
                },
                "research_labels": research_labels,
            }
        )

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "partition": bridge["partition"],
        "research_only": True,
        "runtime_policy_selected": False,
        "candidate_frozen": False,
        "opens_new_holdout": False,
        "live_authorized": False,
        "production_authorized": False,
        "causal_contract": {
            "snapshot_contains_only_predecision_runtime_inputs": True,
            "research_labels_are_segregated_and_policy_prohibited": True,
            "historical_knowledge_remains_aggregate_only": True,
            "date_level_outcome_lookup": False,
            "future_bar_lookup": False,
        },
        "source_bindings": {
            "bridge_schema": bridge["schema"],
            "bridge_evidence": bridge["evidence_binding"],
            "context_schema": context["schema"],
            "context_evidence": context["evidence"],
        },
        "historical_knowledge": bridge["historical_knowledge"],
        "snapshot_count": len(snapshots),
        "missing_context_count": missing_context,
        "snapshots": snapshots,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.bridge, args.context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "snapshot_count": payload["snapshot_count"],
                "missing_context_count": payload["missing_context_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
