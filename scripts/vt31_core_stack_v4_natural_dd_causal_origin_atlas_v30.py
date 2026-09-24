"""VT31 Shared natural drawdown causal-origin atlas V30.

Phase-1 diagnostic for SUPERINTELLIGENCE_009.

Purpose:
- preserve every methodology-valid trade and its original economic outcome;
- never change sizing, stop, target, density, capital or risk budget;
- label realized drawdown excursions OFFLINE only after the fact;
- ask which causal resident Shared states existed before the losses that formed
  the worst drawdown excursions;
- quantify overlap with valuable winners so later intelligence cannot "solve"
  DD by confusing recoverable/winning environments with terminal loss risk.

R8/R6 are consumed research folds. R5 and fresh holdouts remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_resident_instinct_signature_atlas_v28 as v28

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_causal_origin_atlas.v30"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_CAUSAL_ORIGIN_ATLAS_V30"
ZERO = Decimal("0")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _dt(value: object) -> datetime:
    return datetime.fromisoformat(str(value))


def _baseline_metrics(prepared: list[dict[str, object]]) -> dict[str, object]:
    return v28.v27._metrics([cast(Decimal, item["baseline_r"]) for item in prepared])


def _drawdown_excursions(
    prepared: list[dict[str, object]],
) -> list[dict[str, object]]:
    ordered = sorted(
        enumerate(prepared),
        key=lambda pair: cast(str, cast(dict[str, object], pair[1]["row"])["signal_at"]),
    )
    equity = ZERO
    peak = ZERO
    peak_order = -1
    trough_order = -1
    trough_dd = ZERO
    excursions: list[dict[str, object]] = []

    def close_excursion(end_order: int) -> None:
        nonlocal trough_order, trough_dd
        if trough_dd <= ZERO or trough_order < 0:
            trough_order = -1
            trough_dd = ZERO
            return
        start_order = peak_order + 1
        segment = ordered[start_order : trough_order + 1]
        excursions.append(
            {
                "depth_r": format(trough_dd, "f"),
                "peak_order": peak_order,
                "start_order": start_order,
                "trough_order": trough_order,
                "recovery_or_end_order": end_order,
                "item_indices": [idx for idx, _ in segment],
                "trades": len(segment),
                "losses": sum(
                    cast(Decimal, item["baseline_r"]) < ZERO
                    for _, item in segment
                ),
                "wins": sum(
                    cast(Decimal, item["baseline_r"]) > ZERO
                    for _, item in segment
                ),
                "start_signal_at": (
                    None
                    if not segment
                    else cast(dict[str, object], segment[0][1]["row"])["signal_at"]
                ),
                "trough_signal_at": (
                    None
                    if not segment
                    else cast(dict[str, object], segment[-1][1]["row"])["signal_at"]
                ),
            }
        )
        trough_order = -1
        trough_dd = ZERO

    for order, (_, item) in enumerate(ordered):
        equity += cast(Decimal, item["baseline_r"])
        if equity > peak:
            close_excursion(order)
            peak = equity
            peak_order = order
            continue
        dd = peak - equity
        if dd > trough_dd:
            trough_dd = dd
            trough_order = order

    close_excursion(len(ordered))
    excursions.sort(key=lambda row: _d(row["depth_r"]), reverse=True)
    for rank, excursion in enumerate(excursions, start=1):
        excursion["rank"] = rank
    return excursions


def _signature_rows(
    prepared: list[dict[str, object]],
    excursions: list[dict[str, object]],
) -> list[dict[str, object]]:
    max_indices = (
        set(cast(list[int], excursions[0]["item_indices"]))
        if excursions
        else set()
    )
    top3_indices: set[int] = set()
    for excursion in excursions[:3]:
        top3_indices.update(cast(list[int], excursion["item_indices"]))

    rows: list[dict[str, object]] = []
    for index, item in enumerate(prepared):
        source = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        context = cast(dict[str, object], item["entry_context"])
        instinct = v28.v27._instinct(context)
        outcome = "LOSS" if baseline_r < ZERO else "WIN" if baseline_r > ZERO else "FLAT"
        observable = bool(cast(list[dict[str, object]], item["events"]))

        lead_seconds: int | None = None
        if context.get("as_of") is not None and source.get("filled_at") is not None:
            lead_seconds = max(
                0,
                int((_dt(source["filled_at"]) - _dt(context["as_of"])).total_seconds()),
            )

        semantic = (
            f"T={v28._band(instinct.threat_bps)}|"
            f"U={v28._band(instinct.urgency_bps)}|"
            f"S={v28._band(instinct.structural_risk_bps)}|"
            f"R={v28._band(instinct.resilience_bps)}"
        )
        rows.append(
            {
                "index": index,
                "signal_at": source["signal_at"],
                "baseline_r": format(baseline_r, "f"),
                "outcome": outcome,
                "observable_postfill": observable,
                "unobservable_loss": outcome == "LOSS" and not observable,
                "in_max_dd_excursion": index in max_indices,
                "in_top3_dd_excursions": index in top3_indices,
                "lead_seconds_before_fill": lead_seconds,
                "situation": instinct.situation.value,
                "methodology": instinct.support_methodology.value,
                "environment_trajectory": (
                    f"{context['environment_state']}|{context['trajectory_state']}"
                ),
                "semantic_signature": semantic,
                "market_support_bps": instinct.market_support_bps,
                "threat_bps": instinct.threat_bps,
                "urgency_bps": instinct.urgency_bps,
                "shock_risk_bps": instinct.shock_risk_bps,
                "structural_risk_bps": instinct.structural_risk_bps,
                "resilience_bps": instinct.resilience_bps,
                "threat_convergence_bps": instinct.threat_convergence_bps,
                "confidence_bps": instinct.confidence_bps,
                "expansion_capacity_bps": instinct.expansion_capacity_bps,
            }
        )
    return rows


def _dimension_atlas(
    rows: list[dict[str, object]],
    *,
    key: str,
) -> dict[str, dict[str, object]]:
    buckets: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        buckets[str(row[key])].append(row)

    output: dict[str, dict[str, object]] = {}
    for value, members in buckets.items():
        losses = [row for row in members if row["outcome"] == "LOSS"]
        wins = [row for row in members if row["outcome"] == "WIN"]
        max_dd_losses = [
            row
            for row in losses
            if bool(row["in_max_dd_excursion"])
        ]
        top3_dd_losses = [
            row
            for row in losses
            if bool(row["in_top3_dd_excursions"])
        ]
        unobservable_losses = [
            row
            for row in losses
            if bool(row["unobservable_loss"])
        ]
        lead_values = [
            int(row["lead_seconds_before_fill"])
            for row in losses
            if row["lead_seconds_before_fill"] is not None
        ]
        output[value] = {
            "sample": len(members),
            "losses": len(losses),
            "wins": len(wins),
            "flats": len(members) - len(losses) - len(wins),
            "loss_rate": (
                "0"
                if not members
                else format(Decimal(len(losses)) / Decimal(len(members)), "f")
            ),
            "max_dd_losses": len(max_dd_losses),
            "top3_dd_losses": len(top3_dd_losses),
            "unobservable_losses": len(unobservable_losses),
            "total_r": format(
                sum((_d(row["baseline_r"]) for row in members), ZERO),
                "f",
            ),
            "loss_r": format(
                sum((_d(row["baseline_r"]) for row in losses), ZERO),
                "f",
            ),
            "winner_r": format(
                sum((_d(row["baseline_r"]) for row in wins), ZERO),
                "f",
            ),
            "minimum_lead_seconds_before_loss": (
                None if not lead_values else min(lead_values)
            ),
            "median_lead_seconds_before_loss": (
                None
                if not lead_values
                else sorted(lead_values)[len(lead_values) // 2]
            ),
        }
    return dict(sorted(output.items()))


def _fold(
    prepared: list[dict[str, object]],
) -> dict[str, object]:
    excursions = _drawdown_excursions(prepared)
    rows = _signature_rows(prepared, excursions)
    baseline = _baseline_metrics(prepared)
    max_dd = excursions[0] if excursions else None
    top3_depth = sum((_d(row["depth_r"]) for row in excursions[:3]), ZERO)

    loss_rows = [row for row in rows if row["outcome"] == "LOSS"]
    winner_rows = [row for row in rows if row["outcome"] == "WIN"]
    max_dd_losses = [
        row for row in loss_rows if bool(row["in_max_dd_excursion"])
    ]
    top3_losses = [
        row for row in loss_rows if bool(row["in_top3_dd_excursions"])
    ]
    unobservable_losses = [
        row for row in loss_rows if bool(row["unobservable_loss"])
    ]

    return {
        "baseline": baseline,
        "drawdown": {
            "max_excursion": max_dd,
            "top5_excursions": excursions[:5],
            "top3_depth_sum_r_nonadditive_diagnostic": format(top3_depth, "f"),
            "losses_in_max_excursion": len(max_dd_losses),
            "losses_in_top3_excursions": len(top3_losses),
            "unobservable_losses": len(unobservable_losses),
            "total_losses": len(loss_rows),
            "total_winners": len(winner_rows),
        },
        "atlases": {
            "situation": _dimension_atlas(rows, key="situation"),
            "methodology": _dimension_atlas(rows, key="methodology"),
            "environment_trajectory": _dimension_atlas(
                rows,
                key="environment_trajectory",
            ),
            "semantic_signature": _dimension_atlas(
                rows,
                key="semantic_signature",
            ),
        },
        "offline_labels_only": True,
        "runtime_outcome_input_used": False,
        "actuation_used": False,
    }


def _stable_cross_fold(
    r8: dict[str, object],
    r6: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    a8 = cast(dict[str, dict[str, dict[str, object]]], r8["atlases"])
    a6 = cast(dict[str, dict[str, dict[str, object]]], r6["atlases"])

    for dimension in (
        "situation",
        "methodology",
        "environment_trajectory",
        "semantic_signature",
    ):
        d8 = a8[dimension]
        d6 = a6[dimension]
        rows: list[dict[str, object]] = []
        for value in sorted(set(d8).intersection(d6)):
            x = d8[value]
            y = d6[value]
            combined_max_dd = int(x["max_dd_losses"]) + int(y["max_dd_losses"])
            combined_top3_dd = int(x["top3_dd_losses"]) + int(y["top3_dd_losses"])
            combined_losses = int(x["losses"]) + int(y["losses"])
            combined_wins = int(x["wins"]) + int(y["wins"])
            diagnostic_ratio = Decimal(combined_top3_dd) / Decimal(1 + combined_wins)
            rows.append(
                {
                    "value": value,
                    "r8": x,
                    "r6": y,
                    "combined_max_dd_losses": combined_max_dd,
                    "combined_top3_dd_losses": combined_top3_dd,
                    "combined_losses": combined_losses,
                    "combined_wins": combined_wins,
                    "top3_dd_loss_to_winner_diagnostic_ratio": format(
                        diagnostic_ratio,
                        "f",
                    ),
                    "runtime_policy_claim": False,
                }
            )
        rows.sort(
            key=lambda row: (
                int(row["combined_top3_dd_losses"]),
                _d(row["top3_dd_loss_to_winner_diagnostic_ratio"]),
                int(row["combined_losses"]),
            ),
            reverse=True,
        )
        result[dimension] = rows
    return result


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v28.v27.v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(daily_path)
    r8_rows = v28.v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6_rows = v28.v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8_rows) != 228 or len(r6_rows) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v28.v27.v26._prepare(
        r8_rows,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v28.v27.v26._prepare(
        r6_rows,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )

    f8 = _fold(p8)
    f6 = _fold(p6)
    stable = _stable_cross_fold(f8, f6)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "DIAGNOSTIC_ONLY_NO_POLICY_FREEZE",
        "challenge_set": {"r8": 228, "r6": 278},
        "r8": f8,
        "r6": f6,
        "cross_fold_stable_causal_atlas": stable,
        "phase_1_contract": {
            "same_trade_universe": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "capital_weighting_used": False,
            "entry_abstention_used": False,
            "stop_geometry_mutated": False,
            "target_geometry_mutated": False,
            "trailing_used": False,
            "target_extension_used": False,
            "offline_outcomes_used_only_for_labels": True,
            "runtime_outcome_input_used": False,
            "future_market_input_used": False,
            "r5_opened": False,
            "new_holdout_opened": False,
        },
        "governance": {
            "vt31_is_falsification_lab_only": True,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "r8": payload["r8"],
                "r6": payload["r6"],
                "cross_fold_stable_causal_atlas": payload[
                    "cross_fold_stable_causal_atlas"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
