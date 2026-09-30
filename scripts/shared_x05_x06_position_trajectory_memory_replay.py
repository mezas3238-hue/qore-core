#!/usr/bin/env python3
"""Real causal replay for X-05 Position Journey / X-06 Trajectory Memory."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.shared_position_trajectory_memory import (
    build_position_trajectory_memory,
)

IDENTITY = "QORE_SHARED_X05_X06_POSITION_TRAJECTORY_MEMORY_REAL_REPLAY_001"


def _partition(
    *,
    partition: str,
    trades: Path,
    nas: Path,
    sp: Path,
    us: Path,
) -> dict[str, object]:
    sequences = base._source_sequences(
        partition=partition,
        trades_path=trades,
        nas_path=nas,
        sp_path=sp,
        us_path=us,
    )
    if not sequences:
        raise ValueError(f"{partition}: no position sequences")

    state_counts: Counter[str] = Counter()
    memory_count = deterministic_count = point_count = 0

    for sequence in sequences:
        observations = cast(tuple[Any, ...], sequence["observations"])
        if not observations:
            continue
        for observation in observations:
            if (
                observation.future_market_used
                or observation.future_outcome_used
                or observation.pnl_used
            ):
                raise AssertionError("trajectory memory received forbidden evidence")
        first = build_position_trajectory_memory(observations)
        second = build_position_trajectory_memory(observations)
        memory_count += 1
        deterministic_count += int(
            first.trajectory_fingerprint == second.trajectory_fingerprint
        )
        point_count += len(first.points)
        for point in first.points:
            state_counts[point.journey_state.value] += 1
            if (
                point.position_management_authority
                or point.execution_authority
                or point.risk_authority
                or point.capital_authority
            ):
                raise AssertionError("trajectory point leaked sovereign authority")

    return {
        "partition": partition,
        "position_sequence_count": len(sequences),
        "memory_count": memory_count,
        "trajectory_point_count": point_count,
        "deterministic_memory_count": deterministic_count,
        "deterministic_replay": deterministic_count == memory_count,
        "journey_state_counts": dict(sorted(state_counts.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-trades", type=Path, required=True)
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = {}
    for partition in ("r6", "r5"):
        results[partition] = _partition(
            partition=f"x05_x06_{partition}",
            trades=getattr(args, f"{partition}_trades"),
            nas=getattr(args, f"{partition}_nas"),
            sp=getattr(args, f"{partition}_sp"),
            us=getattr(args, f"{partition}_us"),
        )

    passed = all(
        row["position_sequence_count"] > 0
        and row["memory_count"] == row["position_sequence_count"]
        and row["trajectory_point_count"] > 0
        and row["deterministic_replay"]
        and bool(row["journey_state_counts"])
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "X05_X06_REAL_DATA_BOUND_CAUSAL_REPLAY_PASS"
            if passed
            else "X05_X06_REAL_REPLAY_FAIL"
        ),
        "results": results,
        "proof": {
            "source_time_points_only": True,
            "future_market_used_by_memory": False,
            "future_outcome_used_by_memory": False,
            "pnl_used_by_memory": False,
            "closed_terminal_outcome_used_offline_only_to_bound_historical_episode": True,
            "deterministic_replay": passed,
            "position_management_authority": False,
        },
        "scientific_claims": {
            "journey_state_predictive_value_demonstrated": False,
            "trajectory_memory_economic_value_demonstrated": False,
        },
        "governance": {
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": payload["status"], "results": results}, sort_keys=True))


if __name__ == "__main__":
    main()
