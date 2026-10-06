"""VT31 NAS100 rapid Breaker conflict admission frontier V1.

Consumed-evidence development only.

Fixed integrated base:
    VT31_AB_COMP006_CLEAN_BREAKER_CONFLICT_SURVIVOR

Only degree of freedom:
- abstain narrow pre-entry causal Breaker conflict A;
- abstain narrow pre-entry causal Breaker conflict B;
- abstain A or B.

No outcome, fold/date identity, sizing, leverage, compounding, portfolio or
capital state can influence action.
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

SCHEMA = "qore.vt31.nas100.rapid_breaker_conflict_admission_frontier.v1"
ADMISSION_BASE = "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M"
COMPARATOR_ID = "VT31_AB_COMP006_CLEAN_BREAKER_CONFLICT_SURVIVOR"
POSITION_VARIANT = "BASE_PLUS_FVG_NONSHALLOW_OR_NONOB_NORMAL"

VARIANTS = (
    "COMP006_CONTROL",
    "COMP006_PLUS_H4_BULLISH_CONFLICT",
    "COMP006_PLUS_FRESH_MID_NORMAL_BREAKER",
    "COMP006_PLUS_RAPID_BREAKER_UNION",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _conflict_a(row: dict[str, object]) -> bool:
    if str(row["entry_family"]) != "breaker":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("prior_day_state")) == "bullish"
        and str(context.get("reference_volatility_state")) == "normal"
        and str(context.get("h4_state")) == "bullish"
        and str(context.get("h1_state")) == "mixed"
        and str(context.get("m15_state")) == "mixed"
        and str(context.get("premarket_state")) == "bearish"
        and str(context.get("cash_open_state")) == "bullish"
    )


def _conflict_b(row: dict[str, object]) -> bool:
    if str(row["entry_family"]) != "breaker":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("reference_volatility_state")) == "normal"
        and adverse._reclaim_sequence_state(
            context.get("reference_reclaim_age_minutes")
        )
        == "FRESH_LT8M"
        and adverse._confirmation_latency_state(
            context.get("confirmation_latency_minutes")
        )
        == "MID_6_10M"
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
    return {
        "trade_count": len(rows),
        "relative_density_vs_structural": (
            "0"
            if structural_count == 0
            else format(Decimal(len(rows)) / Decimal(structural_count), "f")
        ),
        "relative_density_vs_comp006": (
            "0"
            if not comparator
            else format(Decimal(len(rows)) / Decimal(len(comparator)), "f")
        ),
        "stress_0_05r": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(rows),
        "halfyear_stress": specialist._block_metrics(rows, halfyear=True),
        "winner_preservation_vs_comp006": admission._winner_preservation(
            comparator,
            rows,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(rows),
        "excluded_trade_count": len(excluded),
        "excluded_trade_forensics": [
            {
                "signal_at": row["signal_at"],
                "r_multiple": row["r_multiple"],
                "exit_reason": row["exit_reason"],
                "entry_family": row["entry_family"],
                "side": row["side"],
                "conflict_a": _conflict_a(row),
                "conflict_b": _conflict_b(row),
            }
            for row in excluded
        ],
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

    admitted = [
        row
        for row in comp003_rows
        if not admission._is_abstained(row, ADMISSION_BASE)
    ]
    recovery_filtered = [
        row for row in admitted if not recovery._should_abstain(row)
    ]
    fvg_filtered = [
        row
        for row in recovery_filtered
        if not recovery._fvg_short_compressed_fresh_fast(row)
    ]
    comp006 = [
        row
        for row in fvg_filtered
        if not recovery._episode_breaker_bearish_compressed_bullish(row)
    ]

    variant_rows = {
        "COMP006_CONTROL": comp006,
        "COMP006_PLUS_H4_BULLISH_CONFLICT": [
            row for row in comp006 if not _conflict_a(row)
        ],
        "COMP006_PLUS_FRESH_MID_NORMAL_BREAKER": [
            row for row in comp006 if not _conflict_b(row)
        ],
        "COMP006_PLUS_RAPID_BREAKER_UNION": [
            row
            for row in comp006
            if not (_conflict_a(row) or _conflict_b(row))
        ],
    }

    reports = {
        name: _report(
            structural_count=len(structural_rows),
            comparator=comp006,
            rows=rows,
        )
        for name, rows in variant_rows.items()
    }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "comparator_id": COMPARATOR_ID,
        "position_variant": POSITION_VARIANT,
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "same_position_logic_all_variants": True,
            "only_admission_degree_of_freedom": True,
            "conflict_a_entry_time_only": True,
            "conflict_b_entry_time_only": True,
            "preexisting_reclaim_bucket_used": True,
            "preexisting_confirmation_bucket_used": True,
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
