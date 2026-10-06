"""VT31 NAS100 Breaker rotation admission frontier V1.

Consumed-evidence development only.

Fixed position comparator:
    VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT

Only degree of freedom:
    abstain a Breaker SHORT when prior-day state is rotation and the frozen
    09:00 reference-volatility state is compressed.

All admission inputs are available causally before entry. No outcome, fold,
date identity, size, leverage or capital engineering can influence action.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.breaker_rotation_admission_frontier.v1"
ADMISSION_BASE = "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M"
COMPARATOR_ID = "VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT"
POSITION_VARIANT = "BASE_PLUS_FVG_NONSHALLOW_OR_NONOB_NORMAL"

VARIANTS = (
    "COMP003_CONTROL",
    "ABSTAIN_BREAKER_SHORT_ROTATION_COMPRESSED",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _breaker_rotation_compressed(row: dict[str, object]) -> bool:
    if str(row["entry_family"]) != "breaker":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("prior_day_state")) == "rotation"
        and str(context.get("reference_volatility_state")) == "compressed"
    )


def _report(
    *,
    structural_count: int,
    comparator: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    kept = {str(row["signal_at"]) for row in rows}
    excluded = [
        row for row in comparator if str(row["signal_at"]) not in kept
    ]
    excluded_forensics = []
    for row in excluded:
        context = cast(dict[str, object], row.get("entry_context", {}))
        excluded_forensics.append(
            {
                "signal_at": row["signal_at"],
                "r_multiple": row["r_multiple"],
                "exit_reason": row["exit_reason"],
                "entry_family": row["entry_family"],
                "side": row["side"],
                "prior_day_state": context.get("prior_day_state"),
                "reference_volatility_state": context.get(
                    "reference_volatility_state"
                ),
                "h1_state": context.get("h1_state"),
                "m15_state": context.get("m15_state"),
                "cash_open_state": context.get("cash_open_state"),
                "premarket_state": context.get("premarket_state"),
                "reference_reclaim_age_minutes": context.get(
                    "reference_reclaim_age_minutes"
                ),
                "confirmation_latency_minutes": context.get(
                    "confirmation_latency_minutes"
                ),
                "entry_evidence_freshness": context.get(
                    "entry_evidence_freshness"
                ),
            }
        )
    return {
        "trade_count": len(rows),
        "relative_density_vs_structural": (
            "0"
            if structural_count == 0
            else format(
                Decimal(len(rows)) / Decimal(structural_count),
                "f",
            )
        ),
        "relative_density_vs_comp003": (
            "0"
            if not comparator
            else format(
                Decimal(len(rows)) / Decimal(len(comparator)),
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
        "winner_preservation_vs_comp003": admission._winner_preservation(
            comparator,
            rows,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(rows),
        "max_drawdown_episode_forensics": (
            adverse._max_drawdown_episode_forensics(
                comparator,
                rows,
            )
        ),
        "excluded_trade_count": len(comparator) - len(rows),
        "excluded_trade_forensics": excluded_forensics,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    comp003_rows: list[dict[str, object]] = []

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

        outcome = adverse._simulate(
            day_bars,
            executable,
            state,
            variant=POSITION_VARIANT,
        )
        if outcome.get("status") != "terminal":
            raise AssertionError(
                "Comparator 003 changed terminal eligibility: "
                f"{outcome}"
            )
        comp003_rows.append(outcome)
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
    if [str(row["signal_at"]) for row in comp003_rows] != structural_ids:
        raise AssertionError(
            "Comparator 003 changed sovereign terminal trade identity"
        )

    comparator = [
        row
        for row in comp003_rows
        if not admission._is_abstained(row, ADMISSION_BASE)
    ]
    candidate = [
        row
        for row in comparator
        if not _breaker_rotation_compressed(row)
    ]

    reports = {
        "COMP003_CONTROL": _report(
            structural_count=len(structural_rows),
            comparator=comparator,
            rows=comparator,
        ),
        "ABSTAIN_BREAKER_SHORT_ROTATION_COMPRESSED": _report(
            structural_count=len(structural_rows),
            comparator=comparator,
            rows=candidate,
        ),
    }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "admission_base": ADMISSION_BASE,
        "comparator_id": COMPARATOR_ID,
        "position_variant": POSITION_VARIANT,
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "same_position_logic_all_variants": True,
            "only_admission_degree_of_freedom": True,
            "breaker_family_used_for_action": True,
            "side_used_for_action": True,
            "prior_day_state_used_for_action": True,
            "reference_volatility_used_for_action": True,
            "new_numeric_threshold_added": False,
            "outcome_used_for_action": False,
            "excluded_trade_forensics_observation_only": True,
            "excluded_trade_forensics_action_authority": False,
            "max_drawdown_episode_forensics_observation_only": True,
            "max_drawdown_episode_forensics_action_authority": False,
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
