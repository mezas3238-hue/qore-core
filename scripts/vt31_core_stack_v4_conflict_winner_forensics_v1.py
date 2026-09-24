"""R6 diagnostics for V4 Shared conflict decisions.

Research-only. Uses R8 as historical memory and R6 as consumed calibration.
R5 is never opened. Outcome fields are diagnostic labels only and are never
inputs to the conflict decision.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_ev_ensemble_v2 as ev
import vt31_core_stack_v4_high_resolution_perception_v1 as v4

POLICY = ev.Policy(
    maximum_analogs=48,
    minimum_similarity_bps=4000,
    minimum_confidence_bps=2000,
    conflict_ev_r=Decimal("-0.05"),
    favorable_ev_r=Decimal("0.30"),
    minimum_negative_views=3,
    caution_multiplier=Decimal("0.25"),
)

DIAGNOSTIC_FIELDS = (
    "side",
    "entry_family",
    "planned_target_r_native",
    "risk_ref",
    "raid_depth_ref",
    "entry_location_ref",
    "candidate_combo",
    "pre_behavior_proxy",
    "pre_path_efficiency",
    "pre_overlap_rate",
    "pre_fvg_count",
    "pre_sweep_reclaim_count",
    "pre_displacement_count",
    "pre_last5_range_fraction",
    "recent_path_efficiency_hr",
    "recent_overlap_rate_hr",
    "prior_day_state_hr",
    "prior_day_body_fraction_hr",
    "h4_state_hr",
    "h1_state_hr",
    "premarket_state_hr",
    "cash_open_state_hr",
    "position_in_prior_day_range_hr",
    "current_path_vs_previous_hr",
    "reference_width_vs_prior5_hr",
    "raid_depth_ref_hr",
    "prior_nas100_regime",
    "prior_peer_direction_state",
    "peer_consensus",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _numeric_summary(
    winners: list[dict[str, object]],
    losses: list[dict[str, object]],
) -> dict[str, object]:
    output: dict[str, object] = {}
    for field in DIAGNOSTIC_FIELDS:
        def vals(rows: list[dict[str, object]]) -> list[Decimal]:
            result: list[Decimal] = []
            for row in rows:
                raw = row.get(field)
                if raw is None or str(raw) in {"unavailable", "None"}:
                    continue
                try:
                    value = Decimal(str(raw))
                except Exception:
                    continue
                if value.is_finite():
                    result.append(value)
            return result

        win_values = vals(winners)
        loss_values = vals(losses)
        if not win_values or not loss_values:
            continue
        output[field] = {
            "winner_n": len(win_values),
            "loss_n": len(loss_values),
            "winner_mean": format(
                sum(win_values, Decimal(0)) / Decimal(len(win_values)),
                "f",
            ),
            "loss_mean": format(
                sum(loss_values, Decimal(0)) / Decimal(len(loss_values)),
                "f",
            ),
            "winner_min": format(min(win_values), "f"),
            "winner_max": format(max(win_values), "f"),
            "loss_min": format(min(loss_values), "f"),
            "loss_max": format(max(loss_values), "f"),
        }
    return output


def _categorical_summary(
    winners: list[dict[str, object]],
    losses: list[dict[str, object]],
) -> dict[str, object]:
    output: dict[str, object] = {}
    for field in DIAGNOSTIC_FIELDS:
        winner_counts = Counter(str(row.get(field)) for row in winners)
        loss_counts = Counter(str(row.get(field)) for row in losses)
        if len(winner_counts) <= 1 and len(loss_counts) <= 1:
            continue
        keys = sorted(set(winner_counts) | set(loss_counts))
        values: dict[str, object] = {}
        for key in keys:
            w = winner_counts[key]
            l = loss_counts[key]
            if w + l < 3:
                continue
            values[key] = {
                "winners": w,
                "losses": l,
                "winner_share": format(
                    Decimal(w) / Decimal(w + l),
                    "f",
                ),
            }
        if values:
            output[field] = values
    return output


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r8_raw: Path,
    r6_raw: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v4.v3._load_daily(daily_path)
    r8 = v4._raw_context(
        r8_raw,
        v4.v3._decorate(v4.v3._load_trades(r8_trades), daily),
    )
    r6 = v4._raw_context(
        r6_raw,
        v4.v3._decorate(v4.v3._load_trades(r6_trades), daily),
    )
    memories = {
        name: ev._memory(r8, fields)
        for name, fields in v4.VIEWS.items()
    }

    conflict: list[dict[str, object]] = []
    for source in r6:
        view = v4._ensemble(memories, source, POLICY)
        if view["disposition"] != "CONFLICT":
            continue
        row = {
            "local_date": source["local_date"],
            "signal_at": source["signal_at"],
            "net_r_after_friction": source["net_r_after_friction"],
            "diagnostic_outcome": (
                "WIN"
                if _d(source["net_r_after_friction"]) > 0
                else "LOSS"
            ),
            "shared_view": view,
        }
        for field in DIAGNOSTIC_FIELDS:
            row[field] = source.get(field)
        conflict.append(row)

    winners = [
        row for row in conflict
        if row["diagnostic_outcome"] == "WIN"
    ]
    losses = [
        row for row in conflict
        if row["diagnostic_outcome"] == "LOSS"
    ]
    winners.sort(
        key=lambda row: _d(row["net_r_after_friction"]),
        reverse=True,
    )
    return {
        "schema": "qore.core_stack_v4.vt31.conflict_winner_forensics.v1",
        "policy": POLICY.payload(),
        "r5_opened": False,
        "conflict_count": len(conflict),
        "conflict_winners": len(winners),
        "conflict_losses": len(losses),
        "winner_r_sacrificed": format(
            sum(
                (_d(row["net_r_after_friction"]) for row in winners),
                Decimal(0),
            ),
            "f",
        ),
        "loss_r_avoided": format(
            -sum(
                (_d(row["net_r_after_friction"]) for row in losses),
                Decimal(0),
            ),
            "f",
        ),
        "numeric_summary": _numeric_summary(winners, losses),
        "categorical_summary": _categorical_summary(winners, losses),
        "conflict_winner_rows": winners,
        "governance": {
            "r8_history_only": True,
            "r6_consumed_calibration": True,
            "r5_opened": False,
            "outcome_used_for_decision": False,
            "outcome_used_for_diagnostics_only": True,
            "live_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r8-raw", type=Path, required=True)
    parser.add_argument("--r6-raw", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r8_raw=args.r8_raw,
        r6_raw=args.r6_raw,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "conflict_count": payload["conflict_count"],
                "conflict_winners": payload["conflict_winners"],
                "conflict_losses": payload["conflict_losses"],
                "winner_r_sacrificed": payload["winner_r_sacrificed"],
                "loss_r_avoided": payload["loss_r_avoided"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
