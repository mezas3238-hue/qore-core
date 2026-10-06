"""VT31 NAS100 Breaker pre-target structural-protection frontier V1.

Consumed-evidence development only.

The admission population is held fixed at the current strongest A+B witness:

    A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M

The B-side comparator is also fixed:

    H3 + W5 soft-DOL1 + full-cognition DOL2 + post-acceptance PS2

The only experimental degree of freedom is a market-native protective swing
for Breaker entries before DOL1 acceptance:

- CONTROL: no extra pre-target Breaker protection;
- BREAKER_PS1: first confirmed improving M1 protective swing;
- BREAKER_PS2: two confirmed improving M1 protective swings.

All protective actions are causal, can only improve the existing stop, and
become effective on the next M1. No sizing, leverage, compounding or capital
weighting is allowed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.breaker_pretarget_protection_frontier.v1"
ADMISSION_VARIANT = "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M"
B_COMPARATOR_ID = "VT31_BSIDE_H3_W5_DOL2_PS2_RESEARCH_COMPARATOR_001"
WINDOW = 5

VARIANTS: dict[str, int | None] = {
    "CONTROL": None,
    "BREAKER_PS1": 1,
    "BREAKER_PS2": 2,
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    confirmations: int | None,
) -> dict[str, object]:
    outcome = composition._simulate_composite(
        day_bars,
        executable,
        state,
        window=WINDOW,
        pretarget_breaker_ps_confirmations=confirmations,
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
    return outcome


def _winner_preservation(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    return admission._winner_preservation(baseline, candidate)


def _report(
    full_control: list[dict[str, object]],
    baseline: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    density = (
        Decimal(0)
        if not full_control
        else Decimal(len(rows)) / Decimal(len(full_control))
    )
    breaker_rows = [row for row in rows if row["entry_family"] == "breaker"]
    committed = [
        row
        for row in breaker_rows
        if row.get("pretarget_breaker_ps_committed") is True
    ]
    return {
        "trade_count": len(rows),
        "relative_density_vs_unfiltered_b": format(density, "f"),
        "stress_0_05r": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(rows),
        "halfyear_stress": specialist._block_metrics(rows, halfyear=True),
        "winner_preservation_vs_control": _winner_preservation(
            baseline,
            rows,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(rows),
        "breaker_trade_count": len(breaker_rows),
        "pretarget_breaker_ps_committed_count": len(committed),
        "pretarget_breaker_ps_exit_count": sum(
            row.get("exit_reason")
            == "composite-breaker-pretarget-protective-stop"
            for row in rows
        ),
        "exit_reason_counts": dict(
            sorted(Counter(str(row["exit_reason"]) for row in rows).items())
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    full_rows: dict[str, list[dict[str, object]]] = {
        name: [] for name in VARIANTS
    }

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        structural = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if structural.get("status") != "terminal":
            return structural

        for name, confirmations in VARIANTS.items():
            outcome = _simulate(
                day_bars,
                executable,
                state,
                confirmations=confirmations,
            )
            if outcome.get("status") != "terminal":
                raise AssertionError(
                    f"{name} changed terminal eligibility: {outcome}"
                )
            full_rows[name].append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(list[dict[str, object]], base_payload["trades"])
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    for name, rows in full_rows.items():
        ids = [str(row["signal_at"]) for row in rows]
        if ids != structural_ids:
            raise AssertionError(
                f"{name} changed sovereign terminal trade identity"
            )

    filtered = {
        name: [
            row
            for row in rows
            if not admission._is_abstained(row, ADMISSION_VARIANT)
        ]
        for name, rows in full_rows.items()
    }
    baseline = filtered["CONTROL"]
    baseline_ids = [str(row["signal_at"]) for row in baseline]
    for name, rows in filtered.items():
        ids = [str(row["signal_at"]) for row in rows]
        if ids != baseline_ids:
            raise AssertionError(
                f"{name} changed fixed admission population"
            )

    reports = {
        name: _report(full_rows["CONTROL"], baseline, rows)
        for name, rows in filtered.items()
    }
    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "admission_variant": ADMISSION_VARIANT,
        "b_comparator_id": B_COMPARATOR_ID,
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "same_admission_population_all_variants": True,
            "entry_price_changed": False,
            "initial_stop_changed": False,
            "h3_changed": False,
            "soft_dol1_window_changed": False,
            "dol2_selector_changed": False,
            "post_acceptance_ps2_changed": False,
            "pretarget_breaker_protection_only_degree_of_freedom": True,
            "protection_can_only_improve_stop": True,
            "protection_effective_next_m1": True,
            "position_sizing_used": False,
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
    print(
        json.dumps(
            {
                "admission_variant": payload["admission_variant"],
                "b_comparator_id": payload["b_comparator_id"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
