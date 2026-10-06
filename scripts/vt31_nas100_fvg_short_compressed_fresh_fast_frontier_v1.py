"""VT31 NAS100 FVG short compressed fresh-fast admission frontier V1.

Consumed-evidence development only.

Fixed integrated control:
- B-side Comparator 003;
- A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M;
- Breaker SHORT + prior-day rotation + compressed-reference abstention,
  except the bullish recovery sequence.

Only new degree of freedom:
    abstain FVG SHORT + compressed reference + FRESH_LT8M reclaim +
    FAST_LE5M confirmation.

All action inputs exist before entry. No outcome, fold/date identity, sizing,
leverage, compounding or capital state can influence action.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_breaker_rotation_recovery_exception_frontier_v1 as recovery
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.fvg_short_compressed_fresh_fast_frontier.v1"
ADMISSION_BASE = "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M"
B_COMPARATOR_ID = "VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT"
INTEGRATED_COMPARATOR_ID = (
    "VT31_AB_COMP004_BREAKER_ROTATION_WITH_BULLISH_RECOVERY_EXCEPTION"
)
POSITION_VARIANT = "BASE_PLUS_FVG_NONSHALLOW_OR_NONOB_NORMAL"
CANDIDATE = "ABSTAIN_FVG_SHORT_COMPRESSED_FRESH_FAST"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _fvg_short_compressed_fresh_fast(row: dict[str, object]) -> bool:
    if str(row["entry_family"]) != "fair-value-gap":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("reference_volatility_state")) == "compressed"
        and adverse._reclaim_sequence_state(
            context.get("reference_reclaim_age_minutes")
        )
        == "FRESH_LT8M"
        and adverse._confirmation_latency_state(
            context.get("confirmation_latency_minutes")
        )
        == "FAST_LE5M"
    )


def _report(
    *,
    structural_count: int,
    control: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "trade_count": len(rows),
        "relative_density_vs_control": (
            "0"
            if not control
            else format(Decimal(len(rows)) / Decimal(len(control)), "f")
        ),
        "relative_density_vs_structural": (
            "0"
            if not structural_count
            else format(Decimal(len(rows)) / Decimal(structural_count), "f")
        ),
        "stress_0_05r": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(rows),
        "halfyear_stress": specialist._block_metrics(rows, halfyear=True),
        "winner_preservation_vs_control": admission._winner_preservation(
            control,
            rows,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(rows),
        "max_drawdown_episode_forensics": adverse._max_drawdown_episode_forensics(
            control,
            rows,
        ),
        "excluded_trade_count": len(control) - len(rows),
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

    comp003 = [
        row
        for row in comp003_rows
        if not admission._is_abstained(row, ADMISSION_BASE)
    ]
    control = [
        row
        for row in comp003
        if not recovery._should_abstain(row)
    ]
    candidate = [
        row
        for row in control
        if not _fvg_short_compressed_fresh_fast(row)
    ]

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "admission_base": ADMISSION_BASE,
        "b_comparator_id": B_COMPARATOR_ID,
        "integrated_comparator_id": INTEGRATED_COMPARATOR_ID,
        "position_variant": POSITION_VARIANT,
        "variants": {
            "CURRENT_SURVIVOR_CONTROL": _report(
                structural_count=len(structural_rows),
                control=control,
                rows=control,
            ),
            CANDIDATE: _report(
                structural_count=len(structural_rows),
                control=control,
                rows=candidate,
            ),
        },
        "governance": {
            "consumed_evidence_only": True,
            "same_position_logic_all_variants": True,
            "only_new_admission_degree_of_freedom": True,
            "fvg_family_used_for_action": True,
            "short_side_used_for_action": True,
            "reference_volatility_used_for_action": True,
            "reclaim_bucket_used_for_action": True,
            "confirmation_latency_bucket_used_for_action": True,
            "reclaim_fresh_bucket_preexisting": True,
            "confirmation_fast_bucket_preexisting": True,
            "new_numeric_threshold_added": False,
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
