"""VT31 Shared natural-DD leave-one-quarter-out phenotype validation V43.

Phase-1 temporal falsification only.

V41/V42 build rich single-view and hierarchical pair phenotype registries on
consumed R8/R6 evidence. V43 prevents target leakage by splitting each fold into
four chronological quarters and repeating eight internal holdouts:

- one quarter is target and is NEVER used to select phenotype rules;
- the remaining 7 quarters are source;
- a source phenotype is eligible only when it has zero source winners and at
  least 2 source losses in BOTH R8 and R6;
- both single-view and pair-view phenotypes are discovered;
- the untouched target quarter is then evaluated.

Every trade is a target exactly once across the 8 evaluations. This is still
consumed research, not certification and not a fresh holdout.

No sizing, risk weighting, abstention, stop/target mutation, trailing, target
extension, R5, LIVE, or production.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_hierarchical_dd_phenotype_disambiguation_v42 as v42

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_loqo_phenotype_validation.v43"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_LOQO_PHENOTYPE_VALIDATION_V43"
ZERO = Decimal("0")

v41 = v42.v41
v33 = v41.v33
v26 = v41.v26
v18 = v41.v18

SINGLE_VIEWS = tuple(v41.ALL_VIEWS)
PAIR_VIEWS = tuple(v42.PAIR_VIEWS)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _quarters(rows: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    n = len(ordered)
    boundaries = [0, n // 4, n // 2, (3 * n) // 4, n]
    return [ordered[boundaries[i] : boundaries[i + 1]] for i in range(4)]


def _single_signature(
    sequence: dict[str, object],
    view: str,
    keys: tuple[str, ...],
) -> tuple[str, str]:
    return (view, v41._view_signature(sequence, keys))


def _pair_signature(
    sequence: dict[str, object],
    left: str,
    right: str,
) -> tuple[str, str, str]:
    return (left, right, v42._pair_signature(sequence, left, right))


def _discover_single(
    source8: list[dict[str, object]],
    source6: list[dict[str, object]],
) -> set[tuple[str, str]]:
    fold_groups: dict[str, dict[tuple[str, str], list[dict[str, object]]]] = {
        "R8": defaultdict(list),
        "R6": defaultdict(list),
    }
    for fold, rows in (("R8", source8), ("R6", source6)):
        groups = fold_groups[fold]
        for row in rows:
            sequence = cast(dict[str, object], row["sequence"])
            for view, keys in SINGLE_VIEWS:
                groups[_single_signature(sequence, view, keys)].append(row)

    shared = set(fold_groups["R8"]).intersection(fold_groups["R6"])
    eligible: set[tuple[str, str]] = set()
    for key in shared:
        good = True
        for fold in ("R8", "R6"):
            members = fold_groups[fold][key]
            losses = sum(row["outcome"] == "LOSS" for row in members)
            wins = sum(row["outcome"] == "WIN" for row in members)
            if wins != 0 or losses < 2:
                good = False
                break
        if good:
            eligible.add(key)
    return eligible


def _discover_pairs(
    source8: list[dict[str, object]],
    source6: list[dict[str, object]],
) -> set[tuple[str, str, str]]:
    fold_groups: dict[
        str,
        dict[tuple[str, str, str], list[dict[str, object]]],
    ] = {
        "R8": defaultdict(list),
        "R6": defaultdict(list),
    }
    for fold, rows in (("R8", source8), ("R6", source6)):
        groups = fold_groups[fold]
        for row in rows:
            sequence = cast(dict[str, object], row["sequence"])
            for left, right in PAIR_VIEWS:
                groups[_pair_signature(sequence, left, right)].append(row)

    shared = set(fold_groups["R8"]).intersection(fold_groups["R6"])
    eligible: set[tuple[str, str, str]] = set()
    for key in shared:
        good = True
        for fold in ("R8", "R6"):
            members = fold_groups[fold][key]
            losses = sum(row["outcome"] == "LOSS" for row in members)
            wins = sum(row["outcome"] == "WIN" for row in members)
            if wins != 0 or losses < 2:
                good = False
                break
        if good:
            eligible.add(key)
    return eligible


def _row_matches_single(
    row: dict[str, object],
    rules: set[tuple[str, str]],
) -> bool:
    sequence = cast(dict[str, object], row["sequence"])
    return any(
        _single_signature(sequence, view, keys) in rules
        for view, keys in SINGLE_VIEWS
    )


def _row_matches_pair(
    row: dict[str, object],
    rules: set[tuple[str, str, str]],
) -> bool:
    sequence = cast(dict[str, object], row["sequence"])
    return any(
        _pair_signature(sequence, left, right) in rules
        for left, right in PAIR_VIEWS
    )


def _evaluate_target(
    target: list[dict[str, object]],
    *,
    single_rules: set[tuple[str, str]],
    pair_rules: set[tuple[str, str, str]],
) -> dict[str, object]:
    flagged: list[dict[str, object]] = []
    for row in target:
        single = _row_matches_single(row, single_rules)
        pair = _row_matches_pair(row, pair_rules)
        if single or pair:
            flagged.append(
                {
                    **row,
                    "matched_single": single,
                    "matched_pair": pair,
                }
            )

    losses = [row for row in target if row["outcome"] == "LOSS"]
    winners = [row for row in target if row["outcome"] == "WIN"]
    flagged_losses = [row for row in flagged if row["outcome"] == "LOSS"]
    flagged_winners = [row for row in flagged if row["outcome"] == "WIN"]
    winner_r = sum((_d(row["baseline_r"]) for row in flagged_winners), ZERO)
    loss_r = -sum((_d(row["baseline_r"]) for row in flagged_losses), ZERO)

    single_only_losses = sum(
        row["outcome"] == "LOSS"
        and bool(row["matched_single"])
        and not bool(row["matched_pair"])
        for row in flagged
    )
    pair_only_losses = sum(
        row["outcome"] == "LOSS"
        and bool(row["matched_pair"])
        and not bool(row["matched_single"])
        for row in flagged
    )
    both_losses = sum(
        row["outcome"] == "LOSS"
        and bool(row["matched_single"])
        and bool(row["matched_pair"])
        for row in flagged
    )

    return {
        "sample": len(target),
        "losses": len(losses),
        "winners": len(winners),
        "flagged": len(flagged),
        "flagged_losses": len(flagged_losses),
        "loss_recall": _ratio(len(flagged_losses), len(losses)),
        "flagged_winners": len(flagged_winners),
        "winner_false_positive_rate": _ratio(
            len(flagged_winners),
            len(winners),
        ),
        "flagged_loss_r_identified": format(loss_r, "f"),
        "flagged_winner_r_exposure": format(winner_r, "f"),
        "single_only_flagged_losses": single_only_losses,
        "pair_only_flagged_losses": pair_only_losses,
        "single_and_pair_flagged_losses": both_losses,
        "flagged_winner_examples": sorted(
            (
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": row["baseline_r"],
                    "matched_single": row["matched_single"],
                    "matched_pair": row["matched_pair"],
                }
                for row in flagged_winners
            ),
            key=lambda row: _d(row["baseline_r"]),
            reverse=True,
        )[:20],
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

    single_rules = _discover_single(source8, source6)
    pair_rules = _discover_pairs(source8, source6)
    evaluation = _evaluate_target(
        target,
        single_rules=single_rules,
        pair_rules=pair_rules,
    )

    return {
        "target_fold": target_fold,
        "target_quarter": target_quarter + 1,
        "target_first_signal_at": (
            None if not target else target[0]["signal_at"]
        ),
        "target_last_signal_at": (
            None if not target else target[-1]["signal_at"]
        ),
        "source_r8_sample": len(source8),
        "source_r6_sample": len(source6),
        "discovered_single_rule_count": len(single_rules),
        "discovered_pair_rule_count": len(pair_rules),
        "target_used_for_rule_selection": False,
        "evaluation": evaluation,
    }


def _aggregate(runs: list[dict[str, object]]) -> dict[str, object]:
    evaluations = [
        cast(dict[str, object], run["evaluation"])
        for run in runs
    ]
    total_sample = sum(int(e["sample"]) for e in evaluations)
    total_losses = sum(int(e["losses"]) for e in evaluations)
    total_winners = sum(int(e["winners"]) for e in evaluations)
    flagged_losses = sum(int(e["flagged_losses"]) for e in evaluations)
    flagged_winners = sum(int(e["flagged_winners"]) for e in evaluations)
    loss_r = sum((_d(e["flagged_loss_r_identified"]) for e in evaluations), ZERO)
    winner_r = sum((_d(e["flagged_winner_r_exposure"]) for e in evaluations), ZERO)

    return {
        "target_run_count": len(runs),
        "total_target_sample": total_sample,
        "total_target_losses": total_losses,
        "total_target_winners": total_winners,
        "heldout_flagged_losses": flagged_losses,
        "heldout_loss_recall": _ratio(flagged_losses, total_losses),
        "heldout_flagged_winners": flagged_winners,
        "heldout_winner_false_positive_rate": _ratio(
            flagged_winners,
            total_winners,
        ),
        "heldout_loss_r_identified": format(loss_r, "f"),
        "heldout_winner_r_exposure": format(winner_r, "f"),
        "zero_winner_target_runs": sum(
            int(e["flagged_winners"]) == 0
            for e in evaluations
        ),
        "all_target_runs_zero_winner": all(
            int(e["flagged_winners"]) == 0
            for e in evaluations
        ),
        "single_only_flagged_losses": sum(
            int(e["single_only_flagged_losses"])
            for e in evaluations
        ),
        "pair_only_flagged_losses": sum(
            int(e["pair_only_flagged_losses"])
            for e in evaluations
        ),
        "single_and_pair_flagged_losses": sum(
            int(e["single_and_pair_flagged_losses"])
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

    q8 = _quarters(rows8)
    q6 = _quarters(rows6)
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
        "status": "LEAVE_ONE_QUARTER_OUT_PHENOTYPE_FALSIFICATION_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "split_contract": {
            "quarters_per_fold": 4,
            "target_run_count": 8,
            "method": "CHRONOLOGICAL_EQUAL_COUNT_QUARTERS",
            "target_quarter_used_for_rule_selection": False,
            "single_rule_cross_fold_support": "ZERO_WINNERS_AND_MIN_2_LOSSES_EACH_SOURCE_FOLD",
            "pair_rule_cross_fold_support": "ZERO_WINNERS_AND_MIN_2_LOSSES_EACH_SOURCE_FOLD",
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
            "outcomes_used_offline_in_source_for_rule_discovery": True,
            "target_outcomes_used_for_selection": False,
            "target_outcomes_used_for_evaluation_only": True,
            "registry_is_not_runtime_policy": True,
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
