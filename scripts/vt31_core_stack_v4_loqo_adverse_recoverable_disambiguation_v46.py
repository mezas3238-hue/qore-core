"""VT31 Shared LOQO adverse-vs-recoverable disambiguation V46.

Phase-1 temporal falsification only.

V43 proved that source-pure adverse phenotypes transfer with high loss recall,
but also flag many heldout winners. V46 learns a SECOND, independent causal
layer from source data only:

1. discover cross-fold source-pure adverse single/pair phenotypes exactly as V43;
2. among SOURCE trades flagged adverse, discover "winner rescue" signatures
   using V45's additional causal dimensions;
3. a rescue signature is eligible only if, in BOTH source folds, it has:
   - at least one adverse-flagged winner,
   - zero adverse-flagged losses;
4. evaluate untouched target quarter:
   - ADVERSE = matches V43 adverse phenotype;
   - RECOVERABLE_ADVERSE = ADVERSE + matches a source rescue signature;
   - TERMINAL_RISK_CANDIDATE = ADVERSE without rescue signature.

The target quarter is never used to select adverse or rescue rules.

No sizing, weighting, abstention, stop/target mutation, trailing, extension,
R5, fresh holdout, LIVE or production.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_heldout_winner_rescue_counter_signatures_v45 as v45

SCHEMA = "qore.core_stack_v4.vt31.loqo_adverse_recoverable_disambiguation.v46"
IDENTITY = "VT31_NAS100_SHARED_LOQO_ADVERSE_RECOVERABLE_DISAMBIGUATION_V46"
ZERO = Decimal("0")

v43 = v45.v43
v41 = v45.v41
v33 = v45.v33
v26 = v45.v26
v18 = v45.v18

EXTRA_FEATURES = tuple(v45.EXTRA_FEATURES)
RESCUE_VIEWS: tuple[tuple[str, str], ...] = tuple(
    (feature, mode)
    for feature in EXTRA_FEATURES
    for mode in ("PATH", "DELTA")
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _is_adverse(
    row: dict[str, object],
    *,
    single_rules: set[tuple[str, str]],
    pair_rules: set[tuple[str, str, str]],
) -> bool:
    return (
        v43._row_matches_single(row, single_rules)
        or v43._row_matches_pair(row, pair_rules)
    )


def _rescue_key(
    row: dict[str, object],
    *,
    feature: str,
    mode: str,
) -> tuple[str, str, str]:
    sequence = cast(dict[str, object], row["sequence"])
    return (
        feature,
        mode,
        v45._extra_signature(sequence, feature, mode),
    )


def _discover_rescue(
    source8: list[dict[str, object]],
    source6: list[dict[str, object]],
    *,
    single_rules: set[tuple[str, str]],
    pair_rules: set[tuple[str, str, str]],
) -> set[tuple[str, str, str]]:
    fold_groups: dict[
        str,
        dict[tuple[str, str, str], list[dict[str, object]]],
    ] = {
        "R8": defaultdict(list),
        "R6": defaultdict(list),
    }

    for fold, rows in (("R8", source8), ("R6", source6)):
        adverse_rows = [
            row
            for row in rows
            if _is_adverse(
                row,
                single_rules=single_rules,
                pair_rules=pair_rules,
            )
        ]
        for row in adverse_rows:
            for feature, mode in RESCUE_VIEWS:
                fold_groups[fold][
                    _rescue_key(row, feature=feature, mode=mode)
                ].append(row)

    shared = set(fold_groups["R8"]).intersection(fold_groups["R6"])
    rescue: set[tuple[str, str, str]] = set()
    for key in shared:
        valid = True
        for fold in ("R8", "R6"):
            members = fold_groups[fold][key]
            wins = sum(row["outcome"] == "WIN" for row in members)
            losses = sum(row["outcome"] == "LOSS" for row in members)
            if wins < 1 or losses != 0:
                valid = False
                break
        if valid:
            rescue.add(key)
    return rescue


def _matches_rescue(
    row: dict[str, object],
    rules: set[tuple[str, str, str]],
) -> bool:
    return any(
        _rescue_key(row, feature=feature, mode=mode) in rules
        for feature, mode in RESCUE_VIEWS
    )


def _evaluate(
    target: list[dict[str, object]],
    *,
    single_rules: set[tuple[str, str]],
    pair_rules: set[tuple[str, str, str]],
    rescue_rules: set[tuple[str, str, str]],
) -> dict[str, object]:
    adverse = [
        row
        for row in target
        if _is_adverse(
            row,
            single_rules=single_rules,
            pair_rules=pair_rules,
        )
    ]
    rescued = [row for row in adverse if _matches_rescue(row, rescue_rules)]
    terminal = [row for row in adverse if not _matches_rescue(row, rescue_rules)]

    losses = [row for row in target if row["outcome"] == "LOSS"]
    winners = [row for row in target if row["outcome"] == "WIN"]
    adverse_losses = [row for row in adverse if row["outcome"] == "LOSS"]
    adverse_winners = [row for row in adverse if row["outcome"] == "WIN"]
    rescued_losses = [row for row in rescued if row["outcome"] == "LOSS"]
    rescued_winners = [row for row in rescued if row["outcome"] == "WIN"]
    terminal_losses = [row for row in terminal if row["outcome"] == "LOSS"]
    terminal_winners = [row for row in terminal if row["outcome"] == "WIN"]

    adverse_winner_r = sum((_d(row["baseline_r"]) for row in adverse_winners), ZERO)
    rescued_winner_r = sum((_d(row["baseline_r"]) for row in rescued_winners), ZERO)
    terminal_winner_r = sum((_d(row["baseline_r"]) for row in terminal_winners), ZERO)
    terminal_loss_r = -sum((_d(row["baseline_r"]) for row in terminal_losses), ZERO)

    return {
        "sample": len(target),
        "losses": len(losses),
        "winners": len(winners),
        "adverse_flagged": len(adverse),
        "adverse_losses": len(adverse_losses),
        "adverse_winners": len(adverse_winners),
        "adverse_loss_recall": _ratio(len(adverse_losses), len(losses)),
        "adverse_winner_false_positive_rate": _ratio(
            len(adverse_winners),
            len(winners),
        ),
        "adverse_winner_r_exposure": format(adverse_winner_r, "f"),
        "rescued": len(rescued),
        "rescued_losses": len(rescued_losses),
        "rescued_winners": len(rescued_winners),
        "rescued_winner_r": format(rescued_winner_r, "f"),
        "terminal_risk_candidates": len(terminal),
        "terminal_losses": len(terminal_losses),
        "terminal_winners": len(terminal_winners),
        "terminal_loss_recall": _ratio(len(terminal_losses), len(losses)),
        "terminal_winner_false_positive_rate": _ratio(
            len(terminal_winners),
            len(winners),
        ),
        "terminal_loss_r_identified": format(terminal_loss_r, "f"),
        "terminal_winner_r_exposure": format(terminal_winner_r, "f"),
        "winner_count_reduction_vs_adverse": (
            len(adverse_winners) - len(terminal_winners)
        ),
        "winner_r_reduction_vs_adverse": format(
            adverse_winner_r - terminal_winner_r,
            "f",
        ),
        "loss_count_sacrificed_to_rescue": len(rescued_losses),
        "largest_terminal_false_winners": sorted(
            (
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": row["baseline_r"],
                }
                for row in terminal_winners
            ),
            key=lambda row: _d(row["baseline_r"]),
            reverse=True,
        )[:15],
        "largest_correctly_rescued_winners": sorted(
            (
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": row["baseline_r"],
                }
                for row in rescued_winners
            ),
            key=lambda row: _d(row["baseline_r"]),
            reverse=True,
        )[:15],
    }


def _target_run(
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
    rescue_rules = _discover_rescue(
        source8,
        source6,
        single_rules=single_rules,
        pair_rules=pair_rules,
    )
    evaluation = _evaluate(
        target,
        single_rules=single_rules,
        pair_rules=pair_rules,
        rescue_rules=rescue_rules,
    )
    return {
        "target_fold": target_fold,
        "target_quarter": target_quarter + 1,
        "target_used_for_adverse_rule_selection": False,
        "target_used_for_rescue_rule_selection": False,
        "single_rule_count": len(single_rules),
        "pair_rule_count": len(pair_rules),
        "rescue_rule_count": len(rescue_rules),
        "evaluation": evaluation,
    }


def _aggregate(runs: list[dict[str, object]]) -> dict[str, object]:
    evaluations = [
        cast(dict[str, object], row["evaluation"])
        for row in runs
    ]
    total_losses = sum(int(e["losses"]) for e in evaluations)
    total_winners = sum(int(e["winners"]) for e in evaluations)
    adverse_losses = sum(int(e["adverse_losses"]) for e in evaluations)
    adverse_winners = sum(int(e["adverse_winners"]) for e in evaluations)
    terminal_losses = sum(int(e["terminal_losses"]) for e in evaluations)
    terminal_winners = sum(int(e["terminal_winners"]) for e in evaluations)
    rescued_losses = sum(int(e["rescued_losses"]) for e in evaluations)
    rescued_winners = sum(int(e["rescued_winners"]) for e in evaluations)

    adverse_winner_r = sum(
        (_d(e["adverse_winner_r_exposure"]) for e in evaluations),
        ZERO,
    )
    terminal_winner_r = sum(
        (_d(e["terminal_winner_r_exposure"]) for e in evaluations),
        ZERO,
    )
    rescued_winner_r = sum(
        (_d(e["rescued_winner_r"]) for e in evaluations),
        ZERO,
    )
    terminal_loss_r = sum(
        (_d(e["terminal_loss_r_identified"]) for e in evaluations),
        ZERO,
    )

    return {
        "target_run_count": len(runs),
        "total_losses": total_losses,
        "total_winners": total_winners,
        "adverse_losses": adverse_losses,
        "adverse_winners": adverse_winners,
        "adverse_loss_recall": _ratio(adverse_losses, total_losses),
        "adverse_winner_false_positive_rate": _ratio(
            adverse_winners,
            total_winners,
        ),
        "adverse_winner_r_exposure": format(adverse_winner_r, "f"),
        "rescued_losses": rescued_losses,
        "rescued_winners": rescued_winners,
        "rescued_winner_r": format(rescued_winner_r, "f"),
        "terminal_losses": terminal_losses,
        "terminal_winners": terminal_winners,
        "terminal_loss_recall": _ratio(terminal_losses, total_losses),
        "terminal_winner_false_positive_rate": _ratio(
            terminal_winners,
            total_winners,
        ),
        "terminal_loss_r_identified": format(terminal_loss_r, "f"),
        "terminal_winner_r_exposure": format(terminal_winner_r, "f"),
        "winner_count_reduction_vs_adverse": adverse_winners - terminal_winners,
        "winner_r_reduction_vs_adverse": format(
            adverse_winner_r - terminal_winner_r,
            "f",
        ),
        "loss_count_sacrificed_to_rescue": rescued_losses,
        "all_target_runs_zero_terminal_winner": all(
            int(e["terminal_winners"]) == 0
            for e in evaluations
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
    target_runs = [
        _target_run(
            target_fold=fold,
            target_quarter=quarter,
            q8=q8,
            q6=q6,
        )
        for fold in ("R8", "R6")
        for quarter in range(4)
    ]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "LOQO_ADVERSE_RECOVERABLE_DISAMBIGUATION_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "rescue_feature_count": len(EXTRA_FEATURES),
        "rescue_view_count": len(RESCUE_VIEWS),
        "discovery_contract": {
            "target_used_for_adverse_rule_selection": False,
            "target_used_for_rescue_rule_selection": False,
            "rescue_requires_zero_source_losses_each_fold": True,
            "rescue_requires_minimum_one_source_winner_each_fold": True,
            "numeric_threshold_grid_search": False,
        },
        "target_runs": target_runs,
        "aggregate": _aggregate(target_runs),
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
            "target_outcomes_used_for_selection": False,
            "target_outcomes_used_for_evaluation_only": True,
            "classification_only_no_actuation": True,
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
                "aggregate": payload["aggregate"],
                "target_runs": payload["target_runs"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
