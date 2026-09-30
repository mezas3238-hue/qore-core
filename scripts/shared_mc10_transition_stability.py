#!/usr/bin/env python3
"""Source-only transition stability validation for MC-10."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import product
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.market_physics_constraints import (
    MarketPhysicsState,
    assess_market_physics,
    classify_market_physics_state,
    learn_transition_constraints,
)

IDENTITY = "QORE_SHARED_MC10_MARKET_PHYSICS_TRANSITION_STABILITY_001"
TRAIN_FRACTION_BPS = 6_000
MAX_TVD_CAP_BPS = 5_000
MIN_TVD_TOLERANCE_BPS = 500
MAX_UNSEEN_CAP_BPS = 2_000
MIN_UNSEEN_TOLERANCE_BPS = 100
MAX_HARD_VIOLATION_RATE_BPS = 100

ALL_PAIRS = tuple(product(tuple(MarketPhysicsState), repeat=2))


def _rows(paths: dict[str, Path], partition: str):
    return source._aligned_source_rows(paths, partition=partition, require_future=False)


def _states(paths: dict[str, Path], partition: str) -> tuple[MarketPhysicsState, ...]:
    rows = _rows(paths, partition)
    return tuple(classify_market_physics_state(item[0]) for item in rows)


def _counts(states: tuple[MarketPhysicsState, ...]) -> Counter[tuple[MarketPhysicsState, MarketPhysicsState]]:
    return Counter(zip(states, states[1:], strict=False))


def _tvd_bps(
    reference: Counter[tuple[MarketPhysicsState, MarketPhysicsState]],
    observed: Counter[tuple[MarketPhysicsState, MarketPhysicsState]],
) -> int:
    ref_total = sum(reference.values())
    obs_total = sum(observed.values())
    if ref_total <= 0 or obs_total <= 0:
        raise ValueError("transition distribution cannot be empty")
    distance = 0.0
    for pair in ALL_PAIRS:
        distance += abs(
            reference[pair] / ref_total - observed[pair] / obs_total
        )
    return int(round(0.5 * distance * 10_000))


def _unseen_rate_bps(
    reference: Counter[tuple[MarketPhysicsState, MarketPhysicsState]],
    observed: Counter[tuple[MarketPhysicsState, MarketPhysicsState]],
) -> int:
    total = sum(observed.values())
    unseen = sum(count for pair, count in observed.items() if reference[pair] == 0)
    return 0 if total <= 0 else unseen * 10_000 // total


def _hard_violation_rate_bps(paths: dict[str, Path], partition: str) -> int:
    rows = _rows(paths, partition)
    rejected = sum(
        not assess_market_physics(item[0]).hard_constraints_pass
        for item in rows
    )
    return 0 if not rows else rejected * 10_000 // len(rows)


def _validation(
    *,
    paths: dict[str, Path],
    partition: str,
    reference: Counter[tuple[MarketPhysicsState, MarketPhysicsState]],
    tvd_tolerance_bps: int,
    unseen_tolerance_bps: int,
) -> dict[str, object]:
    states = _states(paths, partition)
    observed = _counts(states)
    tvd = _tvd_bps(reference, observed)
    unseen = _unseen_rate_bps(reference, observed)
    violation = _hard_violation_rate_bps(paths, partition)
    gates = {
        "tvd_lte_source_only_tolerance": tvd <= tvd_tolerance_bps,
        "unseen_rate_lte_source_only_tolerance": unseen <= unseen_tolerance_bps,
        "hard_constraint_violation_rate_lte_100_bps": (
            violation <= MAX_HARD_VIOLATION_RATE_BPS
        ),
    }
    return {
        "partition": partition,
        "observation_count": len(states),
        "transition_count": max(0, len(states) - 1),
        "distinct_transition_count": len(observed),
        "tvd_bps": tvd,
        "unseen_transition_rate_bps": unseen,
        "hard_constraint_violation_rate_bps": violation,
        "gates": gates,
        "pass": all(gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def paths(name: str) -> dict[str, Path]:
        return {
            "NAS100": getattr(args, f"{name}_nas"),
            "SP500": getattr(args, f"{name}_sp"),
            "US30": getattr(args, f"{name}_us"),
        }

    r8_states = _states(paths("r8"), "mc10_stability_r8")
    split = len(r8_states) * TRAIN_FRACTION_BPS // 10_000
    if split < 2 or len(r8_states) - split < 2:
        raise ValueError("R8 source split too small for transition stability")
    r8_train = r8_states[:split]
    # Include boundary state so the first calibration transition is causal.
    r8_calibration = r8_states[split - 1 :]

    reference = _counts(r8_train)
    calibration_counts = _counts(r8_calibration)
    internal_tvd = _tvd_bps(reference, calibration_counts)
    internal_unseen = _unseen_rate_bps(reference, calibration_counts)
    tvd_tolerance = min(
        MAX_TVD_CAP_BPS,
        max(MIN_TVD_TOLERANCE_BPS, 2 * internal_tvd),
    )
    unseen_tolerance = min(
        MAX_UNSEEN_CAP_BPS,
        max(MIN_UNSEEN_TOLERANCE_BPS, 2 * internal_unseen),
    )

    # Bind the exact source-only transition grammar used by validation.
    learned = learn_transition_constraints(r8_train)
    if not learned:
        raise ValueError("R8 train learned no transition grammar")

    results = {
        partition: _validation(
            paths=paths(partition),
            partition=partition,
            reference=reference,
            tvd_tolerance_bps=tvd_tolerance,
            unseen_tolerance_bps=unseen_tolerance,
        )
        for partition in ("r6", "r5")
    }
    passed = all(bool(row["pass"]) for row in results.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC10_TRANSITION_STABILITY_REPLICATED_PASS"
            if passed
            else "MC10_TRANSITION_STABILITY_FALSIFIED"
        ),
        "r8_source_only": {
            "observation_count": len(r8_states),
            "train_observation_count": len(r8_train),
            "calibration_observation_count": len(r8_calibration),
            "learned_transition_count": len(learned),
            "internal_calibration_tvd_bps": internal_tvd,
            "internal_calibration_unseen_rate_bps": internal_unseen,
            "frozen_tvd_tolerance_bps": tvd_tolerance,
            "frozen_unseen_tolerance_bps": unseen_tolerance,
        },
        "results": results,
        "transition_stability_demonstrated": passed,
        "hard_constraints_enforced": True,
        "unseen_transition_treated_as_impossibility": False,
        "future_market_used": False,
        "future_outcome_used": False,
        "trader_methodology_used": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
        "mc10_completed_and_proven": passed,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
