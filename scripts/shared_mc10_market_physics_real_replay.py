#!/usr/bin/env python3
"""R8 source learning and R6/R5 replay for MC-10 Market Physics foundation."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.market_physics_constraints import (
    MarketPhysicsState,
    assess_market_physics,
    classify_market_physics_state,
    learn_transition_constraints,
)

IDENTITY = "QORE_SHARED_MC10_MARKET_PHYSICS_REAL_REPLAY_001"


def _source_rows(paths: dict[str, Path], partition: str):
    return source._aligned_source_rows(paths, partition=partition, require_future=False)


def _states(paths: dict[str, Path], partition: str) -> tuple[MarketPhysicsState, ...]:
    rows = _source_rows(paths, partition)
    return tuple(classify_market_physics_state(row[0]) for row in rows)


def _evaluate(
    paths: dict[str, Path],
    partition: str,
    constraints,
) -> dict[str, object]:
    rows = _source_rows(paths, partition)
    violations: Counter[str] = Counter()
    states: Counter[str] = Counter()
    unseen = 0
    deterministic = 0
    previous = None
    admissible = 0
    for observation, _source_states, _pre, future in rows:
        if future is not None:
            raise AssertionError("MC-10 source replay cannot attach future market")
        first = assess_market_physics(
            observation,
            previous_state=previous,
            learned_constraints=constraints,
        )
        second = assess_market_physics(
            observation,
            previous_state=previous,
            learned_constraints=constraints,
        )
        deterministic += int(first.fingerprint() == second.fingerprint())
        admissible += int(first.explanation_admissible)
        states[first.state.value] += 1
        for violation in first.violations:
            violations[violation.value] += 1
        if first.learned_transition_seen is False:
            unseen += 1
        previous = first.state
    return {
        "partition": partition,
        "observation_count": len(rows),
        "deterministic_replay": deterministic == len(rows),
        "admissible_count": admissible,
        "rejected_inconsistent_count": len(rows) - admissible,
        "unseen_transition_count": unseen,
        "state_counts": dict(sorted(states.items())),
        "violation_counts": dict(sorted(violations.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def paths(partition: str) -> dict[str, Path]:
        return {
            "NAS100": getattr(args, f"{partition}_nas"),
            "SP500": getattr(args, f"{partition}_sp"),
            "US30": getattr(args, f"{partition}_us"),
        }

    r8_states = _states(paths("r8"), "r8")
    constraints = learn_transition_constraints(r8_states)
    if not constraints:
        raise ValueError("MC-10 R8 learned no transition constraints")

    results = {
        partition: _evaluate(paths(partition), partition, constraints)
        for partition in ("r6", "r5")
    }
    replay_pass = all(
        row["observation_count"] > 0 and row["deterministic_replay"]
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC10_MARKET_PHYSICS_ENGINE_REAL_DATA_BOUND_REPLAY_PASS"
            if replay_pass
            else "MC10_MARKET_PHYSICS_REAL_REPLAY_FAIL"
        ),
        "r8_source_observation_count": len(r8_states),
        "r8_learned_transition_count": len(constraints),
        "results": results,
        "hard_constraints_enforced": True,
        "learned_transition_constraints_bound": True,
        "unseen_transition_treated_as_impossibility": False,
        "transition_stability_demonstrated": False,
        "mc10_completed_and_proven": False,
        "future_market_used": False,
        "future_outcome_used": False,
        "trader_methodology_used": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
