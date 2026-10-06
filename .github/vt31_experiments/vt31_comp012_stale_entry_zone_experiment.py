#!/usr/bin/env python3
"""VT31 Comparator-012 STALE entry-zone failure experiment.

Runs only on the reusable Comparator-009 post-entry causal ledger.
The decision uses closed-M1 causal facts; execution is at the next M1 open.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_specialist_r1_candidate as specialist

CONTROL = "COMP009_CONTROL"
CANDIDATE = "COMP012_STALE_ENTRY_ZONE_FAILURE_EXIT"
FRICTION = specialist.FRICTION


def d(value: object) -> Decimal:
    return Decimal(str(value))


def terminal_rows(
    prepared_rows: list[dict[str, Any]],
    *,
    candidate: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    changed: list[dict[str, object]] = []
    for source in prepared_rows:
        control_r = d(source["control_r_multiple"])
        result_r = control_r
        action: dict[str, object] | None = None
        if candidate:
            for raw in cast(list[dict[str, Any]], source["observations"]):
                if raw.get("closed_through_entry_zone_against_thesis") is not True:
                    continue
                if str(raw.get("reclaim_bucket")) != "STALE_8_14M":
                    continue
                if raw.get("cognitive_exit_authorized") is True:
                    continue
                next_open = raw.get("next_m1_open_r")
                if next_open is None:
                    continue
                result_r = d(next_open)
                action = {
                    "signal_at": source["signal_at"],
                    "local_date": source["local_date"],
                    "entry_family": source["entry_family"],
                    "side": source["side"],
                    "control_r": format(control_r, "f"),
                    "candidate_r": format(result_r, "f"),
                    "delta_r": format(result_r - control_r, "f"),
                    "observation_at": raw["observation_at"],
                    "current_open_r": raw.get("current_open_r"),
                    "next_m1_open_r": raw.get("next_m1_open_r"),
                    "reclaim_bucket": raw.get("reclaim_bucket"),
                    "closed_through_entry_zone_against_thesis": True,
                    "existing_cognitive_exit_authorized": False,
                    "h4_state": raw.get("h4_state"),
                    "h1_state": raw.get("h1_state"),
                    "m15_state": raw.get("m15_state"),
                    "management_context": raw.get("management_context"),
                    "destination_state": raw.get("destination_state"),
                }
                break
        row = {
            "signal_at": source["signal_at"],
            "local_date": source["local_date"],
            "entry_family": source["entry_family"],
            "side": source["side"],
            "r_multiple": format(result_r, "f"),
            "control_r_multiple": format(control_r, "f"),
            "changed": action is not None,
        }
        rows.append(row)
        if action is not None:
            changed.append(action)
    return rows, changed


def winner_preservation(
    control: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, str]:
    control_values = [d(row["r_multiple"]) - FRICTION for row in control]
    candidate_values = [d(row["r_multiple"]) - FRICTION for row in candidate]
    control_wins = [x for x in control_values if x > 0]
    candidate_wins = [x for x in candidate_values if x > 0]
    control_r = sum(control_wins, Decimal(0))
    candidate_r = sum(candidate_wins, Decimal(0))
    return {
        "count": (
            "1"
            if not control_wins
            else format(
                Decimal(len(candidate_wins)) / Decimal(len(control_wins)),
                "f",
            )
        ),
        "r": (
            "1"
            if control_r == 0
            else format(candidate_r / control_r, "f")
        ),
    }


def variant_payload(
    rows: list[dict[str, object]],
    *,
    control_rows: list[dict[str, object]],
    changed: list[dict[str, object]],
) -> dict[str, object]:
    metrics = specialist._metrics(rows, friction=FRICTION)
    preserve = winner_preservation(control_rows, rows)
    return {
        "trade_count": len(rows),
        "relative_density_vs_control": "1",
        "metrics": metrics,
        "winner_preservation": preserve,
        "temporal_blocks": specialist._block_metrics(rows, halfyear=True),
        "net_r_values": [
            format(d(row["r_multiple"]) - FRICTION, "f")
            for row in rows
        ],
        "candidate_rows": rows,
        "changed_trade_count": len(changed),
        "changed_trade_forensics": changed,
    }


def run(prepared_path: Path, lane: str) -> dict[str, Any]:
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    if (
        prepared.get("schema")
        != "qore.github-trader-lab.vt31-comp009-post-entry-facts.v1"
    ):
        raise ValueError("unexpected prepared ledger schema")
    prepared_rows = cast(list[dict[str, Any]], prepared["rows"])
    control_rows, _ = terminal_rows(prepared_rows, candidate=False)
    candidate_rows, changed = terminal_rows(prepared_rows, candidate=True)
    if [row["signal_at"] for row in control_rows] != [
        row["signal_at"] for row in candidate_rows
    ]:
        raise AssertionError("candidate changed Comparator-009 trade identity")

    return {
        "schema": "qore.github-trader-lab.normalized-replay.v2",
        "adapter": "vt31-comp012-stale-entry-zone-failure-v1",
        "subject": "VT31_NAS100",
        "lane": lane,
        "control": CONTROL,
        "variants": {
            CONTROL: variant_payload(
                control_rows,
                control_rows=control_rows,
                changed=[],
            ),
            CANDIDATE: variant_payload(
                candidate_rows,
                control_rows=control_rows,
                changed=changed,
            ),
        },
        "governance": {
            "consumed_evidence_only": True,
            "prepared_upstream_reused": True,
            "decision_from_closed_m1_only": True,
            "next_open_execution_only": True,
            "stale_bucket_preexisting": True,
            "entry_zone_geometry_frozen_at_entry": True,
            "new_numeric_threshold_added": False,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "fresh_holdout_opened": False,
            "candidate_certified": False,
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
    print(
        "VT31_COMP012_LANE "
        + json.dumps(
            {
                "lane": args.lane,
                "control": payload["variants"][CONTROL]["metrics"],
                "candidate": payload["variants"][CANDIDATE]["metrics"],
                "changed_trade_count": payload["variants"][CANDIDATE][
                    "changed_trade_count"
                ],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
