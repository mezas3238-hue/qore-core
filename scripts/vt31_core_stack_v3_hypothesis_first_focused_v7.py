"""Focused search for Hypothesis-First V7."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

import vt31_core_stack_v3_ev_ensemble_v2 as ev
import vt31_core_stack_v3_hypothesis_first_v7 as v7

MEMORY = ev.Policy(
    maximum_analogs=32,
    minimum_similarity_bps=6500,
    minimum_confidence_bps=2500,
    conflict_ev_r=Decimal("-0.05"),
    favorable_ev_r=Decimal("0.30"),
    minimum_negative_views=2,
    caution_multiplier=Decimal("0.50"),
)

FOCUSED = tuple(
    v7.Policy(
        memory_policy=MEMORY,
        reversal_rescue_min=reversal,
        reversal_margin_min=margin,
        continuation_reject_min=continuation,
        continuation_margin_min=margin,
        range_reject_min=range_min,
        anomaly_reject_min=anomaly_min,
        hypothesis_memory_conflict_ev=hyp_ev,
        hypothesis_memory_min_confidence_bps=1500,
        severe_continuation_reject=severe,
    )
    for reversal in (4, 5)
    for margin in (1, 2)
    for continuation in (3, 4)
    for range_min in (2, 3)
    for anomaly_min in (3, 4)
    for hyp_ev in (Decimal("-0.05"), Decimal("0"))
    for severe in (False, True)
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
    v7.POLICIES = FOCUSED
    payload = v7.run(
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
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_shared_hypothesis": payload[
                    "passes_shared_hypothesis"
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
