"""VT31 Shared natural-DD reciprocal stable sequence intersection V36.

Phase-1 calibration diagnostic only.

V35 discovered winner-safe sequence rules independently in R8 and R6.
V36 keeps only the exact semantic rules that independently satisfy the
discovery contract in BOTH consumed folds, then measures their union.

This is intentionally stricter than V34:
- every retained rule has zero winners in R8 discovery;
- every retained rule has zero winners in R6 discovery;
- every retained rule has >=3 losses and >=2 top-3 DD losses in each fold.

No actuation, no sizing, no abstention, no stop/target mutation, no trailing,
no target extension. This is not certification and does not open R5/fresh holdout.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

import vt31_core_stack_v4_natural_dd_reciprocal_sequence_transfer_v35 as v35

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_reciprocal_stable_intersection.v36"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_RECIPROCAL_STABLE_INTERSECTION_V36"

v34 = v35.v34
v33 = v35.v33
v26 = v35.v26
v18 = v35.v18


def _key(rule: v35.DiscoveredRule) -> tuple[str, str]:
    return (rule.dimension, rule.value)


def _intersection(
    r8_rules: tuple[v35.DiscoveredRule, ...],
    r6_rules: tuple[v35.DiscoveredRule, ...],
) -> tuple[v35.DiscoveredRule, ...]:
    r6_map = {_key(rule): rule for rule in r6_rules}
    stable = [rule for rule in r8_rules if _key(rule) in r6_map]
    stable.sort(
        key=lambda rule: (
            rule.discovery_top3_dd_losses
            + r6_map[_key(rule)].discovery_top3_dd_losses,
            rule.discovery_losses + r6_map[_key(rule)].discovery_losses,
            rule.discovery_loss_r + r6_map[_key(rule)].discovery_loss_r,
        ),
        reverse=True,
    )
    return tuple(stable)


def _combined_rule_payload(
    r8_rules: tuple[v35.DiscoveredRule, ...],
    r6_rules: tuple[v35.DiscoveredRule, ...],
    stable: tuple[v35.DiscoveredRule, ...],
) -> list[dict[str, object]]:
    r8_map = {_key(rule): rule for rule in r8_rules}
    r6_map = {_key(rule): rule for rule in r6_rules}
    output: list[dict[str, object]] = []
    for rule in stable:
        a = r8_map[_key(rule)]
        b = r6_map[_key(rule)]
        output.append(
            {
                "dimension": rule.dimension,
                "value": rule.value,
                "r8": a.payload(),
                "r6": b.payload(),
                "combined_losses": a.discovery_losses + b.discovery_losses,
                "combined_top3_dd_losses": (
                    a.discovery_top3_dd_losses
                    + b.discovery_top3_dd_losses
                ),
                "combined_unobservable_losses": (
                    a.discovery_unobservable_losses
                    + b.discovery_unobservable_losses
                ),
                "combined_loss_r": format(
                    a.discovery_loss_r + b.discovery_loss_r,
                    "f",
                ),
            }
        )
    return output


def _quality(
    r8: dict[str, object],
    r6: dict[str, object],
) -> dict[str, object]:
    zero_winner_both = (
        int(r8["flagged_winners"]) == 0
        and int(r6["flagged_winners"]) == 0
    )
    top3_mean = (
        Decimal(str(r8["top3_dd_loss_recall"]))
        + Decimal(str(r6["top3_dd_loss_recall"]))
    ) / Decimal("2")
    unobservable_mean = (
        Decimal(str(r8["unobservable_loss_recall"]))
        + Decimal(str(r6["unobservable_loss_recall"]))
    ) / Decimal("2")
    return {
        "zero_flagged_winners_both_folds": zero_winner_both,
        "winner_r_exposure_both_zero": (
            Decimal(str(r8["flagged_winner_r_exposure"])) == 0
            and Decimal(str(r6["flagged_winner_r_exposure"])) == 0
        ),
        "mean_top3_dd_loss_recall": format(top3_mean, "f"),
        "mean_unobservable_loss_recall": format(unobservable_mean, "f"),
        "natural_dd_intelligence_candidate": (
            zero_winner_both
            and len(r8.get("rule_match_counts", {})) > 0
            and len(r6.get("rule_match_counts", {})) > 0
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

    discovered8 = v35._discover(rows8)
    discovered6 = v35._discover(rows6)
    stable = _intersection(discovered8, discovered6)

    eval8 = v35._evaluate_transfer(rows8, rules=stable)
    eval6 = v35._evaluate_transfer(rows6, rules=stable)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "RECIPROCAL_STABLE_SEQUENCE_INTERSECTION_NO_ACTUATION",
        "source_hypothesis": "COMPOSITE_PRECISION_ORIGIN",
        "discovery_contract": {
            "zero_winners_required_per_fold": True,
            "minimum_losses_per_fold": 3,
            "minimum_top3_dd_losses_per_fold": 2,
            "exact_rule_intersection_required": True,
            "numeric_threshold_grid_search": False,
        },
        "challenge_set": {"r8": 228, "r6": 278},
        "r8_discovered_rule_count": len(discovered8),
        "r6_discovered_rule_count": len(discovered6),
        "stable_rule_count": len(stable),
        "stable_rules": _combined_rule_payload(
            discovered8,
            discovered6,
            stable,
        ),
        "r8_evaluation": eval8,
        "r6_evaluation": eval6,
        "quality": _quality(eval8, eval6),
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
                "stable_rule_count": payload["stable_rule_count"],
                "stable_rules": payload["stable_rules"],
                "r8_evaluation": payload["r8_evaluation"],
                "r6_evaluation": payload["r6_evaluation"],
                "quality": payload["quality"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
