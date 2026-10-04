#!/usr/bin/env python3
"""Real source-only replay for WP-06 / MC-17 Market Agency foundation."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.market_agency_model import (
    assess_market_agency,
)

IDENTITY = "QORE_SHARED_WP06_MARKET_AGENCY_REAL_REPLAY_001"


def _run(*, partition: str, paths: dict[str, Path]) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    if not rows:
        raise ValueError("WP-06 real replay has no source observations")

    dominant = Counter()
    deterministic = 0
    insufficient = 0
    support_sum = Counter()
    uncertainty_sum = Counter()

    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("WP-06 real replay must not attach future state")
        first = assess_market_agency(observation)
        second = assess_market_agency(observation)
        if first.fingerprint() != second.fingerprint():
            raise AssertionError("WP-06 Market Agency replay is not deterministic")
        deterministic += 1
        insufficient += int(first.insufficient)
        if first.dominant_mechanism is not None:
            dominant[first.dominant_mechanism.value] += 1
        for hypothesis in first.hypotheses:
            support_sum[hypothesis.mechanism.value] += hypothesis.support_bps
            uncertainty_sum[hypothesis.mechanism.value] += hypothesis.uncertainty_bps
            if hypothesis.actor_identity_claimed:
                raise AssertionError("WP-06 leaked actor identity claim")
            if hypothesis.calibrated_probability_claimed:
                raise AssertionError("WP-06 support masqueraded as probability")
        if (
            first.trader_methodology_used
            or first.creates_trader_setup
            or first.execution_authority
            or first.risk_authority
            or first.sizing_authority
            or first.capital_authority
        ):
            raise AssertionError("WP-06 leaked sovereign authority")

    count = len(rows)
    return {
        "partition": partition,
        "source_observation_count": count,
        "deterministic_count": deterministic,
        "all_deterministic": deterministic == count,
        "insufficient_count": insufficient,
        "dominant_mechanism_counts": dict(sorted(dominant.items())),
        "mean_support_bps": {
            key: value // count for key, value in sorted(support_sum.items())
        },
        "mean_uncertainty_bps": {
            key: value // count for key, value in sorted(uncertainty_sum.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = {}
    for partition in ("r6", "r5"):
        results[partition] = _run(
            partition=partition,
            paths={
                "NAS100": getattr(args, f"{partition}_nas"),
                "SP500": getattr(args, f"{partition}_sp"),
                "US30": getattr(args, f"{partition}_us"),
            },
        )

    passed = all(
        row["all_deterministic"]
        and row["source_observation_count"] > 0
        and bool(row["dominant_mechanism_counts"])
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "WP06_MARKET_AGENCY_ENGINE_REAL_DATA_BOUND_REPLAY_PASS"
            if passed
            else "WP06_MARKET_AGENCY_REAL_REPLAY_FAIL"
        ),
        "results": results,
        "scientific_claims": {
            "scenario_discrimination_improved": False,
            "calibration_improved": False,
            "oos_value_demonstrated": False,
            "wp06_exit_gate_pass": False,
        },
        "proof": {
            "future_market_read": False,
            "future_outcome_read": False,
            "trader_methodology_read": False,
            "actor_identity_claimed": False,
            "calibrated_probability_claimed": False,
            "deterministic_replay": passed,
        },
        "governance": {
            "wp05_dependency_closed": False,
            "wp06_close_authorized": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": payload["status"], "results": results}, sort_keys=True))


if __name__ == "__main__":
    main()
