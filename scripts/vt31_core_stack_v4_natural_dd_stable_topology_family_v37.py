"""VT31 Shared natural-DD stable topology family generalization V37.

Phase-1 diagnostic only.

V36 established seven exact pre-entry sequences with zero winners in both
consumed folds. V37 generalizes their SEMANTIC TOPOLOGY without numeric
threshold tuning, testing whether the underlying transition families can
capture more drawdown-origin losses while preserving winners.

No actuation, no sizing, no abstention, no stop/target mutation, no trailing,
no target extension. Outcomes are offline evaluation labels only.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable, cast

import vt31_core_stack_v4_natural_dd_reciprocal_stable_intersection_v36 as v36

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_stable_topology_family.v37"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_STABLE_TOPOLOGY_FAMILY_V37"
ZERO = Decimal("0")

v35 = v36.v35
v34 = v35.v34
v33 = v35.v33
v26 = v35.v26
v18 = v35.v18


@dataclass(frozen=True, slots=True)
class TopologyFamily:
    name: str
    matcher: Callable[[dict[str, object]], bool]
    semantic_basis: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "semantic_basis": self.semantic_basis,
            "numeric_threshold_grid_search": False,
            "actuation": False,
        }


def _tokens(sequence: dict[str, object], key: str) -> tuple[str, ...]:
    value = str(sequence.get(key, ""))
    return tuple(token for token in value.split(">") if token)


def _ordered_contains(tokens: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
    if not pattern:
        return True
    cursor = 0
    for token in tokens:
        if token == pattern[cursor]:
            cursor += 1
            if cursor == len(pattern):
                return True
    return False


def _false_recovery(sequence: dict[str, object]) -> bool:
    trajectory = _tokens(sequence, "trajectory_state_sequence")
    terminal = _tokens(sequence, "trajectory_terminal_3")
    return (
        _ordered_contains(trajectory, ("DIVERGING", "STABILIZING", "RECOVERING"))
        or terminal == ("STABILIZING", "RECOVERING", "RECOVERING")
    )


def _fragile_support_oscillation(sequence: dict[str, object]) -> bool:
    terminal = _tokens(sequence, "environment_terminal_3")
    return (
        len(terminal) == 3
        and "FRAGILE" in terminal
        and "SUPPORTIVE" in terminal
    )


def _restored_to_fragile(sequence: dict[str, object]) -> bool:
    environment = _tokens(sequence, "environment_state_sequence")
    return _ordered_contains(environment, ("RESTORED", "FRAGILE"))


def _fragile_degrade_false_support(sequence: dict[str, object]) -> bool:
    environment = _tokens(sequence, "environment_state_sequence")
    return _ordered_contains(
        environment,
        ("FRAGILE", "DEGRADING", "SUPPORTIVE"),
    )


def _stable_union(sequence: dict[str, object]) -> bool:
    return (
        _false_recovery(sequence)
        or _fragile_support_oscillation(sequence)
        or _restored_to_fragile(sequence)
        or _fragile_degrade_false_support(sequence)
    )


FAMILIES = (
    TopologyFamily(
        name="FALSE_RECOVERY_TOPOLOGY",
        matcher=_false_recovery,
        semantic_basis=(
            "DIVERGING -> STABILIZING -> RECOVERING",
            "STABILIZING -> RECOVERING -> RECOVERING",
        ),
    ),
    TopologyFamily(
        name="FRAGILE_SUPPORT_OSCILLATION",
        matcher=_fragile_support_oscillation,
        semantic_basis=(
            "terminal environment contains FRAGILE and SUPPORTIVE",
        ),
    ),
    TopologyFamily(
        name="RESTORED_TO_FRAGILE",
        matcher=_restored_to_fragile,
        semantic_basis=("RESTORED precedes FRAGILE",),
    ),
    TopologyFamily(
        name="FRAGILE_DEGRADE_FALSE_SUPPORT",
        matcher=_fragile_degrade_false_support,
        semantic_basis=("FRAGILE -> DEGRADING -> SUPPORTIVE",),
    ),
    TopologyFamily(
        name="STABLE_TOPOLOGY_UNION",
        matcher=_stable_union,
        semantic_basis=(
            "union of the four fixed topology families",
        ),
    ),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _evaluate(
    rows: list[dict[str, object]],
    *,
    family: TopologyFamily,
) -> dict[str, object]:
    flagged: list[dict[str, object]] = []
    for row in rows:
        if not bool(row["source_origin_match"]):
            continue
        sequence = cast(dict[str, object] | None, row["sequence"])
        if sequence is None or not family.matcher(sequence):
            continue
        flagged.append(row)

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
    winner_r = sum((_d(row["baseline_r"]) for row in flagged_winners), ZERO)
    loss_r = -sum((_d(row["baseline_r"]) for row in flagged_losses), ZERO)
    top3_loss_r = -sum((_d(row["baseline_r"]) for row in flagged_top3), ZERO)

    return {
        "family": family.payload(),
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
        "flagged_winner_examples": sorted(
            (
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": row["baseline_r"],
                    "sequence": row["sequence"],
                }
                for row in flagged_winners
            ),
            key=lambda row: _d(row["baseline_r"]),
            reverse=True,
        )[:10],
        "actuation_used": False,
        "runtime_policy_claim": False,
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
    rows8 = v34._annotated_fold(p8, sp_evidence=r8_sp, us_evidence=r8_us)
    rows6 = v34._annotated_fold(p6, sp_evidence=r6_sp, us_evidence=r6_us)

    results: list[dict[str, object]] = []
    for family in FAMILIES:
        e8 = _evaluate(rows8, family=family)
        e6 = _evaluate(rows6, family=family)
        results.append(
            {
                "family": family.payload(),
                "r8": e8,
                "r6": e6,
                "diagnostic_score": format(_score(e8, e6), "f"),
            }
        )
    results.sort(key=lambda row: _d(row["diagnostic_score"]), reverse=True)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "STABLE_TOPOLOGY_FAMILY_GENERALIZATION_NO_ACTUATION",
        "source_hypothesis": "COMPOSITE_PRECISION_ORIGIN",
        "challenge_set": {"r8": 228, "r6": 278},
        "family_results": results,
        "best_diagnostic_family": None if not results else results[0]["family"],
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
            "outcomes_used_offline_for_evaluation_only": True,
            "topology_generalized_without_numeric_grid": True,
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
                "best_diagnostic_family": payload["best_diagnostic_family"],
                "family_results": payload["family_results"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
