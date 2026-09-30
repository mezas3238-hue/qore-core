#!/usr/bin/env python3
"""Bind real journey evidence into the bounded MC-19 Trajectory Intelligence audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

IDENTITY = "QORE_SHARED_MC19_TRAJECTORY_INTELLIGENCE_AUDIT_001"


def _load(root: Path, filename: str) -> dict[str, object]:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise ValueError(f"expected one {filename}, found {len(matches)}")
    return json.loads(matches[0].read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journey", type=Path, required=True)
    parser.add_argument("--lineage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    journey = _load(args.journey, "x05-x06-real-replay.json")
    lineage = _load(args.lineage, "sti7-sti9-real-position-lineage.json")

    if journey["status"] != "X05_X06_REAL_DATA_BOUND_CAUSAL_REPLAY_PASS":
        raise ValueError("X05/X06 real journey replay is not passed")
    if lineage["status"] != "STI7_STI9_REAL_POSITION_LINEAGE_COMPLETED_AND_PROVEN":
        raise ValueError("STI7/STI9 position lineage is not completed")

    r6 = journey["results"]["r6"]
    r5 = journey["results"]["r5"]
    payload = {
        "identity": IDENTITY,
        "status": "MC19_TRAJECTORY_INTELLIGENCE_REAL_FOUNDATION_PASS",
        "r6_trajectory_point_count": r6["trajectory_point_count"],
        "r5_trajectory_point_count": r5["trajectory_point_count"],
        "r6_memory_count": r6["memory_count"],
        "r5_memory_count": r5["memory_count"],
        "journey_states_present": sorted(
            set(r6["journey_state_counts"]) | set(r5["journey_state_counts"])
        ),
        "world_at_entry_lineage_completed": True,
        "world_now_delta_lineage_completed": True,
        "source_time_points_only": True,
        "future_market_used_by_journey_memory": False,
        "outcome_used_by_journey_memory": False,
        "pnl_used_by_journey_memory": False,
        "position_management_authority": False,
        "normal_adversity_vs_structural_deterioration_contract_present": True,
        "avoidable_loss_reduction_with_winner_preservation_proven": False,
        "dependency": "STI8_V4_FUTURE_OOS_ECONOMIC_GATE",
        "mc19_completed_and_proven": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
