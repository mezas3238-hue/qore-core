"""VT31 NAS100 Comparator-010 live-context adverse exit frontier V1.

Consumed-evidence development only. Fresh holdout remains sealed.

Frozen control:
    VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR

Predeclared degrees of freedom:
A) materially-adverse FVG + current H1 MIXED + non-supportive management;
B) materially-adverse LONG + current M15 bearish + MIXED management;
C) union A or B.

All decisions use fully closed M1 cognition and execute only at next M1 open.
No new numeric threshold is introduced.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_breaker_mixed_weak_efficiency_adverse_exit_v1 as weak
import vt31_nas100_bullish_h1_mid_confirmation_conflict_admission_v1 as mid
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_live_cognitive_breaker_protection_frontier_v1 as live_cognition
import vt31_nas100_rapid_breaker_conflict_admission_frontier_v1 as rapid
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_cognitive_telemetry import (
    observe_cognitive_actuation,
)

SCHEMA = "qore.vt31.nas100.comp010.live_context_adverse_exit.v1"
COMPARATOR_ID = "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
LAB_CONTROL_ALIAS = "COMP006_CONTROL"

VARIANT_A = "COMP010_FVG_H1_MIXED_ADVERSE_EXIT"
VARIANT_B = "COMP010_LONG_M15_BEARISH_ADVERSE_EXIT"
VARIANT_UNION = "COMP010_FVG_H1_OR_LONG_M15_ADVERSE_EXIT"
VARIANTS = (
    LAB_CONTROL_ALIAS,
    VARIANT_A,
    VARIANT_B,
    VARIANT_UNION,
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _fvg_h1_mixed_allowed(
    diagnostic: dict[str, object],
    *,
    entry_family: str,
) -> bool:
    if entry_family != "fair-value-gap":
        return False
    if diagnostic.get("maximum_cognition_verified") is not True:
        return False
    if _d(diagnostic["current_open_r"]) > adverse.MATERIAL_ADVERSE_R:
        return False
    if str(diagnostic.get("h1_state")) != "mixed":
        return False
    return str(diagnostic.get("management_context")) in {"MIXED", "CAUTIOUS"}


def _long_m15_bearish_allowed(
    diagnostic: dict[str, object],
    *,
    side: str,
) -> bool:
    if side != "long":
        return False
    if diagnostic.get("maximum_cognition_verified") is not True:
        return False
    if _d(diagnostic["current_open_r"]) > adverse.MATERIAL_ADVERSE_R:
        return False
    if str(diagnostic.get("m15_state")) != "bearish":
        return False
    return str(diagnostic.get("management_context")) == "MIXED"


def _simulate_variant(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    variant: str,
) -> dict[str, object]:
    evaluations: list[dict[str, object]] = []
    entry_family = str(executable.selected_family.value)
    side = str(executable.side.value)
    reference_volatility_state = str(state["reference_volatility_state"])

    def exit_authorizer(
        bar: object,
        current_stop: Decimal,
    ) -> bool:
        observation_at = cast(datetime, bar.closed_at)
        _, diagnostic = live_cognition._live_cognitive_decision(
            day_bars=day_bars,
            executable=executable,
            state=state,
            observation_at=observation_at,
            current_stop=current_stop,
            candidate_stop=current_stop,
            confirmations=1,
            mode="WEAK_PATH",
        )
        comp007_allowed = adverse._exit_allowed(
            diagnostic,
            variant=rapid.POSITION_VARIANT,
            entry_family=entry_family,
            reference_volatility_state=reference_volatility_state,
        )
        comp009_weak_allowed = weak._extra_exit_allowed(
            diagnostic,
            entry_family=entry_family,
        )
        a_allowed = _fvg_h1_mixed_allowed(
            diagnostic,
            entry_family=entry_family,
        )
        b_allowed = _long_m15_bearish_allowed(
            diagnostic,
            side=side,
        )

        extra_allowed = False
        if variant == VARIANT_A:
            extra_allowed = a_allowed
        elif variant == VARIANT_B:
            extra_allowed = b_allowed
        elif variant == VARIANT_UNION:
            extra_allowed = a_allowed or b_allowed
        elif variant != LAB_CONTROL_ALIAS:
            raise AssertionError(f"unexpected variant: {variant}")

        allowed = comp007_allowed or comp009_weak_allowed or extra_allowed
        diagnostic["cognitive_exit_variant"] = variant
        diagnostic["cognitive_exit_authorized"] = allowed
        diagnostic["comp007_base_exit_authorized"] = comp007_allowed
        diagnostic["comp009_weak_efficiency_exit_authorized"] = (
            comp009_weak_allowed
        )
        diagnostic["comp010_fvg_h1_mixed_exit_authorized"] = a_allowed
        diagnostic["comp010_long_m15_bearish_exit_authorized"] = b_allowed
        diagnostic["comp010_extra_exit_authorized"] = extra_allowed
        diagnostic["actuation_sensor"] = observe_cognitive_actuation(
            expected_action=str(diagnostic["decision_action"]),
            routed_actions=("EXIT",) if allowed else (),
        ).payload()
        evaluations.append(diagnostic)
        return allowed

    outcome = composition._simulate_composite(
        day_bars,
        executable,
        state,
        window=adverse.WINDOW,
        pretarget_cognitive_exit_authorizer=exit_authorizer,
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
        outcome["cognitive_exit_variant"] = variant
        outcome["cognitive_exit_evaluations"] = evaluations
    return outcome


def _apply_comp009_admission(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    comp007_rows = weak._apply_comp007_admission(rows)
    return [row for row in comp007_rows if not mid._conflict(row)]


def _build_variant_rows(
    evidence_path: Path,
) -> tuple[
    list[dict[str, object]],
    dict[str, list[dict[str, object]]],
]:
    original = specialist._simulate_selected_plan
    position_rows: dict[str, list[dict[str, object]]] = {
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

        for name in VARIANTS:
            outcome = _simulate_variant(
                day_bars,
                executable,
                state,
                variant=name,
            )
            if outcome.get("status") != "terminal":
                raise AssertionError(
                    f"{name} changed sovereign terminal eligibility: "
                    f"{outcome}"
                )
            position_rows[name].append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(
        list[dict[str, object]],
        base_payload["trades"],
    )
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    for name, rows in position_rows.items():
        if [str(row["signal_at"]) for row in rows] != structural_ids:
            raise AssertionError(
                f"{name} changed sovereign terminal trade identity"
            )

    admitted = {
        name: _apply_comp009_admission(rows)
        for name, rows in position_rows.items()
    }
    control_ids = [
        str(row["signal_at"]) for row in admitted[LAB_CONTROL_ALIAS]
    ]
    for name, rows in admitted.items():
        if [str(row["signal_at"]) for row in rows] != control_ids:
            raise AssertionError(
                f"{name} changed Comparator-009 admitted trade identity"
            )
    return structural_rows, admitted


def _eligible_dates(
    evidence_path: Path,
) -> list[str]:
    series, _, _, _, _, _ = specialist.load_market_evidence(evidence_path)
    by_day: dict[object, list[object]] = defaultdict(list)
    for bar in series:
        by_day[specialist._day(bar.opened_at)].append(bar)
    eligible: list[str] = []
    for day in sorted(by_day):
        bars = tuple(
            sorted(
                by_day[day],
                key=lambda bar: bar.opened_at,
            )
        )
        if specialist._admitted_day(bars):
            eligible.append(day.isoformat())
    return eligible


def _minimal_rows(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "signal_at": row["signal_at"],
            "local_date": row["local_date"],
            "entry_family": row.get("entry_family"),
            "side": row.get("side"),
            "exit_reason": row.get("exit_reason"),
            "r_multiple": row["r_multiple"],
        }
        for row in rows
    ]


def _changed_trade_forensics(
    control: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> list[dict[str, object]]:
    left = {str(row["signal_at"]): row for row in control}
    right = {str(row["signal_at"]): row for row in candidate}
    if set(left) != set(right):
        raise AssertionError("position frontier changed admitted identity")

    changed: list[dict[str, object]] = []
    for signal_at in sorted(left):
        base = left[signal_at]
        cand = right[signal_at]
        base_r = _d(base["r_multiple"])
        cand_r = _d(cand["r_multiple"])
        if base_r == cand_r and base.get("exit_reason") == cand.get(
            "exit_reason"
        ):
            continue
        events = cast(
            list[dict[str, object]],
            cand.get("cognitive_exit_evaluations", []),
        )
        extra = [
            event
            for event in events
            if event.get("comp010_extra_exit_authorized") is True
        ]
        changed.append(
            {
                "signal_at": signal_at,
                "entry_family": cand.get("entry_family"),
                "side": cand.get("side"),
                "control_r": format(base_r, "f"),
                "candidate_r": format(cand_r, "f"),
                "delta_r": format(cand_r - base_r, "f"),
                "control_exit_reason": base.get("exit_reason"),
                "candidate_exit_reason": cand.get("exit_reason"),
                "entry_context": cand.get("entry_context", {}),
                "extra_authorization_events": extra,
            }
        )
    return changed


def _report(
    *,
    structural_count: int,
    control: list[dict[str, object]],
    rows: list[dict[str, object]],
    eligible_dates: list[str],
) -> dict[str, object]:
    winner = admission._winner_preservation(control, rows)
    changed = _changed_trade_forensics(control, rows)
    evaluations = [
        cast(dict[str, object], event)
        for row in rows
        for event in cast(
            list[dict[str, object]],
            row.get("cognitive_exit_evaluations", []),
        )
    ]
    density = (
        Decimal(0)
        if not control
        else Decimal(len(rows)) / Decimal(len(control))
    )
    return {
        "trade_count": len(rows),
        "relative_density_vs_comp006": format(density, "f"),
        "relative_density_vs_control": format(density, "f"),
        "relative_density_vs_structural": (
            "0"
            if structural_count == 0
            else format(
                Decimal(len(rows)) / Decimal(structural_count),
                "f",
            )
        ),
        "stress_0_05r": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(rows),
        "halfyear_stress": specialist._block_metrics(
            rows,
            halfyear=True,
        ),
        "winner_preservation_vs_comp006": winner,
        "winner_preservation_vs_control": winner,
        "changed_trade_count": len(changed),
        "changed_trade_forensics": changed,
        "candidate_rows": _minimal_rows(rows),
        "eligible_dates": eligible_dates,
        "cognitive_evaluation_count": len(evaluations),
        "comp010_extra_authorization_count": sum(
            event.get("comp010_extra_exit_authorized") is True
            for event in evaluations
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    structural_rows, variant_rows = _build_variant_rows(evidence_path)
    eligible_dates = _eligible_dates(evidence_path)
    control = variant_rows[LAB_CONTROL_ALIAS]
    reports = {
        name: _report(
            structural_count=len(structural_rows),
            control=control,
            rows=rows,
            eligible_dates=eligible_dates,
        )
        for name, rows in variant_rows.items()
    }
    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "comparator_id": COMPARATOR_ID,
        "lab_control_alias": LAB_CONTROL_ALIAS,
        "lab_control_research_identity": "COMP009_CONTROL",
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "control_is_exact_comp009_position_and_admission_stack": True,
            "same_admitted_trade_identity_all_variants": True,
            "only_position_exit_degree_of_freedom": True,
            "decision_on_fully_closed_m1": True,
            "execution_on_next_m1_open": True,
            "material_adverse_threshold_preexisting": True,
            "new_numeric_threshold_added": False,
            "maximum_cognition_required": True,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
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
