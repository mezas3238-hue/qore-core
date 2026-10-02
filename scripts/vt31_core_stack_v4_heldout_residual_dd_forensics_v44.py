"""VT31 Shared heldout residual DD phenotype forensics V44.

Phase-1 knowledge-gap diagnosis only.

V43 validates phenotype recognition with eight leave-one-quarter-out targets.
V44 uses the SAME source/target isolation, then inspects only the TARGET losses
that remained unrecognized and classifies why source knowledge could not safely
recognize them.

A missed target loss may be:
- PURE_LOW_SUPPORT: matching source phenotype(s) had zero source winners but
  failed the cross-fold minimum support required by V43;
- SOURCE_AMBIGUOUS: matching source phenotype(s) contained both source losses
  and source winners, so they were correctly withheld from pure recognition;
- SOURCE_WINNER_ONLY: matching source phenotype(s) had source winners but no
  source losses;
- NOVEL_TARGET_FORM: at least one exact target phenotype had never appeared in
  the source evidence;
- MULTI_CAUSE: more than one of the above applies.

Target outcomes are used only AFTER the heldout recognition decision, for
forensic diagnosis. Nothing discovered from a target quarter is fed back into
that quarter's recognition result.

No sizing, risk weighting, abstention, stop/target mutation, trailing, target
extension, R5, fresh holdout, LIVE or production.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_natural_dd_loqo_phenotype_validation_v43 as v43

SCHEMA = "qore.core_stack_v4.vt31.heldout_residual_dd_forensics.v44"
IDENTITY = "VT31_NAS100_SHARED_HELDOUT_RESIDUAL_DD_FORENSICS_V44"
ZERO = Decimal("0")

v42 = v43.v42
v41 = v43.v41
v33 = v41.v33
v26 = v41.v26
v18 = v41.v18

SINGLE_VIEWS = tuple(v43.SINGLE_VIEWS)
PAIR_VIEWS = tuple(v43.PAIR_VIEWS)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _source_single_groups(
    source8: list[dict[str, object]],
    source6: list[dict[str, object]],
) -> dict[tuple[str, str], dict[str, object]]:
    fold_groups: dict[str, dict[tuple[str, str], list[dict[str, object]]]] = {
        "R8": defaultdict(list),
        "R6": defaultdict(list),
    }
    for fold, rows in (("R8", source8), ("R6", source6)):
        for row in rows:
            sequence = cast(dict[str, object], row["sequence"])
            for view, keys in SINGLE_VIEWS:
                key = v43._single_signature(sequence, view, keys)
                fold_groups[fold][key].append(row)

    output: dict[tuple[str, str], dict[str, object]] = {}
    all_keys = set(fold_groups["R8"]) | set(fold_groups["R6"])
    for key in all_keys:
        payload: dict[str, object] = {"kind": "SINGLE", "key": key}
        for fold in ("R8", "R6"):
            members = fold_groups[fold].get(key, [])
            payload[fold] = {
                "sample": len(members),
                "losses": sum(row["outcome"] == "LOSS" for row in members),
                "wins": sum(row["outcome"] == "WIN" for row in members),
            }
        output[key] = payload
    return output


def _source_pair_groups(
    source8: list[dict[str, object]],
    source6: list[dict[str, object]],
) -> dict[tuple[str, str, str], dict[str, object]]:
    fold_groups: dict[
        str,
        dict[tuple[str, str, str], list[dict[str, object]]],
    ] = {
        "R8": defaultdict(list),
        "R6": defaultdict(list),
    }
    for fold, rows in (("R8", source8), ("R6", source6)):
        for row in rows:
            sequence = cast(dict[str, object], row["sequence"])
            for left, right in PAIR_VIEWS:
                key = v43._pair_signature(sequence, left, right)
                fold_groups[fold][key].append(row)

    output: dict[tuple[str, str, str], dict[str, object]] = {}
    all_keys = set(fold_groups["R8"]) | set(fold_groups["R6"])
    for key in all_keys:
        payload: dict[str, object] = {"kind": "PAIR", "key": key}
        for fold in ("R8", "R6"):
            members = fold_groups[fold].get(key, [])
            payload[fold] = {
                "sample": len(members),
                "losses": sum(row["outcome"] == "LOSS" for row in members),
                "wins": sum(row["outcome"] == "WIN" for row in members),
            }
        output[key] = payload
    return output


def _status(group: dict[str, object] | None) -> str:
    if group is None:
        return "NOVEL_TARGET_FORM"

    r8 = cast(dict[str, object], group["R8"])
    r6 = cast(dict[str, object], group["R6"])
    losses8, losses6 = int(r8["losses"]), int(r6["losses"])
    wins8, wins6 = int(r8["wins"]), int(r6["wins"])
    total_losses = losses8 + losses6
    total_wins = wins8 + wins6

    if total_wins == 0 and losses8 >= 2 and losses6 >= 2:
        return "SUPPORTED_PURE"
    if total_wins == 0 and total_losses > 0:
        return "PURE_LOW_SUPPORT"
    if total_losses > 0 and total_wins > 0:
        return "SOURCE_AMBIGUOUS"
    if total_losses == 0 and total_wins > 0:
        return "SOURCE_WINNER_ONLY"
    return "NOVEL_TARGET_FORM"


def _loss_forensics(
    row: dict[str, object],
    *,
    single_groups: dict[tuple[str, str], dict[str, object]],
    pair_groups: dict[tuple[str, str, str], dict[str, object]],
) -> dict[str, object]:
    sequence = cast(dict[str, object], row["sequence"])
    statuses: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)

    for view, keys in SINGLE_VIEWS:
        key = v43._single_signature(sequence, view, keys)
        status = _status(single_groups.get(key))
        statuses[status] += 1
        if len(examples[status]) < 4:
            examples[status].append(f"SINGLE:{key[0]}:{key[1]}")

    for left, right in PAIR_VIEWS:
        key = v43._pair_signature(sequence, left, right)
        status = _status(pair_groups.get(key))
        statuses[status] += 1
        if len(examples[status]) < 4:
            examples[status].append(
                f"PAIR:{key[0]}+{key[1]}:{key[2]}"
            )

    active_reasons = [
        reason
        for reason in (
            "PURE_LOW_SUPPORT",
            "SOURCE_AMBIGUOUS",
            "SOURCE_WINNER_ONLY",
            "NOVEL_TARGET_FORM",
        )
        if statuses[reason] > 0
    ]
    if len(active_reasons) > 1:
        primary = "MULTI_CAUSE"
    elif active_reasons:
        primary = active_reasons[0]
    else:
        # A genuinely missed loss should not have any supported-pure match.
        primary = "UNEXPECTED_SUPPORTED_PURE_ONLY"

    return {
        "signal_at": row["signal_at"],
        "baseline_r": row["baseline_r"],
        "primary_reason": primary,
        "reason_counts": dict(sorted(statuses.items())),
        "reason_examples": {
            key: value
            for key, value in sorted(examples.items())
        },
        "supported_pure_view_count": statuses["SUPPORTED_PURE"],
        "pure_low_support_view_count": statuses["PURE_LOW_SUPPORT"],
        "ambiguous_view_count": statuses["SOURCE_AMBIGUOUS"],
        "winner_only_view_count": statuses["SOURCE_WINNER_ONLY"],
        "novel_view_count": statuses["NOVEL_TARGET_FORM"],
    }


def _target_forensics(
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
    evaluation = v43._evaluate_target(
        target,
        single_rules=single_rules,
        pair_rules=pair_rules,
    )

    missed_losses = [
        row
        for row in target
        if row["outcome"] == "LOSS"
        and not v43._row_matches_single(row, single_rules)
        and not v43._row_matches_pair(row, pair_rules)
    ]

    single_groups = _source_single_groups(source8, source6)
    pair_groups = _source_pair_groups(source8, source6)
    forensic_rows = [
        _loss_forensics(
            row,
            single_groups=single_groups,
            pair_groups=pair_groups,
        )
        for row in missed_losses
    ]
    reasons = Counter(str(row["primary_reason"]) for row in forensic_rows)
    loss_r = -sum((_d(row["baseline_r"]) for row in missed_losses), ZERO)

    return {
        "target_fold": target_fold,
        "target_quarter": target_quarter + 1,
        "target_sample": len(target),
        "target_losses": int(evaluation["losses"]),
        "recognized_losses": int(evaluation["flagged_losses"]),
        "missed_losses": len(missed_losses),
        "missed_loss_r": format(loss_r, "f"),
        "reason_counts": dict(sorted(reasons.items())),
        "missed_loss_forensics": forensic_rows,
        "target_outcomes_used_for_rule_selection": False,
        "target_outcomes_used_for_forensics_only_after_decision": True,
    }


def _aggregate(targets: list[dict[str, object]]) -> dict[str, object]:
    all_rows = [
        row
        for target in targets
        for row in cast(
            list[dict[str, object]],
            target["missed_loss_forensics"],
        )
    ]
    reasons = Counter(str(row["primary_reason"]) for row in all_rows)
    total_missed = len(all_rows)
    total_loss_r = -sum((_d(row["baseline_r"]) for row in all_rows), ZERO)

    any_novel = sum(int(row["novel_view_count"]) > 0 for row in all_rows)
    any_low_support = sum(
        int(row["pure_low_support_view_count"]) > 0
        for row in all_rows
    )
    any_ambiguous = sum(
        int(row["ambiguous_view_count"]) > 0
        for row in all_rows
    )
    any_winner_only = sum(
        int(row["winner_only_view_count"]) > 0
        for row in all_rows
    )

    return {
        "target_count": len(targets),
        "total_missed_losses": total_missed,
        "total_missed_loss_r": format(total_loss_r, "f"),
        "primary_reason_counts": dict(sorted(reasons.items())),
        "missed_losses_with_any_novel_view": any_novel,
        "missed_losses_with_any_pure_low_support_view": any_low_support,
        "missed_losses_with_any_ambiguous_view": any_ambiguous,
        "missed_losses_with_any_winner_only_view": any_winner_only,
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

    targets = [
        _target_forensics(
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
        "status": "HELDOUT_RESIDUAL_DD_PHENOTYPE_FORENSICS_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "target_forensics": targets,
        "aggregate": _aggregate(targets),
        "forensic_contract": {
            "same_loqo_split_as_v43": True,
            "target_used_for_rule_selection": False,
            "target_outcome_used_only_after_recognition_decision": True,
            "missed_losses_only": True,
            "diagnosis_is_not_runtime_policy": True,
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
                "aggregate": payload["aggregate"],
                "target_summaries": [
                    {
                        "target_fold": row["target_fold"],
                        "target_quarter": row["target_quarter"],
                        "target_losses": row["target_losses"],
                        "recognized_losses": row["recognized_losses"],
                        "missed_losses": row["missed_losses"],
                        "missed_loss_r": row["missed_loss_r"],
                        "reason_counts": row["reason_counts"],
                    }
                    for row in payload["target_forensics"]
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
