"""VT31 Shared heldout winner-rescue counter-signature atlas V45.

Phase-1 diagnostic only.

V43 showed that source-pure DD phenotypes transfer with high loss recall but
also flag many large heldout winners. V45 studies causal dimensions that were
NOT part of the V41/V42 phenotype views, looking for the missing distinction
between terminal adversity and recoverable adversity.

The target quarter remains excluded from rule discovery. V45 first reproduces
the V43 recognition decision, then uses target outcomes only offline to compare:
- heldout flagged losses;
- heldout false-positive winners.

Additional causal dimensions:
- trajectory deterioration/recovery velocity and persistence;
- environment adverse/recovery velocity and persistence;
- cross-market and structural fragility;
- trend support;
- uncertainty.

Only direction/path labels are used; no numeric threshold grid is fitted.

No actuation, sizing, weighting, abstention, stop/target mutation, trailing,
target extension, R5, fresh holdout, LIVE or production.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_natural_dd_loqo_phenotype_validation_v43 as v43

SCHEMA = "qore.core_stack_v4.vt31.heldout_winner_rescue_counter_signatures.v45"
IDENTITY = "VT31_NAS100_SHARED_HELDOUT_WINNER_RESCUE_COUNTER_SIGNATURES_V45"
ZERO = Decimal("0")

v41 = v43.v41
v33 = v41.v33
v26 = v41.v26
v18 = v41.v18

EXTRA_FEATURES = (
    "trajectory_deterioration_velocity_bps",
    "trajectory_recovery_velocity_bps",
    "trajectory_deterioration_persistence_bps",
    "trajectory_recovery_persistence_bps",
    "environment_adverse_velocity_bps",
    "environment_recovery_velocity_bps",
    "environment_adverse_persistence_bps",
    "environment_recovery_persistence_bps",
    "cross_market_fragility_bps",
    "structural_fragility_bps",
    "trend_support_bps",
    "uncertainty_bps",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _extra_signature(
    sequence: dict[str, object],
    feature: str,
    mode: str,
) -> str:
    path = cast(list[dict[str, object]], sequence["path"])
    values = [int(row[feature]) for row in path]
    if mode == "PATH":
        return v33._path_label(values)
    if mode == "DELTA":
        return v33._delta_label(values[0], values[-1])
    raise AssertionError(mode)


def _target_flagged_rows(
    *,
    target_fold: str,
    target_quarter: int,
    q8: list[list[dict[str, object]]],
    q6: list[list[dict[str, object]]],
) -> dict[str, object]:
    source8 = [
        row
        for quarter, rows in enumerate(q8)
        if not (target_fold == "R8" and quarter == target_quarter)
        for row in rows
    ]
    source6 = [
        row
        for quarter, rows in enumerate(q6)
        if not (target_fold == "R6" and quarter == target_quarter)
        for row in rows
    ]
    target = (
        q8[target_quarter]
        if target_fold == "R8"
        else q6[target_quarter]
    )
    single_rules = v43._discover_single(source8, source6)
    pair_rules = v43._discover_pairs(source8, source6)

    flagged: list[dict[str, object]] = []
    for row in target:
        single = v43._row_matches_single(row, single_rules)
        pair = v43._row_matches_pair(row, pair_rules)
        if single or pair:
            flagged.append(
                {
                    **row,
                    "matched_single": single,
                    "matched_pair": pair,
                    "target_fold": target_fold,
                    "target_quarter": target_quarter + 1,
                }
            )

    losses = [row for row in flagged if row["outcome"] == "LOSS"]
    winners = [row for row in flagged if row["outcome"] == "WIN"]
    return {
        "target_fold": target_fold,
        "target_quarter": target_quarter + 1,
        "flagged": flagged,
        "flagged_losses": losses,
        "flagged_winners": winners,
        "single_rule_count": len(single_rules),
        "pair_rule_count": len(pair_rules),
    }


def _atlas(
    target_groups: list[dict[str, object]],
) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    all_rows = [
        row
        for group in target_groups
        for row in cast(list[dict[str, object]], group["flagged"])
    ]

    for row in all_rows:
        sequence = cast(dict[str, object], row["sequence"])
        for feature in EXTRA_FEATURES:
            for mode in ("PATH", "DELTA"):
                value = _extra_signature(sequence, feature, mode)
                buckets[(feature, mode, value)].append(row)

    result: list[dict[str, object]] = []
    for (feature, mode, value), members in buckets.items():
        losses = [row for row in members if row["outcome"] == "LOSS"]
        winners = [row for row in members if row["outcome"] == "WIN"]
        winner_r = sum((_d(row["baseline_r"]) for row in winners), ZERO)
        loss_r = -sum((_d(row["baseline_r"]) for row in losses), ZERO)
        winner_quarters = {
            (str(row["target_fold"]), int(row["target_quarter"]))
            for row in winners
        }
        loss_quarters = {
            (str(row["target_fold"]), int(row["target_quarter"]))
            for row in losses
        }
        winner_folds = {str(row["target_fold"]) for row in winners}
        loss_folds = {str(row["target_fold"]) for row in losses}

        result.append(
            {
                "feature": feature,
                "mode": mode,
                "value": value,
                "sample": len(members),
                "losses": len(losses),
                "winners": len(winners),
                "loss_r": format(loss_r, "f"),
                "winner_r": format(winner_r, "f"),
                "winner_quarter_count": len(winner_quarters),
                "loss_quarter_count": len(loss_quarters),
                "winner_folds": tuple(sorted(winner_folds)),
                "loss_folds": tuple(sorted(loss_folds)),
                "winner_share": (
                    "0"
                    if not members
                    else format(
                        Decimal(len(winners)) / Decimal(len(members)),
                        "f",
                    )
                ),
                "winner_r_per_loss_r": (
                    None
                    if loss_r == ZERO
                    else format(winner_r / loss_r, "f")
                ),
                "diagnostic_only": True,
            }
        )

    result.sort(
        key=lambda row: (
            int(row["winner_quarter_count"]),
            _d(row["winner_r"]),
            int(row["winners"]),
            -int(row["losses"]),
        ),
        reverse=True,
    )
    return result


def _row_profile(row: dict[str, object]) -> dict[str, object]:
    sequence = cast(dict[str, object], row["sequence"])
    return {
        "signal_at": row["signal_at"],
        "baseline_r": row["baseline_r"],
        "target_fold": row["target_fold"],
        "target_quarter": row["target_quarter"],
        "matched_single": row["matched_single"],
        "matched_pair": row["matched_pair"],
        "macro_turn": sequence["macro_turn"],
        "micro_turn": sequence["micro_turn"],
        "extra_features": {
            feature: {
                "path": _extra_signature(sequence, feature, "PATH"),
                "delta": _extra_signature(sequence, feature, "DELTA"),
                "start": cast(list[dict[str, object]], sequence["path"])[0][feature],
                "end": cast(list[dict[str, object]], sequence["path"])[-1][feature],
            }
            for feature in EXTRA_FEATURES
        },
    }


def _summary(
    target_groups: list[dict[str, object]],
    atlas: list[dict[str, object]],
) -> dict[str, object]:
    losses = [
        row
        for group in target_groups
        for row in cast(list[dict[str, object]], group["flagged_losses"])
    ]
    winners = [
        row
        for group in target_groups
        for row in cast(list[dict[str, object]], group["flagged_winners"])
    ]
    winner_r = sum((_d(row["baseline_r"]) for row in winners), ZERO)
    loss_r = -sum((_d(row["baseline_r"]) for row in losses), ZERO)

    cross_fold_counter_signatures = [
        row
        for row in atlas
        if set(cast(tuple[str, ...], row["winner_folds"])) == {"R8", "R6"}
        and int(row["winner_quarter_count"]) >= 3
    ]
    return {
        "heldout_flagged_losses": len(losses),
        "heldout_false_positive_winners": len(winners),
        "heldout_flagged_loss_r": format(loss_r, "f"),
        "heldout_false_positive_winner_r": format(winner_r, "f"),
        "counter_signature_count": len(atlas),
        "cross_fold_recurrent_winner_counter_signatures": len(
            cross_fold_counter_signatures
        ),
    }


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
    daily = v33.v32.v31.v30.v28.v27.v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(
        daily_path
    )
    r8_source = v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6_source = v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8_source) != 228 or len(r6_source) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v26._prepare(
        r8_source,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v26._prepare(
        r6_source,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    rows8 = v41._all_sequence_rows(
        p8,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    rows6 = v41._all_sequence_rows(
        p6,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    q8 = v43._quarters(rows8)
    q6 = v43._quarters(rows6)

    target_groups = [
        _target_flagged_rows(
            target_fold=fold,
            target_quarter=quarter,
            q8=q8,
            q6=q6,
        )
        for fold in ("R8", "R6")
        for quarter in range(4)
    ]
    atlas = _atlas(target_groups)
    false_winners = sorted(
        (
            row
            for group in target_groups
            for row in cast(list[dict[str, object]], group["flagged_winners"])
        ),
        key=lambda row: _d(row["baseline_r"]),
        reverse=True,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "HELDOUT_WINNER_RESCUE_COUNTER_SIGNATURE_ATLAS_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "extra_features": EXTRA_FEATURES,
        "target_groups": [
            {
                "target_fold": group["target_fold"],
                "target_quarter": group["target_quarter"],
                "single_rule_count": group["single_rule_count"],
                "pair_rule_count": group["pair_rule_count"],
                "flagged_losses": len(
                    cast(list[dict[str, object]], group["flagged_losses"])
                ),
                "flagged_winners": len(
                    cast(list[dict[str, object]], group["flagged_winners"])
                ),
            }
            for group in target_groups
        ],
        "summary": _summary(target_groups, atlas),
        "counter_signature_atlas": atlas,
        "largest_false_positive_winners": [
            _row_profile(row) for row in false_winners[:25]
        ],
        "forensic_contract": {
            "same_loqo_split_as_v43": True,
            "target_used_for_rule_selection": False,
            "target_outcome_used_only_after_recognition_decision": True,
            "numeric_threshold_grid_search": False,
            "new_dimensions_not_used_by_v41_v42": True,
            "diagnostic_is_not_runtime_policy": True,
        },
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
            "realized_dd_reduction_claimed": False,
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
                "summary": payload["summary"],
                "counter_signature_atlas": payload[
                    "counter_signature_atlas"
                ][:60],
                "largest_false_positive_winners": payload[
                    "largest_false_positive_winners"
                ][:15],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
