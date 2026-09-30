#!/usr/bin/env python3
"""Real source-only replay for MC-18 Counterfactual World Engine."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.counterfactual_world_engine import (
    CounterfactualWorldKind,
    build_counterfactual_world_distribution,
)

IDENTITY = "QORE_SHARED_MC18_COUNTERFACTUAL_WORLD_REAL_REPLAY_001"


def _partition(paths: dict[str, Path], partition: str) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    deterministic = 0
    unknown_present = 0
    probability_valid = 0
    dominant: Counter[str] = Counter()
    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("MC18 source replay cannot attach future evidence")
        first = build_counterfactual_world_distribution(observation)
        second = build_counterfactual_world_distribution(observation)
        deterministic += int(first.fingerprint() == second.fingerprint())
        probability_valid += int(
            sum(item.probability_bps for item in first.paths) == 10_000
        )
        unknown_present += int(
            CounterfactualWorldKind.UNKNOWN_SHOCK
            in {item.kind for item in first.paths}
        )
        strongest = max(
            first.paths,
            key=lambda item: (item.probability_bps, item.kind.value),
        )
        dominant[strongest.kind.value] += 1
    passed = (
        bool(rows)
        and deterministic == len(rows)
        and unknown_present == len(rows)
        and probability_valid == len(rows)
    )
    return {
        "partition": partition,
        "observation_count": len(rows),
        "deterministic_count": deterministic,
        "unknown_shock_present_count": unknown_present,
        "probability_valid_count": probability_valid,
        "dominant_world_counts": dict(sorted(dominant.items())),
        "pass": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
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

    results = {
        name: _partition(paths(name), f"mc18_{name}")
        for name in ("r6", "r5")
    }
    passed = all(bool(item["pass"]) for item in results.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC18_COUNTERFACTUAL_WORLD_ENGINE_REAL_DATA_BOUND_PASS"
            if passed
            else "MC18_COUNTERFACTUAL_WORLD_ENGINE_REAL_DATA_BOUND_FAIL"
        ),
        "results": results,
        "bounded_alternative_worlds": True,
        "unknown_shock_preserved": True,
        "deterministic_future_claimed": False,
        "future_market_used": False,
        "outcome_used": False,
        "probability_calibration_demonstrated": False,
        "fresh_oos_path_distribution_value_demonstrated": False,
        "mc18_completed_and_proven": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
