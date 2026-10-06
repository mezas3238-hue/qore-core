"""VT31 NAS100 A+B breaker pretarget structural-protection frontier V1.

Consumed/burned evidence development only.

Fixed stack:
- Architect-A admission: expanded reference rejected and Order Block requires
  SHORT + entry-evidence age >= 11m;
- Architect-B position stack: H3 + W5 full-cognition DOL2 + PS2.

This frontier changes only Breaker post-fill management before DOL1/DOL2:
- PS1: one confirmed improving M1 protective swing;
- PS2: two confirmed improving M1 protective swings.

The swing is observed only on a fully closed M1 bar, becomes active on the next
M1 bar, may only improve the stop, never widens risk, and never changes size.

No sizing, leverage, compounding, capital weighting, fold identity, date label,
or future outcome is runtime authority.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as ab
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.ab_breaker_pretarget_protection_frontier.v1"
WINDOW = 5
FIXED_ADMISSION = "A_EXPANDED_OB_REQUIRE_SHORT_AGE_11M"
VARIANTS: dict[str, int | None] = {
    "CONTROL_AB": None,
    "BREAKER_PS1": 1,
    "BREAKER_PS2": 2,
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _filtered(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if not ab._is_abstained(row, FIXED_ADMISSION)
    ]


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    rows_by_variant: dict[str, list[dict[str, object]]] = {
        name: [] for name in VARIANTS
    }

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        baseline = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if baseline.get("status") != "terminal":
            return baseline

        for name, confirmations in VARIANTS.items():
            outcome = composition._simulate_composite(
                day_bars,
                executable,
                state,
                window=WINDOW,
                pretarget_breaker_ps_confirmations=confirmations,
            )
            if outcome.get("status") != "terminal":
                raise AssertionError(
                    f"{name} changed sovereign terminal eligibility: {outcome}"
                )
            outcome["target_plan"] = state["target_plan"]
            composition._attach_entry_context(outcome, state)
            rows_by_variant[name].append(outcome)

        return baseline

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(list[dict[str, object]], base_payload["trades"])
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    reports: dict[str, object] = {}
    filtered_by_variant: dict[str, list[dict[str, object]]] = {}

    for name, raw_rows in rows_by_variant.items():
        if [str(row["signal_at"]) for row in raw_rows] != structural_ids:
            raise AssertionError(
                f"{name} changed sovereign terminal population"
            )
        rows = _filtered(raw_rows)
        filtered_by_variant[name] = rows
        reports[name] = {
            "trade_count": len(rows),
            "relative_density_vs_structural": format(
                Decimal(len(rows)) / Decimal(len(structural_rows)),
                "f",
            ) if structural_rows else "0",
            "stress_0_05r": specialist._metrics(
                rows,
                friction=specialist.FRICTION,
            ),
            "monte_carlo": specialist._monte_carlo(rows),
            "halfyear_stress": specialist._block_metrics(
                rows,
                halfyear=True,
            ),
            "exit_reasons": dict(
                sorted(Counter(str(row["exit_reason"]) for row in rows).items())
            ),
            "pretarget_breaker_ps_committed_count": sum(
                row.get("pretarget_breaker_ps_committed") is True
                for row in rows
            ),
            "sequence_diagnostics": composition._sequence_diagnostics(rows),
        }

    control = filtered_by_variant["CONTROL_AB"]
    control_map = {str(row["signal_at"]): row for row in control}
    for name, rows in filtered_by_variant.items():
        candidate_map = {str(row["signal_at"]): row for row in rows}
        if set(candidate_map) != set(control_map):
            raise AssertionError(
                f"{name} changed fixed A admission population"
            )
        reports[name]["winner_preservation_vs_control"] = (
            ab._winner_preservation(control, rows)
        )
        reports[name]["changed_trade_count_vs_control"] = sum(
            _d(candidate_map[key]["r_multiple"])
            != _d(control_map[key]["r_multiple"])
            for key in control_map
        )

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "fixed_admission": FIXED_ADMISSION,
        "fixed_position_stack": "H3_W5_DOL2_PS2",
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "fixed_admission_predeclared": True,
            "fixed_position_stack_predeclared": True,
            "breaker_protection_predeclared": True,
            "breaker_protection_closed_m1_only": True,
            "breaker_protection_effective_next_m1": True,
            "breaker_stop_improvement_only": True,
            "initial_stop_widening": False,
            "entry_price_changed": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fold_identity_used_for_action": False,
            "future_outcome_used_for_action": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
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
