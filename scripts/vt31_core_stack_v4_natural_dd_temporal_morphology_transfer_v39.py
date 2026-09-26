"""VT31 Shared natural-DD temporal morphology transfer V39.

Phase-1 consumed-fold temporal transfer diagnostic.

The fixed V38 categorical projections are retained, but morphology signatures
are discovered from only one chronological half and evaluated unchanged on the
other half:
- R8 EARLY -> R8 LATE
- R8 LATE -> R8 EARLY
- R6 EARLY -> R6 LATE
- R6 LATE -> R6 EARLY

Target halves do not participate in rule discovery. Local drawdown labels are
recomputed inside each half so discovery does not depend on the target half's
equity path.

No numeric feature threshold grid. No actuation, sizing, capital weighting,
entry abstention, stop/target mutation, trailing or target extension.
R5 and fresh holdout remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_natural_dd_reciprocal_morphology_v38 as v38

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_temporal_morphology_transfer.v39"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_TEMPORAL_MORPHOLOGY_TRANSFER_V39"
ZERO = Decimal("0")

v34 = v38.v34
v33 = v38.v33
v26 = v38.v26
v18 = v38.v18


@dataclass(frozen=True, slots=True)
class TemporalMorphologyRule:
    projection: str
    keys: tuple[str, ...]
    signature: str
    discovery_losses: int
    discovery_top3_dd_losses: int
    discovery_loss_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "projection": self.projection,
            "keys": self.keys,
            "signature": self.signature,
            "discovery_losses": self.discovery_losses,
            "discovery_top3_dd_losses": self.discovery_top3_dd_losses,
            "discovery_loss_r": format(self.discovery_loss_r, "f"),
        }


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _temporal_split(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    midpoint = len(ordered) // 2
    return ordered[:midpoint], ordered[midpoint:]


def _local_dd_labels(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    equity = ZERO
    peak = ZERO
    active: list[dict[str, object]] = []
    excursions: list[tuple[Decimal, tuple[str, ...]]] = []
    max_depth = ZERO
    max_signals: tuple[str, ...] = ()

    for row in ordered:
        value = _d(row["baseline_r"])
        equity += value
        if equity > peak:
            if active and max_depth > ZERO:
                excursions.append((max_depth, max_signals))
            peak = equity
            active = []
            max_depth = ZERO
            max_signals = ()
            continue

        active.append(row)
        depth = peak - equity
        if depth > max_depth:
            max_depth = depth
            max_signals = tuple(str(x["signal_at"]) for x in active)

    if active and max_depth > ZERO:
        excursions.append((max_depth, max_signals))

    excursions.sort(key=lambda item: item[0], reverse=True)
    top3_signals: set[str] = set()
    for _, signals in excursions[:3]:
        top3_signals.update(signals)
    max_dd_signals = set(excursions[0][1]) if excursions else set()

    return [
        {
            **row,
            "temporal_top3_dd": str(row["signal_at"]) in top3_signals,
            "temporal_max_dd": str(row["signal_at"]) in max_dd_signals,
        }
        for row in rows
    ]


def _discover(
    rows: list[dict[str, object]],
) -> tuple[TemporalMorphologyRule, ...]:
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if not bool(row["source_origin_match"]):
            continue
        sequence = cast(dict[str, object] | None, row["sequence"])
        if sequence is None:
            continue
        for projection, keys in v38.PROJECTIONS:
            signature = v38._signature(sequence, keys)
            groups[(projection, signature)].append(row)

    output: list[TemporalMorphologyRule] = []
    projection_keys = dict(v38.PROJECTIONS)
    for (projection, signature), members in groups.items():
        winners = [row for row in members if row["outcome"] == "WIN"]
        losses = [row for row in members if row["outcome"] == "LOSS"]
        top3 = [
            row for row in losses if bool(row["temporal_top3_dd"])
        ]
        if winners or len(losses) < 3 or len(top3) < 1:
            continue
        output.append(
            TemporalMorphologyRule(
                projection=projection,
                keys=projection_keys[projection],
                signature=signature,
                discovery_losses=len(losses),
                discovery_top3_dd_losses=len(top3),
                discovery_loss_r=-sum(
                    (_d(row["baseline_r"]) for row in losses),
                    ZERO,
                ),
            )
        )

    output.sort(
        key=lambda rule: (
            rule.discovery_top3_dd_losses,
            rule.discovery_losses,
            rule.discovery_loss_r,
        ),
        reverse=True,
    )
    return tuple(output)


def _evaluate(
    rows: list[dict[str, object]],
    *,
    rules: tuple[TemporalMorphologyRule, ...],
) -> dict[str, object]:
    flagged: list[dict[str, object]] = []
    for row in rows:
        if not bool(row["source_origin_match"]):
            continue
        sequence = cast(dict[str, object] | None, row["sequence"])
        if sequence is None:
            continue
        matched = tuple(
            f"{rule.projection}:{rule.signature}"
            for rule in rules
            if v38._signature(sequence, rule.keys) == rule.signature
        )
        if matched:
            flagged.append({**row, "matched_morphologies": matched})

    losses = [row for row in rows if row["outcome"] == "LOSS"]
    winners = [row for row in rows if row["outcome"] == "WIN"]
    flagged_losses = [row for row in flagged if row["outcome"] == "LOSS"]
    flagged_winners = [row for row in flagged if row["outcome"] == "WIN"]
    top3 = [row for row in losses if bool(row["temporal_top3_dd"])]
    flagged_top3 = [
        row for row in flagged_losses if bool(row["temporal_top3_dd"])
    ]
    max_dd = [row for row in losses if bool(row["temporal_max_dd"])]
    flagged_max_dd = [
        row for row in flagged_losses if bool(row["temporal_max_dd"])
    ]
    unobservable = [row for row in losses if bool(row["unobservable_loss"])]
    flagged_unobservable = [
        row for row in flagged_losses if bool(row["unobservable_loss"])
    ]

    total_winner_r = sum((_d(row["baseline_r"]) for row in winners), ZERO)
    winner_r = sum((_d(row["baseline_r"]) for row in flagged_winners), ZERO)
    loss_r = -sum((_d(row["baseline_r"]) for row in flagged_losses), ZERO)
    top3_loss_r = -sum((_d(row["baseline_r"]) for row in flagged_top3), ZERO)

    return {
        "sample": len(rows),
        "rules_received": len(rules),
        "flagged": len(flagged),
        "flagged_fraction": _ratio(len(flagged), len(rows)),
        "losses": len(losses),
        "flagged_losses": len(flagged_losses),
        "loss_recall": _ratio(len(flagged_losses), len(losses)),
        "max_dd_losses": len(max_dd),
        "flagged_max_dd_losses": len(flagged_max_dd),
        "max_dd_loss_recall": _ratio(len(flagged_max_dd), len(max_dd)),
        "top3_dd_losses": len(top3),
        "flagged_top3_dd_losses": len(flagged_top3),
        "top3_dd_loss_recall": _ratio(len(flagged_top3), len(top3)),
        "unobservable_losses": len(unobservable),
        "flagged_unobservable_losses": len(flagged_unobservable),
        "unobservable_loss_recall": _ratio(
            len(flagged_unobservable),
            len(unobservable),
        ),
        "winners": len(winners),
        "flagged_winners": len(flagged_winners),
        "winner_false_positive_rate": _ratio(
            len(flagged_winners),
            len(winners),
        ),
        "total_winner_r": format(total_winner_r, "f"),
        "flagged_winner_r_exposure": format(winner_r, "f"),
        "winner_r_false_positive_exposure": (
            "0"
            if total_winner_r == ZERO
            else format(winner_r / total_winner_r, "f")
        ),
        "flagged_loss_r_identified": format(loss_r, "f"),
        "flagged_top3_dd_loss_r_identified": format(top3_loss_r, "f"),
        "flagged_winner_examples": sorted(
            (
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": row["baseline_r"],
                    "matched_morphologies": row["matched_morphologies"],
                }
                for row in flagged_winners
            ),
            key=lambda row: _d(row["baseline_r"]),
            reverse=True,
        )[:20],
        "actuation_used": False,
        "runtime_policy_claim": False,
    }


def _transfer(
    *,
    fold: str,
    source_name: str,
    source_rows: list[dict[str, object]],
    target_name: str,
    target_rows: list[dict[str, object]],
) -> dict[str, object]:
    rules = _discover(source_rows)
    target = _evaluate(target_rows, rules=rules)
    return {
        "fold": fold,
        "source_half": source_name,
        "target_half": target_name,
        "source_sample": len(source_rows),
        "target_sample": len(target_rows),
        "discovered_rules": [rule.payload() for rule in rules],
        "target_evaluation": target,
        "target_half_used_for_rule_selection": False,
    }


def _fold_transfers(
    rows: list[dict[str, object]],
    *,
    fold: str,
) -> dict[str, object]:
    early, late = _temporal_split(rows)
    early_labeled = _local_dd_labels(early)
    late_labeled = _local_dd_labels(late)
    return {
        "split_contract": {
            "method": "CHRONOLOGICAL_EQUAL_COUNT_HALVES",
            "early_sample": len(early_labeled),
            "late_sample": len(late_labeled),
            "early_first_signal_at": (
                None if not early_labeled else early_labeled[0]["signal_at"]
            ),
            "early_last_signal_at": (
                None if not early_labeled else early_labeled[-1]["signal_at"]
            ),
            "late_first_signal_at": (
                None if not late_labeled else late_labeled[0]["signal_at"]
            ),
            "late_last_signal_at": (
                None if not late_labeled else late_labeled[-1]["signal_at"]
            ),
        },
        "early_to_late": _transfer(
            fold=fold,
            source_name="EARLY",
            source_rows=early_labeled,
            target_name="LATE",
            target_rows=late_labeled,
        ),
        "late_to_early": _transfer(
            fold=fold,
            source_name="LATE",
            source_rows=late_labeled,
            target_name="EARLY",
            target_rows=early_labeled,
        ),
    }


def _summary(
    r8: dict[str, object],
    r6: dict[str, object],
) -> dict[str, object]:
    transfers = [
        cast(dict[str, object], r8["early_to_late"]),
        cast(dict[str, object], r8["late_to_early"]),
        cast(dict[str, object], r6["early_to_late"]),
        cast(dict[str, object], r6["late_to_early"]),
    ]
    evals = [
        cast(dict[str, object], transfer["target_evaluation"])
        for transfer in transfers
    ]
    return {
        "transfer_count": len(evals),
        "zero_winner_transfers": sum(
            int(evaluation["flagged_winners"]) == 0
            for evaluation in evals
        ),
        "all_transfers_zero_winner": all(
            int(evaluation["flagged_winners"]) == 0
            for evaluation in evals
        ),
        "total_target_flagged_losses": sum(
            int(evaluation["flagged_losses"])
            for evaluation in evals
        ),
        "total_target_flagged_winners": sum(
            int(evaluation["flagged_winners"])
            for evaluation in evals
        ),
        "total_target_winner_r_exposure": format(
            sum(
                (_d(evaluation["flagged_winner_r_exposure"]) for evaluation in evals),
                ZERO,
            ),
            "f",
        ),
        "runtime_policy_claim": False,
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
    rows8 = v34._annotated_fold(p8, sp_evidence=r8_sp, us_evidence=r8_us)
    rows6 = v34._annotated_fold(p6, sp_evidence=r6_sp, us_evidence=r6_us)

    r8 = _fold_transfers(rows8, fold="R8")
    r6 = _fold_transfers(rows6, fold="R6")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "TEMPORAL_MORPHOLOGY_TRANSFER_NO_ACTUATION",
        "source_hypothesis": "COMPOSITE_PRECISION_ORIGIN",
        "projection_count": len(v38.PROJECTIONS),
        "discovery_contract": {
            "zero_winners_required_in_source_half": True,
            "minimum_losses_in_source_half": 3,
            "minimum_local_top3_dd_losses_in_source_half": 1,
            "target_half_used_for_selection": False,
            "numeric_feature_threshold_grid_search": False,
        },
        "challenge_set": {"r8": 228, "r6": 278},
        "r8": r8,
        "r6": r6,
        "summary": _summary(r8, r6),
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
                "r8": payload["r8"],
                "r6": payload["r6"],
                "summary": payload["summary"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
