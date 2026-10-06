"""Predeclared non-Breaker reloss+momentum structural protection.

Consumed-evidence development only.

The rule is market-native:
- Breaker entries use the sovereign structural baseline unchanged.
- Fair Value Gap / Order Block entries may improve the stop once only after a
  confirmed M1 protective swing, closed-price momentum deterioration, and
  re-loss of the source confirmation structure.

No R multiple, MFE/MAE threshold, volume, sizing, leverage, compounding, or
capital weighting is a runtime input.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_market_native_momentum_swing_protection_v1 as momentum
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.nonbreaker_reloss_momentum.v1"
VARIANT = "NONBREAKER_RELOSS_MOMENTUM_SWING_ONCE"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _simulate_nonbreaker(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
) -> dict[str, object]:
    family = str(getattr(executable.selected_family, "value"))
    if family == "breaker":
        outcome = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
    else:
        outcome = momentum._simulate(
            day_bars,
            executable,
            require_structure_reloss=True,
        )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        outcome["nonbreaker_reloss_policy_eligible"] = family != "breaker"
    return outcome


def _winner_preservation(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    return momentum._winner_preservation(baseline, candidate)


def _changed_rows(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> list[dict[str, object]]:
    base = {str(row["signal_at"]): row for row in baseline}
    changed: list[dict[str, object]] = []
    for row in candidate:
        key = str(row["signal_at"])
        source = base[key]
        base_r = _d(source["r_multiple"])
        candidate_r = _d(row["r_multiple"])
        if candidate_r == base_r:
            continue
        changed.append(
            {
                "signal_at": key,
                "local_date": row["local_date"],
                "side": row["side"],
                "entry_family": row["entry_family"],
                "baseline_r": format(base_r, "f"),
                "candidate_r": format(candidate_r, "f"),
                "delta_r": format(candidate_r - base_r, "f"),
                "baseline_exit_reason": source["exit_reason"],
                "candidate_exit_reason": row["exit_reason"],
                "structural_protection_armed": row.get(
                    "structural_protection_armed",
                    False,
                ),
                "structural_protection_trigger_at": row.get(
                    "structural_protection_trigger_at"
                ),
                "intelligence_state": row["intelligence_state"],
            }
        )
    return changed


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    try:
        specialist._simulate_selected_plan = original
        baseline_payload = specialist.replay(evidence_path)

        specialist._simulate_selected_plan = _simulate_nonbreaker
        candidate_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    baseline = cast(
        list[dict[str, object]],
        baseline_payload["trades"],
    )
    candidate = cast(
        list[dict[str, object]],
        candidate_payload["trades"],
    )
    changed = _changed_rows(baseline, candidate)
    breaker_changed = [
        row for row in changed if row["entry_family"] == "breaker"
    ]

    variants = {
        "BASELINE": {
            "trade_count": len(baseline),
            "stress_0_05r": baseline_payload["stress_0_05r"],
            "halfyear_stress": baseline_payload["halfyear_stress"],
            "monte_carlo": baseline_payload["monte_carlo"],
            "trade_rows": baseline,
        },
        VARIANT: {
            "trade_count": len(candidate),
            "stress_0_05r": candidate_payload["stress_0_05r"],
            "halfyear_stress": candidate_payload["halfyear_stress"],
            "monte_carlo": candidate_payload["monte_carlo"],
            "winner_preservation_vs_baseline": _winner_preservation(
                baseline,
                candidate,
            ),
            "protection_armed_count": sum(
                row.get("structural_protection_armed") is True
                for row in candidate
            ),
            "changed_trade_count": len(changed),
            "breaker_changed_trade_count": len(breaker_changed),
            "changed_rows": changed,
            "trade_rows": candidate,
        },
    }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": variants,
        "governance": {
            "predeclared_plan": (
                "docs/research/"
                "VT31_ARCH2_NONBREAKER_RELOSS_MOMENTUM_PLAN_001.md"
            ),
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_structural_invalidation_changed": False,
            "primary_structural_target_changed": False,
            "breaker_management_changed": False,
            "runtime_r_decision_authority": False,
            "runtime_volume_decision_authority": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "fixed_profit_threshold_used": False,
            "fresh_holdout_opened": False,
            "automatic_policy_promotion": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "variant": payload["variants"][VARIANT],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
