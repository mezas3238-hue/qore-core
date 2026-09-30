#!/usr/bin/env python3
"""Real causal replay for X-01/X-02/X-03 opportunity surface cognition."""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source
import shared_sti2_v2_trajectory_heads as sti2

from qore.infrastructure.core_stack_v2.shared_global_opportunity_board import (
    SharedOpportunityBoardCandidate,
    build_global_opportunity_attention_board,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    assess_opportunity_trajectory,
)
from qore.infrastructure.core_stack_v2.shared_opportunity_surface import (
    build_global_opportunity_surface,
)

IDENTITY = "QORE_SHARED_X01_X02_X03_OPPORTUNITY_SURFACE_REAL_REPLAY_001"
HISTORY_BOARDS = 120


def _partition(
    *,
    partition: str,
    paths: dict[str, Path],
    policy: object,
) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    if not rows:
        raise ValueError("opportunity surface replay has no source rows")

    observation_history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=policy.sequence_window
    )
    board_history = deque(maxlen=HISTORY_BOARDS)
    rarity_counts: Counter[str] = Counter()
    surface_count = point_count = empty_count = deterministic_count = 0
    asymmetry_sum = 0

    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("opportunity surface replay must be source-only")
        observation_history.append(observation)
        assessment = assess_opportunity_trajectory(
            tuple(observation_history),
            policy=policy,
        )
        candidate = SharedOpportunityBoardCandidate(
            candidate_id=f"{partition}:{observation.observation_id}",
            assessment=assessment,
            observed_at=observation.as_of,
            evidence_cutoff_at=observation.evidence_cutoff_at,
            horizon="M1",
            data_health_bps=observation.data_integrity_bps,
            relevant_traders=(
                ("VT31_NAS100",) if observation.asset == "NAS100" else ()
            ),
            provenance_refs=tuple(
                sorted(
                    set(
                        observation.provenance_refs
                        + (
                            "sti2-v2-frozen-trajectory-policy",
                            "x01-x02-x03-real-replay",
                        )
                    )
                )
            ),
        )
        board = build_global_opportunity_attention_board(
            board_id=f"board:{partition}:{observation.observation_id}",
            as_of=observation.as_of,
            evidence_cutoff_at=observation.evidence_cutoff_at,
            candidates=(candidate,),
        )
        surface = build_global_opportunity_surface(
            surface_id=f"surface:{partition}:{observation.observation_id}",
            as_of=observation.as_of,
            current_board=board,
            historical_boards=tuple(board_history),
        )
        repeated = build_global_opportunity_surface(
            surface_id=f"surface:{partition}:{observation.observation_id}",
            as_of=observation.as_of,
            current_board=board,
            historical_boards=tuple(board_history),
        )
        surface_count += 1
        deterministic_count += int(
            surface.fingerprint() == repeated.fingerprint()
        )
        empty_count += int(surface.is_empty)
        for point in surface.points:
            point_count += 1
            rarity_counts[point.rarity_state.value] += 1
            asymmetry_sum += point.evidence_asymmetry_bps
            if point.order_priority or point.capital_priority:
                raise AssertionError("surface leaked sovereign priority")
        board_history.append(board)

    return {
        "partition": partition,
        "source_observation_count": len(rows),
        "surface_count": surface_count,
        "point_count": point_count,
        "empty_surface_count": empty_count,
        "deterministic_surface_count": deterministic_count,
        "deterministic_replay": deterministic_count == surface_count,
        "rarity_state_counts": dict(sorted(rarity_counts.items())),
        "mean_evidence_asymmetry_bps": (
            0 if point_count == 0 else asymmetry_sum // point_count
        ),
        "past_board_history_only": True,
        "history_board_limit": HISTORY_BOARDS,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy, calibration = sti2._source_policy(
        {
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        }
    )
    results = {}
    for partition in ("r6", "r5"):
        results[partition] = _partition(
            partition=partition,
            paths={
                "NAS100": getattr(args, f"{partition}_nas"),
                "SP500": getattr(args, f"{partition}_sp"),
                "US30": getattr(args, f"{partition}_us"),
            },
            policy=policy,
        )

    passed = all(
        row["source_observation_count"] > 0
        and row["surface_count"] == row["source_observation_count"]
        and row["point_count"] > 0
        and row["empty_surface_count"] > 0
        and row["deterministic_replay"]
        and row["past_board_history_only"]
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "X01_X02_X03_REAL_DATA_BOUND_CAUSAL_REPLAY_PASS"
            if passed
            else "X01_X02_X03_REAL_REPLAY_FAIL"
        ),
        "r8_source_only_calibration": calibration,
        "results": results,
        "proof": {
            "future_market_read": False,
            "future_outcome_read": False,
            "trader_methodology_read": False,
            "rarity_uses_past_boards_only": True,
            "asymmetry_uses_source_evidence_only": True,
            "order_or_capital_priority": False,
        },
        "scientific_claims": {
            "global_multi_family_world_complete": False,
            "predictive_value_claimed": False,
            "economic_value_claimed": False,
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
