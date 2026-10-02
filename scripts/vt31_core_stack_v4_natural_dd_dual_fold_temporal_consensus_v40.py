"""VT31 Shared natural-DD dual-fold temporal consensus transfer V40.

Phase-1 consumed-fold robustness diagnostic.

V39 showed that morphology rules discovered in one temporal half of one fold
can transfer with unacceptable winner exposure. V40 strengthens discovery:

FORWARD:
- discover winner-safe morphologies independently in R8 EARLY and R6 EARLY;
- keep only the exact cross-fold consensus intersection;
- test unchanged on R8 LATE and R6 LATE.

BACKWARD:
- discover independently in R8 LATE and R6 LATE;
- keep only the exact cross-fold consensus intersection;
- test unchanged on R8 EARLY and R6 EARLY.

Target halves never participate in rule selection. Local DD labels are computed
inside source/target halves only.

No numeric feature threshold grid. No actuation, sizing, capital weighting,
entry abstention, stop/target mutation, trailing or target extension.
R5 and fresh holdout remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_natural_dd_temporal_morphology_transfer_v39 as v39

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_dual_fold_temporal_consensus.v40"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_DUAL_FOLD_TEMPORAL_CONSENSUS_V40"
ZERO = Decimal("0")

v38 = v39.v38
v34 = v39.v34
v33 = v39.v33
v26 = v39.v26
v18 = v39.v18


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _key(rule: v39.TemporalMorphologyRule) -> tuple[str, str]:
    return (rule.projection, rule.signature)


def _consensus(
    left: tuple[v39.TemporalMorphologyRule, ...],
    right: tuple[v39.TemporalMorphologyRule, ...],
) -> tuple[v39.TemporalMorphologyRule, ...]:
    right_keys = {_key(rule) for rule in right}
    return tuple(rule for rule in left if _key(rule) in right_keys)


def _consensus_payload(
    left: tuple[v39.TemporalMorphologyRule, ...],
    right: tuple[v39.TemporalMorphologyRule, ...],
    consensus: tuple[v39.TemporalMorphologyRule, ...],
) -> list[dict[str, object]]:
    lmap = {_key(rule): rule for rule in left}
    rmap = {_key(rule): rule for rule in right}
    output: list[dict[str, object]] = []
    for rule in consensus:
        a, b = lmap[_key(rule)], rmap[_key(rule)]
        output.append(
            {
                "projection": rule.projection,
                "keys": rule.keys,
                "signature": rule.signature,
                "source_a": a.payload(),
                "source_b": b.payload(),
                "combined_source_losses": (
                    a.discovery_losses + b.discovery_losses
                ),
                "combined_source_top3_dd_losses": (
                    a.discovery_top3_dd_losses
                    + b.discovery_top3_dd_losses
                ),
                "combined_source_loss_r": format(
                    a.discovery_loss_r + b.discovery_loss_r,
                    "f",
                ),
            }
        )
    output.sort(
        key=lambda row: (
            int(row["combined_source_top3_dd_losses"]),
            int(row["combined_source_losses"]),
            _d(row["combined_source_loss_r"]),
        ),
        reverse=True,
    )
    return output


def _split_rows(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    early, late = v39._temporal_split(rows)
    return v39._local_dd_labels(early), v39._local_dd_labels(late)


def _direction(
    *,
    name: str,
    source_a_name: str,
    source_a: list[dict[str, object]],
    source_b_name: str,
    source_b: list[dict[str, object]],
    target_a_name: str,
    target_a: list[dict[str, object]],
    target_b_name: str,
    target_b: list[dict[str, object]],
) -> dict[str, object]:
    rules_a = v39._discover(source_a)
    rules_b = v39._discover(source_b)
    consensus = _consensus(rules_a, rules_b)
    eval_a = v39._evaluate(target_a, rules=consensus)
    eval_b = v39._evaluate(target_b, rules=consensus)

    return {
        "name": name,
        "source_a": source_a_name,
        "source_b": source_b_name,
        "target_a": target_a_name,
        "target_b": target_b_name,
        "source_a_rule_count": len(rules_a),
        "source_b_rule_count": len(rules_b),
        "consensus_rule_count": len(consensus),
        "consensus_rules": _consensus_payload(
            rules_a,
            rules_b,
            consensus,
        ),
        "target_a_evaluation": eval_a,
        "target_b_evaluation": eval_b,
        "target_halves_used_for_selection": False,
        "summary": {
            "target_flagged_losses": (
                int(eval_a["flagged_losses"])
                + int(eval_b["flagged_losses"])
            ),
            "target_flagged_winners": (
                int(eval_a["flagged_winners"])
                + int(eval_b["flagged_winners"])
            ),
            "target_winner_r_exposure": format(
                _d(eval_a["flagged_winner_r_exposure"])
                + _d(eval_b["flagged_winner_r_exposure"]),
                "f",
            ),
            "both_targets_zero_winner": (
                int(eval_a["flagged_winners"]) == 0
                and int(eval_b["flagged_winners"]) == 0
            ),
        },
    }


def _bidirectional_consensus(
    forward: dict[str, object],
    backward: dict[str, object],
) -> list[dict[str, object]]:
    f = {
        (str(row["projection"]), str(row["signature"])): row
        for row in cast(list[dict[str, object]], forward["consensus_rules"])
    }
    b = {
        (str(row["projection"]), str(row["signature"])): row
        for row in cast(list[dict[str, object]], backward["consensus_rules"])
    }
    return [
        {
            "projection": key[0],
            "signature": key[1],
            "forward": f[key],
            "backward": b[key],
            "runtime_policy_claim": False,
        }
        for key in sorted(set(f).intersection(b))
    ]


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
    rows8 = v34._annotated_fold(p8, sp_evidence=r8_sp, us_evidence=r8_us)
    rows6 = v34._annotated_fold(p6, sp_evidence=r6_sp, us_evidence=r6_us)
    r8_early, r8_late = _split_rows(rows8)
    r6_early, r6_late = _split_rows(rows6)

    forward = _direction(
        name="EARLY_CROSS_FOLD_TO_LATE",
        source_a_name="R8_EARLY",
        source_a=r8_early,
        source_b_name="R6_EARLY",
        source_b=r6_early,
        target_a_name="R8_LATE",
        target_a=r8_late,
        target_b_name="R6_LATE",
        target_b=r6_late,
    )
    backward = _direction(
        name="LATE_CROSS_FOLD_TO_EARLY",
        source_a_name="R8_LATE",
        source_a=r8_late,
        source_b_name="R6_LATE",
        source_b=r6_late,
        target_a_name="R8_EARLY",
        target_a=r8_early,
        target_b_name="R6_EARLY",
        target_b=r6_early,
    )
    bidirectional = _bidirectional_consensus(forward, backward)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "DUAL_FOLD_TEMPORAL_CONSENSUS_NO_ACTUATION",
        "source_hypothesis": "COMPOSITE_PRECISION_ORIGIN",
        "projection_count": len(v38.PROJECTIONS),
        "discovery_contract": {
            "zero_winners_required_in_each_source_half": True,
            "minimum_losses_in_each_source_half": 3,
            "minimum_local_top3_dd_losses_in_each_source_half": 1,
            "cross_fold_consensus_required_before_target_test": True,
            "target_halves_used_for_selection": False,
            "numeric_feature_threshold_grid_search": False,
        },
        "challenge_set": {"r8": 228, "r6": 278},
        "forward": forward,
        "backward": backward,
        "bidirectional_consensus_count": len(bidirectional),
        "bidirectional_consensus": bidirectional,
        "summary": {
            "forward_both_targets_zero_winner": cast(
                dict[str, object],
                forward["summary"],
            )["both_targets_zero_winner"],
            "backward_both_targets_zero_winner": cast(
                dict[str, object],
                backward["summary"],
            )["both_targets_zero_winner"],
            "both_directions_zero_winner": (
                bool(
                    cast(dict[str, object], forward["summary"])[
                        "both_targets_zero_winner"
                    ]
                )
                and bool(
                    cast(dict[str, object], backward["summary"])[
                        "both_targets_zero_winner"
                    ]
                )
            ),
            "runtime_policy_claim": False,
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
            "outcomes_used_offline_for_source_discovery_and_target_evaluation": True,
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
                "forward": payload["forward"],
                "backward": payload["backward"],
                "bidirectional_consensus": payload["bidirectional_consensus"],
                "summary": payload["summary"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
