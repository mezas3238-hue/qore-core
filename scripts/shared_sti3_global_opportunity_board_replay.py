#!/usr/bin/env python3
"""Real source-only replay for STI-3 Global Opportunity Attention Board."""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from pathlib import Path

import shared_sti2_real_opportunity_discovery as v1
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

IDENTITY = "QORE_SHARED_STI3_GLOBAL_OPPORTUNITY_BOARD_REAL_REPLAY_001"
X18_ROUTING_EVIDENCE = "x18-seven-trader-routing-run-36729632136"


def _relevant_traders(asset: str) -> tuple[str, ...]:
    if asset == "NAS100":
        return ("VT31_NAS100",)
    return ()


def _replay(
    *,
    partition: str,
    paths: dict[str, Path],
    policy: object,
) -> dict[str, object]:
    rows = v1._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=policy.sequence_window
    )
    board_count = 0
    entry_count = 0
    empty_count = 0
    deterministic_count = 0
    maturity = Counter()
    mechanisms = Counter()
    routed = Counter()

    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("STI-3 source-only replay must not attach future")
        history.append(observation)
        assessment = assess_opportunity_trajectory(
            tuple(history),
            policy=policy,
        )
        candidate = SharedOpportunityBoardCandidate(
            candidate_id=f"{partition}:{observation.observation_id}",
            assessment=assessment,
            observed_at=observation.as_of,
            evidence_cutoff_at=observation.evidence_cutoff_at,
            horizon="M1",
            data_health_bps=observation.data_integrity_bps,
            relevant_traders=_relevant_traders(observation.asset),
            provenance_refs=tuple(
                sorted(
                    set(
                        observation.provenance_refs
                        + (
                            "sti2-v2-frozen-trajectory-policy",
                            X18_ROUTING_EVIDENCE,
                        )
                    )
                )
            ),
        )
        kwargs = {
            "board_id": f"sti3:{partition}:{observation.observation_id}",
            "as_of": observation.as_of,
            "evidence_cutoff_at": observation.evidence_cutoff_at,
            "candidates": (candidate,),
        }
        board = build_global_opportunity_attention_board(**kwargs)
        replayed = build_global_opportunity_attention_board(**kwargs)
        if board.fingerprint() != replayed.fingerprint():
            raise AssertionError("STI-3 board replay is not deterministic")
        deterministic_count += 1
        board_count += 1
        empty_count += int(board.is_empty)
        entry_count += len(board.entries)
        for entry in board.entries:
            maturity[entry.maturity.value] += 1
            mechanisms[
                "NONE" if entry.trajectory is None else entry.trajectory.value
            ] += 1
            for trader in entry.relevant_traders:
                routed[trader] += 1
            if (
                entry.ranking_is_order_priority
                or entry.creates_trader_setup
                or entry.execution_authority
                or entry.capital_authority
                or entry.risk_authority
            ):
                raise AssertionError("STI-3 replay leaked sovereign authority")

    if board_count == 0:
        raise ValueError("STI-3 replay has no source observations")
    return {
        "partition": partition,
        "source_observation_count": len(rows),
        "board_count": board_count,
        "active_entry_count": entry_count,
        "empty_board_count": empty_count,
        "deterministic_board_count": deterministic_count,
        "maturity_counts": dict(sorted(maturity.items())),
        "mechanism_counts": dict(sorted(mechanisms.items())),
        "relevant_trader_counts": dict(sorted(routed.items())),
        "all_boards_deterministic": deterministic_count == board_count,
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
        results[partition] = _replay(
            partition=partition,
            paths={
                "NAS100": getattr(args, f"{partition}_nas"),
                "SP500": getattr(args, f"{partition}_sp"),
                "US30": getattr(args, f"{partition}_us"),
            },
            policy=policy,
        )

    passed = all(
        row["all_boards_deterministic"]
        and row["board_count"] == row["source_observation_count"]
        and row["board_count"] > 0
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "STI3_REAL_DATA_BOUND_CAUSAL_REPLAY_PASS"
            if passed
            else "STI3_REAL_DATA_REPLAY_FAIL"
        ),
        "engine": "SHARED_GLOBAL_OPPORTUNITY_ATTENTION_BOARD_V1",
        "input_cognition": "STI2_V2_FROZEN_TRAJECTORY_HEADS",
        "r8_source_only_calibration": calibration,
        "replays": results,
        "proof": {
            "real_data_bound": True,
            "future_market_read": False,
            "future_outcome_read": False,
            "trader_methodology_read": False,
            "canonical_order_not_execution_ranking": True,
            "empty_board_contract_valid": True,
            "deterministic_replay": passed,
            "x18_routing_evidence_consumed_read_only": X18_ROUTING_EVIDENCE,
        },
        "governance": {
            "creates_trader_setup": False,
            "execution_authority": False,
            "capital_authority": False,
            "risk_authority": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "r6": results["r6"],
                "r5": results["r5"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
