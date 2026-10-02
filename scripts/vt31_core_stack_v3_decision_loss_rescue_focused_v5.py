"""Focused V5 search around the aggressive-loss / winner-rescue frontier."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

import vt31_core_stack_v3_decision_loss_rescue_v5 as v5
import vt31_core_stack_v3_shared_decision_intelligence_v2 as decision

FOCUSED_LOSS = decision.Policy(
    maximum_analogs=32,
    minimum_similarity_bps=6500,
    minimum_confidence_bps=2500,
    abstain_ev_r=Decimal("-0.05"),
    required_negative_views=2,
    maximum_positive_views=0,
    winner_archetype_ev_floor=Decimal("0.30"),
    winner_archetype_payoff_floor=Decimal("2.5"),
    tail_mean_win_r_floor=Decimal("4.5"),
    tail_payoff_floor=Decimal("3"),
    tail_min_win_rate=Decimal("0.12"),
)

FOCUSED_POLICIES = tuple(
    v5.RescuePolicy(
        loss_policy=FOCUSED_LOSS,
        recent_fraction_numerator=1,
        recent_fraction_denominator=2,
        rescue_similarity_bps=similarity,
        rescue_minimum_views=rescue_views,
        rescue_minimum_winner_r=winner_r,
        recent_positive_ev_r=recent_ev,
        recent_positive_views=recent_views,
        recent_minimum_confidence_bps=1500,
        recent_minimum_effective_n=Decimal("4"),
    )
    for similarity in (8500, 9000)
    for rescue_views in (1, 2)
    for winner_r in (Decimal("2.5"), Decimal("4"))
    for recent_ev in (Decimal("0.10"), Decimal("0.20"))
    for recent_views in (1, 2)
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-json", type=Path, required=True)
    parser.add_argument("--r6-json", type=Path, required=True)
    parser.add_argument("--r5-json", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    v5.POLICIES = FOCUSED_POLICIES
    payload = v5.run(
        r8_json=args.r8_json,
        r6_json=args.r6_json,
        r5_json=args.r5_json,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "passes_shared_decision": payload["passes_shared_decision"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
