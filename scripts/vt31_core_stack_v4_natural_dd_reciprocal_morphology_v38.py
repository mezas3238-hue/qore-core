"""VT31 Shared natural-DD reciprocal morphology intersection V38.

Phase-1 calibration diagnostic only.

V36 established exact winner-safe sequences. V37 showed that broad semantic
topology families regain coverage but also reintroduce valuable winners.

V38 therefore generalizes more conservatively:
- use fixed categorical morphology projections derived from the causal 8-M1 path;
- discover winner-safe morphology signatures independently in R8 and R6;
- retain only exact morphology signatures that independently satisfy the
  discovery contract in BOTH consumed folds;
- measure total and incremental DD-loss coverage beyond V36.

No numeric threshold grid. No actuation. No sizing. No abstention. No stop or
target mutation. No trailing. No target extension. R5/fresh holdout remain closed.
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

import vt31_core_stack_v4_natural_dd_stable_topology_family_v37 as v37

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_reciprocal_morphology_intersection.v38"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_RECIPROCAL_MORPHOLOGY_V38"
ZERO = Decimal("0")

v36 = v37.v36
v35 = v36.v35
v34 = v35.v34
v33 = v35.v33
v26 = v35.v26
v18 = v35.v18

PROJECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "TURN_PAIR",
        ("macro_turn", "micro_turn"),
    ),
    (
        "PRESSURE_CONFIRMATION_PATH",
        (
            "trajectory_pressure_bps_path_label",
            "opposite_pressure_bps_path_label",
            "cross_market_confirmation_bps_path_label",
        ),
    ),
    (
        "MOMENTUM_CONFIRMATION_PATH",
        (
            "momentum_bps_path_label",
            "displacement_bps_path_label",
            "cross_market_confirmation_bps_path_label",
        ),
    ),
    (
        "SUPPORT_ADVERSITY_PATH",
        (
            "trajectory_support_bps_path_label",
            "trajectory_adversity_bps_path_label",
            "environment_support_bps_path_label",
            "environment_adverse_bps_path_label",
        ),
    ),
    (
        "DETERIORATION_DELTA",
        (
            "macro_turn",
            "trajectory_support_bps_delta_label",
            "trajectory_adversity_bps_delta_label",
            "trajectory_pressure_bps_delta_label",
        ),
    ),
    (
        "MICRO_CROSS_DELTA",
        (
            "micro_turn",
            "momentum_bps_delta_label",
            "cross_market_confirmation_bps_delta_label",
            "opposite_pressure_bps_delta_label",
        ),
    ),
    (
        "CONTRADICTION_ANOMALY_PATH",
        (
            "contradiction_bps_path_label",
            "anomaly_bps_path_label",
            "correlation_stability_bps_path_label",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class MorphologyRule:
    projection: str
    keys: tuple[str, ...]
    signature: str
    discovery_losses: int
    discovery_top3_dd_losses: int
    discovery_unobservable_losses: int
    discovery_loss_r: Decimal

    def key(self) -> tuple[str, str]:
        return (self.projection, self.signature)

    def payload(self) -> dict[str, object]:
        return {
            "projection": self.projection,
            "keys": self.keys,
            "signature": self.signature,
            "discovery_losses": self.discovery_losses,
            "discovery_top3_dd_losses": self.discovery_top3_dd_losses,
            "discovery_unobservable_losses": self.discovery_unobservable_losses,
            "discovery_loss_r": format(self.discovery_loss_r, "f"),
        }


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _signature(sequence: dict[str, object], keys: tuple[str, ...]) -> str:
    return "|".join(f"{key}={sequence.get(key, 'MISSING')}" for key in keys)


def _discover(
    rows: list[dict[str, object]],
) -> tuple[MorphologyRule, ...]:
    origin = [row for row in rows if bool(row["source_origin_match"])]
    output: list[MorphologyRule] = []

    for projection, keys in PROJECTIONS:
        groups: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in origin:
            sequence = cast(dict[str, object] | None, row["sequence"])
            if sequence is None:
                continue
            groups[_signature(sequence, keys)].append(row)

        for signature, members in groups.items():
            winners = [row for row in members if row["outcome"] == "WIN"]
            losses = [row for row in members if row["outcome"] == "LOSS"]
            top3 = [
                row for row in losses if bool(row["in_top3_dd_excursions"])
            ]
            if winners or len(losses) < 3 or len(top3) < 2:
                continue
            unobservable = [
                row for row in losses if bool(row["unobservable_loss"])
            ]
            loss_r = -sum((_d(row["baseline_r"]) for row in losses), ZERO)
            output.append(
                MorphologyRule(
                    projection=projection,
                    keys=keys,
                    signature=signature,
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


def _intersect(
    r8_rules: tuple[MorphologyRule, ...],
    r6_rules: tuple[MorphologyRule, ...],
) -> tuple[MorphologyRule, ...]:
    r6_keys = {rule.key() for rule in r6_rules}
    return tuple(rule for rule in r8_rules if rule.key() in r6_keys)


def _matches_morphology(
    row: dict[str, object],
    rules: tuple[MorphologyRule, ...],
) -> tuple[bool, tuple[str, ...]]:
    if not bool(row["source_origin_match"]):
        return False, ()
    sequence = cast(dict[str, object] | None, row["sequence"])
    if sequence is None:
        return False, ()

    matched: list[str] = []
    for rule in rules:
        if _signature(sequence, rule.keys) == rule.signature:
            matched.append(f"{rule.projection}:{rule.signature}")
    return bool(matched), tuple(matched)


def _stable_v36_rules(
    rows8: list[dict[str, object]],
    rows6: list[dict[str, object]],
) -> tuple[v35.DiscoveredRule, ...]:
    d8 = v35._discover(rows8)
    d6 = v35._discover(rows6)
    d6_keys = {(rule.dimension, rule.value) for rule in d6}
    return tuple(
        rule
        for rule in d8
        if (rule.dimension, rule.value) in d6_keys
    )


def _matches_exact(
    row: dict[str, object],
    rules: tuple[v35.DiscoveredRule, ...],
) -> bool:
    if not bool(row["source_origin_match"]):
        return False
    sequence = cast(dict[str, object] | None, row["sequence"])
    if sequence is None:
        return False
    return any(str(sequence.get(rule.dimension)) == rule.value for rule in rules)


def _evaluate(
    rows: list[dict[str, object]],
    *,
    morphology_rules: tuple[MorphologyRule, ...],
    exact_rules: tuple[v35.DiscoveredRule, ...],
) -> dict[str, object]:
    flagged: list[dict[str, object]] = []
    for row in rows:
        matched, names = _matches_morphology(row, morphology_rules)
        if matched:
            flagged.append({**row, "matched_morphologies": names})

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

    exact_signals = {
        str(row["signal_at"])
        for row in rows
        if _matches_exact(row, exact_rules)
    }
    incremental_losses = [
        row
        for row in flagged_losses
        if str(row["signal_at"]) not in exact_signals
    ]
    incremental_top3 = [
        row
        for row in incremental_losses
        if bool(row["in_top3_dd_excursions"])
    ]
    incremental_unobservable = [
        row for row in incremental_losses if bool(row["unobservable_loss"])
    ]

    total_winner_r = sum((_d(row["baseline_r"]) for row in winners), ZERO)
    winner_r = sum((_d(row["baseline_r"]) for row in flagged_winners), ZERO)
    loss_r = -sum((_d(row["baseline_r"]) for row in flagged_losses), ZERO)
    top3_loss_r = -sum((_d(row["baseline_r"]) for row in flagged_top3), ZERO)
    incremental_loss_r = -sum(
        (_d(row["baseline_r"]) for row in incremental_losses),
        ZERO,
    )

    rule_counts: dict[str, int] = {}
    for row in flagged:
        for name in cast(tuple[str, ...], row["matched_morphologies"]):
            rule_counts[name] = rule_counts.get(name, 0) + 1

    return {
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
        "flagged_winner_r_exposure": format(winner_r, "f"),
        "winner_r_false_positive_exposure": (
            "0"
            if total_winner_r == ZERO
            else format(winner_r / total_winner_r, "f")
        ),
        "flagged_loss_r_identified": format(loss_r, "f"),
        "flagged_top3_dd_loss_r_identified": format(top3_loss_r, "f"),
        "incremental_beyond_v36": {
            "losses": len(incremental_losses),
            "top3_dd_losses": len(incremental_top3),
            "unobservable_losses": len(incremental_unobservable),
            "loss_r_identified": format(incremental_loss_r, "f"),
        },
        "morphology_match_counts": dict(sorted(rule_counts.items())),
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


def _combined_rule_payload(
    r8_rules: tuple[MorphologyRule, ...],
    r6_rules: tuple[MorphologyRule, ...],
    stable: tuple[MorphologyRule, ...],
) -> list[dict[str, object]]:
    a = {rule.key(): rule for rule in r8_rules}
    b = {rule.key(): rule for rule in r6_rules}
    output: list[dict[str, object]] = []
    for rule in stable:
        x, y = a[rule.key()], b[rule.key()]
        output.append(
            {
                "projection": rule.projection,
                "keys": rule.keys,
                "signature": rule.signature,
                "r8": x.payload(),
                "r6": y.payload(),
                "combined_losses": x.discovery_losses + y.discovery_losses,
                "combined_top3_dd_losses": (
                    x.discovery_top3_dd_losses
                    + y.discovery_top3_dd_losses
                ),
                "combined_unobservable_losses": (
                    x.discovery_unobservable_losses
                    + y.discovery_unobservable_losses
                ),
                "combined_loss_r": format(
                    x.discovery_loss_r + y.discovery_loss_r,
                    "f",
                ),
            }
        )
    output.sort(
        key=lambda row: (
            int(row["combined_top3_dd_losses"]),
            int(row["combined_losses"]),
            _d(row["combined_loss_r"]),
        ),
        reverse=True,
    )
    return output


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

    discovered8 = _discover(rows8)
    discovered6 = _discover(rows6)
    stable = _intersect(discovered8, discovered6)
    exact = _stable_v36_rules(rows8, rows6)

    eval8 = _evaluate(
        rows8,
        morphology_rules=stable,
        exact_rules=exact,
    )
    eval6 = _evaluate(
        rows6,
        morphology_rules=stable,
        exact_rules=exact,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "RECIPROCAL_STABLE_MORPHOLOGY_NO_ACTUATION",
        "source_hypothesis": "COMPOSITE_PRECISION_ORIGIN",
        "challenge_set": {"r8": 228, "r6": 278},
        "projection_count": len(PROJECTIONS),
        "r8_discovered_morphology_count": len(discovered8),
        "r6_discovered_morphology_count": len(discovered6),
        "stable_morphology_count": len(stable),
        "stable_morphologies": _combined_rule_payload(
            discovered8,
            discovered6,
            stable,
        ),
        "v36_stable_exact_rule_count": len(exact),
        "r8_evaluation": eval8,
        "r6_evaluation": eval6,
        "quality": {
            "zero_flagged_winners_both_folds": (
                int(eval8["flagged_winners"]) == 0
                and int(eval6["flagged_winners"]) == 0
            ),
            "winner_r_exposure_both_zero": (
                _d(eval8["flagged_winner_r_exposure"]) == ZERO
                and _d(eval6["flagged_winner_r_exposure"]) == ZERO
            ),
            "adds_new_losses_beyond_v36": (
                int(cast(dict[str, object], eval8["incremental_beyond_v36"])["losses"]) > 0
                or int(cast(dict[str, object], eval6["incremental_beyond_v36"])["losses"]) > 0
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
            "outcomes_used_offline_for_calibration_only": True,
            "numeric_feature_threshold_grid_search": False,
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
                "stable_morphology_count": payload["stable_morphology_count"],
                "stable_morphologies": payload["stable_morphologies"],
                "r8": payload["r8_evaluation"],
                "r6": payload["r6_evaluation"],
                "quality": payload["quality"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
