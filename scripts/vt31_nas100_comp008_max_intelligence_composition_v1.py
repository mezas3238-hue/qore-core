"""VT31 NAS100 Comparator-008 maximum-intelligence composition V1.

Consumed-evidence development only.

Frozen components:
- Comparator 008 admission survivor.
- Previously validated Breaker MIXED weak-efficiency adverse exit.

No new threshold or market rule is introduced here.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_breaker_mixed_weak_efficiency_adverse_exit_v1 as weak
import vt31_nas100_bullish_h1_mid_confirmation_conflict_admission_v1 as mid
import vt31_nas100_comp007_residual_dd_forensics_v1 as comp007
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.comp008_max_intelligence_composition.v1"
BASE_COMPARATOR_ID = "VT31_AB_COMP008_BULLISH_H1_MID_CONFIRMATION_SURVIVOR"
VARIANT = "COMP008_PLUS_BREAKER_MIXED_WEAK_EFFICIENCY_EXIT"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _apply_comp008_admission(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [row for row in rows if not mid._conflict(row)]


def _changed_trade_forensics(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> list[dict[str, object]]:
    left = {str(row["signal_at"]): row for row in baseline}
    right = {str(row["signal_at"]): row for row in candidate}
    if set(left) != set(right):
        raise AssertionError(
            "composition changed Comparator-008 admitted trade identity"
        )

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
            if event.get(
                "breaker_mixed_weak_efficiency_exit_authorized"
            )
            is True
        ]
        changed.append(
            {
                "signal_at": signal_at,
                "entry_family": cand.get("entry_family"),
                "side": cand.get("side"),
                "baseline_r": format(base_r, "f"),
                "candidate_r": format(cand_r, "f"),
                "delta_r": format(cand_r - base_r, "f"),
                "baseline_exit_reason": base.get("exit_reason"),
                "candidate_exit_reason": cand.get("exit_reason"),
                "entry_context": cand.get("entry_context", {}),
                "extra_authorization_events": extra,
            }
        )
    return changed


def _report(
    *,
    structural_count: int,
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    baseline_ids = [str(row["signal_at"]) for row in baseline]
    candidate_ids = [str(row["signal_at"]) for row in candidate]
    changed = _changed_trade_forensics(baseline, candidate)
    evaluations = [
        cast(dict[str, object], event)
        for row in candidate
        for event in cast(
            list[dict[str, object]],
            row.get("cognitive_exit_evaluations", []),
        )
    ]
    return {
        "trade_count": len(candidate),
        "same_trade_identity_vs_comp008": baseline_ids == candidate_ids,
        "relative_density_vs_structural": (
            "0"
            if structural_count == 0
            else format(
                Decimal(len(candidate)) / Decimal(structural_count),
                "f",
            )
        ),
        "relative_density_vs_comp008": (
            "0"
            if not baseline
            else format(
                Decimal(len(candidate)) / Decimal(len(baseline)),
                "f",
            )
        ),
        "stress_0_05r": specialist._metrics(
            candidate,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(candidate),
        "halfyear_stress": specialist._block_metrics(
            candidate,
            halfyear=True,
        ),
        "winner_preservation_vs_comp008": admission._winner_preservation(
            baseline,
            candidate,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(candidate),
        "changed_trade_count": len(changed),
        "changed_trade_forensics": changed,
        "cognitive_evaluation_count": len(evaluations),
        "extra_authorization_count": sum(
            event.get(
                "breaker_mixed_weak_efficiency_exit_authorized"
            )
            is True
            for event in evaluations
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    structural_base, comp007_rows = comp007._build_union_rows(evidence_path)
    comp008_rows = _apply_comp008_admission(comp007_rows)

    structural_candidate, weak_rows = weak._build_candidate_rows(
        evidence_path
    )
    base_ids = [str(row["signal_at"]) for row in structural_base]
    candidate_structural_ids = [
        str(row["signal_at"]) for row in structural_candidate
    ]
    if base_ids != candidate_structural_ids:
        raise AssertionError("structural replay identity changed")

    combined = _apply_comp008_admission(weak_rows)
    if [str(row["signal_at"]) for row in comp008_rows] != [
        str(row["signal_at"]) for row in combined
    ]:
        raise AssertionError(
            "composition changed Comparator-008 admitted trade identity"
        )

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "base_comparator_id": BASE_COMPARATOR_ID,
        "variant": VARIANT,
        "baseline": {
            "trade_count": len(comp008_rows),
            "stress_0_05r": specialist._metrics(
                comp008_rows,
                friction=specialist.FRICTION,
            ),
            "monte_carlo": specialist._monte_carlo(comp008_rows),
            "halfyear_stress": specialist._block_metrics(
                comp008_rows,
                halfyear=True,
            ),
        },
        "candidate": _report(
            structural_count=len(structural_candidate),
            baseline=comp008_rows,
            candidate=combined,
        ),
        "governance": {
            "consumed_evidence_only": True,
            "base_is_frozen_comp008": True,
            "only_prevalidated_components_composed": True,
            "same_comp008_admission": True,
            "same_target_stack_until_validated_cognitive_exit": True,
            "next_m1_open_execution": True,
            "maximum_cognition_required": True,
            "material_adverse_threshold_preexisting": True,
            "weak_efficiency_threshold_preexisting": True,
            "mid_confirmation_bucket_preexisting": True,
            "new_numeric_threshold_added": False,
            "new_market_rule_added": False,
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
