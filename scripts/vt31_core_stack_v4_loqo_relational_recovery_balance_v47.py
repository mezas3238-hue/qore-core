"""VT31 Shared LOQO relational recovery-balance disambiguation V47.

Phase-1 temporal falsification only.

V46 falsified single extra-feature rescue signatures: no source signature was
winner-only with support in both folds. V47 therefore models RELATIONSHIPS
between causal forces instead of isolated variables.

Fixed semantic comparisons (no fitted numeric thresholds):
- trajectory recovery vs deterioration persistence;
- environment recovery vs adverse persistence;
- trajectory recovery vs deterioration velocity;
- environment recovery vs adverse velocity;
- trend support vs structural fragility;
- cross-market confirmation vs cross-market fragility;
- trajectory support vs trajectory adversity;
- environment support vs environment adversity.

Each comparison is evaluated at END and as DELTA balance. Rescue rules may be
single relational signatures or exact pairs of relational signatures.

For every LOQO target:
1. discover V43 adverse phenotypes from the 7 source quarters;
2. among source adverse rows, discover cross-fold winner-only relational rescue
   signatures with >=1 winner in each source fold and zero source losses;
3. evaluate untouched target quarter.

No sizing, weighting, abstention, stop/target mutation, trailing, extension,
R5, fresh holdout, LIVE or production.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_loqo_adverse_recoverable_disambiguation_v46 as v46

SCHEMA = "qore.core_stack_v4.vt31.loqo_relational_recovery_balance.v47"
IDENTITY = "VT31_NAS100_SHARED_LOQO_RELATIONAL_RECOVERY_BALANCE_V47"
ZERO = Decimal("0")

v43 = v46.v43
v41 = v46.v41
v33 = v46.v33
v26 = v46.v26
v18 = v46.v18

RELATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "TRAJECTORY_PERSISTENCE_BALANCE",
        "trajectory_recovery_persistence_bps",
        "trajectory_deterioration_persistence_bps",
    ),
    (
        "ENVIRONMENT_PERSISTENCE_BALANCE",
        "environment_recovery_persistence_bps",
        "environment_adverse_persistence_bps",
    ),
    (
        "TRAJECTORY_VELOCITY_BALANCE",
        "trajectory_recovery_velocity_bps",
        "trajectory_deterioration_velocity_bps",
    ),
    (
        "ENVIRONMENT_VELOCITY_BALANCE",
        "environment_recovery_velocity_bps",
        "environment_adverse_velocity_bps",
    ),
    (
        "TREND_STRUCTURAL_BALANCE",
        "trend_support_bps",
        "structural_fragility_bps",
    ),
    (
        "CROSS_CONFIRM_FRAGILITY_BALANCE",
        "cross_market_confirmation_bps",
        "cross_market_fragility_bps",
    ),
    (
        "TRAJECTORY_SUPPORT_ADVERSITY_BALANCE",
        "trajectory_support_bps",
        "trajectory_adversity_bps",
    ),
    (
        "ENVIRONMENT_SUPPORT_ADVERSE_BALANCE",
        "environment_support_bps",
        "environment_adverse_bps",
    ),
)

RELATION_VIEWS: tuple[tuple[str, str], ...] = tuple(
    (name, mode)
    for name, _, _ in RELATIONS
    for mode in ("END", "DELTA")
)
PAIR_RELATION_VIEWS: tuple[tuple[tuple[str, str], tuple[str, str]], ...] = tuple(
    itertools.combinations(RELATION_VIEWS, 2)
)
RELATION_MAP = {name: (left, right) for name, left, right in RELATIONS}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _cmp(left: int, right: int) -> str:
    if left > right:
        return "LEFT_GT_RIGHT"
    if right > left:
        return "RIGHT_GT_LEFT"
    return "EQUAL"


def _relation_value(
    row: dict[str, object],
    relation: str,
    mode: str,
) -> str:
    sequence = cast(dict[str, object], row["sequence"])
    path = cast(list[dict[str, object]], sequence["path"])
    left_key, right_key = RELATION_MAP[relation]
    if mode == "END":
        return _cmp(int(path[-1][left_key]), int(path[-1][right_key]))
    if mode == "DELTA":
        left_delta = int(path[-1][left_key]) - int(path[0][left_key])
        right_delta = int(path[-1][right_key]) - int(path[0][right_key])
        return _cmp(left_delta, right_delta)
    raise AssertionError(mode)


def _single_key(
    row: dict[str, object],
    view: tuple[str, str],
) -> tuple[str, str, str]:
    relation, mode = view
    return (relation, mode, _relation_value(row, relation, mode))


def _pair_key(
    row: dict[str, object],
    views: tuple[tuple[str, str], tuple[str, str]],
) -> tuple[str, str]:
    left, right = views
    return (
        f"{left[0]}:{left[1]}={_relation_value(row, left[0], left[1])}",
        f"{right[0]}:{right[1]}={_relation_value(row, right[0], right[1])}",
    )


def _is_adverse(
    row: dict[str, object],
    *,
    adverse_single: set[tuple[str, str]],
    adverse_pair: set[tuple[str, str, str]],
) -> bool:
    return (
        v43._row_matches_single(row, adverse_single)
        or v43._row_matches_pair(row, adverse_pair)
    )


def _eligible_winner_only(
    groups8: dict[object, list[dict[str, object]]],
    groups6: dict[object, list[dict[str, object]]],
) -> set[object]:
    eligible: set[object] = set()
    for key in set(groups8).intersection(groups6):
        valid = True
        for groups in (groups8, groups6):
            members = groups[key]
            wins = sum(row["outcome"] == "WIN" for row in members)
            losses = sum(row["outcome"] == "LOSS" for row in members)
            if wins < 1 or losses != 0:
                valid = False
                break
        if valid:
            eligible.add(key)
    return eligible


def _discover_rescue(
    source8: list[dict[str, object]],
    source6: list[dict[str, object]],
    *,
    adverse_single: set[tuple[str, str]],
    adverse_pair: set[tuple[str, str, str]],
) -> tuple[set[tuple[str, str, str]], set[tuple[str, str]]]:
    single_groups: dict[
        str,
        dict[tuple[str, str, str], list[dict[str, object]]],
    ] = {"R8": defaultdict(list), "R6": defaultdict(list)}
    pair_groups: dict[
        str,
        dict[tuple[str, str], list[dict[str, object]]],
    ] = {"R8": defaultdict(list), "R6": defaultdict(list)}

    for fold, rows in (("R8", source8), ("R6", source6)):
        adverse_rows = [
            row
            for row in rows
            if _is_adverse(
                row,
                adverse_single=adverse_single,
                adverse_pair=adverse_pair,
            )
        ]
        for row in adverse_rows:
            for view in RELATION_VIEWS:
                single_groups[fold][_single_key(row, view)].append(row)
            for views in PAIR_RELATION_VIEWS:
                pair_groups[fold][_pair_key(row, views)].append(row)

    single = cast(
        set[tuple[str, str, str]],
        _eligible_winner_only(single_groups["R8"], single_groups["R6"]),
    )
    pair = cast(
        set[tuple[str, str]],
        _eligible_winner_only(pair_groups["R8"], pair_groups["R6"]),
    )
    return single, pair


def _matches_rescue(
    row: dict[str, object],
    *,
    single_rules: set[tuple[str, str, str]],
    pair_rules: set[tuple[str, str]],
) -> tuple[bool, str | None]:
    for view in RELATION_VIEWS:
        if _single_key(row, view) in single_rules:
            return True, "RELATIONAL_SINGLE"
    for views in PAIR_RELATION_VIEWS:
        if _pair_key(row, views) in pair_rules:
            return True, "RELATIONAL_PAIR"
    return False, None


def _evaluate(
    target: list[dict[str, object]],
    *,
    adverse_single: set[tuple[str, str]],
    adverse_pair: set[tuple[str, str, str]],
    rescue_single: set[tuple[str, str, str]],
    rescue_pair: set[tuple[str, str]],
) -> dict[str, object]:
    adverse = [
        row
        for row in target
        if _is_adverse(
            row,
            adverse_single=adverse_single,
            adverse_pair=adverse_pair,
        )
    ]
    rescued: list[dict[str, object]] = []
    terminal: list[dict[str, object]] = []
    for row in adverse:
        match, kind = _matches_rescue(
            row,
            single_rules=rescue_single,
            pair_rules=rescue_pair,
        )
        if match:
            rescued.append({**row, "rescue_kind": kind})
        else:
            terminal.append(row)

    losses = [row for row in target if row["outcome"] == "LOSS"]
    winners = [row for row in target if row["outcome"] == "WIN"]
    adverse_losses = [row for row in adverse if row["outcome"] == "LOSS"]
    adverse_winners = [row for row in adverse if row["outcome"] == "WIN"]
    rescued_losses = [row for row in rescued if row["outcome"] == "LOSS"]
    rescued_winners = [row for row in rescued if row["outcome"] == "WIN"]
    terminal_losses = [row for row in terminal if row["outcome"] == "LOSS"]
    terminal_winners = [row for row in terminal if row["outcome"] == "WIN"]

    adverse_winner_r = sum((_d(row["baseline_r"]) for row in adverse_winners), ZERO)
    rescue_winner_r = sum((_d(row["baseline_r"]) for row in rescued_winners), ZERO)
    rescue_loss_r = -sum((_d(row["baseline_r"]) for row in rescued_losses), ZERO)
    terminal_winner_r = sum((_d(row["baseline_r"]) for row in terminal_winners), ZERO)
    terminal_loss_r = -sum((_d(row["baseline_r"]) for row in terminal_losses), ZERO)

    return {
        "sample": len(target),
        "losses": len(losses),
        "winners": len(winners),
        "adverse_losses": len(adverse_losses),
        "adverse_winners": len(adverse_winners),
        "adverse_loss_recall": _ratio(len(adverse_losses), len(losses)),
        "adverse_winner_false_positive_rate": _ratio(
            len(adverse_winners),
            len(winners),
        ),
        "adverse_winner_r_exposure": format(adverse_winner_r, "f"),
        "rescued_losses": len(rescued_losses),
        "rescued_winners": len(rescued_winners),
        "rescued_loss_r": format(rescue_loss_r, "f"),
        "rescued_winner_r": format(rescue_winner_r, "f"),
        "terminal_losses": len(terminal_losses),
        "terminal_winners": len(terminal_winners),
        "terminal_loss_recall": _ratio(len(terminal_losses), len(losses)),
        "terminal_winner_false_positive_rate": _ratio(
            len(terminal_winners),
            len(winners),
        ),
        "terminal_loss_r_identified": format(terminal_loss_r, "f"),
        "terminal_winner_r_exposure": format(terminal_winner_r, "f"),
        "winner_count_reduction_vs_adverse": len(adverse_winners) - len(terminal_winners),
        "winner_r_reduction_vs_adverse": format(adverse_winner_r - terminal_winner_r, "f"),
        "loss_count_sacrificed_to_rescue": len(rescued_losses),
        "loss_r_sacrificed_to_rescue": format(rescue_loss_r, "f"),
        "rescue_kind_counts": {
            "RELATIONAL_SINGLE": sum(row["rescue_kind"] == "RELATIONAL_SINGLE" for row in rescued),
            "RELATIONAL_PAIR": sum(row["rescue_kind"] == "RELATIONAL_PAIR" for row in rescued),
        },
        "largest_rescued_winners": sorted(
            (
                {"signal_at": row["signal_at"], "baseline_r": row["baseline_r"], "rescue_kind": row["rescue_kind"]}
                for row in rescued_winners
            ),
            key=lambda row: _d(row["baseline_r"]),
            reverse=True,
        )[:15],
        "largest_terminal_false_winners": sorted(
            (
                {"signal_at": row["signal_at"], "baseline_r": row["baseline_r"]}
                for row in terminal_winners
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
    target = q8[target_quarter] if target_fold == "R8" else q6[target_quarter]

    adverse_single = v43._discover_single(source8, source6)
    adverse_pair = v43._discover_pairs(source8, source6)
    rescue_single, rescue_pair = _discover_rescue(
        source8,
        source6,
        adverse_single=adverse_single,
        adverse_pair=adverse_pair,
    )
    evaluation = _evaluate(
        target,
        adverse_single=adverse_single,
        adverse_pair=adverse_pair,
        rescue_single=rescue_single,
        rescue_pair=rescue_pair,
    )
    return {
        "target_fold": target_fold,
        "target_quarter": target_quarter + 1,
        "target_used_for_selection": False,
        "adverse_single_rule_count": len(adverse_single),
        "adverse_pair_rule_count": len(adverse_pair),
        "rescue_single_rule_count": len(rescue_single),
        "rescue_pair_rule_count": len(rescue_pair),
        "evaluation": evaluation,
    }


def _aggregate(runs: list[dict[str, object]]) -> dict[str, object]:
    evals = [cast(dict[str, object], row["evaluation"]) for row in runs]
    total_losses = sum(int(e["losses"]) for e in evals)
    total_winners = sum(int(e["winners"]) for e in evals)
    adverse_losses = sum(int(e["adverse_losses"]) for e in evals)
    adverse_winners = sum(int(e["adverse_winners"]) for e in evals)
    rescued_losses = sum(int(e["rescued_losses"]) for e in evals)
    rescued_winners = sum(int(e["rescued_winners"]) for e in evals)
    terminal_losses = sum(int(e["terminal_losses"]) for e in evals)
    terminal_winners = sum(int(e["terminal_winners"]) for e in evals)

    adverse_winner_r = sum((_d(e["adverse_winner_r_exposure"]) for e in evals), ZERO)
    rescued_winner_r = sum((_d(e["rescued_winner_r"]) for e in evals), ZERO)
    rescued_loss_r = sum((_d(e["rescued_loss_r"]) for e in evals), ZERO)
    terminal_winner_r = sum((_d(e["terminal_winner_r_exposure"]) for e in evals), ZERO)
    terminal_loss_r = sum((_d(e["terminal_loss_r_identified"]) for e in evals), ZERO)

    return {
        "target_run_count": len(runs),
        "total_losses": total_losses,
        "total_winners": total_winners,
        "adverse_losses": adverse_losses,
        "adverse_winners": adverse_winners,
        "adverse_loss_recall": _ratio(adverse_losses, total_losses),
        "adverse_winner_false_positive_rate": _ratio(adverse_winners, total_winners),
        "adverse_winner_r_exposure": format(adverse_winner_r, "f"),
        "rescued_losses": rescued_losses,
        "rescued_winners": rescued_winners,
        "rescued_loss_r": format(rescued_loss_r, "f"),
        "rescued_winner_r": format(rescued_winner_r, "f"),
        "terminal_losses": terminal_losses,
        "terminal_winners": terminal_winners,
        "terminal_loss_recall": _ratio(terminal_losses, total_losses),
        "terminal_winner_false_positive_rate": _ratio(terminal_winners, total_winners),
        "terminal_loss_r_identified": format(terminal_loss_r, "f"),
        "terminal_winner_r_exposure": format(terminal_winner_r, "f"),
        "winner_count_reduction_vs_adverse": adverse_winners - terminal_winners,
        "winner_r_reduction_vs_adverse": format(adverse_winner_r - terminal_winner_r, "f"),
        "loss_count_sacrificed_to_rescue": rescued_losses,
        "loss_r_sacrificed_to_rescue": format(rescued_loss_r, "f"),
        "winner_rescue_efficiency_r_per_loss_r": (
            None
            if rescued_loss_r == ZERO
            else format(rescued_winner_r / rescued_loss_r, "f")
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
        trades=r8_trades, nas=r8_nas, sp=r8_sp, us=r8_us, daily=daily
    )
    r6_source = v18._load_cross_rows(
        trades=r6_trades, nas=r6_nas, sp=r6_sp, us=r6_us, daily=daily
    )
    if len(r8_source) != 228 or len(r6_source) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v26._prepare(
        r8_source, nas_evidence=r8_nas, sp_evidence=r8_sp, us_evidence=r8_us
    )
    p6, _ = v26._prepare(
        r6_source, nas_evidence=r6_nas, sp_evidence=r6_sp, us_evidence=r6_us
    )
    rows8 = v41._all_sequence_rows(p8, sp_evidence=r8_sp, us_evidence=r8_us)
    rows6 = v41._all_sequence_rows(p6, sp_evidence=r6_sp, us_evidence=r6_us)
    q8 = v43._quarters(rows8)
    q6 = v43._quarters(rows6)

    target_runs = [
        _target_run(target_fold=fold, target_quarter=quarter, q8=q8, q6=q6)
        for fold in ("R8", "R6")
        for quarter in range(4)
    ]
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "LOQO_RELATIONAL_RECOVERY_BALANCE_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "relation_count": len(RELATIONS),
        "relation_view_count": len(RELATION_VIEWS),
        "pair_relation_view_count": len(PAIR_RELATION_VIEWS),
        "discovery_contract": {
            "target_used_for_selection": False,
            "rescue_requires_zero_source_losses_each_fold": True,
            "rescue_requires_minimum_one_source_winner_each_fold": True,
            "numeric_threshold_grid_search": False,
            "semantic_relations_only": True,
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
    print(json.dumps({
        "status": payload["status"],
        "aggregate": payload["aggregate"],
        "target_runs": payload["target_runs"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
