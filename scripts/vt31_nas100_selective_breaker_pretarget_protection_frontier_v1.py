"""VT31 NAS100 selective Breaker pretarget protection frontier V1.

Consumed-evidence development only.

Fixed admission:
    A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M

Fixed B stack:
    H3 + W5 soft-DOL1 + full-cognition DOL2 + post-acceptance PS2

The experiment does NOT protect every Breaker. It tests causal protection only
when entry-time cognition identifies the residual regime-flip state:

- Breaker + M15 mixed;
- Breaker + M15 mixed + confirmation latency 3-5m.

Protection is one or two confirmed improving closed-M1 swings, effective from
the next M1, never widening the stop. No outcome, fold id, size, leverage or
capital engineering can influence the action.
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

SCHEMA = "qore.vt31.nas100.selective_breaker_pretarget_protection_frontier.v1"
ADMISSION_VARIANT = "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M"
B_COMPARATOR_ID = "VT31_BSIDE_H3_W5_DOL2_PS2_RESEARCH_COMPARATOR_001"
WINDOW = 5

VARIANTS: dict[str, tuple[str | None, int | None]] = {
    "CONTROL": (None, None),
    "BREAKER_M15_MIXED_PS1": ("M15_MIXED", 1),
    "BREAKER_M15_MIXED_PS2": ("M15_MIXED", 2),
    "BREAKER_M15_MIXED_CONFIRM_3_5_PS1": ("M15_MIXED_CONFIRM_3_5", 1),
    "BREAKER_M15_MIXED_CONFIRM_3_5_PS2": ("M15_MIXED_CONFIRM_3_5", 2),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _matches_selector(
    executable: object,
    state: dict[str, object],
    selector: str | None,
) -> bool:
    if selector is None:
        return False
    family = str(executable.selected_family.value)
    if family != "breaker":
        return False
    if str(state.get("m15_state")) != "mixed":
        return False
    if selector == "M15_MIXED":
        return True
    if selector == "M15_MIXED_CONFIRM_3_5":
        latency = state.get("confirmation_latency_minutes")
        if latency is None:
            return False
        minute = int(latency)
        return 3 <= minute <= 5
    raise ValueError(f"unsupported selector: {selector}")


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    selector: str | None,
    confirmations: int | None,
) -> dict[str, object]:
    applied = confirmations if _matches_selector(executable, state, selector) else None
    outcome = composition._simulate_composite(
        day_bars,
        executable,
        state,
        window=WINDOW,
        pretarget_breaker_ps_confirmations=applied,
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
        outcome["selective_breaker_protection_selector"] = selector
        outcome["selective_breaker_protection_eligible"] = (
            _matches_selector(executable, state, selector)
            if selector is not None
            else False
        )
    return outcome


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
    eligible = [
        row
        for row in rows
        if row.get("selective_breaker_protection_eligible") is True
    ]
    committed = [
        row
        for row in eligible
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
        "winner_preservation_vs_control": admission._winner_preservation(
            baseline,
            rows,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(rows),
        "selector_eligible_trade_count": len(eligible),
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

        for name, (selector, confirmations) in VARIANTS.items():
            outcome = _simulate(
                day_bars,
                executable,
                state,
                selector=selector,
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
        if [str(row["signal_at"]) for row in rows] != structural_ids:
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
        if [str(row["signal_at"]) for row in rows] != baseline_ids:
            raise AssertionError(
                f"{name} changed fixed admission population"
            )

    reports = {
        name: _report(full_rows["CONTROL"], baseline, rows)
        for name, rows in filtered.items()
    }
    control_map = {str(row["signal_at"]): row for row in baseline}
    for name, rows in filtered.items():
        candidate_map = {str(row["signal_at"]): row for row in rows}
        reports[name]["changed_trade_count_vs_control"] = sum(
            _d(candidate_map[key]["r_multiple"])
            != _d(control_map[key]["r_multiple"])
            for key in control_map
        )

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
            "selector_uses_entry_time_cognition_only": True,
            "selector_uses_m15_state": True,
            "selector_uses_confirmation_latency": True,
            "pretarget_protection_only_degree_of_freedom": True,
            "protection_can_only_improve_stop": True,
            "protection_effective_next_m1": True,
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
