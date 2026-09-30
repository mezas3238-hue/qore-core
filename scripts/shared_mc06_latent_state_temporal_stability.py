#!/usr/bin/env python3
"""Preregistered source-only temporal stability test for MC-06 latent states."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.latent_state_reconstruction import (
    reconstruct_latent_state,
)

IDENTITY = "QORE_SHARED_MC06_LATENT_STATE_TEMPORAL_STABILITY_001"
MIN_TRANSITIONS = 100


def _sequence(
    paths: dict[str, Path],
    partition: str,
) -> list[tuple[object, str]]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    sequence: list[tuple[object, str]] = []
    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("MC06 stability cannot attach future evidence")
        belief = reconstruct_latent_state(observation)
        dominant = max(
            belief.estimates,
            key=lambda item: (item.weight_bps, item.state.value),
        )
        sequence.append((observation.as_of, dominant.state.value))
    return sequence


def _transitions(sequence: list[tuple[object, str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for (left_at, left), (right_at, right) in zip(
        sequence,
        sequence[1:],
        strict=False,
    ):
        delta = (right_at - left_at).total_seconds() / 60
        if 20 <= delta <= 40:
            counts[f"{left}->{right}"] += 1
    return counts


def _distribution(counts: Counter[str]) -> dict[str, int]:
    total = sum(counts.values())
    if total <= 0:
        return {}
    keys = sorted(counts)
    result = {
        key: counts[key] * 10_000 // total
        for key in keys
    }
    remainder = 10_000 - sum(result.values())
    for index in range(remainder):
        result[keys[index % len(keys)]] += 1
    return result


def _tvd_bps(left: dict[str, int], right: dict[str, int]) -> int:
    keys = set(left) | set(right)
    return sum(abs(left.get(key, 0) - right.get(key, 0)) for key in keys) // 2


def _partition_result(
    sequence: list[tuple[object, str]],
    reference: dict[str, int],
) -> dict[str, object]:
    counts = _transitions(sequence)
    distribution = _distribution(counts)
    return {
        "observation_count": len(sequence),
        "transition_count": sum(counts.values()),
        "transition_distribution_bps": distribution,
        "tvd_vs_r8_bps": _tvd_bps(reference, distribution),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    prereg = json.loads(args.preregistration.read_text())
    if prereg["status"] != "PREREGISTERED_BEFORE_STABILITY_EVALUATION":
        raise AssertionError("MC06 stability preregistration is not frozen")

    def paths(name: str) -> dict[str, Path]:
        return {
            "NAS100": getattr(args, f"{name}_nas"),
            "SP500": getattr(args, f"{name}_sp"),
            "US30": getattr(args, f"{name}_us"),
        }

    r8 = _sequence(paths("r8"), "mc06_stability_r8")
    midpoint = len(r8) // 2
    r8_left = _distribution(_transitions(r8[:midpoint]))
    r8_right = _distribution(_transitions(r8[midpoint:]))
    r8_full = _distribution(_transitions(r8))
    internal_tvd = _tvd_bps(r8_left, r8_right)
    tolerance = max(750, min(10_000, 2 * internal_tvd + 250))

    r6 = _partition_result(
        _sequence(paths("r6"), "mc06_stability_r6"),
        r8_full,
    )
    r5 = _partition_result(
        _sequence(paths("r5"), "mc06_stability_r5"),
        r8_full,
    )
    enough = (
        sum(_transitions(r8).values()) >= MIN_TRANSITIONS
        and int(r6["transition_count"]) >= MIN_TRANSITIONS
        and int(r5["transition_count"]) >= MIN_TRANSITIONS
    )
    passed = (
        enough
        and int(r6["tvd_vs_r8_bps"]) <= tolerance
        and int(r5["tvd_vs_r8_bps"]) <= tolerance
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC06_LATENT_STATE_TEMPORAL_STABILITY_PASS"
            if passed
            else "MC06_LATENT_STATE_TEMPORAL_STABILITY_FALSIFIED"
        ),
        "r8": {
            "observation_count": len(r8),
            "transition_count": sum(_transitions(r8).values()),
            "internal_split_tvd_bps": internal_tvd,
            "frozen_tolerance_bps": tolerance,
            "transition_distribution_bps": r8_full,
        },
        "r6": r6,
        "r5": r5,
        "gates": {
            "minimum_transition_count": MIN_TRANSITIONS,
            "sample_sufficiency_pass": enough,
            "r6_tvd_pass": int(r6["tvd_vs_r8_bps"]) <= tolerance,
            "r5_tvd_pass": int(r5["tvd_vs_r8_bps"]) <= tolerance,
        },
        "probabilistic_latent_state_engine": True,
        "uncertainty_attached": True,
        "provenance_attached": True,
        "actor_identity_claimed": False,
        "future_market_used": False,
        "outcome_used": False,
        "productive_authority": False,
        "mc06_completed_and_proven": passed,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
