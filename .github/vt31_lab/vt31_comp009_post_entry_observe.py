#!/usr/bin/env python3
"""Observation-only VT31 post-entry market-fact audit adapter."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_specialist_r1_candidate as specialist

CONTROL = "COMP009_CONTROL"
FACTS = (
    "closed_back_through_structural_level",
    "closed_through_entry_zone_against_thesis",
    "closed_beyond_adverse_reference_boundary",
)


def d(value: object) -> Decimal:
    return Decimal(str(value))


def trade_rows(rows: list[dict[str, Any]]) -> list[dict[str, object]]:
    return [
        {
            "signal_at": row["signal_at"],
            "local_date": row["local_date"],
            "r_multiple": row["control_r_multiple"],
        }
        for row in rows
    ]


def fact_report(
    rows: list[dict[str, Any]],
    fact: str,
) -> dict[str, Any]:
    matched: list[dict[str, Any]] = []
    for row in rows:
        events = [
            cast(dict[str, Any], event)
            for event in row["observations"]
            if bool(cast(dict[str, Any], event).get(fact))
        ]
        if not events:
            continue
        first = events[0]
        stressed = d(row["control_r_multiple"]) - specialist.FRICTION
        matched.append(
            {
                "signal_at": row["signal_at"],
                "local_date": row["local_date"],
                "side": row["side"],
                "entry_family": row["entry_family"],
                "control_r_multiple": row["control_r_multiple"],
                "control_stressed_r": format(stressed, "f"),
                "event_count": len(events),
                "first_observation_at": first["observation_at"],
                "first_current_open_r": first.get("current_open_r"),
                "first_next_m1_open_r": first.get("next_m1_open_r"),
                "existing_cognitive_exit_authorized": first.get(
                    "cognitive_exit_authorized"
                ),
                "current_reasoning_action": first.get(
                    "current_reasoning_action"
                ),
                "h4_state": first.get("h4_state"),
                "h1_state": first.get("h1_state"),
                "m15_state": first.get("m15_state"),
                "management_context": first.get("management_context"),
                "destination_state": first.get("destination_state"),
                "reclaim_bucket": first.get("reclaim_bucket"),
                "last_causal_event_family": first.get(
                    "last_causal_event_family"
                ),
                "last_causal_event_source": first.get(
                    "last_causal_event_source"
                ),
                "winner": stressed > 0,
            }
        )
    return {
        "fact": fact,
        "trade_count": len(matched),
        "winner_count": sum(bool(row["winner"]) for row in matched),
        "loss_count": sum(not bool(row["winner"]) for row in matched),
        "already_exit_authorized_count": sum(
            row["existing_cognitive_exit_authorized"] is True
            for row in matched
        ),
        "side_counts": dict(
            sorted(Counter(str(row["side"]) for row in matched).items())
        ),
        "entry_family_counts": dict(
            sorted(
                Counter(str(row["entry_family"]) for row in matched).items()
            )
        ),
        "matched_trades": matched,
    }


def categorical_observation(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for row in rows:
        stressed = d(row["control_r_multiple"]) - specialist.FRICTION
        seen: set[tuple[str, str]] = set()
        for event in row["observations"]:
            event = cast(dict[str, Any], event)
            values = {
                "h4_state": event.get("h4_state"),
                "h1_state": event.get("h1_state"),
                "m15_state": event.get("m15_state"),
                "management_context": event.get("management_context"),
                "destination_state": event.get("destination_state"),
                "protection_urgency": event.get("protection_urgency"),
                "reclaim_bucket": event.get("reclaim_bucket"),
                "last_causal_event_family": event.get(
                    "last_causal_event_family"
                ),
                "last_causal_event_source": event.get(
                    "last_causal_event_source"
                ),
            }
            for key, value in values.items():
                token = (key, str(value))
                if token in seen:
                    continue
                seen.add(token)
                records.append(
                    {
                        "field": key,
                        "value": str(value),
                        "signal_at": row["signal_at"],
                        "side": row["side"],
                        "entry_family": row["entry_family"],
                        "winner": stressed > 0,
                        "control_stressed_r": format(stressed, "f"),
                    }
                )
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(
            (record["field"], record["value"]),
            [],
        ).append(record)
    return {
        f"{key}={value}": {
            "trade_count": len(items),
            "winner_count": sum(bool(item["winner"]) for item in items),
            "loss_count": sum(not bool(item["winner"]) for item in items),
        }
        for (key, value), items in sorted(grouped.items())
    }


def run(prepared_path: Path, lane: str) -> dict[str, Any]:
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    if (
        prepared.get("schema")
        != "qore.github-trader-lab.vt31-comp009-post-entry-facts.v1"
    ):
        raise ValueError("unexpected VT31 post-entry prepared ledger schema")
    rows = cast(list[dict[str, Any]], prepared["rows"])
    metrics_rows = trade_rows(rows)
    metrics = specialist._metrics(
        metrics_rows,
        friction=specialist.FRICTION,
    )
    net_r_values = [
        format(
            d(row["control_r_multiple"]) - specialist.FRICTION,
            "f",
        )
        for row in rows
    ]
    return {
        "schema": "qore.github-trader-lab.normalized-replay.v2",
        "adapter": "vt31-comp009-post-entry-fact-observation-v1",
        "subject": "VT31_NAS100",
        "lane": lane,
        "control": CONTROL,
        "variants": {
            CONTROL: {
                "trade_count": len(rows),
                "relative_density_vs_control": "1",
                "metrics": metrics,
                "winner_preservation": {
                    "count": "1",
                    "r": "1",
                },
                "temporal_blocks": specialist._block_metrics(
                    metrics_rows,
                    halfyear=True,
                ),
                "net_r_values": net_r_values,
            }
        },
        "diagnostics": {
            "geometric_facts": {
                fact: fact_report(rows, fact)
                for fact in FACTS
            },
            "categorical_single_states": categorical_observation(rows),
            "observation_count": sum(
                len(row["observations"]) for row in rows
            ),
        },
        "governance": {
            "observation_only": True,
            "policy_promoted": False,
            "prepared_upstream_reused": True,
            "pure_edge_research": True,
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
