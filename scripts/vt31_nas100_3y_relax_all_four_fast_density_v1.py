#!/usr/bin/env python3
"""Fast exact density truth for VT31 3Y RELAX_ALL_FOUR.

Measures selected -> terminal -> each causal downstream admission stage without
running expensive post-entry cognitive exit simulation. Therefore trade counts
and admission attrition are exact for this admission experiment; structural
exit economics are diagnostic only and are not a substitute for the separate
full current-position economic replay.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_breaker_mixed_weak_efficiency_adverse_exit_v1 as weak
import vt31_nas100_breaker_rotation_recovery_exception_frontier_v1 as recovery
import vt31_nas100_bullish_h1_mid_confirmation_conflict_admission_v1 as mid
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_rapid_breaker_conflict_admission_frontier_v1 as rapid
import vt31_nas100_specialist_r1_candidate as specialist

BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
SCHEMA = "qore.vt31.nas100.owner_3y.relax_all_four.fast_density_truth.v1"
TARGET_TRADES = 450
REASONABLE_DENSITY_FLOOR = 400
IGNORED = frozenset(
    {
        "SITUATION:CURRENT_PATH_NOT_COMPRESSED",
        "EXPERIENCE:NONCOMPRESSED_REFERENCE_OUTSIDE_LOW_DD_GATE",
        "EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE",
        "SITUATION:NO_REFERENCE_LIQUIDITY_STATE_BY_CUTOFF",
    }
)
TRANSIENT_WAIT = frozenset(
    {
        "STRATEGY:SOURCE_CONFIRMATION_NOT_COMPLETE",
        "STRATEGY:ENTRY_EVIDENCE_NOT_ACTIONABLE",
        "SITUATION:REFERENCE_LIQUIDITY_STATE_NOT_YET_PRESENT",
        "EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION",
    }
)


def _minimal(row: dict[str, object]) -> dict[str, object]:
    return {
        "signal_at": row["signal_at"],
        "local_date": row["local_date"],
        "entry_family": row.get("entry_family"),
        "side": row.get("side"),
        "r_multiple": row["r_multiple"],
        "exit_reason": row.get("exit_reason"),
    }


def _stage(
    name: str,
    before: list[dict[str, object]],
    after: list[dict[str, object]],
) -> dict[str, object]:
    kept = {str(row["signal_at"]) for row in after}
    removed = [
        row for row in before if str(row["signal_at"]) not in kept
    ]
    return {
        "stage": name,
        "input_count": len(before),
        "output_count": len(after),
        "removed_count": len(removed),
        "removed_structural_metrics_0_05r": (
            None
            if not removed
            else specialist._metrics(
                removed,
                friction=specialist.FRICTION,
            )
        ),
        "removed_rows": [_minimal(row) for row in removed],
    }


def replay(evidence_path: Path) -> dict[str, object]:
    evidence_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence_payload.get("base_id") != BASE_ID:
        raise ValueError("fast density truth requires canonical owner 3Y base")

    original_reason = specialist.reason
    original_simulator = specialist._simulate_selected_plan
    terminal_rows: list[dict[str, object]] = []
    demoted_counts: Counter[str] = Counter()

    def relaxed_reason(
        state: object,
        *,
        apply_comp008_admission: bool = False,
    ) -> object:
        raw = original_reason(
            state,
            apply_comp008_admission=apply_comp008_admission,
        )
        kept = tuple(
            code for code in raw.contradictions if code not in IGNORED
        )
        demoted = tuple(
            code for code in raw.contradictions if code in IGNORED
        )
        demoted_counts.update(demoted)
        if kept:
            action = "ABSTAIN"
        elif any(code in TRANSIENT_WAIT for code in raw.uncertainty):
            action = "WAIT"
        else:
            action = "EXECUTE"
        return replace(
            raw,
            action=action,
            contradictions=kept,
            context_observations=(
                *raw.context_observations,
                *(
                    "3Y_RELAX_ALL_FOUR:"
                    f"DEMOTED_ADMISSION_CONTRADICTION={code}"
                    for code in demoted
                ),
            ),
        )

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        outcome = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if outcome.get("status") == "terminal":
            outcome["target_plan"] = state["target_plan"]
            composition._attach_entry_context(outcome, state)
            terminal_rows.append(outcome)
        return outcome

    specialist.reason = relaxed_reason
    specialist._simulate_selected_plan = simulator
    try:
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist.reason = original_reason
        specialist._simulate_selected_plan = original_simulator

    structural_rows = cast(
        list[dict[str, object]],
        base_payload["trades"],
    )
    if [str(x["signal_at"]) for x in structural_rows] != [
        str(x["signal_at"]) for x in terminal_rows
    ]:
        raise AssertionError("terminal capture identity mismatch")

    stage0 = terminal_rows
    stage1 = [
        row
        for row in stage0
        if not admission._is_abstained(row, rapid.ADMISSION_BASE)
    ]
    stage2 = [
        row for row in stage1 if not recovery._should_abstain(row)
    ]
    stage3 = [
        row
        for row in stage2
        if not recovery._fvg_short_compressed_fresh_fast(row)
    ]
    stage4 = [
        row
        for row in stage3
        if not recovery._episode_breaker_bearish_compressed_bullish(row)
    ]
    stage5 = [
        row
        for row in stage4
        if not (rapid._conflict_a(row) or rapid._conflict_b(row))
    ]
    stage6 = [row for row in stage5 if not mid._conflict(row)]
    weak_identity = weak._apply_comp007_admission(stage0)
    if [str(x["signal_at"]) for x in weak_identity] != [
        str(x["signal_at"]) for x in stage5
    ]:
        raise AssertionError("manual Comparator-007 stage decomposition drift")
    final_count = len(stage6)

    action_counts = Counter(
        str(row.get("action", "UNKNOWN"))
        for row in cast(
            list[dict[str, object]],
            base_payload["reasoning_trace"],
        )
    )
    stages = [
        _stage("ADMISSION_BASE", stage0, stage1),
        _stage("RECOVERY_FILTER", stage1, stage2),
        _stage("FVG_SHORT_COMPRESSED_FRESH_FAST", stage2, stage3),
        _stage("BREAKER_BEARISH_COMPRESSED_BULLISH", stage3, stage4),
        _stage("RAPID_BREAKER_CONFLICT_UNION", stage4, stage5),
        _stage("BULLISH_H1_MID_CONFIRMATION_CONFLICT", stage5, stage6),
    ]
    result = {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "variant": "RELAX_ALL_FOUR",
        "selected_execute_days": action_counts["EXECUTE"],
        "selection_map_parity": action_counts["EXECUTE"] == 609,
        "status_counts": base_payload["status_counts"],
        "terminal_trade_count": len(stage0),
        "terminal_fill_rate_vs_selected": (
            "0"
            if action_counts["EXECUTE"] == 0
            else format(
                Decimal(len(stage0))
                / Decimal(action_counts["EXECUTE"]),
                "f",
            )
        ),
        "downstream_stages": stages,
        "final_admitted_trade_count": final_count,
        "final_selected_to_admitted_rate": (
            "0"
            if action_counts["EXECUTE"] == 0
            else format(
                Decimal(final_count)
                / Decimal(action_counts["EXECUTE"]),
                "f",
            )
        ),
        "target_trades_3y": TARGET_TRADES,
        "reasonable_density_floor": REASONABLE_DENSITY_FLOOR,
        "gap_to_450": TARGET_TRADES - final_count,
        "reasonable_density_gate_pass": (
            final_count >= REASONABLE_DENSITY_FLOOR
        ),
        "final_structural_exit_metrics_0_05r": specialist._metrics(
            stage6,
            friction=specialist.FRICTION,
        ),
        "demoted_contradiction_observation_counts": dict(
            sorted(demoted_counts.items())
        ),
        "final_rows": [_minimal(row) for row in stage6],
        "governance": {
            "research_only": True,
            "single_contiguous_3y_base": True,
            "post_entry_cognitive_exit_economics_included": False,
            "structural_exit_metrics_are_diagnostic_only": True,
            "outcome_used_for_admission_action": False,
            "future_information_used_for_admission_action": False,
            "sizing_or_leverage_used": False,
            "policy_promoted": False,
            "candidate_certified": False,
        },
    }
    return result


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
                "selected_execute_days": payload["selected_execute_days"],
                "status_counts": payload["status_counts"],
                "terminal_trade_count": payload["terminal_trade_count"],
                "downstream_stages": payload["downstream_stages"],
                "final_admitted_trade_count": payload[
                    "final_admitted_trade_count"
                ],
                "gap_to_450": payload["gap_to_450"],
                "reasonable_density_gate_pass": payload[
                    "reasonable_density_gate_pass"
                ],
                "final_structural_exit_metrics_0_05r": payload[
                    "final_structural_exit_metrics_0_05r"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
