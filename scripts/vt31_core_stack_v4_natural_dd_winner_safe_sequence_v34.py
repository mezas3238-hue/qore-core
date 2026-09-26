"""VT31 Shared natural-DD winner-safe sequence discrimination V34.

Phase-1 calibration diagnostic only.

V33 discovered cross-fold pre-entry sequences that occurred inside the V31
COMPOSITE_PRECISION_ORIGIN population with losses in both consumed folds and
zero winners. V34 freezes those already-observed semantic sequences into fixed
candidate sets and measures their UNION coverage on R8/R6.

Important:
- the V31 origin condition remains mandatory;
- outcomes are used only offline for evaluation;
- no trade is changed;
- no sizing, capital weighting, entry abstention, stop/target mutation,
  trailing, or target extension;
- this is NOT a runtime policy and NOT certification.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_natural_dd_preentry_sequence_topology_v33 as v33

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_winner_safe_sequence.v34"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_WINNER_SAFE_SEQUENCE_V34"
ZERO = Decimal("0")

v31 = v33.v31
v30 = v33.v30
v26 = v33.v26
v18 = v33.v18


@dataclass(frozen=True, slots=True)
class SequenceRule:
    dimension: str
    value: str

    def payload(self) -> dict[str, str]:
        return {"dimension": self.dimension, "value": self.value}


CORE_RULES = (
    SequenceRule("environment_terminal_3", "SUPPORTIVE>FRAGILE>FRAGILE"),
    SequenceRule(
        "trajectory_state_sequence",
        "INSUFFICIENT>DIVERGING>STABILIZING>RECOVERING",
    ),
    SequenceRule("environment_state_sequence", "INSUFFICIENT>RESTORED>FRAGILE"),
    SequenceRule("environment_terminal_3", "FRAGILE>SUPPORTIVE>SUPPORTIVE"),
    SequenceRule("environment_terminal_3", "SUPPORTIVE>SUPPORTIVE>FRAGILE"),
)

EXTENDED_RULES = CORE_RULES + (
    SequenceRule("environment_terminal_3", "SUPPORTIVE>SUPPORTIVE>SUPPORTIVE"),
    SequenceRule(
        "environment_state_sequence",
        "INSUFFICIENT>FRAGILE>DEGRADING>SUPPORTIVE",
    ),
    SequenceRule("environment_state_sequence", "INSUFFICIENT>FRAGILE>RESTORED"),
    SequenceRule(
        "trajectory_terminal_3",
        "STABILIZING>RECOVERING>RECOVERING",
    ),
    SequenceRule("trajectory_state_sequence", "INSUFFICIENT>DIVERGING>RECOVERING"),
    SequenceRule(
        "trajectory_terminal_3",
        "DIVERGING>DIVERGING>STABILIZING",
    ),
    SequenceRule(
        "trajectory_terminal_3",
        "HEALTHY>DETERIORATING>DETERIORATING",
    ),
    SequenceRule(
        "trajectory_terminal_3",
        "WEAKENING>DETERIORATING>DETERIORATING",
    ),
)

BROAD_RULES = EXTENDED_RULES + (
    SequenceRule(
        "trajectory_state_sequence",
        "INSUFFICIENT>RECOVERING>DIVERGING>DETERIORATING",
    ),
    SequenceRule(
        "environment_state_sequence",
        "INSUFFICIENT>FRAGILE>RESTORED>SUPPORTIVE",
    ),
    SequenceRule("environment_terminal_3", "FRAGILE>FRAGILE>RESTORED"),
    SequenceRule("trajectory_terminal_3", "DIVERGING>DIVERGING>DIVERGING"),
    SequenceRule(
        "environment_state_sequence",
        "INSUFFICIENT>FRAGILE>SUPPORTIVE>DEGRADING",
    ),
    SequenceRule(
        "environment_state_sequence",
        "INSUFFICIENT>SUPPORTIVE>FRAGILE>SUPPORTIVE",
    ),
    SequenceRule("environment_terminal_3", "FRAGILE>SUPPORTIVE>DEGRADING"),
)

CANDIDATES = (
    ("WINNER_SAFE_CORE", CORE_RULES),
    ("WINNER_SAFE_EXTENDED", EXTENDED_RULES),
    ("WINNER_SAFE_BROAD", BROAD_RULES),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _annotated_fold(
    prepared: list[dict[str, object]],
    *,
    sp_evidence: Path,
    us_evidence: Path,
) -> list[dict[str, object]]:
    excursions = v30._drawdown_excursions(prepared)
    base_rows = v30._signature_rows(prepared, excursions)
    by_signal = {str(row["signal_at"]): row for row in base_rows}
    source_hypothesis = next(
        hypothesis
        for hypothesis in v31.HYPOTHESES
        if hypothesis.name == "COMPOSITE_PRECISION_ORIGIN"
    )

    sp_by_day = v18.v13._group_market(sp_evidence)
    us_by_day = v18.v13._group_market(us_evidence)
    output: list[dict[str, object]] = []

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        base = by_signal[str(row["signal_at"])]
        sequence: dict[str, object] | None = None
        if source_hypothesis.matches(base):
            sequence = v33._sequence(
                item=item,
                sp_by_day=sp_by_day,
                us_by_day=us_by_day,
            )
        output.append(
            {
                **base,
                "source_origin_match": source_hypothesis.matches(base),
                "sequence": sequence,
            }
        )
    return output


def _matches_rules(
    row: dict[str, object],
    rules: tuple[SequenceRule, ...],
) -> tuple[bool, tuple[str, ...]]:
    if not bool(row["source_origin_match"]):
        return False, ()
    sequence = cast(dict[str, object] | None, row["sequence"])
    if sequence is None:
        return False, ()

    matched: list[str] = []
    for rule in rules:
        if str(sequence.get(rule.dimension)) == rule.value:
            matched.append(f"{rule.dimension}={rule.value}")
    return bool(matched), tuple(matched)


def _evaluate(
    rows: list[dict[str, object]],
    *,
    name: str,
    rules: tuple[SequenceRule, ...],
) -> dict[str, object]:
    flagged: list[dict[str, object]] = []
    for row in rows:
        match, matched_rules = _matches_rules(row, rules)
        if not match:
            continue
        flagged.append({**row, "matched_rules": matched_rules})

    losses = [row for row in rows if row["outcome"] == "LOSS"]
    winners = [row for row in rows if row["outcome"] == "WIN"]
    flagged_losses = [row for row in flagged if row["outcome"] == "LOSS"]
    flagged_winners = [row for row in flagged if row["outcome"] == "WIN"]

    top3_losses = [
        row for row in losses if bool(row["in_top3_dd_excursions"])
    ]
    flagged_top3_losses = [
        row for row in flagged_losses if bool(row["in_top3_dd_excursions"])
    ]
    max_dd_losses = [
        row for row in losses if bool(row["in_max_dd_excursion"])
    ]
    flagged_max_dd_losses = [
        row for row in flagged_losses if bool(row["in_max_dd_excursion"])
    ]
    unobservable_losses = [
        row for row in losses if bool(row["unobservable_loss"])
    ]
    flagged_unobservable_losses = [
        row for row in flagged_losses if bool(row["unobservable_loss"])
    ]

    total_winner_r = sum((_d(row["baseline_r"]) for row in winners), ZERO)
    flagged_winner_r = sum((_d(row["baseline_r"]) for row in flagged_winners), ZERO)
    flagged_loss_r = -sum((_d(row["baseline_r"]) for row in flagged_losses), ZERO)
    flagged_top3_loss_r = -sum(
        (_d(row["baseline_r"]) for row in flagged_top3_losses),
        ZERO,
    )

    rule_counts: dict[str, int] = {}
    for row in flagged:
        for matched in cast(tuple[str, ...], row["matched_rules"]):
            rule_counts[matched] = rule_counts.get(matched, 0) + 1

    lead_values = [
        int(row["lead_seconds_before_fill"])
        for row in flagged_losses
        if row["lead_seconds_before_fill"] is not None
    ]

    return {
        "candidate": name,
        "rules": [rule.payload() for rule in rules],
        "sample": len(rows),
        "flagged": len(flagged),
        "flagged_fraction": _ratio(len(flagged), len(rows)),
        "losses": len(losses),
        "flagged_losses": len(flagged_losses),
        "loss_recall": _ratio(len(flagged_losses), len(losses)),
        "max_dd_losses": len(max_dd_losses),
        "flagged_max_dd_losses": len(flagged_max_dd_losses),
        "max_dd_loss_recall": _ratio(
            len(flagged_max_dd_losses),
            len(max_dd_losses),
        ),
        "top3_dd_losses": len(top3_losses),
        "flagged_top3_dd_losses": len(flagged_top3_losses),
        "top3_dd_loss_recall": _ratio(
            len(flagged_top3_losses),
            len(top3_losses),
        ),
        "unobservable_losses": len(unobservable_losses),
        "flagged_unobservable_losses": len(flagged_unobservable_losses),
        "unobservable_loss_recall": _ratio(
            len(flagged_unobservable_losses),
            len(unobservable_losses),
        ),
        "winners": len(winners),
        "flagged_winners": len(flagged_winners),
        "winner_false_positive_rate": _ratio(
            len(flagged_winners),
            len(winners),
        ),
        "total_winner_r": format(total_winner_r, "f"),
        "flagged_winner_r_exposure": format(flagged_winner_r, "f"),
        "winner_r_false_positive_exposure": (
            "0"
            if total_winner_r == ZERO
            else format(flagged_winner_r / total_winner_r, "f")
        ),
        "flagged_loss_r_identified": format(flagged_loss_r, "f"),
        "flagged_top3_dd_loss_r_identified": format(flagged_top3_loss_r, "f"),
        "minimum_lead_seconds_before_flagged_loss": (
            None if not lead_values else min(lead_values)
        ),
        "median_lead_seconds_before_flagged_loss": (
            None
            if not lead_values
            else sorted(lead_values)[len(lead_values) // 2]
        ),
        "rule_match_counts": dict(sorted(rule_counts.items())),
        "flagged_winner_examples": sorted(
            (
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": row["baseline_r"],
                    "matched_rules": row["matched_rules"],
                }
                for row in flagged_winners
            ),
            key=lambda row: _d(row["baseline_r"]),
            reverse=True,
        )[:20],
        "actuation_used": False,
        "realized_dd_claimed_reduced": False,
    }


def _score(r8: dict[str, object], r6: dict[str, object]) -> Decimal:
    coverage = (
        _d(r8["top3_dd_loss_recall"])
        + _d(r6["top3_dd_loss_recall"])
        + _d(r8["unobservable_loss_recall"])
        + _d(r6["unobservable_loss_recall"])
    ) / Decimal("4")
    winner_exposure = (
        _d(r8["winner_r_false_positive_exposure"])
        + _d(r6["winner_r_false_positive_exposure"])
    ) / Decimal("2")
    return coverage * (Decimal("1") - min(Decimal("1"), winner_exposure))


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
    rows8 = _annotated_fold(p8, sp_evidence=r8_sp, us_evidence=r8_us)
    rows6 = _annotated_fold(p6, sp_evidence=r6_sp, us_evidence=r6_us)

    results: list[dict[str, object]] = []
    for name, rules in CANDIDATES:
        r8_eval = _evaluate(rows8, name=name, rules=rules)
        r6_eval = _evaluate(rows6, name=name, rules=rules)
        results.append(
            {
                "candidate": name,
                "r8": r8_eval,
                "r6": r6_eval,
                "diagnostic_score": format(_score(r8_eval, r6_eval), "f"),
                "zero_winner_cross_fold_expected_from_v33": True,
                "runtime_policy_claim": False,
            }
        )
    results.sort(key=lambda row: _d(row["diagnostic_score"]), reverse=True)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "CALIBRATION_WINNER_SAFE_SEQUENCE_NO_ACTUATION",
        "source_hypothesis": "COMPOSITE_PRECISION_ORIGIN",
        "challenge_set": {"r8": 228, "r6": 278},
        "candidate_results": results,
        "best_diagnostic_candidate": None if not results else results[0]["candidate"],
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
            "outcomes_used_offline_for_calibration_only": True,
            "rules_selected_from_consumed_v33_cross_fold_atlas": True,
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
                "best_diagnostic_candidate": payload["best_diagnostic_candidate"],
                "candidate_results": payload["candidate_results"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
