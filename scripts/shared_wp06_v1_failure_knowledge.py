#!/usr/bin/env python3
"""Failure-knowledge diagnostic for falsified WP-06 Market Agency V1.

Burned R6/R5 outcomes are used only to determine whether a temporal agency
hypothesis is scientifically justified. This diagnostic cannot demonstrate V2
value and selects no numeric rescue threshold.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source
import shared_sti2_v2_trajectory_heads as target

from qore.infrastructure.core_stack_v2.market_agency_model import (
    SharedAgencyMechanism,
    assess_market_agency,
)

IDENTITY = "QORE_SHARED_WP06_MARKET_AGENCY_V1_FAILURE_KNOWLEDGE_001"
TARGET_BPS = 6_500


def _target(pre, future) -> str:
    state = source._target_state(pre, future)
    scores = target._target_mechanism_scores(state)
    mechanism, score = max(
        scores.items(),
        key=lambda item: (item[1], item[0].value),
    )
    return "NO_MATERIAL" if score < TARGET_BPS else mechanism.value


def _partition(paths: dict[str, Path], partition: str) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=True,
    )
    previous_mechanism: SharedAgencyMechanism | None = None
    previous_margin: int | None = None
    previous_asset: str | None = None
    transition_by_target: dict[str, Counter[str]] = defaultdict(Counter)
    change_by_target: dict[str, Counter[str]] = defaultdict(Counter)
    margin_direction_by_target: dict[str, Counter[str]] = defaultdict(Counter)
    target_counts: Counter[str] = Counter()
    total = 0

    for observation, _states, pre, future in rows:
        if future is None:
            raise AssertionError("WP06 failure diagnostic requires burned target")
        assessment = assess_market_agency(observation)
        if assessment.dominant_mechanism is None:
            previous_mechanism = None
            previous_margin = None
            previous_asset = observation.asset
            continue
        dominant = assessment.dominant_mechanism
        dominant_row = next(
            item for item in assessment.hypotheses if item.mechanism is dominant
        )
        margin = dominant_row.support_bps - dominant_row.contradiction_bps

        # Source trajectory state is materialized before attaching burned target.
        same_asset = previous_asset == observation.asset
        if same_asset and previous_mechanism is not None and previous_margin is not None:
            transition = f"{previous_mechanism.value}->{dominant.value}"
            changed = "CHANGED" if previous_mechanism is not dominant else "PERSISTED"
            delta = margin - previous_margin
            direction = "RISING" if delta > 0 else "FALLING" if delta < 0 else "FLAT"
            future_target = _target(pre, future)
            transition_by_target[future_target][transition] += 1
            change_by_target[future_target][changed] += 1
            margin_direction_by_target[future_target][direction] += 1
            target_counts[future_target] += 1
            total += 1

        previous_mechanism = dominant
        previous_margin = margin
        previous_asset = observation.asset

    if total <= 0:
        raise ValueError(f"{partition}: no diagnostic trajectory rows")

    change_rates = {
        label: {
            key: count * 10_000 // max(1, sum(counter.values()))
            for key, count in sorted(counter.items())
        }
        for label, counter in sorted(change_by_target.items())
    }
    direction_rates = {
        label: {
            key: count * 10_000 // max(1, sum(counter.values()))
            for key, count in sorted(counter.items())
        }
        for label, counter in sorted(margin_direction_by_target.items())
    }

    return {
        "partition": partition,
        "trajectory_row_count": total,
        "target_counts": dict(sorted(target_counts.items())),
        "change_rates_bps": change_rates,
        "margin_direction_rates_bps": direction_rates,
        "transition_counts_by_target": {
            label: dict(counter.most_common(12))
            for label, counter in sorted(transition_by_target.items())
        },
    }


def _range(values: list[int]) -> int:
    return 0 if not values else max(values) - min(values)


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
        results[partition] = _partition(
            {
                "NAS100": getattr(args, f"{partition}_nas"),
                "SP500": getattr(args, f"{partition}_sp"),
                "US30": getattr(args, f"{partition}_us"),
            },
            partition,
        )

    diagnostics = {}
    for key in ("CHANGED", "PERSISTED"):
        spreads = []
        for partition in ("r6", "r5"):
            rates = results[partition]["change_rates_bps"]
            spreads.append(
                _range([int(row.get(key, 0)) for row in rates.values()])
            )
        diagnostics[f"{key.lower()}_target_separation_bps"] = spreads
    for key in ("RISING", "FALLING"):
        spreads = []
        for partition in ("r6", "r5"):
            rates = results[partition]["margin_direction_rates_bps"]
            spreads.append(
                _range([int(row.get(key, 0)) for row in rates.values()])
            )
        diagnostics[f"{key.lower()}_margin_target_separation_bps"] = spreads

    trajectory_signal_present = (
        min(diagnostics["changed_target_separation_bps"]) > 0
        or min(diagnostics["rising_margin_target_separation_bps"]) > 0
        or min(diagnostics["falling_margin_target_separation_bps"]) > 0
    )

    payload = {
        "identity": IDENTITY,
        "status": "WP06_V1_FAILURE_KNOWLEDGE_COMPLETE",
        "parent_v1_status": "WP06_MARKET_AGENCY_CALIBRATION_OOS_FALSIFIED",
        "results": results,
        "diagnostics": diagnostics,
        "trajectory_signal_present_in_both_consumed_partitions": trajectory_signal_present,
        "v2_candidate": (
            "AGENCY_TRAJECTORY_STATE"
            if trajectory_signal_present
            else "NO_SUPPORTED_V2_FROM_CURRENT_REPRESENTATION"
        ),
        "v2_policy_selected": False,
        "v2_value_demonstrated": False,
        "numeric_threshold_rescue_selected": False,
        "burned_r6_r5_used_for_failure_knowledge_only": True,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
