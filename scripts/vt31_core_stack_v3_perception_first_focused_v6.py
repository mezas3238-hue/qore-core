"""Focused Perception-First V6 search.

Same architecture/data/gates as the full V6. This wrapper restricts the search
to the current engineering hypothesis so results arrive without spending cycles
on already-implausible combinations.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

import vt31_core_stack_v3_ev_ensemble_v2 as ev
import vt31_core_stack_v3_perception_first_v6 as v6

MEMORY_POLICIES = (
    ev.Policy(
        maximum_analogs=32,
        minimum_similarity_bps=6500,
        minimum_confidence_bps=2500,
        conflict_ev_r=conflict,
        favorable_ev_r=Decimal("0.30"),
        minimum_negative_views=2,
        caution_multiplier=Decimal("0.50"),
    )
    for conflict in (Decimal("-0.05"), Decimal("-0.10"))
)

FOCUSED = tuple(
    v6.Policy(
        memory_policy=memory,
        perception_contradiction_min=confirm,
        severe_perception_min=severe,
        perception_rescue_support_min=3,
        perception_rescue_max_contradictions=1,
        perception_memory_conflict_ev=perception_ev,
        perception_memory_min_confidence_bps=1500,
        allow_perception_only_severe_reject=allow_severe,
    )
    for memory in MEMORY_POLICIES
    for confirm in (1, 2)
    for severe in (3, 4)
    for perception_ev in (Decimal("-0.05"), Decimal("0"))
    for allow_severe in (False, True)
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-json", type=Path, required=True)
    parser.add_argument("--r6-json", type=Path, required=True)
    parser.add_argument("--r5-json", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    for partition in ("r8", "r6", "r5"):
        for market in ("nas", "sp500", "us30"):
            parser.add_argument(
                f"--{partition}-{market}",
                type=Path,
                required=True,
            )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    v6.POLICIES = FOCUSED
    payload = v6.run(
        r8_json=args.r8_json,
        r6_json=args.r6_json,
        r5_json=args.r5_json,
        daily_path=args.daily_path,
        r8_nas=args.r8_nas,
        r8_sp500=args.r8_sp500,
        r8_us30=args.r8_us30,
        r6_nas=args.r6_nas,
        r6_sp500=args.r6_sp500,
        r6_us30=args.r6_us30,
        r5_nas=args.r5_nas,
        r5_sp500=args.r5_sp500,
        r5_us30=args.r5_us30,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_shared_perception": payload[
                    "passes_shared_perception"
                ],
                "frozen_policy": payload["frozen_policy"],
                "evaluation": payload["evaluation"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
