"""VT31 Shared natural-DD reciprocal sequence transfer V35.

Phase-1 consumed-fold transfer diagnostic.

Discovery is isolated by fold:
- discover exact pre-entry sequence values on R8, test unchanged on R6;
- discover exact pre-entry sequence values on R6, test unchanged on R8.

A sequence qualifies on the discovery fold only when:
- it exists inside V31 COMPOSITE_PRECISION_ORIGIN;
- it has zero winners;
- at least 3 losses;
- at least 2 losses belonging to the discovery fold's top-3 DD excursions.

No sequence is selected using the target fold. This is still consumed research,
not certification and not a fresh holdout.

No sizing, capital weighting, abstention, stop/target mutation, trailing, or
target extension. Outcomes are offline discovery/evaluation labels only.
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

import vt31_core_stack_v4_natural_dd_winner_safe_sequence_v34 as v34

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_reciprocal_sequence_transfer.v35"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_RECIPROCAL_SEQUENCE_TRANSFER_V35"
ZERO = Decimal("0")

v33 = v34.v33
v31 = v34.v31
v30 = v34.v30
v26 = v34.v26
v18 = v34.v18

DIMENSIONS = (
    "environment_state_sequence",
    "trajectory_state_sequence",
    "environment_terminal_3",
    "trajectory_terminal_3",
)


@dataclass(frozen=True, slots=True)
class DiscoveredRule:
    dimension: str
    value: str
    discovery_losses: int
    discovery_top3_dd_losses: int
    discovery_unobservable_losses: int
    discovery_loss_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "value": self.value,
            "discovery_losses": self.discovery_losses,
            "discovery_top3_dd_losses": self.discovery_top3_dd_losses,
            "discovery_unobservable_losses": self.discovery_unobservable_losses,
            "discovery_loss_r": format(self.discovery_loss_r, "f"),
        }


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _discover(
    rows: list[dict[str, object]],
) -> tuple[DiscoveredRule, ...]:
    output: list[DiscoveredRule] = []
    origin_rows = [row for row in rows if bool(row["source_origin_match"])]

    for dimension in DIMENSIONS:
        groups: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in origin_rows:
            sequence = cast(dict[str, object] | None, row["sequence"])
            if sequence is None:
                continue
            groups[str(sequence[dimension])].append(row)

        for value, members in groups.items():
            winners = [row for row in members if row["outcome"] == "WIN"]
            losses = [row for row in members if row["outcome"] == "LOSS"]
            top3 = [
                row
                for row in losses
                if bool(row["in_top3_dd_excursions"])
            ]
            if winners or len(losses) < 3 or len(top3) < 2:
                continue
            unobservable = [
                row for row in losses if bool(row["unobservable_loss"])
            ]
            loss_r = -sum((_d(row["baseline_r"]) for row in losses), ZERO)
            output.append(
                DiscoveredRule(
                    dimension=dimension,
                    value=value,
                    discovery_losses=len(losses),
                    discovery_top3_dd_losses=len(top3),
                    discovery_unobservable_losses=len(unobservable),
                    discovery_loss_r=loss_r,
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


def _evaluate_transfer(
    rows: list[dict[str, object]],
    *,
    rules: tuple[DiscoveredRule, ...],
) -> dict[str, object]:
    flagged: list[dict[str, object]] = []
    for row in rows:
        if not bool(row["source_origin_match"]):
            continue
        sequence = cast(dict[str, object] | None, row["sequence"])
        if sequence is None:
            continue
        matched = tuple(
            f"{rule.dimension}={rule.value}"
            for rule in rules
            if str(sequence.get(rule.dimension)) == rule.value
        )
        if matched:
            flagged.append({**row, "matched_rules": matched})

    losses = [row for row in rows if row["outcome"] == "LOSS"]
    winners = [row for row in rows if row["outcome"] == "WIN"]
    flagged_losses = [row for row in flagged if row["outcome"] == "LOSS"]
    flagged_winners = [row for row in flagged if row["outcome"] == "WIN"]
    top3 = [row for row in losses if bool(row["in_top3_dd_excursions"])]
    flagged_top3 = [
        row for row in flagged_losses if bool(row["in_top3_dd_excursions"])
    ]
    max_dd = [row for row in losses if bool(row["in_max_dd_excursion"])]
    flagged_max_dd = [
        row for row in flagged_losses if bool(row["in_max_dd_excursion"])
    ]
    unobservable = [row for row in losses if bool(row["unobservable_loss"])]
    flagged_unobservable = [
        row for row in flagged_losses if bool(row["unobservable_loss"])
    ]

    total_winner_r = sum((_d(row["baseline_r"]) for row in winners), ZERO)
    flagged_winner_r = sum((_d(row["baseline_r"]) for row in flagged_winners), ZERO)
    flagged_loss_r = -sum((_d(row["baseline_r"]) for row in flagged_losses), ZERO)
    flagged_top3_loss_r = -sum(
        (_d(row["baseline_r"]) for row in flagged_top3),
        ZERO,
    )

    rule_counts: dict[str, int] = {}
    for row in flagged:
        for name in cast(tuple[str, ...], row["matched_rules"]):
            rule_counts[name] = rule_counts.get(name, 0) + 1

    return {
        "rules_received": len(rules),
        "sample": len(rows),
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
        "flagged_winner_r_exposure": format(flagged_winner_r, "f"),
        "winner_r_false_positive_exposure": (
            "0"
            if total_winner_r == ZERO
            else format(flagged_winner_r / total_winner_r, "f")
        ),
        "flagged_loss_r_identified": format(flagged_loss_r, "f"),
        "flagged_top3_dd_loss_r_identified": format(
            flagged_top3_loss_r,
            "f",
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
        "runtime_policy_claim": False,
    }


def _transfer(
    *,
    discovery_name: str,
    discovery_rows: list[dict[str, object]],
    target_name: str,
    target_rows: list[dict[str, object]],
) -> dict[str, object]:
    rules = _discover(discovery_rows)
    target = _evaluate_transfer(target_rows, rules=rules)
    return {
        "discovery_fold": discovery_name,
        "target_fold": target_name,
        "discovered_rules": [rule.payload() for rule in rules],
        "target_evaluation": target,
        "target_fold_not_used_for_rule_selection": True,
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
    rows8 = v34._annotated_fold(
        p8,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    rows6 = v34._annotated_fold(
        p6,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )

    r8_to_r6 = _transfer(
        discovery_name="R8",
        discovery_rows=rows8,
        target_name="R6",
        target_rows=rows6,
    )
    r6_to_r8 = _transfer(
        discovery_name="R6",
        discovery_rows=rows6,
        target_name="R8",
        target_rows=rows8,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "RECIPROCAL_CONSUMED_FOLD_TRANSFER_NO_ACTUATION",
        "source_hypothesis": "COMPOSITE_PRECISION_ORIGIN",
        "discovery_contract": {
            "dimensions": DIMENSIONS,
            "zero_winners_required": True,
            "minimum_losses": 3,
            "minimum_top3_dd_losses": 2,
            "target_fold_used_for_selection": False,
            "numeric_threshold_grid_search": False,
        },
        "challenge_set": {"r8": 228, "r6": 278},
        "r8_to_r6": r8_to_r6,
        "r6_to_r8": r6_to_r8,
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
            "outcomes_used_offline_for_discovery_and_evaluation": True,
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
                "r8_to_r6": payload["r8_to_r6"],
                "r6_to_r8": payload["r6_to_r8"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
