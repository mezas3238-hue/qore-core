"""VT31 post-1R contextual management frontier V2.

Mechanism-discovery follow-up. Reuses the audited V1 simulator at H3, but lets
positive post-1R path efficiency veto premature breakeven inside
POSITIVE_BELOW_1R. Exact sovereign admission remains fixed.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_post_1r_contextual_management_frontier_v1 as v1
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.post_1r_contextual_management_frontier.v2"
VARIANTS = (
    "STRUCTURAL_ONLY",
    "H3_STATE_ONLY",
    "H3_EFFICIENCY_VETO",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _efficiency(closes_r: list[Decimal]) -> Decimal:
    if len(closes_r) < 2:
        return Decimal(0)
    net = closes_r[-1] - closes_r[0]
    path = sum(
        abs(right - left)
        for left, right in zip(closes_r, closes_r[1:], strict=False)
    )
    return Decimal(0) if path == 0 else net / path


def replay(evidence_path: Path) -> dict[str, object]:
    original_simulator = specialist._simulate_selected_plan
    original_state = v1.persistence._persistence_state
    payloads: dict[str, dict[str, object]] = {}

    try:
        for variant in VARIANTS:
            if variant == "H3_EFFICIENCY_VETO":

                def state_fn(closes: list[Decimal]) -> str:
                    state = original_state(closes)
                    if (
                        state == "POSITIVE_BELOW_1R"
                        and _efficiency(closes) > 0
                    ):
                        return "RECOVERED_1R_FLOOR"
                    return state

                v1.persistence._persistence_state = state_fn
            else:
                v1.persistence._persistence_state = original_state

            horizon = None if variant == "STRUCTURAL_ONLY" else 3

            def simulator(
                day_bars: tuple[object, ...],
                executable: object,
                state: dict[str, object],
                *,
                _horizon: int | None = horizon,
            ) -> dict[str, object]:
                outcome = v1._simulate(
                    day_bars,
                    executable,
                    horizon=_horizon,
                )
                if outcome.get("status") == "terminal":
                    outcome["target_plan"] = state["target_plan"]
                return outcome

            specialist._simulate_selected_plan = simulator
            payloads[variant] = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original_simulator
        v1.persistence._persistence_state = original_state

    baseline = cast(
        list[dict[str, object]],
        payloads["STRUCTURAL_ONLY"]["trades"],
    )
    baseline_ids = [str(row["signal_at"]) for row in baseline]
    variants: dict[str, object] = {}

    for variant, payload in payloads.items():
        rows = cast(list[dict[str, object]], payload["trades"])
        if [str(row["signal_at"]) for row in rows] != baseline_ids:
            raise AssertionError(
                f"{variant} changed sovereign admission population"
            )
        variants[variant] = {
            "trade_count": len(rows),
            "stress_0_05r": payload["stress_0_05r"],
            "monte_carlo": payload["monte_carlo"],
            "halfyear_stress": payload["halfyear_stress"],
            "quarter_stress": payload["quarter_stress"],
            "winner_preservation_vs_structural": (
                None
                if variant == "STRUCTURAL_ONLY"
                else v1._winner_preservation(baseline, rows)
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": variants,
        "governance": {
            "mechanism_discovery_followup": True,
            "same_sovereign_admission_population": True,
            "horizon_closed_m1": 3,
            "positive_efficiency_veto_is_causal": True,
            "future_outcome_used_for_runtime_action": False,
            "r_runtime_strategy_allowed": True,
            "r_used_for_volume": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
