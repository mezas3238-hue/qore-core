"""VT31 NAS100 Comparator-007 residual drawdown forensics.

Observation-only consumed-evidence diagnostic.

This module does not change admission or position policy. It reconstructs the
exact stressed peak-to-trough path of the fixed Comparator-007 union survivor
and compares its trades with winning trades that share causal entry context.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_breaker_rotation_recovery_exception_frontier_v1 as recovery
import vt31_nas100_rapid_breaker_conflict_admission_frontier_v1 as rapid
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.comp007.residual_dd_forensics.v1"
COMPARATOR_ID = "VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR"

CONTEXT_KEYS = (
    "prior_day_state",
    "reference_volatility_state",
    "h4_state",
    "h1_state",
    "m15_state",
    "premarket_state",
    "cash_open_state",
    "position_in_prior_day_range",
    "liquidity_state",
    "raid_state",
    "efficiency_state",
    "overlap_state",
    "risk_geometry_state",
    "target_geometry_state",
    "destination_state",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _build_union_rows(
    evidence_path: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
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
            variant=rapid.POSITION_VARIANT,
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
        if not admission._is_abstained(row, rapid.ADMISSION_BASE)
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
    union = [
        row
        for row in comp006
        if not (rapid._conflict_a(row) or rapid._conflict_b(row))
    ]
    return structural_rows, union


def _signature(row: dict[str, object]) -> dict[str, str]:
    context = cast(dict[str, object], row.get("entry_context", {}))
    result = {
        "entry_family": str(row.get("entry_family")),
        "side": str(row.get("side")),
    }
    for key in CONTEXT_KEYS:
        result[key] = str(context.get(key))
    result["reclaim_bucket"] = adverse._reclaim_sequence_state(
        context.get("reference_reclaim_age_minutes")
    )
    result["confirmation_bucket"] = adverse._confirmation_latency_state(
        context.get("confirmation_latency_minutes")
    )
    return result


def _trade_forensics(
    row: dict[str, object],
    *,
    stressed_r: Decimal,
    equity_after: Decimal,
    drawdown_after: Decimal,
) -> dict[str, object]:
    context = cast(dict[str, object], row.get("entry_context", {}))
    selected_context = {
        key: context.get(key)
        for key in CONTEXT_KEYS
        if key in context
    }
    for key in (
        "reference_reclaim_age_minutes",
        "confirmation_latency_minutes",
        "reference_range_points",
        "risk_points",
        "target_points",
        "destination_points",
        "structure_event",
        "last_structure_event",
    ):
        if key in context:
            selected_context[key] = context.get(key)

    post_entry = {
        key: row.get(key)
        for key in (
            "current_open_r",
            "management_context_state",
            "management_trace",
            "position_trace",
            "cognitive_trace",
            "last_structure_event_family",
            "cognitive_exit_evaluations",
        )
        if key in row
    }

    return {
        "signal_at": row.get("signal_at"),
        "entry_family": row.get("entry_family"),
        "side": row.get("side"),
        "r_multiple": row.get("r_multiple"),
        "stressed_r": format(stressed_r, "f"),
        "exit_reason": row.get("exit_reason"),
        "equity_after_r": format(equity_after, "f"),
        "drawdown_after_r": format(drawdown_after, "f"),
        "signature": _signature(row),
        "entry_context": selected_context,
        "post_entry": post_entry,
    }


def _max_drawdown(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    equity = Decimal(0)
    peak = Decimal(0)
    peak_index = -1
    max_dd = Decimal(0)
    best_peak_index = -1
    trough_index = -1
    states: list[tuple[Decimal, Decimal, Decimal]] = []

    for index, row in enumerate(rows):
        value = _d(row["r_multiple"]) - specialist.FRICTION
        equity += value
        if equity > peak:
            peak = equity
            peak_index = index
        dd = peak - equity
        states.append((value, equity, dd))
        if dd > max_dd:
            max_dd = dd
            best_peak_index = peak_index
            trough_index = index

    start = best_peak_index + 1
    path = []
    if trough_index >= start:
        for index in range(start, trough_index + 1):
            value, eq, dd = states[index]
            path.append(
                _trade_forensics(
                    rows[index],
                    stressed_r=value,
                    equity_after=eq,
                    drawdown_after=dd,
                )
            )

    peak_trade = (
        None
        if best_peak_index < 0
        else {
            "index": best_peak_index,
            "signal_at": rows[best_peak_index].get("signal_at"),
            "equity_after_r": format(states[best_peak_index][1], "f"),
        }
    )
    recovery_trade = (
        None
        if trough_index + 1 >= len(rows)
        else {
            "index": trough_index + 1,
            "signal_at": rows[trough_index + 1].get("signal_at"),
            "r_multiple": rows[trough_index + 1].get("r_multiple"),
            "stressed_r": format(states[trough_index + 1][0], "f"),
        }
    )

    return {
        "max_drawdown_r": format(max_dd, "f"),
        "peak_index": best_peak_index,
        "trough_index": trough_index,
        "path_start_index": start,
        "path_trade_count": len(path),
        "peak_trade": peak_trade,
        "trough_signal_at": (
            None if trough_index < 0 else rows[trough_index].get("signal_at")
        ),
        "recovery_trade": recovery_trade,
        "path": path,
    }


def _matched_winners(
    rows: list[dict[str, object]],
    dd_path: list[dict[str, object]],
) -> list[dict[str, object]]:
    winners = [
        row
        for row in rows
        if _d(row["r_multiple"]) - specialist.FRICTION > 0
    ]
    winner_signatures = [(row, _signature(row)) for row in winners]
    result = []

    for item in dd_path:
        signature = cast(dict[str, str], item["signature"])
        ranked = []
        for winner, winner_signature in winner_signatures:
            matches = [
                key
                for key, value in signature.items()
                if winner_signature.get(key) == value
            ]
            ranked.append(
                {
                    "score": len(matches),
                    "matched_fields": matches,
                    "signal_at": winner.get("signal_at"),
                    "r_multiple": winner.get("r_multiple"),
                    "entry_family": winner.get("entry_family"),
                    "side": winner.get("side"),
                    "signature": winner_signature,
                }
            )
        ranked.sort(
            key=lambda x: (
                -int(cast(int, x["score"])),
                str(x["signal_at"]),
            )
        )
        result.append(
            {
                "drawdown_signal_at": item["signal_at"],
                "top_winner_matches": ranked[:3],
            }
        )
    return result


def _state_counts(
    dd_path: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    winners = [
        row
        for row in rows
        if _d(row["r_multiple"]) - specialist.FRICTION > 0
    ]
    fields = ("entry_family", "side", *CONTEXT_KEYS, "reclaim_bucket", "confirmation_bucket")
    report: dict[str, object] = {}
    dd_signatures = [
        cast(dict[str, str], item["signature"])
        for item in dd_path
    ]
    winner_signatures = [_signature(row) for row in winners]
    for field in fields:
        report[field] = {
            "drawdown_path": dict(
                Counter(signature.get(field, "None") for signature in dd_signatures)
            ),
            "winners": dict(
                Counter(signature.get(field, "None") for signature in winner_signatures)
            ),
        }
    return report


def replay(evidence_path: Path) -> dict[str, object]:
    structural_rows, union_rows = _build_union_rows(evidence_path)
    dd = _max_drawdown(union_rows)
    dd_path = cast(list[dict[str, object]], dd["path"])
    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "comparator_id": COMPARATOR_ID,
        "structural_trade_count": len(structural_rows),
        "comparator_trade_count": len(union_rows),
        "stress_friction_r_per_trade": format(specialist.FRICTION, "f"),
        "exact_drawdown": dd,
        "matched_winner_controls": _matched_winners(union_rows, dd_path),
        "state_counts": _state_counts(dd_path, union_rows),
        "governance": {
            "observation_only": True,
            "policy_change_authorized": False,
            "new_threshold_added": False,
            "outcome_labels_runtime_authority": False,
            "fold_identity_runtime_authority": False,
            "date_identity_runtime_authority": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "fresh_holdout_opened": False,
            "candidate_frozen": False,
            "candidate_certified": False,
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
