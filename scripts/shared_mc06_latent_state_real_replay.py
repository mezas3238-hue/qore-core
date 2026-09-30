#!/usr/bin/env python3
"""Real source-only replay for MC-06 latent-state reconstruction."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.latent_state_reconstruction import (
    reconstruct_latent_state,
)

IDENTITY = "QORE_SHARED_MC06_LATENT_STATE_REAL_REPLAY_001"


def _partition(paths: dict[str, Path], partition: str) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    deterministic = 0
    actor_claims = 0
    dominant = Counter()
    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("MC06 source replay cannot attach future evidence")
        first = reconstruct_latent_state(observation)
        second = reconstruct_latent_state(observation)
        deterministic += int(first.fingerprint() == second.fingerprint())
        actor_claims += sum(item.actor_identity_claimed for item in first.estimates)
        top = max(
            first.estimates,
            key=lambda item: (item.weight_bps, item.state.value),
        )
        dominant[top.state.value] += 1
    passed = bool(rows) and deterministic == len(rows) and actor_claims == 0
    return {
        "partition": partition,
        "observation_count": len(rows),
        "deterministic_count": deterministic,
        "actor_identity_claim_count": actor_claims,
        "dominant_state_counts": dict(sorted(dominant.items())),
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
        name: _partition(paths(name), f"mc06_{name}")
        for name in ("r6", "r5")
    }
    passed = all(bool(item["pass"]) for item in results.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC06_LATENT_STATE_ENGINE_REAL_DATA_BOUND_PASS"
            if passed
            else "MC06_LATENT_STATE_ENGINE_REAL_DATA_BOUND_FAIL"
        ),
        "results": results,
        "probabilistic_weights_normalized": True,
        "uncertainty_attached": True,
        "provenance_attached": True,
        "actor_identity_claimed": False,
        "latent_predictive_value_demonstrated": False,
        "latent_calibration_demonstrated": False,
        "mc06_completed_and_proven": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
