#!/usr/bin/env python3
"""STI-3 real attention-budget interaction over source-only opportunity boards."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

import shared_sti2_real_opportunity_discovery as source
import shared_sti2_v2_trajectory_heads as sti2

from qore.infrastructure.core_stack_v2.shared_attention_budget import (
    SharedAttentionCandidate,
    SharedAttentionCategory,
    allocate_shared_attention,
)
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

IDENTITY = "QORE_SHARED_STI3_ATTENTION_BUDGET_INTERACTION_001"
MAX_OBSERVATIONS_PER_PARTITION = 4_000
DATA_HEALTH_PASS_BPS = 9_500


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _clip_positive(value: int) -> int:
    return max(1, min(10_000, value))


def _board_candidate(
    *,
    partition: str,
    observation: SharedOpportunitySourceObservation,
    assessment: object,
) -> SharedOpportunityBoardCandidate:
    return SharedOpportunityBoardCandidate(
        candidate_id=f"{partition}:{observation.observation_id}",
        assessment=assessment,
        observed_at=observation.as_of,
        evidence_cutoff_at=observation.evidence_cutoff_at,
        horizon="M1",
        data_health_bps=observation.data_integrity_bps,
        relevant_traders=(
            ("VT31_NAS100",)
            if observation.asset == "NAS100"
            else ()
        ),
        provenance_refs=tuple(
            sorted(
                set(
                    observation.provenance_refs
                    + (
                        "sti2-v2-frozen-trajectory-policy",
                        "x13-attention-budget-contract",
                    )
                )
            )
        ),
    )


def _attention_rows(
    *,
    board_entry: Any,
    healthy: bool,
) -> tuple[SharedAttentionCandidate, ...]:
    support = int(board_entry.support_bps)
    common = {
        "as_of": board_entry.observed_at,
        "evidence_cutoff_at": board_entry.evidence_cutoff_at,
        "uncertainty_bps": int(board_entry.uncertainty_bps),
        "urgency_bps": _clip_positive(int(board_entry.trajectory_score_bps)),
        "compute_units": 1,
    }
    return (
        SharedAttentionCandidate(
            candidate_id="01-board-opportunity",
            category=SharedAttentionCategory.ACTIVE_OPPORTUNITY,
            information_value_bps=support,
            data_health_passed=healthy,
            provenance_refs=board_entry.provenance_refs,
            **common,
        ),
        SharedAttentionCandidate(
            candidate_id="02-board-opportunity-lower-materiality",
            category=SharedAttentionCategory.ACTIVE_OPPORTUNITY,
            information_value_bps=max(0, support // 2),
            data_health_passed=healthy,
            provenance_refs=board_entry.provenance_refs,
            **common,
        ),
        SharedAttentionCandidate(
            candidate_id="03-background",
            category=SharedAttentionCategory.BACKGROUND_WORLD,
            information_value_bps=10_000,
            data_health_passed=True,
            provenance_refs=board_entry.provenance_refs,
            **common,
        ),
    )


def _partition(
    *,
    partition: str,
    paths: dict[str, Path],
    policy: object,
) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=f"sti3_attention_{partition}",
        require_future=False,
    )
    history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=policy.sequence_window
    )
    active = 0
    healthy_materiality_pass = 0
    zero_materiality_pass = 0
    health_veto_pass = 0
    budget_pass = 0
    deterministic_pass = 0

    for observation, _states, _pre, future in rows[:MAX_OBSERVATIONS_PER_PARTITION]:
        if future is not None:
            raise AssertionError("STI3 attention interaction must remain source-only")
        history.append(observation)
        assessment = assess_opportunity_trajectory(
            tuple(history),
            policy=policy,
        )
        candidate = _board_candidate(
            partition=partition,
            observation=observation,
            assessment=assessment,
        )
        kwargs = {
            "board_id": f"sti3-attention:{partition}:{observation.observation_id}",
            "as_of": observation.as_of,
            "evidence_cutoff_at": observation.evidence_cutoff_at,
            "candidates": (candidate,),
        }
        board = build_global_opportunity_attention_board(**kwargs)
        repeated = build_global_opportunity_attention_board(**kwargs)
        deterministic_pass += int(board.fingerprint() == repeated.fingerprint())
        if not board.entries:
            continue

        active += 1
        entry = board.entries[0]
        healthy = entry.data_health_bps >= DATA_HEALTH_PASS_BPS
        normal = allocate_shared_attention(
            _attention_rows(board_entry=entry, healthy=healthy),
            as_of=entry.observed_at,
            budget_units=1,
        )
        selected = tuple(
            item.candidate_id for item in normal.decisions if item.selected
        )
        by_id = {item.candidate_id: item for item in normal.decisions}

        if normal.used_units <= normal.budget_units:
            budget_pass += 1

        if healthy and entry.support_bps > 0:
            if selected != ("01-board-opportunity",):
                raise AssertionError(
                    "highest-materiality active opportunity must win scarce attention"
                )
            if by_id["03-background"].selected:
                raise AssertionError(
                    "background cannot displace active opportunity under scarcity"
                )
            healthy_materiality_pass += 1
        elif entry.support_bps == 0:
            if by_id["01-board-opportunity"].reason_code != "ZERO_INFORMATION_VALUE":
                raise AssertionError("zero-materiality opportunity must not consume budget")
            zero_materiality_pass += 1

        degraded = allocate_shared_attention(
            _attention_rows(board_entry=entry, healthy=False),
            as_of=entry.observed_at,
            budget_units=1,
        )
        degraded_by_id = {
            item.candidate_id: item for item in degraded.decisions
        }
        if (
            degraded_by_id["01-board-opportunity"].selected
            or degraded_by_id["01-board-opportunity"].reason_code
            != "DATA_HEALTH_BLOCK"
        ):
            raise AssertionError("data-health failure must veto board opportunity")
        health_veto_pass += 1

    observed = min(len(rows), MAX_OBSERVATIONS_PER_PARTITION)
    if observed == 0 or active == 0:
        raise ValueError("STI3 attention interaction lacks active real boards")
    return {
        "partition": partition,
        "source_observation_count": observed,
        "active_board_count": active,
        "deterministic_board_count": deterministic_pass,
        "healthy_positive_materiality_pass_count": healthy_materiality_pass,
        "zero_materiality_pass_count": zero_materiality_pass,
        "data_health_veto_pass_count": health_veto_pass,
        "budget_invariant_pass_count": budget_pass,
        "pass": (
            deterministic_pass == observed
            and health_veto_pass == active
            and budget_pass == active
            and healthy_materiality_pass + zero_materiality_pass <= active
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--sti3-replay", type=Path, required=True)
    parser.add_argument("--sti3-stress", type=Path, required=True)
    parser.add_argument("--x13", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    replay = _load(args.sti3_replay)
    stress = _load(args.sti3_stress)
    x13 = _load(args.x13)

    if replay.get("status") != "STI3_REAL_DATA_BOUND_CAUSAL_REPLAY_PASS":
        raise AssertionError("STI3 real replay missing")
    if stress.get("status") != "STI3_SOURCE_STRESS_PASS":
        raise AssertionError("STI3 source stress missing")
    if x13.get("status") != "X13_COMPLETED_AND_PROVEN_REPLICATED_REAL_POSITIONS":
        raise AssertionError("X13 real attention proof missing")
    if x13.get("all_pass") is not True:
        raise AssertionError("X13 attention proof did not pass")

    policy, _calibration = sti2._source_policy(
        {
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        }
    )
    results = {
        partition: _partition(
            partition=partition,
            paths={
                "NAS100": getattr(args, f"{partition}_nas"),
                "SP500": getattr(args, f"{partition}_sp"),
                "US30": getattr(args, f"{partition}_us"),
            },
            policy=policy,
        )
        for partition in ("r6", "r5")
    }
    interaction_pass = all(bool(row["pass"]) for row in results.values())

    payload = {
        "identity": IDENTITY,
        "status": (
            "STI3_REAL_REPLAY_STRESS_ATTENTION_INTERACTION_PASS"
            if interaction_pass
            else "STI3_ATTENTION_INTERACTION_FAILED"
        ),
        "real_replay_pass": True,
        "source_stress_pass": True,
        "x13_attention_budget_proof_consumed": True,
        "results": results,
        "scarcity_materiality_behavior_proven": interaction_pass,
        "data_health_veto_proven": interaction_pass,
        "attention_budget_never_exceeded": interaction_pass,
        "canonical_board_order_is_execution_priority": False,
        "trade_outcome_value_used_for_attention": False,
        "current_real_market_family": "US_EQUITY_INDEX",
        "current_real_markets": ("NAS100", "SP500", "US30"),
        "current_real_trader_routing": ("VT31_NAS100",),
        "global_multi_family_coverage_complete": False,
        "seven_trader_real_world_routing_complete": False,
        "sti3_completed_and_proven": False,
        "external_dependency": "B_GLOBAL_WORLD_MULTI_FAMILY_AND_7_TRADER_ROUTING",
        "execution_authority": False,
        "capital_authority": False,
        "risk_authority": False,
        "productive_authority": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
